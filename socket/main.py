import socket

# Define the IP and port of the server (Raspberry Pi)
HOST = '3.15.51.67'  # e.g., '192.168.1.10'
PORT = 9992                 # Same port as the server

# Create the socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(b'Hello, Raspberry Pi!')  # Send a message to the server
    data = s.recv(1024)  # Receive response from the server

print(f"Received from server: {data.decode()}")
