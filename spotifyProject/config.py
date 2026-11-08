import sys

from pathlib import Path

# ── Spotify API Credentials ───────────────────────────────────────────────────
# Get these from https://developer.spotify.com/dashboard
# Loaded from environment variables (SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET)
# so secrets stay out of the source code. Set them before running the app.
import os as _os

SPOTIPY_CLIENT_ID     = _os.getenv("SPOTIPY_CLIENT_ID", "")
SPOTIPY_CLIENT_SECRET = _os.getenv("SPOTIPY_CLIENT_SECRET", "")
REDIRECT_URI          = _os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

# ── Paths ─────────────────────────────────────────────────────────────────────
# Root of the project (the folder containing this file)
if getattr(sys, 'frozen', False):
    BASE_DIR      = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# Where user accounts and app data are stored
USER_DATA_DIR = BASE_DIR / "user_data"

# Where spotipy caches the OAuth token so you don't re-login every launch
CACHE_PATH    = USER_DATA_DIR / ".spotify_cache"


# ── Validation ────────────────────────────────────────────────────────────────
def validate_spotify_credentials() -> None:
    """Raise a clear error if the user forgot to fill in their credentials."""
    if not SPOTIPY_CLIENT_ID or SPOTIPY_CLIENT_ID == "YOUR_CLIENT_ID_HERE":
        raise ValueError(
            "Spotify Client ID is not set.\n"
            "Edit spotifyProject/config.py and add your Client ID.\n"
            "Get one at: https://developer.spotify.com/dashboard"
        )
    if not SPOTIPY_CLIENT_SECRET or SPOTIPY_CLIENT_SECRET == "YOUR_CLIENT_SECRET_HERE":
        raise ValueError(
            "Spotify Client Secret is not set.\n"
            "Edit spotifyProject/config.py and add your Client Secret.\n"
            "Get one at: https://developer.spotify.com/dashboard"
        )
