"""Figure for the downstream-impact experiment.

Two panels, because the experiment has two findings that must be read together:
merging is substantial and destructive (left), yet aggregate model performance
is unmoved (right). Showing either alone would mislead.

Same print constraints as the main manuscript figures: vector output, a single
perceptually-uniform hue for magnitude, values printed so colour is never the
only encoding, recessive chrome.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).parent
RESULTS = HERE / "downstream_results.json"
OUT = HERE / "figures"

INK = "#1a1a1a"
MUTED = "#666666"
BARS = {"Minimal": "#a8c4d8", "ChEMBL-like": "#5a90b4", "Aggressive": "#22506e"}

TARGET_LABELS = {
    "CHEMBL233": "μ-opioid",
    "CHEMBL203": "EGFR",
    "CHEMBL279": "VEGFR2",
    "CHEMBL240": "hERG",
}

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 9,
        "axes.edgecolor": MUTED,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def main() -> int:
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    targets = [t for t in ("CHEMBL233", "CHEMBL203", "CHEMBL240", "CHEMBL279") if t in res]
    protocols = ["Minimal", "ChEMBL-like", "Aggressive"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.0, 3.6))
    x = np.arange(len(targets))
    width = 0.26

    # --- Left: discordant merges per 1000 compounds -----------------------
    for i, proto in enumerate(protocols):
        vals = []
        for t in targets:
            stats = res[t][proto]
            disc = stats.get("discordant_at_1.0", 0)
            vals.append(1000 * disc / max(1, stats["n_identities"]))
        bars = ax1.bar(x + (i - 1) * width, vals, width, label=proto, color=BARS[proto])
        for b, v in zip(bars, vals, strict=True):
            if v > 0:
                ax1.text(
                    b.get_x() + b.get_width() / 2,
                    v + 0.3,
                    f"{v:.1f}",
                    ha="center",
                    fontsize=7,
                    color=INK,
                )
    ax1.set_xticks(x)
    ax1.set_xticklabels([TARGET_LABELS[t] for t in targets], fontsize=8)
    ax1.set_ylabel("Discordant merges per 1000 compounds", fontsize=8)
    ax1.set_title("Training labels corrupted by merging", fontsize=9, pad=8)
    ax1.legend(fontsize=7, frameon=False)
    ax1.grid(axis="y", color="#ececec", linewidth=0.6)
    ax1.set_axisbelow(True)

    # --- Right: model RMSE, with seed-noise error bars --------------------
    for i, proto in enumerate(protocols):
        means, errs = [], []
        for t in targets:
            q = res[t][proto].get("qsar_matched", {})
            means.append(q.get("rmse_mean", np.nan))
            errs.append(q.get("rmse_sd", 0.0))
        ax2.bar(
            x + (i - 1) * width,
            means,
            width,
            yerr=errs,
            label=proto,
            color=BARS[proto],
            error_kw={"elinewidth": 1, "ecolor": INK, "capsize": 2},
        )
    ax2.set_xticks(x)
    ax2.set_xticklabels([TARGET_LABELS[t] for t in targets], fontsize=8)
    ax2.set_ylabel("Cross-validated RMSE (pIC50)", fontsize=8)
    ax2.set_title("Model performance is unaffected", fontsize=9, pad=8)
    ax2.legend(fontsize=7, frameon=False)
    ax2.grid(axis="y", color="#ececec", linewidth=0.6)
    ax2.set_axisbelow(True)

    fig.tight_layout()
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / "fig4_downstream_impact.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig4_downstream_impact.png", bbox_inches="tight", dpi=300)
    print(f"Wrote {OUT / 'fig4_downstream_impact.pdf'} / .png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
