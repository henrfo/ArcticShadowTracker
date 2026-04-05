#!/usr/bin/env python3
"""
analyze_coverage_boundary.py — empirical BarentsWatch coverage edge map.

Most "AIS gap" anomalies are not suspicious. They're vessels crossing the edge
of BarentsWatch's geographic coverage — a predictable, geographic event that
looks identical to a real signal loss on the wire. This script learns where
those edges actually are from historical anomaly data, so the runtime detector
can distinguish "left coverage area" from "genuine signal loss".

How it works:
    1. Fetch the published anomalies.json (from gh-pages) OR read a local file.
    2. Extract every transmission_gap anomaly's last_position.
    3. Bucket the positions into 0.1° x 0.1° cells (~11 x 5.5 km at 60°N).
    4. Any cell with >= THRESHOLD_GAPS hits is a "coverage edge cell".
    5. Write the set of edge cells to data/coverage_edge_cells.json.

Runtime usage:
    detect_anomalies.py loads this JSON once at startup. For each new gap,
    if the last_position falls inside a coverage edge cell, the anomaly is
    reclassified as `left_coverage` (low severity, hidden from default feed).

This script is safe to re-run any time. It's also cheap — 1.5k anomalies takes
well under a second. Commit the generated JSON so deployed runtime reads it.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None  # we can still read local files without requests


# --- Tunable constants ------------------------------------------------------
# 0.1° is ~11 km lat × ~5.5 km lon at 60°N. Fine enough to distinguish coastal
# cells from deep-sea, coarse enough that sparse noise doesn't create phantom edges.
CELL_SIZE_DEG = 0.1

# A cell must have at least this many gaps to count as a coverage edge.
# Tune down (e.g. 5) if the initial edge map is too sparse to catch real edges.
THRESHOLD_GAPS = 10

DEFAULT_SOURCE_URL = "https://henrfo.github.io/ArcticShadowTracker/data/anomalies/anomalies.json"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "data" / "coverage_edge_cells.json"


def cell_key(lat: float, lon: float, size: float) -> tuple[float, float]:
    """Snap a (lat, lon) to the bottom-left corner of its cell, rounded to
    avoid floating-point surprises (e.g. 59.300000000001)."""
    return (
        round((lat // size) * size, 4),
        round((lon // size) * size, 4),
    )


def load_anomalies(source: str) -> list[dict]:
    """Load anomalies from a URL or a local file path."""
    if source.startswith(("http://", "https://")):
        if requests is None:
            raise RuntimeError(
                "Cannot fetch URL: requests not installed. Pass a local path instead."
            )
        print(f"Fetching {source}")
        r = requests.get(source, timeout=30)
        r.raise_for_status()
        data = r.json()
    else:
        path = Path(source)
        print(f"Reading {path}")
        data = json.loads(path.read_text())
    return data.get("anomalies", []) or []


def compute_edge_cells(
    anomalies: list[dict], threshold: int, cell_size: float
) -> tuple[Counter, list, int]:
    """Count gaps per cell and return (full_counter, edge_cells_above_threshold, skipped)."""
    counter: Counter = Counter()
    skipped = 0
    for a in anomalies:
        if a.get("anomaly_type") != "transmission_gap":
            continue
        details = a.get("details") or {}
        pos = details.get("last_position") or {}
        lat, lon = pos.get("lat"), pos.get("lon")
        if lat is None or lon is None:
            skipped += 1
            continue
        counter[cell_key(lat, lon, cell_size)] += 1

    edge_cells = [list(k) for k, v in counter.items() if v >= threshold]
    edge_cells.sort()
    return counter, edge_cells, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--source",
        default=DEFAULT_SOURCE_URL,
        help="URL or local path to anomalies.json (default: gh-pages)",
    )
    ap.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Where to write the edge cells JSON (default: {DEFAULT_OUTPUT})",
    )
    ap.add_argument(
        "--threshold",
        type=int,
        default=THRESHOLD_GAPS,
        help=f"Minimum gaps per cell to qualify as coverage edge (default: {THRESHOLD_GAPS})",
    )
    ap.add_argument(
        "--cell-size",
        type=float,
        default=CELL_SIZE_DEG,
        help=f"Cell size in degrees (default: {CELL_SIZE_DEG})",
    )
    args = ap.parse_args()

    anomalies = load_anomalies(args.source)
    total_gaps = sum(
        1 for a in anomalies if a.get("anomaly_type") == "transmission_gap"
    )
    print(f"Loaded {len(anomalies):,} anomalies ({total_gaps:,} transmission_gap)")

    counter, edge_cells, skipped = compute_edge_cells(
        anomalies, args.threshold, args.cell_size
    )
    cells_covered = sum(v for k, v in counter.items() if v >= args.threshold)
    coverage_pct = (cells_covered / total_gaps * 100) if total_gaps else 0

    print(
        f"Grid resolution: {args.cell_size}° cells, threshold {args.threshold} gaps"
    )
    print(f"Non-empty cells: {len(counter):,}")
    print(f"Edge cells:      {len(edge_cells):,}")
    print(
        f"Gaps in edge cells: {cells_covered:,} of {total_gaps:,} "
        f"({coverage_pct:.1f}% reclassification rate)"
    )
    if skipped:
        print(f"Skipped {skipped} anomalies with missing last_position")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": args.source,
        "cell_size_deg": args.cell_size,
        "threshold_gaps": args.threshold,
        "analyzed_anomalies": len(anomalies),
        "analyzed_transmission_gaps": total_gaps,
        "gaps_in_edge_cells": cells_covered,
        "reclassification_rate": round(coverage_pct, 1),
        "edge_cells": edge_cells,  # list of [lat, lon] pairs
    }
    output_path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {output_path}")

    # Show the top 10 hottest cells for sanity-check
    print("\nTop 10 hottest cells:")
    for (lat, lon), count in counter.most_common(10):
        print(f"  ({lat:+6.2f}, {lon:+6.2f}): {count} gaps")

    return 0


if __name__ == "__main__":
    sys.exit(main())
