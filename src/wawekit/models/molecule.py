"""The molecule domain model.

:class:`MoleculeRecord` is Wawekit's central data object: an RDKit molecule
plus the identity and provenance information every feature needs (a display
name, which file it came from, its position in that file, and any properties
carried by the source record, e.g. SDF data fields).

Design notes
------------
* **No Qt here.** Models are pure Python + RDKit so they can be unit-tested and
  reused headlessly (CLI, notebooks, batch pipelines).
* **Lazy caching.** Canonical SMILES and molecular formula are computed on
  first access and cached, because GUI views request display values repeatedly
  (every repaint) and recomputing canonical SMILES is not free.
* **Not frozen.** Unlike :class:`~wawekit.core.config.AppConfig`, records cache
  derived values internally, so full immutability is impractical; treat them as
  read-only by convention after creation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rdkit import Chem
from rdkit.Chem import rdMolDescriptors


@dataclass(slots=True)
class MoleculeRecord:
    """One molecule with its identity, provenance and source properties.

    Attributes
    ----------
    mol:
        The sanitized RDKit molecule object.
    name:
        Human-readable name (SDF ``_Name`` field, SMILES name column, or a
        generated fallback like ``file_3``).
    source:
        Path of the file this molecule was read from (``None`` if created
        in-memory, e.g. by a future sketcher).
    index_in_source:
        1-based position of the record within its source file.
    properties:
        Data fields attached to the source record (e.g. SDF tags such as
        activity values). Values keep the types RDKit inferred.

    """

    mol: Chem.Mol
    name: str
    source: Path | None = None
    index_in_source: int = 0
    properties: dict[str, Any] = field(default_factory=dict)

    # Lazily-computed caches (excluded from __init__ and repr).
    _smiles: str | None = field(default=None, init=False, repr=False)
    _formula: str | None = field(default=None, init=False, repr=False)

    @property
    def smiles(self) -> str:
        """Canonical isomeric SMILES for this molecule (computed once)."""
        if self._smiles is None:
            self._smiles = Chem.MolToSmiles(self.mol)
        return self._smiles

    @property
    def formula(self) -> str:
        """Molecular formula, e.g. ``C9H8O4`` (computed once)."""
        if self._formula is None:
            self._formula = rdMolDescriptors.CalcMolFormula(self.mol)
        return self._formula

    @property
    def num_heavy_atoms(self) -> int:
        """Number of non-hydrogen atoms."""
        return self.mol.GetNumHeavyAtoms()

    @property
    def source_name(self) -> str:
        """Short display string for the source file (empty if in-memory)."""
        return self.source.name if self.source is not None else ""
