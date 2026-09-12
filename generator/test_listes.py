# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from regles import appliquer_regles

tests = [
    ("فرنسا", "pays"),
    ("أنتيغوا وباربودا", "pays"),
    ("المغرب", "pays"),
    ("النمسا", "pays"),
    ("القاهرة", "ville"),
    ("تيبازة", "ville"),
    ("مكة", "ville"),
    ("إفريقيا", "supranational"),
    ("القطب الشمالي", "supranational"),
    ("العباسيون", "dynastie"),
    ("بنو هلال", "dynastie"),
    ("العرب", "ethnonyme"),
    ("الفايكنغ", "ethnonyme"),
]

for mot, cat in tests:
    r, e = appliquer_regles(mot, cat)
    if r:
        print(f"OK  {mot:30} ({cat:15}) -> {r['singulier_masculin']}")
    else:
        print(f"BLQ {mot:30} ({cat:15}) -> PAS DE DERIVATION")
