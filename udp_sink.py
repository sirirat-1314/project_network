"""Consume UDP on h2 so the kernel does not reply with ICMP port-unreachable."""
import socket

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind(("10.0.0.2", 5000))
    while True:
        sock.recvfrom(65535)

