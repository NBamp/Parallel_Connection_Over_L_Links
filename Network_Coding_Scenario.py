
from Channel import Channel
import Common_methods
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

        while not decoder.is_complete():

            for channel in channels:

                successfully_transmitted_packets, loss_packets = 0, 0  # counters for successfully transmitted and lost packets in a frame duration

                for index in range(channel.capacity):

                    if decoder.is_complete() and channel.unused_packets == -1:
                        channel.unused_packets = channel.capacity - index

                    coefficients = generator.generate()
                    symbol = encoder.encode_symbol(coefficients)

                    if random.uniform(0, 1) >= channel.loss_probability:
                        decoder.decode_symbol(symbol, bytearray(coefficients))
                        successfully_transmitted_packets += 1
                    else:
                        loss_packets += 1


                if not (successfully_transmitted_packets == 0 and loss_packets == 0) : #In case successfully_transmitted_packets == 0 and loss_packets == 0 link has nothing else to send , so there is no need for using extra frame.
                    channel.update_by_the_end_of_frame(successfully_transmitted_packets,loss_packets)

                print(f"For channel {channels.index(channel)+1} total transmitted packets = {channel.capacity} , successfully transmitted packets are = {successfully_transmitted_packets} , loss packets = {loss_packets} in block_frame {block_frame+1}")


            block_frame += 1
            print('\n\n')

        delay_per_block , successfully_transmitted_packets_per_block = 0 , 0
        lost_packets_per_block = 0

        for i in channels:
            a , b = i.compute_delay_and_successfully_transmitted_packets_per_block()
            delay_per_block , successfully_transmitted_packets_per_block = delay_per_block + a , successfully_transmitted_packets_per_block + b
            lost_packets_per_block += i.compute_number_of_losses_per_block()

        avg_delay_per_block = delay_per_block / successfully_transmitted_packets_per_block
        data_rate_per_block = (successfully_transmitted_packets_per_block * symbol_bytes) / block_frame
        unuseful_packets_per_block = Common_methods.compute_unused_packets_per_block_network_coding_version(channels)

        total_successful_packets.append(current_block_size)
        total_unuseful_packets.append(unuseful_packets_per_block)
        total_frames.append(block_frame)
        avg_data_rate.append(data_rate_per_block)
        avg_delay.append(avg_delay_per_block)

        for i in channels:
            i.reset_for_encoding_version()


        print("---------------------------------------")
        print(f"Block {num_of_blocks} was fully decoded!!!")
        print(f"Total frames used for block {num_of_blocks} are {block_frame} frames!")
        print(f"Total transmitted packets are {successfully_transmitted_packets_per_block + lost_packets_per_block}")
        print(f"Total successfully transmitted packets are {successfully_transmitted_packets_per_block}")
        print(f"Total lost packets are {lost_packets_per_block}")
        print(f"Total useful packets are {total_successful_packets[-1]}")
        print(f"Total unused packets are  {total_unuseful_packets[-1]}")
        print(f"Average delay = {avg_delay_per_block:.2f} frame\nThroughput = {data_rate_per_block:.2f} bytes/frame")
        print("---------------------------------------\n\n")


    end = time.time()

    print("#####-----Statistics-----#####")
    print(f"Total elapsed time: \t\t{end-start} sec\n")
    print(f"Blocks which were fully decoded are {num_of_blocks}.\nTotal frames  used  {Common_methods.compute_total(total_frames)}.\nTotal throughput = {(Common_methods.compute_total(total_successful_packets) * symbol_bytes)/Common_methods.compute_total(total_frames):.2f} bytes/frame"
          f"\nAverage Throughput = {Common_methods.compute_average(avg_data_rate):.2f} bytes/frame\n"
            f"Average delay = {Common_methods.compute_average(avg_delay):.2f} frame")



if __name__ == "__main__":
    main()







