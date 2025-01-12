import socket
import threading
import time
from typing import Tuple

from hackathon.protocol import REQUEST_MESSAGE_TYPE, BROADCAST_PORT, build_message, OFFER_MESSAGE_TYPE, parse_message, \
    PAYLOAD_MESSAGE_TYPE

UDP_PAYLOAD_SIZE = 512
BROADCAST_INTERVAL = 1

BROADCAST_ADDR = ("255.255.255.255", BROADCAST_PORT)


def main():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    print(f"Server started, listening on IP address {ip_address}")

    # TODO: get random free ports:
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
    tcp_thread.join()
    udp_thread.join()
    broadcast_thread.join()


def start_broadcasting_offer(udp_port: int, tcp_port: int):
    offer_message = build_message(OFFER_MESSAGE_TYPE, udp_port, tcp_port)
    while True:
        send_broadcast(offer_message)
        time.sleep(BROADCAST_INTERVAL)


def send_broadcast(message: bytes) -> None:
    """
    Sends a broadcast message.

    :param message: The message to be broadcasted.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            sock.sendto(message, BROADCAST_ADDR)
            print("DBG: Sent broadcast message...")
        except Exception as e:
            print(f"Error sending broadcast message: {e}")


def handle_tcp_requests(host: str, port: int) -> None:
    """
    Starts a TCP server to handle client requests.

    :param host: The host address.
    :param port: The TCP port.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"DBG: Server listening on {host}:{port}")

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                print(f"DBG: Connection from {client_address}")
                threading.Thread(
                    target=handle_tcp_client,
                    args=(client_socket,),
                    daemon=True
                ).start()
            except KeyboardInterrupt:
                print("DBG: Shutting down the TCP server.")
                break
            except Exception as e:
                print(f"An error occurred: {e}")


def handle_tcp_client(client_socket: socket.socket) -> None:
    """
    Handles a single TCP client.

    :param client_socket: The client's socket.
    """
    with client_socket:
        try:
            message = client_socket.recv(1024)
            if message[-1] != ord("\n"):
                raise ValueError("Message is too large or improperly terminated with '\\n'.")

            message_type, body = parse_message(message)
            if message_type != REQUEST_MESSAGE_TYPE:
                raise ValueError(f"Got wrong message type, expected {REQUEST_MESSAGE_TYPE} and got {message_type}.")

            file_size = body[0]
            print(f"DBG: Received filesize of {file_size} bytes")

            response = "a" * file_size
            client_socket.sendall(response.encode())
            print(f"DBG: Sent response of length: {len(response)}")
        except Exception as e:
            print(f"An error occurred: {e}")


def handle_client_udp(client_address: Tuple[str, int], message: bytes):
    """Handle a single UDP client in a separate thread."""
    try:
        message_type, body = parse_message(message)

        if message_type != REQUEST_MESSAGE_TYPE:
            raise ValueError(f"Got wrong message type, expected {REQUEST_MESSAGE_TYPE} and got {message_type}.")

        file_size = body[0]

        print(f"DBG: Handling UDP client {client_address}, received message: {message}")

        send_udp_payloads(target_address=client_address, file_size=file_size, payload_size=UDP_PAYLOAD_SIZE)
    except Exception as e:
        print(f"An error occurred with UDP client {client_address}: {e}")
    finally:
        print(f"DBG: Finished handling UDP client {client_address}")


def send_udp_payloads(target_address: Tuple[str, int], file_size: int, payload_size: int) -> None:
    """
    Sends UDP payloads to a client.

    :param target_address: The target client's address.
    :param file_size: The total size of the file.
    :param payload_size: The size of each UDP payload.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        total_segments = (file_size + payload_size - 1) // payload_size

        try:
            for segment_number in range(total_segments):
                start_byte = segment_number * payload_size
                remaining_bytes = file_size - start_byte
                current_payload_size = min(payload_size, remaining_bytes)
                payload_data = b'a' * current_payload_size

                payload_message = build_message(
                    PAYLOAD_MESSAGE_TYPE,
                    total_segments,
                    segment_number,
                    payload=payload_data
                )

                udp_socket.sendto(payload_message, target_address)
                print(f"Sent segment {segment_number + 1}/{total_segments}, size: {current_payload_size} bytes")
        except Exception as e:
            print(f"An error occurred while sending UDP payloads: {e}")


def handle_udp_requests(host: str, port: int) -> None:
    """
    Starts a UDP server to handle client requests.

    :param host: The host address.
    :param port: The UDP port.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind((host, port))
        print(f"DBG: UDP server listening on {host}:{port}")

        while True:
            try:
                message, client_address = udp_socket.recvfrom(1024)
                print(f"DBG: Received message from {client_address}: {message}")

                threading.Thread(
                    target=handle_client_udp,
                    args=(client_address, message),
                    daemon=True
                ).start()
            except KeyboardInterrupt:
                print("DBG: Shutting down the UDP server.")
                break
            except Exception as e:
                print(f"An error occurred: {e}")


if __name__ == '__main__':
    main()
