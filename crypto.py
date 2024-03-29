from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import datetime
from collections import defaultdict
import pandas as pd
import pickle


class Blockchain:
    def __init__(self):
        self.max_supply = 1_000_000
        self.sum_ratio = 1/2
        self.sum_coef = self.max_supply * (1 - self.sum_ratio)
        self.difficulty = 4
        self.max_block_transactions = 100
        self.transactions_count = 0
        self.block_count = 0
        self.bank = defaultdict(float)
        self.bank_block_count = 0
        self.chain = [self.GenesisBlock()]
        self.pending_transactions = [] 

    def GenesisBlock(self):
        pk = 'MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE876ZlFXjbkI53EQYztVCIp3/a7vGQ0My'\
            'qcv/nsU3pfPtZZlGdH6LjBM5XZUDBXgZ8KW6psapks5e7vvUiVFxLw=='
        date = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        initial_amount = self.sum_coef * self.sum_ratio ** 0
        first_transaction = Transaction(0, 'MineReward', pk,
                                        initial_amount, date)
        first_transaction.signature = '0' * 128
        genesis_block = Block(0, '0' * 64, [first_transaction], date, 
                              self.sum_ratio, self.sum_coef)
        genesis_block.mine(self.difficulty)
        self.transactions_count += 1
        self.block_count += 1
        self.bank[pk] = initial_amount
        return genesis_block

    def add_transaction(self, sender, receiver, amount, private_key):
        index = self.transactions_count
        date = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        transaction = Transaction(index, sender, receiver, float(amount), date)
        transaction.sign(private_key)
        if transaction.verify_transaction(self.bank):
            self.pending_transactions.append(transaction)
            self.transactions_count += 1
            return transaction
        else:
            raise Exception('Transaction has not been added.')

    def calculate_bank(self, bank, sender, receiver, amount):
        bank[sender] -= amount
        bank[receiver] += amount
        return bank

    def blockchain_bank(self, bank, from_block_index=0):
        bank_block_count = from_block_index
        for block in self.chain[from_block_index:]:
            for transaction in block.transactions.split(';'):
                args = transaction.split(',')
                bank = self.calculate_bank(bank,
                                           args[1], args[2], float(args[3]))
            bank_block_count += 1
        return bank, bank_block_count

    def mine(self, miner):
        try:
            _ = txt2pk(miner)
        except Exception as e:
            print(f'{miner} is a wrong direction: {e}')
            raise e
        if len(self.pending_transactions) < 1:
            raise Exception('Not enough transactions. '
                            'There has to be 1 or more.')
        else:
            bank = defaultdict(float)
            bank_block_count = 0
            bank, bank_block_count = \
                self.blockchain_bank(bank, bank_block_count)
            transactions = []
            pending_transactions = self.pending_transactions.copy()
            for transaction in pending_transactions:
                if transaction.verify_transaction(bank):
                    transactions.append(transaction)
                    bank = self.calculate_bank(bank,
                                               transaction.sender,
                                               transaction.receiver,
                                               transaction.amount)
                _ = self.pending_transactions.pop(0)
                if len(transactions) == self.max_block_transactions - 1:
                    break
            if len(transactions) == 0:
                raise Exception('No valid transactions found.')
            last_index = transaction.index
            date = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
            miner_reward = self.sum_coef * self.sum_ratio ** len(self.chain) 
            reward_transaction = Transaction(last_index + 1, 'MineReward',
                                             miner, miner_reward, date)
            reward_transaction.signature = '0' * 128
            transactions.append(reward_transaction)
            self.transactions_count += 1
            bank = self.calculate_bank(bank, 'MineReward',
                                       miner, miner_reward)
            previous_hash = self.chain[-1].hash
            block = Block(len(self.chain), previous_hash, transactions, date,
                          self.sum_ratio, self.sum_coef)
            block.mine(self.difficulty)
            self.chain.append(block)
            bank_block_count += 1
            self.bank = bank
            self.bank_block_count = bank_block_count
            self.block_count = len(self.chain)
            return block, bank, bank_block_count, len(self.chain)

    def verify_chain(self):
        block = self.chain[0]
        prev_hash = block.hash
        if prev_hash[:self.difficulty] != '0' * self.difficulty:
            raise Exception('Block 0 invalid hash.')
        caclulated_hash = block.calculate_hash()
        if prev_hash != caclulated_hash:
            raise Exception('Block 0 hash differs from the calculated:\n'
                            f'Registered hash: {prev_hash}\n'
                            f'Calculated hash: {caclulated_hash}')

        for block in self.chain[1:]:
            hash_ = block.hash
            if hash_[:self.difficulty] != '0' * self.difficulty:
                raise Exception(f'Block {block.index} invalid hash.')
            if block.previous_hash != prev_hash:
                raise Exception(f'Block {block.index} previoius hash its '
                                f'different from the {block.index - 1} hash.')
            caclulated_hash = block.calculate_hash()
            if hash_ != caclulated_hash:
                raise Exception(f'Block {block.index} hash differs from the '
                                'calculated:\n'
                                f'Registered hash: {hash_}\n'
                                f'Calculated hash: {caclulated_hash}')
            miner_rewards = 0
            for transaction in block.transactions.split(';'):
                t = transaction.split(',')
                if t[1] == 'MineReward':
                    miner_rewards += float(t[3])
            if miner_rewards != self.sum_coef * self.sum_ratio ** block.index:
                raise Exception('In block' + block.index + 'there is a fraudulent '
                                'miner reward.')
            prev_hash = hash_
        return True

    def ledger_book(self):
        ledger_book = pd.DataFrame(columns=['id', 'Block_id', 'Sender',
                                            'Receiver', 'Amount', 'Date',
                                            'Signature'])
        for block in self.chain:
            n_block = block.index
            for transaction in block.transactions.split(';'):
                t = transaction.split(',')
                ledger_book = ledger_book.append(
                    {'id': int(t[0]),
                     'Block_id': int(n_block),
                     'Sender': t[1],
                     'Receiver': t[2],
                     'Amount': float(t[3]),
                     'Date': pd.to_datetime(t[4]+t[5],
                                            format="%m/%d/%Y %H:%M:%S"),
                     'Signature': t[6]},
                    ignore_index=True
                )
        return ledger_book

    def print_blocks(self):
        chain = pd.DataFrame(columns=['Block_id', 'PrevHash', 'Hash', 'Nonse',
                                      'Transactions', 'Date', 'MinerReward'])
        for block in self.chain:
            chain = chain.append(
                {'Block_id': block.index,
                 'PrevHash': block.previous_hash,
                 'Hash': block.hash,
                 'Nonse': block.nonse,
                 'Transactions': block.transactions,
                 'Date': pd.to_datetime(block.datetime,
                                        format="%m/%d/%Y, %H:%M:%S"),
                 'MinerReward': block.miner_reward},
                ignore_index=True
            )
        return chain

    def save_chain(self):
        with open('chain.pickle', 'wb') as f:
            pickle.dump(self.__dict__, f, protocol=pickle.HIGHEST_PROTOCOL)

    def load_chain(self, Blockchain=None):
        if not Blockchain:
            with open('chain.pickle', 'rb') as f:
                self.__dict__ = pickle.load(f)
        else:
            self.__dict__ = pickle.loads(Blockchain)

        self.verify_chain()


class Block:
    def __init__(self, index, previous_hash, transactions, datetime, 
                 sum_ratio, sum_coef):
        self.index = index
        self.miner_reward = sum_coef * sum_ratio ** index 
        self.datetime = datetime
        self.transactions = ';'.join([t.msg + ',' + t.signature
                                     for t in transactions])
        self.hash = None
        self.previous_hash = previous_hash
        self.nonse = -1

    def calculate_hash(self):
        msg = ';'.join([str(self.index),
                        str(self.datetime),
                        str(self.previous_hash),
                        str(self.nonse),
                        str(self.transactions)])
        sha256 = hashes.Hash(hashes.SHA256())
        sha256.update(msg.encode())
        return sha256.finalize().hex()

    def mine(self, difficulty):
        self.hash = self.calculate_hash()
        while self.hash[:difficulty] != '0' * difficulty:
            self.nonse += 1
            self.hash = self.calculate_hash()


class Transaction:
    def __init__(self, index, sender, receiver, amount, date):
        self.index = index
        self.sender = sender
        self.receiver = receiver
        self.amount = float(amount)
        self.date = date
        self.msg = ','.join([str(index),
                             str(sender),
                             str(receiver),
                             str(amount),
                             str(date)])
        self.signature = None

    def sign(self, private_key):
        self.signature = private_key.sign(
            self.msg.encode(), 
            ec.ECDSA(hashes.SHA256())
            ).hex()

    def verify_sign(self):
        if self.signature is None:
            raise Exception(f'Transaction {self.index} not signed.')
        try:
            sender = txt2pk(self.sender)
            sender.verify(
                bytes.fromhex(self.signature),
                self.msg.encode(),
                ec.ECDSA(hashes.SHA256())
                )
            return True
        except Exception:
            return False

    def verify_transaction(self, bank):
        
        if self.sender == 'MineReward' or self.receiver == 'MineReward':
            print(f'Transaction {self.index} error. '
                  'MineReward is not a valid direction.')
            return False
        elif self.sender not in bank.keys():
            print(f'Transaction {self.index} error. '
                  f'Sender account {self.sender} does not exist.')
            return False
        elif not self.verify_sign():
            print(f'Transaction {self.index} error. '
                  'Signature verification failed.')
            return False
        elif self.sender == self.receiver:
            print(f'Transaction {self.index} error. '
                  'Sender and reiceiver directions are the same.')
            return False
        elif not any([isinstance(self.amount, int),
                      isinstance(self.amount, float)]):
            print(f'Transaction {self.index} error. '
                  'Transaction amount has to be int or float.')
            return False
        elif float(self.amount) <= 0:
            print(f'Transaction {self.index} error. '
                  'Transaction amount has to be positive.')
            return False
        elif self.amount > bank[self.sender]:
            print(f'Transaction {self.index} error. '
                  f'Limit amount exceeded. {self.sender} ' +
                  f'has only {bank[self.sender]} coins ' +
                  f'and is triying to send {self.amount}')
            return False
        elif not txt2pk(self.receiver):
            print('Transaction {self.index} error. Invalid receiver direction.')
            return False
        else:
            try:
                _ = txt2pk(self.receiver)
            except Exception as e:
                print(f'Transaction {self.index} error. '
                      f'{self.receiver} is a wrong receiver direction: {e}')
                return False
            return True


def generate_keys(name, password=None):
    key = ec.generate_private_key(ec.SECP256K1())
    if password:
        sk = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=\
                serialization.BestAvailableEncryption(password.encode())
        )
    else:
        sk = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

    pk = key.public_key()
    pk = pk.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with open(name + '.txt', 'wb') as f:
        f.write(pk)
        f.write(b'\n\n')
        f.write(sk)
    return sk, pk

def load_keys(file, password=None):

    with open(file, 'rb') as f:
        lines = f.readlines()
    pk = b''.join(lines[0:4])
    sk = b''.join(lines[6:])

    pk = serialization.load_pem_public_key(pk)

    if password:
        sk = serialization.load_pem_private_key(
            sk,
            password=password.encode()
        )
    else:
        sk = serialization.load_pem_private_key(
            sk,
            password=None
        )
    return pk, sk

def pk2txt(pk):
    txt = pk.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode().splitlines()[1:-1]
    return ''.join(txt)

def txt2pk(txt):
    pk = f'-----BEGIN PUBLIC KEY-----\n{txt[:64]}\n{txt[64:]}\n'\
        '-----END PUBLIC KEY-----'.encode()
    try:
        pk = serialization.load_pem_public_key(pk)
    except:
        print(f"Error. Couldn't load the public key: {pk}")
        pk = False
    return pk

def load_transaction(txt):
    t = txt.split(',')
    t = {
        'id': int(t[0]),
        'Sender': t[1],
        'Receiver': t[2],
        'Amount': float(t[3]),
        'Date': pd.to_datetime(f'{t[4]} {t[5]}',
                            format="%m/%d/%Y %H:%M:%S"),
        'Signature': t[6]
        }
    transaction = Transaction(
        t['id'],
        t['Sender'],
        t['Receiver'],
        t['Amount'],
        t['Date'].strftime("%m/%d/%Y, %H:%M:%S")
        )
    transaction.signature = t['Signature']
    return transaction