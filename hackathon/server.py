import socket
import threading
import time
from typing import Tuple

from hackathon.color_printing import print_in_color, COLORS, print_error
from hackathon.protocol import BROADCAST_PORT, build_message, OFFER_MESSAGE_TYPE, PAYLOAD_MESSAGE_TYPE, \
    parse_request_message

DEFAULT_UDP_PAYLOAD_SIZE: int = 512  # Maximum size for UDP payloads
BROADCAST_INTERVAL: int = 1  # Interval in seconds for broadcasting messages
BROADCAST_ADDR: Tuple[str, int] = ("255.255.255.255", BROADCAST_PORT)  # Broadcast address and port
UDP_SERVER_PORT: int = 8080
TCP_SERVER_PORT: int = 8081

def main() -> None:
    """
    The main entry point for the server program. Starts the TCP and UDP servers
    and broadcasts offer messages.
    """
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    print_in_color(f"Server started, listening on IP address {ip_address}", color=COLORS.GREEN)

    broadcast_thread = threading.Thread(
        target=broadcast_offer_messages,
        kwargs=dict(udp_port=UDP_SERVER_PORT, tcp_port=TCP_SERVER_PORT)
    )
    tcp_thread = threading.Thread(
        target=start_tcp_server,
        kwargs=dict(server_ip=ip_address, server_port=TCP_SERVER_PORT)
    )
    udp_thread = threading.Thread(
        target=start_udp_server,
        kwargs=dict(server_ip=ip_address, server_port=UDP_SERVER_PORT)
    )

    tcp_thread.start()
    udp_thread.start()
    broadcast_thread.start()

    tcp_thread.join()
    udp_thread.join()
    broadcast_thread.join()


def broadcast_offer_messages(udp_port: int, tcp_port: int) -> None:
    """
    Periodically broadcasts an offer message over UDP.

    :param udp_port: The UDP port offered to clients.
    :param tcp_port: The TCP port offered to clients.
    """
    offer_message = build_message(OFFER_MESSAGE_TYPE, udp_port, tcp_port)
    while True:
        send_broadcast_message(offer_message)
        time.sleep(BROADCAST_INTERVAL)


def send_broadcast_message(message: bytes) -> None:
    """
    Sends a broadcast message.

    :param message: The message to be broadcasted.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # level, opt, value
        try:
            sock.sendto(message, BROADCAST_ADDR)
            print_in_color("DBG: Sent broadcast message...", color=COLORS.LIGHTYELLOW_EX)
        except Exception as e:
            print_error(f"Error sending broadcast message: {e}")


def start_tcp_server(server_ip: str, server_port: int) -> None:
    """
    Starts a TCP server to handle client requests.

    :param server_ip: The host address to bind the server.
    :param server_port: The TCP port to listen on.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((server_ip, server_port))
        server_socket.listen(5)  # The max amount of clients that can wait for the server to accept the connection
        print_in_color(f"DBG: Server listening on {server_ip}:{server_port}", color=COLORS.LIGHTYELLOW_EX)

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                print_in_color(f"DBG: Connection from {client_address}", color=COLORS.LIGHTYELLOW_EX)
                threading.Thread(
                    target=process_tcp_client_request,
                    args=(client_socket,)
                ).start()
            except Exception as e:
                print_error(f"Error in TCP server: {e}")


def process_tcp_client_request(client_socket: socket.socket) -> None:
    """
    Handles a single TCP client.

    :param client_socket: The client's socket.
    """
    with client_socket:
        try:
            message: bytes = client_socket.recv(1024)
            if message[-1] != ord("\n"):
                raise ValueError("Message is too large or improperly terminated with '\\n'.")

            file_size = parse_request_message(message)
            print_in_color(f"DBG: Received filesize of {file_size} bytes", color=COLORS.LIGHTYELLOW_EX)

            response: str = "a" * file_size
            client_socket.sendall(response.encode())
            print_in_color(f"DBG: Sent response of length: {len(response)}", color=COLORS.LIGHTYELLOW_EX)
        except Exception as e:
            print_error(f"Error processing TCP client request: {e}")


def process_udp_client_request(client_address: Tuple[str, int], message: bytes) -> None:
    """
    Handles a single UDP client in a separate thread.

    :param client_address: The address of the client.
    :param message: The message received from the client.
    """
    try:
        file_size: int = parse_request_message(message)
        print_in_color(f"DBG: Handling UDP client {client_address}, received message: {message}", color=COLORS.LIGHTYELLOW_EX)
        send_udp_file_segments(target_address=client_address, file_size=file_size, payload_size=DEFAULT_UDP_PAYLOAD_SIZE)
    except Exception as e:
        print_error(f"Error processing UDP client {client_address}: {e}")


def send_udp_file_segments(target_address: Tuple[str, int], file_size: int, payload_size: int) -> None:
    """
    Sends UDP payloads to a client.

    :param target_address: The target client's address.
    :param file_size: The total size of the file.
    :param payload_size: The size of each UDP payload.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        total_segments: int = (file_size + payload_size - 1) // payload_size

        for segment_number in range(total_segments):
            start_byte = segment_number * payload_size
            remaining_bytes = file_size - start_byte
            current_payload_size = min(payload_size, remaining_bytes)
            payload_data: bytes = b'a' * current_payload_size

            payload_message: bytes = build_message(
                PAYLOAD_MESSAGE_TYPE,
                total_segments,
                segment_number,
                payload=payload_data
            )

            udp_socket.sendto(payload_message, target_address)
            print_in_color(f"DBG: Sent segment {segment_number + 1}/{total_segments}, size: {current_payload_size} bytes", color=COLORS.LIGHTYELLOW_EX)


def start_udp_server(server_ip: str, server_port: int) -> None:
    """
    Starts a UDP server to handle client requests.

    :param server_ip: The host address to bind the server.
    :param server_port: The UDP port to listen on.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind((server_ip, server_port))
        print_in_color(f"DBG: UDP server listening on {server_ip}:{server_port}", color=COLORS.LIGHTYELLOW_EX)

        while True:
            try:
                message, client_address = udp_socket.recvfrom(1024)
                print_in_color(f"DBG: Received message from {client_address}: {message}", color=COLORS.LIGHTYELLOW_EX)

                threading.Thread(
                    target=process_udp_client_request,
                    args=(client_address, message)
                ).start()
            except Exception as e:
                print_error(f"Error in UDP server: {e}")


if __name__ == '__main__':
    main()
