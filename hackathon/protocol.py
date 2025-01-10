import struct
from typing import Tuple

BROADCAST_PORT = 12345
MAGIC_COOKIE = 0xabcddcba.to_bytes(4, byteorder="big")
HEADER_FORMAT = "4sB"  # Protocol (4 bytes) + Message Type (1 byte)
OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4
MESSAGES_FORMATS = {
    OFFER_MESSAGE_TYPE: ">HH",
    REQUEST_MESSAGE_TYPE: ">Q",
    PAYLOAD_MESSAGE_TYPE: ">QQ",
}


def parse_header(data: bytes) -> int:
    magic_cookie, message_type = struct.unpack(HEADER_FORMAT, data)  # TODO: Add error handling
    if magic_cookie != MAGIC_COOKIE:
        raise ValueError(f"Wrong protocol type, got {magic_cookie} expected {MAGIC_COOKIE}")
    return message_type


def parse_request(data: bytes) -> int:
    return struct.unpack(MESSAGES_FORMATS[REQUEST_MESSAGE_TYPE], data)[0]


def build_offer_message(tcp_port, udp_port):
    message = struct.pack(MESSAGES_FORMATS[OFFER_MESSAGE_TYPE], udp_port, tcp_port)
    return build_header(OFFER_MESSAGE_TYPE) + message


def parse_offer_message(data: bytes) -> Tuple[int, int]:
    header_size = struct.calcsize(HEADER_FORMAT)
    message_type = parse_header(data[:header_size])
    if message_type != OFFER_MESSAGE_TYPE:
        raise ValueError(f"Wrong message type. Got {message_type} expected {OFFER_MESSAGE_TYPE}")
    udp_port, tcp_port = struct.unpack(MESSAGES_FORMATS[message_type], data[header_size:])
    return udp_port, tcp_port


def build_payload(total_segments: int, segment_number: int, payload_data: bytes) -> bytes:
    message = struct.pack(MESSAGES_FORMATS[PAYLOAD_MESSAGE_TYPE], total_segments, segment_number) + payload_data
    return build_header(PAYLOAD_MESSAGE_TYPE) + message


def build_header(message_type: int) -> bytes:
    return struct.pack(HEADER_FORMAT, MAGIC_COOKIE, message_type)

