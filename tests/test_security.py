from app.services.security import generate_share_token, hash_token


def test_generate_share_token_is_urlsafe_and_non_empty():
    token = generate_share_token()
    assert isinstance(token, str)
    assert len(token) >= 32
    assert "+" not in token
    assert "/" not in token


def test_generate_share_token_is_effectively_unique():
    t1 = generate_share_token()
    t2 = generate_share_token()
    assert t1 != t2


def test_hash_token_is_deterministic_and_sha256_length():
    digest1 = hash_token("abc123")
    digest2 = hash_token("abc123")
    digest3 = hash_token("abc1234")

    assert digest1 == digest2
    assert digest1 != digest3
    assert len(digest1) == 64
