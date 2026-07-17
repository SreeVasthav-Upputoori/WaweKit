# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Module 4 — Molecular standardization.**
  - Configurable pipeline service (`standardize_records`) on RDKit
    `rdMolStandardize`: Cleanup, salt stripping (largest fragment), charge
    neutralization, canonical tautomer, and duplicate removal by standardized
    canonical SMILES. Immutable-in/new-out; per-record failure resilience;
    full `StandardizationReport` provenance (what changed, dups, failures).
  - `StandardizeDialog` (checkbox pipeline picker, static `get_options` factory).
  - Chemistry menu + toolbar action; runs on the shared `FunctionWorker` with
    progress; results replace the dataset with a change-summary dialog.
- **Polish rider.**
  - Hand-authored SVG icon set (`resources/icons/`) + `icons.get_icon` loader
    (importlib.resources, multi-size, cached); app/window icon; toolbar icons.
  - Right-click context menu on the molecule table (Copy SMILES, Copy Names,
    Remove Selected); `set_records`/`remove_rows` on the model.
  - Capped SMILES column width so Formula/Heavy atoms/Source stay visible.
- **Module 3 — Molecule viewer.**
  - Qt-free SVG renderer service (`render_svg`) with dark-mode palette,
    transparent background, and on-the-fly 2D coordinate generation.
  - Structure thumbnails inside the molecule table via a custom
    `QStyledItemDelegate` with HiDPI pixmap caching (renders visible cells only).
  - Structure dock panel: large scalable depiction, identity (name, formula,
    canonical SMILES), SDF properties table, Copy SMILES, Save Image (SVG/PNG).
  - Selection wiring (`selection_changed` signal) and theme-reactive rendering
    (`ThemeManager` is now a `QObject` emitting `theme_changed`).
  - View menu now uses `QDockWidget.toggleViewAction()` for both docks.

### Fixed
- Molecule table displayed rows in reverse load order: enabling sorting applied
  Qt's default descending sort indicator; the view now starts with an explicit
  ascending sort on the row-number column.
- Structure thumbnails bled into adjacent table cells: the delegate centered
  using the pixmap's *physical* pixel rect (2× oversampled) instead of its
  device-independent size; painting is now also clipped to the cell rect.
  Found by screenshot-driven visual inspection.
- **Module 2 — Molecule loading.**
  - `MoleculeRecord` domain model (RDKit `Mol` + name, provenance, SDF
    properties; cached canonical SMILES and formula).
  - Robust loader service for SDF, MOL and SMILES files with per-record error
    capture (`LoadReport`/`LoadError`) and progress callbacks; UI-free.
  - Reusable background-worker infrastructure (`FunctionWorker` on
    `QThreadPool`, signal-based results/progress).
  - Sortable molecule table (Qt Model/View: `QAbstractTableModel` +
    `QSortFilterProxyModel` + `QTableView`) as the central workspace.
  - File → Open dialog, window-wide drag-and-drop, sequential load queue,
    status-bar progress bar, error summary dialog, loaded-files list in the
    Workspace dock.
  - Table/list styling for both themes; loader and table test suites
    (18 tests total, all passing).
- **Module 1 — Project architecture.**
  - `src`-layout package `wawekit` with layered structure
    (`core`, `models`, `services`, `gui`, `plugins`, `resources`).
  - Core infrastructure: constants, cross-platform paths (`QStandardPaths`),
    typed `AppConfig` with layered TOML loading, and rotating-file logging.
  - Themed desktop shell: `MainWindow` with menu bar, toolbar, status bar and a
    dockable workspace panel; runtime dark/light theme switching via QSS.
  - Composition root (`app.run`) and `python -m wawekit` entry point.
  - Packaging (`pyproject.toml`, hatchling), console script `wawekit`.
  - Tooling config for black, ruff, pytest.
  - Smoke test suite (`pytest` + `pytest-qt`, offscreen).
  - Open-source docs: README, CONTRIBUTING, CODE_OF_CONDUCT, MIT LICENSE.
  - Learning artifacts: graphical abstract + notes under `learning/`.
