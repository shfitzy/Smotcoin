""" Provides verification helper methods. """

from utility.hash_util import hash_block, hash_string_256
from wallet import Wallet


class Verification:

    DIFFICULTY = 4

    @staticmethod
    def valid_proof(transactions, last_hash, proof):
        guess = (str([tx.to_ordered_dict() for tx in transactions]) + str(last_hash) + str(proof)).encode()
        guess_hash = hash_string_256(guess)
        return guess_hash[0:Verification.DIFFICULTY] == ('0' * Verification.DIFFICULTY)

    @classmethod
    def verify_chain(cls, blockchain):
        """ Verify the current blockchain and return True if it's valid, False otherwise. """
        for index in range(1, len(blockchain)):
            block = blockchain[index]
            if block.previous_hash != hash_block(blockchain[index - 1]):
                print('Previous hash does not match.')
                return False
            if not cls.valid_proof(block.transactions[:-1], block.previous_hash, block.proof):
                print('Proof of work is invalid.')
                return False

        return True

    @staticmethod
    def verify_transaction(transaction, get_balance, check_funds=True):
        return (not check_funds or get_balance(transaction.sender) >= transaction.amount) and Wallet.verify_transaction(transaction)

    @classmethod
    def verify_transactions(cls, open_transactions, get_balance):
        return all([cls.verify_transaction(tx, get_balance, False) for tx in open_transactions])
