# To do list:
#   - Variable difficulty
#   - Tor network for Transactions
#   - External network
#   - Cool html interface?

import ecdsa
from hashlib import sha256
import datetime
from collections import defaultdict
import pandas as pd
import pickle


class Blockchain:
    def __init__(self):
        self.miner_reward = 50
        self.difficulty = 4
        self.max_block_transactions = 100
        self.transactions_count = 0
        self.block_count = 0
        self.bank = defaultdict(float)
        self.bank_block_count = 0
        self.chain = [self.GenesisBlock()]
        self.pending_transactions = []

    def GenesisBlock(self):
        pk = 'dba49f4be76fd812fe408e3aad1df29c5e3d17357daac91f8a5bc5be71686fc'\
            'b210fd8cee191486d2cbcb3160cfee5a7dbb2b5b5d923d6c79547a23d618ab261'
        date = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        initial_amount = 20
        first_transaction = Transaction(0, 'MineReward', pk,
                                        initial_amount, date)
        first_transaction.signature = '0' * 128
        genesis_block = Block(0, '0' * 64, [first_transaction], date)
        genesis_block.mine(self.difficulty)
        self.transactions_count += 1
        self.block_count += 1
        self.bank[pk] = 20
        return genesis_block

    def add_transaction(self, sender, receiver, amount, private_key):
        index = self.transactions_count
        date = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        transaction = Transaction(index, sender, receiver, amount, date)
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
            reward_transaction = Transaction(last_index + 1, 'MineReward',
                                             miner, self.miner_reward, date)
            reward_transaction.signature = '0' * 128
            transactions.append(reward_transaction)
            self.transactions_count += 1
            bank = self.calculate_bank(bank, 'MineReward',
                                       miner, self.miner_reward)
            previous_hash = self.chain[-1].hash
            block = Block(len(self.chain), previous_hash, transactions, date)
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
            if miner_rewards != self.miner_reward:
                raise Exception('In block' + t[0] + 'there is a fraudulent '
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
                                      'Transactions', 'Date'])
        for block in self.chain:
            chain = chain.append(
                {'Block_id': block.index,
                 'PrevHash': block.previous_hash,
                 'Hash': block.hash,
                 'Nonse': block.nonse,
                 'Transactions': block.transactions,
                 'Date': pd.to_datetime(block.datetime,
                                        format="%m/%d/%Y, %H:%M:%S")},
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
    def __init__(self, index, previous_hash, transactions, datetime):
        self.index = index
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
        return sha256(msg.encode()).digest().hex()

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
        self.amount = amount
        self.date = date
        self.msg = ','.join([str(index),
                             str(sender),
                             str(receiver),
                             str(amount),
                             str(date)])
        self.signature = None

    def sign(self, private_key):
        key = ecdsa.SigningKey.from_string(bytes.fromhex(private_key),
                                           curve=ecdsa.SECP256k1,
                                           hashfunc=sha256)
        self.signature = key.sign(self.msg.encode(), hashfunc=sha256).hex()

    def verify_sign(self):
        if self.signature is None:
            raise Exception(f'Transaction {self.index} not signed.')
        public_key = self.sender
        key = ecdsa.VerifyingKey.from_string(bytes.fromhex(public_key),
                                             curve=ecdsa.SECP256k1,
                                             hashfunc=sha256)
        try:
            key.verify(bytes.fromhex(self.signature), self.msg.encode())
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
                  f'has only {bank[self.sender]} coins' +
                  f'and is triying to send {self.amount}')
            return False
        else:
            try:
                receiver = bytes.fromhex(self.receiver)
                _ = ecdsa.VerifyingKey.from_string(receiver,
                                                   curve=ecdsa.SECP256k1,
                                                   hashfunc=sha256)
            except Exception as e:
                print(f'Transaction {self.index} error. '
                      f'{self.receiver} is a wrong receiver direction: {e}')
                return False
            return True


def generate_keys(name):
    key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    sk = key.to_string().hex()
    pk = key.verifying_key.to_string().hex()
    with open(name + '.txt', 'w') as f:
        f.write(f'Public Key: {pk}')
        f.write('\n')
        f.write(f'Private Key: {sk}')
    return sk, pk
