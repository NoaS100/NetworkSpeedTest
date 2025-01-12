import concurrent.futures
import socket
from datetime import datetime, timedelta
from typing import Tuple

from hackathon.protocol import BROADCAST_PORT, parse_offer_message, build_request_message, parse_payload_message

UDP_TIMEOUT = 1 # Timeout used for finishing udp download
BUFFER_SIZE = 1024  # Socket buffer size for receiving data
TCP_MESSAGE_TERMINATOR = "\n".encode()  # Terminator for TCP request messages
BITS_IN_BYTE = 8  # Conversion factor for bytes to bits


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

            process_tcp_results(tcp_futures)
            process_udp_results(udp_futures)

        print("All transfers complete, listening to offer requests")


def process_tcp_results(tcp_futures: list) -> None:
    """
    Processes the results of TCP download futures.

    :param tcp_futures: A list of futures representing TCP downloads.
    """
    for future in concurrent.futures.as_completed(tcp_futures):
        try:
            duration, total_data_received = future.result()
            speed = total_data_received * BITS_IN_BYTE / duration
            print(f"TCP transfer finished, total time: {duration} seconds, total speed: {speed} bits/second")
        except Exception as e:
            print(f"An error occurred in a TCP task: {e}")


def process_udp_results(udp_futures: list) -> None:
    """
    Processes the results of UDP download futures.

    :param udp_futures: A list of futures representing UDP downloads.
    """
    for future in concurrent.futures.as_completed(udp_futures):
        try:
            duration, total_data_received, segments_received_count, expected_segments_count = future.result()
            speed = total_data_received * BITS_IN_BYTE / duration
            percentage_received = (segments_received_count / expected_segments_count) * 100 if expected_segments_count > 0 else 0
            print(
                f"UDP transfer finished, total time: {duration} seconds, total speed: {speed} bits/second, percentage of packets received: {percentage_received}%")
        except Exception as e:
            print(f"An error occurred in a UDP task: {e}")


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
            if value < 0 or (value == 0 and not include_zero):
                print(f"Value must be {'zero or ' if include_zero else ''}a positive integer. Please try again.")
            else:
                return value
        except ValueError:
            print("Invalid input. Please enter a numeric value.")


def listen_for_offer() -> Tuple[str, int, int]:
    """
    Listens for and returns a valid offer message.

    :return: A tuple containing the server address, UDP port, and TCP port.
    """
    print("Client started, listening for offer requests...")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", BROADCAST_PORT))

        while True:
            offer_message, (server_ip, server_port) = sock.recvfrom(1024)
            if is_valid_offer(offer_message):
                return (server_ip, ) + parse_offer_message(offer_message)


def is_valid_offer(offer_message: bytes) -> bool:
    """
    Validates an offer message.

    :param offer_message: The raw offer message.
    :return: True if the offer is valid, False otherwise.
    """
    try:
        parse_offer_message(offer_message)
        return True
    except Exception:
        print("DBG: Got invalid offer message. Keep trying...")
        return False


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

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", 0))
        sock.settimeout(UDP_TIMEOUT)
        sock.sendto(request_message, (server_ip, server_port))
        segments_received_count = 0
        expected_segments_count = 1
        total_data_received = 0

        start_time = datetime.now()

        while True:
            try:
                message = sock.recv(BUFFER_SIZE)
                expected_segments_count, current_segment, payload = parse_payload_message(message)
                segments_received_count += 1
                total_data_received += len(payload)
            except socket.timeout:
                print("DBG: Got timeout message - finishing...")
                break

        end_time = datetime.now()

        duration_seconds = (end_time - start_time - timedelta(seconds=UDP_TIMEOUT)).total_seconds()
        return duration_seconds, total_data_received, segments_received_count, expected_segments_count


def perform_tcp_download(server_ip: str, server_port: int, download_size: int) -> Tuple[float, int]:
    """
    Measures the performance of a TCP download.

    :param server_ip: The server's address.
    :param server_port: The TCP port to connect to.
    :param download_size: The size of the file to download.
    :return: A tuple containing the duration of the transfer and the total data received.
    """
    request_message = build_request_message(download_size)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_ip, server_port))
        sock.sendall(request_message + TCP_MESSAGE_TERMINATOR)

        start_time = datetime.now()

        response = sock.recv(download_size)

        end_time = datetime.now()

        print(f"DBG: Got a response of length {len(response)}")
        duration_seconds = (end_time - start_time).total_seconds()
        return duration_seconds, len(response)


if __name__ == '__main__':
    main()
