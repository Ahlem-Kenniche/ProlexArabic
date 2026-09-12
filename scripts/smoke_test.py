#!/usr/bin/env python3
"""Fast, network-free smoke test for the EACL demonstration package."""
from pathlib import Path
import sqlite3, subprocess, sys
from rdflib import Graph

# Import the same rule module used by the Streamlit application.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from regles import appliquer_regles

ROOT = Path(__file__).resolve().parents[1]

def ok(msg): print(f"[OK] {msg}")
def main():
    # 1. SQLite demo data
    db = ROOT / "data_sample" / "prolexbase_sample.db"
    con = sqlite3.connect(db)
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ["prolexeme_arb", "instance_arb", "derivative_arb", "pivot", "type"]}
    con.close()
    assert counts["prolexeme_arb"] > 0 and counts["instance_arb"] > 0
    ok("SQLite demo database is readable: " + ", ".join(f"{k}={v:,}" for k,v in counts.items()))

    # 2. Core Arabic rule system
    forms, message = appliquer_regles("مصر", "pays")
    assert forms and forms.get("singulier_masculin") == "مصري", (forms, message)
    ok("Arabic morphology rule check: مصر → مصري")

    # 3. Turtle files
    for rel in ["ontology/prolexbase-ontolex.ttl", "rdf/sample.ttl"]:
        g = Graph(); g.parse(ROOT/rel, format="turtle")
        assert len(g) > 0
        ok(f"{rel} parses as Turtle ({len(g):,} triples)")

    # 4. SPARQL sample queries
    r = subprocess.run([sys.executable, str(ROOT/"scripts"/"run_sample_queries.py")], cwd=ROOT)
    if r.returncode != 0: raise SystemExit(r.returncode)
    ok("CQ1-CQ10 run on the curated RDF fixture")

    # 5. XML/XSD validation
    r = subprocess.run([sys.executable, str(ROOT/"prolmf"/"validate_xml.py")], cwd=ROOT)
    if r.returncode != 0: raise SystemExit(r.returncode)
    ok("ProLMF XML validates against bundled XSD")

    print("\nSmoke test completed successfully.")
if __name__ == "__main__": main()
