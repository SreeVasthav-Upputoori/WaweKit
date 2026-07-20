# Research Track · R2–R6 — Divergence, Metrics, GUI, Benchmark, Manuscript

> Stages 2–6 of the flagship research effort, built as one fast pass (R1 already
> has its own detailed notes at `learning/research-track-R1-protocol-engine/`).
> This document covers what each stage adds, briefly but completely.

---

## R2 — Divergence analysis + ablation cause attribution

**File:** `services/reproducibility/divergence.py`

- `analyze_molecule(mol, protocols)` standardizes a molecule with every protocol
  and checks agreement on **both** identity conventions (SMILES, InChIKey) —
  the R1 finding made this mandatory, not optional.
- **Ablation cause attribution**: for a labile molecule, take the richest
  protocol in the comparison, and toggle each of its operations off one at a
  time (`protocol.with_op(op, False)`, the R1 primitive built for exactly this).
  If removing an operation changes the InChIKey (checked first — the "deeper"
  identity) or the SMILES, that operation is implicated as a cause. This is the
  step that turns "these two disagree" into "these two disagree *because of*
  charge neutralization" — an attributable diagnosis, not just a flag.
- `analyze_divergence(records, protocols)` runs this over a whole dataset and
  aggregates: `n_labile`, `n_smiles_labile`, `n_inchikey_labile`,
  `cause_counts()`.
- 9 tests, including one that reproduces the R1 tautomer finding as a
  divergence result, and one confirming ablation correctly attributes a salt
  divergence to `fragment_parent`/`uncharge`.

## R3 — Reproducibility metrics

**File:** `services/reproducibility/metrics.py`

- `compute_metrics(run)` turns a `DivergenceRun` into three numbers a paper
  wants: the headline **reproducibility score** (per identity), the **pairwise
  protocol-agreement matrix** (finer-grained — similar protocols should agree
  more than dissimilar ones, which a test confirms), and the **cause spectrum**
  (fraction of labile molecules implicating each operation).
- Deliberately matplotlib-free — this module only computes numbers; rendering
  is R4's job. Keeps the metrics independently testable and reusable from a
  plain script.
- 7 tests, including the dataset-scale version of the R1 finding
  (InChIKey-reproducibility can exceed SMILES-reproducibility on the same set).

## R4 — GUI panel

**Files:** `gui/widgets/reproducibility_panel.py`, `gui/dialogs/reproducibility_dialog.py`

- Follows the Chemical Space panel's proven pattern (Module 10): embedded
  Matplotlib canvases with a real navigation toolbar, so the heatmap and cause
  chart export to PNG/PDF/SVG as paper figures for free.
- **Protocol-agreement heatmap** (InChIKey agreement, red-yellow-green) and a
  **cause-spectrum bar chart**, plus a sortable list of labile molecules
  (worst-agreement first) each showing its form counts and attributed cause.
- Wired as a **Research** menu (new top-level menu, distinct from Chemistry —
  this is explicitly a research feature, not a roadmap one) → `Ctrl+Shift+R` →
  `ReproducibilityDialog` (pick protocols, toggle ablation) → background worker
  → the panel, tabbed with Chemical Space along the bottom dock.
- Screenshot-verified end-to-end in the real app (8 illustrative molecules,
  correct headline stats, both charts rendering, causes listed) — see
  `learning/research-track-R4-gui-panel/screenshot_panel.png`.

## R5 — Benchmark harness

**File:** `services/reproducibility/benchmark.py` (also runnable as
`python -m wawekit.services.reproducibility.benchmark`)

- A Qt-free CLI: reads a SMILES file, runs the R1–R3 pipeline, prints the
  summary a paper's Results section needs, and writes a per-molecule CSV.
- Run for real on a 40-molecule illustrative set spanning salts, charges,
  tautomer-ambiguous heterocycles, isotopes, and stereocenters — see
  `learning/research-track-R5-benchmark/` for the input set, the raw CSV, and
  the captured console output. Headline numbers: **70.0% SMILES-reproducible,
  75.0% InChIKey-reproducible, dominant causes charge (41.7%) and salt/fragment
  handling (33.3%)** — these are the numbers R6's manuscript draft reports.
- 7 tests (SMILES parsing/skipping, CSV output shape, end-to-end run, CLI exit
  codes).

## R6 — Manuscript

**File:** `learning/research-track-R6-manuscript/manuscript_draft.md`

A full IMRAD-structure draft (Abstract, Introduction, Related Work, Methods,
Results, Discussion, Conclusion), populated with the **real R5 benchmark
numbers**, not placeholders. Explicitly marked with a status checklist of what
remains before submission (scaling to public ChEMBL/PubChem/DrugBank data,
literature citations, and cause-taxonomy validation against known hard cases).
The abstract, methods description, and results table are ready to be dropped
into a journal template once the benchmark is scaled up.

## Verification (all stages)

- `pytest`: R2 (9) + R3 (7) + R5 (7) new tests, plus R1's 12 — **298 tests
  passing project-wide**. Clean under `ruff`/`black`.
- The GUI is proven by construction (app smoke test) and by a real screenshot
  of a completed audit.
- The benchmark harness was actually **run**, not just tested — its output is
  captured in this repository as evidence.

## What's genuinely novel here (recap for a reader who skips straight to this file)

1. **A measurement framework**, not a new standardizer — this is the point the
   founding project brief insisted on, and it is what R1–R3 deliver.
2. **Dual-identity divergence measurement**, motivated by a real, surprising
   result (InChIKey vs SMILES disagree about what "reproducible" means) found
   by a failing unit test, not assumed in advance.
3. **Ablation-based cause attribution** — the mechanism that makes the method's
   output actionable rather than merely descriptive.
4. **An open, reusable benchmark harness** with real (if illustrative-scale)
   results already in hand, ready to scale to a publication-grade dataset.
