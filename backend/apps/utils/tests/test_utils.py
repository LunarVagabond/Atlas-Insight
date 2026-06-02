import pytest
from unittest.mock import MagicMock, patch
from cryptography.fernet import Fernet


# ── EncryptedCharField ────────────────────────────────────────────────────────

@pytest.fixture
def fernet_key():
    return Fernet.generate_key().decode()


@pytest.fixture
def encrypted_field():
    from apps.utils.encryption import EncryptedCharField
    return EncryptedCharField()


class TestEncryptedCharField:
    def test_roundtrip(self, encrypted_field, fernet_key, settings):
        settings.FIELD_ENCRYPTION_KEY = fernet_key
        plaintext = 'secret-token-abc123'
        encrypted = encrypted_field.get_prep_value(plaintext)
        assert encrypted.startswith('enc:')
        assert encrypted != plaintext
        recovered = encrypted_field.from_db_value(encrypted, None, None)
        assert recovered == plaintext

    def test_prep_value_is_idempotent(self, encrypted_field, fernet_key, settings):
        settings.FIELD_ENCRYPTION_KEY = fernet_key
        plaintext = 'my-secret'
        encrypted = encrypted_field.get_prep_value(plaintext)
        # Calling again on already-encrypted value must not double-encrypt
        encrypted_again = encrypted_field.get_prep_value(encrypted)
        assert encrypted_again == encrypted

    def test_empty_value_passthrough(self, encrypted_field, fernet_key, settings):
        settings.FIELD_ENCRYPTION_KEY = fernet_key
        assert encrypted_field.get_prep_value('') == ''
        assert encrypted_field.from_db_value('', None, None) == ''
        assert encrypted_field.get_prep_value(None) is None

    def test_no_key_passthrough(self, encrypted_field, settings):
        settings.FIELD_ENCRYPTION_KEY = ''
        plaintext = 'no-encrypt'
        assert encrypted_field.get_prep_value(plaintext) == plaintext
        assert encrypted_field.from_db_value(plaintext, None, None) == plaintext

    def test_invalid_token_returns_empty(self, encrypted_field, fernet_key, settings):
        settings.FIELD_ENCRYPTION_KEY = fernet_key
        bad_value = 'enc:notvalidbase64fernet=='
        result = encrypted_field.from_db_value(bad_value, None, None)
        assert result == ''

    def test_plaintext_in_db_passes_through(self, encrypted_field, fernet_key, settings):
        settings.FIELD_ENCRYPTION_KEY = fernet_key
        # Pre-existing plaintext row (before encryption was added)
        result = encrypted_field.from_db_value('old-plaintext', None, None)
        assert result == 'old-plaintext'


# ── flag_enabled ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestFlagEnabled:
    def test_unknown_flag_returns_false(self):
        from apps.utils.flags import flag_enabled
        assert flag_enabled('nonexistent_flag_xyz') is False

    def test_enabled_flag_returns_true(self):
        from apps.repositories.models import FeatureFlag
        from apps.utils.flags import flag_enabled
        from django.core.cache import cache
        cache.clear()
        FeatureFlag.objects.create(name='test_flag_on', enabled=True)
        assert flag_enabled('test_flag_on') is True

    def test_disabled_flag_returns_false(self):
        from apps.repositories.models import FeatureFlag
        from apps.utils.flags import flag_enabled
        from django.core.cache import cache
        cache.clear()
        FeatureFlag.objects.create(name='test_flag_off', enabled=False)
        assert flag_enabled('test_flag_off') is False

    def test_result_is_cached(self):
        from apps.utils.flags import flag_enabled
        from django.core.cache import cache
        cache.clear()
        with patch('apps.repositories.models.FeatureFlag.objects') as mock_mgr:
            mock_mgr.get.side_effect = Exception('DB error')
            result1 = flag_enabled('cached_flag')
            result2 = flag_enabled('cached_flag')
            # Both return False (DB error → default), but DB called only once
            assert result1 is False
            assert result2 is False
            assert mock_mgr.get.call_count == 1
