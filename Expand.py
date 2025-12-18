

from Channel import Channel
import Common_methods
import random
import argparse
import time

import pyerasure.block as pyblock
import pyerasure.finite_field
import pyerasure.block.generator as pygenerator


def compute_fraction_lost_packets_divided_with_success_probability_compared_to_capacity(R_i: int, channels: list[Channel]):
    """

    :param R_i: Value of R(i-1)
    :param channels: List where each channel is stored
    :return: Computation of (R(i-1)/1-p2) - C2 in order to check if R(i-1)/1-p2>C2 when channel2 is the one with the lowest throughput

    """

    return round((R_i / (1 - channels[-1].loss_probability)) - channels[-1].capacity)


def compute_R_i_divided_with_probability_success(R_i: int , loss_probability: int):
    """

    :param R_i: Value of R(i-1)
    :param loss_probability: Loss probability of channel2 which is the channel with the lowest throughput
    :return: Computation of the following fraction for later convenience

    """
    return round(R_i / (1-loss_probability))


def check_for_remaining_packets(end: int,rank: int):
    """

    When having source packets to transmit there is a start and an end indices according to which channel and case we are at.
    In case encoder.symbols are about to finish there is a chance in which end indice is higher than encoder.rank which means there aren't any source_packets left to transmit.
    In this situation the channel will continue sending coded packets which is the number of the below variable remaining_packets
    :param end:
    :param rank:
    :return:
    """

    remaining_packets = 0
    if end > rank:
        remaining_packets = end - rank
        end = rank
    return end,remaining_packets


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--num_symbols", help="Total number of transmitted symbols")
    parser.add_argument("--symbol_size", help="Symbol size in bytes")
    parser.add_argument("--seed", help="Seed to control randomness")
    parser.add_argument("--block_size", help="Block (generation) size")

    args = parser.parse_args()

    symbols = int(args.num_symbols)
    symbol_bytes = int(args.symbol_size)
    seed = int(args.seed)
    block_size = int(args.block_size)


    avg_data_rate = [] #Array for storing data_rate per block
    avg_delay = [] #Array for storing avg_delay per block
    total_frames = [] #Array for storing number of frames per block
    total_successful_packets = []  #Array of useful packets per block
    total_unuseful_packets = []  #Array of unuseful packets in encoding scenario
    total_lost_packets = []  #Array of lost packets per block
    successfully_transmitted_packets_per_block = 0
    lost_packets_per_block = 0

    num_links = int(input("Define the number of links for the simulation : "))

    channels = [Channel(symbol_bytes) for _ in range(num_links)]  # List containing one Channel Object for each link

    frame_size = 0

    for i in range(num_links):

        channels[i].loss_probability = (float((input(f"Enter channel {i+1} loss probability rate in range[0,1] : "))))
        channels[i].capacity = int(input(F"Enter channel {i+1}'s capacity measured in subframes : "))
        channels[i].maximum_throughput = channels[i].capacity * (1 - channels[i].loss_probability)
        frame_size += channels[i].capacity


    ########Descending order by throughput##########
    channels.sort(key=lambda c: c.maximum_throughput, reverse=True)

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
        uncoded_packets_counter = 0 #While there are uncoded_packets the algorith works as cases.When they finish each channel transmits coded packets according to its capacity until the block is decoded.
        start , end = 0,0 #Indices used when there is transmission of uncoded packets
        R_i = [] #Lost packets per frame


        print("-----------------------------------------")
        print(f"\t\tFor Block {num_of_blocks}\t\t|")
        print("-----------------------------------------")

        while not decoder.is_complete():

            #Each of these variable are computed per frame
            successfully_transmitted_uncoded_packets, lost_uncoded_packets , successfully_transmitted_coded_packets , lost_coded_packets , remaining_coded_packets , packets_per_frame = 0 , 0 , 0 , 0 , 0 ,0
            for channel in channels:

                #While uncoded packets exists
                if uncoded_packets_counter < encoder.rank:

                    #First case where R_i is empty or 0 , where each channel sends uncoded packets according to its capacity.
                    if not R_i or R_i[block_frame-1] == 0:

                        end += channel.capacity
                        end,remaining_coded_packets = check_for_remaining_packets(end , encoder.rank)

                        for index in range(start,end):
                            packets_per_frame += 1
                            uncoded_packets_counter += 1
                            symbol = encoder.symbol_data(index)
                            if random.uniform(0, 1) >= channel.loss_probability:
                                decoder.decode_systematic_symbol(symbol, index , block_frame)
                                successfully_transmitted_uncoded_packets += 1
                            else:
                                lost_uncoded_packets +=1
                        start = end

                        if remaining_coded_packets>0:
                            for index in range(remaining_coded_packets):

                                packets_per_frame += 1
                                coefficients = generator.generate()
                                symbol = encoder.encode_symbol(coefficients)
                                if random.uniform(0, 1) >= channel.loss_probability:
                                    decoder.decode_symbol(symbol, bytearray(coefficients) ,block_frame)
                                    successfully_transmitted_coded_packets += 1
                                else:
                                    lost_coded_packets += 1

                                #In the block is decoded and the loop hasn't finished the number of remaining iterations until the end indice are stored as unused_packets for channel.
                                if decoder.is_complete() and channel.unused_packets == -1:
                                    channel.unused_packets = remaining_coded_packets - (index + 1)



                        print(f"For channel {channels.index(channel)+1} transmitted {packets_per_frame} packets in frame {block_frame+1}.")
                        packets_per_frame = 0


                    #Second case where R_i[block_frame -1] > 0 where coding packets starts to send
                    else:

                        #Coded packets don't exceed channel's capacity with the lowest throughput
                        if compute_fraction_lost_packets_divided_with_success_probability_compared_to_capacity(R_i[block_frame-1] , channels) <  0 :

                            #Channel with maximum throughput from which uncoded_packets according to its capacity will pass
                            if channels.index(channel) == 0:

                                #Uncoded_packets in this case are equal to channel's capacity
                                end +=  channel.capacity
                                end,remaining_coded_packets = check_for_remaining_packets(end , encoder.rank)

                                for index in range(start,end):
                                    packets_per_frame += 1
                                    uncoded_packets_counter += 1
                                    symbol = encoder.symbol_data(index)
                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_systematic_symbol(symbol, index , block_frame)
                                        successfully_transmitted_uncoded_packets += 1
                                    else:
                                        lost_uncoded_packets += 1
                                start = end

                                
                                for index in range(remaining_coded_packets):

                                    packets_per_frame += 1
                                    coefficients = generator.generate()
                                    symbol = encoder.encode_symbol(coefficients)

                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_symbol(symbol, bytearray(coefficients) ,block_frame)
                                        successfully_transmitted_coded_packets += 1
                                    else:
                                        lost_coded_packets += 1

                                    #In the block is decoded and the loop hasn't finished the number of remaining iterations until the end indice are stored as unused_packets for channel.
                                    if decoder.is_complete() and channel.unused_packets == -1:
                                        channel.unused_packets = remaining_coded_packets - (index + 1)

                                print(f"For channel {channels.index(channel)+1} transmitted {packets_per_frame} packets in frame {block_frame+1}")
                                packets_per_frame = 0

                            #Channel with minimum throughput from which uncoded and coded packets will pass
                            else:

                                #Uncoded packets in this case are C2 - (R(i-1)/1-p2 ) or absolute value of already computed (R(i-1)/1-p2)-C2 with the below function
                                end += abs(compute_fraction_lost_packets_divided_with_success_probability_compared_to_capacity(R_i[block_frame-1] , channels))
                                end,remaining_coded_packets = check_for_remaining_packets(end , encoder.rank)


                                for index in range(start,end):
                                    packets_per_frame += 1
                                    uncoded_packets_counter += 1
                                    symbol = encoder.symbol_data(index)
                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_systematic_symbol(symbol, index , block_frame)
                                        successfully_transmitted_uncoded_packets += 1
                                    else:
                                        lost_uncoded_packets += 1

                                start = end

                                #Coded_packets in this case are (R(i-1)/1-p2) + remaining_coded_packets if there are any
                                for index in range(compute_R_i_divided_with_probability_success(R_i[block_frame-1] , channel.loss_probability) + remaining_coded_packets ):

                                    packets_per_frame += 1
                                    coefficients = generator.generate()
                                    symbol = encoder.encode_symbol(coefficients)

                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_symbol(symbol, bytearray(coefficients) , block_frame)
                                        successfully_transmitted_coded_packets += 1
                                    else:
                                        lost_coded_packets += 1

                                    if decoder.is_complete() and channel.unused_packets == -1:
                                        channel.unused_packets = (compute_R_i_divided_with_probability_success(R_i[block_frame-1] , channel.loss_probability) + remaining_coded_packets) - (index+1)

                                print(f"For channel {channels.index(channel)+1} transmitted {packets_per_frame} packets in frame {block_frame+1}")
                                packets_per_frame = 0

                        #Coded packets exceed channel's capacity with minimum throughput
                        else:

                            if channels.index(channel) == 0:

                                #Uncoded packets in this case are C1 - (R(i-1) - C2*(1-p2) / 1-p1)
                                end += round(channel.capacity - ((R_i[block_frame-1] - channels[-1].maximum_throughput) / (1 - channel.loss_probability)))
                                end,remaining_coded_packets = check_for_remaining_packets(end , encoder.rank)

                                for index in range(start,end):
                                    packets_per_frame += 1
                                    uncoded_packets_counter += 1
                                    symbol = encoder.symbol_data(index)
                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_systematic_symbol(symbol, index ,block_frame)
                                        successfully_transmitted_uncoded_packets += 1
                                    else:
                                        lost_uncoded_packets += 1

                                start = end


                                #Coded packets in this case (R(i-1) - C2*(1-p2)) / 1-p1 + remaining_coded_packets if there are any
                                for index in range(round((R_i[block_frame-1] - channels[-1].maximum_throughput) / (1 - channel.loss_probability)) + remaining_coded_packets):
                                    packets_per_frame += 1

                                    coefficients = generator.generate()
                                    symbol = encoder.encode_symbol(coefficients)

                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_symbol(symbol, bytearray(coefficients) ,block_frame)
                                       # print(decoder._coefficients)
                                        successfully_transmitted_coded_packets += 1
                                    else:
                                        lost_coded_packets += 1

                                    if decoder.is_complete() and channel.unused_packets == -1:
                                        channel.unused_packets = (round((R_i[block_frame-1] - channels[-1].maximum_throughput) / (1 - channel.loss_probability)) + remaining_coded_packets ) - (index+1)

                                print(f"For channel {channels.index(channel)+1} transmitted {packets_per_frame} packets in frame {block_frame+1}")
                                packets_per_frame = 0

                            else:

                                #Coded_packets in this case are equal to channel;s capacity
                                for index in range(channel.capacity):
                                    packets_per_frame += 1

                                    coefficients = generator.generate()
                                    symbol = encoder.encode_symbol(coefficients)

                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_symbol(symbol, bytearray(coefficients) ,block_frame)
                                        successfully_transmitted_coded_packets += 1
                                    else:
                                        lost_coded_packets += 1

                                    if decoder.is_complete() and channel.unused_packets == -1:
                                        channel.unused_packets = channel.capacity - (index + 1)

                                print(f"For channel {channels.index(channel)+1} transmitted {packets_per_frame} packets in frame {block_frame+1}")
                                packets_per_frame = 0

                #Uncoded packets have finished  , so each channel send coded packets according to its capacity
                else:

                    for index in range(channel.capacity):
                        packets_per_frame += 1

                        coefficients = generator.generate()
                        symbol = encoder.encode_symbol(coefficients)

                        if random.uniform(0, 1) >= channel.loss_probability:
                            decoder.decode_symbol(symbol, bytearray(coefficients) ,block_frame)
                            successfully_transmitted_coded_packets += 1
                        else:
                            lost_coded_packets += 1

                        if decoder.is_complete() and channel.unused_packets == -1:
                            channel.unused_packets = channel.capacity - (index+1)


                    print(f"For channel {channels.index(channel)+1} transmitted {packets_per_frame} packets in frame {block_frame+1}")
                    packets_per_frame = 0


            print(f"End of Frame {block_frame+1}!")
            print(f"\tsuccessfully transmitted uncoded packets : {successfully_transmitted_uncoded_packets} , lost uncoded packets : {lost_uncoded_packets}\n\t"
                  f"successfully transmitted coded packets : {successfully_transmitted_coded_packets} , lost coded packets : {lost_coded_packets}\n")


            R_i.append(lost_uncoded_packets)
            successfully_transmitted_packets_per_block += successfully_transmitted_coded_packets + successfully_transmitted_uncoded_packets
            lost_packets_per_block += lost_uncoded_packets + lost_coded_packets
            block_frame += 1



        total_unuseful_packets.append(Common_methods.compute_unused_packets_per_block_network_coding_version(channels))
        total_frames.append(block_frame)
        total_successful_packets.append(successfully_transmitted_packets_per_block)
        total_lost_packets.append(lost_packets_per_block)
        avg_data_rate.append((successfully_transmitted_packets_per_block * symbol_bytes) / block_frame)
        avg_delay.append(decoder.sum_of_delay)

        print("-----------------------------------------")
        print(f"Block {num_of_blocks} was fully decoded!!!")
        print(f"Total frames used for block {num_of_blocks} are {block_frame} frames!")
        print(f"Total transmitted packets are {successfully_transmitted_packets_per_block + lost_packets_per_block}")
        print(f"Total successfully transmitted packets are {successfully_transmitted_packets_per_block}")
        print(f"Total lost packets are {total_lost_packets[-1]}")
        print(f"Total useful packets are {total_successful_packets[-1]}")
        print(f"Total unused packets are  {total_unuseful_packets[-1]}")
        print(f"Average delay = {avg_delay[-1]:.2f} frame\n")
        print(f"Average data rate per block = {avg_data_rate[-1]:.2f} bytes/frame")
        print("-----------------------------------------\n\n")

        successfully_transmitted_packets_per_block , lost_packets_per_block = 0,0


    end = time.time()

    print("#####-----Statistics-----#####")
    print(f"Total elapsed time: \t\t{end-start} sec\n")
    print(f"Blocks which were fully decoded are {num_of_blocks}.\nTotal frames  used  {Common_methods.compute_total(total_frames)}.\nTotal throughput = {(Common_methods.compute_total(total_successful_packets) * symbol_bytes)/Common_methods.compute_total(total_frames):.2f} bytes/frame"
          f"\nAverage Throughput = {Common_methods.compute_average(avg_data_rate):.2f} bytes/frame")

    



if __name__ == "__main__":
    main()




