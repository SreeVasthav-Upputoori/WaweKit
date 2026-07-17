"""Shared pytest fixtures.

Qt requires exactly one :class:`QApplication` per process. ``pytest-qt`` provides
a ``qtbot``/``qapp`` fixture that manages this for us, so GUI code can be
constructed and driven inside tests without a real display (using the ``offscreen``
Qt platform in CI).
"""

from __future__ import annotations

import os

import pytest

# Force Qt to use a headless platform plugin during tests so they run on CI and
# on machines without a display server.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def app_config():
    """Return a default AppConfig for tests that need one."""
    from wawekit.core.config import AppConfig

    return AppConfig()
