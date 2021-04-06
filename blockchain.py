from functools import reduce
from json import dumps, loads
import pickle
import requests

from block import Block
from transaction import Transaction
from utility.hash_util import hash_block
from utility.verification import Verification
from wallet import Wallet


class Blockchain:

    MINING_REWARD_SENDER = 'MINING REWARD'
    MINING_REWARD = 10

    def __init__(self, public_key, node_id):
        genesis_block = Block(0, '', [], 100, 0)
        self.__chain = [genesis_block]
        self.__open_transactions = []
        self.__peer_nodes = set()
        self.public_key = public_key
        self.node_id = node_id
        self.resolve_conflicts = False
        self.load_data()

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
            try:
                with open('blockchain-{}.p'.format(self.node_id), mode='rb') as file:
                    file_content = pickle.loads(file.read())
                    self.__chain = file_content['chain']
                    self.__open_transactions = file_content['ot']
            except (IOError, IndexError):
                print('File not found!')
        else:
            try:
                with open('blockchain-{}.txt'.format(self.node_id), mode='r') as file:
                    file_content = file.readlines()
                    blockchain = loads(file_content[0][:-1])
                    updated_blockchain = []
                    for block in blockchain:
                        transactions = [Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in
                                        block['transactions']]
                        updated_block = Block(block['index'], block['previous_hash'], transactions, block['proof'],
                                              block['timestamp'])
                        updated_blockchain.append(updated_block)
                    self.__chain = updated_blockchain
                    open_transactions = loads(file_content[1][:-1])
                    updated_open_transactions = []
                    for tx in open_transactions:
                        updated_transaction = Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount'])
                        updated_open_transactions.append(updated_transaction)
                    self.__open_transactions = updated_open_transactions
                    self.__peer_nodes = set(loads(file_content[2]))
            except (IOError, IndexError):
                print('File not found!')

    def save_data(self):
        with open('blockchain-{}.p'.format(self.node_id), mode='wb') as file:
            data = {
                'chain': self.__chain,
                'ot': self.__open_transactions
            }
            file.write(pickle.dumps(data))
        with open('blockchain-{}.txt'.format(self.node_id), mode='w') as file:
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
            file.write('\n')
            file.write(dumps(list(self.__peer_nodes)))

    def proof_of_work(self):
        last_block = self.__chain[-1]
        last_hash = hash_block(last_block)
        proof = 0
        while not Verification.valid_proof(self.__open_transactions, last_hash, proof):
            proof += 1
        return proof

    def get_balance(self, sender=None):
        """ Calculates the balance for a blockchain participant.

        :return: The current balance for the participant.
        """
        if sender is None:
            if self.public_key is None:
                return None
            participant = self.public_key
        else:
            participant = sender

        user_transactions = [[tx.amount * -1 for tx in block.transactions if tx.sender == participant] for block in self.__chain]
        user_transactions.extend(
            [[tx.amount for tx in block.transactions if tx.recipient == participant] for block in self.__chain])
        user_transactions.append([tx.amount * -1 for tx in self.__open_transactions if tx.sender == participant])

        return reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum, user_transactions, 0)

    def get_last_blockchain_value(self):
        """ Returns the last value of the current blockchain. """
        return None if not self.__chain else self.__chain[-1]

    def add_transaction(self, recipient, sender, signature, amount=1.0, is_receiving=False):
        """ Append a new value as well as the last blockchain value to the blockchain.

        Arguments:
            sender: The sender of the coins.
            recipient: The recipient of the coins.
            signature: The signature of the payload, constructed via a private key.
            amount: The amount of coins sent with the transaction (default = 1.0).
            is_receiving: A boolean to determine whether or not this is an incoming request from another node.
        """
        # if self.public_key is None:
        #     return False

        transaction = Transaction(sender, recipient, signature, amount)
        if Verification.verify_transaction(transaction, self.get_balance):
            self.__open_transactions.append(transaction)
            self.save_data()

            if not is_receiving:
                for node in self.__peer_nodes:
                    url = 'http://{}/broadcast_transaction'.format(node)
                    try:
                        response = requests.post(url, json={'sender': sender, 'recipient': recipient, 'amount': amount, 'signature': signature})
                        if response.status_code == 400 or response.status_code == 500:
                            print('Transaction declined, needs resolving.')
                            return False
                    except requests.exceptions.ConnectionError:
                        continue

            return True
        else:
            return False

    def mine_block(self):
        if self.public_key is None:
            return None

        hashed_block = hash_block(self.__chain[-1])
        proof = self.proof_of_work()

        reward_transaction = Transaction(Blockchain.MINING_REWARD_SENDER, self.public_key, '', Blockchain.MINING_REWARD)
        copied_transactions = self.__open_transactions[:]

        for tx in copied_transactions:
            if not Wallet.verify_transaction(tx):
                return None

        copied_transactions.append(reward_transaction)
        block = Block(len(self.__chain), hashed_block, copied_transactions, proof)

        self.__chain.append(block)
        self.__open_transactions = []
        self.save_data()
        for node in self.__peer_nodes:
            url = 'http://{}/broadcast-block'.format(node)
            converted_block = block.__dict__.copy()
            converted_block['transactions'] = [tx.__dict__ for tx in converted_block['transactions']]
            try:
                response = requests.post(url, json={'block': converted_block})
                if response.status_code == 400 or response.status_code == 500:
                    print('Block declined, needs resolving.')
                if response.status_code == 409:
                    self.resolve_conflicts = True
            except requests.exceptions.ConnectionError:
                continue

        return block

    def add_block(self, block):
        transactions = [Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transactions']]
        # Excluding the last transaction, because that is the "reward" transaction
        valid_proof = Verification.valid_proof(transactions[:-1], block['previous_hash'], block['proof'])
        hashes_match = hash_block(self.chain[-1]) == block['previous_hash']
        if not valid_proof or not hashes_match:
            return False

        converted_block = Block(block['index'], block['previous_hash'], transactions, block['proof'], block['timestamp'])
        self.__chain.append(converted_block)
        stored_transactions = self.__open_transactions[:]
        for itx in block['transactions']:
            for opentx in stored_transactions:
                if opentx.sender == itx['sender'] and opentx.recipient == itx['recipient'] and opentx.amount == itx['amount'] and opentx.signature == itx['signature']:
                    try:
                        self.__open_transactions.remove(opentx)
                    except ValueError:
                        print('Item was already removed')
        self.save_data()
        return True

    def resolve(self):
        winner_chain = self.chain
        replace = False

        for node in self.__peer_nodes:
            url = 'http://{}/chain'.format(node)
            try:
                response = requests.get(url)
                node_chain = response.json()
                node_chain = [Block(block['index'], block['previous_hash'], [Transaction(tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transactions']], block['proof'], block['timestamp']) for block in node_chain]
                node_chain_length = len(node_chain)
                local_chain_length = len(self.chain)
                if node_chain_length > local_chain_length and Verification.verify_chain(node_chain):
                    winner_chain = node_chain
                    replace = True
            except requests.exceptions.ConnectionError:
                continue

        self.resolve_conflicts = False
        self.__chain = winner_chain
        if replace:
            self.__open_transactions = []
        self.save_data()
        return replace

    def add_peer_node(self, node):
        """ Adds a new node to the peer node set.

        Arguments:
            node: The node URL which should be added.
        """
        self.__peer_nodes.add(node)
        self.save_data()

    def remove_peer_node(self, node):
        """ Removes a new node to the peer node set.

        Arguments:
            node: The node URL which should be removed.
        """
        self.__peer_nodes.discard(node)
        self.save_data()

    def get_peer_nodes(self):
        """ Return a list of all connected peer nodes. """
        return list(self.__peer_nodes)
