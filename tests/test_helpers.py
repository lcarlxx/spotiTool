"""Tests for the pure helper functions across SpotiTool."""

import pytest

from spotifyProject import __version__
from spotifyProject.music_recognition import extract_spotify_uri
from spotifyProject.spotify_downloader import (
    _extension_for,
    get_ydl_config,
    normalize_string,
    sanitize_filename,
)


def test_version_is_one_zero():
    assert __version__ == "1.0.0"


class TestExtractSpotifyUri:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("https://open.spotify.com/playlist/0ZyG7KYBa5cT8oJua0V4jJ",
             "spotify:playlist:0ZyG7KYBa5cT8oJua0V4jJ"),
            ("https://open.spotify.com/playlist/0ZyG7KYBa5cT8oJua0V4jJ?si=abc123",
             "spotify:playlist:0ZyG7KYBa5cT8oJua0V4jJ"),
            ("https://open.spotify.com/track/1CfuBY3BDdKpooQ9L5zgUc",
             "spotify:track:1CfuBY3BDdKpooQ9L5zgUc"),
            ("https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy",
             "spotify:album:4aawyAB9vmqN3uQ7FjRGTy"),
            ("spotify:playlist:0ZyG7KYBa5cT8oJua0V4jJ",
             "spotify:playlist:0ZyG7KYBa5cT8oJua0V4jJ"),
            ("0ZyG7KYBa5cT8oJua0V4jJ", "spotify:playlist:0ZyG7KYBa5cT8oJua0V4jJ"),
        ],
    )
    def test_valid_inputs(self, raw, expected):
        assert extract_spotify_uri(raw) == expected

    @pytest.mark.parametrize("raw", ["", "   ", None, "not a link", "https://example.com/x"])
    def test_invalid_inputs(self, raw):
        assert extract_spotify_uri(raw) is None


class TestSanitizeFilename:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ('AC/DC: Back in Black?', 'AC_DC_ Back in Black_'),
            ('a<b>c:d"e|f?g*h', 'a_b_c_d_e_f_g_h'),
            ('trailing dots...', 'trailing dots'),
            ('trailing spaces   ', 'trailing spaces'),
        ],
    )
    def test_sanitises(self, raw, expected):
        assert sanitize_filename(raw) == expected

    def test_truncates_long_names(self):
        assert len(sanitize_filename("x" * 400)) <= 150

    def test_keeps_safe_characters(self):
        assert sanitize_filename("Björk - Jóga (Live)") == "Björk - Jóga (Live)"


class TestNormalizeString:
    def test_strips_bracketed_qualifiers(self):
        assert "remastered" not in normalize_string("Song (Remastered 2011)")
        assert normalize_string("Song (feat. Someone)") == "song"

    def test_lowercases_and_collapses_spaces(self):
        assert normalize_string("  Hello   World  ") == "hello world"

    def test_handles_empty(self):
        assert normalize_string("") == ""


class TestExtensionFor:
    @pytest.mark.parametrize(
        "fmt, expected",
        [
            ("flac", "flac"),
            ("FLAC (Lossless)", "flac"),
            ("mp3", "mp3"),
            ("MP3 320kbps", "mp3"),
            ("m4a", "m4a"),
            ("aac", "m4a"),
            ("wav", "wav"),
            ("", "mp3"),
        ],
    )
    def test_mapping(self, fmt, expected):
        assert _extension_for(fmt) == expected


class TestYdlConfig:
    @pytest.mark.parametrize("bitrate", ["128", "192", "256", "320", "999"])
    def test_any_bitrate_is_accepted(self, bitrate):
        """Regression: an unknown bitrate used to raise KeyError."""
        opts, ext = get_ydl_config("mp3", bitrate, "/tmp/track")
        assert ext == "mp3"
        assert opts["postprocessors"][0]["preferredcodec"] == "mp3"

    @pytest.mark.parametrize(
        "fmt, ext, codec",
        [
            ("flac", "flac", "flac"),
            ("wav", "wav", "wav"),
            ("m4a", "m4a", "aac"),
            ("aac", "m4a", "aac"),
            ("mp3", "mp3", "mp3"),
        ],
    )
    def test_formats(self, fmt, ext, codec):
        opts, produced = get_ydl_config(fmt, "320", "/tmp/track")
        assert produced == ext
        assert opts["postprocessors"][0]["preferredcodec"] == codec

    def test_output_template_uses_placeholder(self):
        opts, _ = get_ydl_config("mp3", "320", "/tmp/track")
        assert opts["outtmpl"] == "/tmp/track.%(ext)s"

    def test_player_clients_option(self):
        opts, _ = get_ydl_config("mp3", "320", "/tmp/t", player_clients="android_vr,ios")
        assert opts["extractor_args"]["youtube"]["player_client"] == ["android_vr", "ios"]

    def test_cookies_option(self):
        opts, _ = get_ydl_config("mp3", "320", "/tmp/t", cookies_from_browser="chrome")
        assert opts["cookiesfrombrowser"] == ("chrome",)
