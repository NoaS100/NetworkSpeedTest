import socket
import threading
from typing import Tuple

from hackathon.protocol import BROADCAST_PORT, parse_offer_message


def main():
    file_size = request_file_size()
    udp_connections_amount = request_udp_connections_amount()
    tcp_connections_amount = request_tcp_connections_amount()

    server_address, udp_port, tcp_port = get_offer_message()
    print(f"Receive offer from {server_address}")
    udp_threads = [
        threading.Thread(
            target=measure_udp_download,
            kwargs=dict(host=server_address, port=udp_port, file_size=file_size),
            daemon=True
        ) for _ in range(udp_connections_amount)
    ]
    tcp_threads = [
        threading.Thread(
            target=measure_tcp_download,
            kwargs=dict(host=server_address, port=udp_port, file_size=file_size),
            daemon=True
        ) for _ in range(tcp_connections_amount)
    ]
    all_threads = udp_threads + tcp_threads
    for thread in all_threads:
        thread.start()
    for thread in all_threads:
        thread.join()


def request_file_size() -> int:
    return 1024  # TODO: Change this to input


def request_udp_connections_amount() -> int:
    return 2  # TODO: Change this to input


def request_tcp_connections_amount() -> int:
    return 1  # TODO: Change this to input


def get_offer_message() -> Tuple[str, int, int]:
    print("Client started, listening for offer requests...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.bind(("", BROADCAST_PORT))
    received_valid_offer_message = False
    while not received_valid_offer_message:
        message, client_address = sock.recvfrom(1024)  # Buffer size of 1024 bytes
        try:
            udp_port, tcp_port = parse_offer_message(message)
            received_valid_offer_message = True
        except Exception:
            print("DBG: Got invalid offer message. Keep trying...")
    return client_address[0], udp_port, tcp_port


def measure_udp_download(host: str, port: int, file_size: int) -> int:
    pass


def measure_tcp_download(host: str, port: int, file_size: int) -> int:
    pass


if __name__ == '__main__':
    main()
