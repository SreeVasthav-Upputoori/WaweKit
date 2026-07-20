"""Capture figures for the SoftwareX paper from the *current* application.

Screenshots in a software paper are evidence about the shipped artefact, so
they must be regenerated whenever the interface changes rather than reused.
The previously available captures predated several features (the Plugins menu,
the standalone 3D viewer, the property-filter panel, the alerts column) and
still showed the earlier red–green agreement heatmap that was replaced with a
colour-vision-safe ramp — publishing them would have described software that
no longer exists.

Runs fully offscreen, driving the real MainWindow with real sample data:
nothing here is mocked or staged, so the figures show what a user sees.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Offscreen, but with real fonts so text in the figures is legible.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from wawekit.core.config import AppConfig  # noqa: E402
from wawekit.gui.main_window import MainWindow  # noqa: E402
from wawekit.gui.themes.theme_manager import ThemeManager  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "figures"
REPO = HERE.parent.parent
#: The reproducibility figure must show the feature *working*, which means a
#: dataset that actually contains protocol-sensitive structures. The similarity
#: demo set is chemically homogeneous and audits at 100% agreement, producing a
#: uniformly-coloured heatmap and an empty cause chart — technically correct and
#: completely uninformative as a figure. This set spans salts, charged species,
#: tautomer-ambiguous heterocycles, isotopes and stereocentres.
SAMPLE = REPO / "learning" / "research-track-R5-benchmark" / "benchmark_set.smi"

# Large enough that dock panels are readable at journal figure width.
WINDOW = (1680, 1000)


def _pump(app: QApplication, ms: int = 1200) -> None:
    """Let queued work and rendering settle before grabbing."""
    import time

    deadline = time.monotonic() + ms / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    app = QApplication(sys.argv)
    theme = ThemeManager(app, initial_theme="light")  # light reproduces better in print
    window = MainWindow(config=AppConfig(), theme_manager=theme)
    window.resize(*WINDOW)
    window.show()
    _pump(app)

    # Real data through the real loader.
    window._enqueue_paths([SAMPLE])
    for _ in range(600):
        app.processEvents()
        if window._table_panel.row_count:
            break
    _pump(app)

    # Compute descriptors first, so the table shows populated analysis columns
    # and the property-filter panel shows real ranges rather than its empty state.
    from wawekit.services.chemistry.descriptors import compute_descriptors

    compute_descriptors(window._table_panel.model.records)
    window._table_panel.refresh_descriptors()
    window._property_filter_panel.update_ranges(window._table_panel.model.records)
    _pump(app)

    window._table_panel._view.selectRow(0)
    _pump(app)
    window.grab().save(str(OUT / "fig1_main_window.png"))
    print("fig1_main_window.png — table, structure panel, descriptors")

    # The distinguishing feature: a real audit, computed not staged.
    from wawekit.services.reproducibility import analyze_divergence, compute_metrics
    from wawekit.services.reproducibility.protocol import DEFAULT_PROTOCOLS

    records = [(r.name, r.mol) for r in window._table_panel.model.records]
    run = analyze_divergence(records, DEFAULT_PROTOCOLS, True)
    window._repro_panel.set_results(run, compute_metrics(run))
    window._repro_dock.show()
    window._repro_dock.raise_()
    window._repro_dock.setMinimumHeight(420)  # give the charts room in the figure
    _pump(app)
    window.grab().save(str(OUT / "fig2_reproducibility_audit.png"))
    print("fig2_reproducibility_audit.png — agreement heatmap + cause spectrum")

    # The panel alone, at full size, for a legible close-up.
    window._repro_panel.resize(1200, 620)
    _pump(app)
    window._repro_panel.grab().save(str(OUT / "fig3_reproducibility_panel.png"))
    print("fig3_reproducibility_panel.png — panel close-up")

    print(f"\nWrote figures to {OUT}")
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
