import concurrent.futures
import socket
from datetime import datetime, timedelta
from typing import Tuple

from hackathon.protocol import BROADCAST_PORT, parse_offer_message, build_request_message, parse_payload_message

UDP_TIMEOUT = 1


def main() -> None:
    """
    The main entry point of the client program. It handles input from the user,
    listens for server offers, and manages the transfer process using threads.
    """
    file_size = get_positive_integer("Enter the file size to download (positive integer): ", include_zero=False)
    udp_connections_count = get_positive_integer("Enter the number of UDP connections (zero or positive integer): ")
    tcp_connections_count = get_positive_integer("Enter the number of TCP connections (zero or positive integer): ")

    while True:
        server_ip, udp_port, tcp_port = listen_for_offer()
        print(f"Receive offer from {server_ip}")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            udp_futures = [
                executor.submit(
                    perform_udp_download,
                    server_ip=server_ip, server_port=udp_port, download_size=file_size
                ) for _ in range(udp_connections_count)
            ]
            tcp_futures = [
                executor.submit(
                    perform_tcp_download,
                    server_ip=server_ip, server_port=tcp_port, download_size=file_size
                ) for _ in range(tcp_connections_count)
            ]

            # Process TCP results
            for future in concurrent.futures.as_completed(tcp_futures):
                try:
                    duration, total_data_received = future.result()
                    speed = total_data_received * 8 / duration
                    print(f"TCP transfer finished, total time: {duration} seconds, total speed: {speed} bits/second")
                except Exception as e:
                    print(f"An error occurred in a TCP thread: {e}")

            # Process UDP results
            for future in concurrent.futures.as_completed(udp_futures):
                try:
                    duration, total_data_received, total_segments_received, total_segments = future.result()
                    speed = total_data_received * 8 / duration
                    percentage_received = (total_segments_received / total_segments) * 100 if total_segments > 0 else 0
                    print(
                        f"UDP transfer finished, total time: {duration} seconds, total speed: {speed} bits/second, percentage of packets received: {percentage_received}%")
                except Exception as e:
                    print(f"An error occurred in a UDP thread: {e}")

        print("All transfers complete, listening to offer requests")


def get_positive_integer(message: str, include_zero: bool = True) -> int:
    """
    Requests a positive integer (or zero if allowed) from the user.

    :param message: The message to display when asking for input.
    :param include_zero: Whether zero is allowed as a valid input.
    :return: A valid positive integer or zero.
    """
    while True:
        try:
            value = int(input(message))
            if value < 0 or (not include_zero and value == 0):
                if not include_zero and value == 0:
                    print("Value must be a positive integer (greater than zero). Please try again.")
                else:
                    print("Value must be zero or a positive integer. Please try again.")
            else:
                return value
        except ValueError:
            print("Invalid input. Please enter a numeric value.")


def listen_for_offer() -> Tuple[str, int, int]:
    """
    Listens for offer messages from the server and parses a valid offer.

    :return: A tuple containing the server address, UDP port, and TCP port.
    """
    print("Client started, listening for offer requests...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.bind(("", BROADCAST_PORT))
    valid_offer_received = False
    while not valid_offer_received:
        offer_message, server_address = sock.recvfrom(1024)
        try:
            udp_port, tcp_port = parse_offer_message(offer_message)
            valid_offer_received = True
        except Exception:
            print("DBG: Got invalid offer message. Keep trying...")
    server_ip, server_port = server_address
    return server_ip, udp_port, tcp_port


def perform_udp_download(server_ip: str, server_port: int, download_size: int) -> Tuple[float, int, int, int]:
    """
    Measures the performance of a UDP download.

    :param server_ip: The server's address.
    :param server_port: The UDP port to connect to.
    :param download_size: The size of the file to download.
    :return: A tuple containing the duration of the transfer, total data received,
             total segments received, and the total number of segments expected.
    """
    request_message = build_request_message(download_size)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))
    sock.settimeout(UDP_TIMEOUT)
    try:
        sock.sendto(request_message, (server_ip, server_port))

        start_time = datetime.now()
        segments_received_count = 0
        expected_segments_count = 1
        total_data_received = 0
        while True:
            try:
                message, server_ip = sock.recvfrom(1024)
                expected_segments_count, current_segment, payload = parse_payload_message(message)
                segments_received_count += 1
                total_data_received += len(payload)
            except socket.timeout:
                print("DBG: Got timeout message - finishing...")
                break
        end_time = datetime.now()

        duration_seconds = (end_time - start_time - timedelta(seconds=UDP_TIMEOUT)).total_seconds()
        return duration_seconds, total_data_received, segments_received_count, expected_segments_count
    finally:
        sock.close()


def perform_tcp_download(server_ip: str, server_port: int, download_size: int) -> Tuple[float, int]:
    """
    Measures the performance of a TCP download.

    :param server_ip: The server's address.
    :param server_port: The TCP port to connect to.
    :param download_size: The size of the file to download.
    :return: A tuple containing the duration of the transfer and the total data received.
    """
    request_message = build_request_message(download_size)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.connect((server_ip, server_port))
    try:
        sock.sendall(request_message + "\n".encode())

        start_time = datetime.now()
        response = sock.recv(download_size)
        print(f"DBG: Got a response of length {len(response)}")
        end_time = datetime.now()

        duration_seconds = (end_time - start_time).total_seconds()
        return duration_seconds, len(response)
    finally:
        sock.close()


if __name__ == '__main__':
    main()
