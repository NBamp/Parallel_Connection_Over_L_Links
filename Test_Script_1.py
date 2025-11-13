class Channel:

    def __init__(self,num_links,subframes,symbol_size):

        self.num_links = num_links
        self.subframes = subframes
        self.symbol_size = symbol_size
        self.frames = 0
        self.trans_packets = [0] * self.num_links #transmitted packets for each link
        self.data_rate = [0] * self.num_links #data rate for each link divided with the number of frame when block is fully decoded
        self.loss_packet_rate = [0] * self.num_links #loss packet rate for each link divided with the number of frame when block is fully decoded
        self.loss_packets = [0] * self.num_links #loss packets for each link
        self.m = [0] * self.num_links #basically the m1,m2,... computed for each link
        self.avg_delay = [0] * self.num_links #basically the a1,a2,... computed for each link
        self.link_range = [self.subframes] * num_links #equal to scheduling on how many subframes will each link have based on for link 1 m1/m1+m2 ...
        self.channel_transmitted = [] #A list of dicts which contain frame:sum of transmitted packets in this frame

        for i in range(num_links):
            self.channel_transmitted.append(dict())



    def update(self):

        self.frames += 1
        sum_m = 0 #denominator will all m computed
        for i in self.m:  
            sum_m += i  #If sum_ = 0 ti kanoume?????

        for i in range(len(self.link_range)):
            if sum_m ==0:
                self.link_range[i] = 1
            else:
                self.link_range[i] = (self.m[i] / sum_m) * self.subframes #new schedule for each link
                first_decimal = int(abs(self.link_range[i] * 10)) % 10 #in case the result is float number it follows rounding
                if first_decimal<5:
                    self.link_range[i]= math.floor(self.link_range[i])
                else:
                    self.link_range[i]= math.ceil(self.link_range[i])
            print(f"Scheduler decided to send {self.get_link_range(i)} packets to link {i+1}")
        print("\n\n")

    def update_rate(self):
        for i in range(len(self.data_rate)):
            self.data_rate[i] = (self.trans_packets[i] * self.symbol_size)  / self.frames
            self.loss_packet_rate[i] = (self.loss_packets[i] * self.symbol_size) / self.frames
            print(f"Data rate for link {i+1} = {self.data_rate[i]:.2f} symbol/frame\n"
                  f"Loss packet rate for link {i+1} = {self.loss_packet_rate[i]:.2f} symbol/frame")


    def get_link_range(self,i): # For link with index i return the link_range
        return self.link_range[i]
    
    def get_transmmitedpackets(self,index):
        return self.trans_packets[index]

    def get_losspackets(self,index):
        return self.loss_packets[index]

    def get_frames(self):
        return self.frames

    def set_transmitted_packets(self,index,total):
        self.trans_packets[index] += total

    def set_loss_packets(self,index,total):
        self.loss_packets[index] += total

    def set_m(self,index,transmitted,losses,block_frame):
        self.m[index] =  transmitted/(transmitted+losses) #Otan m[i]=0 ???? gia ton scheduler
        self.set_transmitted_packets(index,transmitted)
        self.set_loss_packets(index,losses)
        self.channel_transmitted[index][block_frame] = transmitted
        print(f"For link {index+1} in total {self.get_link_range(index)} packets {transmitted} were transmitted and {losses} were lost!!")

    def sum_trans_loss(self):

        trans_sum , loss_sum , total = 0,0,0
        for i in range(self.num_links):
            trans_sum += self.trans_packets[i]
            loss_sum += self.loss_packets[i]
        total = trans_sum + loss_sum

        return trans_sum,loss_sum,total

    def clear_transmitted_channel(self):
        for i in self.channel_transmitted:
            i.clear()

    def avg_delay_compute(self,block_frame):
        for i in range(self.num_links):
            packets_per_block = 0 #counter for each link
            for j in self.channel_transmitted[i]:
                packets_per_block += self.channel_transmitted[i][j]
                self.avg_delay[i] += self.channel_transmitted[i][j] * (block_frame-j)
            if packets_per_block == 0:
                packets_per_block = 1
            self.avg_delay[i] =  self.avg_delay[i]/packets_per_block

import random
import argparse
import math
import time

import pyerasure.block as pyblock
import pyerasure.finite_field
import pyerasure.block.generator as pygenerator


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--num_symbols", help="Total number of transmitted symbols")
    parser.add_argument("--symbol_size", help="Symbol size in bytes")
    parser.add_argument("--seed", help="Seed to control randomness")
    parser.add_argument("--block_size", help="Block (generation) size")
    parser.add_argument("--frame_size", help="How many subframes does a frame contains?")

    args = parser.parse_args()

    symbols = int(args.num_symbols)
    symbol_bytes = int(args.symbol_size)
    seed = int(args.seed)
    block_size = int(args.block_size)
    frame_size = int(args.frame_size)

    num_links = int(input("Define the number of links for the simulation : "))
    data_rate_arr = num_links * [0]  #array which contains data rate for each link
    loss_prob_arr = num_links * [0]   #array which contains loss probability for each link

    channel = Channel(num_links,frame_size,block_size)

    for i in range(num_links):
        loss_prob_arr[i] = (float((input(f"Enter channel {i+1} loss probability rate in range[0,1] : "))))
        data_rate_arr[i] = (float(input(f"Enter channel {i+1}  data rate  in range[0,1]  : ")))


    print(f"PyErasure Simulation\n---------------------------------------")
    # print(f"Number of Transmitted Symbols: \t{args.num_symbols}\nSymbol Size (bytes): \t\t{args.symbol_size}\nBlock size: \t\t\t{args.block_size}\nLoss Probability (%): \t\t{args.ploss}\nSeed: \t\t\t\t{args.seed}")

    # Pick the finite field to use for the encoding and decoding.
    field =  pyerasure.finite_field.Binary8()

    # Allocate some data to encode - fill data_in with random data
    random.seed(seed)
    data_in = bytearray(random.getrandbits(8) for _ in range(symbols*symbol_bytes))



    elapsed_timeslots = 0 # indicating how many timeslots have elapsed since the beginning of transmission
    transmitted_packets = 0 # counter for the total number of source packets sent from the encoder

    offset = 0
    is_seed_set = False # to tune generator's seed

    num_of_blocks = 0

    start = time.time()

    while True:

        if offset >= len(data_in):
            break
        #maybe use memoryview instead, check if error occurs with indexing
        block_data = data_in[offset:offset + block_size*symbol_bytes] #no error if index exceeds length
        offset += block_size*symbol_bytes

        current_block_size = symbols % block_size if len(block_data) != block_size*symbol_bytes else block_size

        # Create encoder and decoder to handle block size data each time (smaller last block size in case of inexact division)
        encoder = pyblock.Encoder(field, current_block_size, symbol_bytes)
        decoder = pyblock.Decoder(field, current_block_size, symbol_bytes)

        num_of_blocks += 1

        # Create generator generator. The generator must similarly be created
        # based on the encoder/decoder.
        generator = pygenerator.RandomUniform(field, encoder.symbols)
        if not is_seed_set:
            generator.set_seed(seed)
            is_seed_set = True

        encoder.set_symbols(block_data)

        block_frame = 0
        while not decoder.is_complete():


            start = decoder.rank
            for index in range(num_links):
                transmitted_packets,loss_packets = 0,0
                for i in range(channel.get_link_range(index)):

                        coefficients = generator.generate()
                        symbol = encoder.encode_symbol(coefficients)

                        if random.uniform(0, 1) >= loss_prob_arr[index]:
                            decoder.decode_symbol(symbol, bytearray(coefficients))
                            transmitted_packets+=1
                        else:
                            loss_packets+=1
                if transmitted_packets==0 and loss_packets==0:
                    continue
                else:
                    channel.set_m(index,transmitted_packets,loss_packets,block_frame)


            channel.update()

            block_frame+=1


        channel.avg_delay_compute(block_frame)
        channel.clear_transmitted_channel()
        





        print("---------------------------------------")
        print(f"Block {num_of_blocks} was fully decoded!!!")
        channel.update_rate()
        print(f"Total frames used for block {num_of_blocks} are {block_frame}!")
        print("---------------------------------------\n\n\n")




    end = time.time()

    Total_trans,Total_loss,Total_Packets = channel.sum_trans_loss()

    print("#####-----Statistics-----#####")
    print(f"Total Transmitted packets: \t{Total_trans}")
    print(f"Total Lost packets: \t{Total_loss}")
    print(f"Total elapsed time: \t\t{end-start} sec")
    print(f"Total frames spent: \t\t{channel.get_frames()}")
    print(f"Final packet_delivery_ratio for system = {Total_trans/Total_Packets:.2f}")
    print(f"Final loss_rate for system =  {Total_loss/Total_Packets:.2f}")







if __name__ == "__main__":
    main()
