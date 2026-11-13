"""Shared pytest fixtures and import bootstrap."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def user_data_dir(tmp_path, monkeypatch):
    """Point the app's data directory at a temporary folder."""
    from spotifyProject import auth

    monkeypatch.setattr(auth, "DATA_FILE", tmp_path / "user_data.json")
    return tmp_path
