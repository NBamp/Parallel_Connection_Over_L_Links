import random
import argparse
import math
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
    parser.add_argument("--code_rate", help="Ratio of source to total transmitted packets in form k/n")
    args = parser.parse_args()

    num_links = int(input("Define the number of links for the simulation : "))
    loss_prob_arr = []   #array which contains loss probability for each link
    data_rate_arr = num_links * [0]  #array which contains data rate for each link
    channel_transmitted = {} #total of successfully transmitted packets for each channel when block is fully decoded
    r_t = len(data_rate_arr) * [0]  #store for each channel ri(t)



    for i in range(num_links):
        loss_prob_arr.append(float((input(f"Enter channel {i+1} loss probability rate in range[0,1] : "))))
        data_rate_arr[i] = (float(input(f"Enter channel {i+1}  data rate  in range[0,1]  : ")))
        channel_transmitted[i] = 0
        r_t[i] = data_rate_arr[i]  #Initialize starting data rate for each channel



    R_t_1 = len(data_rate_arr) * [0]  #store for each channel Ri(t-1)
    R_t = len(data_rate_arr) * [None]  #store for each channel Ri(t)
    proportional_fair_scheduler_res = len(data_rate_arr) * [0] #
    time_constant = random.randint(1,10) #time constant for computing R_t




    symbols = int(args.num_symbols)
    symbol_bytes = int(args.symbol_size)
    seed = int(args.seed)
    block_size = int(args.block_size)

    try:
        source_k, source_plus_repair = map(int, args.code_rate.split('/'))
        if source_plus_repair - source_k < 0:
            raise ValueError("Code Rate should be in range [0,1]. Please insert appropriate values.")
        repair_n = source_plus_repair - source_k
    except ValueError:
        raise ValueError("Wrong format for code rate.")

    print(f"PyErasure Simulation\n---------------------------------------")
    # print(f"Number of Transmitted Symbols: \t{args.num_symbols}\nSymbol Size (bytes): \t\t{args.symbol_size}\nBlock size: \t\t\t{args.block_size}\nLoss Probability (%): \t\t{args.ploss}\nSeed: \t\t\t\t{args.seed}")

    # Pick the finite field to use for the encoding and decoding.
    field =  pyerasure.finite_field.Binary8()

    # Allocate some data to encode - fill data_in with random data
    random.seed(seed)
    data_in = bytearray(random.getrandbits(8) for _ in range(symbols*symbol_bytes))



    elapsed_timeslots = 0 # indicating how many timeslots have elapsed since the beginning of transmission
    transmitted_packets = 0 # counter for the total number of source packets sent from the encoder

    offset = 0
    total_coded = 0
    is_seed_set = False # to tune generator's seed


    source_packets = 0
    packet_delivery_system_sum = 0
    loss_packet_system_sum = 0
    num_of_blocks = 0

    start = time.time()

    channel = 0 #selected channel

    while True:


        if offset >= len(data_in):
            break
        #maybe use memoryview instead, check if error occurs with indexing
        block_data = data_in[offset:offset + block_size*symbol_bytes] #no error if index exceeds length
        offset += block_size*symbol_bytes


        current_block_size = symbols % block_size if len(block_data) != block_size*symbol_bytes else block_size

        # Create encoder and decoder to handle block size data each time (smaller last block size in case of inexact division)
        encoder = pyblock.Encoder(field, current_block_size, symbol_bytes)
        decoder = pyblock.Decoder(field, current_block_size, symbol_bytes)

        source_packets += current_block_size
        num_of_blocks += 1

        # Create generator generator. The generator must similarly be created
        # based on the encoder/decoder.
        generator = pygenerator.RandomUniform(field, encoder.symbols)
        if not is_seed_set:
            generator.set_seed(seed)
            is_seed_set = True

        encoder.set_symbols(block_data)


        # Number of coded packets to transmit at the end of the block
        coded_packets_per_block = math.ceil(current_block_size / source_k) * repair_n # will result in more redundancy than SW approach if g is not divided by k
        total_coded += coded_packets_per_block




        source_packet_time = {}  #dictionary for storing partial decoded source packets with each time of those
        sum_decoded_packet_time = 0 #sum of total time of source packets until decoder is decoded
        channel_throughput = 0
        packet_loss_block = 0 # counter for packet lose
        packet_delivery_block = 0
        source_encoded_symbols = [] #store each encoded symbol from source packets
        avg_packet_delay_block = 0



        print("Proportional Fair Scheduler selected")
        channel = proportional_fair_scheduler_res.index(max(proportional_fair_scheduler_res))


        print(f"Channel {channel+1} selected for use")

        for index in range(encoder.rank):  #source packets sent from encoder

            coefficients = generator.generate()
            symbol = encoder.encode_symbol(coefficients)
            source_encoded_symbols.append(symbol)
            elapsed_timeslots += 1
            transmitted_packets += 1


            if random.uniform(0, 1) >= loss_prob_arr[channel]:

                decoder.decode_symbol(symbol, bytearray(coefficients))
                source_packet_time[index] = [elapsed_timeslots,decoder.rank-1]


            else:

                packet_loss_block += 1



            if decoder.is_complete():
                break


        prev_source = 0




        for i in source_packet_time.keys():
            print(f"Decoder symbol number {source_packet_time[i][1]} received encoded packet from source number {i}")

            if i-prev_source == 1 or i == source_packet_time[i][1] : #in order packets no delay
                avg_packet_delay_block += 0
            else:
                avg_packet_delay_block += i-prev_source #when delay exists

            prev_source = i

        print(f"Sum of delays before computing average = {avg_packet_delay_block}")

        avg_packet_delay_block = math.ceil(avg_packet_delay_block/decoder.rank)


        print(f"Average packet delay of block is {avg_packet_delay_block}")



        for index in range(coded_packets_per_block):

            coefficients = generator.generate()
            symbol = encoder.encode_symbol(coefficients)
            elapsed_timeslots += 1
            if random.uniform(0, 1) >= loss_prob_arr[channel]:
                decoder.decode_symbol(symbol, bytearray(coefficients))

            if decoder.is_complete():
                break

        if decoder.is_complete():
            for i in source_packet_time.keys():
                sum_decoded_packet_time += elapsed_timeslots - source_packet_time[i][0]
            channel_throughput = (len(source_packet_time) * symbol_bytes) / sum_decoded_packet_time
        else:
            channel_throughput = 0 #data_rate of channel is 0 because block wasnt fully decoded
            print(f"Block number {num_of_blocks} wasn't fully decoded ")

        print(f"Channel {channel+1} Throughput = {channel_throughput}")

        if channel_throughput > data_rate_arr[channel]:  #in case it happens ,  throughput cannot be greater than data_rate
            channel_throughput = data_rate_arr[channel]

        r_t[channel] = channel_throughput

        packet_delivery_block = current_block_size - packet_loss_block
        packet_delivery_system_sum += packet_delivery_block
        loss_packet_system_sum += packet_loss_block


        if channel_throughput != 0:  # There is no counting for decoded source packets when block wasn't fully decoded
            if channel_transmitted[channel] == 0 :
                channel_transmitted[channel] = packet_delivery_block
            else:
                val = channel_transmitted[channel]
                channel_transmitted[channel] = val + packet_delivery_block

        if elapsed_timeslots>0:
            for i in range(len(R_t_1)):
                R_t_1[i] = channel_transmitted[i] * symbol_bytes/elapsed_timeslots  #total number of trasmitted data by that time / timeslot
                print(f"Channel {i+1}'s R(t-1) = {R_t_1[i]}")
                R_t[i] = (1-(1/time_constant)*R_t_1[i] + (1/time_constant)*r_t[i])
                print(f"Channel {i+1}'s R(t) = {R_t[i]}")
                print(f"Channel {i+1}'s r(t) = {r_t[i]}\n")
                proportional_fair_scheduler_res[i] = r_t[i] * (1/R_t[i])


        print(f"Proportional fair scheduler array = {proportional_fair_scheduler_res}")
        print(f"From {current_block_size} source packets {packet_delivery_block}  transmitted successfully and {packet_loss_block} were lost in block_number {{{num_of_blocks}}}")
        print('--------------------------------------------------------------\n\n')

        exit()

    #system_throughput = system_throughput/(symbols / block_size)
    end = time.time()



    print("#####-----Statistics-----#####")
    print(f"Total Transmitted packets: \t{transmitted_packets}")
    print(f"Total coded packets: \t\t{total_coded}")
    print(f"Elapsed timeslots: \t\t{elapsed_timeslots}")
    print(f"Total elapsed time: \t\t{end-start} sec")
    print(f"From {source_packets} total source packets {packet_delivery_system_sum} transmitted successfully and {loss_packet_system_sum} were lost!  ")
    print(f"Final packet_delivery_ratio for system = {packet_delivery_system_sum/source_packets}")
    print(f"Final loss_rate for system =  {loss_packet_system_sum/source_packets}")







if __name__ == "__main__":
    main()
