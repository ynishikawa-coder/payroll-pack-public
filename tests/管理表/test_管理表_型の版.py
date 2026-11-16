"""管理表「会社」の 型の版 を読む口（寄せる道具の入力へ）。作り物の会社だけ。"""
import importlib.util
from pathlib import Path

import pytest

ここ = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("管理表_試験_型の版", ここ.parent.parent / "管理表" / "管理表.py")
管理表 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(管理表)


def _今の値(*行):
    h = 管理表.見出し("会社")
    return [h] + [[{"会社": c, "組": "作り物の組", "型の版": v}.get(k, "") for k in h] for c, v in 行]


def test_型の版を読み_空は0で名を出す():
    o = 管理表.型の版({"今の値": _今の値(("作り物A", "11"), ("作り物B", ""))})
    assert o == {"型の版": {"作り物A": 11, "作り物B": 0}, "版が空": ["作り物B"]}


def test_行の無い会社と数でない版は拒む():
    with pytest.raises(管理表.拒む, match="行が無い"):
        管理表.型の版({"今の値": _今の値(("作り物A", "11")), "会社たち": ["作り物C"]})
    with pytest.raises(管理表.拒む, match="数でない"):
        管理表.型の版({"今の値": _今の値(("作り物A", "十一"))})


def test_寄せの管理表へ書くの行はそのまま書く口へ渡せる():
    手順 = 管理表.書く({"タブ": "会社", "今の値": _今の値(("作り物A", "3")), "会社の一覧": {"作り物A": "作り物の組"},
                     "受け持つ組": "作り物の組", "行たち": [{"会社": "作り物A", "型の版": "11", "最後に配った日": "2026-11-16"}]})
    assert {(s["列"], s["値"]) for s in 手順} == {("型の版", "11"), ("最後に配った日", "2026-11-16")}
