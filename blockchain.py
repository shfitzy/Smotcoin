from collections import OrderedDict
from functools import reduce
from json import dumps, loads
import pickle

from hash_util import hash_string_256, hash_block

MINING_REWARD = 10
DIFFICULTY = 2
# Initializing our blockchain list
genesis_block = {
    'previous_hash': '',
    'index': 0,
    'transactions': [],
    'proof': 100
}
blockchain = [genesis_block]
open_transactions = []
owner = 'Shane'
participants = {owner}


def load_data(use_pickle=False):
    global blockchain
    global open_transactions

    if use_pickle:
        with open('blockchain.p', mode='rb') as file:
            file_content = pickle.loads(file.read())
            blockchain = file_content['chain']
            open_transactions = file_content['ot']
    else:
        with open('blockchain.txt', mode='r') as file:
            file_content = file.readlines()
            blockchain = loads(file_content[0][:-1])
            updated_blockchain = []
            for block in blockchain:
                updated_block = {
                    'previous_hash': block['previous_hash'],
                    'index': block['index'],
                    'proof': block['proof'],
                    'transactions': [OrderedDict(
                        [('sender', tx['sender']), ('recipient', tx['recipient']), ('amount', tx['amount'])]
                    ) for tx in block['transactions']]
                }
                updated_blockchain.append(updated_block)
            blockchain = updated_blockchain
            open_transactions = loads(file_content[1])
            updated_open_transactions = []
            for transaction in open_transactions:
                updated_transaction = OrderedDict([('sender', transaction['sender']), ('recipient', transaction['recipient']), ('amount', transaction['amount'])])
                updated_open_transactions.append(updated_transaction)
            open_transactions = updated_open_transactions


def save_data():
    with open('blockchain.p', mode='wb') as file:
        save_data = {
            'chain': blockchain,
            'ot': open_transactions
        }
        file.write(pickle.dumps(save_data))
    with open('blockchain.txt', mode='w') as file:
        file.write(dumps(blockchain))
        file.write('\n')
        file.write(dumps(open_transactions))


load_data()


def valid_proof(transactions, last_hash, proof):
    guess = (str(transactions) + str(last_hash) + str(proof)).encode()
    guess_hash = hash_string_256(guess)
    return guess_hash[0:DIFFICULTY] == ('0' * DIFFICULTY)


def proof_of_work():
    last_block = blockchain[-1]
    last_hash = hash_block(last_block)
    proof = 0
    while not valid_proof(open_transactions, last_hash, proof):
        proof += 1
    return proof


def get_balance(user):
    user_transactions = [[tx['amount'] * -1 for tx in block['transactions'] if tx['sender'] == user] for block in blockchain]
    user_transactions.extend([[tx['amount'] for tx in block['transactions'] if tx['recipient'] == user] for block in blockchain])
    user_transactions.append([tx['amount'] * -1 for tx in open_transactions if tx['sender'] == user])

    return reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum, user_transactions, 0)


def get_last_blockchain_value():
    """ Returns the last value of the current blockchain. """
    return None if not blockchain else blockchain[-1]


def verify_transaction(transaction):
    sender_balance = get_balance(transaction['sender'])
    return sender_balance >= transaction['amount']


def add_transaction(recipient, sender=owner, amount=1.0):
    """ Append a new value as well as the last blockchain value to the blockchain.

    Arguments:
        sender: The sender of the coins.
        recipient: The recipient of the coins.
        amount: The amount of coins sent with the transaction (default = 1.0).
    """
    transaction = OrderedDict([('sender', sender), ('recipient', recipient), ('amount', amount)])
    if verify_transaction(transaction):
        open_transactions.append(transaction)
        participants.add(sender)
        participants.add(recipient)
        save_data()
        return True
    else:
        return False


def mine_block():
    hashed_block = hash_block(blockchain[-1])
    proof = proof_of_work()

    reward_transaction = OrderedDict([('sender', 'MINING REWARD'), ('recipient', owner), ('amount', MINING_REWARD)])
    copied_transactions = open_transactions[:]
    copied_transactions.append(reward_transaction)

    block = {
        'previous_hash': hashed_block,
        'index': len(blockchain),
        'transactions': copied_transactions,
        'proof': proof
    }
    blockchain.append(block)
    return True


def get_transaction_value():
    """ Returns the input of the user (a new transaction amount) as a float. """
    tx_recipient = input('Enter the recipient of the transaction: ')
    tx_amount = float(input('Your transaction amount please: '))
    return tx_recipient, tx_amount


def get_user_choice():
    return input('Your choice: ')


def print_blockchain_elements():
    for block in blockchain:
        print(block)


def verify_chain():
    """ Verify the current blockchain and return True if it's valid, False otherwise. """
    for index in range(1, len(blockchain)):
        block = blockchain[index]
        if block['previous_hash'] != hash_block(blockchain[index-1]):
            print('Previous hash does not match.')
            return False
        if not valid_proof(block['transactions'][:-1], block['previous_hash'], block['proof']):
            print('Proof of work is invalid.')
            return False

    return True


def verify_transactions():
    return all([verify_transaction(tx) for tx in open_transactions])


waiting_for_input = True

while waiting_for_input:
    print('Please choose')
    print('1: Add a new transaction value')
    print('2: Mine a new block')
    print('3: Output the blockchain blocks')
    print('4: Output participants')
    print('5: Check transaction validity')
    print('h: Manipulate the chain')
    print('v: Verify the chain')
    print('q: Quit')
    user_choice = get_user_choice()
    if user_choice == '1':
        tx_data = get_transaction_value()
        recipient, amount = tx_data
        if add_transaction(recipient, amount=amount):
            print('Added transaction!')
        else:
            print('Transaction failed!')
        print(open_transactions)
    elif user_choice == '2':
        if mine_block():
            open_transactions = []
            save_data()
    elif user_choice == '3':
        print_blockchain_elements()
    elif user_choice == '4':
        print(participants)
    elif user_choice == '5':
        if verify_transactions():
            print('All transactions are valid')
        else:
            print('There are invalid transactions')
    elif user_choice == 'h':
        if len(blockchain) > 0:
            blockchain[0] = {
                'previous_hash': '',
                'index': 0,
                'transactions': [{'sender': 'Chris', 'recipient': 'Max', 'amount': 100}]
            }
    elif user_choice == 'v':
        print(verify_chain())
    elif user_choice == 'q':
        waiting_for_input = False
    else:
        print('Input was invalid, please pick a value from the list!')

    if not verify_chain():
        print_blockchain_elements()
        print('Invalid blockchain!')
        break
    print('Balance of {}: {:6.2f}'.format(owner, get_balance(owner)))
else:
    print('User left!')

print('Done!')
