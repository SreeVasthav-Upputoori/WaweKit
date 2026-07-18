# Module 5 — Molecular Descriptors + Quick-Filter · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`
> and the two screenshots in this folder (`descriptors-panel.png`,
> `descriptors-filter.png`).

---

## 1. What we built and why it matters

**Descriptors** are numbers computed from a structure — the basic vocabulary of
computational chemistry. This module adds the classic drug-likeness panel and
the **Lipinski "Rule of 5"** verdict derived from it:

| Descriptor | Meaning | RDKit call |
|---|---|---|
| MW | molecular weight (g/mol) | `Descriptors.MolWt` |
| LogP | lipophilicity (Crippen) | `Descriptors.MolLogP` |
| TPSA | topological polar surface area (Å²) | `Descriptors.TPSA` |
| HBD / HBA | H-bond donors / acceptors | `Descriptors.NumHDonors` / `NumHAcceptors` |
| RotB | rotatable bonds (flexibility) | `Descriptors.NumRotatableBonds` |
| Rings | ring count (SSSR) | `rdMolDescriptors.CalcNumRings` |
| Lipinski | how many Rule-of-5 thresholds are broken | derived from the above |

Why it matters: **everything downstream** — similarity, clustering, chemical-
space plots (Modules 6–11) — either consumes these numbers directly or repeats
this exact "compute a value per molecule, cache it, show it in a column,
background-thread it" shape. Getting the pattern right once makes the next six
modules mostly repetition.

We also delivered the **quick-filter box** promised at the end of Module 4: a
text field above the table that filters visible rows by substring (`aspirin`)
or by a real numeric comparison against a descriptor (`MW < 500`).

## 2. RDKit: the descriptor toolbox

`rdkit.Chem.Descriptors` and `rdkit.Chem.rdMolDescriptors` are pure functions
`Mol -> number`. There is no state to build up (unlike Module 4's
`TautomerEnumerator`), so `compute_descriptor_set(mol)` is a flat call list.

**Lipinski is not an RDKit call — it is a rule we own.** The four thresholds
(MW ≤ 500, LogP ≤ 5, HBD ≤ 5, HBA ≤ 10) and the "≤ 1 violation passes"
convention live in `models/descriptors.py` as named constants. `HBD`/`HBA` here
mean the *Lipinski* donor/acceptor definitions RDKit's `NumHDonors`/
`NumHAcceptors` implement — deliberately, so the count and the rule agree.

## 3. The layering fork this module forced

The plan sketched `DescriptorSet` living in `services/`. **The layering rule
killed that:** dependencies point downward only —
`gui → services → models → core` — and `MoleculeRecord` (a *model*) now carries
a `descriptors` field. A model may never import from a service. So:

- **`models/descriptors.py`** — the *data*: `DescriptorSet` (frozen), the
  Lipinski constants, and `DESCRIPTOR_SPECS` (the column registry). No RDKit.
- **`services/chemistry/descriptors.py`** — the *computation*: RDKit calls that
  fill a `DescriptorSet`, plus the batch `compute_descriptors` + report.

This split is what lets a notebook build a `DescriptorSet` by hand, or a future
SD-file reader adopt values already in the file, without dragging RDKit along.

## 4. Where computed values live (the design decision)

We chose **one typed field on the record**: `descriptors: DescriptorSet | None`.
Not eight loose fields, and not a side-table cache. The reasoning:

- **One field per *concept*, not per *value*.** Module 6 adds `fingerprint` the
  same way; the record grows by one slot per feature, not one per number.
- **Staleness solves itself.** Standardization builds *new* records, whose
  `descriptors` default to `None` and get recomputed — stale numbers can't
  survive a structural edit. A side-table keyed by SMILES would instead collide
  on duplicates and have to be carried alongside the records everywhere.
- **O(1) lookup, trivial sort**, because the value is right on the row's object.

**Descriptors mutate records in place — Module 4 did the opposite.** That looks
inconsistent until you see the rule underneath: *the standardizer changes
chemistry, so it returns new records; descriptors change nothing.* A descriptor
is a cache of a value the structure already implies, exactly like
`MoleculeRecord.smiles`. Filling the cache in place means the table keeps the
same record objects — no dataset swap, no lost selection, just a repaint.

## 5. The column registry: adding a descriptor is a one-line diff

`DESCRIPTOR_SPECS` is a tuple of `DescriptorSpec(key, label, getter, fmt,
tooltip)` and it is the **single source of truth**. From it we derive:

- the table headers (`_HEADERS` splices the spec labels between the leading
  columns and `Source`),
- each cell's display text (`spec.fmt.format(spec.getter(ds))`),
- each column's sort key (the raw number via `spec.getter`),
- the header tooltip, and
- the quick-filter's vocabulary (`DESCRIPTOR_BY_KEY`, lowercased).

Adding a ninth descriptor means appending one `DescriptorSpec`. No other file
learns about it. A test (`test_specs_cover_every_dataset_field`) calls every
getter and format string against a real molecule, so a typo in the registry
fails loudly.

## 6. The quick-filter: a tiny query language, and why not regex

Qt's built-in `setFilterRegularExpression` matches a column's **display text**.
That is fine for `aspirin` and useless for `MW < 500` — regex cannot compare
numbers. So `MoleculeFilterProxyModel` overrides `filterAcceptsRow` and asks the
**record**, not its rendered text, seeing real floats and ints.

`parse_filter(text)` returns one of four things:

- `None` — empty query, accept everything.
- `NumericFilter` — matched `key op number` where `key` is a known descriptor.
- `TextFilter` — substring against name + SMILES, case-insensitive.
- `InvalidFilter` — *looks* like a comparison but isn't parseable (unknown
  descriptor, or `MW >` with no number). It matches nothing **and carries a
  reason string** the status label shows.

That `InvalidFilter` case is a deliberate honesty decision: a filter that
quietly matches nothing is how users lose data. `MW >` shows
"⚠ Incomplete comparison…", not a silently empty table.

**Two subtleties worth remembering:**

- **Records without descriptors are *hidden* by a numeric filter, not shown.**
  The honest answer to "is MW < 500?" before computing is *unknown*, and mixing
  unknowns with confirmed matches misrepresents the result set. This is why
  `descriptors-filter.png` needs descriptors computed first — and why
  `refresh_descriptors()` re-invalidates the filter so `MW < 500` starts working
  the instant the numbers arrive.
- **`invalidate()` not `invalidateRowsFilter()`.** The narrower call is the
  "correct" one, but PySide6 6.11 flags it (and `invalidateFilter`) as
  deprecated via a binding annotation, so we use the stable public slot. A
  `-W error::DeprecationWarning` test run confirms we emit none.

## 7. GUI wiring

- **`FunctionWorker` again** — the *fourth* consumer of the Module 2 worker.
  `compute_descriptors` takes the same `progress` callback shape, so it drops
  onto a background thread with zero new infrastructure. Same payoff as Module 4.
- **Same concurrency discipline** — the worker gets a snapshot
  (`list(model.records)`) and loads pause while it runs (`_desc_worker` added to
  the `_start_next_load` guard). A file finishing mid-run would just miss this
  descriptor pass, not corrupt anything, but pausing keeps the progress bar
  meaningful and the behaviour identical to standardization.
- **`descriptors_updated()`** emits `dataChanged` over *only* the descriptor
  column block — no `beginResetModel`, so scroll position and selection survive
  the repaint.
- **Filter status label** under the table reports `N molecule(s)`,
  `N of M shown`, or the `⚠ reason` — live feedback on every keystroke.

## 8. Verification (actually run)

- `pytest`: **70/70 passing** (was 44). New: 12 descriptor tests (aspirin values
  vs known references, Lipinski counting at 0/1/4 violations, cache-in-place,
  reuse, `recompute`, progress-to-total, spec registry coverage), 15 filter
  tests (every operator, negatives/decimals, case-insensitive tokens, unknown &
  incomplete → invalid, text vs numeric predicates, hidden-before-compute), and
  6 table tests (blank-until-computed, formatted-after-compute, header tooltip,
  text + numeric filtering through the panel).
- `-W error::DeprecationWarning`: clean (proves the `invalidate()` fix).
- `ruff` + `black`: clean.
- **Screenshots** (this folder), driven through the real `MainWindow`:
  `descriptors-panel.png` (all eight descriptor columns populated on the 9-mol
  demo set) and `descriptors-filter.png` (`MW < 200` → "5 of 9 shown",
  ibuprofen at 206 correctly dropped, row numbers preserving original indices).

Spot-check against literature values, visible in the panel screenshot: aspirin
MW 180.16 / LogP 1.31 / TPSA 63.6 / HBD 1 / HBA 3 / RotB 2 / Rings 1 /
Lipinski 0 — all correct.

## 9. Research lens

Honest read: **this module is table stakes, not a paper.** Computing standard
descriptors is a solved problem and wrapping them in a GUI is not novelty. The
one genuinely research-adjacent thread here is **applicability / confidence**:
Crippen LogP and TPSA are *models* with known failure regions (organometallics,
zwitterions, very large or unusual scaffolds), yet tools present every value
with identical false confidence. A per-descriptor **reliability flag** — "this
LogP is an extrapolation outside the training domain" — would be a real
contribution, but it only becomes tractable once fingerprints (Module 6) give us
a similarity-to-training-set signal. Parked until then; noting it so the thread
isn't lost. The stronger opportunity remains Module 4's standardization-
divergence benchmark.

## 10. What's next

Module 6 — **Fingerprints** (Morgan/ECFP, RDKit, MACCS). It attaches to
`MoleculeRecord` as a second `fingerprint` field using the exact pattern proven
here, and unlocks Module 7 (similarity search) and Module 11 (clustering).
```
gui: Chemistry → "Compute Fingerprints" → FunctionWorker
services/chemistry/fingerprints.py → compute_fingerprints(records, progress)
MoleculeRecord gains: fingerprint field (cached, in place, None until computed)
```
