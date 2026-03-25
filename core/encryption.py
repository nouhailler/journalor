"""AES-256-GCM encryption with PBKDF2 key derivation."""

import os
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from utils.constants import PBKDF2_ITERATIONS, SALT_SIZE


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte AES key from password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def hash_pin(pin: str, salt: bytes) -> str:
    """Hash a PIN for storage verification."""
    key = derive_key(pin, salt)
    return base64.b64encode(key).decode("utf-8")


def generate_salt() -> bytes:
    return os.urandom(SALT_SIZE)


class EncryptionManager:
    """Handles encryption/decryption of journal entry content."""

    def __init__(self):
        self._key: bytes | None = None

    def is_unlocked(self) -> bool:
        return self._key is not None

    def unlock(self, password: str, salt: bytes) -> None:
        self._key = derive_key(password, salt)

    def lock(self) -> None:
        self._key = None

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt text, return nonce+ciphertext as bytes."""
        if not self._key:
            raise RuntimeError("EncryptionManager is locked.")
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext)

    def decrypt(self, data: bytes) -> str:
        """Decrypt bytes back to plaintext string."""
        if not self._key:
            raise RuntimeError("EncryptionManager is locked.")
        raw = base64.b64decode(data)
        nonce = raw[:12]
        ciphertext = raw[12:]
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
