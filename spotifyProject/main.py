import tkinter as tk
from tkinter import messagebox
from auth import register_user, login_user, load_users, save_users
from spotify_auth import get_spotify_client

class LoginScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Project - Login")
        self.root.geometry("400x450")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False,False)

        self.build_ui()

    def build_ui(self):
        # Title
        tk.Label(self.root, text="🎵 Python Project",
                 font=("Helvetica", 22, "bold"),
                 bg="#1a1a2e", fg="#1DB954").pack(pady=30)
        
        # Username Field
        tk.Label(self.root, text="Username", font=("Helvetica", 11),
                 bg="#1a1a2e", fg="white").pack()
        self.username_entry = tk.Entry(self.root, font=("Helvetica", 12),
                                       width=25, bg="#16213e", fg="white",
                                       insertbackground="white")
        self.username_entry.pack(pady=5)

        # Password field
        tk.Label(self.root, text="Password", font=("Helvetica", 11),
                 bg="#1a1a2e", fg="white").pack(pady=(10,0))
        self.password_entry = tk.Entry(self.root, font=("Helvetica", 12),
                 width=25, show="*", bg="#16213e", fg="white",
                 insertbackground="white")
        self.password_entry.pack(pady=5)

        # Buttons
        tk.Button(self.root, text="Login", font=("Helvetica", 12, "bold"), 
                 bg="#1DB954", fg="black", width=20,
                 command=self.handle_login).pack(pady=(20,5))
        
        tk.Button(self.root, text="Create Account", font=("Helvetica", 12),
                 bg="#535353", fg="white", width=20,
                 command=self.handle_register).pack(pady=(20,5))
        
        # Status message label
        self.status_label = tk.Label(self.root, text="", font=("Helvetica", 10),
                 bg="#1a1a2e", fg="white")
        self.status_label.pack(pady=10)

    def handle_login(self):
        username = self.username_entry.get().strip() # .get() helps to receive something from a widget
        password = self.password_entry.get().strip()

        if not username or not password:
            self.status_label.config(text="Please fill in all fields.")
            return
        
        success, message = login_user(username, password)
        if success:
            self.open_homepage(username)
        else:
            self.status_label.config(text=message)
    
    def handle_register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            self.status_label.config(text="Please fill in all fields.")
            return
        
        try:
            success, message = register_user(username, password)
            if success:
                messagebox.showinfo("Account Created Successfully!",
                                    "Account Created! Now link your Spotify Account.")
                self.link_spotify(username)
            else:
                self.status_label.config(text=message)
        except Exception as e:
            messagebox.showerror("Registration Error", f"Something went wrong:\n\n{e}")


    def link_spotify(self, username):
        try:
            sp = get_spotify_client()
            sp_user = sp.current_user()
            # save spotify username to our JSON
            users = load_users()
            users[username]["spotify_id"] = sp_user["id"]
            save_users(users)
            messagebox.showinfo("Linked!", f"Spotify account '{sp_user['display_name']}' linked!")
            self.open_homepage(username)
        except Exception as e:
            messagebox.showerror("Spotify Error", f"Spotify linking failed:\n{e}")
            self.open_homepage(username)
    
    def open_homepage(self, username):
        # closes the login and opens the homepage
        from homepage import HomePage
        self.root.destroy()
        new_root = tk.Tk()
        HomePage(new_root, username)
        new_root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    LoginScreen(root)
    root.mainloop()