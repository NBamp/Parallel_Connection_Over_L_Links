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
    data_rate_arr = []   #array which contains data rate for each link



    for i in range(num_links):
        loss_prob_arr.append(float((input(f"Enter channel{i+1}'s loss probability in range[0,1] : "))))
        data_rate_arr.append(int(input(f"Enter channel{i+1}'s data rate  in range[0,100] : ")))

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


    loss_rate_channel = 0
    system_throughput = 0
    avg_delay = 0

    inp = int(input("Which approach for computing throughput do you prefer?Press 1 for computing throughput while symbol is still Partially_Decoded or "
                    "Press 2 for computing throughput when  symbol is DECODED : "))
    start = time.time()
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


        block_timeslots = 0   #timeslots used for each block
        c_loss_rate_block = 0 #loss rate for each block
        c_throughput_block = 0 #troughput for each block with the first option of computing
        c_throughput_block_fully_dec = 0 #troughput for each block with the second option of computing
        avg_delay_block = 0 #average delay of packe for each block
       # c_coded_timeslots = 0
        source_timeslots = [] #helper for computing throughput when symbol is DECODED
        packet_delay = {} #storing index of packets as key and slot arrival as value in case of packet delay
        sum_of_delays = [] #store delay for each delayed packet


        pref_channel = max(data_rate_arr) #fair schedule ///we can dynamic renew data_rate with thoughput in order to have dynamic scheduling in this case
        for index in range(encoder.rank):  #source packets sent from encoder

            coefficients = generator.generate()
            symbol = encoder.encode_symbol(coefficients)
            elapsed_timeslots += 1
            transmitted_packets += 1
            block_timeslots += 1

            for i in packet_delay.keys():
                if isinstance(packet_delay[i],int):
                    if decoder.rank == i:
                        x = packet_delay[i]
                        sum_of_delays.append(block_timeslots - x)
                        packet_delay[i] = ""



            if index == decoder.rank:
                packet_delay.update({index:""})
            else:
                packet_delay.update({index:block_timeslots})

            if random.uniform(0, 1) >= loss_prob_arr[data_rate_arr.index(pref_channel)]:
                decoder.decode_symbol(symbol, bytearray(coefficients))
                c_throughput_block += symbol_bytes
                source_timeslots.append(block_timeslots)
            else:
                c_loss_rate_block += 1


        for index in range(coded_packets_per_block):

            if decoder.is_complete():

                for i in source_timeslots:
                    c_throughput_block_fully_dec += symbol_bytes/(block_timeslots - i)

                if index < coded_packets_per_block-1:
                    total_coded -= coded_packets_per_block - index
                break


            for i in packet_delay.keys():
                if isinstance(packet_delay[i],int):
                    if decoder.rank == i:
                        x = packet_delay[i]
                        sum_of_delays.append(block_timeslots - x)
                        packet_delay[i] = ""

            block_timeslots += 1
            coefficients = generator.generate()
            symbol = encoder.encode_symbol(coefficients)
            elapsed_timeslots += 1
            if random.uniform(0, 1) >= loss_prob_arr[data_rate_arr.index(pref_channel)]:
                decoder.decode_symbol(symbol, bytearray(coefficients))
            else:
                c_loss_rate_block += 1





        if inp == 1:
            system_throughput += c_throughput_block/block_size
        else:
            system_throughput += c_throughput_block_fully_dec

        #data_rate_arr[data_rate_arr.index(pref_channel)] = c_throughput_block/(block_size+c_coded_timeslots) #dynamic renewal of data rate
        loss_rate_channel += c_loss_rate_block/block_timeslots

        for i in sum_of_delays:
            avg_delay_block += i



        avg_delay += avg_delay_block/block_size



    loss_rate_channel = loss_rate_channel/(symbols / block_size)
    system_throughput = system_throughput/(symbols / block_size)
    avg_delay = avg_delay/(symbols / block_size)


    



    end = time.time()

    print("#####-----Statistics-----#####")
    print(f"Total Transmitted packets: \t{transmitted_packets}")
    print(f"Total coded packets: \t\t{total_coded}")
    print(f"Total Transmitted packets received: \t\t{transmitted_packets -total_coded}")
    print(f"Elapsed timeslots: \t\t{elapsed_timeslots}")
    print(f"Total elapsed time: \t\t{end-start} sec")
    print(f"Final loss_rate_channel: \t{loss_rate_channel}")
    print(f"Final system throughput : \t{system_throughput} ")
    print(f"Avg delay per packet : \t{avg_delay} ")






if __name__ == "__main__":
    main()
