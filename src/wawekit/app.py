"""Application composition root.

This is the *one* module that assembles the whole application in the correct
order and owns the Qt event loop. Everything else is a component that gets wired
together here. Keeping assembly in a single place (the "composition root"
pattern) makes startup easy to read and reason about.

Startup sequence
----------------
1. Create the QApplication and set identity (name/org) — this makes Qt's
   standard-path lookups return app-scoped directories.
2. Ensure the user data/log/config directories exist.
3. Load configuration (defaults + user overrides).
4. Initialize logging at the configured level.
5. Apply the theme.
6. Build and show the main window.
7. Run the event loop.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from wawekit.core import constants
from wawekit.core.config import load_config
from wawekit.core.logging_config import setup_logging
from wawekit.core.paths import ensure_app_dirs

logger = logging.getLogger(__name__)

#: Location of the shipped default settings, relative to the repo root.
#: When frozen by PyInstaller this file may be absent, which is fine — the
#: dataclass defaults still apply.
_SHIPPED_DEFAULTS = Path(__file__).resolve().parents[2] / "config" / "default_settings.toml"


def _create_application(argv: list[str]) -> QApplication:
    """Create the QApplication and set its identity for path scoping."""
    app = QApplication(argv)
    app.setApplicationName(constants.APP_NAME)
    app.setApplicationDisplayName(constants.APP_NAME)
    app.setOrganizationName(constants.ORG_NAME)
    app.setApplicationVersion(constants.APP_VERSION)
    return app


def run(argv: list[str] | None = None) -> int:
    """Start the application and block until it exits.

    Parameters
    ----------
    argv:
        Command-line arguments; defaults to :data:`sys.argv`.

    Returns
    -------
    int
        The Qt event loop's exit code (0 on clean exit).

    """
    argv = list(sys.argv if argv is None else argv)

    app = _create_application(argv)
    ensure_app_dirs()

    config = load_config(shipped_defaults=_SHIPPED_DEFAULTS)
    logfile = setup_logging(config.log_level)
    logger.info("Starting %s %s", constants.APP_NAME, constants.APP_VERSION)
    logger.info("Log file: %s", logfile)

    # Imported here (not at module top) so logging/config are ready first and so
    # importing wawekit.app never forces the GUI stack to load prematurely.
    from wawekit.gui.icons import get_icon
    from wawekit.gui.main_window import MainWindow
    from wawekit.gui.themes.theme_manager import ThemeManager

    app.setWindowIcon(get_icon("app"))

    theme_manager = ThemeManager(app, initial_theme=config.theme)
    window = MainWindow(config=config, theme_manager=theme_manager)
    window.show()

    exit_code = app.exec()
    logger.info("Application exited with code %s", exit_code)
    return exit_code
