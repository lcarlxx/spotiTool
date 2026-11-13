"""SpotiTool command-line launcher.

Run from source with:  python run_cli.py <command>
Or use the packaged executable:  spotitool-cli.exe <command>

Examples:
    python run_cli.py validate
    python run_cli.py stats
    python run_cli.py recognize --source mic
    python run_cli.py download <spotify-url>
"""
import sys

from bootstrap import ensure_import_path

ensure_import_path()

if __name__ == "__main__":
    from spotifyProject.cli import main

    sys.exit(main())
