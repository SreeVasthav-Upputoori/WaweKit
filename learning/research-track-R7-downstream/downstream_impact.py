"""Measure the downstream consequences of standardization protocol choice.

The reproducibility audit establishes that protocols disagree about molecular
identity. This asks the question that determines whether that matters: **when a
protocol merges two distinct compounds into one identity, do those compounds
have the same measured biology?**

Three consequences are measured, in increasing order of what a modeller cares
about:

1. **Dataset size.** Grouping by standardized identity is exactly what
   deduplication does, so protocol choice silently changes how many compounds
   a "dataset" contains.

2. **Discordant merges — the substantive harm.** When two compounds with
   *different* measured activity collapse to one identity, the merge destroys
   real structure-activity signal. Whatever aggregation follows (mean, median)
   invents an activity that neither compound has. A merge spanning more than
   `DISCORDANT_LOG` log units is counted as discordant; that threshold is the
   conventional activity-cliff scale, and results are reported across a range
   of thresholds so the finding does not rest on one arbitrary cut.

3. **QSAR model performance.** The same model, features and protocol-independent
   evaluation procedure trained on each protocol's version of the same source
   data. Repeated k-fold cross-validation over several seeds, so the spread
   attributable to protocol choice can be compared against the spread
   attributable to random resampling — a difference smaller than seed noise is
   not a difference.

Design note: comparing models across protocols is only fair if the *evaluation*
is comparable. Each protocol produces a differently-sized dataset, and smaller
datasets are generally easier or harder to fit, so raw performance is
confounded with dataset size.

The obvious size control — restricting to identities common to all protocols —
does **not** work here, and the reason is worth stating because it is easy to
get wrong: identities are InChIKeys *of the standardized structure*, so a
molecule that a protocol actually changed receives a different key under that
protocol. Intersecting the keysets therefore selects precisely the molecules on
which all protocols agreed, on which every protocol's dataset is identical by
construction and no performance difference can exist. It measures nothing.

The control used instead is a random subsample of each protocol's dataset down
to the smallest dataset's size, with a fixed seed: dataset size is held equal
while the standardization that produced it varies.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from math import log10
from pathlib import Path

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import rdFingerprintGenerator
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import KFold

from wawekit.services.reproducibility.protocol import (
    PRESET_AGGRESSIVE,
    PRESET_CHEMBL_LIKE,
    PRESET_MINIMAL,
    standardize,
)

RDLogger.DisableLog("rdApp.*")

HERE = Path(__file__).parent
RAW = HERE / "bioactivity_raw.json"
DISCORDANT_LOG = 1.0  # log units; conventional activity-cliff scale
THRESHOLDS = (0.5, 1.0, 1.5, 2.0)
SEEDS = (11, 22, 33)  # 3 seeds x 5 folds = 15 CV estimates per configuration
N_FOLDS = 5
SUBSAMPLE_SEED = 20260720
PROTOCOLS = (PRESET_MINIMAL, PRESET_CHEMBL_LIKE, PRESET_AGGRESSIVE)


def load_compounds() -> dict[str, dict[str, float]]:
    """Return {target: {smiles: median pIC50}} from the raw activity records."""
    by_target: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for rec in json.loads(RAW.read_text(encoding="utf-8")):
        # pIC50 = -log10(molar); standard_value is in nM.
        by_target[rec["target"]][rec["smiles"]].append(-log10(rec["nM"] * 1e-9))
    return {
        target: {smi: statistics.median(vals) for smi, vals in compounds.items()}
        for target, compounds in by_target.items()
    }


def group_by_identity(compounds: dict[str, float], protocol) -> tuple[dict[str, dict], int]:
    """Group input compounds by their standardized InChIKey under `protocol`.

    The *standardized* SMILES is retained alongside the members, because that —
    not an arbitrary input structure — is what a real pipeline goes on to
    featurise. Using an input structure here would silently give the model
    stereochemistry that the protocol had just removed.
    """
    groups: dict[str, dict] = {}
    n_failed = 0
    for smiles, activity in compounds.items():
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            n_failed += 1
            continue
        form = standardize(mol, protocol)
        if not form.ok:
            n_failed += 1
            continue
        entry = groups.setdefault(form.inchikey, {"std_smiles": form.smiles, "members": []})
        entry["members"].append((smiles, activity))
    return groups, n_failed


def merge_stats(groups: dict[str, dict]) -> dict:
    """Count merges and how many destroy real activity differences."""
    merged = {k: v for k, v in groups.items() if len(v["members"]) > 1}
    spreads = [
        max(a for _, a in v["members"]) - min(a for _, a in v["members"]) for v in merged.values()
    ]
    stats = {
        "n_identities": len(groups),
        "n_merged_groups": len(merged),
        "n_compounds_in_merges": sum(len(v["members"]) for v in merged.values()),
        "max_spread": max(spreads) if spreads else 0.0,
        "median_spread": statistics.median(spreads) if spreads else 0.0,
    }
    for threshold in THRESHOLDS:
        stats[f"discordant_at_{threshold}"] = sum(1 for s in spreads if s > threshold)
    return stats


def worst_merges(groups: dict[str, dict], top: int = 10) -> list[dict]:
    """Return the merges that fused the most divergent activities."""
    merged = [
        {
            "inchikey": k,
            "std_smiles": v["std_smiles"],
            "n": len(v["members"]),
            "spread": max(a for _, a in v["members"]) - min(a for _, a in v["members"]),
            "activities": [round(a, 2) for _, a in v["members"]],
            "inputs": [s for s, _ in v["members"]],
        }
        for k, v in groups.items()
        if len(v["members"]) > 1
    ]
    merged.sort(key=lambda m: -m["spread"])
    return merged[:top]


def featurise(smiles_list: list[str]) -> np.ndarray:
    """Morgan fingerprints **including chirality**.

    Chirality is deliberately encoded: with an achiral fingerprint, enantiomers
    are already indistinguishable to the model and stereochemistry-stripping
    could not possibly change the features — the experiment would answer a
    question nobody asked. Including it reflects a modeller who has chosen to
    represent stereochemistry, which is the setting where losing it can hurt.
    """
    gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048, includeChirality=True)
    rows = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        arr = np.zeros(2048, dtype=np.int8)
        if mol is not None:
            for bit in gen.GetFingerprint(mol).GetOnBits():
                arr[bit] = 1
        rows.append(arr)
    return np.array(rows)


def qsar_scores(groups: dict[str, dict], subsample_to: int | None = None) -> dict[str, float]:
    """Cross-validated model performance on one protocol's merged dataset.

    Each standardized identity becomes one training example, featurised from
    the *standardized* structure and labelled with the mean of the merged
    compounds' activities — exactly what a modeller does after deduplicating,
    and exactly where a discordant merge does its damage.

    ``subsample_to`` draws a fixed-seed random subset so every protocol is
    evaluated at identical dataset size (see the module docstring for why the
    intersection-of-identities control does not work).
    """
    items = sorted(groups.items())  # deterministic order before any sampling
    if subsample_to is not None and len(items) > subsample_to:
        rng = np.random.default_rng(SUBSAMPLE_SEED)
        idx = rng.choice(len(items), size=subsample_to, replace=False)
        items = [items[i] for i in sorted(idx)]
    if len(items) < 100:
        return {}
    smiles = [v["std_smiles"] for _, v in items]
    y = np.array([statistics.mean(a for _, a in v["members"]) for _, v in items])
    X = featurise(smiles)

    rmses, r2s, rhos = [], [], []
    for seed in SEEDS:
        kf = KFold(n_splits=N_FOLDS, shuffle=True, random_state=seed)
        for train_idx, test_idx in kf.split(X):
            model = RandomForestRegressor(
                n_estimators=200, n_jobs=-1, random_state=seed, min_samples_leaf=2
            )
            model.fit(X[train_idx], y[train_idx])
            pred = model.predict(X[test_idx])
            rmses.append(float(np.sqrt(mean_squared_error(y[test_idx], pred))))
            r2s.append(float(r2_score(y[test_idx], pred)))
            rhos.append(float(spearmanr(y[test_idx], pred).statistic))
    return {
        "n_examples": len(items),
        "rmse_mean": float(np.mean(rmses)),
        "rmse_sd": float(np.std(rmses)),
        "r2_mean": float(np.mean(r2s)),
        "r2_sd": float(np.std(r2s)),
        "spearman_mean": float(np.mean(rhos)),
        "spearman_sd": float(np.std(rhos)),
    }


def main() -> int:
    """Run the downstream-impact experiment across all targets."""
    data = load_compounds()
    results: dict[str, dict] = {}

    for target, compounds in sorted(data.items()):
        print(f"\n=== {target}: {len(compounds)} unique input structures ===", flush=True)
        per_protocol = {}
        grouped = {}
        for protocol in PROTOCOLS:
            groups, n_failed = group_by_identity(compounds, protocol)
            grouped[protocol.name] = groups
            stats = merge_stats(groups)
            stats["n_failed"] = n_failed
            stats["n_input"] = len(compounds)
            per_protocol[protocol.name] = stats
            print(
                f"  {protocol.name:13} identities={stats['n_identities']:6} "
                f"merged_groups={stats['n_merged_groups']:5} "
                f"discordant>1log={stats['discordant_at_1.0']:5} "
                f"max_spread={stats['max_spread']:.2f}",
                flush=True,
            )

        # Worst discordant merges, kept as concrete evidence: a reviewer should
        # be able to inspect the actual structures whose activities were fused.
        worst = worst_merges(grouped["Aggressive"], top=10)
        per_protocol["_worst_merges_aggressive"] = worst
        if worst:
            print("  worst discordant merges under Aggressive:", flush=True)
            for w in worst[:5]:
                print(
                    f"    spread={w['spread']:.2f} log  n={w['n']}  " f"pIC50 {w['activities']}",
                    flush=True,
                )

        smallest = min(len(g) for g in grouped.values())
        print(f"  QSAR (3x5-fold CV; size-matched n={smallest}):", flush=True)
        for name, groups in grouped.items():
            full = qsar_scores(groups)
            matched = qsar_scores(groups, subsample_to=smallest)
            if full:
                per_protocol[name]["qsar_full"] = full
                print(
                    f"    {name:13} full     n={full['n_examples']:6} "
                    f"RMSE={full['rmse_mean']:.3f}+-{full['rmse_sd']:.3f} "
                    f"R2={full['r2_mean']:.3f}",
                    flush=True,
                )
            if matched:
                per_protocol[name]["qsar_matched"] = matched
                print(
                    f"    {name:13} matched  n={matched['n_examples']:6} "
                    f"RMSE={matched['rmse_mean']:.3f}+-{matched['rmse_sd']:.3f} "
                    f"R2={matched['r2_mean']:.3f}",
                    flush=True,
                )

        results[target] = per_protocol

    out = HERE / "downstream_results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
