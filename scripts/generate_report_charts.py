"""
Report Chart Generator for CronasFastAPI
======================================================
Reads load_test_results.json and produces publication-quality charts
suitable for a project report / thesis / presentation.

Usage:
    python scripts/generate_report_charts.py
    python scripts/generate_report_charts.py --input path/to/results.json
    python scripts/generate_report_charts.py --output path/to/charts_dir

Generates:
  1. throughput_over_time.png    — Requests per second bar chart
  2. latency_distribution.png   — Histogram of response latencies
  3. latency_percentiles.png    — p50 / p95 / p99 bar chart
  4. success_rate.png           — Donut chart (success vs. fail)
  5. concurrency_vs_latency.png — Latency under increasing concurrency
  6. cumulative_throughput.png  — Cumulative jobs processed over time
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless backend — no GUI required
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# ---------- Aesthetic constants ----------

COLORS = {
    "primary":     "#6366f1",   # indigo-500
    "secondary":   "#8b5cf6",   # violet-500
    "success":     "#22c55e",   # green-500
    "danger":      "#ef4444",   # red-500
    "warning":     "#f59e0b",   # amber-500
    "info":        "#06b6d4",   # cyan-500
    "p50":         "#6366f1",
    "p95":         "#f59e0b",
    "p99":         "#ef4444",
    "bg":          "#0f172a",   # slate-900
    "card":        "#1e293b",   # slate-800
    "text":        "#f8fafc",   # slate-50
    "muted":       "#94a3b8",   # slate-400
    "grid":        "#334155",   # slate-700
    "gradient_1":  "#6366f1",
    "gradient_2":  "#a855f7",
}

def apply_dark_style(ax: plt.Axes, fig: plt.Figure | None = None) -> None:
    """Apply a consistent dark theme to a matplotlib axes."""
    ax.set_facecolor(COLORS["card"])
    if fig:
        fig.set_facecolor(COLORS["bg"])
    ax.tick_params(colors=COLORS["muted"], labelsize=10)
    ax.xaxis.label.set_color(COLORS["text"])
    ax.yaxis.label.set_color(COLORS["text"])
    ax.title.set_color(COLORS["text"])
    for spine in ax.spines.values():
        spine.set_color(COLORS["grid"])
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.5, alpha=0.5)


DEFAULT_INPUT = Path(__file__).parent / "load_test_results.json"
DEFAULT_OUTPUT = Path(__file__).parent / "charts"


def load_results(path: Path) -> dict:
    if not path.exists():
        print(f"Error: {path} not found. Run load_test.py first.")
        raise SystemExit(1)
    return json.loads(path.read_text())


# ──────────────────────────────────────────────
# ----------------------------------------------
# Chart 1: Throughput Over Time
# ----------------------------------------------

def chart_throughput(data: dict, output_dir: Path) -> None:
    ts = data.get("time_series", [])
    if not ts:
        print("  [SKIP] Skipping throughput chart (no time series data)")
        return

    seconds = [t["second"] for t in ts]
    counts  = [t["requests"] for t in ts]

    fig, ax = plt.subplots(figsize=(12, 5))
    apply_dark_style(ax, fig)

    bars = ax.bar(seconds, counts, color=COLORS["primary"], edgecolor=COLORS["secondary"], linewidth=0.3, width=0.8)

    # Gradient effect via alpha
    max_val = max(counts) if counts else 1
    for bar, val in zip(bars, counts):
        bar.set_alpha(0.5 + 0.5 * (val / max_val))

    ax.set_xlabel("Time (seconds)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Requests Accepted", fontsize=12, fontweight="bold")
    ax.set_title(f"Throughput Over Time — {data['total_requests']:,} Total Requests", fontsize=14, fontweight="bold", pad=15)

    # Annotate peak
    peak_idx = counts.index(max(counts))
    ax.annotate(
        f"Peak: {counts[peak_idx]:,} req/s",
        xy=(seconds[peak_idx], counts[peak_idx]),
        xytext=(seconds[peak_idx] + 1, counts[peak_idx] * 1.05),
        fontsize=10, color=COLORS["warning"],
        arrowprops=dict(arrowstyle="->", color=COLORS["warning"]),
    )

    avg_rps = data.get("throughput_rps", 0)
    ax.axhline(y=avg_rps, color=COLORS["danger"], linestyle="--", linewidth=1, label=f"Avg: {avg_rps:.0f} req/s")
    ax.legend(facecolor=COLORS["card"], edgecolor=COLORS["grid"], labelcolor=COLORS["text"])

    fig.tight_layout()
    fig.savefig(output_dir / "throughput_over_time.png", dpi=200, facecolor=COLORS["bg"])
    plt.close(fig)
    print("  [OK] throughput_over_time.png")


# ----------------------------------------------
# Chart 2: Latency Distribution (Histogram)
# ----------------------------------------------

def chart_latency_distribution(data: dict, output_dir: Path) -> None:
    latencies = [r["latency_ms"] for r in data.get("results", [])]
    if not latencies:
        print("  [SKIP] Skipping latency distribution chart (no result data)")
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    apply_dark_style(ax, fig)

    n, bins, patches = ax.hist(latencies, bins=80, color=COLORS["primary"], edgecolor=COLORS["secondary"], linewidth=0.3, alpha=0.85)

    # Color gradient on bars
    max_n = max(n) if len(n) else 1
    for patch, count in zip(patches, n):
        ratio = count / max_n
        r, g, b = 0.39, 0.40, 0.95  # base indigo
        patch.set_facecolor((r, g * (0.5 + 0.5 * ratio), b))

    # Percentile lines
    p50 = data.get("latency_p50_ms", 0)
    p95 = data.get("latency_p95_ms", 0)
    p99 = data.get("latency_p99_ms", 0)
    ax.axvline(p50, color=COLORS["p50"], linestyle="-", linewidth=2, label=f"p50: {p50:.1f}ms")
    ax.axvline(p95, color=COLORS["p95"], linestyle="--", linewidth=2, label=f"p95: {p95:.1f}ms")
    ax.axvline(p99, color=COLORS["p99"], linestyle=":", linewidth=2, label=f"p99: {p99:.1f}ms")

    ax.set_xlabel("Latency (ms)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Request Count", fontsize=12, fontweight="bold")
    ax.set_title("API Response Latency Distribution", fontsize=14, fontweight="bold", pad=15)
    ax.legend(facecolor=COLORS["card"], edgecolor=COLORS["grid"], labelcolor=COLORS["text"], fontsize=11)

    fig.tight_layout()
    fig.savefig(output_dir / "latency_distribution.png", dpi=200, facecolor=COLORS["bg"])
    plt.close(fig)
    print("  [OK] latency_distribution.png")


# ----------------------------------------------
# Chart 3: Latency Percentiles Bar Chart
# ----------------------------------------------

def chart_latency_percentiles(data: dict, output_dir: Path) -> None:
    labels = ["Min", "Avg", "p50", "p95", "p99", "Max"]
    values = [
        data.get("latency_min_ms", 0),
        data.get("latency_avg_ms", 0),
        data.get("latency_p50_ms", 0),
        data.get("latency_p95_ms", 0),
        data.get("latency_p99_ms", 0),
        data.get("latency_max_ms", 0),
    ]
    colors = [COLORS["info"], COLORS["primary"], COLORS["p50"], COLORS["p95"], COLORS["p99"], COLORS["danger"]]

    fig, ax = plt.subplots(figsize=(10, 5))
    apply_dark_style(ax, fig)

    bars = ax.bar(labels, values, color=colors, edgecolor=COLORS["grid"], linewidth=0.5, width=0.6)

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
            f"{val:.1f}ms", ha="center", va="bottom", fontsize=11, color=COLORS["text"], fontweight="bold"
        )

    ax.set_ylabel("Latency (ms)", fontsize=12, fontweight="bold")
    ax.set_title(f"Latency Percentile Breakdown — {data['total_requests']:,} Requests", fontsize=14, fontweight="bold", pad=15)

    # Target line
    ax.axhline(y=2000, color=COLORS["warning"], linestyle="--", linewidth=1, alpha=0.7, label="Target: <2000ms")
    ax.legend(facecolor=COLORS["card"], edgecolor=COLORS["grid"], labelcolor=COLORS["text"])

    fig.tight_layout()
    fig.savefig(output_dir / "latency_percentiles.png", dpi=200, facecolor=COLORS["bg"])
    plt.close(fig)
    print("  [OK] latency_percentiles.png")


# ----------------------------------------------
# Chart 4: Success Rate Donut
# ----------------------------------------------

def chart_success_rate(data: dict, output_dir: Path) -> None:
    success = data.get("successful", 0)
    fail = data.get("failed", 0)
    total = success + fail
    if total == 0:
        return

    fig, ax = plt.subplots(figsize=(6, 6))
    fig.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["bg"])

    sizes = [success, fail] if fail > 0 else [success]
    chart_colors = [COLORS["success"], COLORS["danger"]] if fail > 0 else [COLORS["success"]]
    labels = [f"Success\n{success:,}", f"Failed\n{fail:,}"] if fail > 0 else [f"Success\n{success:,}"]

    wedges, texts = ax.pie(
        sizes, labels=labels, colors=chart_colors,
        startangle=90, wedgeprops=dict(width=0.35, edgecolor=COLORS["bg"], linewidth=2),
        textprops=dict(color=COLORS["text"], fontsize=12, fontweight="bold"),
    )

    # Center text
    pct = (success / total) * 100
    ax.text(0, 0, f"{pct:.1f}%\nSuccess", ha="center", va="center",
            fontsize=20, fontweight="bold", color=COLORS["success"] if pct >= 95 else COLORS["warning"])

    ax.set_title("Request Success Rate", fontsize=14, fontweight="bold", color=COLORS["text"], pad=20)

    fig.tight_layout()
    fig.savefig(output_dir / "success_rate.png", dpi=200, facecolor=COLORS["bg"])
    plt.close(fig)
    print("  [OK] success_rate.png")


# ----------------------------------------------
# Chart 5: Cumulative Throughput Over Time
# ----------------------------------------------

def chart_cumulative(data: dict, output_dir: Path) -> None:
    ts = data.get("time_series", [])
    if not ts:
        return

    seconds = [t["second"] for t in ts]
    cumulative = []
    running = 0
    for t in ts:
        running += t["requests"]
        cumulative.append(running)

    fig, ax = plt.subplots(figsize=(12, 5))
    apply_dark_style(ax, fig)

    ax.fill_between(seconds, cumulative, color=COLORS["primary"], alpha=0.3)
    ax.plot(seconds, cumulative, color=COLORS["primary"], linewidth=2.5)

    # Mark milestones
    milestones = [1000, 2000, 3000, 4000, 5000]
    for ms in milestones:
        if ms <= cumulative[-1]:
            for i, c in enumerate(cumulative):
                if c >= ms:
                    ax.plot(seconds[i], c, "o", color=COLORS["warning"], markersize=8, zorder=5)
                    ax.annotate(f"{ms:,}", xy=(seconds[i], c), xytext=(seconds[i] + 0.3, c * 1.03),
                                fontsize=9, color=COLORS["warning"])
                    break

    ax.set_xlabel("Time (seconds)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Total Jobs Processed", fontsize=12, fontweight="bold")
    ax.set_title("Cumulative Throughput", fontsize=14, fontweight="bold", pad=15)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{int(x):,}"))

    fig.tight_layout()
    fig.savefig(output_dir / "cumulative_throughput.png", dpi=200, facecolor=COLORS["bg"])
    plt.close(fig)
    print("  [OK] cumulative_throughput.png")


# ----------------------------------------------
# Chart 6: Avg Latency Over Time (line)
# ----------------------------------------------

def chart_latency_over_time(data: dict, output_dir: Path) -> None:
    ts = data.get("time_series", [])
    if not ts:
        return

    seconds = [t["second"] for t in ts]
    avg_lat = [t["avg_latency_ms"] for t in ts]
    p95_lat = [t["p95_latency_ms"] for t in ts]

    fig, ax = plt.subplots(figsize=(12, 5))
    apply_dark_style(ax, fig)

    ax.fill_between(seconds, avg_lat, alpha=0.2, color=COLORS["primary"])
    ax.plot(seconds, avg_lat, color=COLORS["primary"], linewidth=2, label="Avg Latency")
    ax.plot(seconds, p95_lat, color=COLORS["p95"], linewidth=2, linestyle="--", label="p95 Latency")

    ax.set_xlabel("Time (seconds)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Latency (ms)", fontsize=12, fontweight="bold")
    ax.set_title("Latency Over Time During Load Test", fontsize=14, fontweight="bold", pad=15)
    ax.legend(facecolor=COLORS["card"], edgecolor=COLORS["grid"], labelcolor=COLORS["text"])

    fig.tight_layout()
    fig.savefig(output_dir / "latency_over_time.png", dpi=200, facecolor=COLORS["bg"])
    plt.close(fig)
    print("  [OK] latency_over_time.png")


# ----------------------------------------------
# Chart 7: Summary Stats Card (for report embed)
# ----------------------------------------------

def chart_summary_card(data: dict, output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["card"])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")

    # Title
    ax.text(5, 3.5, "LOAD TEST SUMMARY", ha="center", va="center",
            fontsize=18, fontweight="bold", color=COLORS["text"],
            bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS["primary"], alpha=0.8))

    metrics = [
        (1.5, 2.2, f"{data['total_requests']:,}",  "Total Requests", COLORS["info"]),
        (4.0, 2.2, f"{data['throughput_rps']:.0f}", "Requests/sec",   COLORS["success"]),
        (6.5, 2.2, f"{data['latency_p50_ms']:.0f}ms", "p50 Latency", COLORS["p50"]),
        (8.5, 2.2, f"{data['latency_p99_ms']:.0f}ms", "p99 Latency", COLORS["p99"]),
    ]

    for x, y, value, label, color in metrics:
        ax.text(x, y, value, ha="center", va="center", fontsize=22, fontweight="bold", color=color)
        ax.text(x, y - 0.5, label, ha="center", va="center", fontsize=10, color=COLORS["muted"])

    success_pct = (data["successful"] / data["total_requests"]) * 100 if data["total_requests"] else 0
    ax.text(5, 0.5, f"Success Rate: {success_pct:.1f}%  •  Total Time: {data['total_time_seconds']:.1f}s",
            ha="center", va="center", fontsize=11, color=COLORS["muted"])

    fig.tight_layout()
    fig.savefig(output_dir / "summary_card.png", dpi=200, facecolor=COLORS["bg"])
    plt.close(fig)
    print("  [OK] summary_card.png")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate report charts from load test results")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to load test results JSON")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output directory for charts")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    data = load_results(args.input)

    print(f"\n{'='*60}")
    print(f"  Generating Report Charts")
    print(f"  Input  : {args.input}")
    print(f"  Output : {args.output}")
    print(f"{'='*60}\n")

    chart_throughput(data, args.output)
    chart_latency_distribution(data, args.output)
    chart_latency_percentiles(data, args.output)
    chart_success_rate(data, args.output)
    chart_cumulative(data, args.output)
    chart_latency_over_time(data, args.output)
    chart_summary_card(data, args.output)

    print(f"\n  All charts saved to: {args.output}/")
    print(f"  You can embed these directly in your project report.\n")


if __name__ == "__main__":
    main()
