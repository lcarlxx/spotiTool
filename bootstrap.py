"""Shared import bootstrap for the launchers.

`run.py` and `run_cli.py` both need the repository root on sys.path so that
`import spotifyProject` works when the executable is started from any directory.
"""
import os
import sys


def ensure_import_path() -> None:
    """Put this file's directory first on sys.path (idempotent)."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
