from Channel import Channel

def compute_total(array: list[int]):
    return sum(array)

def compute_average(array: list[int]):
    return sum(array)/len(array)

def compute_unused_packets_per_block_network_coding_version(channels: list[Channel]):
    unused = 0
    for channel in channels:
        if channel.unused_packets == -1:
            continue
        unused += channel.unused_packets
    return unused
