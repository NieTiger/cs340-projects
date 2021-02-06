import struct

# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP

# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY


class Streamer:
    def __init__(self, dst_ip, dst_port, src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
        and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port

        # Packet header structure
        # sequence #               unsigned long (L)
        # receive_buffer size     unsigned long (L)
        self._HEADER_FORMAT = "LL"
        self._HEADER_SIZE = len(struct.pack(self._HEADER_FORMAT, 1, 1))
        self._PACKET_SIZE = 1472
        self._PAYLOAD_SIZE = self._PACKET_SIZE - self._HEADER_SIZE

        # Send info
        self.send_next_seq_n = 0

        # Recv info
        self.recv_expect_seq_n = 0
        self.buf_lst = []

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        while data_bytes:
            if len(data_bytes) > self._PAYLOAD_SIZE:
                recv_buf_size = len(data_bytes) - self._PAYLOAD_SIZE
            else:
                recv_buf_size = 0
            
            header_buf = struct.pack(self._HEADER_FORMAT, self.send_next_seq_n, recv_buf_size)

            send_buf = header_buf + data_bytes[: self._PAYLOAD_SIZE]
            self.socket.sendto(send_buf, (self.dst_ip, self.dst_port))
            data_bytes = data_bytes[self._PAYLOAD_SIZE :]

            self.send_next_seq_n += 1

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        if self.buf_lst and self.buf_lst[-1][0] == self.recv_expect_seq_n:
            self.recv_expect_seq_n += 1
            _, data = self.buf_lst.pop()
            return data

        while True:
            buf, addr = self.socket.recvfrom()

            seq_n, recv_buf_size = struct.unpack(
                self._HEADER_FORMAT, buf[: self._HEADER_SIZE]
            )

            buf = buf[self._HEADER_SIZE :]

            self.buf_lst.append((seq_n, buf))
            self.buf_lst.sort(key=lambda x: x[0], reverse=True)

            if self.buf_lst[-1][0] == self.recv_expect_seq_n:
                self.recv_expect_seq_n += 1
                _, data = self.buf_lst.pop()
                return data

        return data

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
        the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        pass
