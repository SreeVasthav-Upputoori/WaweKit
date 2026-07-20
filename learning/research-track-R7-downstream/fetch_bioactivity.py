"""Fetch ChEMBL bioactivity data for the downstream-impact experiment.

The reproducibility audit (R5) measures *whether* protocols disagree. It cannot
say whether that disagreement matters. This experiment supplies the missing
link: when a protocol merges two distinct input compounds into one standardized
identity, does it merge compounds with *genuinely different measured activity*?
If so, standardization has destroyed real structure–activity signal and
injected contradictory labels into the training set.

Targets are chosen to span the cases where this should and should not happen:

* **CHEMBL233 (mu-opioid receptor)** — opioid pharmacology is strongly
  enantioselective (levorphanol vs dextrorphan being the textbook case), so
  stereochemistry-stripping should be actively harmful here.
* **CHEMBL203 (EGFR)**, **CHEMBL279 (VEGFR2)** — large, well-populated kinase
  sets; the workhorse case for QSAR.
* **CHEMBL240 (hERG)** — a safety endpoint where mispredicting is costly.

Only IC50 measurements in nM are kept, converted to pIC50. Where a compound has
several measurements the median is used, which is the standard aggregation and
avoids letting one outlying assay dominate.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://www.ebi.ac.uk/chembl/api/data/activity"
OUT_DIR = Path(__file__).parent
USER_AGENT = "WaweKit-downstream-experiment/1.0 (academic research)"
PAGE = 1000
MAX_PER_TARGET = 12000

TARGETS = {
    "CHEMBL233": "mu-opioid receptor",
    "CHEMBL203": "EGFR",
    "CHEMBL279": "VEGFR2",
    "CHEMBL240": "hERG",
}


def _get(url: str, retries: int = 4) -> dict:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=90) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == retries - 1:
                raise
            wait = 2**attempt
            print(f"    retry {attempt + 1} after {type(exc).__name__} ({wait}s)", flush=True)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def fetch_target(target_id: str, label: str) -> list[dict]:
    """Fetch IC50 activities with structures for one target."""
    print(f"\n{target_id} ({label})", flush=True)
    records: list[dict] = []
    offset = 0
    while offset < MAX_PER_TARGET:
        url = (
            f"{API}?target_chembl_id={target_id}&standard_type=IC50"
            f"&format=json&limit={PAGE}&offset={offset}"
        )
        data = _get(url)
        batch = data.get("activities", [])
        if not batch:
            break
        for act in batch:
            smiles = act.get("canonical_smiles")
            value = act.get("standard_value")
            units = act.get("standard_units")
            relation = act.get("standard_relation")
            # Censored values ("<", ">") are not usable as regression targets.
            if not smiles or value is None or units != "nM" or relation != "=":
                continue
            try:
                nm = float(value)
            except (TypeError, ValueError):
                continue
            if nm <= 0:
                continue
            records.append(
                {
                    "target": target_id,
                    "molecule_chembl_id": act.get("molecule_chembl_id"),
                    "smiles": smiles,
                    "nM": nm,
                }
            )
        offset += PAGE
        total = data["page_meta"]["total_count"]
        print(
            f"    {min(offset, total)}/{min(total, MAX_PER_TARGET)} — kept {len(records)}",
            flush=True,
        )
        if offset >= total:
            break
        time.sleep(0.15)
    return records


def main() -> int:
    """Run the downstream-impact experiment across all targets."""
    all_records: list[dict] = []
    for target_id, label in TARGETS.items():
        all_records.extend(fetch_target(target_id, label))

    out = OUT_DIR / "bioactivity_raw.json"
    out.write_text(json.dumps(all_records), encoding="utf-8")
    print(f"\nTotal usable measurements: {len(all_records)}")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
