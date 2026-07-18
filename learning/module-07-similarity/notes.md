# Module 7 — Similarity Search · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`
> and the screenshots in this folder (`similarity-dialog.png`,
> `similarity-dialog-invalid.png`, `similarity-ranked.png`,
> `similarity-filtered.png`, `similarity-light.png`).

---

## 1. What we built and why it matters

Module 6 turned every structure into a bit vector. This module answers the
question those vectors exist for: **"given this molecule, which others in my
dataset look like it?"**

That question — *find me more compounds like my hit* — is the single most-used
operation in a medicinal chemist's day, and it's the first module whose output a
chemist would actually act on. Everything before this described molecules.
This one **ranks** them.

Run it on `samples/demo_similarity.smi` (new this module — an aspirin analogue
series that fades out into unrelated chemistry), query aspirin:

| Rank | Molecule | Tanimoto |
|---|---|---|
| 1 | **aspirin** (the query) | 1.000 |
| 2 | salicylic-acid | 0.448 |
| 3 | benzoic-acid | 0.357 |
| 4 | methyl-salicylate | 0.353 |
| 5 | ethyl-salicylate | 0.324 |
| … | paracetamol | 0.222 |
| 12 | caffeine | 0.089 |
| 13 | glucose | 0.025 |

The salicylates rank top, the other drugs mid, the sugar last. The chemistry is
sane.

**Note 0.448 for salicylic acid** — that's aspirin *minus one acetyl group*, and
it still only scores 0.45. Real-world similarity scores are far lower than
intuition suggests. The "≥ 0.85 is similar" threshold you read in papers is
*very* strict, and this is the number to remember when someone proposes one.

## 2. The design fork: a similarity is not a property of a molecule

This is the idea the whole module is built around, and it's what makes Module 7
structurally different from 5 and 6.

A descriptor (MW) and a fingerprint are **intrinsic** — they depend on the
structure and nothing else. Recompute tomorrow, get the same answer. `MW =
180.16` is a complete fact on its own.

A similarity score is **relational**. `0.448` on its own is *meaningless*. It is
0.448:

- **against aspirin**,
- **by Tanimoto**,
- **on Morgan r2 · 2048b vectors**.

Change any one of those three and the number changes — while looking exactly as
plausible as before.

So `SimilarityScore` refuses to be a bare float. It carries the `SimilarityQuery`
that produced it:

```python
@dataclass(frozen=True, slots=True)
class SimilarityScore:
    value: float
    query: SimilarityQuery      # smiles + name + metric + fingerprint options
```

This is the same discipline Module 6 established when `Fingerprint` started
carrying its options: **a derived number travels with the context that makes it
true.** The payoff is visible in the UI — the cell shows `0.448`, the tooltip
shows `Tanimoto vs aspirin · Morgan r2 · 2048b`. You cannot read the score
without its context being one hover away.

### Why the query stores SMILES, not the record

`SimilarityQuery` identifies the query by *canonical SMILES*, not by a reference
to the `MoleculeRecord` it came from. Two practical reasons:

- The query may not be **in** the dataset — pasting a SMILES to search a library
  is standard practice, and there's no record to point at.
- Holding a record would keep it alive after the user deletes that row, and make
  the score's identity depend on object lifetime instead of on chemistry.

### Where each piece lives (the layering rule, again)

- `SimilarityQuery` / `SimilarityScore` / `SimilarityMetric` → **models**,
  because `MoleculeRecord.similarity` refers to them and models may never import
  services.
- `SimilarityRequest` / `SimilarityReport` / `search_similar` → **services**,
  because nothing in models refers to them. Same call Module 4 made with
  `StandardizationOptions`.

## 3. Bulk, not a Python loop

RDKit offers both `TanimotoSimilarity(a, b)` and
`BulkTanimotoSimilarity(a, [b, c, d, …])`. Same numbers — but bulk crosses the
Python↔C++ boundary **once** for the whole dataset and loops in C++.

```python
scores = _BULK_FUNCTIONS[metric](query_fp.bits, [r.fingerprint.bits for r in scorable])
```

This is *why* Module 6 kept RDKit's native `ExplicitBitVect` instead of
converting to numpy: bulk consumes it directly, no conversion step. A decision
made one module early paid off here for free.

**Progress reporting follows the time, not the steps.** The scoring is a single
C++ call — microseconds. All the time goes into *encoding* the dataset, so
`search_similar` passes the `progress` callback straight to `compute_fingerprints`
and doesn't try to fake granularity over a call that's already instant.

## 4. The bug this module exists to prevent (and what I got wrong)

I originally wrote in the service docstring: *"Tanimoto between a Morgan r2
vector and a MACCS vector returns a number… nothing in RDKit will warn you."*

**That was wrong**, and measuring it made the real lesson much sharper.

RDKit guards exactly one thing: **bit length**.

```
Morgan 2048 vs MACCS 167   ->  ValueError: BitVects must be same length
```

Loud, obvious, safe. But it has nothing whatsoever to say about vectors that are
the *same length* and mean *different things* (aspirin vs salicylic acid, all
measured and now pinned in `test_rdkit_only_guards_bit_length_not_meaning`):

| Compared | RDKit says | Verdict |
|---|---|---|
| Morgan r2 **vs Morgan r2** | 0.448 | the truth |
| Morgan r2 vs Morgan r3 | **0.394** | silent · plausible · wrong |
| Morgan r2 vs RDKit path | **0.005** | silent · a real hit looks like noise |
| ECFP vs FCFP | **0.000** | silent · a close analogue scores zero |

The mistake RDKit catches is the one you'd have noticed anyway. The mistake that
*ships* is same-length-different-meaning: every number above is a float in
exactly the range a chemist expects, and only the first means anything.

So `search_similar` does two things before scoring:

1. **Encodes the query with the same options as the dataset** — by running
   `compute_fingerprints` over the records first (cheap: it reuses matching
   vectors and recomputes mismatched ones), then building the query's vector
   with those same options. The query is *never* encoded with defaults.
2. **Checks every record with `is_comparable_to` anyway**, and refuses the
   failures.

### Step 2 is not redundant — and I only found out by testing it

My first instinct was that step 2 was pure defensiveness, and I said so in a
comment: *"Unreachable in normal operation."* Then a test failed for an
unexpected reason and I checked. It's reachable, and here's how:

`compute_fingerprints` assigns a new vector **only on success**:

```python
try:
    record.fingerprint = Fingerprint(bits=build(record.mol), options=normalized)
except Exception:
    report.failures.append(...)     # <- record KEEPS its old fingerprint
```

So: take a MACCS-encoded dataset, re-encode as Morgan, and have one molecule
throw. That record silently keeps its **MACCS** vector while everything around it
is Morgan. Same field, same type, different meaning — and since MACCS is 167 bits
it would even hit RDKit's length guard, but a Morgan-r2 → Morgan-r3 version of
the same accident sails straight through.

The comment now says what's true, and `test_incomparable_leftover_fingerprint_is_skipped_not_scored`
pins the path. **Lesson: a "defensive" check you can't explain is a check you
haven't understood yet.** Write the test that tries to reach it.

### Blank, never 0.000

Records that can't be scored get `similarity = None`, and the cell renders empty.
A `0.000` would claim "we compared this and found nothing in common". Blank says
"we didn't compare this". Same rule as Module 5's uncomputed descriptors, and
stale scores from a previous query are actively cleared rather than left sitting
under a new query's column heading.

## 5. Two design decisions worth stealing

### No threshold field on the dialog

Every tool wants to ask *"similarity cutoff?"* in the search dialog. We
deliberately don't. A threshold chosen **before** you've seen a single score is a
guess: set it too high and you re-run the whole search to find out, too low and
you scroll.

Instead the scores land in a **sortable column**, and Module 5's quick-filter
narrows them *afterwards*, interactively:

```
Sim >= 0.7        # 6 of 13 shown
```

One box for `MW < 500` and `Sim >= 0.7`. One grammar to learn. No threshold field
on the dialog at all. **Reuse worth having removes a control, not just code.**

`SimilarityFilter` is a *sibling* of `NumericFilter`, not a `DescriptorSpec`
entry — bolting similarity into `DESCRIPTOR_SPECS` would have bought a few lines
of shared plumbing while quietly teaching the rest of the app that a score is a
property of a molecule, which is the one idea this module exists to correct.

### Extract on the second consumer, not the first

Module 6 kept the fingerprint controls inside `FingerprintDialog`, and that was
**right**: a widget invented for a single caller is an abstraction you pay for
and don't use.

Module 7 is the second caller — a similarity search must encode the query and the
dataset the same way, so its dialog needs the same choices. *Now* extraction pays:
`FingerprintOptionsWidget` means one enable/disable rule, and — more valuably —
one place for the `QVariant` coercion, so it can't be forgotten in the next
dialog.

**Extract when the duplication is real and present, not when it's imagined.**
The tests moved with the behaviour (`test_fingerprint_options.py`), leaving
`test_fingerprint_dialog.py` testing what the dialog still does.

## 6. Two bugs found by looking at the screen

Both were invisible to all 173 tests and obvious in the first screenshot. This is
the argument for the convention of ending every module with real screenshots.

### A checked radio button rendered *nothing*

Module 7 is the first module to use radio buttons. In the dark theme, Qt's native
style drew the **checked** dot invisibly against our background — the unchecked
radio showed a circle, the checked one showed **nothing at all**. The dialog
looked like no option was selected, and the user had no way to tell which query
source was live.

Not caused by this module — a latent theme bug from Module 1 that no previous
feature had triggered. Fixed with an explicit indicator in both `.qss` files:

```css
QRadioButton::indicator:checked {
    background-color: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.5,
                                      stop: 0 #5a9fd8, stop: 0.5 #5a9fd8,
                                      stop: 0.55 #1a1b1e, stop: 1 #1a1b1e);
}
```

The hard stop at 0.5 is the trick: it's a filled circle inside a ring, not a
fade. Checkboxes were checked and are fine — they're deliberately left native.
`test_themes.py` pins that the rule survives (only a screenshot can catch the
rendering itself, but deleting the rule silently restores the bug).

### The result landed off-screen

The Similarity column sits past the whole descriptor panel. On a normal window,
running a search produced **no visible change**: the score was off the right
edge, and sorting had silently rearranged the rows — which is somehow worse than
nothing happening. `refresh_similarity` now ends with:

```python
self._view.scrollTo(self._proxy.index(0, SIMILARITY_COLUMN),
                    QAbstractItemView.ScrollHint.EnsureVisible)
```

## 7. Qt techniques new this module

- **`FontRole`** — the query molecule's own row renders bold. After sorting it
  sits at the top scoring 1.000, but so might a duplicate, and once the user
  re-sorts by another column it's lost entirely. `is_query_molecule()` compares
  *canonical SMILES*, deliberately **not** `value == 1.0`: a perfect score means
  the fingerprints are identical, which is weaker than being the same molecule
  (hashed vectors collide, and no fingerprint here sees stereochemistry).
- **Live validation** — the pasted-SMILES box parses on every keystroke and OK
  stays disabled until the query resolves. Parsing one SMILES is microseconds,
  far below noticeable. The alternative (accept anything, fail after the dialog
  closes) makes the user re-open and re-type to learn what was wrong.
- **`rdBase.BlockLogs()`** — RDKit reports a bad SMILES by returning `None` *and*
  writing to stderr. Validating per keystroke meant `C1CC` mid-typing spewed a
  `SMILES Parse Error` line per character. `BlockLogs` mutes RDKit for that one
  call; the failure is already surfaced by the return value.
- **`similarity_requested` signal** — the table panel doesn't run the search. It
  has no worker, no progress bar, and no business knowing about services; it
  reports the *intent* and lets `MainWindow` decide. Same seam as
  `selection_changed`.
- **Splitting `_build_context_menu` from `_show_context_menu`** — `exec()` blocks
  on a modal loop, so a test can only inspect what the menu *offers* if building
  it is reachable without showing it.

## 8. The `StrEnum` trap that wasn't

Module 6's hard-won lesson is that a `StrEnum` in a Qt combo comes back from
`currentData()` as a plain `str`, so `is` checks silently fail. `SimilarityDialog`
coerces at the boundary for exactly that reason (`SimilarityMetric(currentData())`).

I *expected* a second trap in the service — `_BULK_FUNCTIONS` is a dict keyed by
enum members, and `Enum.__hash__` is documented as hashing the member's **name**,
which would break lookup by value. Measured it before relying on it:

```
hash(SimilarityMetric.TANIMOTO) == hash('Tanimoto')   # True — hashes by VALUE
```

`StrEnum` inherits `str.__hash__`, so `_BULK_FUNCTIONS["Tanimoto"]` resolves
identically to `_BULK_FUNCTIONS[SimilarityMetric.TANIMOTO]`. No trap. The metric
can arrive from a QVariant or a Module 15 settings file as a bare string and the
lookup just works — pinned by `test_metric_may_arrive_as_a_plain_string`.

Worth writing down because the *expectation* was reasonable and wrong. Check the
interpreter, not your memory.

## 9. Manual tests to run

```
.venv\Scripts\wawekit.exe
```

1. **File → Open** → `samples/demo_similarity.smi` (13 molecules).
2. Select **aspirin** → right-click → **Find Similar to This…** → Search.
   → Table re-sorts, aspirin 1.000 **in bold** at top, glucose 0.025 at bottom,
   status bar names the query and the encoding.
3. Hover a Similarity cell → tooltip reads `Tanimoto vs aspirin · Morgan r2 · 2048b`.
4. Type `Sim >= 0.3` in the filter box → **6 of 13 shown**.
5. **Chemistry → Similarity Search** (Ctrl+Shift+M) with nothing selected →
   dialog opens on **Paste SMILES**; type `C1CC` → ⚠ warning, **Search disabled**;
   correct to `C1CC1` → enabled.
6. Switch metric to **Dice** → re-run → every score ≥ its Tanimoto value.
7. Re-open the dialog → it remembers the encoding you last searched with.
8. **Ctrl+T** → light theme → scores and bold survive; radio dots still visible.

## 10. Publication radar

- **Bit-collision noise in virtual screening** *(strongest new candidate)* —
  hashed FPs fold unbounded fragment space into 2048 bits. How much does
  collision error move real screening rankings, and can we ship a cheap "your bit
  size is too small for this library" diagnostic? Module 7 just built the thing
  that produces the rankings to perturb.
- **Standardization-divergence benchmark** (Module 4) — still the strongest
  candidate overall.
- **Per-descriptor reliability flag** (Module 5) — was parked pending a
  similarity-to-training-set signal. **Module 7 just built that signal.**

Bar to clear, as always: algorithmic novelty, not GUI-wrapping.

## 11. Files touched

**New**

```
src/wawekit/models/similarity.py                  metric, query, score
src/wawekit/services/chemistry/similarity.py      search_similar + report
src/wawekit/gui/dialogs/similarity_dialog.py      query + metric + encoding
src/wawekit/gui/widgets/fingerprint_options.py    extracted, now shared
src/wawekit/resources/icons/similarity.svg        two overlapping sets
samples/demo_similarity.smi                       aspirin analogue series
tests/test_similarity.py                          30 tests
tests/test_similarity_dialog.py                   14 tests
tests/test_fingerprint_options.py                 moved from the dialog's tests
tests/test_themes.py                              radio-indicator regression
```

**Modified**

```
models/molecule.py              + similarity field
gui/widgets/molecule_table.py   Similarity column, FontRole, scrollTo,
                                similarity_requested, menu split
gui/widgets/molecule_filter.py  + SimilarityFilter ("Sim >= 0.7")
gui/dialogs/fingerprint_dialog.py   thinned to a shell
gui/main_window.py              action, worker, report, _last_fingerprint
gui/themes/{dark,light}.qss     radio indicator fix
services/io/molecule_loader.py  + parse_smiles (with BlockLogs)
```

**Status:** 173 tests green · ruff + black clean · no deprecation warnings ·
verified end-to-end in the running app.
