"""Cross-toolkit standardization divergence on the ChEMBL random sample.

The main audit compares protocols composed from RDKit operations, which is
what makes cause attribution possible but leaves the headline figures
describing a bracket *we* defined rather than the disagreement practitioners
actually meet. This experiment replaces the constructed protocols with the
production pipelines themselves:

* **ChEMBL pipeline** — the ``chembl_structure_pipeline`` package, i.e. the
  code the database runs, in its documented two-stage form.
* **MolVS default** — ``Standardizer.standardize()``, which normalises without
  removing salts.
* **MolVS super-parent** — ``Standardizer.super_parent()``, which additionally
  strips fragments, charge, isotopes and stereochemistry.
* **ChEMBL-like (RDKit)** — our composed approximation, included precisely so
  that it can be checked against the real pipeline. If the approximation is
  faithful the two agree; where they disagree, the main manuscript's
  "ChEMBL-like" label is overstated and that needs reporting.

Two questions are answered that the within-RDKit audit cannot address:

1. How much do real, independently-developed standardizers disagree?
2. Is disagreement *between* tools larger than disagreement between
   configurations *within* one tool? A finding either way changes the practical
   advice: the first says "record which tool", the second says "recording the
   tool is not enough".

Run on the same seeded 4,972-structure ChEMBL sample as the main audit, so the
two sets of numbers are directly comparable.
"""

from __future__ import annotations

import json
from pathlib import Path

from rdkit import Chem, RDLogger

from wawekit.services.reproducibility import analyze_divergence, compute_metrics
from wawekit.services.reproducibility.protocol import PRESET_CHEMBL_LIKE, PRESET_MINIMAL
from wawekit.services.reproducibility.standardizers import (
    ChEMBLPipelineStandardizer,
    MolVSStandardizer,
    ProtocolStandardizer,
    available_standardizers,
)

RDLogger.DisableLog("rdApp.*")

HERE = Path(__file__).parent
SAMPLE = HERE.parent / "research-track-R5-benchmark" / "chembl_sample.json"


def main() -> int:
    """Run the cross-toolkit audit and write its results."""
    availability = available_standardizers()
    print("External standardizers available:", availability)
    if not all(availability.values()):
        print("  (missing packages: install chembl_structure_pipeline and molvs)")

    records = json.loads(SAMPLE.read_text(encoding="utf-8"))
    named = []
    for rec in records:
        mol = Chem.MolFromSmiles(rec["smiles"])
        if mol is not None:
            named.append((rec["chembl_id"], mol))
    print(f"Structures: {len(named)}")

    standardizers = (
        ProtocolStandardizer(PRESET_MINIMAL),
        ProtocolStandardizer(PRESET_CHEMBL_LIKE),
        ChEMBLPipelineStandardizer(),
        MolVSStandardizer(super_parent=False),
        MolVSStandardizer(super_parent=True),
    )
    print("Comparing:", ", ".join(s.name for s in standardizers))
    print()

    run = analyze_divergence(named, standardizers, attribute_causes=True)
    metrics = compute_metrics(run)

    n = metrics.n_molecules
    print(f"  Structures analysed:      {n}")
    print(f"  SMILES reproducibility:   {metrics.smiles_reproducibility:.1%}")
    print(f"  InChIKey reproducibility: {metrics.inchikey_reproducibility:.1%}")
    print(f"  Divergent:                {metrics.n_labile} ({metrics.n_labile / n:.1%})")
    print(f"  With a failure:           {metrics.n_with_failures}")

    print("\n  Pairwise agreement (InChIKey / SMILES):")
    for pair in metrics.pairwise:
        print(
            f"    {pair.protocol_a:22} vs {pair.protocol_b:22} "
            f"{pair.inchikey_agreement:6.1%} / {pair.smiles_agreement:6.1%}"
        )

    # Does our composed approximation actually reproduce the real pipeline?
    approximation = next(
        (
            p
            for p in metrics.pairwise
            if {p.protocol_a, p.protocol_b} == {"ChEMBL-like", "ChEMBL pipeline"}
        ),
        None,
    )
    if approximation is not None:
        print(
            f"\n  Fidelity of the composed 'ChEMBL-like' protocol to the real pipeline: "
            f"{approximation.inchikey_agreement:.1%} (InChIKey)"
        )

    # Within-tool vs between-tool: the comparison that changes the advice.
    within = [
        p
        for p in metrics.pairwise
        if {p.protocol_a, p.protocol_b} == {"MolVS default", "MolVS super-parent"}
    ]
    between = [
        p
        for p in metrics.pairwise
        if "ChEMBL pipeline" in (p.protocol_a, p.protocol_b)
        and ("MolVS" in p.protocol_a or "MolVS" in p.protocol_b)
    ]
    if within and between:
        w = within[0].inchikey_agreement
        b = sum(p.inchikey_agreement for p in between) / len(between)
        print(f"\n  Within-tool agreement (MolVS configs):   {w:.1%}")
        print(f"  Between-tool agreement (ChEMBL vs MolVS): {b:.1%}")
        verdict = "WITHIN-tool" if w < b else "BETWEEN-tool"
        print(f"  -> {verdict} configuration differences dominate.")

    print("\n  Cause spectrum (attributable via the composed protocols only):")
    for op, frac in sorted(metrics.cause_spectrum.items(), key=lambda kv: -kv[1]):
        if frac > 0:
            print(f"    {op.value:22} {frac:6.1%}")

    summary = {
        "n_molecules": n,
        "smiles_reproducibility": metrics.smiles_reproducibility,
        "inchikey_reproducibility": metrics.inchikey_reproducibility,
        "n_labile": metrics.n_labile,
        "n_with_failures": metrics.n_with_failures,
        "standardizers": [s.name for s in standardizers],
        "pairwise": [
            {
                "a": p.protocol_a,
                "b": p.protocol_b,
                "inchikey": p.inchikey_agreement,
                "smiles": p.smiles_agreement,
            }
            for p in metrics.pairwise
        ],
        "cause_spectrum": {op.value: f for op, f in metrics.cause_spectrum.items() if f > 0},
    }
    out = HERE / "crosstoolkit_results.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
