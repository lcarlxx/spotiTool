# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for SpotiTool v1.0.

Builds TWO executables from the same codebase:

  dist/SpotiTool.exe       — the desktop GUI app (no console window)
  dist/spotitool-cli.exe   — the CLI tool (console output, for scripting)

Build with:
    pyinstaller spotiTool.spec --noconfirm

Both are single-file executables. User data (accounts, Spotify token cache)
is stored in a `user_data` folder next to the executable, so the app can be
moved anywhere and still keep its settings.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

PROJECT_ROOT = Path(SPECPATH).resolve()
PACKAGE_DIR = PROJECT_ROOT / "spotifyProject"

# ── Bundled data files ────────────────────────────────────────────────────────
datas = []

# CustomTkinter ships themes + fonts as data files
try:
    datas += collect_data_files("customtkinter")
except Exception:
    pass

# The app logo (loaded from RESOURCE_DIR, i.e. the bundled spotifyProject dir)
logo = PACKAGE_DIR / "spotiTool_logo-blurred.png"
if logo.is_file():
    datas.append((str(logo), "spotifyProject"))

# yt-dlp ships data/plugins that are resolved at runtime
try:
    _yt_datas, _yt_binaries, _yt_hidden = collect_all("yt_dlp")
    datas += _yt_datas
    binaries = _yt_binaries
    yt_hidden = _yt_hidden
except Exception:
    binaries = []
    yt_hidden = []

# ── Hidden imports ────────────────────────────────────────────────────────────
hiddenimports = list(yt_hidden)
for package in ("shazamio", "mutagen", "sounddevice", "spotipy", "PIL"):
    try:
        hiddenimports += collect_submodules(package)
    except Exception:
        pass

hiddenimports += [
    "spotifyProject",
    "spotifyProject.cli",
    "spotifyProject.config",
    "spotifyProject.auth",
    "spotifyProject.homepage",
    "spotifyProject.main",
    "spotifyProject.music_recognition",
    "spotifyProject.spotify_auth",
    "spotifyProject.spotify_downloader",
    "spotifyProject.spotify_stats",
    "tkinter",
    "tkinter.messagebox",
    "tkinter.filedialog",
]

# Exclude heavy/unused libraries to keep the bundle smaller
excludes = [
    "matplotlib", "pandas", "scipy",
    "PyQt5", "PyQt6", "PySide2", "PySide6", "wx", "IPython", "pytest",
    "setuptools._distutils",
]

block_cipher = None


def make_analysis(entry_script: str) -> Analysis:
    return Analysis(
        [str(PROJECT_ROOT / entry_script)],
        pathex=[str(PROJECT_ROOT)],
        binaries=binaries,
        datas=datas,
        hiddenimports=hiddenimports,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=excludes,
        noarchive=False,
        cipher=block_cipher,
    )


# ── GUI build (windowed) ──────────────────────────────────────────────────────
gui_analysis = make_analysis("run.py")
gui_pyz = PYZ(gui_analysis.pure, gui_analysis.zipped_data, cipher=block_cipher)

gui_exe = EXE(
    gui_pyz,
    gui_analysis.scripts,
    gui_analysis.binaries,
    gui_analysis.zipfiles,
    gui_analysis.datas,
    [],
    name="SpotiTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# ── CLI build (console) ───────────────────────────────────────────────────────
cli_analysis = make_analysis("run_cli.py")
cli_pyz = PYZ(cli_analysis.pure, cli_analysis.zipped_data, cipher=block_cipher)

cli_exe = EXE(
    cli_pyz,
    cli_analysis.scripts,
    cli_analysis.binaries,
    cli_analysis.zipfiles,
    cli_analysis.datas,
    [],
    name="spotitool-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
