<h1 align="center">Wawekit</h1>

<p align="center">
  <b>Professional open-source desktop cheminformatics toolkit</b><br>
  Built with Python 3.12, RDKit and PySide6 &nbsp;•&nbsp; MIT licensed &nbsp;•&nbsp; Cross-platform
</p>

---

Wawekit is a native desktop application for cheminformatics and early drug
discovery — for academic researchers, computational chemists, pharmaceutical
scientists, and students learning the field. It aims to be one of the best free
RDKit desktop applications available.

> **Status:** early development. Modules 1–8 complete: the app loads SDF, MOL
> and SMILES files into a sortable, structure-thumbnail table with a Structure
> panel (SVG/PNG export); standardizes datasets (salts, charges, tautomers,
> dedup); computes descriptors (with a quick-filter box), fingerprints
> (Morgan/MACCS/RDKit) and Tanimoto similarity rankings; and analyzes
> Bemis–Murcko scaffolds with a diversity panel and click-to-filter grouping —
> all on background threads with progress and full reports.

## Features (roadmap)

Modules are built one at a time to production quality:

1. ✅ Project architecture
2. ✅ Molecule loading (SDF/MOL/SMILES, drag-and-drop, background threads)
3. ✅ Molecule viewer (2D depictions in table + structure panel, SVG/PNG export)
4. ✅ Molecular standardization (salts, charges, tautomers, dedup + change report)
5. ✅ Descriptors (MW, LogP, TPSA, HBD/HBA, RotB, rings, Lipinski + quick-filter)
6. ✅ Fingerprints (Morgan/MACCS/RDKit, options dialog)
7. ✅ Similarity search (Tanimoto ranking, query dialog, results filter)
8. ✅ Scaffold analysis (Bemis–Murcko, diversity grouping, click-to-filter)
9. ✅ Conformer generation (ETKDG + MMFF/UFF, interactive 3D viewer, SDF export)
10. ✅ Chemical space visualization (PCA/t-SNE scatter, colour-by, table-linked)
11. ✅ Clustering (Butina + K-Means, cluster column, colour the map by cluster)
12. ✅ Substructure search (SMARTS/SMILES, matched-atom highlighting, filter)
13. ✅ Batch processing (chained pipeline, CSV/SDF export, cancellable)
14. ✅ Report generation (shareable HTML + PDF, molecule grid, summary stats)
15. ✅ Settings (persist theme, log level, window/dock layout)
16. ⬜ Plugin system
17. ⬜ Packaging
18. ⬜ Documentation
19. ⬜ Testing
20. ⬜ Release preparation

## Research flagship

Beyond the feature roadmap, Wawekit is being developed toward a methods
publication: a **standardization-reproducibility auditor**. Structure
standardization is mandatory but under-specified — different protocols produce
different "standard" structures for the same molecule, so a molecule's identity
can silently depend on the pipeline. Wawekit quantifies this *divergence* as a
first-class diagnostic and (via operation ablation) attributes each disagreement
to a specific normalization operation.

Early result already surfaced by the protocol engine: **the choice of identity
key changes what "reproducible" means** — InChIKey masks tautomer divergence that
canonical SMILES reveals, so the two disagree on which molecules are
pipeline-dependent. See [`learning/research-track-R1-protocol-engine/`](learning/research-track-R1-protocol-engine/).

## Architecture

Strict layered design; dependencies point downward only:

```
gui  ->  services  ->  models  ->  core
```

| Layer | Responsibility | Imports Qt? |
|-------|----------------|-------------|
| `core` | config, logging, paths, constants | no |
| `models` | RDKit-backed domain objects | no |
| `services` | orchestration, background workers | no |
| `gui` | PySide6 windows and widgets | yes |

## Installation (development)

Requires Python 3.12+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
```

## Running

```bash
wawekit
# or, equivalently
python -m wawekit
```

## Development

```bash
pytest            # run the test suite
ruff check .      # lint
black .           # format
mkdocs serve      # preview docs
```

## Learning notes

Every completed module ships with a **graphical abstract** (self-contained HTML)
and **build notes** under [`learning/`](learning/). These document *how* and
*why* each feature was built — the project doubles as a software-engineering and
cheminformatics course.

## Acknowledgements

The interactive 3D conformer viewer is powered by
[3Dmol.js](https://3dmol.csb.pitt.edu/) (BSD-3-Clause), vendored and used
offline. See `src/wawekit/resources/web/NOTICE-3Dmol.txt` for attribution.

## License

[MIT](LICENSE) © Sree Vasthav Upputoori
