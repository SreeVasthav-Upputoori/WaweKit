"""Characterise the ChEMBL sample and run the reproducibility audit on it.

Produces every number the manuscript's Results section reports, so each figure
there is traceable to one command rather than to a note.

Two things are measured that the manuscript must disclose rather than assume:

1. **Realised within-block clustering.** The sampling design draws blocks of
   consecutive ChEMBL records (see `fetch_chembl_sample.py`), and records
   adjacent in ChEMBL often come from one publication series. Mean pairwise
   Tanimoto similarity *within* blocks is compared against *between* blocks; if
   within-block similarity is much higher, the effective sample size is smaller
   than the nominal count and the confidence interval must widen accordingly.
2. **Structural composition.** What fraction of the sample actually contains
   the features the audit can act on (multiple fragments, formal charges,
   isotopes, stereocentres). A divergence rate is only interpretable next to
   the prevalence of the features that cause divergence.

A Wilson score interval is used for the reproducibility proportions rather than
the normal approximation: it behaves correctly for proportions near 0 or 1 and
at the per-cause subgroup sizes, where the normal approximation can produce
bounds outside [0, 1].
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter
from pathlib import Path

from rdkit import Chem, RDLogger
from rdkit.Chem import DataStructs, rdFingerprintGenerator

from wawekit.services.reproducibility import analyze_divergence, compute_metrics
from wawekit.services.reproducibility.protocol import DEFAULT_PROTOCOLS, StandardOp

RDLogger.DisableLog("rdApp.*")  # the sample legitimately contains odd valences

HERE = Path(__file__).parent
SEED = 20260720


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def describe_structures(mols: list[Chem.Mol]) -> dict[str, int]:
    """Count the structural features the standardization operations act on."""
    counts = Counter()
    for mol in mols:
        if len(Chem.GetMolFrags(mol)) > 1:
            counts["multi_fragment"] += 1
        if any(a.GetFormalCharge() != 0 for a in mol.GetAtoms()):
            counts["formally_charged"] += 1
        if any(a.GetIsotope() != 0 for a in mol.GetAtoms()):
            counts["isotope_labelled"] += 1
        if Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False):
            counts["has_stereocentre"] += 1
        if any(
            a.GetSymbol() not in {"C", "H", "N", "O", "S", "P", "F", "Cl", "Br", "I"}
            for a in mol.GetAtoms()
        ):
            counts["contains_metal_or_rare_element"] += 1
    return dict(counts)


def clustering_check(records: list[dict], mols: list[Chem.Mol]) -> dict[str, float]:
    """Compare within-block vs between-block structural similarity."""
    gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    fps = [gen.GetFingerprint(m) for m in mols]

    by_block: dict[int, list[int]] = {}
    for i, rec in enumerate(records):
        by_block.setdefault(rec["block_offset"], []).append(i)

    within: list[float] = []
    for idxs in by_block.values():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                within.append(DataStructs.TanimotoSimilarity(fps[idxs[a]], fps[idxs[b]]))

    rng = random.Random(SEED)
    between: list[float] = []
    blocks = list(by_block.values())
    for _ in range(len(within) or 1000):
        b1, b2 = rng.sample(blocks, 2) if len(blocks) > 1 else (blocks[0], blocks[0])
        between.append(DataStructs.TanimotoSimilarity(fps[rng.choice(b1)], fps[rng.choice(b2)]))

    mean_w = sum(within) / len(within) if within else 0.0
    mean_b = sum(between) / len(between) if between else 0.0
    return {
        "mean_within_block_tanimoto": mean_w,
        "mean_between_block_tanimoto": mean_b,
        "n_within_pairs": len(within),
        "n_between_pairs": len(between),
    }


def main() -> int:
    records = json.loads((HERE / "chembl_sample.json").read_text(encoding="utf-8"))
    print(f"Sample records fetched: {len(records)}")

    parsed: list[dict] = []
    mols: list[Chem.Mol] = []
    n_unparseable = 0
    for rec in records:
        mol = Chem.MolFromSmiles(rec["smiles"])
        if mol is None:
            n_unparseable += 1
            continue
        parsed.append(rec)
        mols.append(mol)
    print(f"Parsed by RDKit:        {len(mols)}  (unparseable: {n_unparseable})")

    print("\n--- Structural composition ---")
    comp = describe_structures(mols)
    for key, val in sorted(comp.items(), key=lambda kv: -kv[1]):
        print(f"  {key:32} {val:6}  ({val / len(mols):.1%})")

    print("\n--- Sampling-design check (within vs between block similarity) ---")
    clust = clustering_check(parsed, mols)
    for key, val in clust.items():
        print(f"  {key:32} {val:.4f}" if isinstance(val, float) else f"  {key:32} {val}")

    print("\n--- Reproducibility audit ---")
    named = [(rec["chembl_id"], mol) for rec, mol in zip(parsed, mols, strict=True)]
    run = analyze_divergence(named, DEFAULT_PROTOCOLS, attribute_causes=True)
    metrics = compute_metrics(run)

    n = metrics.n_molecules
    smi_ok = round(metrics.smiles_reproducibility * n)
    inchi_ok = round(metrics.inchikey_reproducibility * n)
    smi_lo, smi_hi = wilson(smi_ok, n)
    inchi_lo, inchi_hi = wilson(inchi_ok, n)

    print(f"  Molecules analysed:       {n}")
    print(
        f"  SMILES reproducibility:   {metrics.smiles_reproducibility:.1%}"
        f"  95% CI [{smi_lo:.1%}, {smi_hi:.1%}]"
    )
    print(
        f"  InChIKey reproducibility: {metrics.inchikey_reproducibility:.1%}"
        f"  95% CI [{inchi_lo:.1%}, {inchi_hi:.1%}]"
    )
    print(f"  Labile molecules:         {metrics.n_labile} ({metrics.n_labile / n:.1%})")
    print(f"  Molecules with failures:  {metrics.n_with_failures}")

    print("\n  Pairwise agreement (InChIKey / SMILES):")
    for pair in metrics.pairwise:
        print(
            f"    {pair.protocol_a:14} vs {pair.protocol_b:14} "
            f"{pair.inchikey_agreement:6.1%} / {pair.smiles_agreement:6.1%}"
        )

    print("\n  Divergence cause spectrum (fraction of labile molecules):")
    n_labile = max(1, metrics.n_labile)
    for op, frac in sorted(metrics.cause_spectrum.items(), key=lambda kv: -kv[1]):
        if frac > 0:
            k = round(frac * n_labile)
            lo, hi = wilson(k, n_labile)
            print(f"    {op.value:22} {frac:6.1%}  95% CI [{lo:.1%}, {hi:.1%}]  (n={k})")

    unattributed = sum(1 for r in run.results if r.is_labile and not r.causes)
    print(f"\n  Labile but unattributed:  {unattributed} ({unattributed / n_labile:.1%} of labile)")

    summary = {
        "n_fetched": len(records),
        "n_parsed": len(mols),
        "n_unparseable": n_unparseable,
        "composition": comp,
        "clustering": clust,
        "n_molecules": n,
        "smiles_reproducibility": metrics.smiles_reproducibility,
        "smiles_ci": [smi_lo, smi_hi],
        "inchikey_reproducibility": metrics.inchikey_reproducibility,
        "inchikey_ci": [inchi_lo, inchi_hi],
        "n_labile": metrics.n_labile,
        "n_with_failures": metrics.n_with_failures,
        "pairwise": [
            {
                "a": p.protocol_a,
                "b": p.protocol_b,
                "inchikey": p.inchikey_agreement,
                "smiles": p.smiles_agreement,
            }
            for p in metrics.pairwise
        ],
        "cause_spectrum": {
            op.value: frac for op, frac in metrics.cause_spectrum.items() if frac > 0
        },
        "unattributed_labile": unattributed,
        "protocols": [p.name for p in DEFAULT_PROTOCOLS],
        "operations": [op.value for op in StandardOp],
    }
    (HERE / "chembl_results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {HERE / 'chembl_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
