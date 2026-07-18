# Module 8 — Scaffold Analysis · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`
> and the three screenshots in this folder.

---

## 1. What we built

Bemis–Murcko **scaffold analysis**: reduce each molecule to its core ring
systems + linkers, then group the dataset by shared scaffold to reveal
**scaffold diversity**. Two surfaces:

1. A cached **Scaffold column** in the molecule table (sortable — so sorting
   *is* grouping, keeping the flat table intact).
2. A **Scaffolds dock panel** — the analytical inversion: one row per scaffold,
   ranked by member count, rendered as thumbnails, with a diversity headline and
   a click-to-filter interaction.

On the demo set: **15 molecules → 5 scaffolds** (Murcko), or **→ 4** under the
generic framework (benzene and pyridine cores merge). See the screenshots.

## 2. The design decision, and why

The brief flagged this as "the first grouping feature" and asked whether the
scaffold should be a per-record field + column, or a separate tree/group view.
The instruction on record was: *do what's best per industry standard.* The call:

**Both a cached per-record field AND a grouping panel — one compute, two views.**

- The per-molecule scaffold is cached exactly like descriptors/fingerprints
  (`record.scaffold`), shown in a **sortable column**. Because the table already
  sorts, sorting that column clusters members of the same scaffold together —
  *grouping without a tree view*. This is what keeps the "first grouping
  feature" from forcing an architectural change to the flat table.
- The **Scaffolds dock** is the real analytical payload: diversity stats + a
  frequency-ranked, thumbnail-rendered list. This is what tools like DataWarrior
  show, and it is where scaffold analysis earns its name.

**No options dialog** (unlike fingerprints). Both scaffold representations are
cheap and computed together in a single pass, so there is nothing to configure
at compute time — this follows the *descriptors* pattern (a plain menu action).
The exact-vs-generic choice is a **view** preference, so it lives as a toggle
**in the panel**. Compute once, view either way. Making it a compute option
would have meant recomputing to switch — strictly worse.

## 3. RDKit: the scaffold toolbox

`rdkit.Chem.Scaffolds.MurckoScaffold`:

| Call | Result |
|---|---|
| `GetScaffoldForMol(mol)` | exact Murcko scaffold (ring systems + linkers, side chains stripped) |
| `MakeScaffoldGeneric(scaffold)` | the generic framework: every atom → carbon, every bond → single |

**The acyclic edge case is the one that matters.** A molecule with no rings
(ethanol, hexane, acetic acid) has *no* scaffold — `GetScaffoldForMol` returns
an **empty molecule** (`GetNumAtoms() == 0`). We surface this honestly as
`has_ring_system=False` with empty SMILES, display it as `(acyclic)`, and
collect all such molecules into one group keyed by `""`. A tool that crashed or
fabricated a scaffold here would be quietly wrong on a huge fraction of real
fragment/reagent sets. There is a dedicated test for it.

**Why exact ≠ generic matters (a real result in the screenshots):** benzene and
pyridine are *different* exact Murcko scaffolds but the *same* generic framework
(both are an all-carbon six-ring). So Murcko grouping gives 5 groups and generic
gives 4 — the generic view is deliberately coarser. Both are one representation
switch apart because both SMILES are cached on every record.

## 4. Software design (the shared seam, again)

- **Model in `models`, computation in `services`.** `ScaffoldResult` /
  `ScaffoldRepresentation` are models because `MoleculeRecord.scaffold`
  references them and models may not import services. The RDKit work
  (`compute_scaffolds`, `group_scaffolds`) is the service. Fifth module to prove
  the pattern.
- **Cache in place, don't swap.** `compute_scaffolds` fills `record.scaffold`
  and the table repaints just the scaffold column (`scaffolds_updated`) —
  scroll and selection survive. Same discipline as descriptors, opposite of the
  standardizer (which changes chemistry, so it builds new records).
- **A report, not just results** — `ScaffoldReport` carries computed/reused
  counts and per-molecule failures; one bad molecule never aborts the run.
- **Grouping returns fresh objects.** `group_scaffolds` is a read-only view over
  records, ranked by `(-size, key)` so the common cores lead and ties are
  stable.

## 5. The panel is intent-only (the seam that keeps layers clean)

`ScaffoldPanel` owns no worker and no RDKit. It renders groups it is handed and
emits **intent**: `scaffold_selected(group)` and `representation_changed(rep)`.
`MainWindow` — which owns the records, the worker, and the table — decides what
to do. This is identical to how the table emits `similarity_requested` rather
than running a search itself. A panel that reached into services would be the
first crack in the layering.

## 6. Filtering: a second AND-ed channel, not the text box

Clicking a scaffold filters the table to its members. The obvious shortcut —
stuffing `scaffold:<smiles>` into the quick-filter box — was rejected: a
scaffold SMILES is not something a human reads or types, and it would pollute
the box the "one grammar" philosophy is about. Instead the proxy grew a
**second filter channel** (`set_scaffold_filter`) that **ANDs** with the text
query. So "this scaffold" and "…with `MW < 500`" can both be true at once
(there is a test for exactly that). The channels are independent: clearing the
text box does not clear the scaffold selection, and vice versa.

Switching representation **clears** any active scaffold filter, because the
group keys differ between Murcko and generic — a filter chosen under one is
meaningless under the other, so silently keeping it would match the wrong rows.

## 7. A stale-state trap we closed

Standardization replaces the dataset with *new* records whose `scaffold` is
`None`. Left alone, the Scaffolds panel would still show groups pointing at the
old, deleted records, and an active scaffold filter would hide every new row.
`_on_standardize_finished` calls `_reset_scaffold_view()` to clear the panel and
the filter. Cross-feature interactions like this — where operation A invalidates
feature B's cached view — are where desktop apps accumulate ghost bugs; worth
being deliberate about.

## 8. Verification (actually run)

- `pytest`: **194 tests passing** (was 173) — scaffold service (ring/acyclic,
  exact≠generic, generic-merges-heteroatoms, cache-in-place/reuse, recompute,
  grouping ranks + skips uncomputed, progress), the panel (placeholder, populate,
  selection emits group, show-all emits None, representation toggle), and table
  integration (blank-until-analysed, acyclic marker, representation follows
  toggle, scaffold filter restricts + ANDs with text).
- Clean under `ruff`, `black`, and `-W error::DeprecationWarning`.
- **Screenshots** (this folder): the ranked scaffold panel, a click-to-filter
  result, and the coarser generic grouping in light theme.

## 9. Research lens

Scaffold analysis is textbook — but it unlocks a genuinely publishable question,
and it is *not* a GUI wrapper:

- **Gap:** Bemis–Murcko is the default scaffold definition everywhere, yet it is
  known to over-merge (all six-membered aromatics become one generic ring) and
  over-split (a single heteroatom swap makes a "new" scaffold). There is no
  widely-adopted, open, *tunable* middle ground that a bench chemist can steer.
- **Novel contribution:** a **parameterised scaffold abstraction ladder** — a
  family of scaffold definitions between "exact Murcko" and "generic framework"
  (e.g. preserve aromaticity but not element; preserve ring size but not
  heteroatom position), plus a **diversity-stability metric** measuring how a
  library's scaffold count changes along that ladder. A library whose diversity
  collapses immediately under mild abstraction is "brittle"; one that holds is
  genuinely diverse.
- **Experiments:** run the ladder over public sets (ChEMBL targets, DrugBank,
  a fragment library); correlate the stability metric with known
  scaffold-hopping success. **Metrics:** scaffold count vs abstraction level,
  area-under-the-diversity-decay-curve, rank correlation with medicinal-chemistry
  diversity judgments.
- Wawekit is the vehicle: `ScaffoldRepresentation` is already an enum with two
  rungs — the ladder is more rungs of the same abstraction, and the panel
  already visualises the count at each. This still ranks behind Module 4's
  standardization-divergence benchmark, but it is the most concrete new idea
  since.
