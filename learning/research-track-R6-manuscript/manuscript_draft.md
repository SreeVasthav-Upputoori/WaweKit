# Quantifying and Attributing Standardization Reproducibility in Cheminformatics Pipelines

**Draft manuscript — working title.** Target venue: *Journal of Cheminformatics*
(primary) or a Frontiers methods/tools title (secondary). This is a drafting
scaffold populated with real (illustrative-scale) results from the Wawekit
implementation; a submission-ready version requires scaling the benchmark to
public datasets (§Methods, "Scaling to publication scale").

---

## Abstract

Molecular structure standardization — normalizing salts, charge states,
tautomers, and stereochemistry to a canonical form — is a mandatory
preprocessing step in essentially every cheminformatics pipeline, yet the
*protocols* used to perform it vary across tools, organizations, and even
individual settings within one toolkit. We introduce a measurement framework
that treats standardization **reproducibility** as a first-class, quantifiable
property of a dataset rather than an implicit assumption. Given a set of
standardization protocols, our method (1) determines whether they agree on each
molecule's standardized identity, evaluated under **two** common identity
conventions (canonical SMILES and InChIKey) that we show can disagree with each
other; and (2) attributes each disagreement to a specific normalization
operation via systematic **ablation**. Applied to an illustrative 40-molecule
benchmark spanning salts, charged species, tautomer-ambiguous heterocycles,
isotopes, and stereocenters, three representative protocols (Minimal,
ChEMBL-like, Aggressive) agreed on only 70.0% of molecules under SMILES identity
and 75.0% under InChIKey identity, with charge handling (uncharge, 41.7% of
divergent cases) and salt/fragment handling (33.3%) the dominant causes. The
method and an open-source reference implementation are released as part of
Wawekit, an open desktop cheminformatics toolkit, enabling reproducibility audits
to be run as a standard step in dataset curation.

## 1. Introduction

Structure standardization underlies every downstream cheminformatics operation:
similarity search, clustering, QSAR modeling, and database deduplication all
assume that "the same molecule" is represented identically. In practice,
standardization is performed by a *protocol* — an ordered composition of
normalization operations (salt stripping, charge neutralization, tautomer
canonicalization, stereochemistry handling, and others) — and different research
groups, software packages, and even different configurations of the same
toolkit apply different protocols. The consequence is that a molecule's
"standard" structure, and therefore its identity within a dataset, can be
**pipeline-dependent**. Two datasets curated with different standardization
choices are not guaranteed to be directly comparable, and a result computed on
one cannot always be reproduced from the other.

Existing tools (the ChEMBL structure pipeline, MolVS, RDKit's `rdMolStandardize`)
provide standardization *implementations*, each encoding one set of choices.
None, to our knowledge, provides a way to **measure how much two protocols
disagree**, on which molecules, or **why**. This gap matters because
standardization choices are rarely reported with the precision needed to
reproduce them (which operations, in which order, with which parameters), and
because the field has no established diagnostic for flagging when a dataset's
molecular identities are protocol-fragile.

We contribute:

1. A **composable protocol model** — standardization expressed as a fixed-order
   sequence of independently toggleable operations — that makes two protocols
   directly comparable and enables per-operation attribution (§3.1).
2. A **dual-identity divergence measure** — agreement evaluated separately under
   canonical-SMILES and InChIKey identity — motivated by the empirical finding
   that the two conventions disagree on which molecules are reproducible
   (§3.2, §4.1): InChI's internal tautomer normalization can mask a divergence
   that canonical SMILES reveals.
3. An **ablation-based cause-attribution procedure** that, for each divergent
   molecule, identifies which specific operation(s) are responsible (§3.3).
4. A **reference open-source implementation** (Wawekit) with a reusable
   benchmark harness, and illustrative results quantifying divergence and its
   causes on a 40-molecule structurally diverse set (§4).

## 2. Related Work

*(To be expanded with a literature pass before submission. Candidate anchors:)*

- RDKit `rdMolStandardize` and the ChEMBL structure curation pipeline
  (Bento et al., *J. Cheminform.*) — standardization *implementations*, not
  divergence measurement.
- MolVS (Swain) — a configurable Python standardizer; again an implementation.
- InChI technical manual (Heller et al., *J. Cheminform.* 2015) — documents
  InChI's internal tautomer/charge normalization layers, which our §4.1 finding
  depends on.
- Prior tautomer-enumeration literature (e.g. Sitzmann et al.) is relevant to
  why tautomer canonicalization is contentious, but does not address
  cross-protocol *reproducibility* measurement.
- To our knowledge, no prior work quantifies standardization disagreement as a
  dataset-level, attributable metric; this is the gap we address.

## 3. Methods

### 3.1 Composable standardization protocols

We define a standardization **protocol** as a named subset of eight operations,
drawn from RDKit's `rdMolStandardize` module plus two structural-normalization
utilities, applied in a fixed, chemically motivated order:

1. Metal disconnection (`MetalDisconnector`)
2. Functional-group normalization (`Normalizer`)
3. Reionization (`Reionizer`)
4. Parent-fragment selection (`LargestFragmentChooser`) — salt/solvent stripping
5. Charge neutralization (`Uncharger`)
6. Isotope removal
7. Stereochemistry removal
8. Canonical tautomer selection (`TautomerEnumerator.Canonicalize`)

A protocol is the *subset* of these operations it enables; the application order
is always the fixed sequence above, so two protocols differ only in *which*
operations run, making their outputs directly comparable and any single
operation's effect isolable. We define three representative protocols for this
study:

- **Minimal** — normalization only (operation 2), representing a light-touch
  baseline.
- **ChEMBL-like** — operations 1, 2, 3, 4, 5 (no tautomer canonicalization),
  approximating the published ChEMBL structure curation pipeline.
- **Aggressive** — all eight operations.

### 3.2 Identity and divergence

For a standardized molecule we record two identity representations:

- **Canonical SMILES** (RDKit `MolToSmiles`), which is sensitive to any
  structural change including tautomer choice.
- **InChIKey** (`MolToInchiKey`), which applies InChI's own internal
  normalization layers — including tautomer canonicalization for a defined set
  of tautomer classes — independent of our protocol's operations.

For a molecule audited under a set of protocols, we define **agreement** under
each identity convention as all protocols producing an identical value; a
molecule is **labile** if it disagrees under *either* convention. We report both
conventions separately because, as shown in §4.1, they can disagree with each
other about whether a given molecule is reproducible — a methodological
consideration we did not anticipate before implementing the measurement and
regard as a contribution in its own right.

### 3.3 Ablation-based cause attribution

For each labile molecule, we identify the most operation-rich protocol in the
comparison set and, for each of its enabled operations (evaluated in reverse
application order), re-standardize the molecule with that single operation
disabled. If disabling an operation changes the resulting identity (InChIKey
preferentially, then canonical SMILES) relative to the full protocol's output,
that operation is recorded as an implicated **cause**. This procedure requires
one additional standardization per enabled operation per labile molecule
(bounded, since at most eight operations exist) and yields, for each divergence,
a ranked list of the operation(s) responsible — turning "these protocols
disagree" into "these protocols disagree because of tautomer canonicalization,"
a substantially more actionable diagnostic.

### 3.4 Dataset-level metrics

From a completed audit over *N* molecules and *P* protocols we report:

- **Reproducibility score** (per identity convention) — the fraction of
  molecules on which all *P* protocols agree.
- **Pairwise agreement** — for every protocol pair, the fraction of molecules on
  which that pair individually agrees, finer-grained than the all-agree score
  and informative about *which* protocol differences matter most.
- **Cause spectrum** — among labile molecules, the fraction implicating each of
  the eight operations, forming a taxonomy of *why* a dataset is not fully
  reproducible under standardization.

### 3.5 Implementation

The method is implemented in Python 3.13.2 using RDKit 2026.03.4 for all
chemistry operations, with no dependency on the host application's GUI layer —
the entire measurement pipeline (protocol engine, divergence analysis, metrics,
and a command-line benchmark harness) is implemented as pure, independently
testable services with 39 unit tests covering the protocol engine, divergence
analysis, metrics computation, and benchmark harness. An interactive graphical front-end
(Wawekit) additionally provides a reproducibility panel — a protocol-agreement
heatmap, a cause-spectrum chart, and an inspectable list of labile molecules
with side-by-side structure comparison — for exploratory use during dataset
curation. Both interfaces share the identical underlying computation. Source
code is released under the MIT license.

### 3.6 Scaling to publication scale

The results in §4 are computed on a 40-molecule illustrative set assembled to
span the structural classes we hypothesized would be labile (salts, charged
species, tautomer-ambiguous heterocycles, isotopically labeled compounds, and
stereocenters), and are reported here to validate the method end-to-end. A
submission-ready manuscript requires scaling this to representative public
subsets — we propose stratified random samples of 5,000–10,000 compounds each
from ChEMBL, PubChem, and DrugBank, plus a curated "hard cases" set of molecules
with documented tautomer or charge ambiguity — with the benchmark harness
(§3.5) requiring no code changes to run at that scale beyond runtime.

## 4. Results

### 4.1 InChIKey and canonical SMILES disagree about reproducibility

Motivating this study's dual-identity design: for 2-hydroxypyridine, enabling
canonical-tautomer selection changes the canonical SMILES output
(`Oc1ccccn1` → `O=c1cccc[nH]1`) but leaves the InChIKey unchanged, because
InChI's own normalization already collapses this tautomer pair. Consequently, a
molecule can be flagged as pipeline-dependent under one identity convention and
fully reproducible under the other — the two conventions are not interchangeable
proxies for "the same molecule," and a reproducibility audit that reports only
one is incomplete.

### 4.2 Illustrative benchmark

On a 40-molecule set spanning salts, charged species, tautomer-ambiguous
heterocycles, isotopes, and stereocenters, auditing the Minimal, ChEMBL-like,
and Aggressive protocols gave:

| Metric | Value |
|---|---|
| Molecules analyzed | 40 |
| SMILES reproducibility (all 3 protocols agree) | 70.0% |
| InChIKey reproducibility (all 3 protocols agree) | 75.0% |
| Labile molecules | 12 / 40 (30.0%) |
| Molecules with a protocol failure | 0 |

No protocol failed on any molecule in this set: all 40 produced a valid InChIKey
under all three protocols, so every reported agreement figure is computed over
the full set rather than a surviving subset.

**Pairwise InChIKey agreement:**

| Protocol pair | Agreement |
|---|---|
| ChEMBL-like vs. Aggressive | 90.0% |
| Minimal vs. ChEMBL-like | 85.0% |
| Minimal vs. Aggressive | 75.0% |

Protocol pairs differing by fewer operations (ChEMBL-like vs. Aggressive differ
by three operations: isotope removal, stereo removal, tautomer canonicalization)
agree more often than pairs differing by more (Minimal vs. Aggressive differ by
seven), consistent with divergence accumulating monotonically with protocol
dissimilarity — an expected but previously unquantified relationship.

**Divergence cause spectrum** (fraction of the 12 labile molecules implicating
each operation):

| Operation | Fraction of labile molecules |
|---|---|
| Charge neutralization (`uncharge`) | 41.7% |
| Parent-fragment selection (`fragment_parent`) | 33.3% |
| Isotope removal | 16.7% |
| Canonical tautomer selection | 16.7% |

Charge and salt/fragment handling jointly account for approximately three
quarters of observed divergence in this set, suggesting that — at least for
datasets containing counter-ions and ionizable groups, which is typical of
bioactivity databases — these two operations are the highest-leverage targets
for standardization protocol agreement, ahead of the more heavily studied
tautomer-canonicalization problem.

## 5. Discussion

*(To be expanded.)* Key points to develop:

- The InChIKey/SMILES divergence-disagreement finding (§4.1) has a practical
  consequence for database curators: reporting "molecules deduplicated by
  InChIKey" is not equivalent to "molecules standardized identically," and the
  gap is largest exactly where tautomer ambiguity is common (heterocyclic drug
  scaffolds).
- The dominance of charge/salt-handling causes over tautomer causes in our
  illustrative set (§4.2) is a testable, falsifiable claim that should be
  checked against public-scale data (§3.6) — it may be an artifact of our
  benchmark's composition rather than a general property.
- Practical recommendation for practitioners: report the *protocol*, not just
  "we standardized structures," and consider running a divergence audit before
  merging datasets from different sources.
- Limitations: our operation set, while covering the RDKit standardization
  surface, does not include every published standardization choice (e.g.
  aromaticity perception model, specific tautomer scoring functions); the
  ablation procedure attributes cause among *our* eight operations and cannot
  detect divergence from operations outside that set (e.g. a different
  standardizer implementation entirely, such as a non-RDKit tool).

## 6. Conclusion

Standardization reproducibility is measurable, attributable, and — in our
illustrative benchmark — non-trivial: three reasonable protocols disagreed on
30% of molecules, predominantly due to charge and salt handling rather than the
more commonly discussed tautomer problem. We release the method and its
reference implementation openly, with a benchmark harness designed to scale to
public bioactivity databases, so that standardization reproducibility can become
a routine, reportable property of curated cheminformatics datasets rather than
an unexamined assumption.

## Data and Code Availability

Implementation, tests, and the benchmark harness used to produce §4 are
available in the Wawekit repository under the MIT license
(`src/wawekit/services/reproducibility/`). The illustrative benchmark set and
raw per-molecule results are included at
`learning/research-track-R5-benchmark/` (`benchmark_set.smi`,
`benchmark_results.csv`, `benchmark_output.txt`).

## Author Contributions, Funding, Competing Interests

*(To be completed by the author(s) before submission.)*

---

### Manuscript status and next steps

- [x] Method implemented and unit-tested (R1–R3).
- [x] Reference GUI implementation (R4).
- [x] Benchmark harness implemented and run at illustrative scale (R5).
- [ ] Scale benchmark to public ChEMBL/PubChem/DrugBank subsets (§3.6).
- [ ] Literature review pass for §2 (Related Work) with full citations.
- [ ] Validate the cause-attribution taxonomy against a curated set of known
      tautomer/charge-ambiguous molecules (precision/recall of the flag).
- [ ] Internal review, then target-journal formatting (J. Cheminform. uses a
      BioMed Central / Springer Nature template).
