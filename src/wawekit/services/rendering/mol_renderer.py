"""2D molecule depiction as SVG.

RDKit's modern drawing engine (:mod:`rdkit.Chem.Draw.rdMolDraw2D`) renders a
molecule into an SVG *string* — no Qt involved. Keeping this in ``services``
means the identical depiction code will later feed PDF reports and docs, and it
is fully testable headlessly.

RDKit concepts
--------------
* **2D coordinates** — molecules parsed from SMILES have *no* atom positions;
  :func:`rdkit.Chem.rdDepictor.Compute2DCoords` generates a layout. Molecules
  from SDF/MOL files usually already carry 2D coordinates, which we keep.
* :func:`rdMolDraw2D.PrepareAndDrawMolecule` — handles kekulization, wedge
  bonds and highlighting the way the RDKit authors recommend.
* :func:`rdMolDraw2D.SetDarkMode` — switches the atom palette for dark
  backgrounds (black carbon lines are invisible on a dark theme).
* ``clearBackground = False`` — we draw on a *transparent* background so the
  depiction blends into whatever surface displays it.
"""

from __future__ import annotations

import logging

from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D

logger = logging.getLogger(__name__)


def render_svg(
    mol: Chem.Mol,
    width: int = 350,
    height: int = 280,
    dark: bool = False,
    legend: str = "",
) -> str:
    """Render ``mol`` as an SVG string of ``width`` × ``height`` pixels.

    The input molecule is never mutated: we draw a copy, generating 2D
    coordinates on it only if none exist (records are shared across the app,
    so mutating them here would be a hidden side effect).

    Parameters
    ----------
    mol:
        The molecule to depict.
    width, height:
        Logical canvas size in pixels (SVG scales losslessly afterwards).
    dark:
        Use RDKit's dark-mode palette (light bonds/atoms for dark backgrounds).
    legend:
        Optional caption drawn under the structure.

    Returns
    -------
    str
        The SVG document as text.

    """
    work = Chem.Mol(mol)  # cheap copy; protects the shared record
    if work.GetNumConformers() == 0:
        rdDepictor.Compute2DCoords(work)

    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    options = drawer.drawOptions()
    if dark:
        rdMolDraw2D.SetDarkMode(options)
    options.clearBackground = False  # transparent: blends with any theme

    rdMolDraw2D.PrepareAndDrawMolecule(drawer, work, legend=legend)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()
