# spotiTool: Your all-in-one Spotify Companion

## spotiTool v0.2.0

A Python Spotify companion app with a CustomTkinter GUI and a headless CLI:

- **Music recognition** — identify songs playing on your PC (system audio) or via the microphone, using Shazam
- **Downloads** — grab audio for Spotify tracks/albums/playlists via yt-dlp, with metadata and cover art tagging
- **Listening stats** — top artists, top tracks and recently played
- **Playlist saving** — send identified songs straight to a playlist of your choice

## Setup

1. Use **Python 3.12 or 3.13** (3.14 lacks some prebuilt audio wheels).
2. Install FFmpeg and add it to your system PATH (required for audio processing/downloads).
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set your Spotify API credentials as environment variables (get them at https://developer.spotify.com/dashboard):
   - `SPOTIPY_CLIENT_ID`
   - `SPOTIPY_CLIENT_SECRET`
   - optional: `SPOTIPY_REDIRECT_URI` (default: `http://127.0.0.1:8888/callback`)

   Secrets are never stored in the source code. (Note: an old client secret exists in this repo's git history — rotate yours in the dashboard.)

## Usage

- GUI:
  ```bash
  python run.py
  ```
- CLI — test core features without launching the GUI:
  ```bash
  python -m spotifyProject login                     # run Spotify OAuth once, cache the token
  python -m spotifyProject stats --range short       # top artists / tracks / recently played
  python -m spotifyProject recognize                 # identify audio playing on this PC
  python -m spotifyProject recognize --source mic    # ...via the microphone instead
  python -m spotifyProject recognize --add --user myuser   # ...and save it to the playlist
  python -m spotifyProject download <spotify-url> --format flac
  ```
  Run `python -m spotifyProject <command> --help` for all options.

On first launch, confirm the linked Spotify account and paste a playlist link when asked — the app remembers it.

## Notes & gotchas

- Spotify dev-mode apps can't create playlists and are limited to 5 test users — point the app at an existing playlist.
- Recognition works best with ~10 seconds of clean, mid-song audio; intros and quiet audio often fail — just retry.
- System audio capture uses a loopback device (Stereo Mix / "What U Hear" / similar) and works regardless of your default recording device, so wired earphones and Bluetooth output both work.
- Passwords are hashed with PBKDF2; tokens, user data and caches live in `user_data/` and are gitignored.
- If ShazamIO is updated past v0.5.0, ensure `shazam.recognize()` is used (not the deprecated `recognize_song()`).

## Development history (v0.1.0)

- Google's Speech Recognition API was replaced with ShazamIO for far more reliable music identification.
- Combining Shazam and Spotify searches sometimes returned cover versions by obscure artists; fixed by identifying with Shazam first, then using the Spotify URI embedded in Shazam's `hub.providers` response — bypassing Spotify search (whose strictness caused 400 errors with the old Serialize approach).
- Scopes must be space-separated, with a mandatory trailing space before the closing quote, e.g. `"user-read-playback-state "`.
