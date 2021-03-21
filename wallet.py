from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import Crypto.Random
import binascii


class Wallet:

    def __init__(self):
        self.private_key, self.public_key = None, None

    def create_keys(self):
        self.private_key, self.public_key = self.generate_keys()

    def save_keys(self):
        if self.public_key is not None and self.private_key is not None:
            try:
                with open('wallet.txt', mode='w') as f:
                    f.write(self.public_key + "\n" + self.private_key)
                    return True
            except (IOError, IndexError):
                print('Saving wallet failed...')

        return False

    def load_keys(self):
        with open('wallet.txt', mode='r') as f:
            try:
                keys = f.readlines()
                self.public_key, self.private_key = keys[0][:-1], keys[1]
            except (IOError, IndexError):
                print('Loading wallet failed...')

    @staticmethod
    def generate_keys():
        private_key = RSA.generate(1024, Crypto.Random.new().read)
        public_key = private_key.publickey()
        return binascii.hexlify(private_key.exportKey(format='DER')).decode('ascii'), binascii.hexlify(public_key.exportKey(format='DER')).decode('ascii')

    def sign_transaction(self, sender, recipient, amount):
        signer = PKCS1_v1_5.new(RSA.importKey(binascii.unhexlify(self.private_key)))
        h = SHA256.new((str(sender) + str(recipient) + str(amount)).encode('utf8'))
        signature = signer.sign(h)
        return binascii.hexlify(signature).decode('ascii')

    @staticmethod
    def verify_transaction(transaction):
        public_key = RSA.importKey(binascii.unhexlify(transaction.sender))
        verifier = PKCS1_v1_5.new(public_key)
        h = SHA256.new((str(transaction.sender) + str(transaction.recipient) + str(transaction.amount)).encode('utf8'))
        return verifier.verify(h, binascii.unhexlify(transaction.signature))
