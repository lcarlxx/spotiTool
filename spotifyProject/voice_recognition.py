import tkinter as tk
from tkinter import messagebox
import speech_recognition as sr
import threading
import spotipy
from spotify_auth import add_song_to_playlist
import sounddevice as sd
import scipy.io.wavfile as wav
import tempfile, os
import asyncio
from shazamio import Shazam

class voiceRecognitionTool:
    def __init__(self, root, sp: spotipy.Spotify):
        self.root = root
        self.sp = sp
        self.recognizer = sr.Recognizer()

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
        
        # microphone button
        tk.Button(self.root, text="🎙️\nListen via Microphone",
                  font=("Helvetica", 13, "bold"),
                  bg="#0f3460", fg="white",
                  width=28, height=2,
                  command=self.listen_mic).pack(pady=15)
        
        # system audio button
        tk.Button(self.root, text="🖥️\nDetect System Audio",
                  font=("Helvetica", 13, "bold"),
                  bg="#0f3460", fg="white",
                  width=28, height=2,
                  command=self.listen_system).pack(pady=5)
        
        # status display
        self.status_var = tk.StringVar(value="Ready...")
        tk.Label(self.root, textvariable=self.status_var,
                 font=("Helvetica", 11), bg="#1a1a2e",
                 fg="#1DB954", wraplength=420).pack(pady=20)
        
        # result box
        self.result_box = tk.Text(self.root, height=4, width=50,
                                   bg="#16213e", fg="white",
                                   font=("Helvetica", 11),
                                   state="disabled", wrap="word")
        self.result_box.pack(pady=5)

    def set_status(self,msg):
        self.root.after(0, lambda: self.status_var.set(msg))   

    def show_result(self, text):
        def update():
            self.result_box.config(state="normal")
            self.result_box.delete("1.0", "end")
            self.result_box.insert("end", text)
            self.result_box.config(state="disabled")
        self.root.after(0, update)

    # Shazam-only processor
    def _process_audio(self, wav_path):
        self.set_status("🎵 Identifying with Shazam...")
        try:
            # Create a fresh event loop for this background thread to avoid
            # "This event loop is already running" errors on Windows/macOS
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                song_info = loop.run_until_complete(self._recognize_with_shazam(wav_path))
            finally:
                loop.close()

            if song_info:
                self.set_status(f"✅ Shazam found: {song_info}")
                self._search_spotify(song_info)
            else:
                self.set_status("❌ Shazam couldn't identify the song.\nTry clearer/louder audio.")
        except Exception as e:
            self.set_status(f"Shazam error: {str(e)}")
        finally:
            if os.path.exists(wav_path):
                os.unlink(wav_path)

    async def _recognize_with_shazam(self, audio_path: str):
        """Real Shazam fingerprinting (async)."""
        shazam = Shazam()
        result = await shazam.recognize(audio_path) # result = await shazam.recognize_song(audio_path) did not work
        
        if result and "track" in result:
            track = result["track"]
            title = track.get("title", "")
            artist = track.get("subtitle", "")
            if not artist and track.get("artists"):
                artist = track["artists"][0].get("name", "")
            return f"{title} by {artist}" if title else None
        return None
    
    # microphone listening
    def listen_mic(self):
        threading.Thread(target=self._mic_worker, daemon=True).start()
    
    def _mic_worker(self):
        # print(sr.Microphone.list_microphone_names())  # run once to see your devices
        self.set_status("🎙️ Recording via microphone (8 seconds)...\nPlay the song near your mic!")
        try:
            sample_rate = 44100
            duration = 10

            recording = sd.rec(int(duration * sample_rate),
                            samplerate=sample_rate,
                            channels=1,
                            dtype='int16')
            sd.wait()

            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            wav.write(tmp.name, sample_rate, recording)

            self._process_audio(tmp.name)

        except Exception as e:
            self.set_status(f"Mic Error: {e}")

    # system audio capture
    def listen_system(self):
        threading.Thread(target=self._system_audio_worker, daemon=True).start()

    def _system_audio_worker(self):
        try:
            self.set_status("Recording system audio 🎤...")
            sample_rate = 44100
            duration = 10 # seconds

            # record audio from default input
            recording = sd.rec(int(duration * sample_rate),
                               samplerate=sample_rate,
                               channels=1,
                               dtype='int16')
            sd.wait() # waits until recording is finished

            # saves it as a temp .wav file in order to search it
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            wav.write(tmp.name, sample_rate, recording)

            self._process_audio(tmp.name)

        except Exception as e:
            self.set_status(f"System audio error: {e}\n"
                            "Perhaps: Enable 'Stereo Mix' in Windows sound settings.")
            
    def _search_spotify(self, query: str):
        # This is called from a background thread — schedule onto the main thread
        self.root.after(0, lambda: self._do_search(query))

    def _do_search(self, query: str):
        """Runs on the main thread."""
        self.set_status(f"🔎 Searching Spotify for: '{query}'")
        try:
            results = self.sp.search(q=query, type="track", limit=1)
            tracks = results.get("tracks", {}).get("items", [])

            if not tracks:
                self.set_status("❌ No matching song found on Spotify.")
                return

            track = tracks[0]
            name = track["name"]
            artist = track["artists"][0]["name"]
            uri = track["uri"]

            self.show_result(f"🎵 Found: {name} by {artist}")
            self.set_status("✅ Song Found!")
            self._ask_to_save(name, artist, uri)
        except Exception as e:
            self.set_status(f"Spotify error: {e}")

    def _ask_to_save(self, name, artist, uri):
        answer = messagebox.askyesno("Add to Playlist?",
                                     f"Found: {name} by {artist}\n\nAdd this to your 'ProjectSongs' playlist?")
        
        if answer:
            try:
                add_song_to_playlist(self.sp, uri)
                messagebox.showinfo("Added! ✅", f"'{name}' added to ProjectSongs!")
            except Exception as e:
                messagebox.showerror("Error ❌", f"Failed to add song:\n{e}")