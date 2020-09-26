import socket
import pickle
from crypto import Blockchain, Transaction


ENCODING = 'utf-8'
ADDRESS = input('Enter your adress: ')
PORT = 5050
HEADER = 16

with open('./nodes.txt', 'r') as f:
    NODES = f.read().splitlines()


def save_node(node):
    if node not in NODES:
        NODES.append(node)
        with open('./nodes.txt', 'w') as f:
            for i in NODES:
                f.write(i+'\n')


def make_header(msg):
    return bytes(f'{len(msg):<{HEADER}}', ENCODING) + msg


def receive_message(client_socekt):
    try:
        message_header = client_socekt.recv(HEADER)
        if not len(message_header):
            return False
        message_length = int(message_header.decode(ENCODING))
        full_msg = b''
        while len(full_msg) < message_length:
            full_msg += client_socekt.recv(message_length)
        return {'header': message_header,
                'data': full_msg}
    except Exception as e:
        print(e)
        return False


save_node(ADDRESS)

bc = Blockchain()
try:
    bc.load_chain()
except Exception as e:
    print(f'Empty blockchain. {e}')

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((ADDRESS, PORT))
s.listen()
print(f'[LISTENING] Listening for connections on {ADDRESS} : {PORT}')

while True:
    clientsocket, address = s.accept()
    print(f"[ACCPETED] Connection from {address} has been established.")

    msg = receive_message(clientsocket)
    if msg is False:
        print('Wrong message')
        continue
    try:
        msg = pickle.loads(msg['data'])
        if msg.__class__ == Transaction:
            bc.pending_transactions.append(msg)
        elif msg.__class__ == tuple:
            bc.chain.append(msg[0])
            bc.bank = msg[1]
            bc.bank_block_count = msg[2]
            bc.block_count = msg[3]
            if bc.verify_chain():
                bc.save_chain()
            else:
                print(f'Wrong block received!!! From: {address}.')
        elif msg.__class__ == Blockchain:
            try:
                if msg.verify_chain() and len(msg.chain) >= len(bc.chain):
                    bc = msg
                    bc.save_chain()
                else:
                    print('The received chain was shorther than '
                          'the current chain')
            except Exception as e:
                print(e)
        elif msg.__class__ == list:
            NODES = msg
            with open('./nodes.txt', 'w') as f:
                for i in NODES:
                    f.write(i+'\n')
    except (TypeError,  pickle.UnpicklingError):
        if msg['data'] == b'Send me the blockchain':
            blockchain = pickle.dumps(bc)
            blockchain = make_header(blockchain)
            s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s2.connect((address[0], PORT))
            s2.send(blockchain)
        elif msg['data'] == b'Send me the nodes':
            nodes = pickle.dumps(NODES)
            nodes = make_header(nodes)
            s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s2.connect((address[0], PORT))
            s2.send(nodes)
        elif msg['data'].decode(ENCODING)[:4] == 'node':
            node = msg['data'].decode(ENCODING)[4:]
            save_node(node)
