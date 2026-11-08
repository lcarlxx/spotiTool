"""Command-line interface for spotiTool.

Test and use the app's core features without launching the GUI:

    python -m spotifyProject validate
    python -m spotifyProject login
    python -m spotifyProject stats --range short
    python -m spotifyProject recognize --source system --duration 10
    python -m spotifyProject download <spotify-url> --format flac
    python -m spotifyProject gui
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile

import wave
import sounddevice as sd

from . import __version__
from .config import CACHE_PATH, USER_DATA_DIR, get_spotify_credentials, validate_spotify_credentials
from .music_recognition import _find_system_audio_device, _recognize_with_shazam
from .spotify_auth import add_song_to_playlist, get_public_spotify_client, get_spotify_client

TIME_RANGES = {"short": "short_term", "medium": "medium_term", "long": "long_term"}


# helpers

def _out(msg: str = "") -> None:
    print(msg, flush=True)


def _fail(msg: str) -> int:
    _out(f"❌ {msg}")
    return 1


def _spotify_for_reads():
    """Use the cached OAuth session when present, else a public (no-login) client."""
    if CACHE_PATH.exists():
        return get_spotify_client()
    _out("ℹ️  No saved Spotify login found — using public API access "
         "(run `login` for full read access).")
    return get_public_spotify_client()


# validate

def cmd_validate(args) -> int:
    """Check that credentials and environment are set up correctly."""
    ok = True
    _out(f"SpotiTool {__version__}  ({_prog_name()})")
    _out("-" * 52)

    client_id, client_secret, redirect_uri = get_spotify_credentials()
    if client_id and client_secret:
        _out(f"✅ Credentials found (client ID …{client_id[-6:]})")
    else:
        ok = False
        missing = []
        if not client_id:
            missing.append("SPOTIPY_CLIENT_ID")
        if not client_secret:
            missing.append("SPOTIPY_CLIENT_SECRET")
        _out(f"❌ Missing credentials: {', '.join(missing)}")
        _out("   Fix by EITHER setting these environment variables:")
        _out("     setx SPOTIPY_CLIENT_ID \"your-id\"")
        _out("     setx SPOTIPY_CLIENT_SECRET \"your-secret\"")
        _out("   OR creating a file named spotify_credentials.json in:")
        _out(f"     {USER_DATA_DIR.parent}")
    _out(f"   Redirect URI: {redirect_uri}")

    try:
        import shutil as _shutil
        if _shutil.which("ffmpeg"):
            _out("✅ ffmpeg found on PATH")
        else:
            ok = False
            _out("❌ ffmpeg not found on PATH (needed for downloads)")
    except Exception as exc:  # pragma: no cover
        _out(f"⚠️  Could not check ffmpeg: {exc}")

    try:
        devices = sd.query_devices()
        inputs = [d for d in devices if d.get("max_input_channels", 0) > 0]
        _out(f"✅ Audio input devices: {len(inputs)}")
        loopback = _find_system_audio_device()
        if loopback is None:
            _out("⚠️  No system-audio loopback device found — use `recognize --source mic`")
        else:
            _out(f"✅ System audio device: {devices[loopback]['name']}")
    except Exception as exc:
        _out(f"⚠️  Audio device check failed: {exc}")

    if CACHE_PATH.exists():
        _out(f"✅ Spotify login cached ({CACHE_PATH})")
    else:
        _out(f"ℹ️  Not logged in yet — run `{_prog_name()} login`")
    _out(f"ℹ️  Data directory: {USER_DATA_DIR}")

    if ok:
        _out("\n✅ Setup looks good.")
        return 0
    _out("\n❌ Setup needs attention (see ❌ items above).")
    return 1


# login

def cmd_login(args) -> int:
    validate_spotify_credentials()
    _out("Opening your browser for Spotify login…")
    sp = get_spotify_client(force_reauth=args.force)
    me = sp.current_user()
    _out(f"✅ Logged in as: {me.get('display_name') or me.get('id')}")
    _out(f"   Token cached at: {CACHE_PATH}")
    return 0


# stats

def cmd_stats(args) -> int:
    try:
        sp = _spotify_for_reads()
    except Exception as exc:
        return _fail(str(exc))

    time_range = TIME_RANGES[args.range]
    failures = 0

    def section(title: str, fetch, render) -> None:
        nonlocal failures
        _out(f"\n{title}")
        _out("-" * 52)
        try:
            items = fetch()
            if items:
                for line in render(items):
                    _out(line)
            else:
                _out("No data yet — listen to some music first!")
        except Exception as exc:
            failures += 1
            msg = str(exc)
            if any(code in msg for code in ("401", "403")) or "scope" in msg.lower():
                _out("⚠️  Not available with the current login.\n"
                     f"    Run: {_prog_name()} login")
            else:
                _out(f"⚠️  Could not load: {msg}")

    section(
        f"🎨 Top Artists ({args.range})",
        lambda: sp.current_user_top_artists(limit=10, time_range=time_range).get("items", []),
        lambda items: [
            f"{i:>2}. {a['name']}" + (f"  ({', '.join(a.get('genres', [])[:3])})"
                                      if a.get("genres") else "")
            for i, a in enumerate(items, 1)
        ],
    )
    section(
        "🎵 Top Tracks",
        lambda: sp.current_user_top_tracks(limit=10, time_range=time_range).get("items", []),
        lambda items: [
            f"{i:>2}. {t['name']} — {t['artists'][0]['name']}"
            for i, t in enumerate(items, 1)
        ],
    )
    section(
        "🕒 Recently Played",
        lambda: sp.current_user_recently_played(limit=10).get("items", []),
        lambda items: [
            f"• {it['track']['name']} — {it['track']['artists'][0]['name']}"
            for it in items
        ],
    )
    return 0 if failures == 0 else 1


# recognize

def _write_wav(path: str, samplerate: int, recording) -> None:
    """Write a mono int16 numpy recording to a WAV file using the stdlib."""
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(samplerate)
        handle.writeframes(recording.tobytes())


def _record(duration: int, samplerate: int, source: str) -> str:
    """Record audio and return the path to a temporary WAV file."""
    if source == "system":
        device = _find_system_audio_device()
        if device is None:
            raise RuntimeError(
                "No system audio loopback device found (Stereo Mix / 'What U Hear'). "
                "Try --source mic instead."
            )
    else:
        device = None  # default microphone

    _out(f"🎙️  Recording {duration}s via {source} — play the song now!")
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate,
                       channels=1, dtype="int16", device=device)
    sd.wait()

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    _write_wav(tmp.name, samplerate, recording)
    return tmp.name


def _resolve_track_uri(title: str, artist: str) -> str | None:
    """Find a spotify:track: URI when Shazam did not embed one."""
    try:
        sp = _spotify_for_reads()
        for query in (f'track:"{title}" artist:"{artist}"', f"{title} {artist}"):
            try:
                items = sp.search(q=query, type="track", limit=5).get("tracks", {}).get("items", [])
            except Exception:
                continue
            if not items:
                continue
            target_title = title.lower().strip()
            target_artist = artist.lower().strip()
            for item in items:
                name = item["name"].lower().strip()
                owner = item["artists"][0]["name"].lower().strip()
                if name == target_title and owner == target_artist:
                    return item["uri"]
            return items[0]["uri"]
    except Exception:
        pass
    return None


def cmd_recognize(args) -> int:
    try:
        path = _record(args.duration, 44100, args.source)
    except Exception as exc:
        return _fail(str(exc))

    _out("🎵 Identifying with Shazam…")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_recognize_with_shazam(path))
        finally:
            loop.close()
            asyncio.set_event_loop(None)
    except Exception as exc:
        return _fail(f"Recognition failed: {exc}")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    if not result or not result.get("title"):
        return _fail("Shazam couldn't identify the song. Try clearer or louder audio.")

    title, artist = result["title"], result["artist"]
    uri = result.get("uri")
    _out(f"\n🎵 Found: {title} by {artist}")

    if uri:
        _out(f"   Spotify URI: {uri}")
    else:
        _out("   No Spotify link in the Shazam result — searching Spotify…")
        uri = _resolve_track_uri(title, artist)
        _out(f"   Spotify URI: {uri}" if uri else "   ❌ Not found on Spotify either")

    if args.add:
        if not uri:
            return _fail("Cannot add: track was not found on Spotify.")
        playlist_ref = args.playlist
        if not playlist_ref and args.user:
            from .auth import get_user_playlist
            playlist_ref = get_user_playlist(args.user)
            if not playlist_ref:
                return _fail(f"User '{args.user}' has no saved playlist. "
                             "Pick one in the GUI, or pass --playlist <id|link>.")
        if not playlist_ref:
            return _fail("To add the song, pass --user NAME or --playlist ID.")
        try:
            sp = get_spotify_client()
            used_id = add_song_to_playlist(sp, uri, playlist_ref)
            _out(f"✅ Added '{title}' to playlist {used_id}")
        except Exception as exc:
            return _fail(f"Could not add to playlist: {exc}")
    return 0


# download

def cmd_download(args) -> int:
    from .spotify_downloader import download_track

    url = args.url.strip()
    if not (url.startswith("spotify:") or "open.spotify.com" in url):
        return _fail(
            "That doesn't look like a Spotify link.\n"
            "   Examples:\n"
            "     https://open.spotify.com/track/<id>\n"
            "     https://open.spotify.com/album/<id>\n"
            "     https://open.spotify.com/playlist/<id>"
        )
    args.url = url

    fmt = args.format
    _out(f"⬇️  Downloading {args.url} as {fmt.upper()}…")
    try:
        sp = _spotify_for_reads()
        result = download_track(
            sp,
            args.url,
            format=fmt,
            bitrate=str(args.bitrate),
            output_dir=args.out,
            cookies_from_browser=args.cookies_from_browser,
        )
    except Exception as exc:
        return _fail(str(exc))

    _out(f"\n📁 Location: {result['target_dir']}")
    _out(f"✅ Downloaded: {result['success']}   ⏭️  Skipped: {result['skipped']}"
         f"   ❌ Failed: {result['failed']}")
    for err in result["errors"][:5]:
        _out(f"   • {err}")
    return 0 if result["failed"] == 0 else 1


# gui

def cmd_gui(args) -> int:
    try:
        from .main import main as gui_main
    except Exception as exc:
        return _fail(f"Could not start the GUI: {exc}")
    try:
        gui_main()
    except KeyboardInterrupt:
        return 0
    return 0


# argument parsing

def _prog_name() -> str:
    """Show the real executable name when frozen, the module path otherwise."""
    if getattr(sys, "frozen", False):
        return os.path.basename(sys.executable)
    return "python -m spotifyProject"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_prog_name(),
        description="SpotiTool CLI — run and test every feature without the GUI.",
    )
    parser.add_argument("--version", action="version", version=f"SpotiTool {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="Check credentials, ffmpeg and audio devices")
    p_val.set_defaults(func=cmd_validate)

    p_login = sub.add_parser("login", help="Log in to Spotify once and cache the token")
    p_login.add_argument("--force", action="store_true",
                         help="Ignore the cached token and log in again")
    p_login.set_defaults(func=cmd_login)

    p_stats = sub.add_parser("stats", help="Show top artists, top tracks and recently played")
    p_stats.add_argument("--range", choices=list(TIME_RANGES), default="short",
                         help="Time range (default: short)")
    p_stats.set_defaults(func=cmd_stats)

    p_rec = sub.add_parser("recognize", help="Identify the song that is currently playing")
    p_rec.add_argument("--source", choices=["system", "mic"], default="system",
                       help="Audio source (default: system)")
    p_rec.add_argument("--duration", type=int, default=10,
                       help="Recording length in seconds (default: 10)")
    p_rec.add_argument("--add", action="store_true", help="Add the found song to a playlist")
    p_rec.add_argument("--user", help="App username whose saved playlist to use (with --add)")
    p_rec.add_argument("--playlist", help="Playlist ID or link to add to (with --add)")
    p_rec.set_defaults(func=cmd_recognize)

    p_dl = sub.add_parser("download", help="Download a track, album or playlist")
    p_dl.add_argument("url", help="Spotify track, album or playlist URL")
    p_dl.add_argument("--format", choices=["flac", "mp3", "m4a", "wav"], default="flac")
    p_dl.add_argument("--bitrate", type=int, default=320,
                      help="Bitrate for lossy formats (default: 320)")
    p_dl.add_argument("--out", default=None, help="Output directory (default: ./Spotify FLAC Downloads)")
    p_dl.add_argument("--cookies-from-browser", default=None,
                      metavar="BROWSER",
                      help="Use browser cookies for YouTube (chrome, edge, firefox, …) "
                           "if downloads are blocked with HTTP 403")
    p_dl.set_defaults(func=cmd_download)

    p_gui = sub.add_parser("gui", help="Launch the desktop application")
    p_gui.set_defaults(func=cmd_gui)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to cp1252 and crash on emoji output
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        _out("\nInterrupted.")
        return 130
    except Exception as exc:
        return _fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
