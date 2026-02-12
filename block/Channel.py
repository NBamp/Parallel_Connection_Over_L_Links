import argparse

class Channel:

    def __init__(self, symbol_size):

        self._symbol_size = symbol_size
        self._capacity = 0  # Assume each link start with this value before defining correlation
        self._loss_probability = 0  #Loss probability per link given by the user
        self._throughput = 0 #Maximul throughput computed as capacity * (1-loss_probability)
        self._frames = 0  # Number of frames link has covered
        self._channel_transmitted_dict = {}  # Dictionary with pair {frame_number:[transmitted_packets,loss_packets] , one pair for each frame used by the link and clear dictionary after block is fully decoded
        self._unused_packets = -1  #Number of unused packets used for each channel in encoding version

        #Metrics for scenario with source packets
        self.transmitted_packets = []  #Transmitted packets each time in scenario with source packets
        self.lost_packets = []  #Array with lost packets in source version
        self.added_packets = []  #Two dimension array with new packets from encoder for each link per block_frame

    @property
    def frames(self):
        return self._frames

    @property
    def capacity(self):
        return self._capacity

    @property
    def loss_probability(self):
        return self._loss_probability

    @property
    def throughput(self):
        return self._throughput

    @property
    def channel_transmitted_dict(self):
        return self._channel_transmitted_dict

    @property
    def unused_packets(self):
        return self._unused_packets

    @capacity.setter
    def capacity(self, length):
        self._capacity = length

    @loss_probability.setter
    def loss_probability(self, length):
        self._loss_probability = length

    @throughput.setter
    def throughput(self, length):
        self._throughput = length

    @unused_packets.setter
    def unused_packets(self, number):
        self._unused_packets = number


    
