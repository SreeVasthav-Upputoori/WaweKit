"""Check every numeric claim in the manuscript against the audit's output.

A manuscript and its results file drift apart the moment a number is typed by
hand — a rerun changes a figure, the prose keeps the old one, and nothing
catches it. This extracts every percentage and every "n = N" from the
manuscript's Results section and confirms each corresponds to a value actually
present in `chembl_results.json`.

Not a proof of correctness: it verifies that quoted numbers exist in the data,
not that they were used to support the right claim. It catches stale numbers
after a rerun, which is the failure mode that actually happens.

Usage:  python verify_numbers.py <manuscript.md>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
BENCH = HERE.parent / "research-track-R5-benchmark"
RESULTS = BENCH / "chembl_results.json"
#: The manuscript's §3.5 deliberately quotes the earlier 40-molecule pilot to
#: contrast it with the ChEMBL sample. Those numbers come from a different run,
#: so they are parsed from that run's own captured output rather than being
#: waived — otherwise the comparison section would be the one place in the
#: paper where numbers go unchecked.
PILOT_OUTPUT = BENCH / "benchmark_output.txt"
#: §3.5's sensitivity analysis re-runs the audit with one operation disabled,
#: producing its own results file. Registered here for the same reason as the
#: pilot: a number the paper quotes must be checkable against the run that
#: produced it, not exempted because it came from a variant analysis.
SENSITIVITY = BENCH / "chembl_sensitivity_nostereo.json"
#: §3.7's downstream experiment — merge counts, dataset losses, activity
#: spreads and QSAR scores — lives in its own results file.
DOWNSTREAM = HERE.parent / "research-track-R7-downstream" / "downstream_results.json"
#: §3.8's cross-toolkit comparison against production standardizers.
CROSSTOOLKIT = HERE.parent / "research-track-R9-crosstoolkit" / "crosstoolkit_results.json"
TOLERANCE = 0.0006  # quoted to 1 d.p. as a percentage


def collect_known_values(res: dict) -> tuple[set[float], set[int]]:
    """Every proportion and every count the audit legitimately produced."""
    props: set[float] = set()
    counts: set[int] = set()

    def add_prop(x: float) -> None:
        props.add(round(float(x), 6))

    add_prop(res["smiles_reproducibility"])
    add_prop(res["inchikey_reproducibility"])
    for lo, hi in (res["smiles_ci"], res["inchikey_ci"]):
        add_prop(lo)
        add_prop(hi)
    for pair in res["pairwise"]:
        add_prop(pair["inchikey"])
        add_prop(pair["smiles"])
    n_labile = max(1, res["n_labile"])
    for frac in res["cause_spectrum"].values():
        add_prop(frac)
        # the Wilson bounds the manuscript may quote for each cause
        from analyse_sample import wilson  # noqa: PLC0415 — optional dependency

        lo, hi = wilson(round(frac * n_labile), n_labile)
        add_prop(lo)
        add_prop(hi)

    # Derived proportions the prose may legitimately state.
    n = res["n_molecules"]
    if n:
        add_prop(res["n_labile"] / n)
        add_prop(res["n_with_failures"] / n)
        add_prop(res["unattributed_labile"] / max(1, res["n_labile"]))
        for key, val in res.get("composition", {}).items():  # noqa: B007
            add_prop(val / res["n_parsed"])

    for key in (
        "n_molecules",
        "n_labile",
        "n_with_failures",
        "n_parsed",
        "n_fetched",
        "n_unparseable",
        "unattributed_labile",
    ):
        if key in res:
            counts.add(int(res[key]))
    counts.update(int(v) for v in res.get("composition", {}).values())
    counts.update(round(f * n_labile) for f in res["cause_spectrum"].values())
    return props, counts


def collect_pilot_values() -> tuple[set[float], set[int]]:
    """Parse the pilot run's captured stdout for the values §3.5 quotes."""
    props: set[float] = set()
    counts: set[int] = set()
    if not PILOT_OUTPUT.is_file():
        return props, counts
    text = PILOT_OUTPUT.read_text(encoding="utf-8")
    for match in re.finditer(r"(\d+\.\d+)%", text):
        props.add(round(float(match.group(1)) / 100, 6))
    for match in re.finditer(r"(?:analyzed|molecules):\s+(\d+)", text):
        counts.add(int(match.group(1)))
    return props, counts


def collect_sensitivity_values() -> tuple[set[float], set[int]]:
    """Values from the one-operation-disabled sensitivity run (§3.5)."""
    props: set[float] = set()
    counts: set[int] = set()
    if not SENSITIVITY.is_file():
        return props, counts
    res = json.loads(SENSITIVITY.read_text(encoding="utf-8"))
    props.add(round(res["smiles"], 6))
    props.add(round(res["inchikey"], 6))
    n_labile = res["n_labile"]
    counts.add(n_labile)
    counts.add(res["n"])
    if res["n"]:
        props.add(round(n_labile / res["n"], 6))
    for frac in res["causes"].values():
        props.add(round(frac, 6))
        counts.add(round(frac * n_labile))
    return props, counts


def collect_downstream_values() -> tuple[set[float], set[int]]:
    """Values from the downstream-impact experiment (§3.7)."""
    props: set[float] = set()
    counts: set[int] = set()
    if not DOWNSTREAM.is_file():
        return props, counts
    res = json.loads(DOWNSTREAM.read_text(encoding="utf-8"))
    for per_protocol in res.values():
        n_min = min(
            (
                s["n_identities"]
                for s in per_protocol.values()
                if isinstance(s, dict) and "n_identities" in s
            ),
            default=0,
        )
        n_max = max(
            (s.get("n_input", 0) for s in per_protocol.values() if isinstance(s, dict)),
            default=0,
        )
        if n_max:
            # Fraction of the dataset lost to merging, as the prose quotes it.
            props.add(round((n_max - n_min) / n_max, 6))
        for stats in per_protocol.values():
            if not isinstance(stats, dict):
                continue
            for key in ("n_identities", "n_merged_groups", "n_input", "n_compounds_in_merges"):
                if key in stats:
                    counts.add(int(stats[key]))
            for key, val in stats.items():
                if key.startswith("discordant_at_"):
                    counts.add(int(val))
                    if stats.get("n_identities"):
                        props.add(round(val / stats["n_identities"], 6))
            if "max_spread" in stats:
                props.add(round(stats["max_spread"], 6))
            for block in ("qsar_full", "qsar_matched"):
                q = stats.get(block)
                if isinstance(q, dict):
                    counts.add(int(q["n_examples"]))
                    for metric in ("rmse_mean", "rmse_sd", "r2_mean", "spearman_mean"):
                        if metric in q:
                            props.add(round(q[metric], 6))
    return props, counts


def collect_crosstoolkit_values() -> tuple[set[float], set[int]]:
    """Values from the cross-toolkit comparison (§3.8)."""
    props: set[float] = set()
    counts: set[int] = set()
    if not CROSSTOOLKIT.is_file():
        return props, counts
    res = json.loads(CROSSTOOLKIT.read_text(encoding="utf-8"))
    props.add(round(res["smiles_reproducibility"], 6))
    props.add(round(res["inchikey_reproducibility"], 6))
    counts.add(int(res["n_molecules"]))
    counts.add(int(res["n_labile"]))
    if res["n_molecules"]:
        props.add(round(res["n_labile"] / res["n_molecules"], 6))
    for pair in res["pairwise"]:
        props.add(round(pair["inchikey"], 6))
        props.add(round(pair["smiles"], 6))
    for frac in res.get("cause_spectrum", {}).values():
        props.add(round(frac, 6))
    # The within- vs between-tool means the prose quotes.
    within = [
        p for p in res["pairwise"] if {p["a"], p["b"]} == {"MolVS default", "MolVS super-parent"}
    ]
    between = [
        p
        for p in res["pairwise"]
        if "ChEMBL pipeline" in (p["a"], p["b"]) and ("MolVS" in p["a"] or "MolVS" in p["b"])
    ]
    for group in (within, between):
        if group:
            props.add(round(sum(p["inchikey"] for p in group) / len(group), 6))
    return props, counts


def main(path: Path) -> int:
    sys.path.insert(0, str(BENCH))
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    props, counts = collect_known_values(res)
    for extra_props, extra_counts in (
        collect_pilot_values(),
        collect_sensitivity_values(),
        collect_downstream_values(),
        collect_crosstoolkit_values(),
    ):
        props |= extra_props
        counts |= extra_counts

    text = path.read_text(encoding="utf-8")
    # Only check the results-bearing body, not the reference list.
    body = text.split("## References")[0]

    unmatched: list[str] = []
    for match in re.finditer(r"(\d+\.\d+)\s?%", body):
        value = float(match.group(1)) / 100
        if not any(abs(value - p) < TOLERANCE for p in props):
            unmatched.append(
                f"{match.group(0)}  (context: …{body[max(0, match.start()-60):match.end()+20]}…)"
            )

    for match in re.finditer(r"\bn\s?=\s?([\d,]+)", body):
        value = int(match.group(1).replace(",", ""))
        if value not in counts:
            unmatched.append(
                f"n={value}  (context: …{body[max(0, match.start()-60):match.end()+20]}…)"
            )

    if unmatched:
        print(f"UNVERIFIED NUMBERS ({len(unmatched)}):\n")
        for item in unmatched:
            print(f"  - {item}\n")
        return 1

    print(f"All numeric claims in {path.name} verified against {RESULTS.name}.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1])))
