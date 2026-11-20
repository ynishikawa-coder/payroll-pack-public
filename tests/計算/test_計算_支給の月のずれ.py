"""支給の月のずれ（当月 0・翌月 1・翌々月 2）の正本は 芯/設定の表.json の行の `月のずれ` の 1 か所（台帳 2026-11-20）。

選べる値の並びの位置からずれを作ると、表に値を 1 つ足すだけで黙って「3 か月前」の意味が付く。写し（暦.py の dict・
支給月の字.py の並び・段の解決.py の語の並び）を持つと、表を直しても写しが古いまま残る。ここで、ずれは字で持った値だけから読み、
並びを入れ替えても意味が変わらず、ずれの無い値を足すと止まる事を作り物で確かめる。
"""
import copy
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
if str(根) not in sys.path:
    sys.path.insert(0, str(根))

from 芯 import 設定, 支給月の字  # noqa: E402
from 芯.計算 import 暦  # noqa: E402


def _表を替える(monkeypatch, 替える):
    表 = copy.deepcopy(設定.表())
    替える(表["支払.支給の月"])
    monkeypatch.setattr(設定, "表", lambda: 表)


def test_ずれは表の字の値だけから読む():
    assert 設定.支給の月のずれ() == {"当月": 0, "翌月": 1, "翌々月": 2}
    assert 暦.期間("2027-03", "末", "当月")[1].month == 3
    assert 暦.期間("2027-03", "末", "翌々月")[1].month == 1


def test_並びを入れ替えても意味は変わらない(monkeypatch):
    _表を替える(monkeypatch, lambda e: e.update(選べる値=list(reversed(e["選べる値"]))))
    assert 暦.期間("2027-03", "末", "翌月")[1].month == 2  # 並びの位置で作るなら 1 つ前の月にならない
    assert 支給月の字.字にする(2027, 3, "置き場", 月分=1) == "2027.03支給（1月分）"


def test_ずれの無い値を足すと止まる(monkeypatch):
    _表を替える(monkeypatch, lambda e: e["選べる値"].append("3か月後"))  # 壊す: 値だけ足し、ずれを書かない
    with pytest.raises(ValueError, match="月のずれ の鍵"):
        暦.期間("2027-03", "末", "翌月")
    with pytest.raises(ValueError, match="月のずれ の鍵"):
        支給月の字.字にする(2027, 3, "置き場", 月分=2)


def test_ずれの値が数でない_重なると止まる(monkeypatch):
    _表を替える(monkeypatch, lambda e: e["月のずれ"].update(翌々月=1))  # 壊す: 重なる
    with pytest.raises(ValueError, match="重ならない整数"):
        設定.支給の月のずれ()
    _表を替える(monkeypatch, lambda e: e["月のずれ"].update(翌々月="2"))  # 壊す: 字
    with pytest.raises(ValueError, match="重ならない整数"):
        設定.支給の月のずれ()
