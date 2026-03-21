"""Unit tests for MultiFernet encryption service.

Tests encrypt/decrypt roundtrip, random IV, and key rotation support.
"""

import os
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# test_encrypt_decrypt_roundtrip
# ---------------------------------------------------------------------------


def test_encrypt_decrypt_roundtrip():
    """encrypt_secret followed by decrypt_secret returns the original plaintext."""
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key().decode()
    with patch.dict(os.environ, {"ADMIN_ENCRYPTION_KEY": test_key}):
        # Force re-import to pick up env var
        import importlib

        import app.services.encryption as enc_module

        importlib.reload(enc_module)

        ciphertext = enc_module.encrypt_secret("hello")
        result = enc_module.decrypt_secret(ciphertext)

    assert result == "hello"


# ---------------------------------------------------------------------------
# test_encrypt_different_outputs
# ---------------------------------------------------------------------------


def test_encrypt_different_outputs():
    """Two calls to encrypt_secret with the same input produce different ciphertexts (random IV)."""
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key().decode()
    with patch.dict(os.environ, {"ADMIN_ENCRYPTION_KEY": test_key}):
        import importlib

        import app.services.encryption as enc_module

        importlib.reload(enc_module)

        ct1 = enc_module.encrypt_secret("same")
        ct2 = enc_module.encrypt_secret("same")

    assert ct1 != ct2


# ---------------------------------------------------------------------------
# test_decrypt_with_rotated_key
# ---------------------------------------------------------------------------


def test_decrypt_with_rotated_key():
    """Data encrypted with old key can still be decrypted after key rotation (MultiFernet)."""
    from cryptography.fernet import Fernet

    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()

    import importlib

    import app.services.encryption as enc_module

    # Encrypt with only old_key
    with patch.dict(os.environ, {"ADMIN_ENCRYPTION_KEY": old_key}):
        importlib.reload(enc_module)
        ciphertext = enc_module.encrypt_secret("rotate-me")

    # Decrypt with new_key as primary, old_key as fallback (comma-separated)
    with patch.dict(os.environ, {"ADMIN_ENCRYPTION_KEY": f"{new_key},{old_key}"}):
        importlib.reload(enc_module)
        result = enc_module.decrypt_secret(ciphertext)

    assert result == "rotate-me"


# ---------------------------------------------------------------------------
# test_missing_encryption_key
# ---------------------------------------------------------------------------


def test_missing_encryption_key():
    """Missing ADMIN_ENCRYPTION_KEY raises RuntimeError when encryption is attempted."""
    import importlib

    import app.services.encryption as enc_module

    env_without_key = {k: v for k, v in os.environ.items() if k != "ADMIN_ENCRYPTION_KEY"}
    with patch.dict(os.environ, env_without_key, clear=True):
        importlib.reload(enc_module)

        with pytest.raises(RuntimeError, match="ADMIN_ENCRYPTION_KEY"):
            enc_module.encrypt_secret("secret")
