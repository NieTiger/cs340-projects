from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import ClassVar
import queue
import struct
import time

# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP

# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY


@dataclass(order=True)
class Packet:
    """Class for a single packet"""

    # Header
    seq_n: int
    recv_buf_size: int
    ack: bool

    # Payload
    payload: bytearray = b""

    _HEADER_FORMAT: ClassVar = "LLcx"
    _HEADER_SIZE: ClassVar = len(struct.pack(_HEADER_FORMAT, 0, 0, b"0"))
    _PACKET_SIZE: ClassVar = 1472
    _PAYLOAD_SIZE: ClassVar = _PACKET_SIZE - _HEADER_SIZE

    @classmethod
    def from_bytes(cls, buf):
        seq_n, recv_buf_size, ack = struct.unpack(
            cls._HEADER_FORMAT, buf[: Packet._HEADER_SIZE]
        )

        if ack == b'0':
            ack = False
        else:
            ack = True

        payload = buf[cls._HEADER_SIZE :]
        return Packet(seq_n, recv_buf_size, ack, payload)

    def to_bytes(self):
        return (
            struct.pack(
                self._HEADER_FORMAT,
                self.seq_n,
                self.recv_buf_size,
                b"1" if self.ack else b"0",
            )
            + self.payload
        )


class Streamer:
    def __init__(self, dst_ip, dst_port, src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
        and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port

        # Packet header structure
        # sequence #             unsigned long (L)
        # receive_buffer size    unsigned long (L)
        # ack                    byte (c)

        # Send info
        self.send_next_seq_n = 0
        self.ack = False

        # Recv info
        self.recv_expect_seq_n = 0
        self.buf_q = queue.PriorityQueue()

        # listener thread
        self.closed = False

        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(self.listener)

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        while data_bytes:
            if len(data_bytes) > Packet._PAYLOAD_SIZE:
                recv_buf_size = len(data_bytes) - Packet._PAYLOAD_SIZE
            else:
                recv_buf_size = 0

            header_buf = Packet(self.send_next_seq_n, recv_buf_size, False).to_bytes()

            send_buf = header_buf + data_bytes[: Packet._PAYLOAD_SIZE]

            # Send data to socket
            self.socket.sendto(send_buf, (self.dst_ip, self.dst_port))
            # wait for ack before continuing
            while not self.ack:
                time.sleep(0.001)

            self.ack = False

            data_bytes = data_bytes[Packet._PAYLOAD_SIZE :]

            self.send_next_seq_n += 1

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        while True:
            if (
                self.buf_q.qsize()
                and self.buf_q.queue[0].seq_n == self.recv_expect_seq_n
            ):
                break

        self.recv_expect_seq_n += 1
        packet = self.buf_q.get()
        return packet.payload

    def listener(self):
        while not self.closed:
            try:
                buf, addr = self.socket.recvfrom()
                if not buf:
                    continue

                packet = Packet.from_bytes(buf)

                if packet.ack:
                    self.ack = True
                else:
                    # send ack
                    send_buf = Packet(0, 0, True).to_bytes()
                    self.socket.sendto(send_buf, (self.dst_ip, self.dst_port))

                self.buf_q.put(packet)

            except Exception as e:
                print("Listener died!")
                print(e)

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
        the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        self.closed = True
        self.socket.stoprecv()
