# Module 3 — Molecule Viewer · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`.

---

## 1. What we built

Two ways of *seeing* molecules, fed by one renderer:

1. **Thumbnails in the table** — a custom delegate paints a 2D depiction in
   every row's *Structure* column.
2. **Structure dock panel** — select a row → large scalable depiction, name,
   formula, canonical SMILES, SDF properties, *Copy SMILES*, *Save Image…*
   (SVG or high-resolution PNG).

Both re-render automatically when the theme flips (dark bonds palette ↔ light).

## 2. The big ideas

### One renderer, many consumers (why `render_svg` lives in `services`)

`rdMolDraw2D.MolDraw2DSVG` produces an SVG **string** — pure RDKit, no Qt.
Putting it in `services/rendering` means the *same* code draws table
thumbnails, the structure panel, and later the PDF reports of Module 14 and
documentation images. If we had written rendering inside a widget, we would be
rewriting it three times.

Renderer rules worth memorizing:

- **Draw a copy** (`Chem.Mol(mol)`): records are shared across the whole app;
  generating coordinates on the original would be a hidden mutation. There is a
  test asserting the input keeps zero conformers.
- **SMILES-born molecules have no coordinates** — check
  `GetNumConformers() == 0` and call `rdDepictor.Compute2DCoords`. SDF/MOL
  molecules already carry (usually 2D) coordinates, which we keep.
- **`SetDarkMode(options)`** — the default palette draws carbon skeletons in
  black; invisible on our dark theme.
- **`clearBackground = False`** — transparent background blends into any
  surface (table cell, dock, exported PNG).

### Delegates: custom painting inside Model/View

A `QStyledItemDelegate` is the object Qt asks to paint each cell. Ours:

- Pulls the `MoleculeRecord` through a **custom data role** (`RECORD_ROLE =
  UserRole + 1`). Roles are how models expose *domain objects* to visual
  components without the model knowing who consumes them.
- **Renders on demand** — Qt paints only visible cells, so a 100k-row file
  renders only what you scroll past.
- **Caches pixmaps** keyed by canonical SMILES; the cache clears on theme
  change and at a size bound. Rendered at 2× with `setDevicePixelRatio(2)` for
  crisp HiDPI display.
- Paints the selection highlight *first*, then the transparent structure over it.
- A depiction failure logs and paints nothing — painting must never throw.

### Signals as the app's nervous system

Two new signal patterns:

- `MoleculeTablePanel.selection_changed(MoleculeRecord | None)` — the panel
  translates Qt selection mechanics (proxy coordinates, `mapToSource`) into a
  domain object. `MainWindow` wiring is then one line:
  `table.selection_changed.connect(viewer.set_record)`.
- `ThemeManager` became a `QObject` emitting `theme_changed(str)` — the
  observer pattern. The window doesn't push theme updates into every widget;
  widgets that care subscribe. New theme-aware widgets cost zero changes in
  `MainWindow` beyond one connect.

Also: `QDockWidget.toggleViewAction()` replaced our hand-written dock toggle —
Qt provides a checkable, always-in-sync action for free. Deleting code you
don't need is engineering too.

## 3. A real bug, and what it teaches

`setSortingEnabled(True)` **immediately sorts** using the header's default
sort indicator — which is column 0 **descending**. Result: every file
displayed in reverse load order. The selection test failed with "expected
benzene, got ethanol" and led straight to it. Fix: explicit
`sortByColumn(0, AscendingOrder)` after enabling sorting.

Lessons:
- Test assertions should pin *which* object comes back, not just that one does.
- When a test fails, distinguish "test asserted the wrong observable" (the
  legend test — RDKit draws text as glyph *paths*, so we check for the legend
  element, not the literal string) from "the code is wrong" (the sort bug).
  We hit one of each in this module.

## 4. File-by-file rationale

| File | Why |
|---|---|
| `services/rendering/mol_renderer.py` | Qt-free SVG depiction; the single source of molecular imagery. |
| `gui/widgets/structure_delegate.py` | Thumbnail painting + caching; `RECORD_ROLE` definition. |
| `gui/widgets/structure_viewer.py` | The Structure panel; placeholder/SVG stacked pages; SVG/PNG export. |
| `gui/widgets/molecule_table.py` | New Structure column, record role, selection signal, ascending initial sort. |
| `gui/themes/theme_manager.py` | Now a QObject broadcasting `theme_changed`. |
| `gui/main_window.py` | Structure dock; three-line wiring: selection → viewer, theme → both. |

## 5. Tradeoffs accepted

- **Thumbnail column is fixed-size** and not sortable (sorting a picture is
  meaningless; its sort key is load order).
- **Cache eviction is clear-all at a bound**, not LRU — simpler, and a full
  re-render of visible cells is cheap. An LRU would be premature optimization.
- **No structure editing/sketching** — viewing only; a sketcher is a separate,
  large feature (possibly a plugin later).
- **PNG export at fixed 1200×950** — good for slides; configurable DPI belongs
  in Settings (Module 15).

## 6. Verification (actually run)

- `pytest`: **31/31 passing** — renderer (coords, no-mutation, dark≠light,
  legend, size), viewer panel (placeholder ↔ record, clipboard, theme
  re-render), table (new column, record role, selection signal).
- `ruff check .` clean; `black` clean.

## 7. Research lens

Depiction is solved science (RDKit's layout is excellent). But note for later:
our renderer + delegate architecture makes it trivial to add **atom/bond
highlighting** (the `render_svg` signature already anticipates it). When we
build substructure search (Module 12) and scaffold analysis (Module 8),
highlight-driven visual analytics — e.g., interactive matched-molecular-pair
or R-group heatmaps over the table — is where visualization novelty could
support a methods paper. The publishable core would be the analysis method;
the viewer is its delivery vehicle.
