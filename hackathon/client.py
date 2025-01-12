import socket
import threading
from datetime import datetime, timedelta
from typing import Tuple

from hackathon.protocol import BROADCAST_PORT, parse_offer_message, build_request_message, parse_payload_message

UDP_TIMEOUT = 1


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
            kwargs=dict(host=server_address, port=tcp_port, file_size=file_size),
            daemon=True
        ) for _ in range(tcp_connections_amount)
    ]
    all_threads = udp_threads + tcp_threads
    for thread in all_threads:
        thread.start()
    for thread in all_threads:
        thread.join()


def request_file_size() -> int:
    return 10 * 1024 * 1024  # TODO: Change this to input


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


def measure_udp_download(host: str, port: int, file_size: int) -> float:
    request_message = build_request_message(file_size)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))
    sock.settimeout(UDP_TIMEOUT)
    try:
        sock.sendto(request_message, (host, port))

        start_time = datetime.now()
        total_segments_received = 0
        total_segments = 1
        total_data_received = 0
        while True:
            try:
                message, host = sock.recvfrom(1024)
                total_segments, current_segment, payload = parse_payload_message(message)
                total_segments_received += 1
                total_data_received += len(payload)
            except socket.timeout:
                print("DBG: Got timeout message - finishing...")
                break
        end_time = datetime.now()

        # Subtracting the timeout.
        duration_seconds = (end_time - start_time - timedelta(seconds=UDP_TIMEOUT)).total_seconds()
        speed = total_data_received * 8 / duration_seconds
        print(f"UDP transfer finished, total time: {duration_seconds}, total speed: {speed} bits/second, percentage of packets received: {total_segments_received / total_segments * 100}%")
        return duration_seconds
    finally:
        sock.close()



def measure_tcp_download(host: str, port: int, file_size: int) -> float:
    request_message = build_request_message(file_size)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.connect((host, port))
    try:
        sock.sendall(request_message + "\n".encode())

        start_time = datetime.now()
        response = sock.recv(file_size)
        print(f"DBG: Got a response of length {len(response)}")
        end_time = datetime.now()

        # Using total_seconds to get a float (using seconds might cause getting a result of 0).
        duration_seconds = (end_time - start_time).total_seconds()
        if len(response) != file_size:
            print("Error: Got wrong file size")
        else:
            speed = file_size * 8 / duration_seconds
            print(f"TCP transfer finished, total time: {duration_seconds} seconds, total speed: {speed} bits/second")
        return duration_seconds
    finally:
        sock.close()


if __name__ == '__main__':
    main()
