import socket
import struct
import threading
import time

UDP_PAYLOAD_SIZE = 512
BROADCAST_INTERVAL = 1

BROADCAST_ADDR = ("255.255.255.255", 12345)

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


def main():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    print(f"Server started, listening on IP address {ip_address}")

    udp_port = 8080
    tcp_port = 8081
    broadcast_thread = threading.Thread(
        target=start_broadcasting_offer,
        kwargs=dict(
            udp_port=udp_port,
            tcp_port=tcp_port
        ),
        daemon=True
    )
    tcp_thread = threading.Thread(
        target=handle_tcp_requests,
        kwargs=dict(host=ip_address, port=tcp_port),
        daemon=True
    )
    udp_thread = threading.Thread(
        target=handle_udp_requests,
        kwargs=dict(host=ip_address, port=udp_port),
        daemon=True
    )
    tcp_thread.start()
    udp_thread.start()
    broadcast_thread.start()


def start_broadcasting_offer(udp_port: int, tcp_port: int):
    offer_message = build_offer_message(tcp_port, udp_port)
    print(offer_message)  # TODO: Remove
    while True:
        send_broadcast(offer_message)
        time.sleep(BROADCAST_INTERVAL)


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


def build_payload(total_segments: int, segment_number: int, payload_data: bytes) -> bytes:
    message = struct.pack(MESSAGES_FORMATS[PAYLOAD_MESSAGE_TYPE], total_segments, segment_number) + payload_data
    return build_header(PAYLOAD_MESSAGE_TYPE) + message


def build_header(message_type: int) -> bytes:
    return struct.pack(HEADER_FORMAT, MAGIC_COOKIE, message_type)


def send_broadcast(message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.sendto(message, BROADCAST_ADDR)  # TODO: Handle errors
        print("DBG: Sent broadcast message...")  # TODO: Remove
    except Exception as e:
        print(f"Error sending broadcast message: {e}")
    finally:
        sock.close()


def handle_tcp_requests(host: str, port: int):
    """Start a TCP server that listens for a message and responds."""
    # Create a socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the host and port
    server_socket.bind((host, port))
    print(f"DBG: Server listening on {host}:{port}")  # TODO: delete

    # Listen for incoming connections (backlog of 1)
    server_socket.listen(5)

    while True:
        try:
            # Accept a client connection
            client_socket, client_address = server_socket.accept()
            print(f"DBG: Connection from {client_address}")  # TODO: delete
            client_thread = threading.Thread(
                target=handle_tcp_client,
                args=(client_socket,),
                daemon=True
            )
            client_thread.start()

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"An error occurred: {e}")

    # Close the server socket
    server_socket.close()


def handle_tcp_client(client_socket: socket.socket):
    try:
        # Receive data from the client
        header_size = struct.calcsize(HEADER_FORMAT)
        header_data = client_socket.recv(header_size)
        if not header_data:
            raise ValueError("No data received, closing connection.")

        if len(header_data) < header_size:
            raise ValueError("Got incomplete header")

        message_type = parse_header(header_data)

        if message_type != REQUEST_MESSAGE_TYPE:
            raise ValueError(f"Got wrong message type, expected {REQUEST_MESSAGE_TYPE} and got {message_type}.")

        message_size = struct.calcsize(MESSAGES_FORMATS[message_type])
        message_data = client_socket.recv(message_size + 1)
        if not message_data:
            raise ValueError("No message data received, closing connection.")

        if len(message_data) < message_size + 1:
            raise ValueError("Incomplete message data received.")

        # Check if the last byte is '\n'
        if message_data[-1] != ord("\n"):
            raise ValueError("Message is too large or improperly terminated with '\\n'.")

        file_size = parse_request(message_data[:-1])

        print(f"DBG: Received filesize of {file_size} bytes")  # TODO: delete

        # Send a response back to the client
        response = "a" * file_size
        client_socket.sendall(response.encode())
        print(f"DBG: Sent response: {response}")  # TODO: delete
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the connection
        client_socket.close()
        print("DBG: Connection closed.")  # TODO: delete


def handle_client_udp(client_address: str, message: bytes, udp_socket: socket.socket):
    """Handle a single UDP client in a separate thread."""
    try:
        header_size = struct.calcsize(HEADER_FORMAT)
        message_type = parse_header(message[:header_size])
        if message_type != REQUEST_MESSAGE_TYPE:
            raise ValueError(f"Got wrong message type, expected {REQUEST_MESSAGE_TYPE} and got {message_type}.")
        file_size = parse_request(message_type[header_size:])

        print(f"DBG: Handling UDP client {client_address}, received message: {message}")

        send_udp_payloads(target_address=client_address, udp_socket=udp_socket, file_size=file_size,
                          payload_size=UDP_PAYLOAD_SIZE)
    except Exception as e:
        print(f"An error occurred with UDP client {client_address}: {e}")
    finally:
        print(f"DBG: Finished handling UDP client {client_address}")


def send_udp_payloads(target_address, udp_socket, file_size, payload_size):
    """
    Send UDP packets as specified in the payload message format.

    Args:
        target_address (str): Target IP address.
        udp_socket (socket.socket): UDP socket.
        file_size (int): Total size of the data to send (in bytes).
        payload_size (int): Size of the payload per packet (in bytes).
    """
    # Calculate the total number of segments
    total_segments = (file_size + payload_size - 1) // payload_size  # Ceiling division

    try:
        # Loop through each segment and send it
        for segment_number in range(total_segments):
            # Determine the size of this segment's payload
            start_byte = segment_number * payload_size
            remaining_bytes = file_size - start_byte
            current_payload_size = min(payload_size, remaining_bytes)

            # Generate dummy payload data (e.g., 'a' * current_payload_size)
            payload_data = b'a' * current_payload_size

            # Build the UDP payload message
            payload_message = build_payload(
                total_segments,
                segment_number,
                payload_data
            )

            # Send the packet
            udp_socket.sendto(payload_message, target_address)
            print(f"Sent segment {segment_number + 1}/{total_segments}, size: {current_payload_size} bytes")
    except Exception as e:
        print(f"An error occurred while sending UDP payloads: {e}")
    finally:
        udp_socket.close()
        print("UDP socket closed.")


def handle_udp_requests(host: str, port: int):
    """Start a UDP server that listens for messages and spawns threads for each client."""
    # Create a UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind the socket to the host and port
    udp_socket.bind((host, port))
    print(f"DBG: UDP server listening on {host}:{port}")

    while True:
        try:
            # Receive a message from the client
            message, client_address = udp_socket.recvfrom(1024)  # Buffer size of 1024 bytes
            print(f"DBG: Received message from {client_address}: {message.decode()}")

            # Create a new thread to handle the client
            client_thread = threading.Thread(
                target=handle_client_udp,
                args=(client_address, message, udp_socket),
                daemon=True  # Daemon thread so it exits when the main thread exits
            )
            client_thread.start()
        except KeyboardInterrupt:
            print("DBG: Shutting down the UDP server.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

    # Close the UDP socket
    udp_socket.close()
    print("DBG: UDP server closed.")


if __name__ == '__main__':
    main()
