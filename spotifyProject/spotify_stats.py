import tkinter as tk
from tkinter import ttk, messagebox
import threading


class SpotifyStatsPage:
    """Shows the user's top artists, top tracks and recently played songs."""

    def __init__(self, root, sp):
        self.root = root
        self.sp = sp

        self.root.title("Spotify Stats 📝")
        self.root.geometry("600x520")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)

        self.build_ui()
        self.refresh()

    def build_ui(self):
        tk.Label(self.root, text="Your Spotify Stats 📝",
                 font=("Helvetica", 18, "bold"),
                 bg="#1a1a2e", fg="#1DB954").pack(pady=15)

        # Range selector: last 4 weeks / 6 months / ~1 year
        range_frame = tk.Frame(self.root, bg="#1a1a2e")
        range_frame.pack()
        tk.Label(range_frame, text="Time range:",
                 font=("Helvetica", 10),
                 bg="#1a1a2e", fg="#aaaaaa").pack(side="left", padx=5)
        self.range_var = tk.StringVar(value="short_term")
        ranges = [
            ("Last 4 weeks", "short_term"),
            ("Last 6 months", "medium_term"),
            ("All time", "long_term"),
        ]
        for label, value in ranges:
            tk.Radiobutton(range_frame, text=label, variable=self.range_var,
                           value=value, command=self.refresh,
                           font=("Helvetica", 10),
                           bg="#1a1a2e", fg="white",
                           selectcolor="#16213e",
                           activebackground="#1a1a2e",
                           activeforeground="white").pack(side="left", padx=5)

        tk.Button(self.root, text="🔄 Refresh",
                  font=("Helvetica", 10, "bold"),
                  bg="#0f3460", fg="white",
                  command=self.refresh).pack(pady=5)

        # Three tabs: artists / tracks / recently played
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background="#1a1a2e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#16213e", foreground="white",
                        padding=(14, 6))
        style.map("TNotebook.Tab", background=[("selected", "#1DB954")],
                  foreground=[("selected", "black")])

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=10)

        self.lists = {}
        for key, title in (("artists", "🎨 Top Artists"),
                           ("tracks", "🎵 Top Tracks"),
                           ("recent", "🕒 Recently Played")):
            frame = tk.Frame(self.notebook, bg="#16213e")
            self.notebook.add(frame, text=title)
            box = tk.Text(frame, bg="#16213e", fg="white",
                          font=("Helvetica", 11), state="disabled",
                          wrap="word", relief="flat", padx=10, pady=8)
            box.pack(fill="both", expand=True)
            self.lists[key] = box

        self.status_var = tk.StringVar(value="Loading stats...")
        tk.Label(self.root, textvariable=self.status_var,
                 font=("Helvetica", 10), bg="#1a1a2e",
                 fg="#1DB954").pack(pady=5)

    # ---------- data loading (background thread, UI-safe updates) ----------

    def refresh(self):
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _set_list(self, key, text):
        def update():
            box = self.lists[key]
            box.config(state="normal")
            box.delete("1.0", "end")
            box.insert("end", text)
            box.config(state="disabled")
        self.root.after(0, update)

    def _set_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))

    def _load_worker(self):
        self._set_status("⏳ Loading stats...")
        time_range = self.range_var.get()
        try:
            try:
                # Top artists (up to 10)
                artists = self.sp.current_user_top_artists(limit=10, time_range=time_range)
                lines = []
                for i, a in enumerate(artists.get("items", []), start=1):
                    genres = ", ".join(a.get("genres", [])[:3])
                    line = f"{i:>2}. {a['name']}"
                    if genres:
                        line += f"  ({genres})"
                    lines.append(line)
                self._set_list("artists",
                               "\n".join(lines) if lines else "No artist data yet — listen to some music first!")
            except Exception as e:
                self._set_list("artists", f"❌ Could not load top artists:\n{e}")

            try:
                # Top tracks (up to 10)
                tracks = self.sp.current_user_top_tracks(limit=10, time_range=time_range)
                lines = []
                for i, t in enumerate(tracks.get("items", []), start=1):
                    artist = t["artists"][0]["name"]
                    lines.append(f"{i:>2}. {t['name']} — {artist}")
                self._set_list("tracks",
                               "\n".join(lines) if lines else "No track data yet — listen to some music first!")
            except Exception as e:
                self._set_list("tracks", f"❌ Could not load top tracks:\n{e}")

            try:
                # Recently played (up to 10)
                recent = self.sp.current_user_recently_played(limit=10)
                lines = []
                for item in recent.get("items", []):
                    t = item["track"]
                    lines.append(f"• {t['name']} — {t['artists'][0]['name']}")
                self._set_list("recent",
                               "\n".join(lines) if lines else "No recent play history found.")
            except Exception as e:
                self._set_list("recent", f"❌ Could not load recently played:\n{e}")

            self._set_status("✅ Stats loaded!")
        except Exception as e:
            self._set_status(f"❌ Error loading stats: {e}")
            self.root.after(0, lambda: messagebox.showerror(
                "Spotify Stats", f"Could not load your stats:\n{e}", parent=self.root))
