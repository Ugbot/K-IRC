"""Cryptography utilities for K-IRC."""

import base64
from pathlib import Path
from typing import Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def generate_key_pair() -> Tuple[bytes, bytes]:
    """Generate a new RSA key pair.
    
    Returns:
        Tuple[bytes, bytes]: (private_key_pem, public_key_pem)
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_pem, public_pem


def encrypt_message(public_key_pem: bytes, message: bytes) -> bytes:
    """Encrypt a message using a public key.
    
    Args:
        public_key_pem: The recipient's public key in PEM format.
        message: The message to encrypt.
        
    Returns:
        bytes: The encrypted message.
    """
    public_key = serialization.load_pem_public_key(public_key_pem)
    
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValueError("Invalid public key type")

    ciphertext = public_key.encrypt(
        message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return ciphertext


def decrypt_message(private_key_pem: bytes, ciphertext: bytes) -> bytes:
    """Decrypt a message using a private key.
    
    Args:
        private_key_pem: The recipient's private key in PEM format.
        ciphertext: The encrypted message.
        
    Returns:
        bytes: The decrypted message.
    """
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise ValueError("Invalid private key type")

    plaintext = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return plaintext


def save_key_to_file(key_pem: bytes, path: str) -> None:
    """Save a key to a file."""
    Path(path).write_bytes(key_pem)


def load_key_from_file(path: str) -> bytes:
    """Load a key from a file."""
    return Path(path).read_bytes()


from cryptography.fernet import Fernet

def generate_symmetric_key() -> bytes:
    """Generate a symmetric key (Fernet)."""
    return Fernet.generate_key()


def encrypt_symmetric(key: bytes, message: str) -> bytes:
    """Encrypt a string message using a symmetric key."""
    f = Fernet(key)
    return f.encrypt(message.encode())


def decrypt_symmetric(key: bytes, ciphertext: bytes) -> str:
    """Decrypt a message using a symmetric key."""
    f = Fernet(key)
    return f.decrypt(ciphertext).decode()
