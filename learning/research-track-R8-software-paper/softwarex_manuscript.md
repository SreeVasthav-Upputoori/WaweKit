# WaweKit: an offline desktop workbench for cheminformatics with built-in standardization auditing

**Sree Vasthav Upputoori**<sup>1,\*</sup> and **S. Madhav Varma**<sup>1</sup>

<sup>1</sup> TheWaweAI — *affiliation address to be completed*

<sup>\*</sup> Corresponding author: sreevasthav.upputoori@gmail.com

*ORCID identifiers to be added before submission.*

**Target venue:** *SoftwareX* (Elsevier). Format follows the SoftwareX
template: code metadata table, Motivation and significance, Software
description, Illustrative examples, Impact, Conclusions.

**Relationship to the companion research paper.** This article describes the
software. The scientific study that the reproducibility auditor enabled —
divergence measurement across 4,972 ChEMBL structures and its downstream
consequences on 27,152 bioactivity measurements — is reported separately and
cites this article for the tool. This paper contains no results from that
study beyond what is needed to demonstrate that the feature works.

---

## Code metadata

| | |
|---|---|
| Current code version | 0.1.0 |
| Permanent link to code/repository | https://github.com/SreeVasthav-Upputoori/WaweKit |
| Permanent link to Reproducible Capsule | *(Zenodo DOI — to be minted at submission)* |
| Legal Code License | MIT |
| Code versioning system used | git |
| Software code languages, tools, services used | Python 3.12+, PySide6 (Qt 6), RDKit, scikit-learn, matplotlib, ReportLab, 3Dmol.js; optionally `chembl_structure_pipeline` and MolVS for cross-toolkit comparison |
| Compilation requirements, operating environments | Python ≥ 3.12; Windows, macOS, Linux |
| Link to developer documentation | https://github.com/SreeVasthav-Upputoori/WaweKit/blob/main/docs/FEATURES.md |
| Support email for questions | sreevasthav.upputoori@gmail.com |

---

## 1. Motivation and significance

Cheminformatics analysis of small-molecule datasets — loading structures,
standardizing them, computing descriptors and fingerprints, searching by
similarity or substructure, clustering, and reporting — is routine work, but
the software landscape for performing it interactively is polarised. On one
side are programmatic toolkits, principally RDKit, which are powerful and
free but require fluency in Python. On the other are graphical environments
such as KNIME, Datagrok and DataWarrior, which remove the coding requirement
but bring workflow-engine complexity, platform services, or licensing and
deployment constraints that are not always compatible with teaching settings,
air-gapped environments, or researchers whose primary training is synthetic or
medicinal chemistry rather than programming.

WaweKit occupies the space between: a single-window desktop application that
performs a complete analysis workflow locally, with no account, no server, no
network access and no scripting, while remaining a plain Python package that
can be imported and scripted when the user is ready for that.

The specific gap that motivated its development, however, is narrower and is
what distinguishes WaweKit from the alternatives above. **Structure
standardization — normalising salts, charge states, tautomers, isotopes and
stereochemistry — is a mandatory preprocessing step whose protocol varies
between tools and configurations, and no existing interactive tool lets a user
measure how much that choice affects their own dataset.** Standardization
implementations are widely available; the ChEMBL curation pipeline [1] and the
PubChem standardization service [2] are prominent, independently designed, and
not equivalent to one another. What is not available is a way to ask, of a
specific dataset, which molecules would receive a different identity under a
different protocol, and *which normalization operation* is responsible.

WaweKit provides that capability as a first-class, interactive feature
alongside the conventional analysis toolset, and exposes the same computation
as a Qt-free library and command-line tool so it can be embedded in
non-interactive pipelines.

## 2. Software description

### 2.1 Software architecture

WaweKit is organised in four layers with dependencies pointing in one
direction only:

```
gui  →  services  →  models  →  core
```

* **core** (5 modules, ~370 lines) — configuration, logging, cross-platform
  paths, application constants. No chemistry.
* **models** (9 modules, ~1,200 lines) — RDKit-backed domain objects: the
  molecule record and the typed results attached to it (descriptor sets,
  fingerprints, similarity scores, scaffolds, conformer ensembles, cluster
  assignments, substructure hits). Contains no Qt and no computation.
* **services** (29 modules, ~4,700 lines) — all chemistry and I/O:
  standardization, descriptors, fingerprints, similarity, scaffolds, conformer
  generation, chemical-space projection, clustering, substructure search,
  structural alerts, format conversion, report generation, and the
  reproducibility auditor. Services may use Qt's core (signals, thread pool)
  but never its widgets.
* **gui** (32 modules, ~7,100 lines) — the PySide6 window, docked panels,
  dialogs and delegates.
* **plugins** (3 modules) — third-party extension loading.

Two consequences of this arrangement matter for reuse. First, **every analysis
service imports without Qt**, so the scientific functionality is usable
headlessly; `pip install wawekit` installs the library and command-line tools
without the GUI framework, and `pip install wawekit[gui]` adds the desktop
application. Second, because the GUI holds no computation, the interactive and
programmatic interfaces cannot diverge: the panel and the command-line tool
call the same functions, and this equivalence is asserted by the test suite
rather than by convention.

Long-running operations execute on a Qt thread pool and report progress
through signals, so the interface remains responsive on datasets of thousands
of structures. Every batch service follows the same contract — a progress
callback, a result report carrying per-molecule failures, and the rule that
one unprocessable structure never aborts a run.

### 2.2 Software functionalities

**Data handling.** Import of SDF, MOL and SMILES files by dialog or
drag-and-drop, with per-record error reporting; a standalone format converter
between CSV, SDF, MOL and SMILES; export to CSV and SDF with computed values
attached as data fields.

**Structure display.** A sortable table with 2D depictions rendered per row, a
detail panel with SVG/PNG export, and an interactive 3D viewer (3Dmol.js in an
embedded browser view) that generates a conformation on demand for the
selected molecule.

**Standardization.** Configurable cleanup — salt stripping, charge
neutralisation, tautomer canonicalisation, deduplication — reporting every
change made to every structure rather than applying them silently.

**Analysis.** Drug-likeness descriptors with Lipinski evaluation; Morgan,
MACCS and RDKit fingerprints; Tanimoto/Dice/Cosine similarity ranking;
Bemis–Murcko scaffold grouping with click-to-filter; conformer generation
(ETKDG with MMFF94/UFF optimisation) with energy ranking and SDF export;
chemical-space projection by PCA or t-SNE with linked selection between plot
and table; Butina and k-means clustering; SMARTS/SMILES substructure search
with matched-atom highlighting; and structural-alert screening against the
combined PAINS, Brenk and NIH catalogues (765 substructure filters), flagging
assay-interference and liability motifs with per-molecule detail.

**Filtering.** A query box accepting text and numeric comparisons
(`MW < 500`, `LogP >= 2`), plus an interactive range-filter panel whose bounds
are derived from the loaded dataset.

**Standardization reproducibility auditing.** The distinguishing capability.
The user selects two or more standardizers, and WaweKit reports how often they
produce the same standardized identity — evaluated separately under
canonical-SMILES and InChIKey identity — as an agreement heatmap, a
cause-spectrum chart, and an inspectable list of the affected molecules.

Two kinds of standardizer can be compared, answering different questions. A
**composed protocol** is a named subset of eight normalization operations
applied in fixed order; because its operations are individually addressable,
each disagreement can be attributed to a specific operation by systematic
ablation — disabling one operation, re-standardizing, and recording which
change alters the outcome. A **production pipeline** is a third-party
standardizer invoked as a black box; WaweKit ships adapters for ChEMBL's
`chembl_structure_pipeline` (the code the database itself runs) and for MolVS
in two configurations. A comparison may mix the two freely, so a user can ask
both "how do my protocol variants differ?" and "does my pipeline agree with
ChEMBL's?" — the latter being the question that arises whenever data from
different sources is merged.

The trade-off between the two kinds is made explicit rather than hidden.
Attribution requires operations that can be switched off, which an opaque
external pipeline does not offer, so a comparison consisting only of external
standardizers reports *whether* they disagree without attributing *why*. The
software distinguishes that from "no cause was found": each standardizer
declares through its interface whether it is ablatable, and attribution is
skipped rather than silently returning an empty result that would read as a
negative finding. Including one composed protocol alongside external pipelines
restores attribution for the whole comparison.

**Workflow and output.** A batch dialog chaining standardization →
descriptors → fingerprints → scaffolds → clustering → export as one
cancellable operation; and self-contained HTML and paginated PDF reports with
embedded depictions and summary statistics.

**Extension and presentation.** A plugin system discovering third-party
packages through Python entry points, so installing a package adds menu items
or dock panels with no modification to WaweKit; eight visual themes; and an
illustrated in-application manual.

### 2.3 Quality assurance

The project has 346 automated tests covering the domain models, every
chemistry and I/O service, the reproducibility auditor, GUI panels and
dialogs (headless, via `pytest-qt`), the plugin loader, and the documentation
itself — one test fails if the in-app manual references a missing image or
omits a feature section. Continuous integration runs linting, formatting and
the full suite on Ubuntu, Windows and macOS. A dedicated test asserts that the
graphical, command-line and library interfaces return identical results for
the same input, and a further test asserts that repeated audits of the same
data produce identical output.

## 3. Illustrative examples

### 3.1 Interactive analysis

A user opens a SMILES or SDF file by drag-and-drop; structures appear as a
sortable table with 2D depictions (Figure 1). `Ctrl+D` computes descriptors,
adding columns for molecular weight, logP, TPSA, hydrogen-bond counts,
rotatable bonds, ring count and Lipinski violations, and populating the
property-filter panel with the ranges present in the loaded data. Typing
`MW < 350` in the filter box narrows the table; clicking a column header sorts
by it. Selecting a row updates the structure panel, which also reports any
structural alerts matched. `Ctrl+Shift+P` projects the dataset into two
dimensions, and lassoing a cluster in the plot selects the corresponding table
rows. `Ctrl+R` writes a shareable HTML report. No scripting is involved at any
point, and no data leaves the machine.

### 3.2 Auditing standardization choices

With a dataset loaded, `Research → Reproducibility Audit` offers the three
bundled protocols — Minimal (normalisation only), ChEMBL-like (approximating
the published ChEMBL pipeline, notably without tautomer canonicalisation) and
Aggressive (all eight operations).

Figure 2 shows the result for a 40-structure set spanning salts, charged
species, tautomer-ambiguous heterocycles, isotopic labels and stereocentres.
The panel reports that the three protocols agree on 70% of the set under
canonical-SMILES identity and 75% under InChIKey identity, with twelve
structures sensitive to protocol choice. The heatmap gives pairwise agreement:
ChEMBL-like and Aggressive agree on 90% of structures, while Minimal and
Aggressive agree on only 75%. The cause spectrum attributes those
disagreements to specific operations — charge neutralisation and
parent-fragment selection dominating this set — and the list beneath names the
affected structures individually, so a curator can inspect exactly which
compounds are pipeline-dependent and why. Two entries are marked
*unattributed*, the honest report for a divergence that no single-operation
ablation could isolate.

### 3.3 The same analysis without the interface

The identical computation is available as a library:

```python
from rdkit import Chem
from wawekit.services.reproducibility import analyze_divergence, compute_metrics
from wawekit.services.reproducibility.protocol import DEFAULT_PROTOCOLS

records = [(name, Chem.MolFromSmiles(smi)) for name, smi in my_compounds]
run = analyze_divergence(records, DEFAULT_PROTOCOLS)
metrics = compute_metrics(run)

print(f"{metrics.inchikey_reproducibility:.1%} reproducible")
for operation, fraction in metrics.cause_spectrum.items():
    print(f"  {operation}: {fraction:.1%} of divergent molecules")
```

and as a command-line tool for unattended use:

```
python -m wawekit.services.reproducibility.benchmark compounds.smi --out results.csv
```

Neither requires the GUI dependencies to be installed.

## 4. Impact

**A capability not otherwise available interactively.** To our knowledge no
other graphical cheminformatics tool measures standardization divergence,
attributes it to individual normalization operations, or compares
independently-developed standardization pipelines against one another. The
last of these is the practically consequential one: a laboratory merging
compound data from two sources currently has no straightforward way to ask
whether the two sources would even agree on which records describe the same
compound. WaweKit answers that directly by running both pipelines and
reporting where they part company. Because
standardization determines which database records are treated as the same
compound, this affects deduplication, dataset merging and any model trained on
the result. The companion research paper uses WaweKit to show that protocol
choice can remove several percent of a bioactivity dataset by merging and can
fuse compounds differing thousandfold in potency into single training labels —
consequences that conventional aggregate model metrics do not reveal. WaweKit
makes detecting them a routine step rather than a bespoke study.

**Accessibility.** The application requires no programming, no account, no
network connection and no license server, and is MIT licensed. This suits
teaching environments, institutions without dedicated computational chemistry
support, and settings where data cannot leave local infrastructure. The
repository additionally contains a twenty-module development narrative
documenting how each capability was built and why, which is usable as
instructional material.

**Reuse.** The layered architecture means the chemistry services can be
imported independently of the interface; the headless installation path makes
this practical. The plugin system allows extension without forking. Published
analyses can cite an exact version through the archived release.

**Comparison with existing tools.** WaweKit does not aim to replace
established environments, and its position relative to them should be stated
plainly.

| | WaweKit | DataWarrior | KNIME | RDKit (library) |
|---|---|---|---|---|
| Interactive desktop UI | yes | yes | yes | no |
| No coding required | yes | yes | yes | no |
| Fully offline, no account | yes | yes | yes | yes |
| Open source | MIT | BSD | GPL/commercial | BSD |
| Workflow automation | batch dialog only | limited | extensive | via scripting |
| Visualisation breadth | moderate | extensive | extensive | minimal |
| Ecosystem / user base | new | large | very large | very large |
| Scriptable as a library | yes | no | limited | yes |
| **Standardization reproducibility auditing** | **yes** | no | no | no |
| **Cross-toolkit standardizer comparison** | **yes** | no | no | no |

DataWarrior and KNIME are more mature, have far larger user communities, and
offer broader visualisation and workflow automation than WaweKit does; for
general-purpose exploratory analysis they remain the better-supported choices.
WaweKit's contribution is the reproducibility auditing capability, delivered
in an interface that requires no scripting, together with a codebase small and
strictly layered enough to be reused programmatically or extended.

**Limitations.** The project is new and its user base correspondingly small.
It does not provide workflow automation comparable to KNIME, and its
visualisation is deliberately narrower than DataWarrior's. Cross-toolkit
comparison currently covers the two standardizers distributable as Python
packages (ChEMBL's pipeline and MolVS); pipelines available only as web
services or in other languages would each need an adapter. Cause attribution
remains available only for composed protocols, since it requires operations
that can be individually disabled — a limit of the method rather than of the
implementation.

## Figures

**Figure 1.** The WaweKit main window after loading a structure file and
computing descriptors. The central table carries 2D depictions and one column
per computed value; the structure panel (right) shows the selected molecule
with its matched structural alerts; the property-filter panel (left) derives
its ranges from the loaded data. Docked panels are rearrangeable and each can
be hidden.

**Figure 2.** The reproducibility audit panel, showing a completed audit of 40
structures under three standardization protocols. Top left: pairwise protocol
agreement under InChIKey identity, on a perceptually-uniform,
colour-vision-safe scale with values printed so colour is never the sole
encoding. Top right: the operations to which divergence was attributed by
ablation. Bottom: the individual structures affected, each with its attributed
cause, including entries marked *unattributed* where no single operation
accounted for the difference.

## 5. Conclusions

WaweKit is an open-source desktop workbench that performs the routine
operations of small-molecule cheminformatics locally and without scripting,
and adds a capability not otherwise available in an interactive tool:
measuring how sensitive a dataset's molecular identities are to
standardization protocol choice, and attributing that sensitivity to specific
normalization operations. Its layered architecture keeps the scientific
functionality importable without the interface, so the same computation serves
interactive, scripted and unattended use, with equivalence between them
enforced by the test suite.

## Author contributions

*Template using the CRediT taxonomy — complete and amend to reflect the actual
division of work.*

**Sree Vasthav Upputoori** — Conceptualization; Software; Methodology;
Writing – original draft.

**S. Madhav Varma** — Methodology; Software; Writing – original draft.

## Acknowledgements

*To be completed. WaweKit builds on RDKit, PySide6, scikit-learn, matplotlib,
ReportLab and 3Dmol.js, and on the openly released standardization pipelines of
ChEMBL and MolVS; acknowledging those projects here would be appropriate.*

## Funding and competing interests

*To be completed. State funding sources and any competing interests, or declare
that there are none.*

## Declaration of generative AI use

*To be completed by the authors, per the target journal's current policy.*

## References

1. Bento AP, Hersey A, Félix E, Landrum G, Gaulton A, Atkinson F, Bellis LJ,
   De Veij M, Leach AR. An open source chemical structure curation pipeline
   using RDKit. *J Cheminform.* 2020;12(1):51. doi:10.1186/s13321-020-00456-1
2. Hähnke VD, Kim S, Bolton EE. PubChem chemical structure standardization.
   *J Cheminform.* 2018;10(1):36. doi:10.1186/s13321-018-0293-8
3. Heller SR, McNaught A, Pletnev I, Stein S, Tchekhovskoi D. InChI, the IUPAC
   International Chemical Identifier. *J Cheminform.* 2015;7:23.
   doi:10.1186/s13321-015-0068-4

*Software cited in the text — RDKit, DataWarrior, KNIME, Datagrok, 3Dmol.js —
must be cited per each project's own instructions; these were not verified
through a bibliographic database and should be checked before submission.*
