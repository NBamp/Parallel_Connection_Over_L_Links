class Channel:

    def __init__(self, symbol_size):

        self._frame_size = 0
        self._symbol_size = symbol_size
        self._capacity = 0  # Assume each link start with this value before defining correlation
        self._frames = 0  # Number of frames link has covered
        self._channel_transmitted_dict = {}  # Dictionary with pair {frame_number:[transmitted_packets,loss_packets] , one pair for each frame used by the link and clear dictionary after block is fully decoded
        self.loss_probability = 0  #Loss probability per link given by the user
        self.total_successfully_transmitted_packets = 0
        self.total_loss_packets = 0
        self.total_transmitted_packets = 0
        self._unused_packets = -1  #Number of unused packets used for each channel in encoding version

        #Metrics for scenario with source packets
        self.transmitted_packets = []  #Transmitted packets each time in scenario with source packets
        self.lost_packets = []  #Array with lost packets in source version
        self.added_packets = []  #Two dimension array with new packets from encoder for each link per block_frame

    @property
    def frames(self):
        return self._frames

    @property
    def frame_size(self):
        return self._frame_size

    @property
    def capacity(self):
        return self._capacity

    @property
    def channel_transmitted_dict(self):
        return self._channel_transmitted_dict

    @property
    def unused_packets(self):
        return self._unused_packets

    @frame_size.setter
    def frame_size(self, size):
        self._frame_size = size

    @capacity.setter
    def capacity(self, length):
        self._capacity = length

    @unused_packets.setter
    def unused_packets(self, number):
        self._unused_packets = number

    def update_by_the_end_of_frame(self, trans, loss):
        self._frames += 1
        self._channel_transmitted_dict[self._frames] = [trans, loss]
        self.total_successfully_transmitted_packets += trans
        self.total_loss_packets += loss
        self.total_transmitted_packets += trans + loss


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


    def reset_for_encoding_version(self):
        self._channel_transmitted_dict.clear()
        self._unused_packets = -1


    def reset_source_version(self):
        self.transmitted_packets.clear()
        self.added_packets.clear()
        self.lost_packets.clear()
