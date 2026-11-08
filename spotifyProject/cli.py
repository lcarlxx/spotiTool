"""Command-line interface for spotiTool — lets you test the app's core
features (login, stats, recognition, downloads) without launching the GUI.

Usage (from the repo root):
    python -m spotifyProject login
    python -m spotifyProject stats [--range short|medium|long]
    python -m spotifyProject recognize [--source system|mic] [--duration 10] [--add --user NAME]
    python -m spotifyProject download <spotify-url> [--format flac|mp3] [--bitrate 320] [--out DIR]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
import threading

import scipy.io.wavfile as wav
import sounddevice as sd

from .spotify_auth import get_spotify_client, add_song_to_playlist
from .music_recognition import _find_system_audio_device, _recognize_with_shazam


# ── login ─────────────────────────────────────────────────────────────────────

def cmd_login(args) -> int:
    """Run the Spotify OAuth flow once so the token is cached for the GUI."""
    print("Opening browser for Spotify login...")
    sp = get_spotify_client()
    me = sp.current_user()
    print(f"✅ Logged in and token cached as: {me.get('display_name') or me['id']}")
    return 0


# ── stats ─────────────────────────────────────────────────────────────────────

def cmd_stats(args) -> int:
    sp = get_spotify_client()
    time_range = {"short": "short_term", "medium": "medium_term", "long": "long_term"}[args.range]

    print(f"\n🎨 Top Artists ({args.range.replace('_', ' ')})")
    print("-" * 50)
    artists = sp.current_user_top_artists(limit=10, time_range=time_range).get("items", [])
    for i, a in enumerate(artists, 1):
        genres = ", ".join(a.get("genres", [])[:3])
        print(f"{i:>2}. {a['name']}" + (f"  ({genres})" if genres else ""))
    if not artists:
        print("No data yet — listen to some music first!")

    print(f"\n🎵 Top Tracks")
    print("-" * 50)
    tracks = sp.current_user_top_tracks(limit=10, time_range=time_range).get("items", [])
    for i, t in enumerate(tracks, 1):
        print(f"{i:>2}. {t['name']} — {t['artists'][0]['name']}")
    if not tracks:
        print("No data yet — listen to some music first!")

    print(f"\n🕒 Recently Played")
    print("-" * 50)
    recent = sp.current_user_recently_played(limit=10).get("items", [])
    for item in recent:
        t = item["track"]
        print(f"• {t['name']} — {t['artists'][0]['name']}")
    if not recent:
        print("No recent play history found.")
    return 0


# ── music recognition ─────────────────────────────────────────────────────────

def _record_and_recognize(duration: int, samplerate: int, source: str) -> dict | None:
    if source == "system":
        device = _find_system_audio_device()
        if device is None:
            raise RuntimeError(
                "No system audio loopback device found (Stereo Mix or equivalent). "
                "Try --source mic instead."
            )
    else:
        device = None  # default input device (microphone)

    print(f"🎙️ Recording {duration}s via {source}... play the song now!")
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate,
                       channels=1, dtype="int16", device=device)
    sd.wait()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav.write(tmp.name, samplerate, recording)
        temp_path = tmp.name

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_recognize_with_shazam(temp_path))
        finally:
            loop.close()
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def cmd_recognize(args) -> int:
    result = _record_and_recognize(args.duration, 44100, args.source)

    if not result:
        print("❌ Shazam couldn't identify the song. Try clearer/louder audio.")
        return 1

    title, artist = result["title"], result["artist"]
    print(f"\n🎵 Found: {title} by {artist}")
    if result.get("uri"):
        print(f"   Spotify URI: {result['uri']}")
    else:
        print("   (no Spotify link embedded in the Shazam result)")

    if args.add:
        if not result.get("uri"):
            print("❌ Cannot add: no Spotify URI for this track.")
            return 1
        if args.playlist:
            playlist_id = args.playlist
        elif args.user:
            from .auth import get_user_playlist
            playlist_id = get_user_playlist(args.user)
            if not playlist_id:
                print(f"❌ User '{args.user}' has no saved playlist. "
                      "Pick one in the GUI first, or pass --playlist <id|link>.")
                return 1
        else:
            print("❌ To add the song, pass --user NAME (saved playlist) or --playlist ID.")
            return 1

        sp = get_spotify_client()
        add_song_to_playlist(sp, result["uri"], playlist_id)
        print(f"✅ Added '{title}' to playlist {playlist_id}")
    return 0


# ── downloads ─────────────────────────────────────────────────────────────────

def cmd_download(args) -> int:
    from .spotify_downloader import download_track

    sp = get_spotify_client()
    print(f"⬇️ Downloading {args.url} as {args.format}...")
    result = download_track(
        sp,
        args.url,
        format=args.format,
        bitrate=str(args.bitrate),
        output_dir=args.out,
        progress_callback=lambda d: print(f"   {d}", end="\r", flush=True) if d else None,
    )
    if result:
        print(f"\n✅ Done: {result}")
    else:
        print("\n❌ Download failed — see messages above.")
        return 1
    return 0


# ── argument parsing ──────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m spotifyProject",
        description="spotiTool CLI — test core features without the GUI.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="Run Spotify OAuth once and cache the token")

    p_stats = sub.add_parser("stats", help="Print top artists, tracks and recent plays")
    p_stats.add_argument("--range", choices=["short", "medium", "long"],
                         default="short", help="Time range (default: short)")
    p_stats.set_defaults(func=cmd_stats)

    p_rec = sub.add_parser("recognize", help="Identify the song currently playing")
    p_rec.add_argument("--source", choices=["system", "mic"], default="system",
                       help="Audio source (default: system)")
    p_rec.add_argument("--duration", type=int, default=10,
                       help="Recording length in seconds (default: 10)")
    p_rec.add_argument("--add", action="store_true",
                       help="Add the found song to your playlist")
    p_rec.add_argument("--user", help="App username whose saved playlist to use (with --add)")
    p_rec.add_argument("--playlist", help="Playlist ID or link to add to (with --add)")
    p_rec.set_defaults(func=cmd_recognize)

    p_dl = sub.add_parser("download", help="Download a track/album/playlist by Spotify URL")
    p_dl.add_argument("url", help="Spotify track, album or playlist URL")
    p_dl.add_argument("--format", choices=["flac", "mp3", "m4a", "wav"], default="flac")
    p_dl.add_argument("--bitrate", type=int, default=320, help="Bitrate for lossy formats")
    p_dl.add_argument("--out", default=None, help="Output directory (default: Downloads/)")
    p_dl.set_defaults(func=cmd_download)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to cp1252 and crash on emoji in output
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
        print("\nInterrupted.")
        return 130
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())