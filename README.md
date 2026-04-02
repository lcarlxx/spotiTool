# spotiTool: Your all-in-one Tkinter GUI Spotify Companion
## spotiTool v0.1.0 (22/03/2026)

### Development Notes:
- The app originally used Google's Speech Recognition API for audio identification but it was not properly optimised for music recognition. It was replaced with ShazamIO, which provides significantly more reliable song identification.
- Some required Spotipy API scopes may be missing by default. Ensure all necessary scopes are included in your scope string. Note that scopes must be space-separated — a trailing space before the closing quote is mandatory when appending scopes, e.g. "user-read-playback-state "
- ShazamIO deprecated recognize_song() in version 0.5.0 and replaced it with recognize(). If the app breaks after updating ShazamIO, ensure you are on v0.5.0 or later and that the method used is shazam.recognize() and not shazam.recognize_song()
- Audio capture became significantly more reliable after switching from 2-channel (stereo) to 1-channel (mono) input.
- Spotify has been progressively restricting its API since late 2024. Apps in development mode are now limited to 5 test users and cannot create playlists. As a workaround, a specific Spotify playlist ID must be hardcoded or provided by the user. To make this easier, a future update may include a popup allowing the user to paste a Spotify playlist link, from which the playlist ID will be extracted automatically.
- When Shazam and Spotify searches were combined, the app would sometimes return a cover version by an obscure artist instead of the original, due to Spotify surfacing the first available match. This was fixed by separating the two searches — Shazam identifies the song first, then a separate Spotify search is performed using those results.
-  Spotify's search was too strict to reliably find songs that Shazam had already identified. An attempt to fix this using ShazamIO's Serialize to extract the URI returned a 400 error. The final fix was to extract the Spotify URI directly from Shazam's raw response data, where Shazam embeds a spotify:track:ID link under the hub.providers field, bypassing the Spotify search altogether.

### Setup Info:
-  PyAudio does not currently provide pre-compiled wheels for Python 3.14. Downgrade your Python environment to 3.13 or 3.12 before installing dependencies.
-  For system audio to work, you must install FFmpeg, add it to your system PATH, restart your computer, and enable Stereo Mix in your sound settings — in that order. If you want to switch to microphone input, remember to go back into your sound settings and set your default recording device from Stereo Mix back to your Microphone. *(planning on fixing this soon)*

### Bugs and Fixes:
- Always logged into the same spotify account regardless of user until I added a messagebox popup to ask if it was linked to that specific username to confirm.
- Audio capture still does not work when using wired earphones or Bluetooth audio devices. *(planning on fixing this soon)*
