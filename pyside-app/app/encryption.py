"""AES-256-GCM encryption for Orbit config files."""
from __future__ import annotations

import hashlib
import json
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

_ITERATIONS = 200_000
_KEY_LEN = 32  # 256-bit

# ── Key derivation ─────────────────────────────────────────────────────────────

def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LEN,
        salt=salt,
        iterations=_ITERATIONS,
    )
    return kdf.derive(password.encode('utf-8'))


# ── Core encrypt / decrypt ─────────────────────────────────────────────────────

def encrypt_data(plaintext: str, password: str) -> bytes:
    """Encrypt a JSON string → opaque bytes blob.

    Format: version(1) + salt(16) + nonce(12) + ciphertext+tag
    """
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    return b'\x01' + salt + nonce + ct


def decrypt_data(blob: bytes, password: str) -> str:
    """Decrypt opaque bytes blob → JSON string.

    Raises ValueError on wrong password or corrupted data.
    """
    if blob[0:1] != b'\x01':
        raise ValueError('Unknown encryption version')
    salt = blob[1:17]
    nonce = blob[17:29]
    ct = blob[29:]
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    try:
        plain = aesgcm.decrypt(nonce, ct, None)
        return plain.decode('utf-8')
    except Exception:
        raise ValueError('Wrong master password or corrupted data')


# ── File helpers ───────────────────────────────────────────────────────────────

def is_encrypted(path: str) -> bool:
    """Check if a file is encrypted by inspecting the magic byte."""
    try:
        with open(path, 'rb') as f:
            return f.read(1) == b'\x01'
    except Exception:
        return False


def encrypt_file(path: str, password: str) -> None:
    """Encrypt an existing plaintext file in-place."""
    with open(path, 'r', encoding='utf-8') as f:
        plaintext = f.read()
    blob = encrypt_data(plaintext, password)
    with open(path, 'wb') as f:
        f.write(blob)


def decrypt_file(path: str, password: str) -> str:
    """Read and decrypt an encrypted file, returning the plaintext string."""
    with open(path, 'rb') as f:
        blob = f.read()
    return decrypt_data(blob, password)


def read_json_file(path: str, password: Optional[str] = None) -> dict:
    """Read a file that may or may not be encrypted. Returns a dict.

    If password is None and the file is encrypted, raises ValueError.
    If the file does not exist, returns {}.
    """
    if not os.path.exists(path):
        return {}
    if is_encrypted(path):
        if not password:
            raise ValueError('File is encrypted but no password provided')
        text = decrypt_file(path, password)
    else:
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
    return json.loads(text)


def write_json_file(path: str, data, password: Optional[str] = None) -> None:
    """Write a dict/list to a file, encrypting it when a password is given."""
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if password:
        blob = encrypt_data(text, password)
        with open(path, 'wb') as f:
            f.write(blob)
    else:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)


# ── Session password store ─────────────────────────────────────────────────────

_SESSION_PASSWORD: Optional[str] = None


def set_session_password(password: str) -> None:
    global _SESSION_PASSWORD
    _SESSION_PASSWORD = password


def get_session_password() -> Optional[str]:
    return _SESSION_PASSWORD


def clear_session_password() -> None:
    global _SESSION_PASSWORD
    _SESSION_PASSWORD = None


# ── Password hash helpers ──────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Return a SHA-256 hex digest of the password (for verification storage)."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password_hash(password: str, stored_hash: str) -> bool:
    return hash_password(password) == stored_hash
