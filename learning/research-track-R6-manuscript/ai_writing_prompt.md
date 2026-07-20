# AI writing-collaborator prompt (filled)

Paste everything between the `---BEGIN---` / `---END---` markers into a fresh AI
session. It is self-contained: the assistant does **not** need repository access.

To draft a different section, change the one bracketed instruction in the
"Your task" paragraph (`Introduction` → `Methods` or `Results`). Everything else
stays as-is.

All figures below were re-verified against a live benchmark run on 2026-07-20
after a round of metrics bug-fixes; see "Provenance and known caveats" at the
end, which is deliberately part of the prompt so the assistant cannot overstate
the work.

---BEGIN---

I'm writing a cheminformatics paper for submission to the **Journal of
Cheminformatics** (primary target; a Frontiers methods/tools title is the
fallback venue).

The tool is **WaweKit**, an open-source (MIT) desktop cheminformatics toolkit
built on RDKit and PySide6. The component this paper is about is its
**standardization-reproducibility auditor**: it runs several structure-
standardization protocols over the same dataset, quantifies how often they
disagree about a molecule's standardized identity, and attributes each
disagreement to the specific normalization operation responsible.

Here is my real material — methods and results, verbatim from the
implementation and from an actual benchmark run. Nothing here is estimated or
projected.

## Problem framing (established, not a result of mine)

Structure standardization — normalizing salts, charge states, tautomers, and
stereochemistry to a canonical form — is a mandatory preprocessing step in
essentially every cheminformatics pipeline. The *protocols* used to perform it
vary across tools, organizations, and even between configurations of a single
toolkit. Existing tools (RDKit's `rdMolStandardize`, the ChEMBL structure
curation pipeline, MolVS) provide standardization *implementations*, each
encoding one set of choices. To my knowledge none provides a way to measure how
much two protocols disagree, on which molecules, or why. That is the gap this
work addresses.

## Methods

### Composable protocol model

A standardization **protocol** is defined as a named subset of eight operations,
applied in a fixed, chemically motivated order:

1. Metal disconnection (`MetalDisconnector`)
2. Functional-group normalization (`Normalizer`)
3. Reionization (`Reionizer`)
4. Parent-fragment selection (`LargestFragmentChooser`) — salt/solvent stripping
5. Charge neutralization (`Uncharger`)
6. Isotope removal
7. Stereochemistry removal
8. Canonical tautomer selection (`TautomerEnumerator.Canonicalize`)

A protocol is the *subset* it enables; application order is always the fixed
sequence above. Two protocols therefore differ only in *which* operations run,
which is what makes their outputs directly comparable and any single operation's
effect isolable.

Three representative protocols were used:

- **Minimal** — normalization only (operation 2); a light-touch baseline.
- **ChEMBL-like** — operations 1–5, notably *without* tautomer canonicalization;
  approximates the published ChEMBL structure curation pipeline.
- **Aggressive** — all eight operations.

### Dual-identity divergence measure

For each standardized molecule two identity representations are recorded:

- **Canonical SMILES** (RDKit `MolToSmiles`) — sensitive to any structural
  change, including tautomer choice.
- **InChIKey** (`MolToInchiKey`) — applies InChI's own internal normalization
  layers, including tautomer canonicalization for a defined set of tautomer
  classes, independently of the protocol's operations.

**Agreement** under an identity convention means all protocols produced an
identical value. A molecule is **labile** if it disagrees under *either*
convention. Both conventions are reported separately because they can disagree
with each other about whether a molecule is reproducible (see Results).

A protocol that *fails* on a molecule (RDKit rejects an intermediate) is
recorded as a failure and excluded from the agreement computation for that
molecule — a failure is not evidence of divergence. In the benchmark reported
here there were **zero** such failures: all 40 molecules produced a valid
InChIKey under all three protocols.

### Ablation-based cause attribution

For each labile molecule, the most operation-rich protocol in the comparison set
is identified and, for each of its enabled operations (evaluated in reverse
application order), the molecule is re-standardized with that single operation
disabled. If disabling an operation changes the resulting identity (InChIKey
preferentially, then canonical SMILES) relative to the full protocol's output,
that operation is recorded as an implicated cause. Cost is one additional
standardization per enabled operation per labile molecule, bounded because at
most eight operations exist.

### Dataset-level metrics

- **Reproducibility score** (per identity convention) — fraction of molecules on
  which all protocols agree.
- **Pairwise agreement** — for each protocol pair, the fraction of molecules on
  which that pair individually agrees. Computed only over molecules where both
  protocols in the pair produced a valid identity.
- **Cause spectrum** — among labile molecules, the fraction implicating each
  operation. Sums to more than 1.0 in general, since one molecule can implicate
  several operations.

### Implementation

Python 3.13.2, RDKit 2026.03.4. The entire measurement pipeline (protocol
engine, divergence analysis, metrics, command-line benchmark harness) is
implemented as pure services with no dependency on the application's GUI layer,
covered by 39 unit tests. An interactive graphical front-end additionally
provides a protocol-agreement heatmap, a cause-spectrum chart, and an
inspectable list of labile molecules. Both interfaces share the identical
underlying computation. Released under the MIT license.

## Results

### Finding 1 — the two identity conventions disagree about reproducibility

For 2-hydroxypyridine, enabling canonical-tautomer selection changes the
canonical SMILES output (`Oc1ccccn1` → `O=c1cccc[nH]1`) but leaves the InChIKey
**unchanged**, because InChI's own normalization already collapses this tautomer
pair. A molecule can therefore be flagged as pipeline-dependent under one
identity convention and fully reproducible under the other. The two conventions
are not interchangeable proxies for "the same molecule."

This was found empirically, from a failing unit test written on the assumption
that the two would agree — it was not anticipated in the study design.

### Finding 2 — illustrative benchmark (40 molecules, 3 protocols)

Benchmark set: 40 molecules spanning drug-like structures, salts, charged
species, tautomer-ambiguous heterocycles, isotopically labelled compounds, and
stereocenters. Runtime 0.1 s (~344 molecules/s).

| Metric | Value |
|---|---|
| Molecules analyzed | 40 |
| SMILES reproducibility (all 3 protocols agree) | 70.0% |
| InChIKey reproducibility (all 3 protocols agree) | 75.0% |
| Labile molecules | 12 / 40 (30.0%) |
| Molecules with a protocol failure | 0 |

Pairwise InChIKey agreement:

| Protocol pair | Operations differing | Agreement |
|---|---|---|
| ChEMBL-like vs. Aggressive | 3 | 90.0% |
| Minimal vs. ChEMBL-like | 4 | 85.0% |
| Minimal vs. Aggressive | 7 | 75.0% |

Divergence cause spectrum (fraction of the 12 labile molecules implicating each
operation):

| Operation | Fraction of labile molecules |
|---|---|
| Charge neutralization (`uncharge`) | 41.7% |
| Parent-fragment selection (`fragment_parent`) | 33.3% |
| Isotope removal | 16.7% |
| Canonical tautomer selection | 16.7% |

Two observations I draw from this, both of which should be stated as
observations on this set rather than general claims:

- Agreement decreases monotonically as the number of differing operations
  increases (3 → 90.0%, 4 → 85.0%, 7 → 75.0%).
- Charge and salt/fragment handling jointly account for roughly three quarters
  of observed divergence — ahead of the more heavily discussed
  tautomer-canonicalization problem.

## Provenance and known caveats (please respect these)

- The 40-molecule set is **illustrative, not representative**. It was assembled
  deliberately to span structural classes hypothesized to be labile, so the
  30% lability rate and the cause ranking are almost certainly **not**
  generalizable population estimates. Scaling to stratified public subsets
  (ChEMBL / PubChem / DrugBank) is planned but **not yet done**. Do not phrase
  any finding as though it characterizes public chemical databases.
- The cause-attribution procedure can only attribute divergence among *these
  eight* operations. It cannot detect divergence originating outside that set
  (e.g. a different aromaticity model, a different tautomer scoring function, or
  an entirely non-RDKit standardizer).
- The "no prior work does this" claim in the problem framing is my current
  belief, not the result of a systematic literature search. Treat it as a claim
  requiring verification, not an established fact.
- All numbers above were re-verified against a live run after a round of
  metrics bug-fixes; earlier drafts of this material circulated with the same
  figures, which the fixes did not change for this dataset.

## Your task

Please act as a cheminformatics-savvy scientific writing collaborator. Draft the
**[Introduction]** section based only on the material I've given you — don't
invent results, numbers, or claims. Where literature context would strengthen
the section, tell me what claim needs a citation, and I'll have you search for
real, verifiable papers rather than generate references from memory. Match the
tone and rigor of the *Journal of Cheminformatics* — formal, precise, no hype
language.

Specifically:

- Do not write "novel", "powerful", "comprehensive", or "first-ever". If a
  contribution is genuinely new, let the specificity of the claim carry it.
- Keep hedging proportional to evidence: findings from a 40-molecule
  illustrative set must not be worded as general properties of chemical
  databases.
- Where you need a citation, insert `[CITATION NEEDED: <the specific claim>]`
  inline and collect the list at the end. Do not produce author-year strings,
  DOIs, or titles from memory under any circumstances.
- If any part of my material is too thin to support the section you're drafting,
  say so and tell me what additional information or experiment you need, rather
  than filling the gap with plausible-sounding text.

---END---
