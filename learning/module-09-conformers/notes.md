# Module 9 — Conformer Generation · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`
> and the two 3D screenshots in this folder.

---

## 1. What we built

The first **3D** feature. From a flat 2D structure we generate realistic 3D
shapes: **embed** with ETKDGv3 → **optimise** with a force field → **rank** by
energy → **prune** near-duplicates by RMSD. Results show in a new Conformers
dock: an **interactive 3D viewer** (rotate/zoom, real WebGL) over a per-conformer
energy/ΔE/RMSD table, with **SDF export**. Screenshots show ibuprofen's 6
conformers spanning a 1.50 kcal/mol energy range.

## 2. The decision you made: 3Dmol.js in QWebEngine

Qt has no native 3D molecule widget, so *how to display 3D* was a real fork with
a lasting dependency implication — I asked rather than deciding it silently. You
chose the interactive **3Dmol.js-in-QWebEngine** route. What that meant:

- **Vendored, fully offline.** `3Dmol-min.js` (525 KB, BSD-3) is committed under
  `resources/web/` and *inlined into the page*, so the viewer needs no internet
  and no CDN — matching the project's self-contained discipline. Attribution is
  in `resources/web/NOTICE-3Dmol.txt` and the README.
- **Load once, update cheaply.** The heavy script loads a single time when the
  widget is built; each conformer is shown by calling a tiny JS function
  (`wawekitLoad`) with that conformer's MDL mol block. Reloading the page per
  click would re-parse half a megabyte every time.
- **Async-safe.** The page loads asynchronously, so a mol block requested before
  `loadFinished` is held in `_pending` and applied when the page is ready.

Tradeoff accepted: QtWebEngine is a heavy runtime and will need care when we
package with PyInstaller (Module 17). Noted for later; it's a well-trodden path.

## 3. RDKit: the 3D pipeline

| Step | Call | Why |
|---|---|---|
| Add hydrogens | `Chem.AddHs` | 3D geometry is meaningless without them |
| Embed | `EmbedMultipleConfs` + `ETKDGv3` | knowledge-based torsions → realistic starts; `pruneRmsThresh` drops near-duplicates during embedding |
| Optimise | `MMFFOptimizeMoleculeConfs` / `UFFOptimizeMoleculeConfs` | relax geometry, get energies (kcal/mol) |
| Rank / compare | `rdMolAlign.GetBestRMS` | symmetry-aware RMSD of each conformer to the lowest-energy one |

**Reproducibility:** ETKDG takes a `randomSeed`, exposed in the dialog, so a run
is repeatable — important for a research-grade tool.

**The MMFF fallback (a real robustness point):** MMFF94 is the better force field
for drug-like organics but requires parameters for *every* atom; some elements
lack them. Rather than failing the molecule, `_optimise` checks
`MMFFHasAllMoleculeParams` and falls back to **UFF** (which covers the whole
periodic table). The `ConformerSet` records `force_field_used`, so the panel
shows the truth — "MMFF94" or "UFF" — never a silent substitution.

## 4. The new design rule: 3D lives *beside* the record, not *on* it

Every prior derived result (descriptors, fingerprint, scaffold) was a small value
cached on the record. 3D is different: it is a whole *molecule* — with explicit
hydrogens and many conformers. The rule this module introduces:

**The 3D geometry lives on `ConformerSet.mol_3d`, a separate molecule — it is
never written back onto `record.mol`.**

Two reasons: (1) the 2D table thumbnail and Structure panel depict `record.mol`;
a hydrogen-decorated 3D mol would render there as a cluttered mess. (2) A
record's identity is its 2D structure; conformers are a derived 3D *view*. So the
record still gains just one field (`record.conformers`), in the same cache
discipline — but the heavy geometry it points to is a distinct object. There's a
test (`test_mol_3d_has_hydrogens_and_is_separate_from_input`) pinning exactly
this.

## 5. Why generation runs on the *selection* first

Every earlier Chemistry operation ran on the whole dataset. Conformer generation
is far heavier (distance geometry + force-field optimisation, per molecule, ×N
conformers), so `_on_generate_conformers` runs on the **selection** when there is
one, falling back to the whole dataset only when nothing is selected. The status
bar says which scope ran. This is the first operation where "the whole dataset"
is a genuinely expensive default, so it earns the refinement.

## 6. The Conformers panel

- **Follows the table selection** (like the Structure panel): select a molecule
  with conformers → its ranked list appears and the lowest-energy one renders in
  3D. Select one without → a placeholder.
- **Energy table**: conf id, energy, ΔE (above the minimum), RMSD to lowest.
  Clicking a row loads that conformer into the 3D view.
- **Export SDF** writes every conformer with its coordinates — the honest handoff
  to PyMOL/Maestro/docking, and why 3D is useful even beyond the viewer.
- **Emits no signals**: it is a pure consumer of the selection; its one outward
  action (export) is a self-contained file write. Same clean seam as the others.

## 7. Testing a web-backed feature

QWebEngine can't run under the offscreen Qt platform the test suite uses, and a
WebGL viewer is inherently an integration concern. So the split:

- **Unit-tested** (headless): the model (`ConformerSet`, energies, SDF/mol-block
  serialisation), the service (ranking, MMFF/UFF, cache-in-place, reuse,
  progress), and the options dialog. 11 new tests.
- **Screenshot-verified**: the 3D viewer itself, captured through a *real* event
  loop (not offscreen) with a timed grab, because WebGL renders asynchronously —
  a `processEvents` spin would grab a blank frame. The dark/light screenshots are
  the proof the WebGL surface composites correctly and the theme background
  switches.

Total: **205 tests**, clean under `ruff`, `black`, and `-W error::DeprecationWarning`.

## 8. Research lens

Conformer generation is mature, but two genuinely open, publishable threads sit
right here — and neither is a GUI wrapper:

- **Ensemble-sufficiency diagnostic.** Everyone picks `n_confs` by folklore (50?
  200?). A principled, cheap **convergence signal** — "the low-energy basin has
  stopped changing, stop embedding" — measured as the stability of the ranked
  RMSD/energy set as conformers accumulate, would replace guesswork. Wawekit
  already computes exactly the per-conformer energy+RMSD data such a metric needs.
- **Force-field-disagreement flag.** MMFF and UFF often *reorder* the low-energy
  conformers. Quantifying, across public flexible-molecule sets, how often the
  chosen force field changes which conformer is "best" — and flagging molecules
  where it does — is a concrete reliability contribution. Our `force_field_used`
  plumbing and SDF export make the cross-run comparison straightforward.

Both still rank behind Module 4's standardization-divergence benchmark, but the
force-field-disagreement flag is unusually tractable given what this module
already produces.
