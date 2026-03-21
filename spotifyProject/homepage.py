import tkinter as tk
from tkinter import messagebox
from spotify_auth import get_spotify_client

class HomePage:
    def __init__(self, root, username):
        self.root = root
        self.username = username
        self.sp = get_spotify_client()

        self.root.title("Python Project - Home")
        self.root.geometry("600x500")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)

        self.build_ui()

    def build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#16213e", pady=15)
        header.pack(fill="x")

        tk.Label(header, text="🎵 Python Project", font=("Helvetica", 24, "bold"),
                 bg="#1a1a2e", fg="#1DB954").pack(side="left", padx=20)
        
        tk.Button(header, text="About", font=("Helvetica", 11),
                  bg="#535353", fg="white",
                  command=self.show_about).pack(side="right", padx=20)
        
        # Welcome message
        tk.Label(self.root, text=f"Welcome back, {self.username}!👋🏾",
                 font=("Helvetica", 11),
                 bg="#1a1a2e", fg="white").pack(pady=30)

        # Tools
        tk.Button(self.root, text="TOOLS 🪛",
                  font=("Helvetica", 16, "bold"),
                  bg="#1DB954", fg="black",
                  width=20, height=2,
                  command=self.open_tools).pack(pady=10)
        
    def show_about(self):
        messagebox.showinfo("About",
                            "This Python Project is a Spotify companion app.\n\n"
                            "• Identify songs using your microphone or system audio\n"
                            "• View your Spotify listening stats\n"
                            "• Auto-save discovered songs to a playlist\n\n"
                            "Built customly solely with Python, Tkinter & the Spotify API."
                        )
    
    def open_tools(self):
        tools_win = tk.Toplevel(self.root)
        tools_win.title("Tools")
        tools_win.geometry("500x300")
        tools_win.configure(bg="#1a1a2e")
        tools_win.resizable(False, False)

        tk.Label(tools_win, text="Choose a Tool",
                 font=("Helvetica", 16, "bold"),
                 bg="#1a1a2e", fg="white").pack(pady=20)
        
        # Music Recognition
        tk.Button(tools_win,
                  text="Music Recognition 🎙️",
                  font=("Helvetica", 14, "bold"),
                  bg="#0f3460", fg="white",
                  width=30, height=3,
                  command=lambda: self.launch_voice(tools_win)).pack(pady=10)
        
        # Spotify Stats
        tk.Button(tools_win,
                  text="Spotify Stats 📝",
                  font=("Helvetica", 14, "bold"),
                  bg="#0f3460", fg="white",
                  width=30, height=3,
                  command=lambda: self.launch_stats(tools_win)).pack(pady=10)
        
    def launch_voice(self, parent):
        from voice_recognition import voiceRecognitionTool
        voiceRecognitionTool(tk.Toplevel(parent), self.sp)

    def launch_stats(self, parent):
        from spotify_stats import SpotifyStatsPage
        SpotifyStatsPage(tk.Toplevel(parent), self.sp)