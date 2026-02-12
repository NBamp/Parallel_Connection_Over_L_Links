from Channel import Channel

import argparse
import pyerasure.block as pyblock


def parse_simulation_args():

    parser = argparse.ArgumentParser()
    parser.add_argument("--num_symbols", help="Total number of transmitted symbols")
    parser.add_argument("--symbol_size", help="Symbol size in bytes")
    parser.add_argument("--seed", help="Seed to control randomness")
    parser.add_argument("--block_size", help="Block (generation) size")

    args = parser.parse_args()

    return {
        'symbols': int(args.num_symbols),
        'symbol_bytes': int(args.symbol_size),
        'seed': int(args.seed),
        'block_size': int(args.block_size)
    }

def initialize_simulation_state():

    return {
        'data_rate': [],
        'avg_delay': [],
        'total_frames': [],
        'total_successful_packets': [],
        'total_lost_packets': [],
        'total_unuseful_packets': []
    }

def setup_channels(symbol_bytes):

    num_links = int(input("Define the number of links for the simulation : "))
    channels = [Channel(symbol_bytes) for _ in range(num_links)]
    frame_size = 0

    for i in range(num_links):
        channels[i].loss_probability = float(input(
            f"Enter channel {i+1} loss probability rate in range[0,1] : "
        ))
        channels[i].capacity = int(input(
            f"Enter channel {i+1}'s capacity measured in subframes : "
        ))
        channels[i].throughput = channels[i].capacity * (1 - channels[i].loss_probability)
        frame_size += channels[i].capacity

    return channels, frame_size

def setup_block(arguments , offset , field , data_in):

    # maybe use memoryview instead, check if error occurs with indexing
    block_data = data_in[offset:offset + arguments['block_size'] * arguments['symbol_bytes']]  # no error if index exceeds length
    offset += arguments['block_size'] * arguments['symbol_bytes']

    current_block_size = arguments['symbols'] % arguments['block_size'] if len(block_data) != arguments['block_size'] * arguments['symbol_bytes'] else arguments['block_size']

    # Create encoder and decoder to handle block size data each time (smaller last block size in case of inexact division)
    encoder = pyblock.Encoder(field, current_block_size, arguments['symbol_bytes'])
    decoder = pyblock.Decoder(field, current_block_size, arguments['symbol_bytes'])

    encoder.set_symbols(block_data)

    return offset , encoder, decoder,

