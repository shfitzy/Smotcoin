from hashlib import sha256
from json import dumps


def hash_string_256(string):
    """ Hashes the given string using the SHA256 algorithm and returns the hexdigest of it.

    Arguments:
        string: The string to be hashed.
    """
    return sha256(string).hexdigest()


def hash_block(block):
    """ Hashes a block and returns a string representation of it.

    Arguments:
        block: The block that should be hashed.
    """
    hashable_block = block.__dict__.copy()
    hashable_block['transactions'] = [tx.to_ordered_dict() for tx in block.transactions]
    return hash_string_256(dumps(hashable_block, sort_keys=True).encode())
