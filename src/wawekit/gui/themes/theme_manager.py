"""Load and apply Qt Style Sheets (the desktop equivalent of CSS).

Qt lets you restyle an entire application with a single stylesheet string
applied to the :class:`QApplication`. We keep those stylesheets in ``.qss``
files next to this module and load them with :mod:`importlib.resources`, which
works both from source *and* from a frozen PyInstaller bundle (unlike raw file
paths).

Since Module 3 the manager is a :class:`~PySide6.QtCore.QObject` that emits
:attr:`ThemeManager.theme_changed` — molecule depictions must re-render with a
different atom palette when the theme flips, so interested widgets subscribe
instead of the window pushing updates to each of them by hand (the observer
pattern, via Qt signals).
"""

from __future__ import annotations

import logging
from importlib import resources

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

#: Ordered mapping of theme name → stylesheet filename in this package.
_THEMES: dict[str, str] = {
    "dark": "dark.qss",
    "light": "light.qss",
}

#: Fallback used if an unknown theme name is requested.
_DEFAULT_THEME = "dark"


class ThemeManager(QObject):
    """Applies and toggles application-wide visual themes.

    Parameters
    ----------
    app:
        The running :class:`QApplication` whose stylesheet we control.
    initial_theme:
        Name of the theme to apply immediately (``"dark"`` or ``"light"``).

    """

    #: Emitted with the new theme name after a theme has been applied.
    theme_changed = Signal(str)

    def __init__(self, app: QApplication, initial_theme: str = _DEFAULT_THEME) -> None:
        super().__init__()
        self._app = app
        self._current = ""
        self.apply(initial_theme)

    @property
    def current(self) -> str:
        """Name of the currently applied theme."""
        return self._current

    @property
    def is_dark(self) -> bool:
        """Whether the current theme is the dark one (drives depiction palette)."""
        return self._current == "dark"

    @staticmethod
    def available() -> list[str]:
        """Return the list of selectable theme names."""
        return list(_THEMES)

    def _load_stylesheet(self, theme: str) -> str:
        """Read the ``.qss`` text for ``theme`` from packaged resources."""
        filename = _THEMES[theme]
        resource = resources.files("wawekit.gui.themes").joinpath(filename)
        return resource.read_text(encoding="utf-8")

    def apply(self, theme: str) -> None:
        """Apply ``theme`` to the whole application and notify subscribers.

        Unknown names fall back to the default theme rather than raising, so a
        stale config value can never prevent startup.
        """
        if theme not in _THEMES:
            logger.warning("Unknown theme %r; falling back to %r", theme, _DEFAULT_THEME)
            theme = _DEFAULT_THEME
        try:
            self._app.setStyleSheet(self._load_stylesheet(theme))
        except (OSError, ModuleNotFoundError) as exc:
            logger.error("Failed to load theme %r: %s", theme, exc)
            return
        self._current = theme
        logger.info("Applied %s theme", theme)
        self.theme_changed.emit(theme)

    def toggle(self) -> str:
        """Switch to the other theme and return the new theme's name."""
        nxt = "light" if self._current == "dark" else "dark"
        self.apply(nxt)
        return self._current
