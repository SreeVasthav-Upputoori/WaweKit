# Module 12 — Substructure Search · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`
> and the two screenshots in this folder.

---

## 1. What we built

**Find molecules that contain a fragment, and show *where*.** A SMARTS (or
SMILES) query is matched against every molecule; matches are counted in a new
**Substructure column** and — the milestone of this module — the **matched atoms
are highlighted** in both the table thumbnails and the big Structure panel. The
screenshots show a pyridine query lighting up the pyridine ring in the three
pyridines (salmon), leaving the benzene-containing molecules unmarked, with the
column reading `✓` / `—`.

This is the **first feature that enhances the 2D renderer** — every prior module
consumed `render_svg` as-is; this one extends it.

## 2. The renderer change (small, shared, careful)

`render_svg` gained one optional parameter, `highlight_atoms`. When present it:

- computes the **bonds whose both ends are in the atom set** (`_bonds_within`),
  so a matched ring reads as one solid region rather than scattered dots, and
- passes `highlightAtoms` + `highlightBonds` to `PrepareAndDrawMolecule`.

Two disciplines held: the input mol is still **never mutated** (we draw a copy —
there's a test), and the default path (no highlight) is byte-for-byte unchanged.
Because the renderer lives in `services` and is shared, this one change lit up
*both* the thumbnails and the Structure panel with no per-widget drawing code.

## 3. Highlighting through the thumbnail cache (the neat part)

The `StructureDelegate` caches rendered thumbnails. Naively, adding highlights
would show stale (un-highlighted) images after a search. The fix is to **fold
the match into the cache key**:

```
key = (record.smiles, sorted matched-atom tuple or None)
```

So a molecule caches *separately* with and without a highlight. A new search
changes the matched atoms → new key → the thumbnail re-renders highlighted;
clear the query → the key reverts → the plain image is served straight from
cache. No explicit cache-clearing, no stale frames — the invalidation falls out
of the key. (Theme changes still clear the whole cache, as before.)

## 4. A match is relational — same discipline as similarity/cluster

Whether a molecule matches, and which atoms, depends on the *query*. So — the
third time this pattern appears — a `SubstructureHit` **carries its
`SubstructureQuery`**, is cached on the record, and is **actively cleared** when
a fresh search can't handle a molecule. A record searched-but-not-matched gets a
hit with empty `matches` (shown as `—`), distinct from a never-searched record
(blank) — an honesty distinction the sort respects (unsearched sinks below
no-match below matches).

## 5. SMARTS vs SMILES, and live validation

The dialog offers **SMARTS** (the query language — atom/bond primitives,
wildcards, recursion; e.g. `[NX3][CX3](=O)` for an amide) or plain **SMILES**
read as a query. It **validates on every keystroke** through
`substructure.parse_query` (which mutes RDKit stderr and returns `None` rather
than raising), so the Search button is disabled until the pattern parses — the
mistake is shown next to the box, not after the dialog closes. As always, the
dialog imports no RDKit; parsing is a service call.

## 6. Filtering: the fourth AND-ed channel, and a refactor

Substructure adds "show only matches" as a filter. Rather than nest a third
`if` in the proxy, this was the moment to **refactor** `filterAcceptsRow` to
iterate over the active channels:

```python
return all(channel.matches(record) for channel in self._active_channels())
```

So text + scaffold + substructure now combine cleanly, and a fifth channel later
is one line. The filter is cleared on standardize (new records match nothing, so
leaving it on would blank the whole table — a trap closed deliberately).

## 7. Reuse tally

`render_svg`, `StructureDelegate`, `StructureViewerPanel`, the filter proxy, the
worker, the cached-column machinery, the `parse_smiles`→`parse_query` mute-stderr
idiom, the live-validation dialog pattern — all reused or minimally extended.
The only genuinely new surface is the highlight itself.

## 8. Verification

- `pytest`: **232 tests** (was 221) — query parsing (SMARTS vs SMILES, garbage),
  match flagging + atom recording, multi-match counting, a SMARTS amide query,
  invalid-query raising, stale-clear on re-run, display/tooltip, progress; plus
  two renderer tests (highlight changes the drawing; highlight doesn't mutate
  input). Clean under `ruff`, `black`, and `-W error::DeprecationWarning`.
- Screenshot-verified: pyridine highlighted in thumbnails + Structure panel;
  the `✓`/`—` column.

## 9. Research lens

Substructure matching is a solved primitive — but two threads it enables are
publishable, and build on what the app now holds:

- **Privileged-substructure / SAR mining across the loaded set.** With matches,
  clusters (Module 11) and an activity column (SDF properties), the app is one
  analysis from **automatically surfacing substructures enriched in the active
  subset** — a data-driven pharmacophore finder. The matched-atom highlighting
  is already the delivery vehicle for showing what it finds.
- **A benchmark of SMARTS-query ambiguity.** Chemists routinely write SMARTS
  that match more (or less) than intended (aromaticity models, implicit-H, ring
  membership). A curated set of "intended vs actual match" cases, with a
  diagnostic that flags a query whose matches are sensitive to the aromaticity
  perception model, is a genuinely useful, citable contribution — and our
  highlighting makes the discrepancies visible for validation.

Both still rank behind Module 4's standardization-divergence benchmark, but the
privileged-substructure mining is now only a join away from being prototyped.
