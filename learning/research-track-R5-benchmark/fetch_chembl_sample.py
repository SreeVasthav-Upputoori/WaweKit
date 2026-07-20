"""Fetch a reproducible random sample of ChEMBL structures for the benchmark.

Sampling design (stated here because it constrains what the results can claim)
-----------------------------------------------------------------------------
ChEMBL's REST API paginates by offset, and there is no server-side "random
record" endpoint. Drawing N independent single-record requests would need N
round trips (impractical at N=5000), so this uses **cluster sampling**: K
independent uniformly-random offsets into the molecule table, each returning a
block of B consecutive records (N = K x B).

The tradeoff is deliberate and must be disclosed in the manuscript: records
adjacent in ChEMBL's ordering often originate from the same publication or
assay series, so a block can contain structurally related analogues. Small
blocks (B=10) with many independent draws (K=500) keep within-block clustering
low relative to a few large blocks; `analyse_sample.py` measures the realised
clustering so the effect is reported rather than assumed.

Reproducibility: the RNG seed is fixed and the drawn offsets are written to
`chembl_sample_offsets.json` alongside the structures, so the exact sample can
be regenerated or audited.
"""

from __future__ import annotations

import json
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://www.ebi.ac.uk/chembl/api/data/molecule"
SEED = 20260720
N_BLOCKS = 500
BLOCK = 10
OUT_DIR = Path(__file__).parent
USER_AGENT = "WaweKit-reproducibility-benchmark/1.0 (academic research)"


def _get(url: str, retries: int = 4) -> dict:
    """GET with polite retry/backoff; a public API deserves being nice to."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == retries - 1:
                raise
            wait = 2**attempt
            print(f"  retry {attempt + 1} after {type(exc).__name__} (waiting {wait}s)", flush=True)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def main() -> int:
    total = _get(f"{API}?format=json&limit=1")["page_meta"]["total_count"]
    print(f"ChEMBL molecule table: {total} records", flush=True)

    rng = random.Random(SEED)
    max_offset = total - BLOCK
    offsets = sorted(rng.randrange(0, max_offset) for _ in range(N_BLOCKS))

    records: list[dict] = []
    seen: set[str] = set()
    for i, offset in enumerate(offsets, start=1):
        data = _get(f"{API}?format=json&limit={BLOCK}&offset={offset}")
        for mol in data.get("molecules", []):
            structures = mol.get("molecule_structures") or {}
            smiles = structures.get("canonical_smiles")
            chembl_id = mol.get("molecule_chembl_id")
            # Skip records with no structure (biotherapeutics, sequences) and
            # any duplicate a block overlap may have produced.
            if not smiles or not chembl_id or chembl_id in seen:
                continue
            seen.add(chembl_id)
            props = mol.get("molecule_properties") or {}
            records.append(
                {
                    "chembl_id": chembl_id,
                    "smiles": smiles,
                    "block_offset": offset,
                    "max_phase": mol.get("max_phase"),
                    "mw": (props or {}).get("full_mwt"),
                    "molecule_type": mol.get("molecule_type"),
                }
            )
        if i % 25 == 0:
            print(f"  block {i}/{N_BLOCKS} — {len(records)} structures", flush=True)
        time.sleep(0.12)  # be polite to a free public API

    (OUT_DIR / "chembl_sample_offsets.json").write_text(
        json.dumps({"seed": SEED, "n_blocks": N_BLOCKS, "block": BLOCK, "offsets": offsets}),
        encoding="utf-8",
    )
    (OUT_DIR / "chembl_sample.json").write_text(json.dumps(records), encoding="utf-8")

    smi = OUT_DIR / "chembl_sample.smi"
    with smi.open("w", encoding="utf-8") as handle:
        handle.write(f"# ChEMBL random sample: seed={SEED} blocks={N_BLOCKS} block_size={BLOCK}\n")
        handle.write(f"# Fetched from {API} — {len(records)} structures with SMILES\n")
        for rec in records:
            handle.write(f"{rec['smiles']} {rec['chembl_id']}\n")

    print(f"\nWrote {len(records)} structures to {smi}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
