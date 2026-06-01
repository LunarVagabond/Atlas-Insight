import logging

from django.db import models

logger = logging.getLogger(__name__)


def _get_fernet():
    from django.conf import settings
    from cryptography.fernet import Fernet

    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', '')
    if not key:
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedCharField(models.TextField):
    """TextField that transparently encrypts/decrypts using Fernet symmetric encryption.

    Stored as 'enc:<fernet_token>'. Plaintext values (pre-encryption) pass through
    on read and are re-encrypted on next save. No-op when FIELD_ENCRYPTION_KEY unset.
    """

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        f = _get_fernet()
        if f is None:
            return value
        if value.startswith('enc:'):
            try:
                from cryptography.fernet import InvalidToken
                return f.decrypt(value[4:].encode()).decode()
            except InvalidToken:
                logger.error('EncryptedCharField: failed to decrypt value — returning empty string')
                return ''
        return value  # plaintext fallback: re-encrypted on next save

    def get_prep_value(self, value):
        if not value:
            return value
        f = _get_fernet()
        if f is None:
            return value
        if not value.startswith('enc:'):
            return 'enc:' + f.encrypt(value.encode()).decode()
        return value
