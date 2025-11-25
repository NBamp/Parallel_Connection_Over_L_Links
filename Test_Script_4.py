class Channel:

    def __init__(self,symbol_size):

        self._frame_size = 0
        self._symbol_size = symbol_size
        self._capacity = 2  # Assume each link start with this value before defining correlation
        self._assigned_packets = 0  # how many assigned packets scheduled in this link for scenario with encoding
        self._frames = 0  # Number of frames link has covered
        self._channel_transmitted_dict = {}  # Dictionary with pair {frame_number:[transmitted_packets,loss_packets] , one pair for each frame used by the link and clear dictionary after block is fully decoded
        self.avg_delay_per_block = 0 #Average delay packet per link computed after block if fully decoded (In equation only delayed packets are computed)
        self.avg_delay = [] #Use for storing average delay for each block in order to make an average in the end
        self.data_rate_per_block = 0 #Data rate computed for each block after it is fully decoded
        self.data_rate = [] #Use for storing data rate for each block in order to make an average in the end
        self.loss_probability = 0 #Loss probability per link given by the user
        self.total_successfully_transmitted_packets = 0
        self.total_loss_packets = 0
        self.total_transmitted_packets = 0

        #Metrics for scenario with source packets
        self.packet_arrived_and_decoded_frame_dict = {} # Pair with index of encoder_symbol : [frame_arrived,frame_decoded]
        self.lost_packets_index = []



    @property
    def frames(self):
        return self._frames

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


    def update_by_the_end_of_frame(self, trans, loss):

        self._frames += 1
        self._channel_transmitted_dict[self._frames] = [trans,loss]
        self.total_successfully_transmitted_packets += trans
        self.total_loss_packets += loss
        self.total_transmitted_packets += trans + loss


    #After block is decoded , channel_transmitted dictionary clears .
    def clear_transmitted_channel(self):
        self._channel_transmitted_dict.clear()

    #After block is decoded , packet_arrived_and_decoded_frame_dict clears .
    def clear_packet_arrived_and_decoded(self):
        self.packet_arrived_and_decoded_frame_dict.clear()

    #Computing data_rate and avg_delay_per_packet in scenario with source packets per block
    def avg_delay_and_data_rate_per_block_compute_source_version(self):

        delay = 0

        for i in self.packet_arrived_and_decoded_frame_dict:

            delay += self.packet_arrived_and_decoded_frame_dict[i][1] - self.packet_arrived_and_decoded_frame_dict[i][0]

        self.avg_delay_per_block = delay/len(self.packet_arrived_and_decoded_frame_dict)
        self.data_rate_per_block = (len(self.packet_arrived_and_decoded_frame_dict) * self._symbol_size)/ (self.frame_size * self.frames)

        self.data_rate.append(self.data_rate_per_block)
        self.avg_delay.append(self.avg_delay_per_block)


    #Computing data_rate and avg_delay_per_packet in scenario with coding packets per block
    def avg_delay_and_data_rate_per_block_compute(self):

        delay = 0
        successfully_transmitted_packets_per_block = 0

        for i in self._channel_transmitted_dict:
            successfully_transmitted_packets_per_block += self._channel_transmitted_dict[i][0]
            delay += (self._channel_transmitted_dict[i][0]) * (self._frames - i)

        self.avg_delay_per_block = delay / successfully_transmitted_packets_per_block
        self.data_rate_per_block = (successfully_transmitted_packets_per_block * self._symbol_size)/ (self.frame_size * self.frames)

        self.avg_delay.append(self.avg_delay_per_block)
        self.data_rate.append(self.data_rate_per_block)


    def avg_delay_compute(self):

        delay = 0
        for i in self.avg_delay:
            delay += i
        return delay/len(self.avg_delay)

    def avg_data_rate_compute(self):

        throughput = 0
        for i in self.data_rate:
            throughput += i
        return throughput/len(self.data_rate)



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
    parser.add_argument("--encoding", help="Whether there is encoding or not,type Yes for encoding,No otherwise")

    print("Reminder , for testing scenario with source packets select a much larger block_size compared to frame_size.")


    args = parser.parse_args()

    symbols = int(args.num_symbols)
    symbol_bytes = int(args.symbol_size)
    seed = int(args.seed)
    block_size = int(args.block_size)
    encoding = args.encoding.lower()

    num_links = int(input("Define the number of links for the simulation : "))

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
        i.assigned_packets = frame_size
        print(f"For channel {channels.index(i) + 1} capacity of subframes = {i.capacity}")


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
        source_counter_end = frame_size
        added_packets = [] ##List with newly added packets

        while not decoder.is_complete():

            for channel in channels:

                successfully_transmitted_packets, loss_packets = 0, 0  # counters for successfully transmitted and lost packets in a frame duration

                #Scenario with encoding follows
                if encoding == "yes":

                    for index in range(channel.assigned_packets):
                        coefficients = generator.generate()
                        symbol = encoder.encode_symbol(coefficients)
                        if random.uniform(0, 1) >= channel.loss_probability:
                            decoder.decode_symbol(symbol, bytearray(coefficients))
                            successfully_transmitted_packets += 1
                        else:
                            loss_packets += 1
                    channel.update_by_the_end_of_frame(successfully_transmitted_packets , loss_packets)

                #Scenario with sending source packets
                else:

                    #In order to resend the lost packets of each link
                    if  channel.lost_packets_index:
                        source_counter_end = frame_size - len(channel.lost_packets_index) #In order to assign each time number of packets ==  frame_size in each link


                        for index in channel.lost_packets_index[:]:
                            symbol = encoder.symbol_data(index)
                            if random.uniform(0, 1) >= channel.loss_probability:
                                decoder.decode_systematic_symbol(symbol, index)
                                channel.packet_arrived_and_decoded_frame_dict[index][1] = channel.frames  #Add frame in which symbol  decoded
                                successfully_transmitted_packets += 1
                                channel.lost_packets_index.remove(index)  #Lost packet doesnt exist anymore
                                print(f"Packet {index} which was lost , transmitted successfully.")
                            else:
                                loss_packets +=1


                    starting_list = list(channel.packet_arrived_and_decoded_frame_dict)  #In order to show afterward newly added packets for each link


                    for index in list(d_encoder_symbols_data.keys())[source_counter_start:source_counter_end]:

                        symbol = d_encoder_symbols_data[index]

                        if index not in channel.packet_arrived_and_decoded_frame_dict.keys():
                            channel.packet_arrived_and_decoded_frame_dict[index] = [channel.frames,0]  #Add frame in which symbol arrived

                        if random.uniform(0, 1) >= channel.loss_probability:
                            decoder.decode_systematic_symbol(symbol, index)
                            channel.packet_arrived_and_decoded_frame_dict[index][1] = channel.frames  #Add frame in which symbol  decoded
                            successfully_transmitted_packets += 1
                        else:
                            channel.lost_packets_index.append(index)
                            loss_packets +=1

                        d_encoder_symbols_data.pop(index)


                    ending_list = list(channel.packet_arrived_and_decoded_frame_dict)  #In order to show afterward newly added packets for each link

                    if  starting_list:
                        added_packets = [x for x in ending_list if x not in starting_list]

                    channel.update_by_the_end_of_frame(successfully_transmitted_packets,loss_packets)

                print(f"For channel {channels.index(channel)+1} total transmitted packets = {frame_size} , successfully transmitted packets are = {successfully_transmitted_packets} , loss packets = {loss_packets} in block_frame {channel.frames}")
                if encoding == "no":
                    print(f"Lost packets = {channel.lost_packets_index}.")
                    print(f"New packets added =  {added_packets}.")
                    print("---------------------------------------")


            block_frame += 1
            print("---------------------------------------\n")
            print('\n\n')



        for i in channels:

            if encoding == "yes":
                i.avg_delay_and_data_rate_per_block_compute()
                i.clear_transmitted_channel()
            else:
                i.avg_delay_and_data_rate_per_block_compute_source_version()
                i.clear_packet_arrived_and_decoded()

            print(f"For channel_{channels.index(i)+1} in block_frame {num_of_blocks}\nAverage delay = {i.avg_delay_per_block:.2f} sec\nDate rate = {i.data_rate_per_block} bytes/frame")


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
              f"\nTotal lost packets = {i.total_loss_packets}\nFinal average delay = {i.avg_delay_compute():.2f} sec\nFinal data rate = {i.avg_data_rate_compute()} bytes/frame\n\n")

if __name__ == "__main__":
    main()
