import io
import threading
import time

import customtkinter as ctk
import requests
import spotipy
from PIL import Image

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# Colours used throughout
BG          = '#232723'
GREEN       = '#1db954'
CARD_COLOR  = '#457e59'
SKELETON_BG = '#2d3d2d'
SKELETON_FG = '#3a4d3a'


class SpotifyStatsPage:
    def __init__(self, root, sp: spotipy.Spotify, username=None):
        self.root = root
        self.sp = sp
        self.username = username
        self.time_range = ctk.StringVar(value='Last 6 Months')

        # Keep CTkImage references alive (GC protection)
        self.artist_images: list[ctk.CTkImage] = []
        self.track_images:  list[ctk.CTkImage] = []
        self.now_playing_image = None
        self.recent_images: list[ctk.CTkImage] = []

        # Thread-safe image cache — fetched in worker threads, read anywhere
        self._image_cache: dict[str, ctk.CTkImage] = {}
        self._cache_lock = threading.Lock()

        # Playback progress tracking
        self.current_track_duration = 0
        self.progress_ms            = 0
        self.last_sync_time         = 0
        self.is_playing             = False

        self.root.title('Spotify Stats 🎶')
        self.root.geometry('600x700')
        self.root.configure(fg_color=BG)
        self.root.resizable(False, False)

        self.main_scrollable = ctk.CTkScrollableFrame(self.root, fg_color=BG)
        self.main_scrollable.pack(fill='both', expand=True, padx=10, pady=10)

        self.build_ui()

        # Show skeletons immediately so the window never looks blank
        self._show_stats_skeleton()
        self._show_recent_skeleton()

        # Kick off background data fetches
        self.refresh_playback()
        self.root.after(300,  self.refresh_top_stats)
        self.root.after(600,  self.refresh_recently_played)

        # Polling loops
        self.playback_refresh_loop()
        self.update_progress_loop()

    # ── UI construction ───────────────────────────────────────────────

    def build_ui(self):
        ctk.CTkLabel(self.main_scrollable, text='Spotify Stats 🎶',
                     font=ctk.CTkFont('Helvetica', 36, 'bold'),
                     fg_color=BG, text_color=GREEN).pack(pady=15)

        # NOW PLAYING
        self.now_playing_frame = ctk.CTkFrame(self.main_scrollable, fg_color=BG)
        ctk.CTkLabel(self.now_playing_frame, text='Now Playing',
                     font=ctk.CTkFont('Helvetica', 16, 'bold'),
                     fg_color=BG, text_color=GREEN).pack(pady=(10, 5))
        self.now_playing_frame.pack(fill='x', padx=20, pady=8)

        self.now_playing_container = ctk.CTkFrame(self.now_playing_frame, fg_color=CARD_COLOR)
        self.now_playing_container.pack(fill='x', padx=5, pady=(0, 10))

        self.now_playing_cover = ctk.CTkLabel(
            self.now_playing_container, fg_color=CARD_COLOR, text='')
        self.now_playing_cover.pack(side='left', padx=10, pady=10)

        self.now_playing_label = ctk.CTkLabel(
            self.now_playing_container, text='Connecting...',
            font=ctk.CTkFont('Helvetica', 15),
            fg_color=CARD_COLOR, text_color='white',
            wraplength=400, justify='left')
        self.now_playing_label.pack(side='left', padx=10, fill='x', expand=True)

        # TIME RANGE
        time_frame = ctk.CTkFrame(self.main_scrollable, fg_color=BG)
        time_frame.pack(fill='x', padx=20, pady=5)
        ctk.CTkLabel(time_frame, text='Time Range:',
                     fg_color=BG, text_color='white',
                     font=ctk.CTkFont('Helvetica', 14, 'bold')).pack(side='left', padx=5)
        self.time_combobox = ctk.CTkComboBox(
            time_frame, variable=self.time_range,
            values=['Last 4 Weeks', 'Last 6 Months', 'Last 12 Months'],
            command=lambda _: self.refresh_top_stats())
        self.time_combobox.pack(side='left', padx=5)

        # TOP STATS (artists | tracks)
        stats_container = ctk.CTkFrame(self.main_scrollable, fg_color=BG)
        stats_container.pack(fill='both', expand=True, padx=20, pady=8)

        self.top_artists_frame = ctk.CTkFrame(stats_container, fg_color=BG)
        self.top_artists_frame.pack(side='left', fill='both', expand=True, padx=(0, 4))

        self.top_tracks_frame = ctk.CTkFrame(stats_container, fg_color=BG)
        self.top_tracks_frame.pack(side='right', fill='both', expand=True, padx=(4, 0))

        # RECENTLY PLAYED
        self.recent_frame = ctk.CTkFrame(self.main_scrollable, fg_color=BG)
        ctk.CTkLabel(self.recent_frame, text='Recently Played Tracks',
                     font=ctk.CTkFont('Helvetica', 16, 'bold'),
                     fg_color=BG, text_color=GREEN).pack(pady=(10, 5))
        self.recent_frame.pack(fill='both', expand=True, padx=20, pady=(8, 0))

        self.recent_scrollable = ctk.CTkScrollableFrame(
            self.recent_frame, fg_color=BG, height=250)
        self.recent_scrollable.pack(fill='both', expand=True, padx=10, pady=(0, 10))

    # ── Skeleton loaders ──────────────────────────────────────────────

    def _skeleton_row(self, parent, img_size=40):
        """Return a single greyed-out placeholder row."""
        row = ctk.CTkFrame(parent, fg_color=SKELETON_BG, height=img_size + 8)
        row.pack(fill='x', pady=2, padx=5)
        row.pack_propagate(False)
        ctk.CTkLabel(row, text='', fg_color=SKELETON_FG,
                     width=img_size, height=img_size,
                     corner_radius=4).pack(side='left', padx=5, pady=4)
        ctk.CTkLabel(row, text='', fg_color=SKELETON_FG,
                     width=110, height=14,
                     corner_radius=3).pack(side='left', padx=6)

    def _show_stats_skeleton(self):
        """Replace artist/track panels with placeholder rows instantly."""
        for frame, label in [
            (self.top_artists_frame, 'Top Artists'),
            (self.top_tracks_frame,  'Top Songs'),
        ]:
            for w in frame.winfo_children():
                w.destroy()
            ctk.CTkLabel(frame, text=label,
                         font=ctk.CTkFont('Helvetica', 16, 'bold'),
                         text_color=GREEN).pack(pady=5)
            for _ in range(5):
                self._skeleton_row(frame, img_size=40)

    def _show_recent_skeleton(self, count=6):
        """Replace recent-tracks list with placeholder rows instantly."""
        for w in self.recent_scrollable.winfo_children():
            w.destroy()
        for _ in range(count):
            self._skeleton_row(self.recent_scrollable, img_size=50)

    # ── Image helpers ─────────────────────────────────────────────────

    def _fetch_image(self, img_url: str, size: tuple) -> ctk.CTkImage | None:
        """
        Download and cache an image.  Safe to call from any thread.
        Returns a CTkImage ready to drop into a label.
        """
        cache_key = f"{img_url}@{size[0]}x{size[1]}"
        with self._cache_lock:
            if cache_key in self._image_cache:
                return self._image_cache[cache_key]
        try:
            response = requests.get(img_url, timeout=4)
            pil_img  = Image.open(io.BytesIO(response.content)).resize(
                size, Image.Resampling.LANCZOS)
            ctk_img  = ctk.CTkImage(pil_img, size=size)
            with self._cache_lock:
                self._image_cache[cache_key] = ctk_img
            return ctk_img
        except Exception:
            return None

    # ── Now Playing ───────────────────────────────────────────────────

    def set_now_playing(self, text: str):
        self.root.after(0, lambda: self.now_playing_label.configure(text=text))

    def playback_refresh_loop(self):
        self.refresh_playback()
        self.root.after(10_000, self.playback_refresh_loop)

    def refresh_playback(self):
        threading.Thread(target=self._refresh_playback_worker, daemon=True).start()

    def _refresh_playback_worker(self):
        try:
            now_playing = self.sp.current_playback()
            if now_playing and now_playing.get('item'):
                track   = now_playing['item']
                artists = ', '.join(a['name'] for a in track.get('artists', []))

                self.current_track_duration = track.get('duration_ms', 0)
                self.progress_ms            = now_playing.get('progress_ms', 0)
                self.last_sync_time         = time.time()
                self.is_playing             = now_playing.get('is_playing', False)

                status_icon  = '▶️' if self.is_playing else '⏸️'
                progress_str = (f"{self.ms_to_time(self.progress_ms)} / "
                                f"{self.ms_to_time(self.current_track_duration)}")
                text = f"{track.get('name')}\n👤 {artists}\n{status_icon} {progress_str}"

                # Fetch cover art in this worker thread (not on the main thread)
                album   = track.get('album', {})
                ctk_img = None
                if album.get('images'):
                    ctk_img = self._fetch_image(album['images'][1]['url'], (80, 80))

                def update(img=ctk_img, t=text):
                    self.now_playing_label.configure(text=t)
                    if img:
                        self.now_playing_image = img
                        self.now_playing_cover.configure(image=img)

                self.root.after(0, update)
            else:
                self.is_playing = False
                self.set_now_playing('Nothing is currently playing.')
                self.root.after(0, lambda: self.now_playing_cover.configure(image=None))
        except Exception:
            self.set_now_playing('Status: Connection to Servers has been interrupted.')

    def update_progress_loop(self):
        if self.is_playing:
            elapsed = (time.time() - self.last_sync_time) * 1000
            current_ms = self.progress_ms + elapsed

            if current_ms < self.current_track_duration:
                progress_str = (f"{self.ms_to_time(current_ms)} / "
                                f"{self.ms_to_time(self.current_track_duration)}")
                current_text = self.now_playing_label.cget('text')
                lines = current_text.split('\n')
                if len(lines) >= 3:
                    lines[2] = f'▶️ {progress_str}'
                    self.now_playing_label.configure(text='\n'.join(lines))
            else:
                self.refresh_playback()

        self.root.after(1_000, self.update_progress_loop)

    # ── Top Stats ─────────────────────────────────────────────────────

    def refresh_top_stats(self):
        # Show skeleton immediately, then fetch in the background
        self._show_stats_skeleton()
        threading.Thread(target=self._refresh_top_stats_worker, daemon=True).start()

    def _refresh_top_stats_worker(self):
        time_map = {
            'Last 4 Weeks':   'short_term',
            'Last 6 Months':  'medium_term',
            'Last 12 Months': 'long_term',
        }
        selected_range = time_map.get(self.time_range.get(), 'medium_term')

        try:
            top_artists = self.sp.current_user_top_artists(limit=5, time_range=selected_range)
            top_tracks  = self.sp.current_user_top_tracks(limit=5,  time_range=selected_range)

            # ── Pre-fetch ALL images here in the worker thread ────────
            # This is the critical fix: image downloads no longer block
            # the main (UI) thread.
            artist_data = []
            for i, artist in enumerate(top_artists.get('items', []), 1):
                img = None
                if artist.get('images'):
                    img = self._fetch_image(artist['images'][-1]['url'], (40, 40))
                artist_data.append({'rank': i, 'name': artist['name'], 'img': img})

            track_data = []
            for i, track in enumerate(top_tracks.get('items', []), 1):
                img   = None
                album = track.get('album', {})
                if album.get('images'):
                    img = self._fetch_image(album['images'][-1]['url'], (40, 40))
                track_data.append({'rank': i, 'name': track['name'], 'img': img})

            # ── UI update — no network calls inside ───────────────────
            def update_ui(ad=artist_data, td=track_data):
                # Artists
                for w in self.top_artists_frame.winfo_children():
                    w.destroy()
                ctk.CTkLabel(self.top_artists_frame, text='Top Artists',
                             font=ctk.CTkFont('Helvetica', 16, 'bold'),
                             text_color=GREEN).pack(pady=5)
                self.artist_images.clear()
                for item in ad:
                    row = ctk.CTkFrame(self.top_artists_frame, fg_color=CARD_COLOR)
                    row.pack(fill='x', pady=2, padx=5)
                    if item['img']:
                        self.artist_images.append(item['img'])
                        ctk.CTkLabel(row, image=item['img'], text='').pack(
                            side='left', padx=5)
                    ctk.CTkLabel(row, text=f"{item['rank']}. {item['name']}",
                                 text_color='white',
                                 font=ctk.CTkFont(size=12)).pack(side='left', padx=5)

                # Tracks
                for w in self.top_tracks_frame.winfo_children():
                    w.destroy()
                ctk.CTkLabel(self.top_tracks_frame, text='Top Songs',
                             font=ctk.CTkFont('Helvetica', 16, 'bold'),
                             text_color=GREEN).pack(pady=5)
                self.track_images.clear()
                for item in td:
                    row = ctk.CTkFrame(self.top_tracks_frame, fg_color=CARD_COLOR)
                    row.pack(fill='x', pady=2, padx=5)
                    if item['img']:
                        self.track_images.append(item['img'])
                        ctk.CTkLabel(row, image=item['img'], text='').pack(
                            side='left', padx=5)
                    ctk.CTkLabel(row, text=f"{item['rank']}. {item['name']}",
                                 text_color='white',
                                 font=ctk.CTkFont(size=12),
                                 wraplength=150).pack(side='left', padx=5)

            self.root.after(0, update_ui)

        except Exception as e:
            print(f"Stats Error: {e}")

    # ── Recently Played ───────────────────────────────────────────────

    def refresh_recently_played(self):
        self._show_recent_skeleton()
        threading.Thread(target=self._recent_played_worker, daemon=True).start()

    def _recent_played_worker(self):
        try:
            recent_played = self.sp.current_user_recently_played(limit=10)

            # Pre-fetch all thumbnails in the worker thread
            items_data = []
            for item in recent_played.get('items', []):
                track  = item['track']
                img    = None
                album  = track.get('album', {})
                if album.get('images'):
                    img = self._fetch_image(album['images'][-1]['url'], (50, 50))
                artists = ', '.join(a['name'] for a in track['artists'])
                items_data.append({
                    'name':    track['name'],
                    'artists': artists,
                    'img':     img,
                })

            def update_ui(data=items_data):
                for w in self.recent_scrollable.winfo_children():
                    w.destroy()
                self.recent_images.clear()
                for item in data:
                    row = ctk.CTkFrame(self.recent_scrollable, fg_color=CARD_COLOR)
                    row.pack(fill='x', pady=3, padx=5)
                    if item['img']:
                        self.recent_images.append(item['img'])
                        ctk.CTkLabel(row, image=item['img'], text='').pack(
                            side='left', padx=10)
                    info_text = f"{item['name']}\n👤 {item['artists']}"
                    ctk.CTkLabel(row, text=info_text, text_color='white',
                                 justify='left', anchor='w').pack(
                        side='left', padx=10)

            self.root.after(0, update_ui)
        except Exception:
            pass

    # ── Utility ───────────────────────────────────────────────────────

    def ms_to_time(self, ms) -> str:
        if not ms or ms < 0:
            return '0:00'
        seconds = int(ms / 1000)
        return f"{seconds // 60}:{seconds % 60:02d}"


if __name__ == '__main__':
    from spotify_auth import get_spotify_client
    root = ctk.CTk()
    SpotifyStatsPage(root, get_spotify_client())
    root.mainloop()
