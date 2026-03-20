import argparse

class Channel:

    def __init__(self, symbol_size):

        self._symbol_size = symbol_size
        self._bandwidth = 0  # Assume each link start with this value before defining correlation
        self._loss_rate = 0  #Loss probability per link given by the user
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
    def bandwidth(self):
        return self._bandwidth

    @property
    def loss_rate(self):
        return self._loss_rate

    @property
    def throughput(self):
        return self._throughput

    @property
    def channel_transmitted_dict(self):
        return self._channel_transmitted_dict

    @property
    def unused_packets(self):
        return self._unused_packets

    @bandwidth.setter
    def bandwidth(self, length):
        self._bandwidth = length

    @loss_rate.setter
    def loss_rate(self, length):
        self._loss_rate = length

    @throughput.setter
    def throughput(self, length):
        self._throughput = length

    @unused_packets.setter
    def unused_packets(self, number):
        self._unused_packets = number


    def update_by_the_end_of_frame(self, trans, loss):
        self._frames += 1
        self._channel_transmitted_dict[self._frames] = [trans, loss]


    #Computing delay and successfully transmitted packets per block
    def compute_delay_and_successfully_transmitted_packets_per_block(self):
        delay = 0
        successfully_transmitted_packets_per_block = 0
        for i in self._channel_transmitted_dict:
            successfully_transmitted_packets_per_block += self._channel_transmitted_dict[i][0]
            delay += (self.frames - i) * self._channel_transmitted_dict[i][0]

        return delay, successfully_transmitted_packets_per_block

    def compute_number_of_losses_per_block(self):
        loss = 0
        for i in self._channel_transmitted_dict:
            loss += self._channel_transmitted_dict[i][1]
        return loss



