import socket

ENCODING = 'utf-8'
ADDRESS = input('Enter your adress: ')
PORT = 5050
HEADER = 16


def make_header(msg):
    return bytes(f'{len(msg):<{HEADER}}', ENCODING) + msg


with open('./nodes.txt', 'r') as f:
    NODES = f.read().splitlines()

for node in NODES:
    if node != ADDRESS:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((node, PORT))
        s.send(make_header('Send me the nodes'.encode(ENCODING)))
