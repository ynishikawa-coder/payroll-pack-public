"""tests/出口 — 出口の部品の小さな試験（作り物の値だけ）。根を import の道に足す。"""
import sys
from pathlib import Path

根 = str(Path(__file__).resolve().parents[2])
if 根 not in sys.path:
    sys.path.insert(0, 根)
