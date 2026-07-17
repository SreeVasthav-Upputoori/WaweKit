"""Icon loading: packaged SVG files → multi-size :class:`QIcon` objects.

Icons ship as hand-authored SVGs inside ``wawekit/resources/icons`` and are
loaded with :mod:`importlib.resources`, so they work identically from source
and from a frozen PyInstaller bundle. Each icon is rasterized at several sizes
(menus, toolbars, window icon) and cached — QIcon then picks the best size.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from importlib import resources

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

logger = logging.getLogger(__name__)

#: Raster sizes registered per icon; Qt picks the closest for each use.
_SIZES = (16, 24, 32, 48, 64)


@lru_cache(maxsize=64)
def get_icon(name: str) -> QIcon:
    """Return the icon named ``name`` (an SVG in ``resources/icons``).

    A missing or broken asset logs a warning and returns an empty icon —
    branding must never crash the application.
    """
    try:
        svg = resources.files("wawekit.resources").joinpath(f"icons/{name}.svg").read_bytes()
    except (OSError, ModuleNotFoundError):
        logger.warning("Icon asset %r not found", name)
        return QIcon()

    icon = QIcon()
    renderer = QSvgRenderer(QByteArray(svg))
    for size in _SIZES:
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(QPixmap.fromImage(image))
    return icon
