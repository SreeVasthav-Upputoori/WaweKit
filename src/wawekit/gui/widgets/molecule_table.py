"""Molecule table using Qt's Model/View architecture.

Qt separates *data* from *presentation*:

* :class:`MoleculeTableModel` (a :class:`QAbstractTableModel`) adapts our list
  of :class:`~wawekit.models.molecule.MoleculeRecord` objects into rows/columns.
  It stores no widgets and paints nothing.
* :class:`~PySide6.QtWidgets.QTableView` paints whatever model it is given.
* :class:`~PySide6.QtWidgets.QSortFilterProxyModel` sits between them and
  re-orders rows for sorting (and, in later modules, filtering) without ever
  touching the underlying data.
* Since Module 3, a :class:`~wawekit.gui.widgets.structure_delegate.StructureDelegate`
  paints 2D depictions inside the *Structure* column, and the panel emits
  :attr:`MoleculeTablePanel.selection_changed` with the selected record so other
  panels (the structure viewer) can follow the selection.

This separation is why the same model can later feed a structure-grid view, a
plot, or an export — and it is how large tools (DataWarrior, KNIME) stay fast
with hundreds of thousands of rows: the view only asks for visible cells.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QMenu,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from wawekit.gui.widgets.structure_delegate import (
    RECORD_ROLE,
    THUMB_HEIGHT,
    THUMB_WIDTH,
    StructureDelegate,
)
from wawekit.models.molecule import MoleculeRecord

logger = logging.getLogger(__name__)

#: Column order for the table. Kept as data so adding a column is a small diff.
_HEADERS: tuple[str, ...] = ("#", "Structure", "Name", "SMILES", "Formula", "Heavy atoms", "Source")

#: Index of the column painted by the structure delegate.
STRUCTURE_COLUMN = 1

#: Cap for the SMILES column so long strings don't push other columns offscreen.
_SMILES_COLUMN = 3
_SMILES_MAX_WIDTH = 260


class MoleculeTableModel(QAbstractTableModel):
    """Adapts a list of :class:`MoleculeRecord` into a Qt table model.

    The model answers the view's questions: how many rows/columns, what to
    display in each cell (``DisplayRole``), what raw value to sort by
    (``UserRole`` — so 100 sorts after 20, not before it), and which record
    backs a cell (``RECORD_ROLE`` — consumed by the structure delegate).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._records: list[MoleculeRecord] = []

    # ------------------------------------------------------------ Qt overrides
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802,B008
        """Return the number of molecule rows (0 under a valid parent: flat table)."""
        return 0 if parent.isValid() else len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802,B008
        """Return the fixed column count from the header definition."""
        return 0 if parent.isValid() else len(_HEADERS)

    def headerData(  # noqa: N802
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        """Column titles across the top; default numbering on the side."""
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return _HEADERS[section]
        return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return display text, raw sort key, or the backing record, per role."""
        if not index.isValid():
            return None
        record = self._records[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_value(record, index.row(), column)
        if role == Qt.ItemDataRole.UserRole:
            return self._sort_value(record, index.row(), column)
        if role == RECORD_ROLE:
            return record
        return None

    # ------------------------------------------------------------- public API
    def append_records(self, records: list[MoleculeRecord]) -> None:
        """Add ``records`` to the end of the table, notifying attached views.

        ``beginInsertRows``/``endInsertRows`` is Qt's transactional protocol:
        views update incrementally instead of rebuilding everything.
        """
        if not records:
            return
        first = len(self._records)
        last = first + len(records) - 1
        self.beginInsertRows(QModelIndex(), first, last)
        self._records.extend(records)
        self.endInsertRows()
        logger.debug("Appended %d record(s); table now has %d", len(records), last + 1)

    def clear(self) -> None:
        """Remove every record, notifying attached views."""
        self.beginResetModel()
        self._records.clear()
        self.endResetModel()

    def set_records(self, records: list[MoleculeRecord]) -> None:
        """Replace the whole dataset (used after standardization)."""
        self.beginResetModel()
        self._records = list(records)
        self.endResetModel()
        logger.debug("Replaced dataset; table now has %d record(s)", len(records))

    def remove_rows(self, rows: list[int]) -> None:
        """Remove the given source-model ``rows``.

        Deleting from the highest row down keeps the remaining indices valid;
        each removal is announced transactionally so views update in place.
        """
        for row in sorted(set(rows), reverse=True):
            if 0 <= row < len(self._records):
                self.beginRemoveRows(QModelIndex(), row, row)
                del self._records[row]
                self.endRemoveRows()

    def record_at(self, row: int) -> MoleculeRecord:
        """Return the record backing ``row`` (source-model coordinates)."""
        return self._records[row]

    @property
    def records(self) -> list[MoleculeRecord]:
        """The records currently in the model (do not mutate directly)."""
        return self._records

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _display_value(record: MoleculeRecord, row: int, column: int) -> str | None:
        """Return human-readable text for one cell."""
        match column:
            case 0:
                return str(row + 1)
            case 1:
                return None  # painted by the structure delegate
            case 2:
                return record.name
            case 3:
                return record.smiles
            case 4:
                return record.formula
            case 5:
                return str(record.num_heavy_atoms)
            case _:
                return record.source_name

    @staticmethod
    def _sort_value(record: MoleculeRecord, row: int, column: int) -> Any:
        """Return the raw sort key (ints stay ints; text sorts case-insensitively)."""
        match column:
            case 0 | 1:
                return row  # structure column: keep load order (no natural sort)
            case 2:
                return record.name.lower()
            case 3:
                return record.smiles
            case 4:
                return record.formula
            case 5:
                return record.num_heavy_atoms
            case _:
                return record.source_name.lower()


class MoleculeTablePanel(QWidget):
    """Self-contained widget: table view + sort proxy + model + delegate.

    Bundling the Model/View pieces behind one small API keeps
    :class:`~wawekit.gui.main_window.MainWindow` simple and makes the panel
    reusable (and testable) on its own.
    """

    #: Emitted with the newly selected MoleculeRecord, or None when cleared.
    selection_changed = Signal(object)

    def __init__(self, dark: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.model = MoleculeTableModel(self)

        # Proxy: sorts by the raw UserRole values our model provides.
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self.model)
        self._proxy.setSortRole(Qt.ItemDataRole.UserRole)

        self._view = QTableView(self)
        self._view.setModel(self._proxy)
        self._view.setSortingEnabled(True)
        # Qt gotcha: enabling sorting applies the header's *default* indicator,
        # which is column 0 DESCENDING — files would display in reverse load
        # order. Establish an explicit ascending initial sort instead.
        self._view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self._view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._view.setAlternatingRowColors(True)
        self._view.verticalHeader().setVisible(False)
        self._view.horizontalHeader().setStretchLastSection(True)

        # Structure thumbnails: custom delegate + row height to fit them.
        self._delegate = StructureDelegate(self._view, dark=dark)
        self._view.setItemDelegateForColumn(STRUCTURE_COLUMN, self._delegate)
        self._view.verticalHeader().setDefaultSectionSize(THUMB_HEIGHT + 8)

        # Selection → domain object translation for the rest of the app.
        self._view.selectionModel().currentRowChanged.connect(self._on_current_row_changed)

        # Right-click context menu (copy/remove), the desktop-app staple.
        self._view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._view.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

    # ------------------------------------------------------------- public API
    def append_records(self, records: list[MoleculeRecord]) -> None:
        """Append records and keep column widths readable."""
        self.model.append_records(records)
        self._fix_column_widths()

    def set_records(self, records: list[MoleculeRecord]) -> None:
        """Replace the entire dataset (e.g. after standardization)."""
        self.model.set_records(records)
        self._fix_column_widths()
        self.selection_changed.emit(None)  # old selection no longer exists

    def _fix_column_widths(self) -> None:
        """Auto-size columns, then pin the structure and cap the SMILES column."""
        self._view.resizeColumnsToContents()
        self._view.setColumnWidth(STRUCTURE_COLUMN, THUMB_WIDTH + 8)
        if self._view.columnWidth(_SMILES_COLUMN) > _SMILES_MAX_WIDTH:
            self._view.setColumnWidth(_SMILES_COLUMN, _SMILES_MAX_WIDTH)

    def selected_records(self) -> list[MoleculeRecord]:
        """Return the records behind the currently selected rows (in view order).

        Selection lives in *proxy* coordinates (what the user sees, possibly
        sorted); ``mapToSource`` translates back to our data's row numbers.
        """
        rows = self._view.selectionModel().selectedRows()
        return [self.model.record_at(self._proxy.mapToSource(ix).row()) for ix in rows]

    def set_dark(self, dark: bool) -> None:
        """Propagate a theme change to the thumbnail delegate and repaint."""
        self._delegate.set_dark(dark)
        self._view.viewport().update()

    @property
    def row_count(self) -> int:
        """Number of molecules currently shown."""
        return self.model.rowCount()

    # --------------------------------------------------------------- handlers
    def _on_current_row_changed(self, current: QModelIndex, _previous: QModelIndex) -> None:
        """Translate the Qt selection into a MoleculeRecord and broadcast it."""
        record: MoleculeRecord | None = None
        if current.isValid():
            record = self.model.record_at(self._proxy.mapToSource(current).row())
        self.selection_changed.emit(record)

    def _selected_source_rows(self) -> list[int]:
        """Return selected rows in source-model coordinates."""
        return [
            self._proxy.mapToSource(ix).row() for ix in self._view.selectionModel().selectedRows()
        ]

    def _show_context_menu(self, pos) -> None:  # noqa: ANN001 — QPoint
        """Build and show the right-click menu for the current selection."""
        selected = self.selected_records()
        if not selected:
            return
        menu = QMenu(self)

        copy_smiles = QAction(f"Copy SMILES ({len(selected)})", menu)
        copy_smiles.triggered.connect(
            lambda: QApplication.clipboard().setText("\n".join(r.smiles for r in selected))
        )
        menu.addAction(copy_smiles)

        copy_names = QAction(f"Copy Name(s) ({len(selected)})", menu)
        copy_names.triggered.connect(
            lambda: QApplication.clipboard().setText("\n".join(r.name for r in selected))
        )
        menu.addAction(copy_names)

        menu.addSeparator()
        remove = QAction(f"Remove Selected ({len(selected)})", menu)
        remove.triggered.connect(self._remove_selected)
        menu.addAction(remove)

        menu.exec(self._view.viewport().mapToGlobal(pos))

    def _remove_selected(self) -> None:
        """Delete the selected rows and clear the downstream selection."""
        rows = self._selected_source_rows()
        if rows:
            self.model.remove_rows(rows)
            self.selection_changed.emit(None)
            logger.info("Removed %d row(s) from the molecule table", len(rows))
