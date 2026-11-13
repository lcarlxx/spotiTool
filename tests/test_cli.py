"""Tests for the CLI argument parsing and small text helpers."""

import pytest

from spotifyProject.cli import _prog_name, build_parser


def test_prog_name_is_module_path_from_source():
    assert _prog_name() == "python -m spotifyProject"


@pytest.mark.parametrize(
    "argv, command",
    [
        (["validate"], "validate"),
        (["login"], "login"),
        (["login", "--force"], "login"),
        (["stats"], "stats"),
        (["stats", "--range", "long"], "stats"),
        (["recognize"], "recognize"),
        (["recognize", "--source", "mic", "--duration", "5"], "recognize"),
        (["recognize", "--add", "--user", "alice"], "recognize"),
        (["download", "https://open.spotify.com/track/x"], "download"),
        (["download", "u", "--format", "mp3", "--bitrate", "192"], "download"),
        (["gui"], "gui"),
    ],
)
def test_commands_parse(argv, command):
    args = build_parser().parse_args(argv)
    assert args.command == command
    assert callable(args.func)


def test_defaults():
    parser = build_parser()
    assert parser.parse_args(["recognize"]).source == "system"
    assert parser.parse_args(["recognize"]).duration == 10
    assert parser.parse_args(["stats"]).range == "short"
    assert parser.parse_args(["download", "u"]).format == "flac"
    assert parser.parse_args(["download", "u"]).bitrate == 320


def test_unknown_command_exits():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["nonsense"])


def test_invalid_format_rejected():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["download", "u", "--format", "ogg"])


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["--version"])
    assert excinfo.value.code == 0
    assert "1.0.0" in capsys.readouterr().out
