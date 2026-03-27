
import Simulation
import Common_methods
import random

import time

import pyerasure.finite_field
import pyerasure.block.generator as pygenerator


#Function which returns number of coded and uncoded in each case
def computing_condition(innovative: int,throughput: int , min_throughput: int,capacity: int,loss_probability: float):

    #Represents (Xi - (1-p2)*C2) assuming Channel 2 has minimum throughput
    result = innovative - min_throughput

    if throughput == min_throughput:
        if result < 0:
            return capacity - (innovative/(1-loss_probability)) , innovative/(1-loss_probability)
        else:
            return 0 , capacity
    else:
        if result <= 0:
            return capacity , 0
        else:
            return capacity - (result / (1-loss_probability)), (result / (1-loss_probability))

def main():

    arguments = Simulation.parse_simulation_args()
    statistics = Simulation.initialize_simulation_state()
    channels , frame_size = Simulation.setup_channels(arguments['symbol_bytes'])

    channels.sort(key=lambda c:c.throughput , reverse=True)
    min_throughput =  channels[-1].throughput

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
        start , end = 0,0 #Indices used when there is transmission of uncoded packets

        packets_generator_based_on_encoder = 0
        innovative_per_frame = []

        while not decoder.is_complete():


            for channel in channels:

                successfully_transmitted_uncoded_packets, lost_uncoded_packets , successfully_transmitted_coded_packets , lost_coded_packets , remaining_coded_packets , packets_per_frame = 0 , 0 , 0 , 0 , 0 ,0
                uncoded_packets_based_on_algorithm , coded_packets_based_on_algorithm = 0,0
                extra_coded_packets = 0

                if not innovative_per_frame:
                    end += channel.bandwidth
                elif innovative_per_frame[-1] == 0:
                    if end < encoder.symbols:
                        end += channel.bandwidth
                    else:
                        extra_coded_packets = channel.bandwidth
                else:
                    uncoded_packets_based_on_algorithm , coded_packets_based_on_algorithm = (round(num) for num in
                            computing_condition(innovative_per_frame[-1],channel.throughput, min_throughput , channel.bandwidth, channel.loss_rate))

                    uncoded_packets_based_on_algorithm = max(0, min(uncoded_packets_based_on_algorithm, channel.bandwidth))
                    coded_packets_based_on_algorithm   = max(0, min(coded_packets_based_on_algorithm,   channel.bandwidth))

                    assert uncoded_packets_based_on_algorithm + coded_packets_based_on_algorithm == channel.bandwidth
                    end += uncoded_packets_based_on_algorithm

                if end > encoder.rank:
                    extra_coded_packets = end - encoder.rank
                    end = encoder.rank

                for source in range(start, end):

                    symbol = encoder.symbol_data(source)
                    decoder.update_packet_delay(source,"S")

                    if packets_generator_based_on_encoder < encoder.symbols:
                        packets_generator_based_on_encoder += 1

                    if random.uniform(0, 1) >= channel.loss_rate:
                        decoder.decode_systematic_symbol(symbol, source)
                        successfully_transmitted_uncoded_packets += 1
                    else:
                        lost_uncoded_packets +=1

                start = end

                for index in range(coded_packets_based_on_algorithm + extra_coded_packets):

                    coefficients = generator.generate_partial(packets_generator_based_on_encoder)
                    while len(coefficients) < decoder.symbols:
                        coefficients += bytes(1)

                    symbol = encoder.encode_symbol(coefficients)

                    if decoder.is_complete() and channel.unused_packets == -1:
                        channel.unused_packets = channel.bandwidth - index

                    if random.uniform(0, 1) >= channel.loss_rate:
                        decoder.decode_symbol(symbol, bytearray(coefficients))
                        successfully_transmitted_coded_packets += 1
                    else:
                        lost_coded_packets += 1

                successfully_transmitted_packets_per_channel = successfully_transmitted_uncoded_packets + successfully_transmitted_coded_packets
                loss_packets_per_channel = lost_uncoded_packets + lost_coded_packets

                successfully_transmitted_packets_per_block +=  successfully_transmitted_packets_per_channel
                loss_packets_per_block += loss_packets_per_channel

                assert  (successfully_transmitted_packets_per_channel + loss_packets_per_channel) == channel.bandwidth

                print(f"\tFor channel {channels.index(channel)+1}\n"
                      f"Total Transmitted Packets  = {successfully_transmitted_packets_per_channel+loss_packets_per_channel}\n"
                      f"Successfully Transmitted Packets  = {successfully_transmitted_packets_per_channel}\n"
                      f"Successfully Transmitted Uncoded Packets = {successfully_transmitted_uncoded_packets}\n"
                      f"Successfully Transmitted Coded Packets = {successfully_transmitted_coded_packets}\n"
                      f"Loss Packets = {loss_packets_per_channel}\n"
                      f"Lost Uncoded Packets = {lost_uncoded_packets}\n"
                      f"Lost Coded Packets  = {lost_coded_packets}\n"
                      f"Block_frame = {block_frame+1}\n")


            #This ensures that in this block_frame Encoder have sent at least one Source packet otherwise there are only coded packets and there is no reason for computing innovative packets.
            if decoder.packet_delays[decoder.last_source_received_id][0] == block_frame:
                innovative_per_frame.append(decoder.last_source_received_id + 1 - decoder.rank)
                #As far for +1 , if the last Source packet which was sent has id = 9 for example , Encoder has sent 10 packets , so expected rank supposed to be 10 equals  last_source_received_id + 1
            else:
                innovative_per_frame.append(0)

            block_frame += 1
            decoder.update_current_timeslot()

            print('\n\n')

        delay_per_block = decoder.counter_packet_delay_with_source_sceneario()
        data_rate_per_block = (successfully_transmitted_packets_per_block * arguments['symbol_bytes']) / block_frame
        unused_packets_per_block = Common_methods.compute_unused_packets_per_block_network_coding_version(channels)

        statistics['total_successful_packets'].append(successfully_transmitted_packets_per_block)
        statistics['total_lost_packets'].append(loss_packets_per_block)
        statistics['total_unused_packets'].append(unused_packets_per_block)
        statistics['total_frames'].append(block_frame)
        statistics['data_rate'].append(data_rate_per_block)
        statistics['avg_delay'].append(delay_per_block)


        print("---------------------------------------")
        print(f"Block {num_of_blocks} was fully decoded!!!")
        print(f"Total frames used for block {num_of_blocks} are {block_frame} !")
        print(f"Total transmitted packets are {successfully_transmitted_packets_per_block + loss_packets_per_block}!")
        print(f"Total successfully transmitted packets are {successfully_transmitted_packets_per_block}!")
        print(f"Total lost packets are {loss_packets_per_block}!")
        print(f"Total useful packets are {decoder.rank}!")
        print(f"Total unused packets are  {statistics['total_unused_packets'][-1]}!")
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




