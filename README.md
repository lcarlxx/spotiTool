# spotiTool — Spotify Companion (v1.0)

A desktop app and command-line tool for Spotify. Identify music playing around you,
explore your listening stats, and download tracks, albums and playlists — all from
one program.

**Version 1.0 features**

| Feature | What it does |
|---|---|
| 🎙️ **Music recognition** | Records 6 seconds of audio (system playback or your microphone) and identifies the song with Shazam |
| ➕ **Playlist saving** | Sends an identified song straight to a playlist you choose (paste your playlist link once) |
| 📝 **Listening stats** | Now playing, top artists, top tracks and recently played, with a time-range selector |
| 🎶 **Downloader** | Downloads tracks/albums/playlists through yt-dlp, with cover art and metadata tagging (FLAC, MP3, M4A, WAV) |
| 🔐 **Local accounts** | Username/password accounts stored locally with PBKDF2 hashing |
| 💻 **CLI** | Every feature available from a terminal — useful for testing and automation |

---

## Contents

1. [Prerequisites](#1-prerequisites)
2. [Get Spotify API credentials](#2-get-spotify-api-credentials)
3. [Run from source](#3-run-from-source)
4. [Using the desktop app](#4-using-the-desktop-app)
5. [Using the CLI](#5-using-the-cli)
6. [Build a standalone desktop application](#6-build-a-standalone-desktop-application)
7. [Troubleshooting](#7-troubleshooting)
8. [Project layout](#8-project-layout)
9. [FAQ / notes](#9-faq--notes)
10. [Security](#10-security)
11. [License](#11-license)

---

## 1. Prerequisites

### Required

1. **Python 3.12 or 3.13** — download from <https://www.python.org/downloads/>
   - During installation, tick **"Add python.exe to PATH"**.
   - Python 3.14 is *not* recommended: some audio packages have no prebuilt wheels yet.
   - Check your version:
     ```powershell
     python --version
     ```

2. **FFmpeg** — needed for audio conversion during downloads.
   - Download a build from <https://www.gyan.dev/ffmpeg/builds/> (get `ffmpeg-release-essentials.zip`).
   - Unzip it to `C:\ffmpeg`.
   - Add `C:\ffmpeg\bin` to your **PATH**:
     1. Press `Win`, type *"environment variables"*, open **Edit the system environment variables**.
     2. Click **Environment Variables…** → select **Path** → **Edit** → **New**.
     3. Enter `C:\ffmpeg\bin` → **OK** on every window.
     4. **Close and reopen** your terminal, then verify:
        ```powershell
        ffmpeg -version
        ```
        You should see a version banner rather than "not recognized".

3. **Spotify account** — free or premium.

4. **A Spotify playlist you own** — the app adds found songs to it. Dev-mode Spotify
   apps are not allowed to create playlists, so you must supply one:
   - Open Spotify → right-click your playlist → **Share** → **Copy link to playlist**.
   - Keep that link handy; you'll paste it into the app once.

### Optional

- **Stereo Mix / loopback device** for system-audio recognition.
  On Windows: `Win` → *"sound settings"* → **More sound settings** → **Recording** tab →
  right-click empty space → **Show Disabled Devices** → enable **Stereo Mix**.
  Bluetooth/wired headphones usually still work because the app records the loopback
  of the default output device.
- **Microphone** for recognising music in the room (no Stereo Mix needed).

---

## 2. Get Spotify API credentials

1. Go to <https://developer.spotify.com/dashboard> and log in.
2. Click **Create app**. Name it anything (e.g. `SpotiTool`).
3. In **Redirect URI**, enter exactly:
   ```
   http://127.0.0.1:8888/callback
   ```
   Then click **Add**, choose **Web API**, and **Save**.
4. Open your new app → **Settings** → copy the **Client ID** and **Client Secret**.

> ⚠️ **Never commit your Client Secret.** This repo ignores `.env` and
> `spotify_credentials.json`, so your secrets stay local. If a secret was ever pushed,
> rotate it in the dashboard (**Settings → Reset secret**).

---

## 3. Run from source

### Step 1 — get the code

```powershell
git clone https://github.com/lcarlxx/spotiTool.git
cd spotiTool
```

(No git? Download the ZIP from GitHub and unzip it, then `cd` into the folder.)

### Step 2 — create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once and retry:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

You should now see `(.venv)` at the start of your prompt.

### Step 3 — install dependencies

```powershell
pip install -r requirements.txt
```

### Step 4 — provide your Spotify credentials

Pick **one** of these three methods.

**Method A — environment variables (recommended)**

```powershell
setx SPOTIPY_CLIENT_ID "your-client-id-here"
setx SPOTIPY_CLIENT_SECRET "your-client-secret-here"
```

Then **close and reopen** the terminal (and re-activate the venv).

**Method B — a `.env` file** in the project root (`spotiTool\.env`):

```
SPOTIPY_CLIENT_ID=your-client-id-here
SPOTIPY_CLIENT_SECRET=your-client-secret-here
```

**Method C — `spotify_credentials.json`** in the project root:

```json
{
  "client_id": "your-client-id-here",
  "client_secret": "your-client-secret-here"
}
```

### Step 5 — check everything is wired up

```powershell
python -m spotifyProject validate
```

Expected output (yours will differ slightly):

```
SpotiTool 1.0.0  (python -m spotifyProject)
----------------------------------------------------
✅ Credentials found (client ID …4ef868)
   Redirect URI: http://127.0.0.1:8888/callback
✅ ffmpeg found on PATH
✅ Audio input devices: 14
✅ System audio device: Stereo Mix (Realtek(R) Audio)
ℹ️  Not logged in yet — run `python -m spotifyProject login`
ℹ️  Data directory: ...\spotiTool\spotifyProject\user_data

✅ Setup looks good.
```

Every line should start with ✅ or ℹ️. If you see ❌, fix that item first.

### Step 6 — log in to Spotify once

```powershell
python -m spotifyProject login
```

A browser window opens. Approve access, and the terminal confirms:

```
✅ Logged in as: Your Name
   Token cached at: ...\.spotify_cache
```

The token is cached, so you won't need to log in again.

### Step 7 — start the app

```powershell
python run.py
```

(or `python -m spotifyProject gui`)

---

## 4. Using the desktop app

### First launch

1. **Create Account** — pick a username and password (stored locally; passwords are
   hashed with PBKDF2).
2. The app connects to Spotify and asks **"Is this correct?"** about the linked account.
   - **Yes** → you go to the home screen.
   - **No** → a browser re-opens so you can log in with a different Spotify account.
3. Tick **Remember Me** if you want the app to sign you in automatically next time.

### Home screen

Three buttons, each opening a tool window:

| Button | Use it to… |
|---|---|
| **Music Recognition 🎙️** | identify a song and save it to a playlist |
| **Spotify Stats 📝** | see now playing, top artists/tracks, recently played |
| **Spotify Downloader 🎶** | download tracks, albums or playlists |

### Music recognition

1. Click **🎙️ Listen via Microphone** (music in the room) **or**
   **🖥️ Detect System Audio** (music playing on this PC).
2. Wait ~6 seconds of recording plus a moment for Shazam.
3. The result shows in the status line and is added to *Recently Discovered Songs*.
4. Confirm **"Add to Playlist?"** to save it.
5. First time only: paste your playlist link
   (`https://open.spotify.com/playlist/…`) — the choice is remembered.
   Use **🔄 Change Playlist?** later to switch playlists.

**Tips for reliable recognition:** play audio at normal volume mid-song (not the intro),
keep other noise low, and retry once if it fails.

### Spotify stats

Shows what's playing now (with progress bar), plus top artists, top tracks and
recently played. Pick a time range: *Last 4 Weeks*, *Last 6 Months* or *Last 12 Months*.

### Downloader

1. Paste a Spotify **track**, **album** or **playlist** link.
2. Choose the format: `FLAC (Lossless)`, `MP3`, `M4A/AAC` or `WAV`, and a bitrate for
   lossy formats.
3. Click **Download**. Files land in `Spotify FLAC Downloads\` next to where you
   launched the app (sub-folders per album/playlist), with tags and cover art embedded.

> ℹ️ Downloads are fetched from YouTube via yt-dlp, so quality depends on what is
> available there. Check obscure tracks got the right version.

---

## 5. Using the CLI

The CLI runs every feature without opening the GUI — ideal for testing and scripting.

Run it with **either** of these (both are equivalent):

```powershell
python -m spotifyProject <command>      # from source
python run_cli.py <command>             # from source, alternative
.\dist\spotitool-cli.exe <command>      # packaged build (section 6)
```

> Throughout this section, `spotitool` below means whichever of the three you use.

### See all commands

```powershell
spotitool --help
spotitool --version
```

### `validate` — check your setup

```powershell
spotitool validate
```
Checks credentials, ffmpeg, audio devices and login state. Exit code `0` = all good.

### `login` — authenticate once

```powershell
spotitool login
spotitool login --force     # ignore the cached token and log in again
```

### `stats` — listening statistics

```powershell
spotitool stats                      # last 4 weeks (default)
spotitool stats --range medium       # last 6 months
spotitool stats --range long         # last 12 months
```

### `recognize` — identify the current song

```powershell
spotitool recognize                                  # system audio, 10 seconds
spotitool recognize --source mic                     # use the microphone
spotitool recognize --duration 15                    # record longer
spotitool recognize --add --playlist <playlist-link> # add to a playlist
spotitool recognize --add --user alice               # use the playlist saved for user 'alice'
```

Options: `--source system|mic`, `--duration SECONDS`, `--add`, `--user NAME`,
`--playlist ID_OR_LINK`.

### `download` — download music

```powershell
spotitool download https://open.spotify.com/track/<id>
spotitool download https://open.spotify.com/album/<id> --format flac
spotitool download https://open.spotify.com/playlist/<id> --format mp3 --bitrate 320
spotitool download <link> --out "D:\Music"           # custom output folder
```

Options: `--format flac|mp3|m4a|wav`, `--bitrate N`, `--out DIR`,
`--cookies-from-browser BROWSER`.

If YouTube blocks the download with **HTTP 403**, run:

```powershell
spotitool download <link> --cookies-from-browser chrome
```
(also `edge`, `firefox`, `brave` — whichever browser you're signed into YouTube with),
or update yt-dlp: `pip install -U yt-dlp`.

### `gui` — launch the desktop app

```powershell
spotitool gui
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | success |
| `1` | a command failed (bad input, missing credentials, all downloads failed, …) |
| `130` | interrupted with `Ctrl+C` |

This makes the CLI safe to use in scripts (`if ($LASTEXITCODE -eq 0) { … }`).

---

## 6. Build a standalone desktop application

This produces two self-contained `.exe` files — no Python needed on the target PC:

- `dist\SpotiTool.exe` — the desktop app (no console window)
- `dist\spotitool-cli.exe` — the CLI (console)

### Step 1 — install the packaging tools

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

(`requirements-dev.txt` = normal dependencies + PyInstaller.)

### Step 2 — build

**One command:**

```powershell
.\build.ps1
```

or with `cmd`:

```powershell
build.bat
```

or directly:

```powershell
python -m PyInstaller spotiTool.spec --noconfirm
```

The build takes a few minutes. When it finishes you'll see:

```
dist\SpotiTool.exe         (~61 MB)
dist\spotitool-cli.exe     (~61 MB)
```

### Step 3 — run it

```powershell
.\dist\SpotiTool.exe
.\dist\spotitool-cli.exe validate
```

### Step 4 — give it to someone else

1. Copy **`SpotiTool.exe`** (and optionally `spotitool-cli.exe`) anywhere — e.g. a
   folder on their Desktop.
2. They need **FFmpeg on PATH** (section 1, item 2) for downloads.
3. They need **Spotify credentials**. Put a `spotify_credentials.json` **next to the
   exe**:

   ```
   MyFolder\
     SpotiTool.exe
     spotify_credentials.json
   ```

   ```json
   {
     "client_id": "their-client-id",
     "client_secret": "their-client-secret"
   }
   ```

   Environment variables work too.

4. Accounts, the Spotify login token and the recent-songs list are stored in a
   `user_data\` folder created **next to the exe**, so the app keeps its settings when
   moved (keep that folder to preserve data; delete it to reset).
5. First run: create an account → the browser opens for Spotify login → done.

> **Windows SmartScreen:** the exe is unsigned, so Windows may show *"Windows protected
> your PC"*. Click **More info → Run anyway**.

> **Antivirus false positives:** PyInstaller bundles are sometimes flagged. Building the
> exe yourself from this source (the steps above) avoids trusting a downloaded binary.

### Rebuilding after code changes

```powershell
python -m PyInstaller spotiTool.spec --noconfirm
```

Delete `build\` and `dist\` first if you want a completely clean rebuild.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `python: command not found` | Python isn't on PATH. Reinstall and tick *"Add python.exe to PATH"*, or use `py` instead of `python`. |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then re-activate. |
| `Spotify Client ID is not set` | Section 3 step 4 — set env vars, `.env`, or `spotify_credentials.json`, then **reopen the terminal**. |
| Browser login says *redirect_uri: Not matching* | The Redirect URI in your Spotify app must be exactly `http://127.0.0.1:8888/callback` (add it, then **Save**). |
| `INVALID_CLIENT: Invalid redirect URI` in browser | Same as above. |
| Login loop / wrong account | `spotitool login --force` (clears the cached token). |
| *No system audio device found* | Enable **Stereo Mix** (section 1, Optional) or use microphone mode (`--source mic` / the app's microphone button). |
| Recognition always fails | Play audio louder/closer, mid-song, retry; use the other audio source. |
| Downloads fail: *ffmpeg not found* | Install FFmpeg and add `C:\ffmpeg\bin` to PATH, then reopen the terminal. |
| Downloads fail: **HTTP 403 Forbidden** | `--cookies-from-browser chrome`, or `pip install -U yt-dlp`. |
| *No matching track found on Spotify* | That track isn't available on Spotify (common for remixes/live versions). |
| Stats show *Valid user authentication required* | You're not logged in: `spotitool login`. |
| App window doesn't open | Run `python run.py` in a terminal to see the error; make sure dependencies installed. |
| Exe closes instantly with no window | Most likely missing credentials — run `spotitool-cli.exe validate` next to it. |
| `Unclosed client session` warnings | Harmless (Shazam's HTTP session); they don't affect results. |
| Want a clean start (accounts, tokens) | Delete the `user_data\` folder (source: `spotifyProject\user_data\`; exe: next to the exe). |

Still stuck? Run `spotitool validate` first — it pinpoints most setup problems.

---

## 8. Project layout

```
spotiTool/
├── run.py                    # desktop app launcher (python run.py)
├── run_cli.py                # CLI launcher (python run_cli.py …)
├── spotiTool.spec            # PyInstaller build definition (GUI + CLI exes)
├── build.ps1 / build.bat     # one-command builds
├── requirements.txt          # runtime dependencies
├── requirements-dev.txt      # + PyInstaller
└── spotifyProject/
    ├── __init__.py           # version
    ├── __main__.py           # `python -m spotifyProject`
    ├── cli.py                # all CLI commands
    ├── config.py             # paths, credentials loading, validation
    ├── auth.py               # local accounts (PBKDF2 hashing)
    ├── spotify_auth.py       # Spotify OAuth / API clients
    ├── main.py               # login screen + app entry
    ├── homepage.py           # home screen and tool launchers
    ├── music_recognition.py  # Shazam recognition + playlist saving
    ├── spotify_stats.py      # now playing / top artists / recently played
    ├── spotify_downloader.py # yt-dlp downloads + metadata tagging
    └── spotiTool_logo-blurred.png
```

Runtime data (not in git): `spotifyProject/user_data/` contains `user_data.json`
(accounts), `.spotify_cache` (OAuth token), `recent_songs.json` and `cover_cache/`.

---

## 9. FAQ / notes

**Do I need Spotify Premium?** No. Playback isn't controlled; the app reads stats and
writes to your playlist.

**Why can't the app create a playlist for me?** Spotify restricts dev-mode apps from
creating playlists and limits them to 5 test users. You supply a playlist link instead.

**Where do downloads go?** `Spotify FLAC Downloads\` in the current working directory,
with one sub-folder per album/playlist. Use `--out` (CLI) to change it.

**Are my passwords safe?** They're hashed with PBKDF2-SHA256 (200k iterations, per-user
salt) and never leave your machine. They are *not* your Spotify password — they only
unlock the app locally.

**Is my Client Secret safe?** It's read from env vars / `.env` / a gitignored JSON file
and never written into the code or shipped inside the exe.

**Can I use it on another PC?** Copy the exe (+ `spotify_credentials.json`); FFmpeg is
still required for downloads.

**Legal note:** downloading audio may violate Spotify's and YouTube's terms of service.
Use it only for content you have the right to download.

---

## 10. Security

SpotiTool is entirely local — no server, no telemetry. Full details are in
[SECURITY.md](SECURITY.md); the short version:

- **Passwords** are hashed with PBKDF2-HMAC-SHA256 (200k iterations, per-user salt)
  and compared in constant time. They are app passwords, not your Spotify password.
- **Spotify API credentials** are never in the source code — they come from env vars,
  `.env`, or a gitignored `spotify_credentials.json`.
- **Spotify login tokens** are cached locally in `user_data/.spotify_cache` in
  plaintext (standard for spotipy). Anyone who can read your user profile can use
  that token — revoke access at <https://www.spotify.com/account/apps/>.
- No `eval`/`exec`/`pickle`/`shell=True`, no disabled TLS verification, filenames
  from remote metadata are sanitised, and folder-opening uses argv lists (no shell).

**Two things you must do yourself:**

1. **Rotate your client secret** if you ever committed one (this repo's history
   contained one before v1.0). Dashboard → **Settings → Reset secret**.
2. **Treat the `.exe` as public** — never embed a client secret in a distributed
   build; each user supplies their own credentials.

Report vulnerabilities privately (see [SECURITY.md](SECURITY.md)), not via public issues.

---

## 11. License

MIT — see [LICENSE](LICENSE).

```
Copyright (c) 2026 lcarlxx
```

You may use, modify, and redistribute this software, including commercially,
provided the copyright notice and permission notice are retained. The software
is provided **as is**, without warranty of any kind.

Third-party components keep their own licenses: spotipy (MIT), ShazamIO (MIT),
CustomTkinter (MIT), yt-dlp (Unlicense), mutagen (GPL-2.0+), Pillow (HPND),
sounddevice (MIT), requests (Apache-2.0). Note that **mutagen is GPL-2.0+** — if you
distribute a modified build, review how that interacts with your licensing plans.

---

## Development history (v0.1 → v1.0)

- **Audio identification:** Google Speech Recognition was replaced with ShazamIO, then
  Spotify search was dropped in favour of the Spotify URI Shazam embeds in its
  `hub.providers` response (fixes covers/400 errors); a Spotify search fallback handles
  tracks without an embedded URI.
- **Audio capture:** mono capture proved far more reliable than stereo; the desktop app
  now selects a loopback ("Stereo Mix" / "What U Hear") device automatically.
- **Playlists:** replaced a hard-coded playlist ID with a paste-your-link dialog.
- **Security:** hard-coded credentials removed; PBKDF2 password hashing replaces
  encrypted-but-reversible storage.
- **v1.0:** full CLI, single-file PyInstaller desktop build, standard-library WAV
  writing (removes the scipy dependency), background-threaded UI with crash guards,
  honest download error reporting and multi-client retry.
