"""Small load test: N simulated visitors hitting a few pages for a while.

Standard library only, so it runs on the server or a laptop as is:

    python scripts/loadtest.py https://modaresyar-org.site --users 50 --seconds 60
    python scripts/loadtest.py http://127.0.0.1:8100 --users 200 --spoof-ips   # on the server, straight at gunicorn

Throttling: the API allows 100 anonymous requests per hour per IP, so a
test from one machine through nginx turns into 429s within seconds. Those
are reported separately; they mean the limit works, not that the server is
slow. To measure capacity, run on the server against gunicorn directly
(port 8100) with --spoof-ips: there the X-Forwarded-For header is trusted
(NUM_PROXIES = 1), so each simulated visitor counts as its own IP.
"""
import argparse
import random
import statistics
import threading
import time
import urllib.error
import urllib.request
from collections import Counter

DEFAULT_PATHS = ("/api/v1/site/", "/api/v1/courses/", "/api/v1/categories/")


def visitor(base, paths, deadline, spoof_ips, results, lock):
    ip = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    while time.monotonic() < deadline:
        path = random.choice(paths)
        request = urllib.request.Request(base + path, headers={"User-Agent": "amozeshyar-loadtest"})
        if spoof_ips:
            request.add_header("X-Forwarded-For", ip)
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read()
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        except Exception as exc:  # timeouts, refused connections, resets
            status = type(exc).__name__
        elapsed = time.monotonic() - started
        with lock:
            results.append((path, status, elapsed))


def percentile(values, fraction):
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * fraction))] if values else 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base", help="site or backend address, e.g. https://example.com")
    parser.add_argument("--users", type=int, default=20, help="simultaneous visitors (default 20)")
    parser.add_argument("--seconds", type=int, default=30, help="test length (default 30)")
    parser.add_argument("--path", action="append", dest="paths", help=f"path to request; repeatable (default {', '.join(DEFAULT_PATHS)})")
    parser.add_argument("--spoof-ips", action="store_true", help="give each visitor its own X-Forwarded-For (only when hitting gunicorn directly)")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    paths = args.paths or list(DEFAULT_PATHS)
    results, lock = [], threading.Lock()
    deadline = time.monotonic() + args.seconds
    threads = [
        threading.Thread(target=visitor, args=(base, paths, deadline, args.spoof_ips, results, lock), daemon=True)
        for _ in range(args.users)
    ]
    print(f"{args.users} visitors, {args.seconds}s, {base} {paths}")
    started = time.monotonic()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    wall = time.monotonic() - started

    statuses = Counter(status for _, status, _ in results)
    ok = [elapsed for _, status, elapsed in results if status == 200]
    print(f"\nrequests: {len(results)}  ({len(results) / wall:.1f}/s)")
    print("status:  ", ", ".join(f"{status}: {count}" for status, count in statuses.most_common()))
    if ok:
        print(
            f"200 time:  p50 {percentile(ok, 0.50) * 1000:.0f} ms   p95 {percentile(ok, 0.95) * 1000:.0f} ms"
            f"   p99 {percentile(ok, 0.99) * 1000:.0f} ms   max {max(ok) * 1000:.0f} ms"
        )
    print("\nper path (200s only):")
    for path in paths:
        times = [elapsed for p, status, elapsed in results if p == path and status == 200]
        if times:
            print(f"  {path:<28} n={len(times):<6} p50 {statistics.median(times) * 1000:.0f} ms   p95 {percentile(times, 0.95) * 1000:.0f} ms")
    if statuses.get(429):
        print("\n429s are the rate limit doing its job; see the note at the top of this file to measure past it.")


if __name__ == "__main__":
    main()
