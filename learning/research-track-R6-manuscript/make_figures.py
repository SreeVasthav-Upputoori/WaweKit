"""Generate the manuscript figures from `chembl_results.json`.

Every figure is built from the audit's own output file, so no number in a
figure can drift from the number in the text.

Design constraints are journal constraints, not dashboard constraints:

* **Vector output (PDF) plus a PNG preview.** Journals want scalable line art.
* **Sequential data gets a single perceptually-uniform hue ramp.** Protocol
  agreement runs 0 → 1 with no meaningful midpoint, so a diverging ramp
  (red-yellow-green and friends) would imply structure that is not there — and
  red-green is precisely the pairing that fails for colour-vision deficiency.
  `viridis` is perceptually uniform, CVD-safe, and monotonic in greyscale, so
  it survives black-and-white printing.
* **Colour is never the sole encoding.** Every heatmap cell carries its value
  as text; every bar carries a direct label. A reader who cannot distinguish
  the hues loses nothing.
* **Recessive chrome.** No gridlines competing with data, no boxes around
  plots, no legend where a direct label does the job.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: no display needed
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).parent
RESULTS = HERE.parent / "research-track-R5-benchmark" / "chembl_results.json"
FIG_DIR = HERE / "figures"

# Muted, print-safe ink colours; text never wears a series colour.
INK = "#1a1a1a"
MUTED = "#666666"
BAR = "#31688e"  # a mid-ramp viridis blue, legible in greyscale

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 9,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 150,
    }
)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval — matches analyse_sample.py exactly."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _save(fig: plt.Figure, stem: str) -> None:
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{stem}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"  wrote {stem}.pdf / .png")


def figure_agreement_matrix(res: dict) -> None:
    """Fig 1 — pairwise protocol agreement, both identity conventions."""
    names = res["protocols"]
    n = len(names)

    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4), sharey=True)
    fig.subplots_adjust(wspace=0.12)
    for idx, (ax, key, label) in enumerate(
        zip(
            axes,
            ("inchikey", "smiles"),
            ("InChIKey identity", "Canonical-SMILES identity"),
            strict=True,
        )
    ):
        matrix = np.ones((n, n))
        for pair in res["pairwise"]:
            i, j = names.index(pair["a"]), names.index(pair["b"])
            matrix[i, j] = matrix[j, i] = pair[key]

        im = ax.imshow(matrix, vmin=0, vmax=1, cmap="viridis")
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
        # Both panels share one identical y-axis; labelling only the leftmost
        # avoids the right panel's tick labels overprinting the left panel's
        # cells (which is exactly what happened before this was shared).
        if idx == 0:
            ax.set_yticklabels(names, fontsize=8)
        ax.set_title(label, fontsize=9, pad=8)
        for i in range(n):
            for j in range(n):
                value = matrix[i, j]
                ax.text(
                    j,
                    i,
                    f"{value:.1%}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if value < 0.6 else "#101010",
                )
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)

    cbar = fig.colorbar(im, ax=axes, fraction=0.03, pad=0.02)
    cbar.set_label("Pairwise agreement", fontsize=8)
    cbar.ax.tick_params(labelsize=7, length=2)
    cbar.outline.set_visible(False)
    _save(fig, "fig1_agreement_matrix")


def figure_cause_spectrum(res: dict) -> None:
    """Fig 2 — divergence cause spectrum with 95% Wilson intervals."""
    spectrum = res["cause_spectrum"]
    n_labile = max(1, res["n_labile"])
    items = sorted(spectrum.items(), key=lambda kv: kv[1])

    labels = [op.replace("_", " ") for op, _ in items]
    values = [v for _, v in items]
    counts = [round(v * n_labile) for v in values]
    los, his = zip(*(wilson(k, n_labile) for k in counts), strict=True) if counts else ((), ())

    fig, ax = plt.subplots(figsize=(6.4, 0.42 * len(labels) + 1.5))
    y = np.arange(len(labels))
    ax.barh(y, values, color=BAR, height=0.62)
    ax.errorbar(
        values,
        y,
        xerr=[np.array(values) - np.array(los), np.array(his) - np.array(values)],
        fmt="none",
        ecolor=INK,
        elinewidth=1,
        capsize=3,
    )
    for yi, (val, hi, k) in enumerate(zip(values, his, counts, strict=True)):
        ax.text(hi + 0.015, yi, f"{val:.1%}  (n={k})", va="center", fontsize=8, color=INK)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, min(1.0, max(his) + 0.22) if his else 1.0)
    ax.set_xlabel(f"Fraction of divergent molecules (n = {res['n_labile']})", fontsize=8)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax.tick_params(length=2)
    ax.grid(axis="x", color="#e8e8e8", linewidth=0.6)
    ax.set_axisbelow(True)
    _save(fig, "fig2_cause_spectrum")


def figure_reproducibility_summary(res: dict) -> None:
    """Fig 3 — headline reproducibility under each identity convention."""
    fig, ax = plt.subplots(figsize=(5.2, 2.2))

    labels = ["Canonical SMILES", "InChIKey"]
    values = [res["smiles_reproducibility"], res["inchikey_reproducibility"]]
    cis = [res["smiles_ci"], res["inchikey_ci"]]

    y = np.arange(len(labels))
    ax.barh(y, values, color=BAR, height=0.5)
    ax.errorbar(
        values,
        y,
        xerr=[
            [v - lo for v, (lo, _) in zip(values, cis, strict=True)],
            [hi - v for v, (_, hi) in zip(values, cis, strict=True)],
        ],
        fmt="none",
        ecolor=INK,
        elinewidth=1,
        capsize=3,
    )
    for yi, (val, (lo, hi)) in enumerate(zip(values, cis, strict=True)):
        ax.text(hi + 0.012, yi, f"{val:.1%}  [{lo:.1%}–{hi:.1%}]", va="center", fontsize=8)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel(f"Molecules where all protocols agree (n = {res['n_molecules']})", fontsize=8)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    ax.tick_params(length=2)
    ax.grid(axis="x", color="#e8e8e8", linewidth=0.6)
    ax.set_axisbelow(True)
    _save(fig, "fig3_reproducibility")


def main() -> int:
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    print(f"Generating figures from {RESULTS.name} (n={res['n_molecules']}):")
    figure_agreement_matrix(res)
    figure_cause_spectrum(res)
    figure_reproducibility_summary(res)
    print(f"\nFigures in {FIG_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
