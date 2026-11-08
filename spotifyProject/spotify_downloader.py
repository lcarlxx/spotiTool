import customtkinter as ctk
from tkinter import messagebox
import spotipy
import os
import re
import shutil
import tempfile
import threading
import time
import urllib.request
import urllib.parse
import requests
from yt_dlp import YoutubeDL
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TPOS, APIC, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover
from mutagen.wave import WAVE

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('green')


class ConversionTool:
    def __init__(self, root, sp: spotipy.Spotify):
        self.root = root
        self.sp = sp
        self.downloading = False
        self._pending_url = None

        self.root.title("Spotify to FLAC 🎵")
        self.root.geometry("720x660")
        self.root.configure(fg_color="#232723")
        self.root.resizable(True, True)
        self.root.minsize(600, 620)

        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(self.root, text="Spotify Audio Downloader",
                     font=ctk.CTkFont("Helvetica", 22, "bold"),
                     fg_color="#232723", text_color="#1db954").pack(pady=15)

        ctk.CTkLabel(self.root, text="High Quality Downloads (Best Available Audio)",
                     font=ctk.CTkFont("Helvetica", 11), fg_color="#232723", text_color="#aaaaaa").pack(pady=5)

        # Output Format Selector
        format_frame = ctk.CTkFrame(self.root, fg_color="#232723")
        format_frame.pack(pady=10)

        ctk.CTkLabel(format_frame, text="Output Format:",
                     font=ctk.CTkFont("Helvetica", 10, "bold"), fg_color="#232723", text_color="white").pack(side="left", padx=5)

        self.format_var = ctk.StringVar(value="FLAC (Lossless)")
        self.format_dropdown = ctk.CTkComboBox(
            format_frame,
            variable=self.format_var,
            values=[
                "FLAC (Lossless)",
                "MP3",
                "AAC 256kbps",
                "WAV"
            ],
            width=320
        )
        self.format_dropdown.pack(side="left", padx=5)
        self.format_dropdown.bind("<<ComboboxSelected>>", self.on_format_change)

        # MP3 Bitrate selector (hidden by default)
        self.bitrate_frame = ctk.CTkFrame(self.root, fg_color="#232723")
        self.bitrate_label = ctk.CTkLabel(self.bitrate_frame, text="MP3 Quality:",
                                         font=ctk.CTkFont("Helvetica", 10, "bold"), fg_color="#232723", text_color="white")
        self.bitrate_var = ctk.StringVar(value="320")
        self.bitrate_dropdown = ctk.CTkComboBox(
            self.bitrate_frame,
            variable=self.bitrate_var,
            values=[
                "128 kbps  –  Voice / Mobile  (~1 MB / min)",
                "256 kbps  –  Streaming quality  (~2 MB / min)",
                "320 kbps  –  Maximum quality  (~2.4 MB / min)"
            ],
            width=360
        )
        # Hide bitrate selector initially
        self.bitrate_frame.pack_forget()

        self.link_display = ctk.CTkLabel(self.root, text="No link set",
                                         font=ctk.CTkFont("Helvetica", 10), fg_color="#232723", text_color="#aaaaaa")
        self.link_display.pack(pady=(20, 2))

        ctk.CTkButton(self.root, text="📋 Paste Spotify Link",
                      font=ctk.CTkFont("Helvetica", 11), fg_color="#16213e", text_color="white",
                      width=180, command=self.open_link_popup).pack(pady=(4, 20))

        self.progress = ctk.CTkProgressBar(self.root, orientation="horizontal", width=550)
        self.progress.set(0)
        self.progress.pack(pady=20)

        self.status_label = ctk.CTkLabel(self.root, text="Ready — Paste a album/track link (currently incapable of album downloads)",
                                         font=ctk.CTkFont("Helvetica", 14), fg_color="#232723", text_color="white")
        self.status_label.pack(pady=5)

        self.track_label = ctk.CTkLabel(self.root, text="", font=ctk.CTkFont("Helvetica", 16),
                                        fg_color="#232723", text_color="#aaaaaa", wraplength=660)
        self.track_label.pack(pady=5)

        # ── Action buttons row ────────────────────────────────────────
        btn_row = ctk.CTkFrame(self.root, fg_color="#232723")
        btn_row.pack(pady=15)

        self.start_btn = ctk.CTkButton(
            btn_row, text="▶️ Start Download",
            font=ctk.CTkFont("Helvetica", 12, "bold"),
            fg_color="#1DB954", text_color="black", width=180, height=40,
            command=self.start_download)
        self.start_btn.pack(side="left", padx=8)

        # Stop button — wired to self.downloading flag
        self.stop_btn = ctk.CTkButton(
            btn_row, text="⏹ Stop",
            font=ctk.CTkFont("Helvetica", 12, "bold"),
            fg_color="#c0392b", text_color="white", width=120, height=40,
            command=self.stop_download, state="disabled")
        self.stop_btn.pack(side="left", padx=8)

        ctk.CTkButton(self.root, text="Open Output Folder", font=ctk.CTkFont("Helvetica", 10),
                      fg_color="#16213e", text_color="white",
                      width=180, command=self.open_output_folder).pack(pady=10)

    def on_format_change(self, event=None):
        selected = self.format_dropdown.get().lower()
        if "mp3" in selected:
            self.bitrate_label.pack(side="left", padx=5)
            self.bitrate_dropdown.pack(side="left", padx=5)
            self.bitrate_frame.pack(pady=5)
        else:
            self.bitrate_frame.pack_forget()
            self.bitrate_label.pack_forget()
            self.bitrate_dropdown.pack_forget()

    # ── Link popup ────────────────────────────────────────────────────

    def open_link_popup(self):
        popup = ctk.CTkToplevel(self.root)
        popup.title("Paste Spotify Link")
        popup.geometry("460x200")
        popup.configure(fg_color="#232723")
        popup.grab_set()
        popup.transient(self.root)

        ctk.CTkLabel(popup, text="Paste Spotify Link", font=ctk.CTkFont("Helvetica", 14, "bold"),
                     fg_color="#232723", text_color="#1db954").pack(pady=(18, 4))
        ctk.CTkLabel(popup, text="Playlist, Album, or Track URL",
                     font=ctk.CTkFont("Helvetica", 10), fg_color="#232723", text_color="#aaaaaa").pack()

        url_var = ctk.StringVar()
        entry = ctk.CTkEntry(popup, textvariable=url_var, font=ctk.CTkFont("Helvetica", 11),
                             width=420, fg_color="#16213e", text_color="white")
        entry.pack(pady=10, ipady=5, padx=20)
        entry.focus_set()

        def confirm():
            url = url_var.get().strip()
            if url:
                self._pending_url = url
                short = url if len(url) <= 60 else url[:57] + "..."
                self.link_display.configure(text=f"🔗 {short}")
            popup.destroy()

        btn_frame = ctk.CTkFrame(popup, fg_color="#232723")
        btn_frame.pack(pady=4)
        ctk.CTkButton(btn_frame, text="Confirm", font=ctk.CTkFont("Helvetica", 11, "bold"),
                      fg_color="#1DB954", text_color="black", width=120, command=confirm).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Cancel", font=ctk.CTkFont("Helvetica", 11),
                      fg_color="#535353", text_color="white", width=120, command=popup.destroy).pack(side="left", padx=8)

        popup.bind("<Return>", lambda e: confirm())
        popup.bind("<Escape>", lambda e: popup.destroy())

    # ── Helpers ───────────────────────────────────────────────────────

    def sanitize_filename(self, name: str) -> str:
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", name).strip()
        return re.sub(r'[\.\s]+$', '', sanitized)[:150]

    def normalize_string(self, s: str) -> str:
        """Normalize string for fuzzy matching."""
        if not s:
            return ""
        s = s.lower()
        for pat in [r'\(remastered.*?\)', r'\[remastered.*?\]', r'\(remix.*?\)',
                    r'\(version.*?\)', r'\(feat.*?\)', r'\(ft.*?\)', r'\(official.*?\)']:
            s = re.sub(pat, '', s, flags=re.IGNORECASE)
        s = re.sub(r'[^\w\s]', '', s)
        return re.sub(r'\s+', ' ', s).strip()

    def open_output_folder(self):
        output_dir = os.path.join(os.getcwd(), "Spotify FLAC Downloads")
        os.makedirs(output_dir, exist_ok=True)
        try:
            os.startfile(output_dir)
        except AttributeError:
            os.system(f'open "{output_dir}"' if os.name == 'posix' else f'xdg-open "{output_dir}"')

    # ── Download control ──────────────────────────────────────────────

    def start_download(self):
        if self.downloading:
            messagebox.showwarning("Busy", "Download already in progress.")
            return
        if not self._pending_url:
            messagebox.showwarning("No Link", "Paste a Spotify link first.")
            return

        self.downloading = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.set(0)
        threading.Thread(target=self.download_collection,
                         args=(self._pending_url,), daemon=True).start()

    def stop_download(self):
        """Signal the download loop to stop after the current track finishes."""
        self.downloading = False
        self.update_status("Stopping after current track…")

    def _reset_buttons(self):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    # ── Spotify metadata fetching ─────────────────────────────────────

    def get_playlist_tracks(self, url: str):
        """
        Return (collection_name, [track_dict, …]) for a playlist, album, or track.

        Each track_dict has:  name, artist, album, album_art, track_number, disc_number.
        Local files and podcast episodes are silently skipped.
        """
        try:
            if "playlist" in url:
                return self._fetch_playlist(url)
            elif "album" in url:
                return self._fetch_album(url)
            else:
                return self._fetch_track(url)
        except Exception as e:
            raise Exception(f"Failed to fetch Spotify data: {e}")

    def _is_playable_track(self, item) -> bool:
        """
        Return True only for real, streamable track objects.
        Filters out: None items, local files, podcast episodes, malformed tracks.

        IMPORTANT: for playlist items the Spotify API puts 'is_local' on the
        *wrapper* dict (item), NOT on item['track'].  Always check both levels.
        """
        if not item:
            return False
        # is_local lives on the playlist item wrapper — check it before unwrapping
        if item.get('is_local'):
            return False
        track = item.get('track') if isinstance(item, dict) and 'track' in item else item
        if not track:
            return False
        # Also guard against track-level is_local (some API versions set both)
        if track.get('is_local'):
            return False
        if track.get('type') == 'episode':  # podcast episode in playlist
            return False
        if not track.get('name'):           # completely empty / unavailable track
            return False
        if not track.get('artists'):        # malformed object
            return False
        return True

    def _track_dict(self, track, album_name: str, album_art_url,
                    track_number: int = 0, disc_number: int = 1) -> dict:
        return {
            'name':         track['name'],
            'artist':       track['artists'][0]['name'],
            'album':        album_name,
            'album_art':    album_art_url,
            'track_number': track_number,
            'disc_number':  disc_number,
        }

    def _fetch_playlist(self, url: str):
        playlist = self.sp.playlist(url)
        name = playlist['name']
        tracks = []

        self.update_status(f"Fetching playlist: {name}…")

        # sp.playlist_items() is the modern endpoint (/playlists/{id}/items).
        # The older sp.playlist_tracks() (/playlists/{id}/tracks) is deprecated
        # and behaves inconsistently with playlists that mix tracks and episodes.
        page = self.sp.playlist_items(url)
        position = 1

        while page:
            for item in page['items']:
                if not self._is_playable_track(item):
                    continue
                track = item['track']
                try:
                    art = None
                    if track.get('album') and track['album'].get('images'):
                        art = track['album']['images'][0]['url']
                    tracks.append(self._track_dict(
                        track,
                        album_name=track['album']['name'] if track.get('album') else '',
                        album_art_url=art,
                        track_number=position,
                    ))
                    position += 1
                except (KeyError, IndexError, TypeError) as e:
                    # One malformed item should never abort the whole playlist
                    print(f"  ⚠ Skipping malformed item in playlist: {e}")
                    continue

            # Paginate — Spotify returns max 100 items per page
            page = self.sp.next(page) if page.get('next') else None
            if page:
                time.sleep(0.1)     # gentle rate-limit respect

        self.update_status(f"Fetched {len(tracks)} tracks from \"{name}\"")
        return name, tracks

    def _fetch_album(self, url: str):
        """
        Fetch every track from an album with proper pagination.

        The top-level album object gives us the cover art; subsequent pages
        (sp.album_tracks) give us the actual track list.  Without pagination,
        albums with more than 50 tracks are silently truncated.
        """
        album = self.sp.album(url)
        name  = album['name']
        art   = album['images'][0]['url'] if album.get('images') else None
        tracks = []

        self.update_status(f"Fetching album: {name}…")

        # album['tracks'] is already a paging object — paginate it
        page = album['tracks']
        while page:
            for track in page['items']:
                if not track or not track.get('artists'):
                    continue                         # skip None / malformed entries
                tracks.append(self._track_dict(
                    track,
                    album_name=name,
                    album_art_url=art,
                    track_number=track.get('track_number', 0),
                    disc_number=track.get('disc_number', 1),
                ))

            # Paginate — rare but necessary for large / multi-disc releases
            page = self.sp.next(page) if page.get('next') else None
            if page:
                time.sleep(0.1)

        self.update_status(f"Fetched {len(tracks)} tracks from \"{name}\"")
        return name, tracks

    def _fetch_track(self, url: str):
        track = self.sp.track(url)
        art   = None
        if track.get('album') and track['album'].get('images'):
            art = track['album']['images'][0]['url']
        return track['name'], [self._track_dict(
            track,
            album_name=track['album']['name'] if track.get('album') else '',
            album_art_url=art,
            track_number=track.get('track_number', 0),
            disc_number=track.get('disc_number', 1),
        )]

    # ── YouTube search query builder ──────────────────────────────────

    def build_search_query(self, track: dict) -> str:
        """
        Return the best YouTube search string for a track.

        Uses Deezer's public search API as a metadata oracle to get a
        canonical title.  Falls back to raw Spotify metadata on any failure.

        NOTE: Deezer audio streams are Blowfish-encrypted and session-gated;
        there is no usable public download endpoint, so YouTube + yt-dlp
        is the only viable path.
        """
        track_norm  = self.normalize_string(track['name'])
        artist_norm = self.normalize_string(track['artist'])

        for query in [f"{track['artist']} {track['name']}",
                      f"{track['name']} {track['artist']}"]:
            try:
                url  = "https://api.deezer.com/search?q=" + urllib.parse.quote_plus(query)
                resp = requests.get(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'},
                    timeout=8
                )
                resp.raise_for_status()

                for result in resp.json().get('data', []):
                    if result.get('type') != 'track':
                        continue
                    if (
                        (track_norm  in self.normalize_string(result['title'])
                         or self.normalize_string(result['title'])  in track_norm)
                        and
                        (artist_norm in self.normalize_string(result['artist']['name'])
                         or self.normalize_string(result['artist']['name']) in artist_norm)
                    ):
                        return f"{result['artist']['name']} {result['title']} audio"

            except Exception as e:
                print(f"Deezer lookup skipped: {e}")

        return f"{track['artist']} {track['name']} audio"

    # ── Collection download loop ──────────────────────────────────────

    def download_collection(self, url: str):
            try:
                self.update_status("Fetching Spotify metadata…")
                playlist_name, tracks = self.get_playlist_tracks(url)
                total = len(tracks)

                if total == 0:
                    self.safe_after(lambda: messagebox.showwarning(
                        "Empty",
                        "No downloadable tracks found.\n\n"
                        "The playlist/album may contain only local files or podcast episodes."))
                    self.downloading = False
                    self.safe_after(self._reset_buttons)
                    return

                # Only create subfolder for playlists/albums, not single tracks
                base_output = os.path.join(os.getcwd(), "Spotify FLAC Downloads")
                os.makedirs(base_output, exist_ok=True)

                if total == 1:
                    # Single track - save directly to base folder
                    output_dir = base_output
                else:
                    # Playlist / Album - create dedicated subfolder
                    output_dir = os.path.join(
                        base_output,
                        self.sanitize_filename(playlist_name)
                    )
                    os.makedirs(output_dir, exist_ok=True)

                success, failed, skipped = 0, 0, 0
                failed_list = []

                for i, track in enumerate(tracks):
                    if not self.downloading:
                        break

                    self.update_track(f"{i+1}/{total}: {track['name']} — {track['artist']}")

                    try:
                        result = self.download_single_track(
                            self.build_search_query(track), track, output_dir)
                        if result == "skipped":
                            skipped += 1
                        else:
                            success += 1
                    except Exception as err: # Changed from 'e' to avoid confusion
                        print(f"  ✗ {track['name']}: {err}")
                        failed += 1
                        failed_list.append(f"{track['artist']} — {track['name']}")

                    self.update_progress((i + 1) / total * 100)

                # Final status update
                self.downloading = False
                status = f"Done! ✅ {success} | ❌ {failed}"
                self.update_status(status)
                
                # Use a local variable to store the message to avoid NameError in safe_after
                final_msg = (f"Downloaded to:\n{output_dir}\n\n"
                            f"Success:  {success}\nFailed:   {failed}")
                self.safe_after(lambda: messagebox.showinfo("Complete", final_msg))

            except Exception as e:
                self.downloading = False
                # Convert the error to a string immediately so it's captured for the lambda
                error_message = str(e)
                self.safe_after(lambda: messagebox.showerror("Error", error_message))
            finally:
                self.safe_after(self._reset_buttons)
                self.update_track("")
    # ── Single-track download ─────────────────────────────────────────

    def get_ydl_config(self, temp_file_template):
        format_selected = self.format_dropdown.get().lower()
        bitrate_text = self.bitrate_dropdown.get()
        bitrate = '320'
        if '128' in bitrate_text: bitrate = '128'
        elif '256' in bitrate_text: bitrate = '256'

        base_opts = {
            'format':           'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
            'outtmpl':          temp_file_template + '.%(ext)s',
            'quiet':            True,
            'no_warnings':      True,
            'retries':          5,
            'fragment_retries': 5,
            'ignoreerrors':     False,
            'noplaylist':       True,
            'playlist_items':   '1',
        }

        if 'flac' in format_selected:
            ext = 'flac'
            base_opts['postprocessors'] = [{
                'key':              'FFmpegExtractAudio',
                'preferredcodec':   'flac',
                'preferredquality': '0',
            }]
            base_opts['postprocessor_args'] = ['-vn', '-acodec', 'flac', '-compression_level', '8']

        elif 'aac' in format_selected:
            ext = 'm4a'
            base_opts['postprocessors'] = [{
                'key':              'FFmpegExtractAudio',
                'preferredcodec':   'aac',
                'preferredquality': '256',
            }]
            base_opts['postprocessor_args'] = ['-vn', '-acodec', 'aac', '-b:a', '256k']

        elif 'wav' in format_selected:
            ext = 'wav'
            base_opts['postprocessors'] = [{
                'key':              'FFmpegExtractAudio',
                'preferredcodec':   'wav',
            }]
            base_opts['postprocessor_args'] = ['-vn', '-acodec', 'pcm_s16le']

        else: # MP3
            ext = 'mp3'
            base_opts['postprocessors'] = [{
                'key':              'FFmpegExtractAudio',
                'preferredcodec':   'mp3',
                'preferredquality': bitrate,
            }]
            base_opts['postprocessor_args'] = ['-vn', '-acodec', 'libmp3lame', '-q:a', {'128':'7', '256':'2', '320':'0'}[bitrate]]

        return base_opts, ext

    def download_single_track(self, search_query: str, track: dict, output_dir: str):
        """
        Download best available audio from YouTube and encode in selected format.
        Returns "skipped" if file already exists, otherwise None.
        """
        base_name  = self.sanitize_filename(f"{track['artist']} - {track['name']}")
        ydl_opts, ext = self.get_ydl_config(base_name)

        final_file = os.path.join(output_dir, f"{base_name}.{ext}")

        if os.path.exists(final_file) and os.path.getsize(final_file) > 100_000:
            print(f"  ↩ Exists: {base_name}")
            return "skipped"

        temp_dir           = tempfile.mkdtemp(prefix="audio_dl_")
        temp_file_template = os.path.join(temp_dir, base_name)
        ydl_opts['outtmpl'] = temp_file_template + '.%(ext)s'

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"ytsearch1:{search_query}"])

            output_files = [f for f in os.listdir(temp_dir) if f.lower().endswith(f'.{ext}')]
            if not output_files:
                raise FileNotFoundError(f"yt-dlp produced no {ext} file — is ffmpeg on PATH?")

            temp_output = os.path.join(temp_dir, output_files[0])
            if os.path.getsize(temp_output) < 100_000:
                raise ValueError("Output file too small — likely a YouTube error page.")

            shutil.move(temp_output, final_file)
            self.embed_metadata(final_file, track)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ── Metadata embedding ────────────────────────────────────────────

    def embed_metadata(self, flac_file: str, track: dict):
        try:
            audio = FLAC(flac_file)
            audio.clear()
            audio['title']       = track['name']
            audio['artist']      = track['artist']
            audio['album']       = track.get('album', '')
            audio['albumartist'] = track['artist']

            # Track/disc numbers — essential for albums to sort correctly in any player
            if track.get('track_number'):
                audio['tracknumber'] = str(track['track_number'])
            if track.get('disc_number') and track['disc_number'] > 1:
                audio['discnumber'] = str(track['disc_number'])

            if track.get('album_art'):
                try:
                    req = urllib.request.Request(
                        track['album_art'],
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        art_data = resp.read()

                    pic        = Picture()
                    pic.data   = art_data
                    pic.type   = 3          # Front cover
                    pic.mime   = 'image/jpeg'
                    pic.width  = 640
                    pic.height = 640
                    pic.depth  = 24

                    audio.clear_pictures()
                    audio.add_picture(pic)
                except Exception as e:
                    print(f"  ⚠ Artwork skipped: {e}")

            audio.save()
        except Exception as e:
            print(f"  ⚠ Metadata error: {e}")

    # ── Thread-safe UI helpers ────────────────────────────────────────

    def safe_after(self, func):
        self.root.after(0, func)

    def update_status(self, message: str):
        self.safe_after(lambda: self.status_label.configure(text=message))

    def update_track(self, message: str):
        self.safe_after(lambda: self.track_label.configure(text=message))

    def update_progress(self, value: float):
        self.safe_after(lambda: self.progress.set(value / 100))


def sanitize_filename(name: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name).strip()
    return re.sub(r'[\.\s]+$', '', sanitized)[:150]


def normalize_string(s: str) -> str:
    if not s:
        return ''
    s = s.lower()
    for pat in [r'\(remastered.*?\)', r'\[remastered.*?\]', r'\(remix.*?\)',
                r'\(version.*?\)', r'\(feat.*?\)', r'\(ft.*?\)', r'\(official.*?\)']:
        s = re.sub(pat, '', s, flags=re.IGNORECASE)
    s = re.sub(r'[^\w\s]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def _is_playable_track(item) -> bool:
    if not item:
        return False
    if item.get('is_local'):
        return False
    track = item.get('track') if isinstance(item, dict) and 'track' in item else item
    if not track:
        return False
    if track.get('is_local'):
        return False
    if track.get('type') == 'episode':
        return False
    if not track.get('name'):
        return False
    if not track.get('artists'):
        return False
    return True


def _track_dict(track, album_name: str, album_art_url, track_number: int = 0, disc_number: int = 1) -> dict:
    return {
        'name':         track['name'],
        'artist':       track['artists'][0]['name'],
        'album':        album_name,
        'album_art':    album_art_url,
        'track_number': track_number,
        'disc_number':  disc_number,
    }


def _fetch_playlist(sp, url: str):
    playlist = sp.playlist(url)
    name = playlist['name']
    tracks = []

    page = sp.playlist_items(url)
    position = 1

    while page:
        for item in page['items']:
            if not _is_playable_track(item):
                continue
            track = item['track']
            try:
                art = None
                if track.get('album') and track['album'].get('images'):
                    art = track['album']['images'][0]['url']
                tracks.append(_track_dict(
                    track,
                    album_name=track['album']['name'] if track.get('album') else '',
                    album_art_url=art,
                    track_number=position,
                ))
                position += 1
            except (KeyError, IndexError, TypeError):
                continue

        page = sp.next(page) if page.get('next') else None
        if page:
            time.sleep(0.1)

    return name, tracks


def _fetch_album(sp, url: str):
    album = sp.album(url)
    name = album['name']
    art = album['images'][0]['url'] if album.get('images') else None
    tracks = []

    page = album['tracks']
    while page:
        for track in page['items']:
            if not track or not track.get('artists'):
                continue
            tracks.append(_track_dict(
                track,
                album_name=name,
                album_art_url=art,
                track_number=track.get('track_number', 0),
                disc_number=track.get('disc_number', 1),
            ))

        page = sp.next(page) if page.get('next') else None
        if page:
            time.sleep(0.1)

    return name, tracks


def _fetch_track(sp, url: str):
    track = sp.track(url)
    art = None
    if track.get('album') and track['album'].get('images'):
        art = track['album']['images'][0]['url']
    return track['name'], [_track_dict(
        track,
        album_name=track['album']['name'] if track.get('album') else '',
        album_art_url=art,
        track_number=track.get('track_number', 0),
        disc_number=track.get('disc_number', 1),
    )]


def get_playlist_tracks(sp, url: str):
    if 'playlist' in url:
        return _fetch_playlist(sp, url)
    if 'album' in url:
        return _fetch_album(sp, url)
    return _fetch_track(sp, url)


def build_search_query(track: dict) -> str:
    track_norm = normalize_string(track['name'])
    artist_norm = normalize_string(track['artist'])

    for query in [f"{track['artist']} {track['name']}", f"{track['name']} {track['artist']}"]:
        try:
            url = 'https://api.deezer.com/search?q=' + urllib.parse.quote_plus(query)
            resp = requests.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'},
                timeout=8
            )
            resp.raise_for_status()

            for result in resp.json().get('data', []):
                if result.get('type') != 'track':
                    continue
                if (
                    (track_norm in normalize_string(result['title'])
                     or normalize_string(result['title']) in track_norm)
                    and
                    (artist_norm in normalize_string(result['artist']['name'])
                     or normalize_string(result['artist']['name']) in artist_norm)
                ):
                    return f"{result['artist']['name']} {result['title']} audio"

        except Exception:
            continue

    return f"{track['artist']} {track['name']} audio"


def get_ydl_config(format_selected: str, bitrate: str, temp_file_template: str):
    base_opts = {
        'format':           'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
        'outtmpl':          temp_file_template + '.%(ext)s',
        'quiet':            True,
        'no_warnings':      True,
        'retries':          5,
        'fragment_retries': 5,
        'ignoreerrors':     False,
        'noplaylist':       True,
        'playlist_items':   '1',
    }

    if 'flac' in format_selected:
        ext = 'flac'
        base_opts['postprocessors'] = [{
            'key':              'FFmpegExtractAudio',
            'preferredcodec':   'flac',
            'preferredquality': '0',
        }]
        base_opts['postprocessor_args'] = ['-vn', '-acodec', 'flac', '-compression_level', '8']

    elif 'aac' in format_selected:
        ext = 'm4a'
        base_opts['postprocessors'] = [{
            'key':              'FFmpegExtractAudio',
            'preferredcodec':   'aac',
            'preferredquality': '256',
        }]
        base_opts['postprocessor_args'] = ['-vn', '-acodec', 'aac', '-b:a', '256k']

    elif 'wav' in format_selected:
        ext = 'wav'
        base_opts['postprocessors'] = [{
            'key':              'FFmpegExtractAudio',
            'preferredcodec':   'wav',
        }]
        base_opts['postprocessor_args'] = ['-vn', '-acodec', 'pcm_s16le']

    else:
        ext = 'mp3'
        base_opts['postprocessors'] = [{
            'key':              'FFmpegExtractAudio',
            'preferredcodec':   'mp3',
            'preferredquality': bitrate,
        }]
        base_opts['postprocessor_args'] = ['-vn', '-acodec', 'libmp3lame', '-q:a', {'128': '7', '256': '2', '320': '0'}[bitrate]]

    return base_opts, ext


def embed_metadata(audio_path: str, track: dict):
    ext = os.path.splitext(audio_path)[1].lower()
    art_data = None
    if track.get('album_art'):
        try:
            req = urllib.request.Request(
                track['album_art'],
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                art_data = resp.read()
        except Exception:
            art_data = None

    try:
        if ext == '.flac':
            audio = FLAC(audio_path)
            audio.clear()
            audio['title'] = track['name']
            audio['artist'] = track['artist']
            audio['album'] = track.get('album', '')
            audio['albumartist'] = track['artist']

            if track.get('track_number'):
                audio['tracknumber'] = str(track['track_number'])
            if track.get('disc_number') and track['disc_number'] > 1:
                audio['discnumber'] = str(track['disc_number'])

            if art_data:
                pic = Picture()
                pic.data = art_data
                pic.type = 3
                pic.mime = 'image/jpeg'
                pic.width = 640
                pic.height = 640
                pic.depth = 24
                audio.clear_pictures()
                audio.add_picture(pic)

            audio.save()
            return

        if ext == '.mp3':
            try:
                audio = MP3(audio_path, ID3=ID3)
            except ID3NoHeaderError:
                audio = MP3(audio_path)
                audio.add_tags()
            except Exception:
                audio = MP3(audio_path)

            if audio.tags is None:
                audio.add_tags()

            audio.tags.add(TIT2(encoding=3, text=track['name']))
            audio.tags.add(TPE1(encoding=3, text=track['artist']))
            audio.tags.add(TALB(encoding=3, text=track.get('album', '')))
            if track.get('track_number'):
                audio.tags.add(TRCK(encoding=3, text=str(track['track_number'])))
            if track.get('disc_number') and track['disc_number'] > 1:
                audio.tags.add(TPOS(encoding=3, text=str(track['disc_number'])))
            if art_data:
                audio.tags.add(APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=art_data,
                ))
            audio.save(v2_version=3)
            return

        if ext in ('.m4a', '.mp4'):
            audio = MP4(audio_path)
            if audio.tags is None:
                audio.add_tags()

            audio.tags['\xa9nam'] = [track['name']]
            audio.tags['\xa9ART'] = [track['artist']]
            audio.tags['\xa9alb'] = [track.get('album', '')]
            audio.tags['aART'] = [track['artist']]
            if track.get('track_number'):
                audio.tags['trkn'] = [(track['track_number'], 0)]
            if track.get('disc_number'):
                audio.tags['disk'] = [(track['disc_number'], 0)]
            if art_data:
                audio.tags['covr'] = [MP4Cover(art_data, imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()
            return

        if ext == '.wav':
            audio = WAVE(audio_path)
            if audio.tags is None:
                audio.add_tags()
            audio.tags['INAM'] = track['name']
            audio.tags['IART'] = track['artist']
            audio.tags['IPRD'] = track.get('album', '')
            if track.get('track_number'):
                audio.tags['ITRK'] = str(track['track_number'])
            if track.get('disc_number'):
                audio.tags['IDIS'] = str(track['disc_number'])
            audio.save()
            return
    except Exception:
        pass


def get_available_formats():
    return ['flac', 'mp3', 'aac', 'wav']


def download_single_track(search_query: str, track: dict, output_dir: str, format_selected: str, bitrate: str):
    base_name = sanitize_filename(f"{track['artist']} - {track['name']}")
    ydl_opts, ext = get_ydl_config(format_selected, bitrate, os.path.join(output_dir, base_name))
    final_file = os.path.join(output_dir, f"{base_name}.{ext}")

    if os.path.exists(final_file) and os.path.getsize(final_file) > 100_000:
        return 'skipped'

    temp_dir = tempfile.mkdtemp(prefix='audio_dl_')
    temp_file_template = os.path.join(temp_dir, base_name)
    ydl_opts['outtmpl'] = temp_file_template + '.%(ext)s'

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"ytsearch1:{search_query}"])

        output_files = [f for f in os.listdir(temp_dir) if f.lower().endswith(f'.{ext}')]
        if not output_files:
            raise FileNotFoundError(f"yt-dlp produced no {ext} file — is ffmpeg on PATH?")

        temp_output = os.path.join(temp_dir, output_files[0])
        if os.path.getsize(temp_output) < 100_000:
            raise ValueError('Output file too small — likely a YouTube error page.')

        shutil.move(temp_output, final_file)
        embed_metadata(final_file, track)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def download_track(sp, url, format='flac', bitrate='320', output_dir=None, progress_callback=None):
    """Standalone download function usable by CLI and GUI"""

    playlist_name, tracks = get_playlist_tracks(sp, url)
    total = len(tracks)

    base_output = output_dir if output_dir else os.path.join(os.getcwd(), 'Spotify FLAC Downloads')
    os.makedirs(base_output, exist_ok=True)

    if total == 1:
        target_dir = base_output
    else:
        target_dir = os.path.join(base_output, sanitize_filename(playlist_name))
        os.makedirs(target_dir, exist_ok=True)

    success = 0
    failed = 0
    skipped = 0

    for i, track in enumerate(tracks):
        if progress_callback:
            progress_callback((i / total) * 100)
        try:
            result = download_single_track(
                build_search_query(track),
                track,
                target_dir,
                format_selected=format,
                bitrate=bitrate,
            )
            if result == 'skipped':
                skipped += 1
            else:
                success += 1
        except Exception:
            failed += 1

    return target_dir


# ====================== ENTRY POINT ======================
if __name__ == "__main__":
    from .spotify_auth import get_spotify_client

    root = ctk.CTk()
    sp   = get_spotify_client()
    app  = ConversionTool(root, sp)
    root.mainloop()
