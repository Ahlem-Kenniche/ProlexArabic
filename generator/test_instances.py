from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from regles import appliquer_regles, appliquer_instances

print("=== REGION DERIVATION ===")
for m in ["الأندلس", "الصحراء", "الحجاز", "نجد", "تهامة", "كردستان", "سيناء", "الجليل", "البقاع"]:
    r, e = appliquer_regles(m, "region")
    if r:
        print(f"{m} -> {r['singulier_masculin']} / {r['singulier_feminin']} | {e[:55]}")
    else:
        print(f"{m} -> PAS DE DERIVATION | {e[:60]}")

print()
print("=== VILLE DERIVATION ===")
for m in ["واشنطن", "باريس", "لندن", "برلين", "دمشق", "تونس", "بيروت", "حلب", "مراكش"]:
    r, e = appliquer_regles(m, "ville")
    if r:
        print(f"{m} -> {r['singulier_masculin']} (DERIVE)")
    else:
        print(f"{m} -> PAS DE DERIVATION")

print()
print("=== INSTANCES REGION ===")
for m in ["الأندلس", "الصحراء", "آبلدورن"]:
    r = appliquer_instances(m, "region")
    vals = list(r["formes"].values())
    print(f"{m} -> {vals[0]} / {vals[1]} / {vals[2]}")
