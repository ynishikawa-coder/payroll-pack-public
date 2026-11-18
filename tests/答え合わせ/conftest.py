"""tests/答え合わせ — 初期設定の照らしの道具（答え合わせ）の小さな試験（作り物の値だけ）。根を import の道に足す。"""
import sys
from pathlib import Path

根 = str(Path(__file__).resolve().parents[2])
if 根 not in sys.path:
    sys.path.insert(0, 根)
