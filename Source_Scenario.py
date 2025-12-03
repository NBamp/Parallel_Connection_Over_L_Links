
from Channel import Channel
import random
import argparse
import time

import pyerasure.block as pyblock
import pyerasure.finite_field
import pyerasure.block.generator as pygenerator



def compute_total_frames(array):
    frames = 0
    for i in array:
        frames += i
    return frames

def compute_total_transmitted_packets(array):
    packets = 0
    for i in array:
        packets += i
    return packets

def compute_total_lost_packets(array):
    lost = 0
    for i in array:
       lost += i
    return lost

def compute_average_delay(array):
    delay = 0
    for i in array:
        delay += i
    return delay/len(array)



def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--num_symbols", help="Total number of transmitted symbols")
    parser.add_argument("--symbol_size", help="Symbol size in bytes")
    parser.add_argument("--seed", help="Seed to control randomness")
    parser.add_argument("--block_size", help="Block (generation) size")

    print("Reminder , for testing scenario with source packets select a much larger block_size compared to frame_size.")

    args = parser.parse_args()

    symbols = int(args.num_symbols)
    symbol_bytes = int(args.symbol_size)
    seed = int(args.seed)
    block_size = int(args.block_size)



    avg_delay = [] #Array for storing avg_delay per block
    total_frames = [] #Array for storing number of frames per block
    total_transmitted_packets = [] #Array for storing total transmitted packets per block
    total_useful_packets = []  #Array of useful packets per block
    total_lost_packets = []  #Array of lost packets per block



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
                        print(f"Packet {index} which was arrived in block_frame {packet_arrived_and_decoded_frame_dict[index][0]} , transmitted successfully in block_frame {packet_arrived_and_decoded_frame_dict[index][1]} ")
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


                print(f"For channel {channels.index(channel)+1} total transmitted packets = {len(channel.transmitted_packets)} , successfully transmitted packets are = {successfully_transmitted_packets} , loss packets = {loss_packets} in block_frame {block_frame+1}")
                print(f"Transmitted packets = {channel.transmitted_packets}")
                print(f"Lost packets = {channel.lost_packets}")
                print(f"New packets added =  {channel.added_packets[-1]}")
                print("---------------------------------------\n")



            block_frame += 1
            print('\n\n')


        avg_delay_per_block = 0
        lost_packets_per_block = 0


        past_delay = 0
        for i in packet_arrived_and_decoded_frame_dict:
            delay = max(past_delay , packet_arrived_and_decoded_frame_dict[i][1] - packet_arrived_and_decoded_frame_dict[i][0])
            avg_delay_per_block += delay
            past_delay = delay


        avg_delay_per_block = avg_delay_per_block / len(packet_arrived_and_decoded_frame_dict)

        for i in channels:
            lost_packets_per_block += i.compute_number_of_losses_per_block()

        total_useful_packets.append(current_block_size)
        total_lost_packets.append(lost_packets_per_block)
        total_transmitted_packets.append(lost_packets_per_block+current_block_size)
        total_frames.append(block_frame)
        avg_delay.append(avg_delay_per_block)

        for i in channels:
            i.reset_for_encoding_version()


        print("---------------------------------------")
        print(f"Block {num_of_blocks} was fully decoded!!!")
        print(f"Total frames used for block {num_of_blocks} are {block_frame} frames!")
        print(f"Total transmitted packets are {total_transmitted_packets[-1]}")
        print(f"Total useful packets are {total_useful_packets[-1]}")
        print(f"Total rebroadcasts are {lost_packets_per_block}")
        print(f"Average delay = {avg_delay[-1]:.2f} frame\n")
        for i in packet_arrived_and_decoded_frame_dict:
            if (packet_arrived_and_decoded_frame_dict[i][1] - packet_arrived_and_decoded_frame_dict[i][0])>0:
                print(f"Symbol {i} retransmitted {packet_arrived_and_decoded_frame_dict[i][1] - packet_arrived_and_decoded_frame_dict[i][0]} times.")
        print("---------------------------------------\n\n")



    end = time.time()

    print("#####-----Statistics-----#####")
    print(f"Total elapsed time: \t\t{end-start} sec\n")
    print(f"Blocks which were fully decoded are {num_of_blocks}.\nTotal frames  used  {compute_total_frames(total_frames)}.\nAverage delay = {compute_average_delay(avg_delay):.2f} frame\n"
          f"From total {compute_total_transmitted_packets(total_transmitted_packets)} transmitted packets  {compute_total_lost_packets(total_lost_packets)} are rebroadcasts.")



if __name__ == "__main__":
    main()



              



