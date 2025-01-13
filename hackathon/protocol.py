import struct
from typing import Any, Tuple, Union

# TODO: Ask about broadcast port.
# TODO: Ask big/small indian.

# Constants
BROADCAST_PORT: int = 12345  # Port used for broadcasting
MAGIC_COOKIE: bytes = 0xabcddcba.to_bytes(4, byteorder="big")  # Magic cookie for protocol validation
HEADER_FORMAT: str = "4sB"  # Protocol (4 bytes) + Message Type (1 byte)
HEADER_SIZE: int = struct.calcsize(HEADER_FORMAT)  # Size of the header in bytes

# Message types
OFFER_MESSAGE_TYPE: int = 0x2
REQUEST_MESSAGE_TYPE: int = 0x3
PAYLOAD_MESSAGE_TYPE: int = 0x4

# Message formats
MESSAGES_FORMATS: dict[int, str] = {
    OFFER_MESSAGE_TYPE: ">HH",
    REQUEST_MESSAGE_TYPE: ">Q",
    PAYLOAD_MESSAGE_TYPE: ">QQ",
}

def parse_message(data: bytes) -> Tuple[int, Union[Tuple[Any, ...], None]]:
    """
    Parses a message and returns its type and associated data.

    :param data: The raw message data.
    :return: A tuple containing the message type and parsed values, or None if no body exists.
    :raises ValueError: If the message cannot be parsed due to invalid format or type.
    """
    message_type = parse_header(data)

    if message_type in MESSAGES_FORMATS:
        body_format = MESSAGES_FORMATS[message_type]
        body_size = struct.calcsize(body_format)
        body_data = data[HEADER_SIZE:]

        if len(body_data) < body_size:
            raise ValueError("Data too short to contain a valid message body.")

        try:
            parsed_body = struct.unpack(body_format, body_data[:body_size])
        except struct.error as e:
            raise ValueError(f"Failed to unpack message body for type {message_type}: {e}")

        # Handle variable-length payloads for the payload message type
        if message_type == PAYLOAD_MESSAGE_TYPE:
            payload = body_data[body_size:]
            return message_type, (*parsed_body, payload)

        return message_type, parsed_body

    raise ValueError(f"Unsupported message type: {message_type}")


def parse_header(data: bytes) -> int:
    """
    Parses the header of a message and validates the magic cookie.

    :param data: The raw message data.
    :return: The message type extracted from the header.
    :raises ValueError: If the header is invalid or the magic cookie is incorrect.
    """
    if len(data) < HEADER_SIZE:
        raise ValueError("Data too short to contain a valid header.")

    try:
        magic_cookie, message_type = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
        if magic_cookie != MAGIC_COOKIE:
            raise ValueError("Invalid magic cookie.")
    except struct.error as e:
        raise ValueError(f"Failed to parse header: {e}")

    return message_type


def build_message(message_type: int, *args: Any, payload: bytes = b"") -> bytes:
    """
    Builds a complete message including the header and body.

    :param message_type: The type of the message.
    :param args: Fixed fields for the message body.
    :param payload: Optional payload data for variable-length messages.
    :return: The constructed message as bytes.
    :raises ValueError: If packing the message fails or the message type is unsupported.
    """
    if message_type not in MESSAGES_FORMATS:
        raise ValueError(f"Unsupported message type: {message_type}")

    try:
        body = struct.pack(MESSAGES_FORMATS[message_type], *args) + payload
    except struct.error as e:
        raise ValueError(f"Failed to pack values {args} with type '{message_type}': {e}")

    return build_header(message_type) + body


def build_header(message_type: int) -> bytes:
    """
    Builds the header of a message.

    :param message_type: The type of the message.
    :return: The constructed header as bytes.
    :raises ValueError: If packing the header fails.
    """
    try:
        return struct.pack(HEADER_FORMAT, MAGIC_COOKIE, message_type)
    except struct.error as e:
        raise ValueError(f"Failed to pack header with type '{message_type}': {e}")


def parse_request_message(message: bytes) -> int:
    message_type, body = parse_message(message)
    if message_type != REQUEST_MESSAGE_TYPE:
        raise ValueError(f"Got wrong message type, expected {REQUEST_MESSAGE_TYPE} and got {message_type}.")
    return body[0]
