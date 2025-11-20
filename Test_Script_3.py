class Channel:

    def __init__(self,symbol_size):

        self._frame_size = 0
        self._symbol_size = symbol_size
        self._capacity = 2  # Assume each link start with this value before defining correlation
        self._assigned_packets = 0  # how many assigned packets scheduled in this link
        self._frames = 0  # Number of frames link has covered
        self._r_t = 0  # Metric for current data_rate focusing on frame explicitly based on survey
        self._R_t = 0  # Metric for past_average_throughput based on survey
        self._past_throughput_array = [] #For storing past throughput
        self._channel_transmitted = {}  # Dictionary with pair {frame_number:[transmitted_packets,loss_packets] , one pair for each frame used by the link and clear dictionary after block is fully decoded
        self.avg_delay_per_block = 0 #Average delay packet per link computed after block if fully decoded
        self.avg_delay = [] #Use for storing average delay for each block in order to make an average in the end
        self.loss_probability = 0 #Loss probability per link given by the user
        self.total_successfully_transmitted_packets = 0
        self.total_loss_packets = 0
        self.total_transmitted_packets = 0


    @property
    def frame_size(self):
        return self._frame_size

    @property
    def capacity(self):
        return self._capacity

    @property
    def assigned_packets(self):
        return self._assigned_packets

    @frame_size.setter
    def frame_size(self,size):
        self._frame_size = size

    @capacity.setter
    def capacity(self, length):
       self._capacity = length
        #self._assigned_packets = length  # The first time scheduler assigns number of packets equal to capacity for each link

    @assigned_packets.setter
    def assigned_packets(self, value):
        self._assigned_packets = value


    def set_packets(self, trans, loss):

        self._channel_transmitted[self._frames] = [trans,loss]
        self.total_successfully_transmitted_packets += trans
        self.total_loss_packets += loss
        self.total_transmitted_packets += trans + loss

    def compute_metric(self, transmitted, losses):

        self.set_packets(transmitted, losses)
        self._r_t = transmitted / (transmitted + losses)
        if self._frames == 0:  # In first time there is no past average throughput so for convenient 1 is used
            self._R_t = self._r_t
        else:
            if len(self._past_throughput_array)==2:  #In order to reduce estimated cost
                sum_of_past_throughput = 0
                for i in self._past_throughput_array:
                    sum_of_past_throughput += i
                self._past_throughput_array[0] = sum_of_past_throughput/2
                self._past_throughput_array.pop()
            self._R_t = self._past_throughput_array[0]
        self._past_throughput_array.append(self._r_t)  # Update past average throughput
        self._frames += 1
        print(f"Current r(t) = {self._r_t}\nCurrent R(t) = {self._R_t:.2f}")
        return self._r_t/self._R_t



    #Without checking for min/max in assigned packets , total frame_size is covered each time scheduler works per link.The problem begins when assigned_packets is within [1-capacity's link] which is of course reasonable to be.

    def schedule_packets(self,index,array):

        denominator = 0
        for i in array:
            denominator += i
        self.assigned_packets = int(round((array[index]/denominator) * self.frame_size))
        print(f"[Assigned packets for channel_{index+1} = {self.assigned_packets} before limitations with link's capacity]")
        if self.assigned_packets < 1:
            self.assigned_packets = 1
        elif self.assigned_packets > self.capacity:
            self.assigned_packets = self.capacity
        print(f"Assigned packets for channel {index+1} = {self.assigned_packets}")

    def clear_past_throughput_array(self): #When block is decoded fully, array which contains past throughputs clears./
        self._past_throughput_array.clear()


    def clear_transmitted_channel(self):
        self._channel_transmitted.clear()

    def avg_delay_per_block_compute(self):

        successfully_transmitted_packets_per_block = 0
        for i in self._channel_transmitted:
            successfully_transmitted_packets_per_block += self._channel_transmitted[i][0]
            self.avg_delay_per_block += (self._channel_transmitted[i][0]) * (self._frames - i)
        self.avg_delay_per_block = self.avg_delay_per_block / successfully_transmitted_packets_per_block
        self.avg_delay.append(self.avg_delay_per_block)

    def avg_delay_compute(self):

        delay = 0
        for i in self.avg_delay:
            delay += i
        return delay/len(self.avg_delay)





import random
import argparse
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
    parser.add_argument("--frames_for_scheduler_update" , help="After how many frames the scheduler will start execution?")

    args = parser.parse_args()

    symbols = int(args.num_symbols)
    symbol_bytes = int(args.symbol_size)
    seed = int(args.seed)
    block_size = int(args.block_size)
    multiple_k = int(args.frames_for_scheduler_update)

    num_links = int(input("Define the number of links for the simulation : "))
    proportional_fair_metric = [0 for _ in range(num_links)]  # array which contains metric for proportional fair scheduler for each link
    channels = [Channel(symbol_bytes) for _ in range(num_links)]  # List containing one Channel Object for each link

    frame_size = 0
    for i in range(num_links):

        channels[i].loss_probability = (float((input(f"Enter channel {i + 1} loss probability rate in range[0,1] : "))))

        if i == num_links-1 and num_links == 2:
            break

        if i == num_links-1 and num_links != 2:

            a,b =  map(int,(input(f"Enter capacity correlation between channel {1}  and {i+1} in form k/n : ")).split('/'))
            channels[i].capacity = int((round((b/a) * channels[0].capacity)))
            frame_size += channels[0].capacity
            frame_size += channels[i].capacity
        else:
            a,b =  map(int,(input(f"Enter capacity correlation between channel {i+1}  and {i+2} in form k/n : ")).split('/'))
            channels[i+1].capacity = int((round((b/a) * channels[i].capacity)))
            frame_size += channels[i].capacity
            frame_size += channels[i+1].capacity


    for i in channels:
        i.frame_size = frame_size
        i.assigned_packets = i.capacity
        print(f"For channel {channels.index(i) + 1} capacity of subframes = {i.capacity}")

    print(f"Total frame_size = {frame_size}")



    print(f"PyErasure Simulation\n---------------------------------------\n\n")
    # print(f"Number of Transmitted Symbols: \t{args.num_symbols}\nSymbol Size (bytes): \t\t{args.symbol_size}\nBlock size: \t\t\t{args.block_size}\nLoss Probability (%): \t\t{args.ploss}\nSeed: \t\t\t\t{args.seed}")

    # Pick the finite field to use for the encoding and decoding.
    field = pyerasure.finite_field.Binary8()

    # Allocate some data to encode - fill data_in with random data
    random.seed(seed)
    data_in = bytearray(random.getrandbits(8) for _ in range(symbols * symbol_bytes))

    offset = 0
    is_seed_set = False  # to tune generator's seed

    num_of_blocks = 0

    start = time.time()

    while True:

        if offset >= len(data_in):
            break
        # maybe use memoryview instead, check if error occurs with indexing
        block_data = data_in[offset:offset + block_size * symbol_bytes]  # no error if index exceeds length
        offset += block_size * symbol_bytes

        current_block_size = symbols % block_size if len(block_data) != block_size * symbol_bytes else block_size

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

        block_frame = 0  # In order to get how many frames spent for each block
        while not decoder.is_complete():

            start = decoder.rank
            for i in channels:
                successfully_transmitted_packets, loss_packets = 0, 0  # counters for transmitted and loss packets for each link packet assignment
                for j in range(i.assigned_packets):
                    coefficients = generator.generate()
                    symbol = encoder.encode_symbol(coefficients)
                    if random.uniform(0, 1) >= i.loss_probability:
                        decoder.decode_symbol(symbol, bytearray(coefficients))
                        successfully_transmitted_packets += 1
                    else:
                        loss_packets += 1
                print(f"For channel_{channels.index(i)+1} total transmitted packets are {successfully_transmitted_packets+loss_packets} , successfully transmitted packets are {successfully_transmitted_packets} and loss packets are {loss_packets} in frame {block_frame}")
                proportional_fair_metric[channels.index(i)] = i.compute_metric(successfully_transmitted_packets, loss_packets)


            print("---------------------------------------\n")
            block_frame += 1
            if block_frame % multiple_k == 0:
                for i in channels:
                    i.schedule_packets(channels.index(i),proportional_fair_metric)
            print('\n\n')

        # After block is fully decoded
        for i in channels:
            i.avg_delay_per_block_compute()
            i.clear_transmitted_channel()
            print(f"Average delay for channel_{channels.index(i)+1} = {i.avg_delay_per_block:.2f}")


        print("\n\n")
        print("---------------------------------------")
        print(f"Block {num_of_blocks} was fully decoded!!!")
        print(f"Total frames used for block {num_of_blocks} are {block_frame}!")
        print("---------------------------------------\n\n")



    end = time.time()



    print("#####-----Statistics-----#####")
    print(f"Total elapsed time: \t\t{end-start} sec\n")
    for i in channels:
        print(f"For channel_{channels.index(i)+1}\nTotal transmitted packets = {i.total_transmitted_packets}\nTotal successfully transmitted packets = {i.total_successfully_transmitted_packets}"
              f"\nTotal lost packets = {i.total_loss_packets}\nFinal average delay = {i.avg_delay_compute():.2f}\n\n")

if __name__ == "__main__":
    main()
