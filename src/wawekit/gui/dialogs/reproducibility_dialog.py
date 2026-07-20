"""Dialog to configure a standardization-reproducibility audit.

A research feature: pick which protocols to compare (the three presets from R1
by default) and whether to run ablation-based cause attribution (slower, but the
part that turns "these disagree" into "these disagree because of tautomer
canonicalization").
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from wawekit.services.reproducibility import (
    PRESET_AGGRESSIVE,
    PRESET_CHEMBL_LIKE,
    PRESET_MINIMAL,
    StandardizationProtocol,
)


class ReproducibilityDialog(QDialog):
    """Choose protocols and whether to attribute divergence causes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Standardization Reproducibility Audit")
        self.setModal(True)

        intro = QLabel(
            "Compare standardization protocols across the dataset: do they agree\n"
            "on each molecule's standard structure? Research feature (see the\n"
            "learning/research-track-R1 notes for the methodology).",
            self,
        )

        self._minimal = QCheckBox(PRESET_MINIMAL.label, self)
        self._minimal.setChecked(True)
        self._chembl = QCheckBox(PRESET_CHEMBL_LIKE.label, self)
        self._chembl.setChecked(True)
        self._aggressive = QCheckBox(PRESET_AGGRESSIVE.label, self)
        self._aggressive.setChecked(True)

        self._causes = QCheckBox("Attribute divergence causes (ablation — slower)", self)
        self._causes.setChecked(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Run Audit")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        self._buttons = buttons

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(QLabel("Protocols to compare:", self))
        layout.addWidget(self._minimal)
        layout.addWidget(self._chembl)
        layout.addWidget(self._aggressive)
        layout.addWidget(self._causes)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        """Require at least two protocols — one protocol cannot diverge from itself."""
        if len(self._selected_protocols()) >= 2:
            self.accept()

    def _selected_protocols(self) -> tuple[StandardizationProtocol, ...]:
        chosen = []
        if self._minimal.isChecked():
            chosen.append(PRESET_MINIMAL)
        if self._chembl.isChecked():
            chosen.append(PRESET_CHEMBL_LIKE)
        if self._aggressive.isChecked():
            chosen.append(PRESET_AGGRESSIVE)
        return tuple(chosen)

    def result_options(self) -> tuple[tuple[StandardizationProtocol, ...], bool]:
        """Return ``(protocols, attribute_causes)`` from the current controls."""
        return self._selected_protocols(), self._causes.isChecked()

    @staticmethod
    def get_options(
        parent: QWidget | None = None,
    ) -> tuple[tuple[StandardizationProtocol, ...], bool] | None:
        """Show the dialog modally; return options, or ``None`` if cancelled."""
        dialog = ReproducibilityDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.result_options()
        return None
