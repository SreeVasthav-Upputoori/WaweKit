"""Tests for the molecule table model and panel (headless, offscreen Qt)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from rdkit import Chem

from wawekit.gui.widgets.molecule_table import MoleculeTableModel, MoleculeTablePanel
from wawekit.gui.widgets.structure_delegate import RECORD_ROLE
from wawekit.models.molecule import MoleculeRecord


def _records(*smiles_names: tuple[str, str]) -> list[MoleculeRecord]:
    return [
        MoleculeRecord(mol=Chem.MolFromSmiles(smiles), name=name) for smiles, name in smiles_names
    ]


def test_model_starts_empty(qtbot):
    model = MoleculeTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 7  # "#", Structure, Name, SMILES, Formula, Heavy atoms, Source


def test_model_append_and_display(qtbot):
    model = MoleculeTableModel()
    model.append_records(_records(("CCO", "ethanol"), ("c1ccccc1", "benzene")))

    assert model.rowCount() == 2
    assert model.data(model.index(0, 2)) == "ethanol"
    assert model.data(model.index(1, 4)) == "C6H6"
    assert model.data(model.index(0, 0)) == "1"  # 1-based row number
    assert model.data(model.index(0, 1)) is None  # structure column: delegate paints it
    # UserRole exposes raw values for numeric sorting.
    assert model.data(model.index(1, 5), Qt.ItemDataRole.UserRole) == 6


def test_model_exposes_record_through_custom_role(qtbot):
    model = MoleculeTableModel()
    records = _records(("CCO", "ethanol"))
    model.append_records(records)

    assert model.data(model.index(0, 1), RECORD_ROLE) is records[0]


def test_model_clear(qtbot):
    model = MoleculeTableModel()
    model.append_records(_records(("CCO", "ethanol")))
    model.clear()
    assert model.rowCount() == 0


def test_panel_appends_and_counts(qtbot):
    panel = MoleculeTablePanel()
    qtbot.addWidget(panel)

    panel.append_records(_records(("CCO", "ethanol"), ("CC(=O)O", "acetic acid")))
    assert panel.row_count == 2
    assert panel.model.record_at(0).name == "ethanol"


def test_panel_emits_selection_changed(qtbot):
    panel = MoleculeTablePanel()
    qtbot.addWidget(panel)
    panel.append_records(_records(("CCO", "ethanol"), ("c1ccccc1", "benzene")))

    # setCurrentIndex is deterministic (selectRow can emit an intermediate
    # current-index change first, which waitSignal would capture instead).
    with qtbot.waitSignal(panel.selection_changed, timeout=1000) as blocker:
        panel._view.setCurrentIndex(panel._proxy.index(1, 0))

    record = blocker.args[0]
    assert isinstance(record, MoleculeRecord)
    assert record.name == "benzene"
