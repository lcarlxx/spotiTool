import tkinter as tk
from tkinter import messagebox
import speech_recognition as sr
import threading
import spotipy
from spotify_auth import add_song_to_playlist

import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile, os

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
        self.result_box.config(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("end", text)
        self.result_box.config(state="disabled")

    # microphone listening
    def listen_mic(self):
        threading.Thread(target=self._mic_worker, daemon=True).start()
    
    def _mic_worker(self):
        # print(sr.Microphone.list_microphone_names())  # run once to see your devices
        self.set_status("🎙️ Listening... Sing or play a song!")
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=15)
            
            self.set_status("🔍 Recognizing...")
            text = self.recognizer.recognize_google(audio)
            self.set_status(f"You said: '{text}'")
            self._search_spotify(text)
        except sr.WaitTimeoutError:
            self.set_status("⏰ Timed out. Try again.")
        except sr.UnknownValueError:
            self.set_status("❓ Couldn't understand audio. Try again.")
        except Exception as e:
            self.set_status(f"Error: {e}")

    # system audio capture
    def listen_system(self):
        threading.Thread(target=self._system_audio_worker, daemon=True).start()

    def _system_audio_worker(self):
        try:
            sample_rate = 44100
            duration = 8 # seconds

            # record audio from default input
            recording = sd.rec(int(duration * sample_rate),
                               samplerate=sample_rate,
                               channels=2,
                               dtype='int16')
            sd.wait() # waits until recording is finished

            # saves it as a temp .wav file in order to search it
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            wav.write(tmp.name, sample_rate, recording)

            # recognising...
            self.set_status("🔍 Analyzing audio...")
            with sr.AudioFile(tmp.name) as source:
                audio = self.recognizer.record(source)

            os.unlink(tmp.name) # clean up temp file

            text = self.recognizer.recognize_google(audio)
            self.set_status(f"Detected: '{text}'")
            self._search_spotify(text)
        except Exception as e:
            self.set_status(f"System audio error: {e}\n"
                            "Perhaps: Enable 'Stereo Mix' in Windows sound settings.")
            
    def _search_spotify(self, query: str):
        def do_search():
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
                self.set_status("Song Found!")
                # ask user if they should add it to ProjectSongs
                self.root.after(0, lambda: self._ask_to_save(name, artist, uri))
            except Exception as e:
                self.set_status(f"Spotify error: {e}")
        self.root.after(0, do_search)    

    def _ask_to_save(self, name, artist, uri):
        answer = messagebox.askyesno("Add to Playlist?",
                                     f"Found: {name} by {artist}\n\nAdd this to your 'ProjectSongs' playlist?")
        
        if answer:
            add_song_to_playlist(self.sp, uri)
            messagebox.showinfo("Added! ✅", f"'{name}' added to ProjectSongs!")