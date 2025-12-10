from Channel import Channel
import Common_methods
import random
import argparse
import time

import pyerasure.block as pyblock
import pyerasure.finite_field
import pyerasure.block.generator as pygenerator



# In order to get R_i[block_frame-1]/1-P2 - capacity
def compute_fraction_lost_packets_divided_with_success_probability_compared_to_capacity(R_i , array):
    return (R_i / (1 - array[0].loss_probability)) - array[0].capacity

# In order to get R_i[block_frame-1]/1-p2
def compute_R_i_divided_with_probability_success(R_i , probability):
    return round(R_i / (1-probability))

# For source packets if element end  >= len(encoder.rank)
def  check_encoder_length(end,rank):
    if end > rank:
        end = rank
    return end



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

    channels.sort(key=lambda c: c.maximum_throughput, reverse=True) #Descending order by throughput

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
        source_packets_counter = 0
        start , end = 0,0
        R_i = [] #Lost packets per frame

        while not decoder.is_complete():

            while source_packets_counter<encoder.rank: #While source packets still exists

                successfully_transmitted_uncoded_packets, lost_uncoded_packets , successfully_transmitted_coded_packets , lost_coded_packets , lost_total_uncoded_packets_per_frame = 0 , 0 , 0 , 0 , 0

                #First case where R_i is empty or 0 , where each channel sends uncoded packets according to their capacity.
                if not R_i or R_i[block_frame-1] == 0:

                    for channel in channels:
                        end += channel.capacity
                        end = check_encoder_length(end , encoder.rank)
                        for index in range(start,end):
                            source_packets_counter += 1
                            symbol = encoder.symbol_data(index)
                            if random.uniform(0, 1) >= channel.loss_probability:
                                decoder.decode_systematic_symbol(symbol, index)
                                successfully_transmitted_uncoded_packets += 1
                            else:
                                lost_uncoded_packets +=1
                        start = end
                        lost_total_uncoded_packets_per_frame += lost_uncoded_packets

                    print(f"For block {num_of_blocks} successfully transmitted uncoded packets : {successfully_transmitted_uncoded_packets} , lost uncoded packets : {lost_uncoded_packets} in frame {block_frame+1} ")
                    R_i.append(lost_uncoded_packets)

                #Second case where R_i[block_frame -1] > 0 where coding packets starts to send
                else:

                    channels.sort(key=lambda c: c.maximum_throughput) #Ascending order by throughput

                    #Coded packets don't exceed channel's capacity
                    if compute_fraction_lost_packets_divided_with_success_probability_compared_to_capacity(R_i[block_frame-1] , channels) <  0 :


                        for channel in channels:

                            #Channel with lower throughput from which it will send coded packets
                            if channels.index(channel) == 0:

                                end += round(channel.capacity - compute_R_i_divided_with_probability_success(R_i[block_frame-1] , channel.loss_probability))
                                end = check_encoder_length(end , encoder.rank)

                                #uncoded_packets
                                for index in range(start,end):
                                    source_packets_counter += 1
                                    symbol = encoder.symbol_data(index)
                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_systematic_symbol(symbol, index)
                                        successfully_transmitted_uncoded_packets += 1
                                    else:
                                        lost_uncoded_packets += 1
                                start = end

                                #coded_packets
                                for index in range(compute_R_i_divided_with_probability_success(R_i[block_frame-1] , channel.loss_probability)):
                                    if decoder.is_complete() and channel.unused_packets == -1:
                                        channel.unused_packets = channel.capacity - index

                                    coefficients = generator.generate()
                                    symbol = encoder.encode_symbol(coefficients)

                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_symbol(symbol, bytearray(coefficients))
                                        successfully_transmitted_coded_packets += 1
                                    else:
                                        lost_coded_packets += 1
                            else:

                                #uncoded_packets
                                end +=  channel.capacity
                                end = check_encoder_length(end , encoder.rank)
                                for index in range(start,end):
                                    source_packets_counter += 1
                                    symbol = encoder.symbol_data(index)
                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_systematic_symbol(symbol, index)
                                        successfully_transmitted_uncoded_packets += 1
                                    else:
                                        lost_uncoded_packets += 1

                                #In case uncoded packets finish , channel continue sending coded packets according to its capacity
                                if end == encoder.rank and end - start != channel.capacity:
                                    for index in range(channel.capacity - (end - start)):
                                        if decoder.is_complete() and channel.unused_packets == -1:
                                            channel.unused_packets = channel.capacity - index

                                            coefficients = generator.generate()
                                            symbol = encoder.encode_symbol(coefficients)

                                            if random.uniform(0, 1) >= channel.loss_probability:
                                                decoder.decode_symbol(symbol, bytearray(coefficients))
                                                successfully_transmitted_coded_packets += 1
                                            else:
                                                lost_coded_packets += 1
                                start = end


                        print(f"For block {num_of_blocks} successfully transmitted uncoded packets : {successfully_transmitted_uncoded_packets} , lost uncoded packets : {lost_uncoded_packets} in frame {block_frame+1}\n"
                              f"successfully transmitted coded packets : {successfully_transmitted_coded_packets} , lost uncoded packets : {lost_coded_packets} in frame {block_frame+1}")
                        R_i.append(lost_uncoded_packets)


                    #Coded packets exceed channel's capacity
                    else:

                        for channel in channels:
                            if channels.index(channel) == 0:

                                #coded_packets
                                for index in range(channel.capacity):

                                    if decoder.is_complete() and channel.unused_packets == -1:
                                        channel.unused_packets = channel.capacity - index

                                    coefficients = generator.generate()
                                    symbol = encoder.encode_symbol(coefficients)

                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_symbol(symbol, bytearray(coefficients))
                                        successfully_transmitted_coded_packets += 1
                                    else:
                                        lost_coded_packets += 1

                            else:

                                end += round(channel.capacity - ((R_i[block_frame-1] - channels[0].maximum_throughput) / (1 - channel.loss_probability)))
                                end = check_encoder_length(end , encoder.rank)

                                for index in range(start,end):
                                    source_packets_counter += 1
                                    symbol = encoder.symbol_data(index)
                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_systematic_symbol(symbol, index)
                                        successfully_transmitted_uncoded_packets += 1
                                    else:
                                        lost_uncoded_packets += 1
                                start = end


                                for index in range(round((R_i[block_frame-1] - channels[0].maximum_throughput) / (1 - channel.loss_probability))):

                                    if decoder.is_complete() and channel.unused_packets == -1:
                                        channel.unused_packets = channel.capacity - index

                                    coefficients = generator.generate()
                                    symbol = encoder.encode_symbol(coefficients)

                                    if random.uniform(0, 1) >= channel.loss_probability:
                                        decoder.decode_symbol(symbol, bytearray(coefficients))
                                        successfully_transmitted_coded_packets += 1
                                    else:
                                        lost_coded_packets += 1

                                start = end

                        print(f"For block {num_of_blocks} successfully transmitted uncoded packets : {successfully_transmitted_uncoded_packets} , lost uncoded packets : {lost_uncoded_packets} in frame {block_frame+1}\n"
                              f"successfully transmitted coded packets : {successfully_transmitted_coded_packets} , lost coded packets : {lost_coded_packets} in frame {block_frame+1}")
                        R_i.append(lost_uncoded_packets)



                successfully_transmitted_packets_per_block += successfully_transmitted_coded_packets + successfully_transmitted_uncoded_packets
                lost_packets_per_block += lost_uncoded_packets + lost_coded_packets
                block_frame += 1

            successfully_transmitted_coded_packets , lost_coded_packets = 0,0
            for channel in channels:

                for index in range(channel.capacity):

                    if decoder.is_complete() and channel.unused_packets == -1:
                        channel.unused_packets = channel.capacity - index

                    coefficients = generator.generate()
                    symbol = encoder.encode_symbol(coefficients)

                    if random.uniform(0, 1) >= channel.loss_probability:
                        decoder.decode_symbol(symbol, bytearray(coefficients))
                        successfully_transmitted_coded_packets += 1
                    else:
                        lost_coded_packets += 1
            print(f"For block {num_of_blocks} successfully transmitted coded packets : {successfully_transmitted_coded_packets} , lost coded packets : {lost_coded_packets} in frame {block_frame+1} ")
            successfully_transmitted_packets_per_block += successfully_transmitted_coded_packets
            lost_packets_per_block += lost_coded_packets
            block_frame += 1

        unuseful_packets_per_block = Common_methods.compute_unused_packets_per_block_network_coding_version(channels)
        data_rate_per_block = (successfully_transmitted_packets_per_block * symbol_bytes) / block_frame


        total_unuseful_packets.append(unuseful_packets_per_block)
        total_frames.append(block_frame)
        total_successful_packets.append(successfully_transmitted_packets_per_block)
        avg_data_rate.append(data_rate_per_block)

        print("---------------------------------------")
        print(f"Block {num_of_blocks} was fully decoded!!!")
        print(f"Total frames used for block {num_of_blocks} are {block_frame} frames!")
        print(f"Total transmitted packets are {successfully_transmitted_packets_per_block + lost_packets_per_block}")
        print(f"Total successfully transmitted packets are {successfully_transmitted_packets_per_block}")
        print(f"Total lost packets are {lost_packets_per_block}")
        print(f"Total useful packets are {total_successful_packets[-1]}")
        print(f"Total unused packets are  {total_unuseful_packets[-1]}")
  #     print(f"Average delay = {avg_delay_per_block:.2f} frame\nThroughput = {data_rate_per_block:.2f} bytes/frame")
        print("---------------------------------------\n\n")




    end = time.time()

    print("#####-----Statistics-----#####")
    print(f"Total elapsed time: \t\t{end-start} sec\n")
    print(f"Blocks which were fully decoded are {num_of_blocks}.\nTotal frames  used  {Common_methods.compute_total(total_frames)}.\nTotal throughput = {(Common_methods.compute_total(total_successful_packets) * symbol_bytes)/Common_methods.compute_total(total_frames):.2f} bytes/frame"
          f"\nAverage Throughput = {Common_methods.compute_average(avg_data_rate):.2f} bytes/frame")
         # f"\nAverage delay = {compute_average_delay(avg_delay):.2f} frame")
    



if __name__ == "__main__":
    main()

