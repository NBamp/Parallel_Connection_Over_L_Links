class Channel:

    def __init__(self,symbol_size):

        self._frame_size = 0
        self._symbol_size = symbol_size
        self._capacity = 0  # Assume each link start with this value before defining correlation
        self._frames = 0  # Number of frames link has covered
        self._channel_transmitted_dict = {}  # Dictionary with pair {frame_number:[transmitted_packets,loss_packets] , one pair for each frame used by the link and clear dictionary after block is fully decoded
        self.loss_probability = 0 #Loss probability per link given by the user
        self.total_successfully_transmitted_packets = 0
        self.total_loss_packets = 0
        self.total_transmitted_packets = 0

        self.unused_packets = [] #Number of unused packets used for each channel in encoding version

        #Metrics for scenario with source packets
        self.transmitted_packets = [] #Transmitted packets each time in scenario with source packets
        self.lost_packets = [] #Array with lost packets in source version
        self.added_packets = []  #Two dimension array with new packets from encoder for each link per block_frame






    @property
    def frames(self):
        return self._frames

    @property
    def frame_size(self):
        return self._frame_size

    @property
    def capacity(self):
        return self._capacity

    @frame_size.setter
    def frame_size(self,size):
        self._frame_size = size

    @capacity.setter
    def capacity(self, length):
       self._capacity = length
        #self._assigned_packets = length  # The first time scheduler assigns number of packets equal to capacity for each link

    @property
    def channel_transmitted_dict(self):
        return self._channel_transmitted_dict

    def update_by_the_end_of_frame(self, trans, loss):

        self._frames += 1
        self._channel_transmitted_dict[self._frames] = [trans,loss]
        self.total_successfully_transmitted_packets += trans
        self.total_loss_packets += loss
        self.total_transmitted_packets += trans + loss


    #Compute total number of successfully transmitted  packets per block
    def successfully_transmitted_packets_per_block(self):

        successfully_transmitted_packets_per_block = 0
        for i in self._channel_transmitted_dict:
            successfully_transmitted_packets_per_block += self._channel_transmitted_dict[i][0]
        return successfully_transmitted_packets_per_block



    #Computing data_rate and avg_delay_per_packet in scenario with coding packets per block
    def avg_delay_in_encoding_scenario_compute(self):

        delay = 0
        successfully_transmitted_packets_per_block = 0
        for i in self._channel_transmitted_dict:
            successfully_transmitted_packets_per_block += self._channel_transmitted_dict[i][0]
            delay +=  (self.frames - i) * self._channel_transmitted_dict[i][0]

        return delay/successfully_transmitted_packets_per_block


    def compute_number_of_losses_per_block(self):

        loss = 0
        for i in self._channel_transmitted_dict:
            loss += self._channel_transmitted_dict[i][1]
        return loss

    def compute_number_of_successfully_transmitions_per_block(self):

        packets = 0
        for i in self._channel_transmitted_dict:
            packets += self._channel_transmitted_dict[i][0]
        return packets

    #After block is decoded clear metrics

    def clear_arrays_for_encoding_version(self):
        self._channel_transmitted_dict.clear()
        self.unused_packets.clear()


    def clear_arrays_for_source_version(self):

        self.transmitted_packets.clear()
        self.added_packets.clear()
        self.lost_packets.clear()




import random
import argparse
import time
import math

import pyerasure.block as pyblock
import pyerasure.finite_field
import pyerasure.block.generator as pygenerator



def compute_total_frames(array):
    sum_frames = 0
    for i in array:
        sum_frames += i
    return sum_frames

def compute_total_successfully_transmitted_packets(array):
    sum_total_frames = 0
    for i in array:
        sum_total_frames += i.total_successfully_transmitted_packets
    return sum_total_frames

def compute_average_throughput(array):
    throughput = 0
    for i in array:
        throughput += i
    return throughput/len(array)

def compute_average_delay(array):
    delay = 0
    for i in array:
        delay += i
    return delay/len(array)

def compute_unused_packets_per_block_network_coding_version(array):
    unused = 0
    for i in array:
        if i.unused_packets:
            unused += i.unused_packets[0]
    return unused


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--num_symbols", help="Total number of transmitted symbols")
    parser.add_argument("--symbol_size", help="Symbol size in bytes")
    parser.add_argument("--seed", help="Seed to control randomness")
    parser.add_argument("--block_size", help="Block (generation) size")
    parser.add_argument("--encoding", help="Whether there is encoding or not,type Yes for encoding,No otherwise")

    print("Reminder , for testing scenario with source packets select a much larger block_size compared to frame_size.")

    args = parser.parse_args()

    symbols = int(args.num_symbols)
    symbol_bytes = int(args.symbol_size)
    seed = int(args.seed)
    block_size = int(args.block_size)
    encoding = args.encoding.lower()

    avg_data_rate = [] #Array for storing data_rate per block
    avg_delay = [] #Array for storing avg_delay per block
    total_frames = [] #Array for storing number of frames per block
    total_transmitted_packets = [] #Array for storing total transmitted packets per block
    total_useful_packets = []  #Array of useful packets per block
    total_lost_packets = []  #Array of lost packets per block
    total_unuseful_packets = []  #Array of unuseful packets in encoding scenario


    num_links = int(input("Define the number of links for the simulation : "))

    channels = [Channel(symbol_bytes) for _ in range(num_links)]  # List containing one Channel Object for each link

    frame_size = 0

    for i in range(num_links):

        channels[i].loss_probability = (float((input(f"Enter channel {i+1} loss probability rate in range[0,1] : "))))
        channels[i].capacity = int(input(F"Enter channel {i+1}'s capacity measured in subframes : "))
        frame_size += channels[i].capacity

    for i in channels:
        i.frame_size = frame_size

    print(f"Total frame_size = {frame_size}")



    print(f"PyErasure Simulation\n---------------------------------------\n\n")

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

        # Create  generator. The generator must similarly be created
        # based on the encoder/decoder.
        generator = pygenerator.RandomUniform(field, encoder.symbols)
        if not is_seed_set:
            generator.set_seed(seed)
            is_seed_set = True

        encoder.set_symbols(block_data)

        block_frame = 0  # In order to get how many frames spent for each block

        #Variables used for source packet scenario
        #-----------------------------------------

        #Keep of pair index:symbol of encoder_symbols_data
        d_encoder_symbols_data = {}
        for i in range(encoder.rank):
            d_encoder_symbols_data[i] = encoder.symbol_data(i)

        #Counters used for scenario with source packets in order to assign appropriately number of packets in each link
        source_counter_start = 0
        packet_arrived_and_decoded_frame_dict = {} # Pair with index of encoder_symbol : [frame_arrived,frame_decoded]

        while not decoder.is_complete():

            for channel in channels:

                successfully_transmitted_packets, loss_packets = 0, 0  # counters for successfully transmitted and lost packets in a frame duration

                #Scenario with encoding follows
                if encoding == "yes":

                    for index in range(channel.capacity):
                        coefficients = generator.generate()
                        symbol = encoder.encode_symbol(coefficients)
                        if random.uniform(0, 1) >= channel.loss_probability:
                            decoder.decode_symbol(symbol, bytearray(coefficients))
                            successfully_transmitted_packets += 1
                        else:
                            loss_packets += 1

                        if decoder.is_complete() and not channel.unused_packets:
                            channel.unused_packets.append((channel.capacity-1) - index)

                    if not (successfully_transmitted_packets == 0 and loss_packets == 0) : #In case successfully_transmitted_packets == 0 and loss_packets == 0 link has nothing else to send , so there is no need for using extra frame.
                        channel.update_by_the_end_of_frame(successfully_transmitted_packets,loss_packets)

                #Scenario with sending source packets
                else:

                    #In order to resend the lost packets of each link
                    if  channel.lost_packets:
                        channel.transmitted_packets = channel.lost_packets[:]
                        source_counter_end =  channel.capacity - len(channel.lost_packets) #In order to assign each time number of packets ==  link capacity
                    else:
                        channel.transmitted_packets = []
                        source_counter_end = channel.capacity


                    for index in channel.lost_packets[:]:

                        symbol = encoder.symbol_data(index)
                        if random.uniform(0, 1) >= channel.loss_probability:
                            decoder.decode_systematic_symbol(symbol, index)
                            packet_arrived_and_decoded_frame_dict[index][1] = channel.frames+1 #Add frame in which symbol  decoded
                            successfully_transmitted_packets += 1
                            channel.lost_packets.remove(index)  #Lost packet doesnt exist anymore
                            print(f"Packet {index} which was arrived in block_frame {packet_arrived_and_decoded_frame_dict[index][0]} , transmitted successfully in block_frame {block_frame+1} ")
                        else:
                            loss_packets +=1


                    starting_list = list(packet_arrived_and_decoded_frame_dict)  #In order to show afterward newly added packets for each link




                    for index in list(d_encoder_symbols_data.keys())[source_counter_start:source_counter_end]:

                        if source_counter_end==0:
                            break

                        symbol = d_encoder_symbols_data[index]

                        if index not in packet_arrived_and_decoded_frame_dict.keys():
                            packet_arrived_and_decoded_frame_dict[index] = [channel.frames+1,0]  #Add frame in which symbol arrived

                        if random.uniform(0, 1) >= channel.loss_probability:
                            decoder.decode_systematic_symbol(symbol, index)
                            packet_arrived_and_decoded_frame_dict[index][1] = channel.frames+1  #Add frame in which symbol  decoded
                            successfully_transmitted_packets += 1
                        else:
                            channel.lost_packets.append(index)
                            loss_packets +=1

                        d_encoder_symbols_data.pop(index)

                    ending_list = list(packet_arrived_and_decoded_frame_dict)  #In order to show afterward newly added packets for each link


                    if  starting_list:
                        channel.added_packets.append([x for x in ending_list if x not in starting_list])
                        channel.transmitted_packets += channel.added_packets[-1]
                    else:
                        channel.added_packets.append(list(packet_arrived_and_decoded_frame_dict))
                        channel.transmitted_packets = list(packet_arrived_and_decoded_frame_dict)

                    if not (successfully_transmitted_packets == 0 and loss_packets == 0) : #In case successfully_transmitted_packets == 0 and loss_packets == 0 link has nothing else to send , so there is no need for using extra frame.
                        channel.update_by_the_end_of_frame(successfully_transmitted_packets,loss_packets)


                print(f"For channel {channels.index(channel)+1} total transmitted packets = {channel.capacity} , successfully transmitted packets are = {successfully_transmitted_packets} , loss packets = {loss_packets} in block_frame {block_frame+1}")
                if encoding == "no":
                    print(f"Transmitted packets = {channel.transmitted_packets}")
                    print(f"Lost packets = {channel.lost_packets}")
                    print(f"New packets added =  {channel.added_packets[-1]}")
                    print("---------------------------------------\n")


            block_frame += 1
            print('\n\n')


        delay = 0
        avg_del = 0
        data_rate_block_numerator = 0
        successfully_transmitted_packets_per_block = 0
        lost_packets_per_block = 0
        unuseful_packets_per_block = 0

        #Metrics for source scenario
        if encoding == "no":

            a , b = "" ,""
            for frame in range(block_frame):

                past_delay = 0

                for i in channels:

                    if not i.added_packets[frame]:
                        continue

                    if a == ""  and b == "":
                        a = i.added_packets[frame][0]

                    if  b == "":
                        b = i.added_packets[frame][-1]

                if b == "":
                    b = len(packet_arrived_and_decoded_frame_dict)

                for symbol in list(packet_arrived_and_decoded_frame_dict)[a:b+1]: #Summary of packets which scheduler sends each time in links,these packets are sent in row.
                    delay = max(past_delay , packet_arrived_and_decoded_frame_dict[symbol][1] - packet_arrived_and_decoded_frame_dict[symbol][0])
                    past_delay = delay
                    avg_del += delay

                avg_del += math.ceil((delay/len(list(packet_arrived_and_decoded_frame_dict)[a:b+1])))


            avg_del = avg_del / block_frame
            data_rate_block_numerator = len(packet_arrived_and_decoded_frame_dict) * symbol_bytes

        #Metrics for encoding scenario
        else:

            for i in channels:
                data_rate_block_numerator += i.successfully_transmitted_packets_per_block() * symbol_bytes
                avg_del += i.avg_delay_in_encoding_scenario_compute()

            unuseful_packets_per_block = compute_unused_packets_per_block_network_coding_version(channels)
            avg_del = math.ceil(avg_del / num_links)

        for i in channels:
            lost_packets_per_block += i.compute_number_of_losses_per_block()
            successfully_transmitted_packets_per_block += i.compute_number_of_successfully_transmitions_per_block()


        total_useful_packets.append(encoder.rank)
        total_lost_packets.append(lost_packets_per_block)
        if encoding == "yes":
            total_unuseful_packets.append(unuseful_packets_per_block)
        total_transmitted_packets.append(lost_packets_per_block+successfully_transmitted_packets_per_block)
        total_frames.append(block_frame)
        avg_data_rate.append(data_rate_block_numerator/block_frame)
        avg_delay.append(avg_del)
        for i in channels:
            i.clear_arrays_for_source_version()
            i.clear_arrays_for_encoding_version()


        print("---------------------------------------")
        print(f"Block {num_of_blocks} was fully decoded!!!")
        print(f"Total frames used for block {num_of_blocks} are {block_frame} frames!")
        print(f"Total transmitted packets are {total_transmitted_packets[-1]}")
        print(f"Total useful packets are {total_useful_packets[-1]}")
        print(f"Total rebroadcasts are  {total_lost_packets[-1]}")
        if encoding == "yes":
            print(f"Total unused packets are  {total_unuseful_packets[-1]}")
        print(f"Average delay = {avg_delay[-1]:.2f} frame\nThroughput = {avg_data_rate[-1]:.2f} bytes/frame")
        print("---------------------------------------\n\n")




    end = time.time()

    print("#####-----Statistics-----#####")
    print(f"Total elapsed time: \t\t{end-start} sec\n")
    print(f"Blocks which were fully decoded are {num_of_blocks}.\nTotal frames  used  {compute_total_frames(total_frames)}.\nTotal throughput = {(compute_total_successfully_transmitted_packets(channels) * symbol_bytes)/compute_total_frames(total_frames):.2f}bytes/frame"
              f"\nAverage Throughput = {compute_average_throughput(avg_data_rate):.2f}bytes/frame\nAverage delay = {compute_average_delay(avg_delay)}frame")



if __name__ == "__main__":
    main()



              



