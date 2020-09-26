import socket
import pickle
from crypto import Blockchain


ENCODING = 'utf-8'
ADDRESS = input('Enter your adress: ')
PORT = 5050
HEADER = 16


def make_header(msg):
    return bytes(f'{len(msg):<{HEADER}}', ENCODING) + msg


with open('../genesis.txt', 'r') as f:
    pk = f.readline().split(': ')[1][:-1]
    sk = f.readline().split(': ')[1]

with open('../user.txt', 'r') as f:
    pk2 = f.readline().split(': ')[1][:-1]
    sk2 = f.readline().split(': ')[1]

with open('./nodes.txt', 'r') as f:
    NODES = f.read().splitlines()

bc = Blockchain()
try:
    bc.load_chain()
except Exception:
    print('Empty blockchain.')


def send2all(msg):
    for node in NODES:
        if node != ADDRESS:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((node, PORT))
                s.send(msg)
            except Exception as e:
                NODES.remove(node)
                print(f'Lost connection with {node}. {e}')


def send_transaction(sender, receiver, amount, private_key):
    transaction = bc.add_transaction(sender, receiver,
                                     amount, private_key)
    transaction = pickle.dumps(transaction)
    transaction = make_header(transaction)
    send2all(transaction)


def mine(miner):
    block = bc.mine(miner)
    block = pickle.dumps(block)
    block = make_header(block)
    send2all(block)
    bc.save_chain()


def send_blockchain():
    blockchain = pickle.dumps(bc)
    blockchain = make_header(blockchain)
    send2all(blockchain)


send_transaction(pk, pk2, 10, sk)
send_transaction(pk, pk2, 1, sk)
send_transaction(pk2, pk, 1, sk2)
mine(pk)
