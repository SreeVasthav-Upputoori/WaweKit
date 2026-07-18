# Module 10 — Chemical Space Visualization · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`
> and the two scatter screenshots in this folder.

---

## 1. What we built

An **interactive 2D map of the dataset**. Each molecule's fingerprint lives in a
2048-dimensional space; we project it down to two dimensions you can look at, so
clusters, outliers and diversity become obvious. The plot is a real Matplotlib
figure with pan/zoom/**export**, colour-by-property, hover tooltips, and a
two-way link to the table: click or lasso points to select molecules, and the
table's selection rings the matching points. The screenshots show 20 molecules
projected by PCA (46% variance shown), coloured by LogP, with the three
steroid-like molecules ringed from a table selection.

## 2. The pipeline

1. **Ensure fingerprints** — reuse `compute_fingerprints` (Module 6) so every
   molecule is encoded the *same* way; molecules that can't be encoded are
   skipped (reported, not silently dropped).
2. **Build a matrix** — convert each `ExplicitBitVect` to a NumPy row
   (`ConvertToNumpyArray`) and stack into `(n_molecules, n_bits)`.
3. **Reduce to 2D** — **PCA** (linear, fast, deterministic; reports variance per
   axis) or **t-SNE** (non-linear, separates clusters, axes are unitless).

## 3. Design decisions

### A projection is relational, so it lives in the service (not on the record)

This is the same fork as similarity (Module 7), sharpened. Descriptors, scaffolds
and conformers are *intrinsic* — they cache on the record. A projection is not:
a point's `(x, y)` depends on the **whole dataset** and the method, and changes
completely if either does. So `ProjectionMethod`, `SpaceOptions`,
`ProjectionPoint` and `ProjectionResult` all live in the service module (nothing
in `models` refers to them), and the result is held by the GUI panel — never
cached on the record. That means there is no such thing as a stale coordinate to
invalidate; replacing the dataset just clears the plot.

### PCA *and* t-SNE, chosen for what they tell you

PCA is the honest default: fast, reproducible, and its axes carry meaning (the
title and axis labels report captured variance — "46% variance shown", "PC1
31%"). t-SNE is offered for when you specifically want tight clusters to
separate, with the understanding that its axes mean nothing global. The dialog
enables the perplexity control only for t-SNE, and the service clamps perplexity
to the dataset size so a small set can't crash sklearn.

### Lazy sklearn import

`scikit-learn` is imported **inside** `project()`, not at module top. sklearn is
slow to import (~0.5s); paying that at every application startup — when most
sessions never open the chemical space — would be waste. It is imported the first
time a projection actually runs.

### Matplotlib embedding buys a toolbar for free

`FigureCanvasQTAgg` + `NavigationToolbar2QT` gives pan, zoom, and export to
PNG/PDF/SVG with zero extra code — exactly what a research-grade tool needs to
get a figure into a paper. That, plus deterministic PCA, is why Matplotlib beat
a web-plot route here (and it avoids a second QWebEngine after conformers).

## 4. The two-way selection link (and the loop it could have caused)

- **Plot → table**: a click fires Matplotlib's `pick_event`; a drag fires a
  `LassoSelector`. Both resolve to a list of `MoleculeRecord`s and emit
  `points_selected`, which the window turns into a table selection via a new
  `MoleculeTablePanel.select_records` — driving the same machinery a mouse click
  would, so the Structure and Conformer panels follow too.
- **Table → plot**: any table selection change calls
  `ChemicalSpacePanel.highlight_records`, which rings the matching points.

The trap: table selection → highlight plot, and plot select → table selection,
is a cycle. It doesn't loop because **`highlight_records` never emits** — it only
redraws. Plot-click → table-select → plot-highlight terminates there. Keeping the
"display" path (highlight) strictly separate from the "intent" path (emit) is
what makes bidirectional linking safe. `highlight_records` also updates the
existing scatter's sizes/edge-colours **in place** rather than re-rendering, so
the current pan/zoom survives a selection change.

## 5. Colour-by turns the map into a property landscape

The colour combo lists every descriptor (from `DESCRIPTOR_SPECS`) plus the last
similarity score. Continuous values get a viridis colourmap and a colourbar;
**missing values render grey**, so an un-computed descriptor is visibly absent
rather than silently painted as zero — the same honesty rule as the blank
table cells. Hovering a point shows its name and the coloured value.

## 6. Verification

- `pytest`: **212 tests** (was 205) — PCA/t-SNE projection, on-demand
  fingerprinting, determinism under a fixed seed, the too-few-molecules guard,
  a non-default (MACCS) encoding, and progress. Clean under `ruff`, `black`, and
  `-W error::DeprecationWarning` (sklearn/matplotlib included).
- The interactive panel (Matplotlib events, lasso, colourbar, theme) is
  screenshot-verified in dark and light — the second one even caught the live
  cursor-coordinate readout in the toolbar, proving the canvas is fully wired.
- `matplotlib` and `scikit-learn` were promoted from the optional `science`
  extra to **core dependencies**, since Modules 10 and 11 make them load-bearing.

## 7. Research lens

Chemical-space plots are everywhere, and most are decorative. Two threads here
are genuinely publishable and build directly on what this module computes:

- **Projection-honesty overlay.** PCA and t-SNE both *distort* — points that look
  close on screen may be far apart in fingerprint space, and t-SNE notoriously
  invents clusters. A **per-point trustworthiness/continuity overlay** (the
  standard but rarely-shown neighbourhood-preservation metrics) painted onto the
  same scatter would tell a chemist *which regions of the map to believe*. We
  already have the high-dimensional matrix and the 2D coordinates side by side —
  the exact inputs those metrics need.
- **Activity-cliff surfacing in 2D.** Colour-by-similarity plus the projection is
  one step from highlighting **activity cliffs** — pairs that are structurally
  near but far apart in a property. A method that ranks and draws those edges on
  the map, validated against known cliff datasets, is a concrete contribution to
  visual SAR analysis. It reuses this module's projection and Module 7's scores.

Both still rank behind Module 4's standardization-divergence benchmark, but the
projection-honesty overlay is unusually easy to prototype from here.
