# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Research flagship R1 — Standardization protocol engine.**
  - `services/reproducibility/protocol.py`: `StandardOp` (8 toggleable operations),
    `StandardizationProtocol` (a named operation set applied in a fixed order,
    with `with_op` ablation), presets (`Minimal`/`ChEMBL-like`/`Aggressive`), and
    the engine — `apply_protocol`, `standard_identity` (InChIKey), `standardize`
    → `StandardForm` (carries both canonical SMILES and InChIKey).
  - First finding: the canonical-tautomer operation changes the SMILES form but
    **not** the InChIKey (InChI normalizes tautomers), so SMILES- and
    InChIKey-identity disagree on which molecules are pipeline-dependent — the
    divergence study measures both. (12 tests; a demo script + captured output.)
- **Module 15 — Settings.**
  - `core/config.save_config` — a dependency-free TOML writer (the config is a
    flat table; `bool` serialized before `int` so `True` → `true`, not `1`).
  - `SettingsDialog` — a pure editor (config in, config out) for theme, log level
    and the remember-layout toggle, with Restore Defaults; changes apply live and
    persist to `<config_dir>/settings.toml`.
  - Window geometry + dock layout persisted via `QSettings`
    (`saveGeometry`/`saveState` on close, restored on start when enabled); theme
    captured on close so `Ctrl+T` survives a restart without per-toggle writes.
  - File → Settings (Ctrl+,); settings icon.
- **Module 14 — Report generation.**
  - `services/reporting/`: `build_summary` (format-independent stats, honest
    about partial analysis) + `generate_report` dispatching to two writers that
    share the same summary, so HTML and PDF never disagree.
  - `html_writer` — self-contained HTML with **inline SVG** depictions, a
    descriptor Min/Mean/Max table, a molecule grid, and print CSS.
  - `pdf_writer` — paginated A4 PDF via ReportLab; depictions rasterized by the
    new **`render_png`** (RDKit Cairo, Qt-free) so the whole report runs in the
    worker. `render_svg`/`render_png` now share a private `_draw` helper.
  - `ReportDialog` (title, HTML/PDF checkboxes, depiction toggle, molecule cap,
    base output path); an **Open** button on completion; File menu + toolbar.
  - Promoted `reportlab` from the `science` extra to a core dependency.
- **Module 13 — Batch processing.**
  - `services/batch.py`: `BatchConfig` (a serialisable recipe of frozen options),
    `run_batch` chaining standardize → descriptors → fingerprints → scaffolds →
    cluster → export in fixed order, and `BatchResult` with per-step summaries.
  - **Cancellation**: a `threading.Event` checked between steps and within them
    (via a wrapped progress callback); `BatchCancelled` derives from
    `BaseException` so the services' `except Exception` handlers cannot swallow it.
  - `services/io/molecule_exporter.py`: `export_csv` (identity + descriptors +
    annotations, blanks for uncomputed) and `export_sdf` (computed values as SD
    tags, set on a copy — `record.mol` never mutated). Reused by Module 14.
  - `BatchDialog` (step checklist + shared fingerprint encoding + export target);
    a non-modal Cancel button in the status bar; `_reset_derived_views()`
    extracted from the standardize handler and shared. Chemistry menu + toolbar.
- **Module 12 — Substructure search.**
  - `models/substructure.py`: `SubstructureQuery` and `SubstructureHit` (carries
    its query + matched atom indices — query-relative, like a similarity score).
  - `services/chemistry/substructure.py`: `parse_query` (SMARTS/SMILES, mutes
    stderr, returns `None`) and `search_substructure` → `SubstructureReport`.
  - **`render_svg` gained `highlight_atoms`** (the first renderer extension):
    highlights the matched atoms *and* the bonds between them, in both the table
    thumbnails (match folded into the delegate cache key) and the Structure panel.
  - Sortable "Substructure" column (`✓ N` / `—` / blank) and a fourth AND-ed
    filter channel (`SubstructureFilter`, "show only matches"); the proxy's
    `filterAcceptsRow` refactored to iterate its active channels.
  - `SubstructureDialog` with live SMARTS/SMILES validation; Chemistry menu +
    toolbar action + substructure icon.
- **Module 11 — Clustering.**
  - `models/clustering.py`: `ClusterMethod` (Butina/K-Means), `ClusterRun`, and
    `ClusterAssignment` (carries its run — a cluster id is dataset-relative, like
    a similarity score).
  - `services/chemistry/clustering.py`: `ClusterOptions` and `cluster_molecules`
    → `ClusterReport`. Butina (RDKit `ML.Cluster`, Tanimoto distance, cutoff) and
    K-Means (scikit-learn, lazy import); clusters numbered largest-first; ensures
    fingerprints first; assignments cached in place, stale ones cleared.
  - Sortable "Cluster" table column (with provenance tooltip) + a categorical
    "colour by Cluster" mode in the chemical-space scatter (tab20, no colourbar),
    auto-selected after a run so families light up on the map.
  - `ClusteringDialog` (method + reused `FingerprintOptionsWidget` — 4th consumer
    + Butina cutoff / K-Means K); Chemistry menu + toolbar action + cluster icon.
- **Module 10 — Chemical space visualization.**
  - `services/chemistry/chemical_space.py`: `ProjectionMethod` (PCA/t-SNE),
    `SpaceOptions`, `ProjectionPoint`/`ProjectionResult`, and `project` — ensures
    fingerprints, builds the bit matrix, reduces to 2D with scikit-learn (imported
    lazily). A projection is dataset-relative, so it is never cached on records.
  - Interactive Matplotlib scatter (`ChemicalSpacePanel`, bottom dock) with the
    navigation toolbar (pan/zoom/export), colour-by any descriptor or similarity
    (missing values grey), hover tooltips, and click/lasso selection.
  - Two-way link: plot selection → `MoleculeTablePanel.select_records`; table
    selection → `highlight_records` (rings points in place, no feedback loop).
  - `ChemicalSpaceDialog` (method + reused `FingerprintOptionsWidget` + t-SNE
    perplexity); Chemistry menu + toolbar action + `chemspace` icon.
  - Promoted `matplotlib` and `scikit-learn` from the `science` extra to core
    dependencies (Modules 10 and 11 make them load-bearing).
- **Module 9 — Conformer generation** (first 3D feature).
  - `models/conformers.py`: `ForceField` (MMFF94/UFF/None), `ConformerOptions`,
    `Conformer`, and `ConformerSet` — the 3D geometry lives on
    `ConformerSet.mol_3d` (a separate H-added molecule), never on `record.mol`.
  - `services/chemistry/conformers.py`: `generate_conformers` → `ConformerReport`
    via RDKit ETKDGv3 embedding + MMFF94/UFF optimisation (auto UFF fallback when
    MMFF params are missing) + energy ranking + RMSD-to-lowest; seeded for
    reproducibility; cache-in-place.
  - Interactive 3D viewer: `ConformerView` embeds vendored **3Dmol.js** (BSD-3,
    offline, inlined) in a `QWebEngineView`; `ConformerPanel` follows the table
    selection and shows the energy/ΔE/RMSD table with **SDF export**.
  - `ConformerDialog` (n_confs, force field, prune RMSD, seed); Chemistry menu +
    toolbar action. Generation runs on the selection when there is one, else the
    whole dataset (it is far heavier than the 2D operations).
  - Vendored `resources/web/3Dmol-min.js` + attribution `NOTICE-3Dmol.txt`.
- **Module 8 — Scaffold analysis.**
  - `models/scaffold.py`: `ScaffoldResult` (exact Murcko + generic-framework
    SMILES + `has_ring_system`) and `ScaffoldRepresentation` (Murcko/Generic).
    Acyclic molecules are represented honestly as an empty scaffold, not a crash.
  - `services/chemistry/scaffolds.py`: `compute_scaffolds` (cache-in-place, the
    descriptors pattern) → `ScaffoldReport`; `group_scaffolds` → `ScaffoldGroup`
    list ranked by member count (scaffold diversity).
  - Scaffolds dock panel: diversity headline, exact/generic toggle, ranked
    scaffold list with rendered thumbnails, and click-to-filter. Emits intent
    only (no worker/RDKit in the widget).
  - Sortable "Scaffold" column in the table (sorting clusters shared scaffolds).
  - Scaffold filtering added as a second, AND-ed channel on the filter proxy
    (`ScaffoldFilter`) so a scaffold selection combines with the text query;
    Chemistry menu + toolbar action + scaffold icon.
- **Module 7 — Similarity search.**
  - `models/similarity.py`: `SimilarityMetric` (Tanimoto/Dice/Cosine),
    `SimilarityQuery` (query identified by canonical SMILES, its metric and
    fingerprint options), and `SimilarityScore` (a value that carries its query
    — a similarity is relational, not an intrinsic molecule property).
  - `services/chemistry/similarity.py`: `search_similar` → `SimilarityReport`
    (ranked scores, skipped molecules, fingerprints computed as a side effect).
  - `SimilarityDialog` with live SMILES validation; right-click "Find Similar to
    This"; results land in a sortable "Similarity" column (query row bold), no
    threshold field — the quick-filter narrows scores after the fact (`Sim >= 0.7`).
  - `parse_smiles` loader helper (returns `None`, mutes RDKit stderr) so the
    dialog never imports RDKit. Fixed a latent dark-theme bug: checked
    `QRadioButton` rendered no indicator.
- **Module 6 — Fingerprints.**
  - `models/fingerprints.py`: `FingerprintKind` (Morgan/MACCS/RDKit),
    `FingerprintOptions` (with `normalized()` so identity = effective config),
    `Fingerprint` (carries the options that built it — different params are not
    comparable, so a re-run replaces rather than mixes).
  - `services/chemistry/fingerprints.py` on `rdFingerprintGenerator` (not the
    deprecated legacy API); `FingerprintReport`.
  - `FingerprintDialog` + extracted `FingerprintOptionsWidget`; "Fingerprint"
    column showing algorithm and set-bit count. Fixed a Qt-boundary bug: a
    `StrEnum` in combo item-data round-trips as a plain `str` (use `==`, not `is`).
- **Module 5 — Descriptors.**
  - `models/descriptors.py`: frozen `DescriptorSet` (MW, LogP, TPSA, HBD/HBA,
    RotB, rings + Lipinski verdict) and `DESCRIPTOR_SPECS` — the single source of
    truth driving headers, cell formatting, sort keys, tooltips and filter tokens.
  - `services/chemistry/descriptors.py`: `compute_descriptors` → `DescriptorReport`;
    values cached on records in place (a descriptor is a cache, not a new molecule),
    with an in-place column repaint that preserves scroll and selection.
  - Quick-filter box: custom `MoleculeFilterProxyModel` with a tiny query language
    (`aspirin`, `MW < 500`, `Sim >= 0.7`) that compares typed values, not text;
    unparseable queries are reported, never silently ignored.
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
