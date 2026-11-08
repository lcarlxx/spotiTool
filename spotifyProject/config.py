from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
#Writable directory next to the executable (or package dir when running from source)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR)) / "spotifyProject"
else:
    BASE_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = BASE_DIR

# Where user accounts and app data are stored
USER_DATA_DIR = BASE_DIR / "user_data"

# Where spotipy caches the OAuth token so you don't re-login every launch
CACHE_PATH = USER_DATA_DIR / ".spotify_cache"


def _load_dotenv_if_present() -> None:
    """Load KEY=VALUE pairs from a .env file next to the app or in the repo root."""
    candidates = [BASE_DIR / ".env", BASE_DIR.parent / ".env", Path.cwd() / ".env"]
    for env_file in candidates:
        if not env_file.is_file():
            continue
        try:
            for raw_line in env_file.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            pass


def _load_credentials() -> tuple[str, str, str]:
    """Load Spotify credentials from env vars, .env, or spotify_credentials.json."""
    _load_dotenv_if_present()
    client_id = (
        os.getenv("SPOTIPY_CLIENT_ID")
        or os.getenv("SPOTIFY_CLIENT_ID")
        or ""
    ).strip()
    client_secret = (
        os.getenv("SPOTIPY_CLIENT_SECRET")
        or os.getenv("SPOTIFY_CLIENT_SECRET")
        or ""
    ).strip()
    redirect_uri = (
        os.getenv("SPOTIPY_REDIRECT_URI")
        or os.getenv("SPOTIFY_REDIRECT_URI")
        or "http://127.0.0.1:8888/callback"
    ).strip()

    if not (client_id and client_secret):
        for cred_file in (
            BASE_DIR / "spotify_credentials.json",
            USER_DATA_DIR / "spotify_credentials.json",
            Path.cwd() / "spotify_credentials.json",
        ):
            if cred_file.is_file():
                try:
                    data = json.loads(cred_file.read_text(encoding="utf-8"))
                    client_id = client_id or (data.get("client_id") or "").strip()
                    client_secret = client_secret or (data.get("client_secret") or "").strip()
                    redirect_uri = (data.get("redirect_uri") or redirect_uri).strip()
                    break
                except (OSError, json.JSONDecodeError):
                    pass

    return client_id, client_secret, redirect_uri


# ── Spotify API Credentials ───────────────────────────────────────────────────
SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, REDIRECT_URI = _load_credentials()


# ── Validation ────────────────────────────────────────────────────────────────
def get_spotify_credentials() -> tuple[str, str, str]:
    """Re-read credentials on demand (picks up env changes made at runtime)."""
    global SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, REDIRECT_URI
    SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, REDIRECT_URI = _load_credentials()
    return SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, REDIRECT_URI


def validate_spotify_credentials() -> None:
    """Raise a clear error if the user forgot to configure their credentials."""
    client_id, client_secret, _ = get_spotify_credentials()
    if not client_id or client_id == "YOUR_CLIENT_ID_HERE":
        raise ValueError(
            "Spotify Client ID is not set.\n"
            "Set the SPOTIPY_CLIENT_ID environment variable (or create a .env / "
            "spotify_credentials.json file).\n"
            "Get credentials at: https://developer.spotify.com/dashboard"
        )
    if not client_secret or client_secret == "YOUR_CLIENT_SECRET_HERE":
        raise ValueError(
            "Spotify Client Secret is not set.\n"
            "Set the SPOTIPY_CLIENT_SECRET environment variable (or create a .env / "
            "spotify_credentials.json file).\n"
            "Get credentials at: https://developer.spotify.com/dashboard"
        )
