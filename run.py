"""SpotiTool desktop app launcher.

Run from source with:  python run.py
Or use the packaged executable:  SpotiTool.exe
"""
import os
import sys
import traceback

# Make `import spotifyProject` work both from source and inside a frozen bundle.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _report_error(message: str) -> None:
    """Show a startup error to the user, with or without a console attached."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("SpotiTool — Startup Error", message)
        root.destroy()
    except Exception:
        try:
            print(message, file=sys.stderr)
        except Exception:
            pass


def main() -> int:
    try:
        from spotifyProject.main import main as gui_main
    except Exception as exc:
        _report_error(
            "SpotiTool could not start.\n\n"
            f"{exc}\n\n"
            "If you are running from source, install dependencies with:\n"
            "    pip install -r requirements.txt"
        )
        return 1

    try:
        gui_main()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        _report_error(
            "SpotiTool hit an unexpected error.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            + traceback.format_exc(limit=6)
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
