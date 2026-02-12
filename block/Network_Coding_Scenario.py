import Simulation
import Common_methods
import random

import time

import pyerasure.finite_field
import pyerasure.block.generator as pygenerator


def main():

    arguments = Simulation.parse_simulation_args()
    statistics = Simulation.initialize_simulation_state()
    channels , frame_size = Simulation.setup_channels(arguments['symbol_bytes'])


    print(f"Total frame_size = {frame_size}")
    print(f"PyErasure Simulation\n---------------------------------------\n\n")

    # Pick the finite field to use for the encoding and decoding.
    field = pyerasure.finite_field.Binary8()

    # Allocate some data to encode - fill data_in with random data
    random.seed(arguments['seed'])
    data_in = bytearray(random.getrandbits(8) for _ in range(arguments['symbols'] * arguments['symbol_bytes']))

    offset = 0
    is_seed_set = False  # to tune generator's seed

    num_of_blocks = 0

    start = time.time()

    while True:

        offset , encoder , decoder = Simulation.setup_block(arguments, offset, field, data_in)
        print(encoder.rank)

        if offset >= len(data_in):
            break

        # Create  generator. The generator must similarly be created
        # based on the encoder/decoder.
        generator = pygenerator.RandomUniform(field, encoder.symbols)
        if not is_seed_set:
            generator.set_seed(arguments['seed'])
            is_seed_set = True


        num_of_blocks += 1
        block_frame = 0  # In order to get how many frames spent for each block

        successfully_transmitted_packets_per_block, loss_packets_per_block = 0, 0  # counters for successfully transmitted and lost packets in a block

        while not decoder.is_complete():

            packet_counter = 0
            for channel in channels:

                successfully_transmitted_packets_per_channel, loss_packets_per_channel = 0, 0  # counters for successfully transmitted and lost packets in a frame duration

                for index in range(channel.capacity):

                    packet_counter += 1

                    if decoder.is_complete() and channel.unused_packets == -1:
                        channel.unused_packets = channel.capacity - index

                    coefficients = generator.generate()
                    symbol = encoder.encode_symbol(coefficients)

                    if random.uniform(0, 1) >= channel.loss_probability:
                        decoder.decode_symbol(symbol, bytearray(coefficients))
                        successfully_transmitted_packets_per_channel += 1
                    else:
                        loss_packets_per_channel += 1

                successfully_transmitted_packets_per_block += successfully_transmitted_packets_per_channel
                loss_packets_per_block += loss_packets_per_channel

                print(f"\tFor channel {channels.index(channel)+1}\n"
                      f"Total Transmitted Packets  = {successfully_transmitted_packets_per_channel+loss_packets_per_channel}\n"
                      f"Successfully Transmitted Packets  = {successfully_transmitted_packets_per_channel}\n"
                      f"Loss Packets = {loss_packets_per_channel}\n"
                      f"Block_frames = {block_frame+1}\n")

            decoder.update_current_timeslot()
            assert packet_counter == frame_size

            block_frame += 1
            print('\n\n')


        delay_per_block  = decoder.counter_packet_delay()

        data_rate_per_block = (successfully_transmitted_packets_per_block * arguments['symbol_bytes']) / block_frame
        unuseful_packets_per_block = Common_methods.compute_unused_packets_per_block_network_coding_version(channels)

        statistics['total_successful_packets'].append(successfully_transmitted_packets_per_block)
        statistics['total_lost_packets'].append(loss_packets_per_block)
        statistics['total_unuseful_packets'].append(unuseful_packets_per_block)
        statistics['total_frames'].append(block_frame)
        statistics['data_rate'].append(data_rate_per_block)
        statistics['avg_delay'].append(delay_per_block)


        for channel in channels:
            channel.unused_packets = -1


        print("---------------------------------------")
        print(f"Block {num_of_blocks} was fully decoded!!!")
        print(f"Total frames used for block {num_of_blocks} are {block_frame} frames!")
        print(f"Total transmitted packets are {successfully_transmitted_packets_per_block + loss_packets_per_block}!")
        print(f"Total successfully transmitted packets are {successfully_transmitted_packets_per_block}!")
        print(f"Total lost packets are {loss_packets_per_block}!")
        print(f"Total useful packets are {decoder.rank}!")
        print(f"Total unused packets are  {statistics['total_unuseful_packets'][-1]}!")
        print(f"Average delay = {delay_per_block:.2f} frame\nThroughput = {data_rate_per_block:.2f} bytes/frame!")
        print("---------------------------------------\n\n")

        exit()



    end = time.time()

    print("#####-----Statistics-----#####")
    print(f"Total elapsed time: {end - start:.2f} sec\n")

    total_frames = Common_methods.compute_total(statistics['total_frames'])
    total_packets = Common_methods.compute_total(statistics['total_successful_packets'])
    total_throughput = (total_packets * arguments['symbol_bytes']) / total_frames
    avg_throughput = Common_methods.compute_average(statistics['data_rate'])
    avg_delay = Common_methods.compute_average(statistics['avg_delay'])

    print(f"Blocks fully decoded: {num_of_blocks}!")
    print(f"Total frames used: {total_frames}!")
    print(f"Total throughput: {total_throughput:.2f} bytes/frame!")
    print(f"Average throughput: {avg_throughput:.2f} bytes/frame!")
    print(f"Average delay: {avg_delay:.2f} frames!")


if __name__ == "__main__":
    main()







