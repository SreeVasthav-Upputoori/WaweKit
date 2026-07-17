"""The application's main window (the desktop shell).

Module 2 turns the empty shell into a working tool: users open molecule files
via *File → Open* or by dragging them onto the window; parsing runs on a
background thread with a progress bar; results land in the molecule table and
the Workspace dock lists every loaded file.

Design notes
------------
* The window receives its collaborators (config, theme manager) through the
  constructor (*dependency injection*) instead of reaching for globals.
* File loads are queued and processed **one at a time** so the progress bar is
  always meaningful; dropping five files simply enqueues five loads.
* All RDKit work happens in :func:`~wawekit.services.io.molecule_loader.load_file`
  running inside a :class:`~wawekit.services.workers.FunctionWorker`; results
  come back through queued signals, so slots here always run on the GUI thread.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QStackedWidget,
)

from wawekit.core import constants
from wawekit.core.config import AppConfig
from wawekit.gui.dialogs.standardize_dialog import StandardizeDialog
from wawekit.gui.icons import get_icon
from wawekit.gui.themes.theme_manager import ThemeManager
from wawekit.gui.widgets.molecule_table import MoleculeTablePanel
from wawekit.gui.widgets.structure_viewer import StructureViewerPanel
from wawekit.services.chemistry.standardizer import (
    StandardizationReport,
    standardize_records,
)
from wawekit.services.io.molecule_loader import (
    SUPPORTED_EXTENSIONS,
    LoadReport,
    file_dialog_filter,
)
from wawekit.services.io.molecule_loader import load_file as load_molecule_file
from wawekit.services.workers import FunctionWorker

logger = logging.getLogger(__name__)

#: Cap on how many individual record errors we list in the summary dialog.
_MAX_ERRORS_SHOWN = 200


class MainWindow(QMainWindow):
    """Top-level window hosting menus, toolbar, docks and the molecule table.

    Parameters
    ----------
    config:
        The loaded application configuration (sizes, theme, ...).
    theme_manager:
        Shared manager used by the View menu to switch themes at runtime.

    """

    def __init__(self, config: AppConfig, theme_manager: ThemeManager) -> None:
        super().__init__()
        self._config = config
        self._theme_manager = theme_manager

        # Load queue state: paths waiting to be parsed, and the active worker
        # (referenced so Python's GC cannot collect it mid-run).
        self._pending_paths: list[Path] = []
        self._active_worker: FunctionWorker | None = None
        # Standardization worker (kept alive for the same GC reason). Loads are
        # paused while it runs so the dataset cannot change mid-pipeline.
        self._std_worker: FunctionWorker | None = None

        self.setWindowTitle(f"{constants.APP_NAME} {constants.APP_VERSION}")
        self.resize(config.window_width, config.window_height)
        self.setAcceptDrops(True)

        self._build_central_widget()
        self._build_docks()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()

        logger.info("Main window constructed")

    # ------------------------------------------------------------------ build
    def _build_central_widget(self) -> None:
        """Create a stacked central area: welcome page ↔ molecule table."""
        self._welcome = QLabel(
            f"Welcome to {constants.APP_NAME}\n\n"
            "Open molecule files (SDF, MOL, SMILES) via File → Open\n"
            "or drag and drop them anywhere on this window.",
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        self._welcome.setObjectName("welcomeLabel")

        self._table_panel = MoleculeTablePanel(dark=self._theme_manager.is_dark, parent=self)

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._welcome)
        self._stack.addWidget(self._table_panel)
        self.setCentralWidget(self._stack)

    def _build_docks(self) -> None:
        """Create the Workspace dock (loaded files) and the Structure dock."""
        dock = QDockWidget("Workspace", self)
        dock.setObjectName("workspaceDock")
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._sources_list = QListWidget(dock)
        dock.setWidget(self._sources_list)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self._workspace_dock = dock

        structure_dock = QDockWidget("Structure", self)
        structure_dock.setObjectName("structureDock")
        structure_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._structure_panel = StructureViewerPanel(
            dark=self._theme_manager.is_dark, parent=structure_dock
        )
        structure_dock.setWidget(self._structure_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, structure_dock)
        self._structure_dock = structure_dock

        # Cross-panel wiring: table selection drives the structure viewer, and
        # theme changes re-render every depiction with the matching palette.
        self._table_panel.selection_changed.connect(self._structure_panel.set_record)
        self._theme_manager.theme_changed.connect(self._on_theme_changed)

    def _build_actions(self) -> None:
        """Create reusable QActions shared by menus and the toolbar."""
        self.action_open = QAction(get_icon("open"), "&Open Molecules…", self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.setStatusTip("Open molecule files (SDF, MOL, SMILES)")
        self.action_open.triggered.connect(self._on_open_files)

        self.action_standardize = QAction(get_icon("standardize"), "&Standardize…", self)
        self.action_standardize.setShortcut("Ctrl+Shift+S")
        self.action_standardize.setStatusTip(
            "Clean structures: strip salts, neutralize, canonicalize, deduplicate"
        )
        self.action_standardize.triggered.connect(self._on_standardize)

        self.action_quit = QAction("E&xit", self)
        self.action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_quit.setStatusTip("Exit the application")
        self.action_quit.triggered.connect(self.close)

        self.action_toggle_theme = QAction(get_icon("theme"), "Toggle &Theme", self)
        self.action_toggle_theme.setShortcut("Ctrl+T")
        self.action_toggle_theme.setStatusTip("Switch between dark and light themes")
        self.action_toggle_theme.triggered.connect(self._on_toggle_theme)

        # QDockWidget provides ready-made checkable show/hide actions — no
        # custom handlers needed, and the checkmark stays in sync for free.
        self.action_toggle_workspace = self._workspace_dock.toggleViewAction()
        self.action_toggle_workspace.setText("&Workspace Panel")
        self.action_toggle_structure = self._structure_dock.toggleViewAction()
        self.action_toggle_structure.setText("&Structure Panel")

        self.action_about = QAction("&About", self)
        self.action_about.setStatusTip("About this application")
        self.action_about.triggered.connect(self._on_about)

    def _build_menus(self) -> None:
        """Assemble the menu bar from the shared actions."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.action_open)
        file_menu.addSeparator()
        file_menu.addAction(self.action_quit)

        chemistry_menu = menubar.addMenu("&Chemistry")
        chemistry_menu.addAction(self.action_standardize)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction(self.action_toggle_theme)
        view_menu.addSeparator()
        view_menu.addAction(self.action_toggle_workspace)
        view_menu.addAction(self.action_toggle_structure)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self.action_about)

    def _build_toolbar(self) -> None:
        """Create the main toolbar. Text-only for now; icons arrive with assets."""
        toolbar = self.addToolBar("Main")
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(True)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_standardize)
        toolbar.addSeparator()
        toolbar.addAction(self.action_toggle_theme)

    def _build_statusbar(self) -> None:
        """Create the status bar with a (hidden) progress bar for background loads."""
        self._progress = QProgressBar(self)
        self._progress.setMaximumWidth(220)
        self._progress.setVisible(False)
        self.statusBar().addPermanentWidget(self._progress)
        self.statusBar().showMessage("Ready")

    # ------------------------------------------------------------ drag & drop
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 — Qt override
        """Accept the drag if it carries at least one supported local file."""
        if any(self._url_is_supported(url) for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 — Qt override
        """Queue every dropped supported file for loading."""
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        event.acceptProposedAction()
        self._enqueue_paths(paths)

    @staticmethod
    def _url_is_supported(url) -> bool:  # noqa: ANN001 — QUrl
        """Return True if ``url`` is a local file with a supported extension."""
        return url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS

    # ------------------------------------------------------------ load queue
    def _enqueue_paths(self, paths: list[Path]) -> None:
        """Filter ``paths`` to supported formats, queue them, start loading."""
        supported = [p for p in paths if p.suffix.lower() in SUPPORTED_EXTENSIONS]
        rejected = [p for p in paths if p.suffix.lower() not in SUPPORTED_EXTENSIONS]
        if rejected:
            names = ", ".join(p.name for p in rejected)
            self.statusBar().showMessage(f"Skipped unsupported file(s): {names}", 5000)
            logger.warning("Skipped unsupported file(s): %s", names)
        if supported:
            self._pending_paths.extend(supported)
            self._start_next_load()

    def _start_next_load(self) -> None:
        """Start loading the next queued file, if idle and any remain.

        Loads also wait while standardization runs — the pipeline works on a
        snapshot of the dataset, and appending mid-run would lose records.
        """
        if self._active_worker is not None or self._std_worker is not None:
            return
        if not self._pending_paths:
            return
        path = self._pending_paths.pop(0)

        self.action_open.setEnabled(False)
        self._progress.setRange(0, 0)  # busy indicator until first progress signal
        self._progress.setVisible(True)
        self.statusBar().showMessage(f"Loading {path.name}…")

        worker = FunctionWorker(load_molecule_file, path, inject_progress=True)
        worker.signals.progress.connect(self._on_load_progress)
        worker.signals.finished.connect(self._on_load_finished)
        worker.signals.error.connect(self._on_load_error)
        self._active_worker = worker  # keep alive while the pool runs it
        QThreadPool.globalInstance().start(worker)
        logger.info("Started background load of %s", path)

    def _finish_current_load(self) -> None:
        """Reset per-load UI state and move on to the next queued file."""
        self._active_worker = None
        if not self._pending_paths:
            self._progress.setVisible(False)
            self.action_open.setEnabled(True)
        self._start_next_load()

    # --------------------------------------------------------------- handlers
    def _on_open_files(self) -> None:
        """Show the file dialog and queue the chosen files."""
        filenames, _ = QFileDialog.getOpenFileNames(
            self, "Open Molecule Files", "", file_dialog_filter()
        )
        if filenames:
            self._enqueue_paths([Path(f) for f in filenames])

    def _on_load_progress(self, done: int, total: int) -> None:
        """Update the status-bar progress bar from worker signals."""
        if self._progress.maximum() != total:
            self._progress.setRange(0, total)
        self._progress.setValue(done)

    def _on_load_finished(self, report: LoadReport) -> None:
        """Integrate a finished load: table, dock list, status, error summary."""
        self._table_panel.append_records(report.records)
        if self._table_panel.row_count:
            self._stack.setCurrentWidget(self._table_panel)

        self._sources_list.addItem(
            f"{report.source.name}  —  {report.n_loaded} molecule(s)"
            + (f", {report.n_failed} error(s)" if report.n_failed else "")
        )
        self.statusBar().showMessage(
            f"Loaded {report.n_loaded} molecule(s) from {report.source.name} "
            f"({report.n_failed} failed) — {self._table_panel.row_count} total",
            8000,
        )
        if report.errors:
            self._show_error_summary(report)
        self._finish_current_load()

    def _on_load_error(self, message: str) -> None:
        """Report a whole-file failure (unreadable/unsupported file)."""
        QMessageBox.warning(self, "Could not load file", message)
        self.statusBar().showMessage("Load failed", 5000)
        self._finish_current_load()

    def _show_error_summary(self, report: LoadReport) -> None:
        """Show a dialog summarizing per-record failures, details on demand."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Loaded with errors")
        box.setText(
            f"{report.n_failed} record(s) in {report.source.name} could not be read.\n"
            f"{report.n_loaded} molecule(s) loaded successfully."
        )
        shown = report.errors[:_MAX_ERRORS_SHOWN]
        details = "\n".join(str(err) for err in shown)
        if report.n_failed > _MAX_ERRORS_SHOWN:
            details += f"\n… and {report.n_failed - _MAX_ERRORS_SHOWN} more (see log file)"
        box.setDetailedText(details)
        box.exec()

    def _on_standardize(self) -> None:
        """Configure and launch the standardization pipeline on the dataset."""
        if self._table_panel.row_count == 0:
            self.statusBar().showMessage("Load molecules before standardizing", 4000)
            return
        options = StandardizeDialog.get_options(self)
        if options is None:
            return  # cancelled

        records = list(self._table_panel.model.records)  # snapshot for the worker
        self.action_open.setEnabled(False)
        self.action_standardize.setEnabled(False)
        self._progress.setRange(0, len(records))
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self.statusBar().showMessage(f"Standardizing {len(records)} molecule(s)…")

        worker = FunctionWorker(standardize_records, records, options, inject_progress=True)
        worker.signals.progress.connect(self._on_load_progress)
        worker.signals.finished.connect(self._on_standardize_finished)
        worker.signals.error.connect(self._on_standardize_error)
        self._std_worker = worker
        QThreadPool.globalInstance().start(worker)
        logger.info("Started standardization of %d record(s)", len(records))

    def _on_standardize_finished(self, report: StandardizationReport) -> None:
        """Adopt the standardized dataset and present the change report."""
        self._table_panel.set_records(report.records)
        self._structure_panel.set_record(None)
        self._sources_list.addItem(
            f"Standardized  —  {report.n_changed} changed, "
            f"{report.duplicates_removed} duplicate(s) removed"
        )
        self.statusBar().showMessage(
            f"Standardized: {report.n_records} molecule(s), {report.n_changed} changed, "
            f"{report.duplicates_removed} duplicate(s) removed, "
            f"{len(report.failures)} failure(s)",
            10000,
        )
        self._show_standardize_summary(report)
        self._finish_standardize()

    def _on_standardize_error(self, message: str) -> None:
        """Report a whole-pipeline failure (should be rare; per-record errors are handled)."""
        QMessageBox.warning(self, "Standardization failed", message)
        self._finish_standardize()

    def _finish_standardize(self) -> None:
        """Reset UI state after standardization and resume any queued loads."""
        self._std_worker = None
        self._progress.setVisible(False)
        self.action_open.setEnabled(True)
        self.action_standardize.setEnabled(True)
        self._start_next_load()

    def _show_standardize_summary(self, report: StandardizationReport) -> None:
        """Show counts up front, full per-molecule provenance behind Details."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("Standardization complete")
        box.setText(
            f"{report.n_records} molecule(s) in the dataset.\n"
            f"{report.n_changed} modified · {report.duplicates_removed} duplicate(s) removed · "
            f"{len(report.failures)} failure(s)."
        )
        details: list[str] = [str(change) for change in report.changed[:_MAX_ERRORS_SHOWN]]
        if report.failures:
            details.append("")
            details.append("Failures:")
            details.extend(report.failures[:_MAX_ERRORS_SHOWN])
        if details:
            box.setDetailedText("\n".join(details))
        box.exec()

    def _on_toggle_theme(self) -> None:
        """Switch themes and report the result in the status bar."""
        new_theme = self._theme_manager.toggle()
        self.statusBar().showMessage(f"Theme: {new_theme}", 3000)

    def _on_theme_changed(self, theme: str) -> None:
        """Re-render all molecule depictions with the palette matching ``theme``."""
        dark = theme == "dark"
        self._table_panel.set_dark(dark)
        self._structure_panel.set_dark(dark)

    def _on_about(self) -> None:
        """Display the About dialog."""
        QMessageBox.about(
            self,
            f"About {constants.APP_NAME}",
            f"<h3>{constants.APP_NAME} {constants.APP_VERSION}</h3>"
            f"<p>{constants.APP_DESCRIPTION}</p>"
            f"<p>License: {constants.LICENSE}</p>"
            f'<p><a href="{constants.PROJECT_URL}">{constants.PROJECT_URL}</a></p>',
        )
