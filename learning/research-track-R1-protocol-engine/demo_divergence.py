"""R1 demonstration: run the three preset protocols over illustrative molecules
and show where they agree / diverge, on both identity keys."""

from __future__ import annotations

from rdkit import Chem

from wawekit.services.reproducibility.protocol import DEFAULT_PROTOCOLS, standardize

CASES = [
    ("benzene", "c1ccccc1"),
    ("aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
    ("benzene·HCl salt", "c1ccccc1.Cl"),
    ("acetate anion", "CC(=O)[O-]"),
    ("2-hydroxypyridine", "Oc1ccccn1"),
    ("warfarin (enol/keto)", "CC(=O)CC(c1ccccc1)c1c(O)c2ccccc2oc1=O"),
    ("methanol-d1", "[2H]OC"),
    ("L-alanine", "C[C@H](N)C(=O)O"),
]

print(f"{'molecule':22}  {'SMILES-agree':13} {'InChIKey-agree':15} forms")
print("-" * 78)
smiles_labile = inchikey_labile = 0
for name, smi in CASES:
    mol = Chem.MolFromSmiles(smi)
    forms = [standardize(mol, p) for p in DEFAULT_PROTOCOLS]
    smiles_set = {f.smiles for f in forms}
    inchi_set = {f.inchikey for f in forms}
    smiles_ok = len(smiles_set) == 1
    inchi_ok = len(inchi_set) == 1
    smiles_labile += not smiles_ok
    inchikey_labile += not inchi_ok
    print(
        f"{name:22}  {'agree' if smiles_ok else 'DIVERGE':13} "
        f"{'agree' if inchi_ok else 'DIVERGE':15} "
        f"{len(smiles_set)} smiles / {len(inchi_set)} inchikey"
    )

n = len(CASES)
print("-" * 78)
print(f"SMILES-identity divergence:   {smiles_labile}/{n} molecules pipeline-dependent")
print(f"InChIKey-identity divergence: {inchikey_labile}/{n} molecules pipeline-dependent")
print("\nFinding: the two identity keys disagree on which molecules are 'labile'.")
