# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from regles import appliquer_regles, appliquer_instances

tests = [
    ("باريس",    "ville"),
    ("القاهرة",  "ville"),
    ("مكة",      "ville"),
    ("القدس",    "ville"),
    ("دمشق",     "ville"),
    ("يافا",     "ville"),
    ("العرب",    "ethnonyme"),
    ("الأمازيغ", "ethnonyme"),
    ("العباسيون","dynastie"),
    ("الأمويون", "dynastie"),
    ("المرابطون","dynastie"),
    ("فرنسا",    "pays"),
    ("مصر",      "pays"),
    ("اليابان",  "pays"),
]

print("=== DÉRIVÉS (Nisba) ===")
for mot, cat in tests:
    r, e = appliquer_regles(mot, cat)
    if r and r.get("singulier_masculin"):
        print(f"{mot} ({cat}): {r['singulier_masculin']} / {r['singulier_feminin']}")
    else:
        print(f"{mot} ({cat}): NO DERIVATION — {e}")

print("\n=== INSTANCES ===")
for mot, cat in [("فرنسا","pays"),("مصر","pays"),("العباسيون","dynastie"),("باريس","ville")]:
    info = appliquer_instances(mot, cat)
    print(f"{mot}: situation {info['situation']}")
    if info["formes"]:
        for k, v in info["formes"].items():
            print(f"  {k}: {v}")
