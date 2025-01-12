import struct
from typing import Any, Tuple, Union

BROADCAST_PORT = 12345  # TODO: Ask about the broadcast port.

MAGIC_COOKIE = 0xabcddcba.to_bytes(4, byteorder="big")  # TODO: Ask about big indian vs small indian (relevant to the other types as well).
HEADER_FORMAT = "4sB"  # Protocol (4 bytes) + Message Type (1 byte)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

OFFER_MESSAGE_TYPE = 0x2
REQUEST_MESSAGE_TYPE = 0x3
PAYLOAD_MESSAGE_TYPE = 0x4
MESSAGES_FORMATS = {
    OFFER_MESSAGE_TYPE: ">HH",
    REQUEST_MESSAGE_TYPE: ">Q",
    PAYLOAD_MESSAGE_TYPE: ">QQ",
}

def parse_message(data: bytes) -> Tuple[int, Union[Tuple[Any], None]]:
    """
    Parses a message and returns the message type and corresponding data.

    :param data: The raw message data.
    :return: A tuple containing the message type and the parsed values (or None if no body exists).
    :raises ValueError: If the message cannot be parsed due to invalid format or type.
    """
    message_type = parse_header(data)

    # Parse the message body based on the message type
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

        # Handle payload separately to include the variable-length data
        if message_type == PAYLOAD_MESSAGE_TYPE:
            payload = body_data[body_size:]
            return message_type, (*parsed_body, payload)

        return message_type, parsed_body

    # Unsupported message type
    raise ValueError(f"Unsupported message type: {message_type}")


def parse_header(data):
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
    Builds a message with a header and body.

    :param message_type: The type of the message.
    :param args: The fixed fields for the message body.
    :param payload: Optional payload data (for variable-length messages).
    :return: The constructed message as bytes.
    """
    if message_type not in MESSAGES_FORMATS:
        raise ValueError(f"Unsupported message type: {message_type}")

    body = struct.pack(MESSAGES_FORMATS[message_type], *args) + payload
    return build_header(message_type) + body


def build_header(message_type: int) -> bytes:
    return struct.pack(HEADER_FORMAT, MAGIC_COOKIE, message_type)
