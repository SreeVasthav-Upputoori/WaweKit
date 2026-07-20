# Manuscript v2 — number-independent sections (working draft)

These sections are drafted ahead of the ChEMBL audit completing, because they
do not depend on its output. Results and the numeric parts of Abstract,
Discussion and Conclusion are written afterwards, directly from
`chembl_results.json`.

Citation keys refer to `references.md`; every one is PubMed-verified.

---

## 1. Introduction

Structure standardization — the normalization of salts, charge states,
tautomers, isotopic labels and stereochemistry to a canonical representation —
is a mandatory preprocessing step in essentially every cheminformatics
workflow. Similarity search, clustering, database deduplication and QSAR
modelling all rest on the assumption that the same chemical entity is
represented identically wherever it appears. Standardization is what makes that
assumption hold.

In practice, standardization is performed by a *protocol*: an ordered
composition of normalization operations, each encoding a modelling decision.
Whether to strip counter-ions, whether to neutralize formal charges, whether to
select a canonical tautomer, whether to discard stereochemistry — these are
choices, and different databases, software packages and individual
configurations resolve them differently. Public infrastructure reflects this:
the ChEMBL curation pipeline [1] and the PubChem standardization service [3]
are independently designed, independently reasonable, and not equivalent.

The consequence is that a molecule's standardized form — and therefore its
identity within a dataset — can be **pipeline-dependent**. Two datasets curated
under different standardization choices are not guaranteed to be directly
comparable, and a result computed on one may not be reproducible from the
other. That this matters downstream is established: automated curation of
chemical structure and identity measurably changes QSAR model performance [5].

The scale of pipeline dependence is not hypothetical. PubChem reports that 44%
of structures passing its standardization are modified in the process, and that
60% of its standardized structures are not identical to the structure obtained
by round-tripping through InChI — attributed primarily to a different preferred
tautomeric form [3]. Tautomerism in particular is a catalogued source of
representational ambiguity, with thousands of experimentally annotated
tautomeric tuples documented across the literature [4].

What existing work provides is standardization *implementations*, each encoding
one set of choices, together with a small number of pairwise comparisons
between a specific pipeline and a specific reference [3]. What is not available
is a general method for asking, of an arbitrary set of protocols and an
arbitrary dataset: how often do these protocols disagree, on which molecules,
and — critically — *because of which operation*. Without per-operation
attribution, a disagreement is an observation; with it, a disagreement becomes
an actionable diagnostic pointing at the specific modelling decision
responsible.

We therefore treat standardization reproducibility as a measurable,
first-class property of a dataset rather than an implicit assumption, and
contribute:

1. A **composable protocol model** (§3.1) in which standardization is expressed
   as a fixed-order sequence of independently toggleable operations. This makes
   two protocols directly comparable and makes any single operation's
   contribution isolable.
2. A **dual-identity divergence measure** (§3.2), evaluating agreement
   separately under canonical-SMILES and InChIKey identity. We report both
   because the two conventions can disagree with each other about whether a
   given molecule is reproducible — InChI's internal normalization [2] absorbs
   certain differences that canonical SMILES exposes.
3. An **ablation-based cause-attribution procedure** (§3.3) that identifies,
   for each divergent molecule, which operation(s) are responsible. This is the
   component that distinguishes the method from pairwise pipeline comparison.
4. An **open-source reference implementation** with a reusable benchmark
   harness, and its application to a seeded random sample of ChEMBL (§4).

### 1.1 Relationship to prior work

The closest prior art is PubChem's own analysis of its standardization service
[3], which quantifies disagreement between one production pipeline and InChI
round-tripping at full database scale. That work establishes that
standardization disagreement is real and substantial; it does not generalize to
arbitrary protocol sets, and it does not attribute disagreement to individual
normalization operations, because its comparison is between two monolithic
pipelines rather than between compositions of separable operations. Our
contribution is the generalization along both axes — arbitrary *N* protocols,
and per-operation attribution — not the observation that standardization
pipelines disagree, which is already documented.

---

## 2. Methods

### 2.1 Composable standardization protocols

A standardization **protocol** is defined as a named subset of eight
operations, applied in a fixed, chemically motivated order. Six are provided by
RDKit's `rdMolStandardize` module; the remaining two are elementary structural
edits applied directly:

| # | Operation | Implementation |
|---|-----------|----------------|
| 1 | Metal disconnection | `MetalDisconnector` |
| 2 | Functional-group normalization | `Normalizer` |
| 3 | Reionization | `Reionizer` |
| 4 | Parent-fragment selection (salt/solvent stripping) | `LargestFragmentChooser` |
| 5 | Charge neutralization | `Uncharger` |
| 6 | Isotope removal | clear all isotope labels |
| 7 | Stereochemistry removal | `Chem.RemoveStereochemistry` |
| 8 | Canonical tautomer selection | `TautomerEnumerator.Canonicalize` |

The ordering is fixed across all protocols: disconnection and normalization
precede fragment selection, which precedes charge handling, with tautomer
canonicalization last. A protocol is therefore fully specified by *which*
operations it enables. Fixing the order is a deliberate design constraint — it
means two protocols differ only in their operation sets, which is what makes
their outputs comparable and any single operation's effect isolable by
ablation. Standardization is applied to a copy of each input molecule; input
structures are never mutated.

Three representative protocols are used throughout:

- **Minimal** — normalization only (operation 2). A light-touch baseline
  representing the least a pipeline might reasonably do.
- **ChEMBL-like** — operations 1–5, deliberately *excluding* tautomer
  canonicalization, approximating the published ChEMBL curation pipeline [1].
- **Aggressive** — all eight operations.

These are not intended as an exhaustive survey of deployed pipelines but as
three points spanning the range of reasonable practice, chosen so that the
pairwise comparisons differ by controlled numbers of operations (3, 4 and 7).

### 2.2 Identity conventions and divergence

For each standardized structure two identity representations are recorded:

- **Canonical SMILES** (RDKit `MolToSmiles`), sensitive to any structural
  change, including tautomer choice.
- **InChIKey** (`MolToInchiKey`), which applies InChI's own normalization
  layers — including tautomer normalization for a defined set of tautomer
  classes — independently of the protocol's operations [2].

For a molecule audited under a protocol set, **agreement** under an identity
convention means all protocols produced an identical value. A molecule is
**labile** if it disagrees under *either* convention. Both conventions are
reported separately rather than one being selected as canonical, because they
are not interchangeable proxies for chemical identity (§4.1).

A protocol may fail on a molecule if RDKit rejects an intermediate structure.
Such failures are recorded and excluded from the agreement computation for that
molecule: a failure is evidence of fragility, not of divergence, and conflating
the two would let two failed protocols count as agreeing with each other.
Agreement is thus computed over the protocols that produced a valid identity,
with the count of affected molecules reported separately.

### 2.3 Ablation-based cause attribution

For each labile molecule, the most operation-rich protocol in the comparison
set is selected. For each of its enabled operations, evaluated in reverse
application order, the molecule is re-standardized with that single operation
disabled and the resulting identity compared against the full protocol's
output. An operation whose removal changes the identity is recorded as an
implicated cause, ranked by whether it changes InChIKey (deeper identity) or
only canonical SMILES.

Reverse application order reflects that later operations are more likely to be
the proximate cause of a difference in the final structure. The procedure costs
one additional standardization per enabled operation per labile molecule,
bounded because at most eight operations exist.

Two limitations follow directly from the construction and constrain
interpretation. First, attribution is only possible among the operations in the
protocol — divergence originating from a source outside this set (a different
aromaticity model, a different tautomer scoring function, a non-RDKit
standardizer) cannot be detected. Second, when two operations jointly determine
an outcome such that neither alone changes it, single-operation ablation
attributes no cause; these molecules are reported as *unattributed* rather than
silently omitted.

### 2.4 Dataset-level metrics

From an audit over *N* molecules and *P* protocols we report:

- **Reproducibility score**, per identity convention — the fraction of
  molecules on which all *P* protocols agree.
- **Pairwise agreement** — for each protocol pair, the fraction of molecules on
  which that pair agrees, computed over molecules where both produced a valid
  identity. Finer-grained than the all-agree score, and informative about which
  protocol differences carry weight.
- **Cause spectrum** — among labile molecules, the fraction implicating each
  operation. This does not sum to 1: a molecule may implicate several
  operations.

Proportions are reported with 95% Wilson score intervals, which remain within
[0, 1] near the boundaries and behave acceptably at the subgroup sizes involved
in per-cause reporting, where the normal approximation does not.

### 2.5 Implementation and availability

The measurement pipeline — protocol engine, divergence analysis, metrics, and a
command-line benchmark harness — is implemented in Python 3.13.2 against RDKit
2026.03.4, with no dependency on any GUI layer, and is covered by 39 unit
tests. An interactive front-end (WaweKit) additionally presents a
protocol-agreement heatmap, a cause-spectrum chart and an inspectable list of
labile molecules for exploratory curation; both interfaces call the identical
underlying computation. The implementation, the sampling and analysis scripts,
the drawn sample and the raw per-molecule results are released under the MIT
license.
