from pathlib import Path

import customtkinter as ctk
from PIL import Image
from tkinter import messagebox

from .spotify_auth import get_spotify_client

# Color Palette
BG_COLOR       = "#232723"
PRIMARY        = "#62d089"
TEXT_PRIMARY   = "#e1ece3"
SECONDARY      = "#457e59"
TEXT_SECONDARY = "#a8b2a8"
DISABLED_COLOR = "#3a4d3a"

# ── Logo loader ───────────────────────────────────────────────────────────────
_LOGO_PATH = Path(__file__).resolve().parent / "spotiTool_logo-blurred.png"

def _load_logo(size: tuple[int, int]) -> ctk.CTkImage | None:
    """Return a CTkImage of the SpotiTool logo at the requested size, or None."""
    try:
        img = Image.open(_LOGO_PATH).resize(size, Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None


class HomePage:
    def __init__(self, root, username, sp=None):
        self.root     = root
        self.username = username
        self.sp       = sp if sp is not None else get_spotify_client()
        self._buttons: list[ctk.CTkButton] = []

        self.root.title("SpotiTool - Home")
        self.root.geometry("650x550")
        self.root.configure(fg_color=BG_COLOR)
        self.root.resizable(False, False)

        self.build_ui()

    def build_ui(self):
        # ── Header Bar ───────────────────────────────────────────────
        header = ctk.CTkFrame(self.root, fg_color=BG_COLOR, corner_radius=0)
        header.pack(fill="x", pady=15)

        # Logo + "SpotiTool" wordmark on the left
        brand_frame = ctk.CTkFrame(header, fg_color=BG_COLOR)
        brand_frame.pack(side="left", padx=25)

        logo_img = _load_logo((100, 100))
        if logo_img:
            ctk.CTkLabel(brand_frame, image=logo_img, text="",
                         fg_color=BG_COLOR).pack(side="left", padx=(0, 8))
        else:
            ctk.CTkLabel(brand_frame, text="🎵",
                         font=ctk.CTkFont("Helvetica", 28),
                         fg_color=BG_COLOR, text_color=PRIMARY).pack(side="left", padx=(0, 4))

            ctk.CTkLabel(brand_frame, text="SpotiTool",
                        font=ctk.CTkFont("Helvetica", 26, weight="bold"),
                        fg_color=BG_COLOR, text_color=PRIMARY).pack(side="left")

        ctk.CTkButton(
            header, text="About",
            font=ctk.CTkFont("Helvetica", 12),
            fg_color=TEXT_SECONDARY, hover_color=SECONDARY,
            text_color=BG_COLOR, width=70, height=30,
            command=self.show_about,
        ).pack(side="right", padx=25)

        # Welcome Message
        ctk.CTkLabel(
            self.root, text=f"Welcome back, {self.username}! 👋🏾",
            font=ctk.CTkFont("Helvetica", 15),
            text_color=TEXT_PRIMARY,
        ).pack(pady=40)

        ctk.CTkLabel(
            self.root, text="Available Tools",
            font=ctk.CTkFont("Helvetica", 16, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(pady=(0, 15))

        # Status shown while a tool window is opening
        self._status_label = ctk.CTkLabel(
            self.root, text="",
            font=ctk.CTkFont("Helvetica", 11),
            text_color=TEXT_SECONDARY)
        self._status_label.pack(pady=(0, 5))

        # Feature Buttons
        button_specs = [
            ("Music Recognition 🎙️", self.launch_recognition),
            ("Spotify Stats 📝",      self.launch_stats),
            ("Spotify Downloader 🎶", self.launch_stm),
        ]

        for text, cmd in button_specs:
            btn = ctk.CTkButton(
                self.root, text=text,
                font=ctk.CTkFont("Helvetica", 14, weight="bold"),
                fg_color=PRIMARY, hover_color=SECONDARY,
                text_color=BG_COLOR,
                width=350, height=45, corner_radius=8,
                command=cmd)
            btn.pack(pady=10)
            self._buttons.append(btn)

    # ── Button state helpers ──────────────────────────────────────────

    def _set_buttons_loading(self, active_label: str):
        """Disable all feature buttons and show which tool is opening."""
        for btn in self._buttons:
            btn.configure(state="disabled", fg_color=DISABLED_COLOR)
        self._status_label.configure(text=f"Opening {active_label}...")

    def _restore_buttons(self):
        """Re-enable all feature buttons once a tool window is ready."""
        for btn in self._buttons:
            btn.configure(state="normal", fg_color=PRIMARY)
        self._status_label.configure(text="")

    # ── Tool launchers ────────────────────────────────────────────────

    def launch_recognition(self):
        self._set_buttons_loading("Music Recognition")

        def open_tool():
            from .music_recognition import MusicRecognitionTool
            win = ctk.CTkToplevel(self.root)
            self.root.after(0, self._restore_buttons)
            win.protocol("WM_DELETE_WINDOW",
                         lambda: [self._restore_buttons(), win.destroy()])
            MusicRecognitionTool(win, self.sp, self.username)

        self.root.after(50, open_tool)

    def launch_stats(self):
        self._set_buttons_loading("Spotify Stats")

        def open_tool():
            from .spotify_stats import SpotifyStatsPage
            win = ctk.CTkToplevel(self.root)
            self.root.after(0, self._restore_buttons)
            win.protocol("WM_DELETE_WINDOW",
                         lambda: [self._restore_buttons(), win.destroy()])
            SpotifyStatsPage(win, self.sp)

        self.root.after(50, open_tool)

    def launch_stm(self):
        self._set_buttons_loading("Spotify Downloader")

        def open_tool():
            from .spotify_downloader import ConversionTool
            win = ctk.CTkToplevel(self.root)
            self.root.after(0, self._restore_buttons)
            win.protocol("WM_DELETE_WINDOW",
                         lambda: [self._restore_buttons(), win.destroy()])
            ConversionTool(win, self.sp)

        self.root.after(50, open_tool)

    # ── About ─────────────────────────────────────────────────────────

    def show_about(self):
        messagebox.showinfo(
            "About",
            "This is SpotiTool, a Spotify companion app.\n\n"
            "• Identify songs using your microphone or system audio\n"
            "• View your Spotify listening stats\n"
            "• Download songs in multiple audio formats\n\n"
            "Built with Python, CustomTkinter & Spotify API")
