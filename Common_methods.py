def compute_total(array):
    return sum(array)

def compute_average(array):
    return sum(array)/len(array)

def compute_unused_packets_per_block_network_coding_version(array):
    unused = 0
    for i in array:
        if i.unused_packets == -1:
            continue
        unused += i.unused_packets
    return unused
