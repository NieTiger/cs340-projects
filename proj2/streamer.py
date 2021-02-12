import hashlib
import queue
import struct
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
from typing import ClassVar

# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP


def calcHash(msg: bytes) -> bytes:
    """Calculates the hash of a payload"""
    return hashlib.sha256(msg).digest()


class PacketCorruptError(ValueError):
    """Class for when packet hash is incorrect"""

    pass


@dataclass(order=True)
class Packet:
    """Class for a single packet"""

    ### Header
    seq_n: int = 0
    recv_buf_size: int = 0

    ### Flags
    ack: bool = False
    fin: bool = False

    ### Payload
    payload: bytearray = b""

    # Format:
    # Long: seq_n
    # Long: recv_buf_size
    # Char: flags
    HEADER_FORMAT: ClassVar = "LLB"

    HEADER_SIZE: ClassVar = len(struct.pack(HEADER_FORMAT, 0, 0, 0))
    HASH_SIZE: ClassVar = 32
    PACKET_SIZE: ClassVar = 1472
    PAYLOAD_SIZE: ClassVar = PACKET_SIZE - HEADER_SIZE - HASH_SIZE

    @classmethod
    def from_bytes(cls, buf):
        header_bytes = buf[:cls.HEADER_SIZE]
        _hash = buf[cls.HEADER_SIZE : cls.HEADER_SIZE + cls.HASH_SIZE]
        payload = buf[cls.HEADER_SIZE + cls.HASH_SIZE :]

        new_hash = calcHash(header_bytes + payload)
        if new_hash != _hash:
            raise PacketCorruptError

        seq_n, recv_buf_size, _flags = struct.unpack(
            cls.HEADER_FORMAT, header_bytes
        )

        # pack flags into a single byte like TCP
        ack = bool((_flags >> 3) & 1)
        fin = bool((_flags >> 7) & 1)

        print(f"Recv seq_n={seq_n}, ack={ack}, fin={fin}, payload={payload}")

        return Packet(
            seq_n=seq_n, recv_buf_size=recv_buf_size, ack=ack, fin=fin, payload=payload
        )

    def to_bytes(self):
        _flags = int(self.ack) << 3
        _flags |= int(self.fin) << 7

        header_bytes = struct.pack(
            self.HEADER_FORMAT,
            self.seq_n,
            self.recv_buf_size,
            _flags,
        )

        _hash = calcHash(header_bytes + self.payload)

        return header_bytes + _hash + self.payload


class Streamer:
    def __init__(self, dst_ip, dst_port, src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
        and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port

        # Send info
        self.send_next_seq_n = 0
        self.ack = False
        self.ACK_TIMEOUT = 0.25  # seconds

        # Recv info
        self.recv_expect_seq_n = 0
        self.buf_q = queue.PriorityQueue()

        # listener thread
        self.closed = False
        self.should_close = False

        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(self.listener)

    def _send(self, send_buf: bytes, timeout_t: float) -> None:
        timeout = False
        while not self.ack:
            if timeout:
                print("Resending :)")

            # Send data to socket
            self.socket.sendto(send_buf, (self.dst_ip, self.dst_port))

            # wait for ack before continuing
            time_start = time.time()
            while not self.ack:
                time.sleep(0.001)
                if time.time() - time_start > timeout_t:
                    print("Timeout waiting for ack, resend")
                    timeout = True
                    break

        self.ack = False
        self.send_next_seq_n += 1

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        while data_bytes:
            if len(data_bytes) > Packet.PAYLOAD_SIZE:
                recv_buf_size = len(data_bytes) - Packet.PAYLOAD_SIZE
            else:
                recv_buf_size = 0

            send_buf = Packet(
                seq_n=self.send_next_seq_n,
                recv_buf_size=recv_buf_size,
                payload=data_bytes[: Packet.PAYLOAD_SIZE],
            ).to_bytes()
            self._send(send_buf, self.ACK_TIMEOUT)
            print(
                f"Sent (and recv'ed ack for): {data_bytes[:Packet.PAYLOAD_SIZE]}, remaining: {data_bytes[Packet.PAYLOAD_SIZE:]}"
            )

            data_bytes = data_bytes[Packet.PAYLOAD_SIZE :]

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        while not self.closed:
            packet = self.buf_q.get()

            if packet.seq_n == self.recv_expect_seq_n:
                self.recv_expect_seq_n += 1
                return packet.payload

            if packet.seq_n < self.recv_expect_seq_n:
                # This packet was received twice, ignore
                continue
            else:
                self.buf_q.put(packet)

    def listener(self):
        while not self.closed:
            try:
                buf, addr = self.socket.recvfrom()
                if not buf:
                    continue

                try:
                    packet = Packet.from_bytes(buf)
                except PacketCorruptError:
                    # Ignore corrupt packets and wait for a resend due to timeout
                    print("Corruption detected")
                    continue

                if packet.ack:
                    self.ack = True
                    if packet.fin:
                        self.should_close = True
                    continue

                elif packet.fin:
                    # send fin ack
                    send_buf = Packet(
                        seq_n=packet.seq_n, recv_buf_size=0, ack=True, fin=True
                    ).to_bytes()
                    self.socket.sendto(send_buf, (self.dst_ip, self.dst_port))
                    self.should_close = True
                    continue

                # send ack
                send_buf = Packet(
                    seq_n=packet.seq_n, recv_buf_size=0, ack=True
                ).to_bytes()
                self.socket.sendto(send_buf, (self.dst_ip, self.dst_port))

                self.buf_q.put(packet)

            except Exception as e:
                print("Listener died!")
                print(e)

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
        the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        if not self.should_close:
            print(f"close called, queue size: {self.buf_q.qsize()}")
            fin_pack = Packet(seq_n=self.send_next_seq_n, fin=True)
            # Sends and waits for FIN ACK
            self._send(fin_pack.to_bytes(), 2)
            # Send ACK
            ack_pack = Packet(seq_n=self.send_next_seq_n, ack=True)
            self.socket.sendto(ack_pack.to_bytes(), (self.dst_ip, self.dst_port))

        self.closed = True
        self.socket.stoprecv()
