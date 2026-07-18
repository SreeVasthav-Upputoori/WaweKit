# Module 13 — Batch Processing · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`
> and the two screenshots in this folder.

---

## 1. What we built

**Run a whole pipeline over the dataset from one dialog, unattended, and export
the result.** Tick the steps — standardize → descriptors → fingerprints →
scaffolds → cluster — choose CSV or SDF output, hit Run, and the app chains every
operation, fills every column, writes the file, and can be **cancelled** while it
works. The screenshots show the checklist dialog and the finished result: every
descriptor column populated and "exported 16 to batch_results.csv".

## 2. The payoff of eleven modules of discipline

This module is almost entirely **composition**, and that is the point. Every
chemistry service was built to the same shape — Qt-free, a `progress` callback, a
report — so chaining them is trivial: `run_batch` is a loop over a list of
`(label, step)` where each step calls one existing service. And every options
object was a **frozen dataclass / StrEnum**, so a `BatchConfig` is just those
objects in a container — a pipeline you can inspect now and (Module 15) save to a
file. The recurring "why is this frozen and serializable?" from Modules 4–12 is
answered here: *so a batch can hold it as a recipe.*

Also new, and reused onward: an **export service** (`services/io/molecule_exporter.py`)
— CSV (identity + descriptors + annotations, blanks for uncomputed) and SDF
(molecules + computed values as SD tags, set on a *copy* so `record.mol` is never
mutated). Module 14's report generator will build on it.

## 3. Fixed order, not a reorderable list

The pipeline order is **fixed**: standardize first (it *replaces* records — nothing
measured before it would survive), annotations next, export last. A reorderable
step-list UI would be more flexible and much more complex, and most invalid orders
are chemically meaningless anyway. So the config is a set of flags/options in the
one sensible order — a clean v1 that covers the real use case. The runner reassigns
`records = report.records` after standardization so later steps see the new objects.

## 4. Cancellation — and why `BatchCancelled(BaseException)`

A batch is the first operation long enough to want stopping, so it is the first
**cancellable** one. The GUI sets a `threading.Event`; the runner checks it
between steps and — through a wrapped progress callback — *within* a step at each
progress tick, raising `BatchCancelled` to unwind.

The subtle, load-bearing decision: **`BatchCancelled` derives from `BaseException`,
not `Exception`.** Every chemistry service wraps each molecule in `except Exception`
so one bad structure can't abort a run. If cancellation were an `Exception`, a
progress callback raising it *inside* such a loop (the standardizer calls progress
inside its dedup branch, for instance) would be **caught and recorded as a bad
molecule** instead of stopping the batch. `BaseException` (the `KeyboardInterrupt`
family) sails straight through those handlers; only `run_batch`, which catches it
explicitly, stops — returning a partial, `cancelled=True` result. There are two
tests for exactly this (pre-set cancel; cancel after the first tick).

Cancellation is **coarse** — it takes effect at the next progress tick or step
boundary, not instantly mid-molecule. That is honest and enough; finer would mean
threading a cancel token through every service, which the `BaseException`-via-progress
trick avoids entirely (no service changed).

## 5. GUI: a non-modal cancel, and shared reset

- A **Cancel button** lives in the status bar, hidden until a batch runs. It sets
  the event; the run stops and reports how far it got. Non-modal, so the window
  stays responsive.
- Because a batch may **replace** the records (standardization), `_on_batch_finished`
  calls `set_records` and then `_reset_derived_views()` — a helper **extracted from
  the standardize handler** (which now shares it). Both operations invalidate the
  same downstream state (projection, conformers, scaffold grouping, substructure
  filter), so they should reset it the same way. Extracting on the second caller,
  not the first — the same rule the fingerprint-options widget followed.

## 6. Verification

- `pytest`: **245 tests** (was 232) — the runner (all steps run + cache, standardize
  replaces records, CSV/SDF export, empty config, cumulative monotonic progress) and
  **cancellation** (pre-set event stops immediately; mid-run cancel after the first
  tick), plus the exporter (header + row-per-record, blanks for uncomputed, computed
  descriptors written, SDF round-trips tags, SDF doesn't mutate the record). Clean
  under `ruff`, `black`, and `-W error::DeprecationWarning`.
- Screenshot-verified: the dialog, and a full pipeline run populating every column
  with a CSV written to disk.

## 7. Research lens

Batch processing is plumbing — but it is the substrate two publishable ideas need,
and both are now one step away:

- **A reproducible cheminformatics-pipeline provenance record.** A `BatchConfig` is
  a complete, serialisable description of *what was done* to a dataset. Emitting it
  (plus tool versions) alongside the export turns Wawekit runs into **reproducible
  artifacts** — the thing most published cheminformatics analyses lack. The
  standardization-divergence benchmark (Module 4's parked idea) becomes trivially
  runnable as a batch across pipelines once configs are saved (Module 15).
- **Pipeline-order sensitivity.** Because steps compose, one can *measure* how much
  the final annotations shift when defensible orders or options change (e.g.
  standardize-then-fingerprint vs not). A systematic study of how sensitive
  downstream results are to pipeline choices — with this app as the controlled
  harness — is a concrete methodological contribution.

Both still trail Module 4's benchmark, but the provenance record is now genuinely
imminent: the config already exists as a serialisable object.
