"""Central logging configuration.

Logs go to user_data/spotitool.log so problems are still diagnosable from a
packaged windowed executable, where there is no console to print to.
"""
from __future__ import annotations

import logging
import sys

from .config import USER_DATA_DIR

LOG_FILE = USER_DATA_DIR / "spotitool.log"
_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def setup_logging(level: int = logging.INFO, log_file=LOG_FILE) -> logging.Logger:
    """Configure root logging once. Safe to call repeatedly."""
    root = logging.getLogger()
    if getattr(root, "_spotitool_configured", False):
        return root

    root.setLevel(level)
    formatter = logging.Formatter(_FORMAT)

    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # Read only location: keep running with console logging only.
        pass

    # A windowed PyInstaller build has no stdout/stderr to attach to.
    if sys.stderr is not None:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

    root._spotitool_configured = True
    return root
