# Module 17 — Packaging · Build Notes

> Fast pass, per "complete the rest quickly" — real spec, real build, real
> launch of the frozen executable (not just "pyinstaller exited 0").

## What we built

`wawekit.spec` — a hand-written PyInstaller spec, not the naive
`pyinstaller src/wawekit/app.py` one-liner. Three categories of files never
show up in PyInstaller's import-graph analysis and had to be listed
explicitly (full reasoning in [`docs/PACKAGING.md`](../../docs/PACKAGING.md)):

1. Assets read via `importlib.resources` at runtime, never `import`-ed: the
   toolbar SVG icons, the two QSS theme sheets, and `3Dmol-min.js` (Module 9's
   vendored 3D viewer library).
2. RDKit's own data files (atomic parameter tables used by standardization
   and descriptors), pulled in with `collect_data_files("rdkit")`.
3. Hidden compiled submodules — `rdkit.Chem.*`, `sklearn.*`, and
   `matplotlib.backends.backend_qtagg` (needed by every embedded chart:
   Chemical Space, Clustering, the Reproducibility panel).

Deliberate choices, explained in the spec's own comments: folder build (not
`--onefile` — RDKit+Qt+sklearn is too heavy to self-extract on every launch),
UPX disabled (known source of AV false-positives and Qt/RDKit crashes), and
no baked-in `.ico` yet (the app icon is SVG-only; converting one is a
release-prep asset task, not a packaging mechanism — left honestly unset
rather than pointed at a file that doesn't exist).

## Verification (real, not just "the build didn't error")

```
pip install -e ".[dev]"      # pyinstaller>=6.6 added to dev extras
pyinstaller wawekit.spec
```

Build completed in ~144s, producing `dist/Wawekit/Wawekit.exe` (~28.8 MB
executable + `_internal/` with all bundled libraries and data).

Two warnings surfaced in the build log, both reviewed and judged benign:
- `QML plugin binary '...assetdownloaderprivateplugin.dll' does not exist` —
  Wawekit has no QML surface anywhere in the app; this is PySide6's own
  install being incomplete for a Qt feature we never use.
- `Hidden import "scipy.special._cdflib" not found` — an optional scipy
  internal pulled in transitively by scikit-learn's own PyInstaller hook;
  scikit-learn degrades gracefully without it (only used by a handful of
  distribution functions not exercised by clustering/PCA/t-SNE).

**The build was then actually launched** (`dist/Wawekit/Wawekit.exe`, not the
Python source) and its log confirms every category of bundled asset actually
works at runtime, not just at build time:

```
Starting Wawekit 0.1.0
Applied light theme          <- QSS theme file loaded from the frozen bundle
Main window constructed      <- SVG icons rendered (or main window would fail)
Applied dark theme            <- theme toggle round-trip
Applied light theme
Started background load of demo_similarity.smi
Loaded 13 molecule(s), 0 error(s)
Started reproducibility audit over 13 record(s)
Divergence analysis complete: 0/13 labile (SMILES: 0, InChIKey: 0)
```

This exercises RDKit (molecule loading + standardization protocols), the
matplotlib Qt backend (the audit populates the Reproducibility panel's
charts), and the theme/icon assets — three of the exact things a naive
PyInstaller invocation would have silently dropped. The process was left
running briefly, confirmed alive via `tasklist` (not an immediate crash), then
stopped.

## Tradeoffs (stated honestly, given the fast pass)

- Not tested: the QtWebEngine 3D conformer viewer specifically, or a
  macOS/Linux build (this session is Windows-only). The spec's `datas`
  entries are platform-agnostic, but a real Linux/macOS build should be run
  in CI (Module 19) before calling packaging fully cross-platform-verified.
- No code signing, no installer (MSI/NSIS/AppImage/dmg) — explicitly out of
  scope for the packaging *mechanism*; deferred to Module 20 release prep,
  which needs real certificates and per-OS installer tooling this session
  doesn't have.
- No `.ico`/`.icns` app icon baked in yet (SVG-only source asset).
