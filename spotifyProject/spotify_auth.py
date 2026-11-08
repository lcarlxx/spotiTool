from __future__ import annotations

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from .config import (
    CACHE_PATH,
    USER_DATA_DIR,
    get_spotify_credentials,
    validate_spotify_credentials,
)

USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

SCOPE = (
    'user-read-playback-state '
    'user-read-currently-playing '
    'playlist-modify-public '
    'playlist-modify-private '
    'playlist-read-private '
    'playlist-read-collaborative '
    'user-top-read '
    'user-read-recently-played '
    'user-library-read'
)


def get_spotify_client(force_reauth: bool = False) -> spotipy.Spotify:
    validate_spotify_credentials()
    client_id, client_secret, redirect_uri = get_spotify_credentials()
    if force_reauth and CACHE_PATH.exists():
        CACHE_PATH.unlink()
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        cache_path=str(CACHE_PATH),
        open_browser=True,
        show_dialog=True,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def get_public_spotify_client() -> spotipy.Spotify:
    validate_spotify_credentials()
    client_id, client_secret, _ = get_spotify_credentials()
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
    ))


def get_or_create_playlist(sp: spotipy.Spotify, playlist_name: str = 'ProjectSongs') -> str:
    user_id = sp.current_user()['id']
    playlists = sp.current_user_playlists(limit=50)
    while playlists:
        for playlist in playlists['items']:
            if playlist['name'] == playlist_name:
                return playlist['id']
        playlists = sp.next(playlists) if playlists.get('next') else None
    new_playlist = sp.user_playlist_create(
        user_id,
        playlist_name,
        public=False,
        description='Songs found using SpotiTool Music recognition!',
    )
    return new_playlist['id']


def add_song_to_playlist(sp: spotipy.Spotify, track_uri: str, playlist_uri: str | None = None) -> str:
    playlist_id = playlist_uri.split(':')[-1] if playlist_uri and ':' in playlist_uri else playlist_uri
    if not playlist_id:
        playlist_id = get_or_create_playlist(sp)
    sp.playlist_add_items(playlist_id, [track_uri])
    return playlist_id
