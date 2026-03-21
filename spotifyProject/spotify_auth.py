import spotipy
from spotipy.oauth2 import SpotifyOAuth # imports the login tool
import json

# like a username + password for the app
CLIENT_ID = "73c6db4721b74bfb9a4588c6514ef868"
CLIENT_SECRET = "56d668bb771f4c6ba9ea2cda445e053a"
REDIRECT_URI = "http://127.0.0.1:8888/callback"

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
    import os
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".spotify_cache")
    # opens a browser window asking the user to log in to Spotify

    # if the user wants to switch accounts, wipe the cached token first
    if force_reauth and os.path.exists(cache_path):
        os.remove(cache_path)

    # opens a browser window asking the user to log in to Spotify
    auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=cache_path, # saves the token to prevent repeat logins
        open_browser=True,
        show_dialog=True
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)
    return sp

def get_or_create_playlist(sp, playlist_name="ProjectSongs"):
    # look for a playlist called 'ProjectSongs', if it doesn't exist create it
    user_id = sp.current_user()["id"]
    
    # search through all user's playlists
    playlists = sp.current_user_playlists(limit=50)

    while playlists: # keeps going as long as 'playlists' variable keeps going
        for playlist in playlists["items"]:
            if playlist["name"] == playlist_name:
                return playlist["id"] # playlist found
        
        if playlists["next"]:
            playlists = sp.next(playlists)
        else:
            playlists = None

    # however if it's not found, lets create it
    new_playlist = sp.user_playlist_create(
        user=user_id,
        name=playlist_name,
        public=False,
        description="Songs found using Python Project voice recognition!"
    )
    return new_playlist["id"]

def add_song_to_playlist(sp: spotipy.Spotify, track_uri):
    playlist_id = get_or_create_playlist(sp)
    result = sp.playlist_add_items(playlist_id, [track_uri])
    print("Added track:", result)