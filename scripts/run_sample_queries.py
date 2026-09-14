#!/usr/bin/env python3
"""Run CQ1-CQ10 against rdf/sample.ttl.

The sample graph is a curated query fixture. It validates query executability and
expected query shape; it does not reproduce full-corpus counts.
"""
from pathlib import Path
from rdflib import Graph

ROOT = Path(__file__).resolve().parents[1]
GRAPH_FILE = ROOT / "rdf" / "sample.ttl"
QUERY_DIR = ROOT / "sparql"

def main():
    g = Graph()
    g.parse(GRAPH_FILE, format="turtle")
    print(f"Loaded {len(g):,} triples from {GRAPH_FILE.relative_to(ROOT)}")
    failures = []
    for i in range(1, 11):
        qfile = QUERY_DIR / f"CQ{i}.rq"
        try:
            rows = list(g.query(qfile.read_text(encoding="utf-8")))
            print(f"CQ{i}: {len(rows)} row(s)")
            if not rows:
                failures.append(f"CQ{i} returned no rows")
        except Exception as exc:
            failures.append(f"CQ{i} failed: {exc}")
    if failures:
        print("\nFAILED")
        for item in failures:
            print(" -", item)
        raise SystemExit(1)
    print("\nAll CQ1-CQ10 queries executed successfully on the curated sample graph.")

if __name__ == "__main__":
    main()
