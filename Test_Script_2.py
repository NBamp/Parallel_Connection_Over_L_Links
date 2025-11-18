

class Channel:

    def __init__(self,frame_size,symbol_size):


        self.frame_size = frame_size
        self.symbol_size = symbol_size
        self.capacity = 0 #capacity of link
        self.assigned_packets = 0 #how many assigned packets scheduled in this link
        self.frames = 0 #Number of frame link has covered
        self.r_t = 0 #Metric for current data_rate focusing on frame explicitly based on survey
        self.R_t = 0 #Metric for past_average_throughput based on survey
        #Idea,we could also use R_t at the end of each block as kind of data_rate metric
        self.data_rate = 0  #Data rate measured in packets per frame and updated after the block is fully decoded , follows idea about it
        #Because each frame duration depends on number of assigned packets the scheduler made in this link , and because this number differs per each frame,
        #we could compute data_rate at the end of block in similar way as we do in the loss possibility using the sum of transmitted packets divided with the sum of total assigned packets spent
        #The only problem in this approach it is that nor symbol_size nor frame is measured .
        self.actual_loss_possibility = 0 #Actual possibility of packet loss through link
        self.channel_transmitted = {} #Dictionary with pair {assigned_packets:[transmitted_packets,loss_packets] , one pair for each frame used by the link and clear dictionary after block is fully decoded

        #Follows fields for delay,not for the moment
        self.avg_delay = 0



    def get_transmmitedpackets(self):
        return self.trans_packets

    def get_losspackets(self):
        return self.loss_packets

    def get_frames(self):
        return self.frames

    def get_capacity(self):
        return self.capacity

    def get_data_rate(self):
        return self.data_rate

    def get_actual_loss_possibility(self):
        return self.actual_loss_possibility

    def set_transmitted_loss_possibility(self,trans,loss):
        self.channel_transmitted[self.frames] = []
        self.channel_transmitted[self.frames].append(trans)
        self.channel_transmitted[self.frames].append(loss)
        


    def set_capacity_and_assigned(self,length):
        self.capacity = length
        self.assigned_packets = length #The first time scheduler assigns number of packets equal to capacity for each link

    def update_after_the_end_of_frame(self,transmitted,losses):

        self.r_t =  transmitted/(transmitted+losses)
        if self.frames == 0: #In first time there is no past average throughput so for convenient 1 is used
            self.R_t = 1
        self.set_transmitted_loss_possibility(transmitted,losses)
        print(f"Current r(t) = {self.r_t}\nCurrent R(t) = {self.R_t}")
       #self.channel_transmitted[block_frame] = transmitted
        self.frames += 1
        self.assigned_packets = (self.r_t/self.R_t) * self.frame_size #Computing the metric for proportional and multiplying with the frame size for finding the number of packets the scheduler assigns in this link
        first_decimal = int(abs(self.assigned_packets * 10)) % 10 #in case the result is float number it follows rounding
        if first_decimal<5:
            self.assigned_packets = math.floor(self.assigned_packets)
        else:
            self.assigned_packets= math.ceil(self.assigned_packets)
        if self.assigned_packets < 1: #In case r(t) == 0 we avoid  sending 0 packets
            self.assigned_packets = 1
        if self.assigned_packets > self.capacity: #In case the compute results in number larger than capacity of link we assign max the capacity link
            self.assigned_packets = self.capacity
        self.R_t += self.r_t #Update past average throughput

    def update_data_rate_loss_possibility(self,index):

        trans_packets = 0
        loss_packets = 0
        total_subframes_spent = 0
        
        for i in self.channel_transmitted:
            total_subframes_spent += self.channel_transmitted[i][0] + self.channel_transmitted[i][1]
            trans_packets += self.channel_transmitted[i][0]
            loss_packets += self.channel_transmitted[i][1]


        self.data_rate = trans_packets/total_subframes_spent
        self.actual_loss_possibility = loss_packets/total_subframes_spent
        print(f"For channel {index+1}\n---------\nTotal transmitted packets = {trans_packets}\nTotal loss packets = {loss_packets}\nTotal subframes spent = {total_subframes_spent}\nData_rate = {self.data_rate:.2f}\nActual_loss_possibility = {self.actual_loss_possibility:.2f}\n")

        self.channel_transmitted.clear()


    #ignore these methods beneath,they are attempts for computing delay
    '''def clear_transmitted_channel(self):
        self.channel_transmitted.clear()

    def avg_delay_compute(self):

        packets_per_block = 0 #counter for each link
        for i in self.channel_transmitted:
            if self.channel_transmitted[i] == 0:
                continue
            packets_per_block += self.channel_transmitted[i]
            self.avg_delay += self.channel_transmitted[i] * (self.frames-i)
        if packets_per_block == 0:
            packets_per_block = 1
        self.avg_delay = self.avg_delay/packets_per_block'''

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

    channels = [] # List containing one Channel Object for each link

    for i in range(num_links):
        loss_prob_arr[i] = (float((input(f"Enter channel {i+1} loss probability rate in range[0,1] : "))))
        data_rate_arr[i] = (float(input(f"Enter channel {i+1}  data rate  in range[0,1]  : ")))
        channels.append(Channel(frame_size,symbol_bytes))

    #Don't pay too much attention on the below algorithm!!
    #Follows algorithm for defining length of capacity in links based on data_rate and the given frame.Works efficiently only for two links , for more than two maybe we will use numpy to find linear dependency between numbers or we can avoid this by manually defining the capacity for each link,simplifying our code and life (!).
    indexing = data_rate_arr.index(max(data_rate_arr))
    equal_frame_size = frame_size
    while equal_frame_size>0 and channels[indexing].get_capacity()==0:

        if data_rate_arr[indexing]*frame_size > equal_frame_size:
            channels[indexing].set_capacity_and_assigned(equal_frame_size)
        else:
            channels[indexing].set_capacity_and_assigned(int(data_rate_arr[indexing]*frame_size))
        equal_frame_size -= channels[indexing].get_capacity()

        indexing += 1 if indexing+1<len(data_rate_arr) else -1


    for i in channels:
        print(f"For channel {channels.index(i)+1} capacity of subframes is {i.get_capacity()}.")


    print(f"PyErasure Simulation\n---------------------------------------\n\n")
    # print(f"Number of Transmitted Symbols: \t{args.num_symbols}\nSymbol Size (bytes): \t\t{args.symbol_size}\nBlock size: \t\t\t{args.block_size}\nLoss Probability (%): \t\t{args.ploss}\nSeed: \t\t\t\t{args.seed}")

    # Pick the finite field to use for the encoding and decoding.
    field =  pyerasure.finite_field.Binary8()

    # Allocate some data to encode - fill data_in with random data
    random.seed(seed)
    data_in = bytearray(random.getrandbits(8) for _ in range(symbols*symbol_bytes))

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

        block_frame = 0  #In order to get how many frames spent for each block
        while not decoder.is_complete():

            start = decoder.rank
            for i in channels:
                transmitted_packets,loss_packets = 0,0  #counters for transmitted and loss packets for each link packet assignment
                for j in range(i.assigned_packets):
                    coefficients = generator.generate()
                    symbol = encoder.encode_symbol(coefficients)
                    if random.uniform(0, 1) >= loss_prob_arr[channels.index(i)]:
                        decoder.decode_symbol(symbol, bytearray(coefficients))
                        transmitted_packets+=1
                    else:
                        loss_packets+=1
                print(f"For link {channels.index(i)+1} with total {i.assigned_packets} packets , {transmitted_packets} were transmitted and {loss_packets} were lost!!")
                i.update_after_the_end_of_frame(transmitted_packets,loss_packets)
                print(f"Scheduler decided to send {i.assigned_packets} packets to link {channels.index(i) + 1}")
            print("---------------------------------------\n")
            block_frame += 1


        #After block is fully decoded
        for i in channels:
            i.update_data_rate_loss_possibility(channels.index(i))

        print("\n\n")
        print("---------------------------------------")
        print(f"Block {num_of_blocks} was fully decoded!!!")
        print(f"Total frames used for block {num_of_blocks} are {block_frame}!")
        print("---------------------------------------\n\n")

        """  print("\n\n")
        for i in channels:
            i.avg_delay_compute()
            print(f"Average delay packet for link {channels.index(i) + 1} = {i.avg_delay:.2f}")
            i.clear_transmitted_channel()
            i.update_rate()
            print(f"Data rate for link {channels.index(i)+1} = {i.r_t:.2f} symbol/frame\n"
              f"Loss packet rate for link {channels.index(i)+1} = {i.loss_packet_rate:.2f} symbol/frame")"""


    end = time.time()

  #  Total_trans,Total_loss,Total_Packets = channel.sum_trans_loss()

 #   print("#####-----Statistics-----#####")
 #   print(f"Total Transmitted packets: \t{Total_trans}")
 #   print(f"Total Lost packets: \t{Total_loss}")
 #   print(f"Total elapsed time: \t\t{end-start} sec")
#    print(f"Total frames spent: \t\t{channel.get_frames()}")
 #   print(f"Final packet_delivery_ratio for system = {Total_trans/Total_Packets:.2f}")
 #   print(f"Final loss_rate for system =  {Total_loss/Total_Packets:.2f}")







if __name__ == "__main__":
    main()
