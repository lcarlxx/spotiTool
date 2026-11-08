import spotipy
from spotipy.oauth2 import SpotifyOAuth # imports the login tool
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Local, gitignored file holding the Spotify API credentials.
CREDENTIALS_FILE = os.path.join(BASE_DIR, "spotify_credentials.json")

def load_spotify_credentials():
    """Load Spotify API credentials.

    Priority: environment variables (SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET)
    → local spotify_credentials.json (gitignored).

    Secrets must never be hardcoded in source — the previous client secret was
    committed publicly and has to be rotated in the Spotify Developer Dashboard.
    """
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if client_id and client_secret:
        return client_id, client_secret
    try:
        with open(CREDENTIALS_FILE, "r") as f:
            data = json.load(f)
        return data["client_id"], data["client_secret"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        raise RuntimeError(
            "Spotify API credentials not found.\n\n"
            "Either set these environment variables:\n"
            "  SPOTIFY_CLIENT_ID\n"
            "  SPOTIFY_CLIENT_SECRET\n\n"
            "or create a spotify_credentials.json file next to spotify_auth.py:\n"
            '{"client_id": "...", "client_secret": "..."}'
        )

REDIRECT_URI = "http://127.0.0.1:8888/callback"
# Default fallback used until the user picks their own playlist via the popup.
# (Spotify dev-mode apps can't create playlists, so a real playlist ID is required.)
PROJECT_SONGS_PLAYLIST_ID = "0ZyG7KYBa5cT8oJua0V4jJ"
PLAYLIST_CONFIG_FILE = os.path.join(BASE_DIR, "playlist_config.json")

# our permissions
SCOPE = (
    "user-read-playback-state "
    "user-read-currently-playing "
    "playlist-modify-public "
    "playlist-modify-private "
    "playlist-read-private "
    "playlist-read-collaborative "
    "user-top-read "
    "user-read-recently-played"
)

def get_spotify_client(force_reauth=False):
    cache_path = os.path.join(BASE_DIR, ".spotify_cache")

    client_id, client_secret = load_spotify_credentials()

    # if the user wants to switch accounts, wipe the cached token first
    if force_reauth and os.path.exists(cache_path):
        os.remove(cache_path)

    # opens a browser window asking the user to log in to Spotify
    auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=cache_path, # saves the token to prevent repeat logins
        open_browser=True,
        show_dialog=True
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    return sp

def extract_playlist_id(text):
    """Extract a Spotify playlist ID from a link/URI/bare ID.

    Accepts things like:
      https://open.spotify.com/playlist/0ZyG7KYBa5cT8oJua0V4jJ?si=...
      spotify:playlist:0ZyG7KYBa5cT8oJua0V4jJ
      0ZyG7KYBa5cT8oJua0V4jJ
    """
    text = (text or "").strip()
    if not text:
        return None
    match = re.search(r"playlist[/:]([A-Za-z0-9]+)", text)
    if match:
        return match.group(1)
    # a bare ID is a 22-character base62 string
    if re.fullmatch(r"[A-Za-z0-9]{22}", text):
        return text
    return None

def load_saved_playlist_id():
    """Load the playlist ID the user picked in the popup (if any)."""
    try:
        with open(PLAYLIST_CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("playlist_id") or None
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_playlist_id(playlist_id):
    """Remember the user's chosen playlist so they only have to paste it once."""
    with open(PLAYLIST_CONFIG_FILE, "w") as f:
        json.dump({"playlist_id": playlist_id}, f, indent=4)

def add_song_to_playlist(sp: spotipy.Spotify, track_uri, playlist_id=None):
    """Add a track to the user's chosen playlist.

    Falls back to the saved playlist ID, then to the hardcoded default.
    """
    playlist_id = playlist_id or load_saved_playlist_id() or PROJECT_SONGS_PLAYLIST_ID
    result = sp.playlist_add_items(playlist_id, [track_uri])
    print("Added track:", result)
    return playlist_id