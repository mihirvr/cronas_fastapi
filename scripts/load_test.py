"""
Load Test Script for CronasFastAPI
================================================
Fires N concurrent POST /jobs requests against the FastAPI API and
records per-request latency, status codes, and timestamps.

Usage:
    python scripts/load_test.py                       # default 5000 requests
    python scripts/load_test.py --total 1000          # custom total
    python scripts/load_test.py --total 5000 --batch 500  # custom batch size
    python scripts/load_test.py --url http://host:port    # custom API URL

Results are saved to scripts/load_test_results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx


API_BASE = "http://127.0.0.1:8000"
RESULTS_PATH = Path(__file__).parent / "load_test_results.json"


@dataclass
class RequestResult:
    request_index: int
    status_code: int
    latency_ms: float
    sent_at: float        # epoch seconds
    received_at: float    # epoch seconds
    success: bool
    error: str | None = None


@dataclass
class LoadTestSummary:
    total_requests: int
    concurrency_batch: int
    total_time_seconds: float
    successful: int
    failed: int
    throughput_rps: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_min_ms: float
    latency_max_ms: float
    latency_avg_ms: float
    results: list[dict] = field(default_factory=list)
    time_series: list[dict] = field(default_factory=list)


JOB_TEMPLATES = [
    {"name": "email-job",       "schedule_type": "immediate", "payload": {"template": "welcome", "user_id": "bench"}},
    {"name": "report-gen",      "schedule_type": "immediate", "payload": {"report": "daily_metrics"}},
    {"name": "cleanup-task",    "schedule_type": "immediate", "payload": {"action": "purge_old_logs"}},
    {"name": "notification",    "schedule_type": "immediate", "payload": {"channel": "push", "message": "hello"}},
    {"name": "sync-inventory",  "schedule_type": "immediate", "payload": {"warehouse": "main"}},
]


async def send_request(
    client: httpx.AsyncClient,
    index: int,
    semaphore: asyncio.Semaphore,
) -> RequestResult:
    template = JOB_TEMPLATES[index % len(JOB_TEMPLATES)]
    body = {**template, "name": f"{template['name']}-{index}"}

    async with semaphore:
        sent_at = time.time()
        try:
            resp = await client.post(f"/jobs", json=body)
            received_at = time.time()
            return RequestResult(
                request_index=index,
                status_code=resp.status_code,
                latency_ms=round((received_at - sent_at) * 1000, 2),
                sent_at=sent_at,
                received_at=received_at,
                success=resp.status_code == 201,
            )
        except Exception as exc:
            received_at = time.time()
            return RequestResult(
                request_index=index,
                status_code=0,
                latency_ms=round((received_at - sent_at) * 1000, 2),
                sent_at=sent_at,
                received_at=received_at,
                success=False,
                error=str(exc),
            )


def compute_percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_values):
        return sorted_values[f]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


def build_time_series(results: list[RequestResult], bucket_ms: int = 1000) -> list[dict]:
    """Group requests into time buckets to produce throughput-over-time data."""
    if not results:
        return []
    start = min(r.sent_at for r in results)
    buckets: dict[int, dict] = {}
    for r in results:
        bucket_idx = int((r.sent_at - start) * 1000 / bucket_ms)
        if bucket_idx not in buckets:
            buckets[bucket_idx] = {"second": bucket_idx, "count": 0, "success": 0, "fail": 0, "latencies": []}
        buckets[bucket_idx]["count"] += 1
        if r.success:
            buckets[bucket_idx]["success"] += 1
        else:
            buckets[bucket_idx]["fail"] += 1
        buckets[bucket_idx]["latencies"].append(r.latency_ms)

    series = []
    for idx in sorted(buckets.keys()):
        b = buckets[idx]
        lats = sorted(b["latencies"])
        series.append({
            "second": idx,
            "requests": b["count"],
            "success": b["success"],
            "fail": b["fail"],
            "avg_latency_ms": round(sum(lats) / len(lats), 2),
            "p95_latency_ms": round(compute_percentile(lats, 95), 2),
        })
    return series


async def run_load_test(total: int, batch_size: int, base_url: str) -> LoadTestSummary:
    semaphore = asyncio.Semaphore(batch_size)
    print(f"\n{'='*60}")
    print(f"  CronasFastAPI — Load Test")
    print(f"  Total requests : {total}")
    print(f"  Concurrency    : {batch_size}")
    print(f"  Target         : {base_url}")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(60.0),
        limits=httpx.Limits(max_connections=batch_size, max_keepalive_connections=batch_size),
    ) as client:
        # Warm-up request
        print("  Sending warm-up request...")
        try:
            await client.get("/health")
            print("  [OK] API is reachable\n")
        except Exception as exc:
            print(f"  [FAIL] API not reachable: {exc}")
            print("  Make sure the API is running: uvicorn services.job_api.app.main:app --reload\n")
            raise SystemExit(1)

        print(f"  Firing {total} requests...")
        wall_start = time.time()

        tasks = [send_request(client, i, semaphore) for i in range(total)]
        results: list[RequestResult] = await asyncio.gather(*tasks)

        wall_end = time.time()

    total_time = wall_end - wall_start
    latencies = sorted([r.latency_ms for r in results])
    successful = sum(1 for r in results if r.success)
    failed = total - successful

    summary = LoadTestSummary(
        total_requests=total,
        concurrency_batch=batch_size,
        total_time_seconds=round(total_time, 3),
        successful=successful,
        failed=failed,
        throughput_rps=round(total / total_time, 1),
        latency_p50_ms=round(compute_percentile(latencies, 50), 2),
        latency_p95_ms=round(compute_percentile(latencies, 95), 2),
        latency_p99_ms=round(compute_percentile(latencies, 99), 2),
        latency_min_ms=round(latencies[0], 2) if latencies else 0,
        latency_max_ms=round(latencies[-1], 2) if latencies else 0,
        latency_avg_ms=round(sum(latencies) / len(latencies), 2) if latencies else 0,
        results=[asdict(r) for r in results],
        time_series=build_time_series(results),
    )

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Total Requests  : {summary.total_requests}")
    print(f"  Successful      : {summary.successful}")
    print(f"  Failed          : {summary.failed}")
    print(f"  Total Time      : {summary.total_time_seconds}s")
    print(f"  Throughput      : {summary.throughput_rps} req/s")
    print(f"  Latency p50     : {summary.latency_p50_ms}ms")
    print(f"  Latency p95     : {summary.latency_p95_ms}ms")
    print(f"  Latency p99     : {summary.latency_p99_ms}ms")
    print(f"  Latency min     : {summary.latency_min_ms}ms")
    print(f"  Latency max     : {summary.latency_max_ms}ms")
    print(f"{'='*60}\n")

    # Save results
    output = asdict(summary)
    RESULTS_PATH.write_text(json.dumps(output, indent=2))
    print(f"  Results saved to: {RESULTS_PATH}")
    print(f"  Run 'python scripts/generate_report_charts.py' to generate charts.\n")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Load test the CronasFastAPI API")
    parser.add_argument("--total", type=int, default=5000, help="Total number of requests (default: 5000)")
    parser.add_argument("--batch", type=int, default=500, help="Max concurrent requests (default: 500)")
    parser.add_argument("--url", type=str, default=API_BASE, help=f"API base URL (default: {API_BASE})")
    args = parser.parse_args()

    asyncio.run(run_load_test(args.total, args.batch, args.url))


if __name__ == "__main__":
    main()
