"""MultiFernet encryption service for Pikar-AI admin panel.

Provides encrypt/decrypt helpers backed by ``cryptography.fernet.MultiFernet``
for API key storage and other secrets.  Key rotation is supported from day one
via a comma-separated ``ADMIN_ENCRYPTION_KEY`` environment variable.

Key rotation pattern
--------------------
To rotate keys:

1. Generate a new Fernet key::

       python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

2. Prepend the new key to ``ADMIN_ENCRYPTION_KEY``, keeping the old key as a
   fallback::

       ADMIN_ENCRYPTION_KEY=new_key,old_key

3. ``MultiFernet`` will use the first key for all new encryptions and will
   try all keys when decrypting, so existing ciphertexts remain readable.

4. Once all data has been re-encrypted with the new key, remove the old key.
"""

import logging
import os

from cryptography.fernet import Fernet, MultiFernet

logger = logging.getLogger(__name__)


def _get_fernet() -> MultiFernet:
    """Build a MultiFernet instance from the ``ADMIN_ENCRYPTION_KEY`` env var.

    Returns:
        A ``MultiFernet`` wrapping one or more Fernet instances.  The first
        key in the comma-separated list is the primary (used for encryption);
        the rest are fallback keys for decryption.

    Raises:
        RuntimeError: ``ADMIN_ENCRYPTION_KEY`` is not set or is empty.
    """
    raw = os.environ.get("ADMIN_ENCRYPTION_KEY", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise RuntimeError(
            "ADMIN_ENCRYPTION_KEY environment variable is not set. "
            'Generate a key with: python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    fernets = [Fernet(k.encode() if isinstance(k, str) else k) for k in keys]
    return MultiFernet(fernets)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext string with the current primary Fernet key.

    Each call produces a different ciphertext because Fernet uses a random IV
    (initialization vector) internally.

    Args:
        plaintext: The string to encrypt.

    Returns:
        Base64-encoded ciphertext (URL-safe, Fernet token format).

    Raises:
        RuntimeError: ``ADMIN_ENCRYPTION_KEY`` is not configured.
    """
    fernet = _get_fernet()
    token = fernet.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted ciphertext string.

    Tries all configured keys (primary first, then fallbacks) so ciphertexts
    encrypted with a rotated-out key remain decryptable as long as the old key
    is still present in ``ADMIN_ENCRYPTION_KEY``.

    Args:
        ciphertext: Base64-encoded Fernet token produced by :func:`encrypt_secret`.

    Returns:
        The original plaintext string.

    Raises:
        RuntimeError: ``ADMIN_ENCRYPTION_KEY`` is not configured.
        cryptography.fernet.InvalidToken: The ciphertext is invalid or was
            encrypted with an unknown key.
    """
    fernet = _get_fernet()
    plaintext_bytes = fernet.decrypt(ciphertext.encode("utf-8"))
    return plaintext_bytes.decode("utf-8")
