import tkinter as tk
from tkinter import messagebox
import threading
import spotipy
from spotify_auth import add_song_to_playlist
import sounddevice as sd
import scipy.io.wavfile as wav
import tempfile, os
import asyncio
from tkinter import simpledialog
from shazamio import Shazam
from spotify_auth import (
    add_song_to_playlist,
    extract_playlist_id,
    load_saved_playlist_id,
    save_playlist_id,
    PROJECT_SONGS_PLAYLIST_ID,
)

class voiceRecognitionTool:
    def __init__(self, root, sp: spotipy.Spotify):
        self.root = root
        self.sp = sp

        self.root.title("Music Recognition 🎙️")
        self.root.geometry("500x420")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)

        self.build_ui()

    def build_ui(self):
        tk.Label(self.root, text="Music Recognition 🎙️",
                 font=("Helvetica", 18, "bold"),
                 bg="#1a1a2e", fg="#1DB954").pack(pady=20)
        
        tk.Label(self.root,
                 text="Tap a button to identify a song",
                 font=("Helvetica", 11),
                 bg="#1a1a2e", fg="#aaaaaa").pack()
        
        tk.Button(self.root, text="🎙️\nListen via Microphone",
                  font=("Helvetica", 13, "bold"),
                  bg="#0f3460", fg="white",
                  width=28, height=2,
                  command=self.listen_mic).pack(pady=15)
        
        tk.Button(self.root, text="🖥️\nDetect System Audio",
                  font=("Helvetica", 13, "bold"),
                  bg="#0f3460", fg="white",
                  width=28, height=2,
                  command=self.listen_system).pack(pady=5)
        
        self.status_var = tk.StringVar(value="Ready...")
        tk.Label(self.root, textvariable=self.status_var,
                 font=("Helvetica", 11), bg="#1a1a2e",
                 fg="#1DB954", wraplength=420).pack(pady=20)
        
        self.result_box = tk.Text(self.root, height=4, width=50,
                                   bg="#16213e", fg="white",
                                   font=("Helvetica", 11),
                                   state="disabled", wrap="word")
        self.result_box.pack(pady=5)

    def set_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))

    def show_result(self, text):
        def update():
            self.result_box.config(state="normal")
            self.result_box.delete("1.0", "end")
            self.result_box.insert("end", text)
            self.result_box.config(state="disabled")
        self.root.after(0, update)

    def _process_audio(self, wav_path):
        self.set_status("🎵 Identifying with Shazam...")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_dict = loop.run_until_complete(self._recognize_with_shazam(wav_path))
            finally:
                loop.close()

            if not result_dict:
                self.set_status("❌ Shazam couldn't identify the song.\nTry clearer/louder audio.")
                return

            title  = result_dict["title"]
            artist = result_dict["artist"]
            uri    = result_dict.get("uri")  # spotify:track:XXXX — already the right format

            if uri:
                # ✅ Shazam gave us the exact Spotify track — skip the search entirely
                self.set_status(f"✅ Identified: {title} by {artist}")
                self.show_result(f"🎵 Found: {title} by {artist}")
                self.root.after(0, lambda: self._ask_to_save(title, artist, uri))
            else:
                # Fallback: Shazam identified the song but has no Spotify link
                # (rare — happens for very obscure tracks)
                self.set_status(f"🔎 Searching Spotify for: {title} by {artist}...")
                self.root.after(0, lambda: self._do_search(title, artist))

        except Exception as e:
            self.set_status(f"❌ Shazam error: {str(e)}")
        finally:
            if os.path.exists(wav_path):
                os.unlink(wav_path)

    # using asyncio to basically give our code time to pull things in the API
    async def _recognize_with_shazam(self, audio_path: str):
        """Fingerprints the audio with Shazam and extracts the Spotify URI from the hub."""
        shazam = Shazam()
        result = await shazam.recognize(audio_path)

        if not result or "track" not in result:
            return None

        track  = result["track"]
        title  = track.get("title", "")
        artist = track.get("subtitle", "")

        # hub.providers pulls the direct song ID from Shazam's servers already as a URI
        # hence we don't have to stress out about the 400 Error
        spotify_uri = None
        hub = track.get("hub", {})
        for provider in hub.get("providers", []):
            if provider.get("type") == "SPOTIFY":
                for action in provider.get("actions", []):
                    if action.get("type") == "uri":
                        raw = action.get("uri", "")
                        # Shazam always gives "spotify:track:ID" here,
                        # but guard against an https URL just in case
                        if raw.startswith("https://open.spotify.com/track/"):
                            track_id = raw.split("/track/")[1].split("?")[0]
                            spotify_uri = f"spotify:track:{track_id}"
                        elif raw.startswith("spotify:track:"):
                            spotify_uri = raw
                        break
                if spotify_uri:
                    break

        return {"title": title, "artist": artist, "uri": spotify_uri}

    # however if the song can't be discovered on hub.providers, this should work instead
    def _do_search(self, title: str, artist: str):
        """Search Spotify by title + artist. Runs on the main thread."""
        try:
            # Do NOT wrap values in single quotes — Spotify rejects them.
            # Use field filters without quotes, and try up to 5 results so we
            # can pick the best match rather than blindly taking the first one.
            results = self.sp.search(
                q=f"track:{title} artist:{artist}",
                type="track",
                limit=5,
                market="US"
            )
            tracks = results.get("tracks", {}).get("items", [])

            if not tracks:
                # Retry with a simpler free-text query in case field filters failed
                results = self.sp.search(
                    q=f"{title} {artist}",
                    type="track",
                    limit=5,
                    market="US"
                )
                tracks = results.get("tracks", {}).get("items", [])

            if not tracks:
                self.set_status("❌ No matching song found on Spotify.")
                return

            # Prefer exact name matches to avoid picking a cover
            target_title  = title.lower().strip()
            target_artist = artist.lower().strip()
            best = None
            for t in tracks:
                t_name   = t["name"].lower().strip()
                t_artist = t["artists"][0]["name"].lower().strip()
                if t_name == target_title and t_artist == target_artist:
                    best = t
                    break
            if best is None:
                best = tracks[0]  # take the top result if no exact match

            name   = best["name"]
            artist_name = best["artists"][0]["name"]
            uri    = best["uri"]

            self.show_result(f"🎵 Found: {name} by {artist_name}")
            self.set_status("✅ Song Found!")
            self._ask_to_save(name, artist_name, uri)

        except Exception as e:
            self.set_status(f"❌ Spotify error: {e}")

    def listen_mic(self):
        threading.Thread(target=self._mic_worker, daemon=True).start() # allows it to run in the background for a little bit and terminates almost immediately

    def _mic_worker(self):
        self.set_status("🎙️ Recording via microphone...\nPlay the song near your mic!")
        try:
            recording = sd.rec(int(10 * 44100), samplerate=44100,
                               channels=1, dtype='int16')
            sd.wait()
            self._write_wav_and_process(recording, 44100)
        except Exception as e:
            self.set_status(f"❌ Mic Error: {e}")

    def listen_system(self):
        threading.Thread(target=self._system_audio_worker, daemon=True).start()

    def _system_audio_worker(self):
        try:
            self.set_status("🖥️ Recording system audio...")
            sample_rate = 44100
            duration    = 10

            recording = self._record_system_audio(sample_rate, duration)
            self._write_wav_and_process(recording, sample_rate)

        except Exception as e:
            self.set_status(f"❌ System audio error: {e}\n"
                            "Try enabling 'Stereo Mix' in Windows sound settings.")

    def _write_wav_and_process(self, recording, sample_rate):
        """Write a recording to a temp WAV file and hand it to Shazam."""
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        wav.write(tmp.name, sample_rate, recording)
        self._process_audio(tmp.name)

    def _record_system_audio(self, sample_rate, duration):
        """Capture what the default OUTPUT device is playing.

        On Windows, sounddevice 0.5+ supports WASAPI loopback recording.
        This captures whatever the default output device plays — speakers,
        wired earphones, Bluetooth — so no 'Stereo Mix' input device and no
        fiddling with the default recording device is needed anymore.

        Falls back to the classic default-input recording (Stereo Mix) when
        loopback isn't available (e.g. non-Windows or older sounddevice).
        """
        frames = int(duration * sample_rate)
        try:
            wasapi = sd.WasapiSettings(loopback=True)
            recording = sd.rec(frames,
                               samplerate=sample_rate,
                               channels=2,          # output devices are stereo
                               dtype='int16',
                               extra_settings=wasapi)
            sd.wait()
            # mix the stereo loopback capture down to mono — mono input was
            # found to be much more reliable for song identification
            recording = recording.mean(axis=1).astype('int16')
            return recording
        except (AttributeError, sd.PortAudioError, OSError):
            # Fallback: record from the default INPUT device (Stereo Mix).
            # For this to work, the default recording device must be set to
            # Stereo Mix in Windows sound settings.
            recording = sd.rec(frames,
                               samplerate=sample_rate,
                               channels=1,
                               dtype='int16')
            sd.wait()
            return recording

    # save to playlist 
    def _ask_to_save(self, name, artist, uri):
        answer = messagebox.askyesno(
            "Add to Playlist?",
            f"Found: {name} by {artist}\n\nAdd this song to your playlist?"
        )
        if not answer:
            return

        playlist_id = self._get_playlist_id()
        if not playlist_id:
            return  # user cancelled the playlist popup

        try:
            used_id = add_song_to_playlist(self.sp, uri, playlist_id)
            messagebox.showinfo("Added! ✅", f"'{name}' added to your playlist!")
        except Exception as e:
            messagebox.showerror("Error ❌", f"Failed to add song:\n{e}")

    def _get_playlist_id(self):
        """Popup asking the user to paste a Spotify playlist link.

        The playlist ID is extracted automatically from a link, URI or bare
        ID, then remembered so the user is only asked once. Falls back to
        the previously saved playlist, then to the hardcoded default.
        """
        saved = load_saved_playlist_id() or PROJECT_SONGS_PLAYLIST_ID
        while True:
            pasted = simpledialog.askstring(
                "Choose Playlist",
                "Paste a Spotify playlist link (you only need to do this once):",
                initialvalue=f"https://open.spotify.com/playlist/{saved}",
                parent=self.root,
            )
            if pasted is None:
                return None  # cancelled
            playlist_id = extract_playlist_id(pasted)
            if playlist_id:
                save_playlist_id(playlist_id)
                return playlist_id
            messagebox.showwarning(
                "Invalid Link",
                "That doesn't look like a Spotify playlist link.\n"
                "Example: https://open.spotify.com/playlist/...",
                parent=self.root,
            )