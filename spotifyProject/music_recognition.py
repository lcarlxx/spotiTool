import asyncio
import hashlib
import io
import json
import os
import tempfile
import threading
from datetime import datetime
from queue import Queue

import customtkinter as ctk
from tkinter import messagebox
import requests
import wave
import sounddevice as sd
import spotipy
from PIL import Image
from requests.adapters import HTTPAdapter
from shazamio import Shazam
from urllib.parse import urlparse
from urllib3.util.retry import Retry

from .config import USER_DATA_DIR
from .spotify_auth import add_song_to_playlist
from .auth import get_user_playlist, set_user_playlist

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


def extract_spotify_uri(url: str) -> str | None:
    raw = (url or '').strip()
    if not raw:
        return None
    if raw.startswith('spotify:'):
        parts = raw.split(':')
        if len(parts) >= 3 and parts[2]:
            return f'spotify:{parts[1]}:{parts[2]}'
    try:
        path = urlparse(raw).path
        parts = [p for p in path.split('/') if p]
        if len(parts) >= 2:
            return f'spotify:{parts[0]}:{parts[1].split("?")[0]}'
    except Exception:
        pass
    if len(raw) == 22 and raw.isalnum():
        return f'spotify:playlist:{raw}'
    return None


def _write_wav(path: str, samplerate: int, recording) -> None:
    """Write a mono int16 numpy recording to a WAV file using the stdlib."""
    with wave.open(path, 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(samplerate)
        handle.writeframes(recording.tobytes())


def _find_system_audio_device() -> int | None:
    for index, device in enumerate(sd.query_devices()):
        name = device.get('name', '').lower()
        if any(keyword in name for keyword in ['stereo mix', 'loopback', 'what you hear']):
            return index
    return None


def _extract_cover_url(track: dict) -> str | None:
    images = track.get('images', {})
    if isinstance(images, dict):
        return images.get('coverart') or images.get('coverart400')
    return None


def _extract_spotify_uri(track: dict) -> str | None:
    hub = track.get('hub', {})
    for provider in hub.get('providers', []):
        if provider.get('type') == 'SPOTIFY':
            for action in provider.get('actions', []):
                uri = action.get('uri', '')
                if uri.startswith('spotify:track:'):
                    return uri
                if '/track/' in uri:
                    track_id = uri.split('/track/')[-1].split('?')[0]
                    return f'spotify:track:{track_id}'
    return None


async def _recognize_with_shazam(audio_path: str) -> dict | None:
    shazam = Shazam()
    try:
        result = await shazam.recognize(audio_path)
    except Exception:
        return None
    finally:
        # Release the aiohttp session, otherwise Python warns about
        # "Unclosed client session" on exit.
        try:
            await shazam.close()
        except Exception:
            pass
    if not result or 'track' not in result:
        return None
    track = result['track']
    return {
        'title': track.get('title', '').strip(),
        'artist': track.get('subtitle', '').strip(),
        'uri': _extract_spotify_uri(track),
        'cover_url': _extract_cover_url(track),
    }


def record_audio(duration: int = 6, samplerate: int = 44100, source: str = 'system') -> str:
    """Record audio and return the path to a temporary mono WAV file.

    source='system' uses the loopback device (whatever the PC is playing);
    source='mic' uses the default microphone.
    """
    if source == 'system':
        device = _find_system_audio_device()
        if device is None:
            raise RuntimeError(
                "No system audio loopback device found. Enable 'Stereo Mix' / "
                "'What U Hear' in Windows sound settings, or use source='mic'."
            )
    else:
        device = None  # default input device

    recording = sd.rec(int(duration * samplerate), samplerate=samplerate,
                       channels=1, dtype='int16', device=device)
    sd.wait()

    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    _write_wav(tmp.name, samplerate, recording)
    return tmp.name


def recognize_audio(duration: int = 6, samplerate: int = 44100,
                    source: str = 'system') -> dict | None:
    """Record audio, fingerprint it with Shazam, and return the match (or None)."""
    path = record_audio(duration, samplerate, source)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_recognize_with_shazam(path))
        finally:
            loop.close()
            asyncio.set_event_loop(None)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


class MusicRecognitionTool:
    def __init__(self, root, sp: spotipy.Spotify, username: str):
        self.root = root
        self.sp = sp
        self.username = username
        self.USER_DATA_DIR = USER_DATA_DIR
        self.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.RECENT_SONGS_FILE = self.USER_DATA_DIR / 'recent_songs.json'
        self.CACHE_DIR = self.USER_DATA_DIR / 'cover_cache'
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

        self.recent_songs = self.load_recent_songs()
        self.cover_images = []
        self.image_cache = {}
        self.load_queue = Queue()
        self.stop_loader = False

        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.3)
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        self.root.title('Music Recognition 🎙️')
        self.root.geometry('550x650')
        self.root.configure(fg_color='#1a1a2e')
        self.root.resizable(False, False)

        self._start_image_loader()
        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(self.root, text='Music Recognition 🎙️',
                     font=ctk.CTkFont('Helvetica', 18, 'bold'), fg_color='#1a1a2e', text_color='#1DB954').pack(pady=20)

        ctk.CTkLabel(self.root, text='Tap a button to identify a song',
                     font=ctk.CTkFont('Helvetica', 11), fg_color='#1a1a2e', text_color='#aaaaaa').pack(pady=(0, 10))

        ctk.CTkButton(self.root, text='🎙️\nListen via Microphone',
                      font=ctk.CTkFont('Helvetica', 13, 'bold'), fg_color='#0f3460', text_color='white',
                      width=280, height=52, command=self.listen_mic).pack(pady=5)

        ctk.CTkButton(self.root, text='🖥️\nDetect System Audio',
                      font=ctk.CTkFont('Helvetica', 13, 'bold'), fg_color='#0f3460', text_color='white',
                      width=280, height=52, command=self.listen_system).pack(pady=5)

        self.playlist_label = ctk.CTkLabel(self.root, text='', font=ctk.CTkFont('Helvetica', 9),
                                           fg_color='#1a1a2e', text_color='#aaaaaa')
        self.playlist_label.pack(pady=(5, 0))
        self.update_playlist_display()

        ctk.CTkButton(self.root, text='🔄 Change Playlist?', font=ctk.CTkFont('Helvetica', 11),
                      fg_color='#16213e', text_color='white', width=180,
                      command=self.change_playlist_dialog).pack(pady=(10, 5))

        ctk.CTkButton(self.root, text='Return to Homepage', font=ctk.CTkFont('Helvetica', 11),
                      fg_color='#535353', text_color='white', width=180,
                      command=self.go_back_to_home).pack(pady=5)

        self.status_var = ctk.StringVar(value='Ready...')
        ctk.CTkLabel(self.root, textvariable=self.status_var,
                     font=ctk.CTkFont('Helvetica', 11), fg_color='#1a1a2e', text_color='#1DB954',
                     wraplength=480, justify='center').pack(pady=10)

        ctk.CTkLabel(self.root, text='📜 Recently Discovered Songs',
                     font=ctk.CTkFont('Helvetica', 14, 'bold'), fg_color='#1a1a2e', text_color='#1DB954').pack(pady=(15, 5))

        list_frame = ctk.CTkFrame(self.root, fg_color='#1a1a2e')
        list_frame.pack(pady=5, padx=30, fill='both', expand=True)

        self.recent_scrollable = ctk.CTkScrollableFrame(list_frame, fg_color='#1a1a2e')
        self.recent_scrollable.pack(fill='both', expand=True)

        self.update_recent_songs_list()

    def set_status(self, msg: str):
        self.root.after(0, lambda: self.status_var.set(msg))

    def add_recent_song(self, title: str, artist: str, uri: str, cover_url: str | None = None):
        song_entry = {
            'title': title,
            'artist': artist,
            'uri': uri,
            'cover_url': cover_url,
            'timestamp': datetime.now().isoformat(),
        }
        self.recent_songs = [s for s in self.recent_songs if s['uri'] != uri]
        self.recent_songs.insert(0, song_entry)
        self.recent_songs = self.recent_songs[:20]
        self.save_recent_songs()
        self.update_recent_songs_list()

    def load_recent_songs(self) -> list:
        if not self.RECENT_SONGS_FILE.exists():
            return []
        try:
            return json.loads(self.RECENT_SONGS_FILE.read_text(encoding='utf-8'))
        except Exception:
            return []

    def save_recent_songs(self) -> None:
        try:
            self.RECENT_SONGS_FILE.write_text(json.dumps(self.recent_songs, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as exc:
            print(f'Failed to save recent songs: {exc}')

    def _start_image_loader(self):
        def loader_worker():
            while not self.stop_loader:
                try:
                    cover_frame, cover_url, icon_label = self.load_queue.get(timeout=0.5)
                    if not cover_frame.winfo_exists():
                        self.load_queue.task_done()
                        continue
                    cache_key = hashlib.md5(cover_url.encode('utf-8')).hexdigest()
                    cache_path = self.CACHE_DIR / f'{cache_key}.jpg'
                    img = None
                    if cache_key in self.image_cache:
                        img = self.image_cache[cache_key]
                    elif cache_path.exists():
                        try:
                            img = Image.open(cache_path).resize((64, 64), Image.Resampling.LANCZOS)
                            self.image_cache[cache_key] = img
                        except Exception:
                            cache_path.unlink(missing_ok=True)
                    else:
                        try:
                            response = self.session.get(cover_url, timeout=3)
                            response.raise_for_status()
                            img = Image.open(io.BytesIO(response.content)).resize((64, 64), Image.Resampling.LANCZOS)
                            img.save(cache_path, 'JPEG', quality=95)
                            self.image_cache[cache_key] = img
                        except Exception as exc:
                            print(f'Cover download failed for {cover_url}: {exc}')
                    if img and cover_frame.winfo_exists():
                        def update_ui(cf, pil_img):
                            if not cf.winfo_exists():
                                return
                            ctk_img = ctk.CTkImage(light_image=pil_img, size=(64, 64))
                            self.cover_images.append(ctk_img)
                            for child in cf.winfo_children():
                                child.destroy()
                            ctk.CTkLabel(cf, image=ctk_img, fg_color='#0f3460', text='').pack(fill='both', expand=True)
                        self.root.after(0, lambda cf=cover_frame, i=img: update_ui(cf, i))
                    self.load_queue.task_done()
                except Exception:
                    continue
        self.loader_thread = threading.Thread(target=loader_worker, daemon=True)
        self.loader_thread.start()

    def update_recent_songs_list(self):
        def update():
            for widget in self.recent_scrollable.winfo_children():
                widget.destroy()
            self.cover_images.clear()
            for idx, song in enumerate(self.recent_songs):
                song_frame = ctk.CTkFrame(self.recent_scrollable, fg_color='#16213e')
                song_frame.pack(fill='x', pady=6, padx=8)
                cover_url = song.get('cover_url')
                cover_frame = ctk.CTkFrame(song_frame, fg_color='#415347', width=72, height=72)
                cover_frame.pack(side='left', padx=(0, 15))
                cover_frame.pack_propagate(False)
                icon_label = ctk.CTkLabel(cover_frame, text='🎵', font=ctk.CTkFont('Helvetica', 30),
                                          fg_color='#0f3460', text_color='#555555')
                icon_label.pack(expand=True)
                if cover_url:
                    self.load_queue.put((cover_frame, cover_url, icon_label))
                info_frame = ctk.CTkFrame(song_frame, fg_color='#16213e')
                info_frame.pack(side='left', fill='x', expand=True)
                ctk.CTkLabel(info_frame, text=f'{idx + 1}. {song["title"]}',
                             fg_color='#16213e', text_color='white', font=ctk.CTkFont('Helvetica', 11, 'bold'), anchor='w').pack(anchor='w', pady=(0, 2))
                ctk.CTkLabel(info_frame, text=song['artist'],
                             fg_color='#16213e', text_color='#aaaaaa', font=ctk.CTkFont('Helvetica', 10), anchor='w').pack(anchor='w')
        self.root.after(0, update)

    def _process_audio(self, wav_path: str):
        self.set_status('🎵 Identifying with Shazam...')
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_dict = loop.run_until_complete(_recognize_with_shazam(wav_path))
            finally:
                loop.close()
                asyncio.set_event_loop(None)
        except Exception as exc:
            self.set_status(f'❌ Recognition failed: {exc}')
            return
        finally:
            try:
                if os.path.exists(wav_path):
                    os.remove(wav_path)
            except OSError:
                pass
        if not result_dict or not result_dict.get('title'):
            self.set_status('❌ Could not identify the song.\nTry louder or clearer audio.')
            return
        title = result_dict['title']
        artist = result_dict['artist']
        uri = result_dict.get('uri')
        cover_url = result_dict.get('cover_url')
        self.set_status(f'✅ Identified: {title} by {artist}')
        self.add_recent_song(title, artist, uri or '', cover_url)
        self.root.after(0, lambda: self._ask_to_save(title, artist, uri or ''))

    def _do_search(self, title: str, artist: str):
        try:
            results = self.sp.search(q=f'track:"{title}" artist:"{artist}"', type='track', limit=5, market='US')
            tracks = results.get('tracks', {}).get('items', [])
            if not tracks:
                results = self.sp.search(q=f'{title} {artist}', type='track', limit=5, market='US')
                tracks = results.get('tracks', {}).get('items', [])
            if not tracks:
                self.set_status('❌ No matching track found on Spotify.')
                return
            best = tracks[0]
            name = best['name']
            artist_name = best['artists'][0]['name']
            uri = best['uri']
            cover_url = best.get('album', {}).get('images', [])[-1].get('url') if best.get('album', {}).get('images') else None
            self.set_status(f'✅ Found: {name} by {artist_name}')
            self.add_recent_song(name, artist_name, uri, cover_url)
            self._ask_to_save(name, artist_name, uri)
        except Exception as exc:
            self.set_status(f'❌ Spotify search error: {exc}')

    def listen_mic(self):
        threading.Thread(target=self._mic_worker, daemon=True).start()

    def _mic_worker(self):
        self.set_status('🎙️ Recording via microphone...\nPlay the song near your mic!')
        try:
            fs = 44100
            duration = 6
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                wav_path = tmp.name
            _write_wav(wav_path, fs, recording)
            self._process_audio(wav_path)
        except Exception as exc:
            self.set_status(f'❌ Mic Error: {exc}')

    def listen_system(self):
        threading.Thread(target=self._system_audio_worker, daemon=True).start()

    def _system_audio_worker(self):
        self.set_status('🖥️ Recording system audio...')
        try:
            device = _find_system_audio_device()
            if device is None:
                self.set_status('❌ No system audio device found.\nEnable Stereo Mix in Windows sound settings.')
                return
            fs = 44100
            duration = 6
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16', device=device)
            sd.wait()
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                wav_path = tmp.name
            _write_wav(wav_path, fs, recording)
            self._process_audio(wav_path)
        except Exception as exc:
            self.set_status(f'❌ System Audio Error: {exc}')

    def _resolve_uri(self, name: str, artist: str, uri: str):
        """Return a valid spotify:track: URI, searching Spotify as fallback if needed."""
        if uri and uri.startswith('spotify:track:'):
            return uri

        # Shazam didn't give us a URI — search Spotify for it
        self.set_status('🔍 Looking up track on Spotify...')
        try:
            results = self.sp.search(q=f'track:"{name}" artist:"{artist}"', type='track', limit=5)
            tracks = results.get('tracks', {}).get('items', [])
            if not tracks:
                results = self.sp.search(q=f'{name} {artist}', type='track', limit=5)
                tracks = results.get('tracks', {}).get('items', [])
            if tracks:
                return tracks[0]['uri']
        except Exception as exc:
            self.set_status(f'❌ Spotify search failed: {exc}')
        return None

    def _ask_to_save(self, name: str, artist: str, uri: str):
        current_playlist = get_user_playlist(self.username)
        playlist_text = 'your selected playlist' if current_playlist else "your 'ProjectSongs' playlist"
        answer = messagebox.askyesno(
            'Add to Playlist?',
            f'Found: {name} by {artist}\n\nAdd this song to {playlist_text}?'
        )
        if not answer:
            return

        resolved_uri = self._resolve_uri(name, artist, uri)
        if not resolved_uri:
            messagebox.showerror(
                'Not Found',
                f"Could not find '{name}' by {artist} on Spotify.\n"
                "The track may not be available in your region."
            )
            return

        try:
            used_id = add_song_to_playlist(self.sp, resolved_uri, playlist_uri=current_playlist)
            try:
                playlist_name = self.sp.playlist(used_id).get('name', 'ProjectSongs')
            except Exception:
                playlist_name = 'ProjectSongs'
            messagebox.showinfo('Success ✅', f"'{name}' was added to {playlist_name}!")
        except Exception as exc:
            messagebox.showerror('Error', f'Failed to add song:\n{exc}')

    def update_playlist_display(self):
        current_playlist = get_user_playlist(self.username)
        if current_playlist:
            try:
                playlist = self.sp.playlist(current_playlist)
                self.playlist_label.configure(text=f'📁 Active Playlist: {playlist["name"]}')
            except Exception:
                playlist_id = current_playlist.split(':')[-1]
                self.playlist_label.configure(text=f'📁 Active Playlist: {playlist_id[:12]}...')
        else:
            self.playlist_label.configure(text='📁 Using default playlist (ProjectSongs)')

    def change_playlist_dialog(self):
        popup = ctk.CTkToplevel(self.root)
        popup.title('Change Playlist')
        popup.geometry('420x200')
        popup.configure(fg_color='#1a1a2e')
        popup.resizable(False, False)
        popup.grab_set()
        popup.transient(self.root)

        ctk.CTkLabel(popup, text='Change Playlist', font=ctk.CTkFont('Helvetica', 14, 'bold'),
                     fg_color='#1a1a2e', text_color='#1DB954').pack(pady=(18, 4))
        ctk.CTkLabel(popup, text='Paste your Spotify Playlist link:',
                     font=ctk.CTkFont('Helvetica', 10), fg_color='#1a1a2e', text_color='#aaaaaa').pack()

        url_var = ctk.StringVar()
        entry = ctk.CTkEntry(popup, textvariable=url_var, font=ctk.CTkFont('Helvetica', 11),
                             width=300, fg_color='#16213e', text_color='white')
        entry.pack(pady=10, padx=20)
        entry.focus_set()

        def confirm():
            url = url_var.get().strip()
            if not url:
                popup.destroy()
                return
            uri = extract_spotify_uri(url)
            if not uri or not uri.startswith('spotify:playlist:'):
                messagebox.showerror('Invalid Link', '❌ Please paste a valid Spotify playlist link.', parent=popup)
                return
            try:
                playlist = self.sp.playlist(uri)
                set_user_playlist(self.username, uri)
                self.update_playlist_display()
                popup.destroy()
                messagebox.showinfo('Playlist Changed ✅', f'Now adding songs to:\n{playlist["name"]}')
            except Exception as exc:
                messagebox.showerror('Error', f'Could not access playlist:\n{exc}', parent=popup)

        btn_frame = ctk.CTkFrame(popup, fg_color='#1a1a2e')
        btn_frame.pack(pady=4)
        ctk.CTkButton(btn_frame, text='Confirm', font=ctk.CTkFont('Helvetica', 11, 'bold'),
                      fg_color='#1DB954', text_color='black', width=120, command=confirm).pack(side='left', padx=8)
        ctk.CTkButton(btn_frame, text='Cancel', font=ctk.CTkFont('Helvetica', 11),
                      fg_color='#535353', text_color='white', width=120, command=popup.destroy).pack(side='left', padx=8)
        popup.bind('<Return>', lambda e: confirm())
        popup.bind('<Escape>', lambda e: popup.destroy())

    def go_back_to_home(self):
        self.stop_loader = True
        self.root.destroy()


if __name__ == '__main__':
    from .spotify_auth import get_spotify_client

    root = ctk.CTk()
    app = MusicRecognitionTool(root, get_spotify_client(), 'test_user')
    root.mainloop()
