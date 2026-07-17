"""Application-wide constant facts.

These values are imported anywhere the app needs to identify itself: the window
title, the About dialog, the config/log directory names, and the packaging
metadata. Centralizing them here means a rename is a one-line change.

Nothing in this module performs logic or I/O — it is pure data.
"""

from __future__ import annotations

from wawekit import __version__

#: Human-facing product name (window titles, dialogs, docs).
APP_NAME: str = "Wawekit"

#: Machine-safe identifier used for the importable package and CLI.
APP_SLUG: str = "wawekit"

#: Organization/author name. Used by Qt's QSettings and OS path helpers to
#: namespace the app's config and data directories.
ORG_NAME: str = "Wawekit"

#: Short one-line description shown in the About dialog and packaging metadata.
APP_DESCRIPTION: str = "Professional open-source desktop cheminformatics toolkit."

#: Application version, sourced from the package to avoid duplication.
APP_VERSION: str = __version__

#: Project homepage / source repository (edit once you publish).
PROJECT_URL: str = "https://github.com/your-org/wawekit"

#: SPDX identifier of the project license.
LICENSE: str = "MIT"
