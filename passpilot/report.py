"""Charts and a results table from data/: python -m passpilot report"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import DATA_DIR, ROOT

IMG = ROOT / "docs" / "img"
METHODS = ["random", "ga", "agent", "model"]
LABELS = {"random": "Random search", "ga": "Genetic algorithm", "agent": "LLM agent", "model": "Cost-model guided"}
COLORS = {"random": "#9aa5b1", "ga": "#2f80ed", "agent": "#76b900", "model": "#f2994a"}


def _speedup_chart(res):
    benches = sorted(res.bench.unique())
    methods = [m for m in METHODS if m in set(res.method)]
    x, w = np.arange(len(benches)), 0.8 / len(methods)
    fig, ax = plt.subplots(figsize=(11, 4.2))
    for i, m in enumerate(methods):
        g = res[res.method == m].set_index("bench").reindex(benches)
        ax.bar(x + (i - (len(methods) - 1) / 2) * w, g.speedup_vs_o3, w, label=LABELS[m], color=COLORS[m])
    ax.axhline(1.0, color="#333", lw=1, ls="--")
    ax.text(len(benches) - 0.5, 1.005, "-O3", ha="right", va="bottom", fontsize=9)
    ax.set_xticks(x, benches, rotation=30, ha="right")
    ax.set_ylabel("speedup vs clang -O3 (higher is better)")
    ax.set_title("Best pipeline found per benchmark, re-measured (10 runs)")
    lo = max(0.0, min(0.8, res.speedup_vs_o3.min() - 0.05))
    ax.set_ylim(lo, res.speedup_vs_o3.max() + 0.08)
    ax.legend(ncol=len(methods), fontsize=9, frameon=False, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(IMG / "speedup_vs_o3.png", dpi=160)
    plt.close(fig)


def _convergence_chart(ev, bases):
    o3 = bases[bases.baseline == "O3"].set_index("bench").runtime_s
    fig, ax = plt.subplots(figsize=(6.5, 4))
    methods = [m for m in METHODS if m in set(ev.method)]
    # Only benchmarks every method finished, so the curves average over the same programs.
    common = set.intersection(*(set(ev[ev.method == m].bench) for m in methods))
    for m in methods:
        curves = []
        for b, g in ev[(ev.method == m) & ev.bench.isin(common)].groupby("bench"):
            rt = g.sort_values("step").runtime_s.where(g.correct.astype(bool), np.inf).to_numpy()
            best = np.minimum.accumulate(rt)
            curves.append(np.log(o3[b] / best))
        n = min(len(c) for c in curves)
        geo = np.exp(np.mean([c[:n] for c in curves], axis=0))
        ax.plot(np.arange(1, n + 1), geo, label=LABELS[m], color=COLORS[m], lw=2)
    ax.axhline(1.0, color="#333", lw=1, ls="--")
    ax.set_xlabel("pipelines evaluated")
    ax.set_ylabel("best so far, geomean speedup vs -O3")
    ax.set_title("How fast each method finds a good pipeline")
    ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(IMG / "convergence.png", dpi=160)
    plt.close(fig)


def _tradeoff_chart(res):
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for m in [m for m in METHODS if m in set(res.method)]:
        g = res[res.method == m]
        ax.scatter(g.compile_s / g.o3_compile_s, g.speedup_vs_o3, label=LABELS[m], color=COLORS[m], s=36)
    ax.axhline(1.0, color="#333", lw=1, ls="--")
    ax.axvline(1.0, color="#333", lw=1, ls=":")
    ax.set_xlabel("compile time vs -O3 (left is faster)")
    ax.set_ylabel("runtime speedup vs -O3")
    ax.set_title("Runtime vs compile time, every benchmark")
    ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(IMG / "compile_tradeoff.png", dpi=160)
    plt.close(fig)


def report():
    IMG.mkdir(parents=True, exist_ok=True)
    res = pd.read_csv(DATA_DIR / "results.csv")
    ev = pd.read_csv(DATA_DIR / "evaluations.csv")
    bases = pd.read_csv(DATA_DIR / "baselines.csv")
    _speedup_chart(res)
    _convergence_chart(ev, bases)
    _tradeoff_chart(res)
    table = res.pivot(index="bench", columns="method", values="speedup_vs_o3")
    table = table[[m for m in METHODS if m in table.columns]].round(3)
    (DATA_DIR / "speedup_table.md").write_text(table.to_markdown())
    print(table.to_string())
    print(json.dumps(json.loads((DATA_DIR / "summary.json").read_text()), indent=2))
