import threading

import customtkinter as ctk
from PIL import Image
from tkinter import messagebox

from .auth import (
    get_remembered_user,
    login_user,
    load_users,
    register_user,
    save_users,
    set_remember_me,
)
from .config import RESOURCE_DIR
from .spotify_auth import get_spotify_client
from .homepage import HomePage

# Color Palette
BG_COLOR       = "#232723"
PRIMARY        = "#62d089"
TEXT_PRIMARY   = "#e1ece3"
SECONDARY      = "#457e59"
TEXT_SECONDARY = "#a8b2a8"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# Logo loader
_LOGO_PATH = RESOURCE_DIR / "spotiTool_logo-blurred.png"

def _load_logo(size: tuple[int, int]) -> ctk.CTkImage | None:
    """Return a CTkImage of the SpotiTool logo at the requested size, or None."""
    try:
        img = Image.open(_LOGO_PATH).resize(size, Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None


class LoginScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("SpotiTool - Login")
        self.root.geometry("400x600")
        self.root.configure(fg_color=BG_COLOR)
        self.root.resizable(False, False)

        self._loading_overlay  = None
        self._loading_msg_label = None
        self._loading_bar       = None

        self.build_ui()

    def build_ui(self):
        # Title row: logo + "SpotiTool"
        title_frame = ctk.CTkFrame(self.root, fg_color=BG_COLOR)
        title_frame.pack(pady=40)

        logo_img = _load_logo((150, 150))
        if logo_img:
            ctk.CTkLabel(title_frame, image=logo_img, text="",
                         fg_color=BG_COLOR).pack(side="left", padx=(0, 10))
        else:
            ctk.CTkLabel(title_frame, text="🎵",
                         font=ctk.CTkFont("Helvetica", 36),
                         fg_color=BG_COLOR, text_color=PRIMARY).pack(side="left", padx=(0, 6))

            ctk.CTkLabel(title_frame, text="SpotiTool",
                        font=ctk.CTkFont("Helvetica", 28, weight="bold"),
                        fg_color=BG_COLOR, text_color=PRIMARY).pack(side="left")

        # Username
        ctk.CTkLabel(self.root, text="Username", font=ctk.CTkFont("Helvetica", 12),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=50)
        self.username_entry = ctk.CTkEntry(
            self.root, font=ctk.CTkFont("Helvetica", 13),
            width=300, fg_color=BG_COLOR, border_color=TEXT_SECONDARY,
            text_color=TEXT_PRIMARY)
        self.username_entry.pack(pady=8, padx=50)

        # Password
        ctk.CTkLabel(self.root, text="Password", font=ctk.CTkFont("Helvetica", 12),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=50, pady=(10, 0))
        self.password_entry = ctk.CTkEntry(
            self.root, font=ctk.CTkFont("Helvetica", 13),
            width=300, show="•", fg_color=BG_COLOR, border_color=TEXT_SECONDARY,
            text_color=TEXT_PRIMARY)
        self.password_entry.pack(pady=8, padx=50)

        # Remember Me
        self.remember_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            self.root, text="Remember Me",
            variable=self.remember_var,
            fg_color=PRIMARY, hover_color=SECONDARY,
            text_color=TEXT_SECONDARY, font=ctk.CTkFont("Helvetica", 11),
        ).pack(pady=12, anchor="w", padx=50)

        # Buttons
        ctk.CTkButton(
            self.root, text="Login",
            font=ctk.CTkFont("Helvetica", 13, weight="bold"),
            fg_color=PRIMARY, hover_color=SECONDARY, text_color=BG_COLOR,
            width=300, height=35, command=self.handle_login,
        ).pack(pady=(15, 8), padx=50)

        ctk.CTkButton(
            self.root, text="Create Account",
            font=ctk.CTkFont("Helvetica", 12),
            fg_color=TEXT_SECONDARY, hover_color=SECONDARY, text_color=BG_COLOR,
            width=300, height=35, command=self.handle_register,
        ).pack(pady=8, padx=50)

        # Status
        self.status_label = ctk.CTkLabel(
            self.root, text="", font=ctk.CTkFont("Helvetica", 11),
            text_color=TEXT_SECONDARY)
        self.status_label.pack(pady=15)

    # Loading overlay

    def _show_loading(self, message="Connecting to Spotify..."):
        """Cover the login form with an animated loading overlay."""
        if self._loading_overlay is not None:
            return

        overlay = ctk.CTkFrame(self.root, fg_color=BG_COLOR, corner_radius=0)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._loading_overlay = overlay

        # Logo (large) — falls back to emoji if image is missing
        logo_img = _load_logo((150, 150))
        if logo_img:
            ctk.CTkLabel(overlay, image=logo_img, text="",
                         fg_color=BG_COLOR).pack(expand=True, pady=(60, 6))
        else:
            ctk.CTkLabel(overlay, text="🎵",
                         font=ctk.CTkFont("Helvetica", 64),
                         fg_color=BG_COLOR, text_color=PRIMARY).pack(
                             expand=True, pady=(70, 4))

        self._loading_msg_label = ctk.CTkLabel(
            overlay, text=message,
            font=ctk.CTkFont("Helvetica", 13),
            text_color=TEXT_PRIMARY)
        self._loading_msg_label.pack(pady=6)

        self._loading_bar = ctk.CTkProgressBar(
            overlay, width=260, mode="indeterminate",
            progress_color=PRIMARY, fg_color=SECONDARY)
        self._loading_bar.pack(pady=14)
        self._loading_bar.start()

        ctk.CTkLabel(overlay, text="This may open a browser window",
                     font=ctk.CTkFont("Helvetica", 10),
                     text_color=TEXT_SECONDARY).pack(pady=(0, 20))

    def _update_loading_msg(self, message: str):
        if self._loading_msg_label and self._loading_msg_label.winfo_exists():
            self._loading_msg_label.configure(text=message)

    def _hide_loading(self):
        if self._loading_bar:
            self._loading_bar.stop()
        if self._loading_overlay and self._loading_overlay.winfo_exists():
            self._loading_overlay.destroy()
        self._loading_overlay = None

    # Login / Register

    def handle_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            self.status_label.configure(text="Please fill in all fields.")
            return
        success, message = login_user(username, password)
        if success:
            set_remember_me(username, self.remember_var.get())
            self.verify_spotify_account(username)
        else:
            self.status_label.configure(text=message)

    def handle_register(self):
        username = self.username_entry.get().strip().lower()
        password = self.password_entry.get().strip()
        if not username or not password:
            self.status_label.configure(text="Please fill in all fields.")
            return
        success, message = register_user(username, password)
        if success:
            messagebox.showinfo("Account Created Successfully!",
                                "Account created! Now link your Spotify account.")
            self.verify_spotify_account(username)
        else:
            self.status_label.configure(text=message)

    # Spotify auth (threaded)

    def verify_spotify_account(self, username):
        """Connect to Spotify in a background thread so the UI stays responsive."""
        self._show_loading("Connecting to Spotify...")

        def worker():
            try:
                sp = get_spotify_client()
                sp_user = sp.current_user()
                display_name = sp_user.get("display_name") or sp_user.get("id", "Unknown")
                self.root.after(0, lambda: self._on_spotify_connected(username, sp_user, display_name))
            except Exception as exc:
                err_msg = str(exc)
                self.root.after(0, lambda: self._on_spotify_error(username, err_msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_spotify_connected(self, username, sp_user, display_name):
        self._hide_loading()
        answer = messagebox.askyesno(
            "Confirm Spotify Account",
            f"The linked Spotify account is:\n\n🎵 {display_name}\n\nIs this correct?",
        )
        if answer:
            users = load_users()
            users[username]["spotify_id"] = sp_user["id"]
            save_users(users)
            self.open_homepage(username)
        else:
            self.link_spotify(username, force_reauth=True)

    def _on_spotify_error(self, username, err_msg):
        self._hide_loading()
        messagebox.showerror("Spotify Error", f"Could not reach Spotify:\n{err_msg}")
        self.link_spotify(username, force_reauth=True)

    def link_spotify(self, username, force_reauth=False):
        """Re-authenticate with Spotify (also runs in a background thread)."""
        self._show_loading("Opening Spotify login...")
        self._update_loading_msg("Complete the login in your browser, then return here.")

        def worker():
            try:
                sp = get_spotify_client(force_reauth=force_reauth)
                sp_user = sp.current_user()
                self.root.after(0, lambda: self._on_spotify_linked(username, sp_user))
            except Exception as exc:
                err_msg = str(exc)
                self.root.after(0, lambda: self._on_link_error(err_msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_spotify_linked(self, username, sp_user):
        self._hide_loading()
        users = load_users()
        users[username]["spotify_id"] = sp_user["id"]
        save_users(users)
        display_name = sp_user.get("display_name", sp_user.get("id", "Unknown"))
        messagebox.showinfo("Linked!", f"Spotify account '{display_name}' linked!")
        self.open_homepage(username)

    def _on_link_error(self, err_msg):
        self._hide_loading()
        messagebox.showerror("Spotify Error", f"Spotify linking failed:\n{err_msg}")

    # Navigation

    def open_homepage(self, username):
        self.root.destroy()
        new_root = ctk.CTk()
        HomePage(new_root, username)
        new_root.mainloop()


def main():
    root = ctk.CTk()
    remembered_user = get_remembered_user()
    if remembered_user:
        login_screen = LoginScreen(root)
        login_screen.status_label.configure(
            text=f"Welcome back {remembered_user}! Logging in automatically...")
        root.update()
        root.after(1200, lambda: login_screen.verify_spotify_account(remembered_user))
    else:
        LoginScreen(root)
    root.mainloop()


if __name__ == "__main__":
    main()
