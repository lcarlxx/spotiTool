import json
import os
from cryptography.fernet import Fernet

"""
# all account information will be saved here
DATA_FILE = "user_data.json" # holds all usernames and encrypted passwords
KEY_FILE = "secret.key" # stores the encryption key
"""
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "user_data.json")
KEY_FILE = os.path.join(BASE_DIR, "secret.key")

# key management
def load_or_create_key(): # creates an encryption key if one doesn't exist but loads an existing one if it does
    """
    if not os.path.exists(KEY_FILE): # if the encryption key doesn not exist...
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f: # opens the file in binary mode (the encryption keys are not made with normal text) and names it f
            f.write(key) # saves it such that it is not lost
    else: # if the file does exist
        with open(KEY_FILE, "rb") as f: # reads it in binary
            key = f.read() # loads the key from the life and stores it in variable "key"
    return Fernet(key)    
    """
    key_path = str(KEY_FILE)

    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            key = f.read().strip()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    
    if isinstance(key, str):
        key = key.encode()

    return Fernet(key)

# storing the function in this variable will help us in the future to decrypt and encrypt things
fernet = load_or_create_key()

def encrypt_password(plain_password):
    # now we're going to turn this plain password into unreadable encrypted text
    return fernet.encrypt(plain_password.encode()).decode()

def decrypt_password(encrypted_password):
    # now to turn the unreadable encryption back to our plain password
    return fernet.decrypt(encrypted_password.encode()).decode()

"""
.encode() - turns the password into bytes
fernet.encrypt() - locks it with our secret key
fernet.decrypt() - opens it with our secret key
.decode() - turns the locked bytes back into a normal string (such that it can be saved into a JSON)
"""

# function to read all
def load_users():
    if not os.path.exists(DATA_FILE): # if user_data.json doesn't exist
        return {} # returns an empty dictionary to prevent crashing
    try:
        with open(DATA_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except json.JSONDecodeError:
        os.rename(DATA_FILE, DATA_FILE + ".bak")
        return {}   

def save_users(users: dict): # users will be a dictionary
    """
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4) # indent=4 for readability
    """
    try:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(users, f, indent=4)
        os.replace(tmp, DATA_FILE)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save users: {e}")
        return False
    
# create a new user
def register_user(username, password):
    # will use a tuple format of (True/False, "message")
    users = load_users() # loads whatever users are saved
    if username in users:
        return False, "Username already exists!"
    
    users[username] = {
        "password": encrypt_password(password),
        "spotify_id": None # will be filled after spotify login
    }
    if save_users(users):
        return True, "Account created!"
    else:
        return False, "Could not save account. Check folder permissions."  
        

def login_user(username, password):
    users = load_users()
    if username not in users:
        return False, "Username not found!"
    
    try:
        decrypted = decrypt_password(users[username]["password"])
        if decrypted == password:
            return True, "Login Successful!"
        else:
            return False, "Incorrect password!"
    except Exception:
        return False, (
            "Could not read your password — the secret.key file may have changed.\n"
            "Delete both secret.key and user_data.json and create a fresh account."
        )