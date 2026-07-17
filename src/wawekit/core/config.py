"""Typed application configuration.

We model configuration as an immutable :func:`dataclasses.dataclass` rather than
passing raw dictionaries around. Benefits:

* **Type safety** — every setting has a declared type and default.
* **Discoverability** — your IDE autocompletes ``config.theme``.
* **Validation seam** — a single ``__post_init__`` could validate values.

Loading strategy (layered, last-wins):

1. Hardcoded field defaults below.
2. Shipped defaults in ``config/default_settings.toml`` (optional).
3. User overrides in ``<config_dir>/settings.toml`` (optional).

Reading TOML uses the standard-library :mod:`tomllib` (Python 3.11+), so we add
no dependency. Writing settings back is intentionally deferred to Module 15
(Settings); Module 1 only needs to *read* configuration.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any

from wawekit.core.paths import config_dir

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Immutable snapshot of user-configurable application settings.

    Attributes
    ----------
    theme:
        Active UI theme, either ``"dark"`` or ``"light"``.
    log_level:
        Root logging level name, e.g. ``"INFO"`` or ``"DEBUG"``.
    window_width, window_height:
        Default main-window size in pixels.
    remember_window_geometry:
        Whether to persist and restore window size/position (used from Module 15).

    """

    theme: str = "dark"
    log_level: str = "INFO"
    window_width: int = 1280
    window_height: int = 800
    remember_window_geometry: bool = True

    def with_overrides(self, **changes: Any) -> AppConfig:
        """Return a new config with ``changes`` applied (dataclass is frozen)."""
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (used when persisting settings later)."""
        return asdict(self)


def _read_toml(path: Path) -> dict[str, Any]:
    """Read a TOML file into a dict, returning ``{}`` if it is missing/invalid.

    Configuration must never crash the app: a malformed user file is logged and
    ignored so the application still starts with sensible defaults.
    """
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        logger.warning("Ignoring unreadable config file %s: %s", path, exc)
        return {}


def _filter_known(raw: dict[str, Any]) -> dict[str, Any]:
    """Drop keys that are not fields of :class:`AppConfig`.

    This protects us from crashing on stray/legacy keys in a user's file.
    """
    known = {f.name for f in fields(AppConfig)}
    return {k: v for k, v in raw.items() if k in known}


def load_config(shipped_defaults: Path | None = None) -> AppConfig:
    """Build an :class:`AppConfig` by layering defaults and user overrides.

    Parameters
    ----------
    shipped_defaults:
        Optional path to ``config/default_settings.toml`` bundled with the app.

    Returns
    -------
    AppConfig
        A fully-populated, immutable configuration object.

    """
    config = AppConfig()

    if shipped_defaults is not None:
        config = config.with_overrides(**_filter_known(_read_toml(shipped_defaults)))

    user_file = config_dir() / "settings.toml"
    config = config.with_overrides(**_filter_known(_read_toml(user_file)))

    logger.debug("Loaded configuration: %s", config)
    return config
