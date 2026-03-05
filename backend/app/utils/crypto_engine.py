"""
AES-256-GCM helpers and key management notes for PulseTrakAI™

This module provides lightweight AES-GCM helpers for application-level encryption.
Secrets MUST be provided via environment variables (production: Secrets Manager).

Note: This is a helper library for Stage 4 scaffolding. In production, keys
should be stored and rotated by a KMS-backed secrets manager. Do NOT commit
secrets to source control.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import os
from typing import Tuple

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:
    AESGCM = None  # cryptography not installed in this environment; file remains as scaffold


def _get_key() -> bytes:
    """Load AES key from environment variable `AESGCM_KEY` (base64 or raw bytes).

    Keys MUST be loaded from environment only. Do not store in repo.
    """
    k = os.environ.get('AESGCM_KEY')
    if not k:
        raise RuntimeError('AESGCM_KEY not configured in environment')
    # caller may store key as hex/base64; for scaffold we expect raw bytes in env
    return k.encode('utf-8')


def encrypt(plaintext: bytes, associated_data: bytes | None = None) -> Tuple[bytes, bytes]:
    """Encrypt plaintext using AES-256-GCM. Returns (nonce, ciphertext).

    This is a simple wrapper for Stage 4; use KMS-wrapped keys in production.
    """
    if AESGCM is None:
        raise RuntimeError('cryptography library not available')
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext, associated_data)
    return nonce, ct


def decrypt(nonce: bytes, ciphertext: bytes, associated_data: bytes | None = None) -> bytes:
    if AESGCM is None:
        raise RuntimeError('cryptography library not available')
    key = _get_key()
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data)


# Key rotation policy (operational):
# - Rotate AES keys every 90 days.
# - Maintain previous keys for a configurable grace period to decrypt existing data.
# - Use KMS to wrap/un-wrap keys and automate re-encryption flows.
