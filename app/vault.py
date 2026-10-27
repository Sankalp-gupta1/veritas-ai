"""Authenticated encryption at rest. This is NOT end-to-end encryption.

The runtime owns the key and decrypts records to do research. Row/field identities
are authenticated as associated data, so ciphertext cannot be moved between rows.
Missing or invalid keys fail closed. There is no plaintext write fallback.
"""

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def master_key():
    value = os.getenv("VERITAS_VAULT_KEY", "")
    try:
        key = base64.b64decode(value, validate=True)
    except Exception as error:
        raise RuntimeError("The vault is not configured") from error
    if len(key) != 32:
        raise RuntimeError("The vault is not configured")
    return key


def configured():
    try:
        master_key()
        return True
    except RuntimeError:
        return False


def fingerprint(value, purpose):
    return hmac.new(master_key(), f"{purpose}\0{value}".encode(), hashlib.sha256).hexdigest()


def seal(data: bytes, identity: str) -> bytes:
    nonce = os.urandom(12)
    return b"VAI1" + nonce + AESGCM(master_key()).encrypt(nonce, data, identity.encode())


def unseal(data: bytes, identity: str) -> bytes:
    data = bytes(data)
    if not data.startswith(b"VAI1") or len(data) < 32:
        raise ValueError("Invalid encrypted record")
    return AESGCM(master_key()).decrypt(data[4:16], data[16:], identity.encode())


def seal_text(value: str, identity: str) -> str:
    return base64.b64encode(seal(value.encode(), identity)).decode()


def unseal_text(value: str, identity: str) -> str:
    return unseal(base64.b64decode(value, validate=True), identity).decode()
