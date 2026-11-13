"""見張り: 管理表の 3 タブの見出しの並びが黙って変わらない（型を直す時は版と写しを同じ PR で直す）。"""
import importlib.util
import json
from pathlib import Path

ここ = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("管理表_試験", ここ.parent.parent / "管理表" / "管理表.py")
管理表 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(管理表)


def test_見出しの並びが写しと同じ():
    写し = json.loads((ここ / "見出しの並び.json").read_text(encoding="utf-8"))
    assert 管理表.型()["版"] == 写し["版"]
    assert 管理表.全部の見出し() == 写し["見出し"]
