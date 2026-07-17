# Module 4 — Molecular Standardization · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`
> and the before/after/dialog screenshots in this folder.

---

## 1. What we built and why it matters

The first module that does **real chemistry**. Raw datasets are inconsistent:
salts attached, mixed charge states, tautomer variants, and — after fixing
those — duplicates. Descriptors, fingerprints and clustering computed on such
data are *silently wrong*. Every serious pipeline (ChEMBL curation, pharma
registration) standardizes first, so we do too, **before** Modules 5–11.

The result is a user-composable pipeline:
`Cleanup → Strip salts → Neutralize → Canonical tautomer → Remove duplicates`,
run on a background thread, producing a full change report.

On the demo set it collapsed **10 molecules to 6** (see `screenshot_after.png`).

## 2. RDKit: the standardization toolbox

`rdkit.Chem.MolStandardize.rdMolStandardize` provides:

| Tool | Job | Example |
|---|---|---|
| `Cleanup(mol)` | sanitize + normalize functional-group drawings | two nitro depictions → one |
| `LargestFragmentChooser().choose(mol)` | keep the parent, drop salts/solvents | `c1ccccc1.Cl` → `c1ccccc1` |
| `Uncharger().uncharge(mol)` | neutralize sensible charges | `CC(=O)[O-]` → `CC(=O)O` |
| `TautomerEnumerator().Canonicalize(mol)` | one canonical tautomer | 2-hydroxypyridine ≡ 2-pyridone |

**Performance lesson:** these helper objects are *expensive to construct*
(especially `TautomerEnumerator`). We build them **once** in
`standardize_records` and pass them into the per-molecule helper — never inside
the loop. Constructing per-molecule would dominate runtime on large sets.

**Why tautomer canonicalization is OFF by default:** it is the slowest step and
can occasionally pick a form chemists dislike; the user opts in via the dialog.

## 3. Software design (mirrors the loader on purpose)

- **Immutable in, new records out.** `standardize_records` never mutates input
  records. When a molecule changes, we build a *new* `MoleculeRecord` (name,
  source, index, properties preserved). A test asserts the input's SMILES is
  unchanged after a run.
- **Unchanged records are reused, not copied** — if no step altered a molecule,
  the original object is returned (identity test proves it). Cheap and correct.
- **Failures never drop molecules.** A per-record `try/except` logs the failure,
  records it in the report, and keeps the *original* record. One bad molecule
  can't abort a 10k-molecule run.
- **A report, not just results** (`StandardizationReport`): standardized
  records + `changed[]` (before/after SMILES + which steps) + `duplicates_removed`
  + `failures[]`. Same "errors/provenance are data" philosophy as `LoadReport`.
- **Options are a frozen dataclass** — serializable straight into Settings
  (Module 15) and batch configs (Module 13) later.

**Change detection trick:** the inner `advance()` closure compares canonical
SMILES before/after each step and only records the step name if it actually
altered the molecule — so the report says exactly *why* each molecule changed.

## 4. Deduplication: the tradeoff we chose

We dedup by **standardized canonical SMILES** (first occurrence wins). The
documented alternative is **InChI** (also handles some tautomer/charge cases
independently). We chose canonical SMILES because:
- We already compute it (no extra cost).
- After the pipeline's own tautomer/charge normalization, SMILES-equality is
  the right notion of "same standardized structure."
- InChI adds a dependency surface and is slower.

If a future module needs cross-standardization identity (e.g. matching against
an external registry), an InChIKey-based option is a clean addition.

## 5. GUI wiring (and a concurrency subtlety)

- `StandardizeDialog.get_options()` — the **static factory** idiom Qt itself
  uses. Returns `StandardizationOptions` or `None` (cancel). Callers never
  manage dialog lifetime.
- Reuses `FunctionWorker` — the *third* consumer of the generic worker we built
  in Module 2. This is the payoff of writing it generically.
- **Concurrency subtlety:** the worker gets a **snapshot** (`list(model.records)`)
  and loads are **paused** while standardization runs (`_std_worker` guard in
  `_start_next_load`). Otherwise a file finishing mid-pipeline would append rows
  the pipeline never saw, and the `set_records` at the end would delete them.
  Getting cross-task interaction right is where real desktop bugs live.

## 6. Polish rider (why the app now looks the part)

Prompted by the "how is GUI quality?" check, we addressed the biggest amateur
tells:
- **Icons.** Hand-authored SVGs in `resources/icons/` (MIT-clean, no external
  assets), loaded by `icons.get_icon` via `importlib.resources` at multiple
  raster sizes and cached with `lru_cache`. A missing asset logs and returns an
  empty icon — branding never crashes the app. App/window icon + toolbar icons.
- **Right-click context menu** on the table: Copy SMILES, Copy Name(s), Remove
  Selected — the desktop-app staple, operating on the multi-selection.
- **Column widths**: SMILES capped at 260px so Formula / Heavy atoms / Source
  stop being pushed offscreen (visible in `screenshot_after.png` vs Module 3).

## 7. Verification (actually run)

- `pytest`: **44/44 passing** — salt stripping, neutralization, tautomer merge
  → duplicate, dedup first-wins, dedup-disabled, unchanged-reused (identity),
  metadata preserved on change, input-never-mutated, progress-to-total; icon
  loader (known + missing).
- `ruff` + `black`: clean.
- **Screenshots**: before/after standardization + the options dialog, saved in
  this folder — visual proof the 10→6 collapse and the icons render correctly.

## 8. Research lens — the first real opportunity

This is where a **methods paper** starts to look plausible, and it is *not* a
GUI wrapper:

- **Gap:** standardization is treated as a solved black box, yet different
  toolkits/pipelines (RDKit vs ChEMBL structure pipeline vs commercial) produce
  *different* "standard" structures for the same input, and the community has no
  open, reproducible benchmark of *how often they disagree and why*.
- **Novel contribution:** a **standardization-divergence benchmark + an
  auto-repair taxonomy** — classify inputs by which normalization decisions are
  ambiguous (tautomer choice, charge model, mesomeric N-oxides, etc.), quantify
  disagreement across pipelines on public sets (ChEMBL, PubChem, ZINC subsets),
  and propose a confidence score flagging molecules whose standard form is
  pipeline-dependent.
- **Experiments:** run N pipelines over M public molecules; report per-class
  divergence rates; validate the confidence flag against known hard cases.
- **Metrics:** pairwise standardized-InChIKey agreement, per-transformation
  divergence frequency, flag precision/recall on a curated hard set.
- Wawekit is the ideal vehicle: our report already records *which step changed
  what*, so instrumenting divergence is a natural extension. We will revisit
  this after descriptors/fingerprints give us more comparison machinery.
