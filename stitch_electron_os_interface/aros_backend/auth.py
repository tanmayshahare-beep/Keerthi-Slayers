import hashlib
import hmac
import secrets

from fastapi import Header, HTTPException

import app_db

PBKDF2_ITERATIONS = 260_000

# In-memory session store: token -> username. Acceptable for a local,
# single-user desktop app whose backend only listens on 127.0.0.1.
_sessions: dict[str, str] = {}


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    computed, _ = hash_password(password, salt)
    return hmac.compare_digest(computed, expected_hash)


def issue_session(username: str) -> str:
    token = secrets.token_hex(32)
    _sessions[token] = username
    return token


def require_session(authorization: str = Header(default="")) -> str:
    token = authorization.removeprefix("Bearer ").strip()
    username = _sessions.get(token)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username
