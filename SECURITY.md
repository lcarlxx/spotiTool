# Security Policy — SpotiTool

## Supported versions

| Version | Supported |
|---|---|
| 1.x | ✅ |
| < 1.0 | ❌ |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

- Open a private report via GitHub → **Security** → **Report a vulnerability**, or
- Contact the maintainer directly (@lcarlxx on GitHub).

Include: what you found, how to reproduce it, and the impact you believe it has.
You can expect an acknowledgement within a few days.

---

## Threat model

SpotiTool is a **local desktop application**. It has no server component, no
telemetry, and no remote account system. The realistic threats are therefore:

1. Someone with access to your machine reading your files.
2. A malicious website or local process interfering with the OAuth flow.
3. A tampered build / dependency being distributed to users.
4. Your Spotify API credentials leaking through git history or a shared exe.

## What is protected, and how

| Asset | Where it lives | Protection |
|---|---|---|
| App passwords | `user_data/user_data.json` | PBKDF2-HMAC-SHA256, 200,000 iterations, 16-byte random salt per user, constant-time comparison (`hmac.compare_digest`). Never stored or logged in plaintext. |
| Spotify OAuth tokens | `user_data/.spotify_cache` | Stored by spotipy in plaintext JSON (standard for spotipy) — protected by your OS account permissions only. Useful lifetime: access token ~1 h, refresh token until revoked. |
| Spotify API credentials | env var / `.env` / `spotify_credentials.json` | Never written into source. All three locations are gitignored. |
| Recently discovered songs, cover cache | `user_data/` | Non-sensitive; contains song metadata only. |
| Downloaded audio | `Spotify FLAC Downloads/` | Your files, your responsibility. |

Additional hardening already in the code:

- Playlist links, track names and IDs are validated before use.
- Filenames from remote metadata are sanitised (path separators and reserved
  characters stripped) before writing, preventing path traversal.
- No `eval`, `exec`, `pickle`, `yaml.load`, `shell=True` or `verify=False` anywhere.
- External folder-opening uses an argv list (`subprocess.run([...])`), never a
  shell string, so a crafted path cannot inject commands.
- Temporary WAV files are created with `tempfile` and deleted after use.
- The GUI performs network work on background threads and never blocks the UI.

## Known limitations (not vulnerabilities, but you should know)

1. **A distributed `.exe` cannot keep a secret.** Any `SPOTIPY_CLIENT_SECRET`
   bundled into a binary is extractable. That is why the app asks each user for
   their *own* credentials. Moving to the **PKCE** flow (`SpotifyPKCE`, no secret
   at all) is the planned fix.
2. **The OAuth callback listens on `127.0.0.1:8888`.** Any local process could
   race to capture the authorization code. In practice it also needs your client
   secret to exchange that code; PKCE closes this gap too.
3. **Token files are plaintext.** Anyone who can read your user profile can read
   the cached refresh token and act as you on Spotify until you revoke access.
   Revoke at <https://www.spotify.com/account/apps/>.
4. **No login rate limiting** on local accounts. Passwords are strong-hashed, but
   an offline attacker who already has your `user_data.json` can brute-force weak
   passwords.
5. **The executable is unsigned.** Windows SmartScreen may warn. Verify a build
   by compiling it yourself from source with `build.ps1`.
6. **Dependencies use `>=` ranges**, so installs are not byte-reproducible. For
   reproducible builds, pin versions (`pip freeze > requirements.lock`) after a
   verified install.
7. **A client secret was committed to this repository's git history before v1.0.**
   Treat any secret from that history as compromised. Rotate it in the
   [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   (**Settings → Reset secret**) and keep using your own credentials.

## Downloaded content

SpotiTool downloads audio from third-party services via yt-dlp. Downloading may
violate those services' terms of service and/or local copyright law. Use it only
for content you have the right to download. The authors accept no liability for
misuse.
