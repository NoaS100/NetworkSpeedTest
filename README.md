# Server-Client Network Speed Test Project

**Author:** Lee Chemo and Noa Shvets

This project implements a client-server system for testing and analyzing network speed. this happens as the client can request file transfers from the server over both TCP and UDP connections, and detailed performance statistics such as speed, packet loss, and latency are reported.

---

## Project Overview
This system consists of two main components:
1. **Server:** Sends data when requested by the client over either UDP or TCP.
2. **Client:** Listens for server offers and performs file downloads to measure the network performance.

The project demonstrates the practical differences between TCP and UDP protocols in terms of speed, reliability, and efficiency.

---

## Project Structure
- **`server.py`**: Handles broadcasting, receiving client requests, and sending file data.
- **`client.py`**: Connects to the server, initiates file downloads, and calculates transfer metrics.
- **`protocol.py`**: Defines message formats and handles message parsing.
- **`color_printing.py`**: Utility functions for formatted, colored console output.

---

## System Requirements
- **Python 3.x** installed.
- Install the `colorama` library for console color support using:
  ```bash
  pip install colorama
  ```

---

## Usage Instructions
### 1. Start the Server
To run the server, open a terminal and execute:
```bash
python server.py
```
The server will display its IP address and begin broadcasting its availability.

### 2. Start the Client
To run the client, open a separate terminal and execute:
```bash
python client.py
```
When prompted, provide the following inputs:
- **File Size (bytes):** The size of the file to be downloaded.
- **Number of UDP Connections:** Number of parallel UDP connections.
- **Number of TCP Connections:** Number of parallel TCP connections.

---

## Key Features
### Server
- Periodically broadcasts its availability via UDP.
- Handles both TCP and UDP requests.

### Client
- Detects server offers and initiates data transfer.
- Performs concurrent downloads using specified UDP and TCP connections.
- Calculates and displays:
  - Download speed (Mbps).
  - Packet loss percentage (UDP).
  - Transfer time for each protocol.

---

## Sample Output
### Client Console:

```
Client started, listening for offer requests...
Received offer from 192.168.1.10
UDP transfer #1: 1.25 Mbps, 99.5% packets received
TCP transfer #1: 1.5 Mbps
All transfers complete.
```

---

## Lessons Learned
- **TCP vs. UDP:** Understanding the trade-offs between reliability (TCP) and speed (UDP).
- **Multi-threading:** Using concurrent threads for parallel connections.
- **Socket Programming:** Setting up and handling network sockets for data exchange.

---

## Challenges
- **Handling Packet Loss:** Implementing logic to handle missing packets in UDP transfers.
- **Message Parsing:** Ensuring consistent message structure for reliable parsing.

---

## Conclusion
This project provided hands-on experience with client-server communication, TCP and UDP protocols, and multi-threading. It highlights the importance of choosing the right protocol for different use cases.
