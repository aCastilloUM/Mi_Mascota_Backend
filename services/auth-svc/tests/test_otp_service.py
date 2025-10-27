import os
import asyncio
import pytest
from datetime import timedelta

# Ensure required environment variables are set before importing app modules
os.environ.setdefault('DATABASE_URL', 'postgresql://user:pass@localhost:5432/testdb')
os.environ.setdefault('JWT_SECRET', 'test-jwt-secret')
os.environ.setdefault('JWT_ISSUER', 'test-issuer')
os.environ.setdefault('JWT_AUDIENCE', 'test-aud')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

from app.services.otp_service import OTPService, otp_service


@pytest.mark.asyncio
async def test_generate_and_validate_otp(monkeypatch):
    # Use the real singleton but mock redis client methods
    calls = {}

    class DummyRedis:
        def __init__(self):
            self.store = {}

        async def get(self, k):
            return self.store.get(k)

        async def setex(self, k, ttl, v):
            # store string value
            self.store[k] = v

        async def delete(self, k):
            if k in self.store:
                del self.store[k]

        async def incr(self, k):
            v = int(self.store.get(k, 0)) + 1
            self.store[k] = str(v)
            return v

        async def expire(self, k, t):
            pass

    dummy = DummyRedis()
    # monkeypatch redis_client.conn to dummy
    import app.infra.redis as infra_redis
    # Directly set the internal _redis instance used by RedisClient.conn
    infra_redis.redis_client._redis = dummy

    temp_id = 'tmp-123'

    sent = await otp_service.create_and_send(temp_id, to_email='test@example.com')
    assert sent is True

    # Retrieve stored hash key
    key = otp_service._make_key(temp_id)
    stored = await infra_redis.redis_client.conn.get(key)
    assert stored is not None

    # Now validate with wrong code
    valid = await otp_service.validate(temp_id, '000000')
    assert valid is False

    # Attempt to retrieve attempts
    attempts_k = otp_service._attempt_key(temp_id)
    attempts = await infra_redis.redis_client.conn.get(attempts_k)
    assert attempts is not None

    # Simulate correct by hashing stored value (we don't have original code), so directly compare
    # For test, extract the stored hash and validate by comparing to itself
    # This is a small white-box test to ensure validate deletes on matching
    stored_hash = stored
    # Monkeypatch otp_service._hash to return stored_hash for a given input
    monkeypatch.setattr(OTPService, '_hash', lambda self, code: stored_hash)

    valid2 = await otp_service.validate(temp_id, 'ANY')
    assert valid2 is True

    # After success key should be deleted
    assert await infra_redis.redis_client.conn.get(key) is None
