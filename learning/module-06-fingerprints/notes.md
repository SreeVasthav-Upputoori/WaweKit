# Module 6 — Molecular Fingerprints · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`
> and the three screenshots in this folder (`fingerprint-dialog.png`,
> `fingerprints-morgan.png`, `fingerprints-maccs.png`).

---

## 1. What we built and why it matters

A **fingerprint** encodes a structure as a fixed-length bit vector: each bit
means "some fragment is present". Aspirin becomes 2048 bits with 24 set.

That transformation is the point of the whole module. Once molecules are bit
vectors, *"how similar are these two?"* stops being a hard chemistry question
and becomes a fast bitwise operation:

```
Tanimoto(A, B) = |A ∧ B| / |A ∨ B|      # shared bits / total bits
```

Aspirin vs paracetamol scores **0.222**. This is the engine room for the next
third of the roadmap — `DataStructs.BulkTanimotoSimilarity` is literally what
Module 7 (similarity search) and Module 11 (clustering) will call.

Three algorithms, chosen because they teach genuinely different ideas:

| Kind | What it encodes | Size | Parameters |
|---|---|---|---|
| **Morgan** (ECFP) | circular fragments radiating from each atom | hashed, 1024–4096 | radius, bits, features |
| **MACCS** | 166 predefined structural keys ("has a sulfonamide") | fixed 167 | none |
| **RDKit** | Daylight-style linear paths through the molecule | hashed, 1024–4096 | bits |

Their bit densities differ enormously on the same molecule (aspirin: Morgan 24
on / MACCS 21 on / RDKit **354** on), which is a good intuition pump — path
fingerprints light up far more bits than circular ones.

## 2. RDKit: use the generator API (most tutorials are outdated)

Nearly every tutorial still teaches:

```python
AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)   # ← don't
```

In RDKit 2026.03 that prints `DEPRECATION WARNING: please use MorganGenerator`.
The current API is `rdkit.Chem.rdFingerprintGenerator`:

```python
gen = rfg.GetMorganGenerator(radius=2, fpSize=2048)
fp = gen.GetFingerprint(mol)
```

**I verified this against the installed RDKit before writing a line of code** —
worth doing whenever an API has a long tutorial tail.

This shape also restates Module 4's performance lesson: the *generator* is the
expensive object. `_bit_vector_builder(options)` constructs it **once per run**
and returns a plain callable the loop reuses. Building one per molecule would
dominate runtime. MACCS is the exception — no generator, no parameters, so
`MACCSkeys.GenMACCSKeys` *is* the callable. Returning a function rather than
branching inside the loop keeps the hot path free of `if`s.

**We keep RDKit's native `ExplicitBitVect`** rather than converting to numpy or
bytes. It is exactly what `BulkTanimotoSimilarity` consumes, so Module 7 gets
C++ speed with zero conversion. A test asserts that call works on our vectors.

## 3. The comparability problem (the real design work)

Two fingerprints may only be compared if they were **built the same way**.
Morgan r=2 and r=3 are different encodings; Tanimoto between them returns a
number that looks perfectly fine and means nothing.

Nothing stops that happening by accident: compute fingerprints, load more
molecules, recompute with a different radius — now the dataset is quietly mixed
and every similarity downstream is silently wrong. **Silent wrongness is the
worst failure mode in this whole project.**

The fix, decided before writing code:

- Every `Fingerprint` **carries the options that produced it**.
- Caching means **"reuse only if the parameters match"** — a natural
  generalization of Module 5's "reuse if present".
- Changed parameters ⇒ recompute, so a dataset can never end up mixed.
- `is_comparable_to()` lets Module 7 assert before trusting a number.

`fingerprints-maccs.png` is the visual proof: after computing Morgan across the
set, recomputing as MACCS reports **"9 computed, 0 reused"** — every row
recomputed rather than reused, because the parameters changed.

### Normalization: identity is only the params that mattered

MACCS ignores radius, bit size and features. So `MACCS(radius=2)` and
`MACCS(radius=5)` produce **bit-identical** vectors and must compare *equal* —
otherwise Module 7 would refuse to compare a perfectly comparable dataset and
the cache would recompute for nothing.

`FingerprintOptions.normalized()` zeroes the parameters that didn't shape the
bits. The stored identity is the *effective* configuration, not the requested
one. Small function, real bug prevented.

## 4. The Qt gotcha this module cost me (StrEnum → QVariant)

`FingerprintKind` is a `StrEnum` — an enum whose members are also `str`, which
makes it serialize straight into a settings file (Module 15) with no conversion.
I stored members directly as combo-box item data:

```python
self._kind.addItem(str(kind), kind)      # store the enum member
...
return self._kind.currentData()          # ← returns a plain str, NOT the enum!
```

Qt stores item data in a `QVariant`. Because a `StrEnum` member *is* a `str`,
the round-trip converts it, and `currentData()` hands back a **plain `str`**.
Every `is` check against it then silently fails:

```python
"MACCS" is FingerprintKind.MACCS    # False
"MACCS" == FingerprintKind.MACCS    # True
```

Symptom: the dialog reported **Morgan whatever the user picked**, and MACCS left
its bit-size box enabled. Caught by driving the dialog headlessly before writing
tests — not by reading the code, which looks obviously correct.

Fixed at two layers, deliberately:

1. **Coerce at the Qt boundary** — `FingerprintKind(self._kind.currentData())`
   restores a real member, so callers get the type the annotation promises.
2. **Use `==` in the model** — `normalized()` and `label` compare by equality,
   so options built from a plain string (Module 15's TOML, or any QVariant trip)
   still behave. For a `StrEnum` this is the idiomatic test; `is` is the fragile
   one.

The service needed no fix: `match options.kind: case FingerprintKind.MACCS:`
uses **value patterns**, which compare with `==` already. Worth knowing that
`match`/`case` is equality-based, not identity-based.

A regression test (`test_selected_kind_is_a_real_enum_member_not_a_string`)
pins this so it cannot come back.

## 5. GUI wiring

- **`FunctionWorker` again** — the *fifth* consumer of the Module 2 worker.
  Same `progress` shape, so it dropped onto a background thread with no new
  infrastructure.
- **`FingerprintDialog`** reuses Module 4's static-factory idiom
  (`get_options() → Options | None`). New wrinkle: its controls **depend on each
  other**. Radius and features are Morgan-only; bit size is meaningless for
  MACCS. Rather than let users set values that get silently ignored, the kind
  selector drives an enable/disable pass, so the dialog can only express option
  sets that mean something. `fingerprint-dialog.png` shows the Morgan state.
- **The column shows a summary, not the vector.** A 2048-bit vector isn't
  displayable, so the cell reads `Morgan · 24 on`: proof the compute ran, which
  algorithm each row carries (this *matters* — mismatched params break
  similarity), and a mild complexity signal. The **cell tooltip** carries full
  parameters (`Morgan r2 · 2048b · 2048 bits total`).
- **Sorting is by on-bit count, not text** — `"9 on"` must precede `"24 on"`,
  which string ordering gets backwards. A test pins it.
- **Column placement**: the fingerprint column sits between the descriptor block
  and Source, so `_SOURCE_COLUMN` shifted. `_is_descriptor_column` had to change
  from `< _SOURCE_COLUMN` to `< _FINGERPRINT_COLUMN` — a quiet trap, since
  getting it wrong would have made the fingerprint column render as a descriptor.
  A test pins that Source stays last.

### A small refactor while here

Three operations now disable the same action set on start and re-enable on
finish; the fourth would have made four copies of that list. Extracted
`_set_actions_busy(busy)` + `_begin_run(total, message)`, and folded the
existing standardize/descriptor handlers into them. Adding Module 7's similarity
run is now a one-line change instead of a fourth copy to keep in sync.

## 6. Verification (actually run)

- `pytest`: **102/102 passing** (was 70). New: 20 fingerprint tests (all three
  kinds, bit sizes, radius/features changing the bits, normalization for each
  kind, plain-string options, caching reuse/recompute-on-param-change, progress,
  comparability, Tanimoto identity=1.0, `BulkTanimotoSimilarity` on our vectors),
  8 dialog tests (incl. the StrEnum regression), 5 table tests (blank-until-
  computed, summary text, numeric sort key, cell tooltip, Source-stays-last).
- `-W error::DeprecationWarning`: clean.
- `ruff` + `black`: clean first pass.
- **Screenshots** through the real `MainWindow`: the options dialog, Morgan
  across the demo set, and the MACCS recompute proving "9 computed, 0 reused".

## 7. Research lens

Honest read: **also table stakes.** ECFP is from 2010 and universally
implemented; wrapping it is not novelty.

The genuinely interesting thread here is **bit collisions**. Hashed fingerprints
fold an unbounded fragment space into 2048 bits, so distinct fragments *share*
bits — and essentially every published similarity number silently absorbs that
error. The collision rate is measurable (we have the machinery: compute at 1024
vs 4096 and compare), rarely reported, and interacts with dataset size in ways
that are not well characterized. A study quantifying **how much collision noise
moves real virtual-screening rankings**, plus a cheap diagnostic for when your
bit size is too small for your library, would be a real contribution.

That is a stronger idea than Module 5's parked one and shares its machinery.
Still behind Module 4's standardization-divergence benchmark in my ranking, but
worth revisiting after Module 7 gives us ranking metrics to measure against.

## 8. What's next

Module 7 — **Similarity Search**. The payoff: pick a query molecule, Tanimoto it
against the dataset with `BulkTanimotoSimilarity`, sort by score, show the
neighbours. It will assert dataset comparability via `is_comparable_to` before
trusting any number, and it needs a real design conversation about *where the
results live* (a new sortable column? a separate ranked panel? a filter?).
