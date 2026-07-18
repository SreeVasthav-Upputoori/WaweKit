# Module 11 — Clustering · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`
> and the two screenshots in this folder.

---

## 1. What we built

**Cluster molecules by structural similarity** — the "what families are in my
library?" question, and the natural companion to Module 10's chemical-space map.
Two algorithms, each molecule gets a **cluster id** that surfaces two ways:

1. A sortable **"Cluster" table column** (sort it and members group together).
2. A new **categorical "colour by Cluster"** mode in the chemical-space scatter,
   auto-selected after a run so the families light up on the map immediately.

The screenshots show a Butina run over 16 molecules: the alkane family collapsed
into cluster 0 (largest, sorted to the top), with the map coloured by cluster.

## 2. Two algorithms, chosen for their paradigms

| Method | Idea | Needs | When |
|---|---|---|---|
| **Butina** | sphere exclusion on Tanimoto distance | a cutoff, not K | the cheminformatics default — "cluster by similarity" |
| **K-Means** | centroid partitioning of the bit matrix | K up front | when you want exactly K groups |

**Butina** is the medicinal-chemistry standard and the default: pick the molecule
with the most neighbours within the cutoff as a centroid, remove it and its
neighbours, repeat. No K to guess; dissimilar molecules become their own
singleton clusters. It runs on Tanimoto *distance* (`1 - similarity`) via
`rdkit.ML.Cluster.Butina`. **K-Means** (sklearn) is offered as the familiar
fixed-K alternative.

**Numbered largest-first.** Both paths renumber clusters so cluster 0 is always
the biggest — a stable convention the table sort and the colour palette both rely
on. K-Means labels are arbitrary, so we remap them by descending size (there's a
test pinning this).

## 3. A cluster id is relational — cached, but carrying its context

This is the same fork as similarity (Module 7), and the opposite of descriptors.
A cluster id is *not* intrinsic: load different molecules and the same structure
lands in a different cluster. So — exactly as `SimilarityScore` carries its
`SimilarityQuery` — a `ClusterAssignment` carries the `ClusterRun` that produced
it (method, parameters, cluster count). The table cell shows just the id; the
tooltip carries the run, so an id is never read without the context that makes it
mean something. And like stale similarity scores, a molecule that falls out of a
fresh run (no fingerprint) has its old assignment **actively cleared**, never
left stale.

Contrast with Module 10's projection, which is *also* relational but is **not**
cached — because its output (x, y) is only ever consumed by one panel. A cluster
id is consumed by the table column *and* the scatter colouring, so caching it on
the record is what lets both read it without a side channel.

## 4. The satisfying integration: categorical colour-by-cluster

Module 10's colour-by was continuous only (a viridis gradient + colourbar). A
cluster id is a **category**, not a scale — painting it with a gradient would be
misleading. So the panel grew a categorical branch: for the "Cluster" dimension
it uses a qualitative palette (`tab20`) keyed by `id % 20`, with **no colourbar**
(a gradient legend for categories is nonsense). Missing values stay grey, as
everywhere. After a clustering run, `_on_cluster_finished` calls
`space_panel.set_color_by("Cluster")`, so if a projection is on screen the map
recolours by family instantly — the two modules click together.

## 5. Reuse tally (the architecture paying off)

- `compute_fingerprints` (Module 6) — ensures a consistent encoding, exactly as
  chemical space does. Fourth consumer.
- `FingerprintOptionsWidget` (Module 6/7) — the clustering dialog is its
  **fourth** consumer; the QVariant-coercion and enable/disable rules come free.
- `FunctionWorker` (Module 2) — the background seam, now on its eighth job.
- The table's cached-column + `_columns_updated` repaint machinery (Module 5).

Almost none of this module is new plumbing; it is mostly *composition* of parts
built earlier. That is the dividend of the layered discipline.

## 6. Verification

- `pytest`: **221 tests** (was 212) — Butina assigns everyone, largest-first
  numbering, lower cutoff → more clusters, K-Means honours K and is deterministic,
  on-demand fingerprinting, the too-few guard, and re-cluster overwriting a stale
  run. Clean under `ruff`, `black`, and `-W error::DeprecationWarning`.
- Screenshot-verified: the map coloured categorically by cluster, and the Cluster
  column populated and sorted (alkanes as cluster 0).

## 7. Research lens

Clustering is textbook — but it sits right next to two publishable questions,
neither a GUI wrapper:

- **Cutoff-stability / cluster-validity for fingerprint spaces.** Butina's whole
  behaviour hinges on one cutoff nobody principled sets. A **stability curve** —
  how the clustering (via a validity index like silhouette adapted to Tanimoto,
  or cluster-count elbow) changes as the cutoff sweeps — turns a guessed number
  into a defended one, and flags datasets that have no natural cutoff at all. We
  already compute the pairwise-distance data the curve needs.
- **Cluster ↔ scaffold agreement.** We now have two independent groupings of the
  same molecules: similarity clusters (this module) and Bemis–Murcko scaffolds
  (Module 8). Quantifying where they *disagree* — similarity clusters that split
  a scaffold, or merge several — surfaces exactly the scaffold-hop and
  R-group-diversity cases medicinal chemists care about, and is a concrete
  contribution to how libraries are characterised. Both groupings are already
  cached on the record, one join away.

Both still rank behind Module 4's standardization-divergence benchmark, but the
cluster↔scaffold agreement analysis is unusually cheap to prototype now.
