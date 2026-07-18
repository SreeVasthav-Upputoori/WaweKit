# Research Track · R1 — Standardization Protocol Engine · Build Notes

> The first build stage of the flagship: a *standardization-reproducibility
> auditor*. R1 is the engine everything else stands on. Read alongside
> `graphical_abstract.html`, `demo_divergence.py` and its captured
> `demo_output.txt`.

---

## 1. What R1 is and why it exists

The paper's thesis: **structure standardization is not reproducible across
protocols, and that has a measurable, attributable structure.** To measure it, we
first need to *run* many standardization protocols and compare their outputs.
That is R1:

- **`StandardizationProtocol`** — a *named set of toggleable operations*, applied
  in a fixed canonical order. Modelling standardization as composable operations
  (not one opaque `standardize()`) is the whole point: it lets two protocols be
  compared, and lets a divergence later be *attributed* to a specific operation
  by toggling it (ablation, coming in R2).
- **Presets** — `Minimal` (sanitize + normalize), `ChEMBL-like` (metal-disconnect,
  normalize, reionize, keep parent fragment, neutralize — deliberately **no**
  tautomer canonicalization, matching the real ChEMBL pipeline), and `Aggressive`
  (all eight operations).
- **Identity** — a molecule's *standard identity* is its **InChIKey**; protocols
  *agree* on a molecule iff their InChIKeys match. But see §3 — this is where it
  gets interesting.
- **`standardize(mol, protocol)` → `StandardForm`** carrying both the canonical
  **SMILES** and the **InChIKey**, so agreement can be measured on either.

Eight operations (`StandardOp`): metal-disconnect, normalize, reionize,
fragment-parent, uncharge, remove-isotopes, remove-stereo, canonical-tautomer.
Everything is Qt-free — the engine runs in a benchmark harness or a notebook.

## 2. Engineering notes

- **Never mutate the input.** `apply_protocol` works on `Chem.Mol(mol)` — records
  are shared, so mutating one during an audit would corrupt the dataset (tested).
- **Reuse the costly helpers.** `TautomerEnumerator` and friends are built **once**
  (`@lru_cache`), not per molecule — the same performance lesson from Modules 4/6,
  which matters far more here because R2 will call the engine *protocols × ops ×
  molecules* times.
- **Never abort on one bad molecule.** `standardize` catches and returns a
  `StandardForm` with `error` set — a divergence run over 100k molecules cannot
  be killed by one pathological structure.
- **`with_op(op, enabled)`** returns a renamed copy with one operation toggled —
  the exact primitive R2's ablation-based cause attribution needs.

## 3. The finding R1 already surfaces (this is the paper)

A test *failed* in the best possible way and taught us the core methodological
point. The canonical-tautomer operation rewrote 2-hydroxypyridine's SMILES
(`Oc1ccccn1` → `O=c1cccc[nH]1`) — **but its InChIKey did not change.** Why?
**InChI performs its own internal tautomer normalization.** So:

> **The choice of identity key changes what "reproducible" means.** InChIKey
> *masks* tautomer divergence that canonical SMILES *reveals*.

The demo (`demo_output.txt`) makes it concrete over eight molecules:

```
2-hydroxypyridine       DIVERGE (smiles)   agree (inchikey)   2 smiles / 1 inchikey
...
SMILES-identity divergence:   5/8 molecules pipeline-dependent
InChIKey-identity divergence: 4/8 molecules pipeline-dependent
```

The two identity keys **disagree on which molecules are labile**. That is not an
obvious result, it is not a bug, and no standardization tool reports it. It
directly shapes the study:

- The divergence analysis (R2) must measure agreement on **both** identities and
  report their disagreement as a first-class result.
- The taxonomy must separate "SMILES-labile but InChIKey-stable" (tautomer/charge
  cases InChI absorbs) from "labile under both" (salts, isotopes, stereo, and the
  tautomers InChI does *not* normalize).

Finding this on day one — from a failing unit test — is exactly why we build the
engine test-first before the analysis.

## 4. Verification

- `pytest`: **12 R1 tests** (275 total) — InChIKey format, canonical operation
  order, salt stripping, minimal-vs-ChEMBL divergence, the tautomer SMILES change,
  **the InChIKey-masks-tautomer finding**, isotope/stereo effects on identity,
  `with_op` ablation renaming, no-mutation, preset contents, trivial-molecule
  agreement. Clean under `ruff`, `black`, `-W error::DeprecationWarning`.
- **Demonstration**: `demo_divergence.py` → `demo_output.txt`, the "verification
  you can see" for an engine module (the visual payoff arrives in R4).

## 5. What's next on the research track

- **R2 — Divergence analysis**: per-molecule agreement on both identities +
  **ablation-based cause attribution** (toggle each op, see which flip changes the
  outcome → a divergence taxonomy).
- **R3 — Reproducibility metrics**: dataset score, protocol-pair agreement matrix,
  cause spectrum.
- **R4 — GUI panel**: score, agreement heatmap, cause bar chart, and labile
  molecules shown with their divergent forms side-by-side (reusing the depiction
  + highlight engine).
- **R5 — Benchmark harness** over public datasets (ChEMBL/PubChem/ZINC).
- **R6 — Manuscript.**

## 6. Research lens (the whole point now)

R1 makes the contribution buildable and already produced a non-trivial finding
(identity-key-dependent lability). The claim taking shape: *a measurement
framework that quantifies standardization reproducibility, attributes divergences
to specific operations, and shows the result depends on the identity convention.*
That is methodological novelty — not a new standardizer — validated on public
data, delivered in an open tool. It squarely satisfies the founding rule and is a
credible fit for **Journal of Cheminformatics** or a **Frontiers** methods/tool
venue.
