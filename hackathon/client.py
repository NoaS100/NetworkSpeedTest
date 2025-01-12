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
    file_size = request_positive_integer("Enter the file size to download (positive integer): ", allow_zero=False)
    udp_connections_amount = request_positive_integer(
        "Enter the number of UDP connections (zero or positive integer): ")
    tcp_connections_amount = request_positive_integer(
        "Enter the number of TCP connections (zero or positive integer): ")

    while True:
        server_address, udp_port, tcp_port = get_offer_message()
        print(f"Receive offer from {server_address}")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            udp_futures = [
                executor.submit(
                    measure_udp_download,
                    host=server_address, port=udp_port, file_size=file_size
                ) for _ in range(udp_connections_amount)
            ]
            tcp_futures = [
                executor.submit(
                    measure_tcp_download,
                    host=server_address, port=tcp_port, file_size=file_size
                ) for _ in range(tcp_connections_amount)
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


def request_positive_integer(prompt: str, allow_zero: bool = True) -> int:
    """
    Requests a positive integer (or zero if allowed) from the user.

    :param prompt: The message to display when asking for input.
    :param allow_zero: Whether zero is allowed as a valid input.
    :return: A valid positive integer or zero.
    """
    while True:
        try:
            value = int(input(prompt))
            if value < 0 or (not allow_zero and value == 0):
                if not allow_zero and value == 0:
                    print("Value must be a positive integer (greater than zero). Please try again.")
                else:
                    print("Value must be zero or a positive integer. Please try again.")
            else:
                return value
        except ValueError:
            print("Invalid input. Please enter a numeric value.")


def get_offer_message() -> Tuple[str, int, int]:
    """
    Listens for offer messages from the server and parses a valid offer.

    :return: A tuple containing the server address, UDP port, and TCP port.
    """
    print("Client started, listening for offer requests...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.bind(("", BROADCAST_PORT))
    received_valid_offer_message = False
    while not received_valid_offer_message:
        message, client_address = sock.recvfrom(1024)
        try:
            udp_port, tcp_port = parse_offer_message(message)
            received_valid_offer_message = True
        except Exception:
            print("DBG: Got invalid offer message. Keep trying...")
    return client_address[0], udp_port, tcp_port


def measure_udp_download(host: str, port: int, file_size: int) -> Tuple[float, int, int, int]:
    """
    Measures the performance of a UDP download.

    :param host: The server's address.
    :param port: The UDP port to connect to.
    :param file_size: The size of the file to download.
    :return: A tuple containing the duration of the transfer, total data received,
             total segments received, and the total number of segments expected.
    """
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

        duration_seconds = (end_time - start_time - timedelta(seconds=UDP_TIMEOUT)).total_seconds()
        return duration_seconds, total_data_received, total_segments_received, total_segments
    finally:
        sock.close()


def measure_tcp_download(host: str, port: int, file_size: int) -> Tuple[float, int]:
    """
    Measures the performance of a TCP download.

    :param host: The server's address.
    :param port: The TCP port to connect to.
    :param file_size: The size of the file to download.
    :return: A tuple containing the duration of the transfer and the total data received.
    """
    request_message = build_request_message(file_size)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.connect((host, port))
    try:
        sock.sendall(request_message + "\n".encode())

        start_time = datetime.now()
        response = sock.recv(file_size)
        print(f"DBG: Got a response of length {len(response)}")
        end_time = datetime.now()

        duration_seconds = (end_time - start_time).total_seconds()
        return duration_seconds, len(response)
    finally:
        sock.close()


if __name__ == '__main__':
    main()
