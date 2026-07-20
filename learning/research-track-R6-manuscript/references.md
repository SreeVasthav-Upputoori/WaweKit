# Verified references

Every entry below was retrieved from **PubMed** during this session and the
metadata (authors, journal, year, volume, pages, DOI) is as returned by the
PubMed API — none of it is reconstructed from memory. Anything not on this list
must be verified before it enters the manuscript.

---

**[1] Bento AP, Hersey A, Félix E, Landrum G, Gaulton A, Atkinson F, Bellis LJ,
De Veij M, Leach AR.** An open source chemical structure curation pipeline using
RDKit. *Journal of Cheminformatics.* 2020;12(1):51.
DOI: [10.1186/s13321-020-00456-1](https://doi.org/10.1186/s13321-020-00456-1)
PMID: 33431044

> Use for: the ChEMBL structure curation pipeline our "ChEMBL-like" protocol
> approximates; the Checker/Standardizer/GetParent decomposition; evidence that
> incoming compounds "are typically not standardised according to consistent
> rules."

---

**[2] Heller SR, McNaught A, Pletnev I, Stein S, Tchekhovskoi D.** InChI, the
IUPAC International Chemical Identifier. *Journal of Cheminformatics.*
2015;7:23.
DOI: [10.1186/s13321-015-0068-4](https://doi.org/10.1186/s13321-015-0068-4)
PMID: 26136848

> Use for: InChI/InChIKey as the field-standard identity; the existence of
> InChI's internal normalization layers, which our dual-identity finding depends
> on.

---

**[3] Hähnke VD, Kim S, Bolton EE.** PubChem chemical structure standardization.
*Journal of Cheminformatics.* 2018;10(1):36.
DOI: [10.1186/s13321-018-0293-8](https://doi.org/10.1186/s13321-018-0293-8)
PMID: 30097821

> **Most important reference for positioning.** This is the closest prior art
> and it must be cited explicitly rather than glossed. Directly relevant
> reported findings:
> - 44% of structures passing standardization are *modified* in the process
>   (53.6M substance → 45.8M compound unique structures).
> - **"60% of the structures obtained from PubChem structure standardization are
>   not identical to the chemical structure resulting from the InChI (primarily
>   due to preferences for a different tautomeric form)."**
> - Rejection rate 0.36%, dominated by invalid valences.
> - Standardization time dominated by edge cases: 90% of total time is spent on
>   2.05% of structures.
>
> Consequence for our novelty claim: a two-way pipeline-vs-InChI disagreement
> measurement **already exists in the literature**, at production scale. Our
> contribution must therefore be stated as the *N*-protocol generalisation with
> per-operation ablation attribution, not as "first measurement of
> standardization disagreement."

---

**[4] Dhaked DK, Guasch L, Nicklaus MC.** Tautomer Database: A Comprehensive
Resource for Tautomerism Analyses. *Journal of Chemical Information and
Modeling.* 2020;60(3):1090-1100.
DOI: [10.1021/acs.jcim.9b01156](https://doi.org/10.1021/acs.jcim.9b01156)
PMID: 32027495

> Use for: tautomerism as a known, catalogued source of representational
> ambiguity (2819 tautomeric tuples from 171 publications; 79% prototropic).
> Also a concrete candidate for the external validation set proposed in Future
> Work — it provides experimentally annotated tautomer pairs against which
> cause-attribution precision could be measured.

---

**[5] Mansouri K, Grulke CM, Richard AM, Judson RS, Williams AJ.** An automated
curation procedure for addressing chemical errors and inconsistencies in public
datasets used in QSAR modelling. *SAR and QSAR in Environmental Research.*
2016;27(11):939-965.
DOI: [10.1080/1062936X.2016.1253611](https://doi.org/10.1080/1062936X.2016.1253611)
PMID: 27885862

> Use for: the downstream-consequences claim — curation/standardization quality
> measurably changes QSAR model performance ("the latter showed statistically
> improved predictive performance"). This is the citation that justifies why
> standardization divergence is worth measuring at all.

---

## Software / resources to cite (not PubMed-indexed — verify before submission)

These are not journal articles and were **not** verified through PubMed. Cite
using each project's own stated citation instructions:

- **RDKit** — cheminformatics toolkit providing `rdMolStandardize` and all
  chemistry operations. Cite per rdkit.org guidance, with the exact version used
  (2026.03.4).
- **ChEMBL database** — source of the benchmark sample. The current database
  release paper should be cited; verify which release corresponds to the data
  actually fetched (this run: 2,921,148 molecule records).
- **MolVS** — configurable Python standardizer, mentioned in Related Work as an
  alternative implementation. Verify current citation form.

## Claims still needing a citation

Flagged for a targeted search before submission; do not assert these without
support:

- That standardization protocol details are commonly under-reported in
  publications. (Plausible and widely believed, but I found no paper
  quantifying it. Either find one or soften to an observation about the
  examples at hand.)
- Prevalence of salts/counter-ions in vendor and bioactivity databases, if the
  Discussion argues fragment handling matters at scale.
