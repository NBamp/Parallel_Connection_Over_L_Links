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
        retransmission_per_block = 0
        start , end = 0,0

        while not decoder.is_complete():

            for channel in channels:

                successfully_transmitted_packets_per_channel, loss_packets_per_channel = 0, 0  # counters for successfully transmitted and lost packets in a frame duration
                packet_counter = 0
                retransmission_counter = 0

                if channel.lost_packets:

                    for  index in channel.lost_packets:
                        retransmission_counter += 1
                        packet_counter += 1
                        symbol = encoder.symbol_data(index)
                        if random.uniform(0, 1) >= channel.loss_rate:
                            decoder.decode_systematic_symbol(symbol, index)
                            successfully_transmitted_packets_per_channel += 1
                            channel.lost_packets.remove(index)  #Lost packet doesnt exist anymore
                            print(f"Packet {index} which was arrived in block_frame {decoder.packet_delays[index]} , transmitted successfully in block_frame {block_frame+1} ")
                        else:
                            loss_packets_per_channel +=1

                end += channel.bandwidth - packet_counter

                if end > encoder.rank:
                    end = encoder.rank

                if start < encoder.rank:

                    for index in range(start , end):
                        packet_counter += 1
                        symbol = encoder.symbol_data(index)
                        decoder.update_packet_delay(index,"S")  #Time arriving Source Packets
                        if random.uniform(0, 1) >= channel.loss_rate:
                            decoder.decode_systematic_symbol(symbol, index)
                            successfully_transmitted_packets_per_channel += 1
                        else:
                            channel.lost_packets.append(index)

                            loss_packets_per_channel +=1
                    start = end


                successfully_transmitted_packets_per_block += successfully_transmitted_packets_per_channel
                loss_packets_per_block += loss_packets_per_channel

                print(f"\tFor channel {channels.index(channel)+1}\n"
                      f"Total Transmitted Packets  = {successfully_transmitted_packets_per_channel+loss_packets_per_channel}\n"
                      f"Successfully Transmitted Packets  = {successfully_transmitted_packets_per_channel}\n"
                      f"Loss Packets = {loss_packets_per_channel}\n"
                      f"Retransmission Attemps = {retransmission_counter}\n"
                      f"Block_frame = {block_frame+1}\n")

                retransmission_per_block += retransmission_counter


            decoder.update_current_timeslot()
            block_frame += 1
            print('\n\n')

        delay_per_block = decoder.counter_packet_delay_with_source_sceneario()
        data_rate_per_block = (successfully_transmitted_packets_per_block * arguments['symbol_bytes']) / block_frame

        statistics['total_successful_packets'].append(successfully_transmitted_packets_per_block)
        statistics['total_lost_packets'].append(loss_packets_per_block)
        statistics['total_frames'].append(block_frame)
        statistics['data_rate'].append(data_rate_per_block)
        statistics['avg_delay'].append(delay_per_block)


        print("---------------------------------------")
        print(f"Block {num_of_blocks} was fully decoded!!!")
        print(f"Total frames used for block {num_of_blocks} are {block_frame} frames!")
        print(f"Total transmitted packets are {successfully_transmitted_packets_per_block + loss_packets_per_block}!")
        print(f"Total successfully transmitted packets are {successfully_transmitted_packets_per_block}!")
        print(f"Total lost packets are {loss_packets_per_block}!")
        print(f"Total useful packets are {statistics['total_successful_packets'][-1]}!")
        print(f"Average delay = {delay_per_block:.2f} frame\nThroughput = {data_rate_per_block:.2f} bytes/frame!")
        print("---------------------------------------\n\n")


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







