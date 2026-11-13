
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

from .config import USER_DATA_DIR

USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = USER_DATA_DIR / 'user_data.json'

HASH_ALGORITHM = 'sha256'
HASH_ITERATIONS = 200_000
SALT_BYTES = 16


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode('utf-8'),
        salt,
        HASH_ITERATIONS,
    )
    return f'pbkdf2_{HASH_ALGORITHM}${HASH_ITERATIONS}${salt.hex()}${digest.hex()}'


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        prefix, iterations, salt_hex, digest_hex = stored_hash.split('$', 3)
        if not prefix.startswith('pbkdf2_'):
            return False
        algorithm = prefix.replace('pbkdf2_', '')
        iterations = int(iterations)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        candidate = hashlib.pbkdf2_hmac(
            algorithm,
            password.encode('utf-8'),
            salt,
            iterations,
        )
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False


def load_users() -> dict[str, dict]:
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding='utf-8')) or {}
    except json.JSONDecodeError:
        backup_file = DATA_FILE.with_suffix('.json.bak')
        DATA_FILE.replace(backup_file)
        return {}


def save_users(users: dict) -> bool:
    try:
        temp_file = DATA_FILE.with_suffix('.json.tmp')
        temp_file.write_text(json.dumps(users, indent=4), encoding='utf-8')
        temp_file.replace(DATA_FILE)
        return True
    except Exception:
        return False


def register_user(username: str, password: str) -> tuple[bool, str]:
    users = load_users()
    username = username.strip()
    if not username:
        return False, 'Username cannot be blank.'
    if username in users:
        return False, 'Username already exists.'
    users[username] = {
        'password_hash': _hash_password(password),
        'spotify_id': None,
        'remember_me': False,
    }
    return (True, 'Account created!') if save_users(users) else (False, 'Could not save account. Check folder permissions.')


def login_user(username: str, password: str) -> tuple[bool, str]:
    users = load_users()
    if username not in users:
        return False, 'Username not found.'
    password_hash = users[username].get('password_hash')
    if not password_hash:
        return False, 'No password is configured for this account.'
    if _verify_password(password, password_hash):
        return True, 'Login successful.'
    return False, 'Incorrect password.'


def set_remember_me(username: str, enabled: bool) -> None:
    users = load_users()
    if username not in users:
        return
    users[username]['remember_me'] = enabled
    if enabled:
        users[username]['last_logged_in'] = datetime.now(timezone.utc).isoformat()
    save_users(users)


def get_remembered_user() -> str | None:
    """Return the most recently used account that opted into Remember Me.

    Several accounts can be remembered at once; the newest login wins instead of
    whichever happens to come first in the file.
    """
    users = load_users()
    candidates = [
        (str(data.get('last_logged_in') or ''), username)
        for username, data in users.items()
        if data.get('remember_me') and data.get('password_hash')
    ]
    if not candidates:
        return None
    return max(candidates)[1]


def clear_remember_me(username: str) -> None:
    users = load_users()
    if username not in users:
        return
    users[username]['remember_me'] = False
    save_users(users)


def set_user_playlist(username: str, playlist_uri: str) -> bool:
    users = load_users()
    if username not in users:
        return False
    users[username]['selected_playlist'] = playlist_uri
    return save_users(users)


def get_user_playlist(username: str) -> str | None:
    users = load_users()
    return users.get(username, {}).get('selected_playlist')
