import hashlib
import queue
import struct
import time
from concurrent.futures import ThreadPoolExecutor
from typing import ClassVar, List, NamedTuple

# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY

# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP


def calcHash(msg: bytes) -> bytes:
    """Calculates the hash of a payload"""
    return hashlib.sha256(msg).digest()


class PacketCorruptError(ValueError):
    """Class for when packet hash is incorrect"""

    pass


# Format:
# Long: seq_n
# Long: recv_buf_size
# Char: flags
HEADER_FORMAT  = "LLB"

HEADER_SIZE = len(struct.pack(HEADER_FORMAT, 0, 0, 0))
HASH_SIZE = 32
PACKET_SIZE = 1472
PAYLOAD_SIZE = PACKET_SIZE - HEADER_SIZE - HASH_SIZE


class Packet(NamedTuple):
    """Class for a single packet"""

    ### Header
    seq_n: int = 0
    recv_buf_size: int = 0

    ### Flags
    ack: bool = False
    fin: bool = False

    ### Payload
    payload: bytearray = b""

    @classmethod
    def from_bytes(cls, buf) -> "Packet":
        header_bytes = buf[:HEADER_SIZE]
        _hash = buf[HEADER_SIZE : HEADER_SIZE + HASH_SIZE]
        payload = buf[HEADER_SIZE + HASH_SIZE :]

        new_hash = calcHash(header_bytes + payload)
        if new_hash != _hash:
            raise PacketCorruptError

        seq_n, recv_buf_size, _flags = struct.unpack(
            HEADER_FORMAT, header_bytes
        )

        # pack flags into a single byte like TCP
        ack = bool((_flags >> 3) & 1)
        fin = bool((_flags >> 7) & 1)

        # print(f"Recv seq_n={seq_n}, ack={ack}, fin={fin}, payload={payload}")

        return Packet(
            seq_n=seq_n, recv_buf_size=recv_buf_size, ack=ack, fin=fin, payload=payload
        )

    def to_bytes(self):
        _flags = int(self.ack) << 3
        _flags |= int(self.fin) << 7

        header_bytes = struct.pack(
            HEADER_FORMAT,
            self.seq_n,
            self.recv_buf_size,
            _flags,
        )

        _hash = calcHash(header_bytes + self.payload)

        return header_bytes + _hash + self.payload


class InflightPacket:
    seq_n: int
    start_time: int
    timeout_s: int
    packet: bytes
    
    def __init__(self, seq_n=0, start_time=0, timeout_s=0, packet=b""):
        self.seq_n = seq_n
        self.start_time = start_time
        self.timeout_s = timeout_s
        self.packet = packet
        
    def __le__(self, other):
        return self.seq_n <= other.seq_n

    def __lt__(self, other):
        return self.seq_n < other.seq_n

    def __gt__(self, other):
        return self.seq_n > other.seq_n

    def __ge__(self, other):
        return self.seq_n >= other.seq_n

    def __eq__(self, other):
        return self.seq_n == other.seq_n


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
        self.acked_n = 0
        self.ACK_TIMEOUT = 0.25  # seconds
        self.send_q = queue.PriorityQueue()  # queue of InflightPacket

        # Recv info
        self.recv_expect_seq_n = 0
        self.recv_q = queue.PriorityQueue()

        # listener thread
        self.closed = False
        self.should_close = False

        executor = ThreadPoolExecutor(max_workers=2)
        executor.submit(self._listener)
        executor.submit(self._sender)

    def send(self, data_bytes: bytes, timeout_s=None) -> None:
        """Note that data_bytes can be larger than one packet."""
        timeout_s = timeout_s if timeout_s else self.ACK_TIMEOUT

        while data_bytes:
            if len(data_bytes) > PAYLOAD_SIZE:
                recv_buf_size = len(data_bytes) - PAYLOAD_SIZE
            else:
                recv_buf_size = 0

            send_buf = Packet(
                seq_n=self.send_next_seq_n,
                recv_buf_size=recv_buf_size,
                payload=data_bytes[: PAYLOAD_SIZE],
            ).to_bytes()
            self.send_q.put(InflightPacket(seq_n=self.send_next_seq_n, start_time=None, timeout_s=timeout_s, packet=send_buf))
            self.send_next_seq_n += 1
            # print(
                # f"Sent (and recv'ed ack for): {data_bytes[:PAYLOAD_SIZE]}, remaining: {data_bytes[PAYLOAD_SIZE:]}"
            # )

            data_bytes = data_bytes[PAYLOAD_SIZE :]
    
    def _sender(self):
        """Sender background thread"""
        inflight_q: List[InflightPacket] = []  # actual inflight packets

        while not self.closed or not inflight_q.empty():
            # print(f"Loop 1, {self.send_q.empty()}")
            # First check send_q for new packets to send
            while not self.send_q.empty() and len(inflight_q) < 25:
                # print(f"Loop 2, {self.send_q.empty()}")
                new_packet: InflightPacket = self.send_q.get()
                new_packet.start_time = time.time()
                self.socket.sendto(new_packet.packet, (self.dst_ip, self.dst_port))
                inflight_q.append(new_packet)

            # Check acks for inflight packets
            # iterate through inflight packets, remove those <= acked_n
            # for the packet (acked_n + 1), check timer
            idx = -1
            resend_all = False
            for i, pack in enumerate(inflight_q):
                if pack.seq_n <= self.acked_n:
                    # packet has been acked, update idx to be removed
                    idx = i
                else:
                    # earliest packet not acked, check timer
                    if (time.time() - pack.start_time) > pack.timeout_s:
                        # print(f"seq_n {pack.seq_n} timed out")
                        resend_all = True

                    break

            if idx > 0:
                inflight_q = inflight_q[idx:]
            
            if resend_all:
                # if first packet after previous ack'ed timed out,
                # all packets after have also timed out. Resend all
                for pack in inflight_q:
                    pack.start_time = time.time()
                    self.socket.sendto(pack.packet, (self.dst_ip, self.dst_port))


    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        while not self.closed:
            packet = self.recv_q.get()
            print(f"Recv'ed seq_n = {packet.seq_n}")

            if packet.seq_n == self.recv_expect_seq_n:
                self.recv_expect_seq_n += 1

                # send ack
                send_buf = Packet(
                    seq_n=packet.seq_n, recv_buf_size=0, ack=True
                ).to_bytes()
                self.socket.sendto(send_buf, (self.dst_ip, self.dst_port))

                return packet.payload

            if packet.seq_n < self.recv_expect_seq_n:
                # This packet was received twice, ignore
                continue
            else:
                self.recv_q.put(packet)

    def _listener(self):
        """Listener running in a background thread"""
        while not self.closed:
            print("Listener loop")
            try:
                buf, addr = self.socket.recvfrom()
                if not buf:
                    continue

                try:
                    packet = Packet.from_bytes(buf)
                except PacketCorruptError:
                    # Ignore corrupt packets and wait for a resend due to timeout
                    # print("Corruption detected")
                    continue

                if packet.ack:
                    self.acked_n = packet.seq_n
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

                self.recv_q.put(packet)

            except Exception as e:
                print("Listener died!")
                print(e)

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
        the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        if not self.should_close:
            # print(f"close called, queue size: {self.buf_q.qsize()}")
            fin_pack = Packet(seq_n=self.send_next_seq_n, fin=True)
            # Sends and waits for FIN ACK
            self.send(fin_pack.to_bytes(), timeout_s=2)
            # Send ACK
            ack_pack = Packet(seq_n=self.send_next_seq_n, ack=True)
            self.socket.sendto(ack_pack.to_bytes(), (self.dst_ip, self.dst_port))

        self.closed = True
        self.socket.stoprecv()
