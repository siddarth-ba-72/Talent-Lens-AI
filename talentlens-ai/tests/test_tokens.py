from __future__ import annotations

import jwt
import pytest

from app.config import Settings
from app.db.models import new_token_salt
from app.errors import UnauthorizedError
from app.security import tokens


def _claims(settings, token, expected_type=tokens.TYPE_ACCESS):
    return tokens.decode_token(settings, token, expected_type)


def test_access_token_is_bound_to_the_session_fingerprint(settings, make_user):
    user = make_user()
    fingerprint = tokens.new_fingerprint()
    claims = _claims(settings, tokens.create_access_token(settings, user, fingerprint))

    assert claims["sub"] == user.id
    assert claims["role"] == user.role.value
    assert tokens.fingerprint_matches(settings, user, fingerprint, claims)


def test_token_carries_only_a_hash_of_the_fingerprint(settings, make_user):
    user = make_user()
    fingerprint = tokens.new_fingerprint()
    token = tokens.create_access_token(settings, user, fingerprint)

    unverified = jwt.decode(token, options={"verify_signature": False})
    assert fingerprint not in token
    assert unverified["fgp"] != fingerprint
    assert user.token_salt not in str(unverified)


@pytest.mark.parametrize("presented", [None, "", "some-other-browser"])
def test_stolen_token_without_the_matching_cookie_is_rejected(settings, make_user, presented):
    user = make_user()
    claims = _claims(settings, tokens.create_access_token(settings, user, tokens.new_fingerprint()))

    assert not tokens.fingerprint_matches(settings, user, presented, claims)


def test_fingerprint_is_salted_per_user(settings, make_user):
    alice, bob = make_user(), make_user()
    fingerprint = tokens.new_fingerprint()

    assert tokens.fingerprint_hash(settings, alice, fingerprint) != tokens.fingerprint_hash(settings, bob, fingerprint)


def test_rotating_the_salt_revokes_existing_tokens(settings, make_user):
    user = make_user()
    fingerprint = tokens.new_fingerprint()
    claims = _claims(settings, tokens.create_access_token(settings, user, fingerprint))

    user.token_salt = new_token_salt()

    assert not tokens.fingerprint_matches(settings, user, fingerprint, claims)


def test_token_without_a_binding_claim_is_rejected(settings, make_user):
    user = make_user()
    assert not tokens.fingerprint_matches(settings, user, "anything", {"sub": user.id})


def test_token_types_are_not_interchangeable(settings, make_user):
    user = make_user()
    fingerprint = tokens.new_fingerprint()
    refresh = tokens.create_refresh_token(settings, user, fingerprint)
    ticket = tokens.create_signup_ticket(settings, {"email": user.email})

    assert _claims(settings, refresh, tokens.TYPE_REFRESH)["sub"] == user.id
    for token in (refresh, ticket):
        with pytest.raises(UnauthorizedError):
            _claims(settings, token, tokens.TYPE_ACCESS)


def test_expired_token_is_rejected(settings, make_user):
    expired = settings.model_copy(update={"jwt_access_expiry_ms": -1000})
    token = tokens.create_access_token(expired, make_user(), tokens.new_fingerprint())

    with pytest.raises(UnauthorizedError, match="expired"):
        _claims(settings, token)


def test_token_signed_with_another_secret_is_rejected(settings, make_user):
    other = settings.model_copy(update={"jwt_secret": "a-completely-different-secret-0123456789abcdef"})
    token = tokens.create_access_token(other, make_user(), tokens.new_fingerprint())

    with pytest.raises(UnauthorizedError):
        _claims(settings, token)


def test_unsigned_token_is_rejected(settings, make_user):
    user = make_user()
    forged = jwt.encode({"sub": user.id, "type": tokens.TYPE_ACCESS}, key="", algorithm="none")

    with pytest.raises(UnauthorizedError):
        _claims(settings, forged)


def test_short_jwt_secret_is_refused():
    with pytest.raises(ValueError, match="at least 32"):
        Settings(_env_file=None, DATABASE_URL="postgresql://x/y", MONGODB_URI="mongodb://x", JWT_SECRET="too-short")
