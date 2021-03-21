from functools import reduce
from json import dumps, loads
import pickle

from hash_util import hash_block
from block import Block
from transaction import Transaction
from verification import Verification

MINING_REWARD = 10


class Blockchain:

    def __init__(self, hosting_node_id):
        genesis_block = Block(0, '', [], 100, 0)
        self.__chain = [genesis_block]
        self.__open_transactions = []
        self.load_data()
        self.hosting_node = hosting_node_id

    @property
    def chain(self):
        return self.__chain[:]

    @chain.setter
    def chain(self, val):
        pass

    @property
    def open_transactions(self):
        return self.__open_transactions[:]

    @open_transactions.setter
    def open_transactions(self, val):
        pass

    def load_data(self, use_pickle=False):
        if use_pickle:
            with open('blockchain.p', mode='rb') as file:
                file_content = pickle.loads(file.read())
                self.__chain = file_content['chain']
                self.__open_transactions = file_content['ot']
        else:
            try:
                with open('blockchain.txt', mode='r') as file:
                    file_content = file.readlines()
                    blockchain = loads(file_content[0][:-1])
                    updated_blockchain = []
                    for block in blockchain:
                        transactions = [Transaction(tx['sender'], tx['recipient'], tx['amount']) for tx in
                                        block['transactions']]
                        updated_block = Block(block['index'], block['previous_hash'], transactions, block['proof'],
                                              block['timestamp'])
                        updated_blockchain.append(updated_block)
                    self.__chain = updated_blockchain
                    open_transactions = loads(file_content[1])
                    updated_open_transactions = []
                    for tx in open_transactions:
                        updated_transaction = Transaction(tx['sender'], tx['recipient'], tx['amount'])
                        updated_open_transactions.append(updated_transaction)
                    self.__open_transactions = updated_open_transactions
            except (IOError, IndexError):
                print('File not found!')

    def save_data(self):
        with open('blockchain.p', mode='wb') as file:
            data = {
                'chain': self.__chain,
                'ot': self.__open_transactions
            }
            file.write(pickle.dumps(data))
        with open('blockchain.txt', mode='w') as file:
            savable_chain = [
                block.__dict__ for block in [
                    Block(block_el.index, block_el.previous_hash, [
                        tx.__dict__ for tx in block_el.transactions
                    ], block_el.proof, block_el.timestamp) for block_el in self.__chain
                ]
            ]
            file.write(dumps(savable_chain))
            file.write('\n')
            savable_open_transactions = [tx.__dict__ for tx in self.__open_transactions]
            file.write(dumps(savable_open_transactions))

    def proof_of_work(self):
        last_block = self.__chain[-1]
        last_hash = hash_block(last_block)
        proof = 0
        while not Verification.valid_proof(self.__open_transactions, last_hash, proof):
            proof += 1
        return proof

    def get_balance(self):
        """ Calculates the balance for a blockchain participant.

        :return: The current balance for the participant.
        """
        participant = self.hosting_node
        user_transactions = [[tx.amount * -1 for tx in block.transactions if tx.sender == participant] for block in self.__chain]
        user_transactions.extend(
            [[tx.amount for tx in block.transactions if tx.recipient == participant] for block in self.__chain])
        user_transactions.append([tx.amount * -1 for tx in self.__open_transactions if tx.sender == participant])

        return reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum, user_transactions, 0)

    def get_last_blockchain_value(self):
        """ Returns the last value of the current blockchain. """
        return None if not self.__chain else self.__chain[-1]

    def add_transaction(self, recipient, sender, amount=1.0):
        """ Append a new value as well as the last blockchain value to the blockchain.

        Arguments:
            sender: The sender of the coins.
            recipient: The recipient of the coins.
            amount: The amount of coins sent with the transaction (default = 1.0).
        """
        transaction = Transaction(sender, recipient, amount)
        if Verification.verify_transaction(transaction, self.get_balance):
            self.__open_transactions.append(transaction)
            self.save_data()
            return True
        else:
            return False

    def mine_block(self):
        hashed_block = hash_block(self.__chain[-1])
        proof = self.proof_of_work()

        reward_transaction = Transaction('MINING REWARD', self.hosting_node, MINING_REWARD)
        copied_transactions = self.__open_transactions[:]
        copied_transactions.append(reward_transaction)

        block = Block(len(self.__chain), hashed_block, copied_transactions, proof)
        self.__chain.append(block)
        self.__open_transactions = []
        self.save_data()
