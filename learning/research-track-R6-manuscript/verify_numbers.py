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


def main(path: Path) -> int:
    sys.path.insert(0, str(BENCH))
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    props, counts = collect_known_values(res)
    pilot_props, pilot_counts = collect_pilot_values()
    props |= pilot_props
    counts |= pilot_counts

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
