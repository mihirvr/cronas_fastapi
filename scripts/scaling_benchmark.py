"""
Scaling Benchmark for CronasFastAPI
=================================================
Runs the load test at multiple concurrency levels (100, 500, 1000, 2000, 5000)
and produces a single chart showing how latency and throughput scale.

Usage:
    python scripts/scaling_benchmark.py
    python scripts/scaling_benchmark.py --levels 100 500 1000 2000 5000
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from load_test import run_load_test

COLORS = {
    "primary":  "#6366f1",
    "success":  "#22c55e",
    "warning":  "#f59e0b",
    "danger":   "#ef4444",
    "bg":       "#0f172a",
    "card":     "#1e293b",
    "text":     "#f8fafc",
    "muted":    "#94a3b8",
    "grid":     "#334155",
}

OUTPUT_DIR = Path(__file__).parent / "charts"


def apply_dark_style(ax: plt.Axes, fig: plt.Figure) -> None:
    ax.set_facecolor(COLORS["card"])
    fig.set_facecolor(COLORS["bg"])
    ax.tick_params(colors=COLORS["muted"], labelsize=10)
    ax.xaxis.label.set_color(COLORS["text"])
    ax.yaxis.label.set_color(COLORS["text"])
    ax.title.set_color(COLORS["text"])
    for spine in ax.spines.values():
        spine.set_color(COLORS["grid"])
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.5, alpha=0.5)


async def run_scaling_test(levels: list[int], requests_per_level: int, base_url: str) -> list[dict]:
    results = []
    for level in levels:
        print(f"\n{'='*60}")
        print(f"  Running at concurrency level: {level}")
        print(f"{'='*60}")

        summary = await run_load_test(total=requests_per_level, batch_size=level, base_url=base_url)
        results.append({
            "concurrency": level,
            "throughput_rps": summary.throughput_rps,
            "latency_p50_ms": summary.latency_p50_ms,
            "latency_p95_ms": summary.latency_p95_ms,
            "latency_p99_ms": summary.latency_p99_ms,
            "latency_avg_ms": summary.latency_avg_ms,
            "success_rate": round((summary.successful / summary.total_requests) * 100, 2),
        })

    return results


def generate_scaling_chart(results: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    concurrency = [r["concurrency"] for r in results]
    throughput   = [r["throughput_rps"] for r in results]
    p50          = [r["latency_p50_ms"] for r in results]
    p95          = [r["latency_p95_ms"] for r in results]
    p99          = [r["latency_p99_ms"] for r in results]

    # Chart: Throughput vs Concurrency
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.set_facecolor(COLORS["bg"])

    # Left: Throughput
    apply_dark_style(ax1, fig)
    ax1.bar(range(len(concurrency)), throughput, color=COLORS["success"], width=0.6, edgecolor=COLORS["grid"])
    ax1.set_xticks(range(len(concurrency)))
    ax1.set_xticklabels([str(c) for c in concurrency])
    ax1.set_xlabel("Concurrency Level", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Throughput (req/s)", fontsize=12, fontweight="bold")
    ax1.set_title("Throughput vs. Concurrency", fontsize=14, fontweight="bold", pad=15)

    for i, val in enumerate(throughput):
        ax1.text(i, val + max(throughput) * 0.02, f"{val:.0f}", ha="center",
                 fontsize=11, color=COLORS["text"], fontweight="bold")

    # Right: Latency
    apply_dark_style(ax2, fig)
    x = range(len(concurrency))
    ax2.plot(x, p50, "-o", color=COLORS["primary"], linewidth=2.5, markersize=8, label="p50")
    ax2.plot(x, p95, "-s", color=COLORS["warning"], linewidth=2.5, markersize=8, label="p95")
    ax2.plot(x, p99, "-^", color=COLORS["danger"], linewidth=2.5, markersize=8, label="p99")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels([str(c) for c in concurrency])
    ax2.set_xlabel("Concurrency Level", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Latency (ms)", fontsize=12, fontweight="bold")
    ax2.set_title("Latency vs. Concurrency", fontsize=14, fontweight="bold", pad=15)
    ax2.legend(facecolor=COLORS["card"], edgecolor=COLORS["grid"], labelcolor=COLORS["text"], fontsize=11)

    fig.suptitle("CronasFastAPI — Scaling Benchmark", fontsize=16,
                 fontweight="bold", color=COLORS["text"], y=1.02)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "scaling_benchmark.png", dpi=200, facecolor=COLORS["bg"], bbox_inches="tight")
    plt.close(fig)
    print(f"\n  ✓ Scaling chart saved to: {OUTPUT_DIR / 'scaling_benchmark.png'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run scaling benchmark at multiple concurrency levels")
    parser.add_argument("--levels", type=int, nargs="+", default=[100, 500, 1000, 2000, 5000],
                        help="Concurrency levels to test (default: 100 500 1000 2000 5000)")
    parser.add_argument("--requests", type=int, default=2000,
                        help="Requests per level (default: 2000)")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8000",
                        help="API base URL")
    args = parser.parse_args()

    results = asyncio.run(run_scaling_test(args.levels, args.requests, args.url))

    # Save raw data
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "scaling_results.json").write_text(json.dumps(results, indent=2))

    generate_scaling_chart(results)

    print(f"\n{'='*60}")
    print("  SCALING BENCHMARK COMPLETE")
    print(f"{'='*60}")
    for r in results:
        print(f"  Concurrency {r['concurrency']:>5} → {r['throughput_rps']:>7.0f} req/s | "
              f"p50={r['latency_p50_ms']:.0f}ms p95={r['latency_p95_ms']:.0f}ms p99={r['latency_p99_ms']:.0f}ms | "
              f"Success: {r['success_rate']:.1f}%")
    print()


if __name__ == "__main__":
    main()
