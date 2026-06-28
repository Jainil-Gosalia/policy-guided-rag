"""Generate the paper's figures (vector PDFs) from the reported result numbers.

Run:  python paper/figures/make_figures.py
Outputs fig_controllability.pdf, fig_governance.pdf, fig_tradeoff.pdf into this directory.
Numbers match the tables in paper/paper.tex (canonical runs under results/).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).parent
plt.rcParams.update({"font.size": 11})

BLUE, GREY, ORANGE, GREEN, RED = "#3b6fb0", "#9aa0a6", "#e08a3c", "#3c9a5f", "#c0504d"


def fig_controllability():
    """Synthetic: BOOST steering lift (with 95% CI) and EXCLUDE enforcement by condition."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 3.6))

    # Left: steering lift vs rerank-only with 95% CI
    conds = ["augment", "operator"]
    lift = [-0.13, 27.62]
    ci_lo = [-2.50, 21.22]
    ci_hi = [2.15, 34.08]
    err = [[l - lo for l, lo in zip(lift, ci_lo)], [hi - l for hi, l in zip(ci_hi, lift)]]
    colors = [GREY, ORANGE]
    ax1.bar(conds, lift, color=colors, yerr=err, capsize=6, edgecolor="k", linewidth=0.5)
    ax1.axhline(0, color="k", linewidth=0.8)
    ax1.set_ylabel("BOOST steering lift (ranks ↑)")
    ax1.set_title("Controllability: steering lift vs. rerank-only")
    for i, v in enumerate(lift):
        ax1.text(i, v + (1.5 if v >= 0 else -2.5), f"{v:+.1f}", ha="center", fontsize=9)

    # Right: EXCLUDE appearance rate by condition (lower is better)
    ec = ["vanilla", "rerank-only", "augment", "operator"]
    excl = [37.9, 51.7, 51.7, 6.9]
    ax2.bar(ec, excl, color=[BLUE, GREY, GREY, ORANGE], edgecolor="k", linewidth=0.5)
    ax2.set_ylabel("Excluded card in top-n (%)")
    ax2.set_title("Enforcement: EXCLUDE (lower is better)")
    ax2.set_ylim(0, 60)
    for i, v in enumerate(excl):
        ax2.text(i, v + 1, f"{v:.1f}", ha="center", fontsize=8)
    ax2.tick_params(axis="x", labelrotation=20)

    fig.tight_layout()
    fig.savefig(OUT / "fig_controllability.pdf")
    plt.close(fig)


def fig_governance():
    """Non-card governance domain: compliance violation and relevance by condition."""
    conds = ["vanilla", "rerank-only", "operator"]
    compliance = [100.0, 100.0, 0.0]   # must-exclude doc in top-n (lower better)
    relevance = [95.2, 100.0, 100.0]   # sub-topic top-5 (higher better)
    x = np.arange(len(conds))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    ax.bar(x - w / 2, compliance, w, label="Compliance violation (↓)", color=RED, edgecolor="k", linewidth=0.5)
    ax.bar(x + w / 2, relevance, w, label="Sub-topic Top-5 (↑)", color=GREEN, edgecolor="k", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(conds)
    ax.set_ylabel("%")
    ax.set_ylim(0, 110)
    ax.set_title("Document governance: compliance vs. relevance")
    ax.legend(frameon=False, fontsize=9, loc="center right")
    for i, (c, r) in enumerate(zip(compliance, relevance)):
        ax.text(i - w / 2, c + 1.5, f"{c:.0f}", ha="center", fontsize=8)
        ax.text(i + w / 2, r + 1.5, f"{r:.0f}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_governance.pdf")
    plt.close(fig)


def fig_tradeoff():
    """Control–relevance trade-off: stronger enforcement (k_guidance) costs relevance."""
    ks = ["k=3 (default)", "k=8"]
    excl = [6.9, 0.0]      # EXCLUDE appearance (lower better)
    top5 = [68.1, 55.1]    # operator Top-5 (higher better)
    x = np.arange(len(ks))
    w = 0.36
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    ax.bar(x - w / 2, excl, w, label="EXCLUDE in top-n (↓)", color=RED, edgecolor="k", linewidth=0.5)
    ax.bar(x + w / 2, top5, w, label="Operator Top-5 (↑)", color=GREEN, edgecolor="k", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(ks)
    ax.set_ylabel("%")
    ax.set_ylim(0, 80)
    ax.set_title("Control–relevance trade-off (guidance retrieved)")
    ax.legend(frameon=False, fontsize=9)
    for i, (e, t) in enumerate(zip(excl, top5)):
        ax.text(i - w / 2, e + 1, f"{e:.1f}", ha="center", fontsize=8)
        ax.text(i + w / 2, t + 1, f"{t:.1f}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_tradeoff.pdf")
    plt.close(fig)


if __name__ == "__main__":
    fig_controllability()
    fig_governance()
    fig_tradeoff()
    print("Wrote figures to", OUT)
