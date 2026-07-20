# Discussion framing — decisions to carry into the final draft

Written before the ChEMBL numbers landed, so that the framing is chosen on
methodological grounds rather than fitted to whatever the results turn out to
be. Reviewer-facing objections are listed with the intended response.

---

## 1. The novelty claim must be narrowed (non-negotiable)

The earlier draft asserted that no prior work measures standardization
disagreement. **That is false**, and a reviewer familiar with the PubChem
literature would catch it immediately. Hähnke et al. [3] report that 60% of
PubChem-standardized structures differ from the InChI round-trip, attributed
primarily to tautomer preference, at full database scale.

Defensible narrowed claim:

> Prior work compares *one pipeline against one reference*. We generalize to
> *N protocols* and add *per-operation attribution*.

The attribution component appears genuinely unaddressed in the retrieved
literature; the "disagreement exists and is large" observation does not, and
should be cited to [3] as motivation rather than presented as our finding.

## 2. The ChEMBL confound — must be stated prominently, not buried

Sampling from ChEMBL means sampling structures **that have already passed
ChEMBL's own curation pipeline** [1]. The sample is therefore pre-normalized
with respect to exactly the kind of operations under study: counter-ions
already stripped, charges already handled, valences already checked.

Consequences to state explicitly:

- Every divergence figure measured here is a **lower bound** on what the same
  protocols would produce on raw vendor, patent, or literature-extracted
  structures.
- Pairwise agreements involving the ChEMBL-like protocol are **structurally
  favoured** — that protocol approximates the pipeline the data already went
  through. Any observation that ChEMBL-like agrees strongly with something else
  must be read in that light and not presented as a neutral finding.
- The honest framing is: *"even on already-curated data, protocols disagree on
  X% of molecules"* — which is a stronger rhetorical position than an inflated
  number from dirty data would have been, and is defensible.

The right follow-up experiment (state as future work, do not claim): run the
identical audit on an uncurated source and compare, which isolates how much of
the reproducibility gap curation actually closes.

## 3. Expected reversal versus the pilot set — report it, do not hide it

A 40-molecule hand-assembled pilot set gave charge handling (41.7%) and
fragment selection (33.3%) as dominant causes, with tautomer canonicalization
minor (16.7%). Early indications on real ChEMBL data invert this, with stereo
and tautomer handling dominating.

This should be reported as a **methodological result in its own right**, not
quietly dropped:

> A benchmark assembled to contain the phenomena of interest reproduces the
> composition of its own construction, not the composition of the underlying
> population. The cause spectrum measured on a curated random sample differs
> substantially from that measured on a hand-assembled set — which is the
> argument for why the audit must be run on the actual dataset in use rather
> than on a canonical benchmark.

That framing converts an inconvenient discrepancy into support for the tool's
central use case. It is also simply true, which matters more.

## 4. Sampling design limitation

Cluster sampling (500 blocks x 10 consecutive records) rather than simple
random sampling, because the API paginates by offset and 5,000 independent
requests is impractical. Records adjacent in ChEMBL frequently derive from one
publication series, so within-block structural similarity is expected to exceed
between-block similarity, and the effective sample size is below the nominal
count.

`analyse_sample.py` measures the realised effect (mean within-block vs
between-block Tanimoto). Report the measured ratio. If within-block similarity
is substantially elevated, either widen the intervals or state plainly that the
nominal CIs are optimistic — do not report nominal binomial CIs as if the
design were simple random sampling without noting this.

## 5. Composition heterogeneity

The sample contains records ChEMBL types as Small molecule, Unknown, None, and
a small number of Protein (peptide SMILES). Peptides behave differently under
standardization (many ionizable groups, many stereocentres) and could dominate
particular cause categories.

Report the composition. If a cause category is driven by the peptide subset,
say so — an aggregate figure that is really a statement about 16 peptides is
misleading, and stratifying is cheap.

## 6. What must NOT be claimed

- Any figure as a property of "chemical databases" in general. It is a property
  of a seeded random sample of one already-curated database, under three
  specific protocols.
- That the three protocols represent deployed practice. They are three
  controlled points, one of which approximates a real pipeline.
- Any causal claim about which operation a practitioner *should* change. The
  method identifies where protocols differ; whether a given operation is
  chemically *correct* is a separate question this work does not address.
- Precision/recall of the attribution procedure. It has not been validated
  against ground truth. The tautomer database [4] is the obvious substrate for
  that validation and it is future work, not a present claim.

## 7. Limitations section — required contents

1. Attribution confined to the eight operations in the protocol model.
2. Joint-cause blindness of single-operation ablation (report the unattributed
   count as the measured size of this effect).
3. ChEMBL pre-curation confound (§2 above).
4. Cluster-sampling design (§4 above).
5. Single-toolkit study: all protocols are RDKit-based, so cross-toolkit
   divergence — which is where the largest real-world disagreement plausibly
   lives — is out of scope by construction.
6. No external validation of attribution correctness.
