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

> **Status:** early development. Modules 1–4 complete: the app loads SDF, MOL
> and SMILES files into a sortable, structure-thumbnail table with a Structure
> panel (SVG/PNG export), and standardizes datasets (salt stripping, charge
> neutralization, tautomer canonicalization, deduplication) on a background
> thread with a full change report. Toolbar icons, right-click context menu.

## Features (roadmap)

Modules are built one at a time to production quality:

1. ✅ Project architecture
2. ✅ Molecule loading (SDF/MOL/SMILES, drag-and-drop, background threads)
3. ✅ Molecule viewer (2D depictions in table + structure panel, SVG/PNG export)
4. ✅ Molecular standardization (salts, charges, tautomers, dedup + change report)
5. ⬜ Descriptors
6. ⬜ Fingerprints
7. ⬜ Similarity search
8. ⬜ Scaffold analysis
9. ⬜ Conformer generation
10. ⬜ Chemical space visualization
11. ⬜ Clustering
12. ⬜ Substructure search
13. ⬜ Batch processing
14. ⬜ Report generation
15. ⬜ Settings
16. ⬜ Plugin system
17. ⬜ Packaging
18. ⬜ Documentation
19. ⬜ Testing
20. ⬜ Release preparation

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

## License

[MIT](LICENSE) © The Wawekit Authors
