"""源泉の 4 表（月額・日額・賞与の算出率・電算機の特例）の 2026 年（令和 8 年分）の行。

答えは全部、国税庁「令和8年分 源泉徴収税額表」に書いてある数字。
https://www.nta.go.jp/publication/pamph/gensen/zeigakuhyo2026/01.htm
引く口は 芯/計算/引く口.py の 1 つを使う（test_国の例.py と同じ）。
"""
import json
import re
import sys
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
if str(根) not in sys.path:
    sys.path.insert(0, str(根))

from 芯.計算.引く口 import 引く as _引く  # noqa: E402

法の表 = 根 / "法の表"
源泉の表 = ["源泉_月額表", "源泉_日額表", "源泉_賞与の算出率", "源泉_電算機の特例"]


def 引く(名: str, 基準: str):
    return _引く(名, 基準).値


def 行(v, 金額):
    return next(r for r in v["表"]["行"] if r[0] <= 金額 < r[1])


# ---- 行の見張り

@pytest.mark.parametrize("名", 源泉の表)
def test_2026年と2027年の行が切れ目なく並ぶ(名):
    行たち = json.loads((法の表 / f"{名}.json").read_text(encoding="utf-8"))["行"]
    範囲 = [(r["効く始め"], r["効く終わり"], r["状態"]) for r in 行たち]
    assert 範囲[:2] == [("2026-01-01", "2026-12-31", "出た"), ("2027-01-01", "2027-12-31", "出た")]
    出典 = 行たち[0]["出典"]
    assert 出典["URL"].startswith("https://www.nta.go.jp/publication/pamph/gensen/zeigakuhyo2026/data/")
    assert 出典["照らした元"].startswith("https://www.nta.go.jp/publication/pamph/gensen/zeigakuhyo2026/data/")
    assert re.fullmatch(r"[0-9a-f]{64}", 出典["sha256"]) and re.fullmatch(r"[0-9a-f]{64}", 出典["照らした元のsha256"])
    assert "令和7年4月30日財務省告示" in 出典["告示"] and 行たち[0]["注"]


@pytest.mark.parametrize("名", 源泉の表)
def test_支払日で年の行が替わる(名):
    assert 引く(名, "2026-11-25") == 引く(名, "2026-12-31")
    assert 引く(名, "2026-12-31") != 引く(名, "2027-01-01")


# ---- 国税庁「令和8年分 源泉徴収税額表」19〜22 頁の「税額表の使い方」の設例
# https://www.nta.go.jp/publication/pamph/gensen/zeigakuhyo2026/data/19-22.pdf

def test_月額表_甲欄の使用例():
    """支給 420,000 円・社会保険料等 63,400 円・扶養親族等 2 人 → 356,000 円以上 359,000 円未満の行の 7,020 円。"""
    r = 行(引く("源泉_月額表", "2026-11-25"), 420000 - 63400)
    assert (r[0], r[1]) == (356000, 359000)
    assert r[2][2] == 7020


def test_月額表_乙欄の使用例():
    """支給 80,750 円・社会保険料等なし・申告書なし → 105,000 円未満は 3.063％（1 円未満切り捨て）＝ 2,473 円。"""
    v = 引く("源泉_月額表", "2026-11-25")
    assert v["下の端"]["未満"] == 105000
    税 = (Decimal(80750) * Decimal(str(v["下の端"]["乙の率%"])) / 100).to_integral_value(rounding=ROUND_FLOOR)
    assert 税 == 2473


def test_賞与の算出率_使用例():
    """賞与 554,000 円・社会保険料 85,593 円・前月 196,616 円・2 人 → 143 千円以上 276 千円未満・2.042％・9,564 円。"""
    v = 引く("源泉_賞与の算出率", "2026-12-10")
    前月 = 196616
    当たり = [b for b in v["甲"] if (b["甲"][2][0] or 0) <= 前月 < (b["甲"][2][1] or 10**12)]
    assert len(当たり) == 1 and 当たり[0]["甲"][2] == [143000, 276000]
    率 = Decimal(str(当たり[0]["率%"]))
    assert 率 == Decimal("2.042")
    assert (Decimal(554000 - 85593) * 率 / 100).to_integral_value(rounding=ROUND_FLOOR) == 9564


# ---- 境の行（国税庁 令和 8 年分の 01-07.pdf・08-14.pdf・15-16.pdf・18.pdf の数字）

def test_月額表_境の行():
    v = 引く("源泉_月額表", "2026-11-25")
    assert v["表"]["行"][0] == [105000, 107000, [170, 0, 0, 0, 0, 0, 0, 0], 3800]
    assert 行(v, 261905) == [260000, 263000, [6530, 4920, 3310, 1680, 0, 0, 0, 0], 39600]
    assert v["表"]["行"][-1] == [737000, 740000, [71380, 64900, 58440, 51980, 45510, 39040, 32580, 26110], 257700]
    点 = {p["額"]: p for p in v["点"]}
    assert 点[740000]["乙"] == 259200 and 点[1710000]["乙"] == 655400
    assert v["7人を超える1人ごとに引く"] == 1610


def test_日額表_境の行():
    v = 引く("源泉_日額表", "2026-11-25")
    assert v["下の端"]["未満"] == 3500
    assert v["表"]["行"][0] == [3500, 3600, [5, 0, 0, 0, 0, 0, 0, 0], 120, 0]
    assert v["表"]["行"][-1] == [23900, 24000, [2240, 2025, 1810, 1590, 1380, 1165, 950, 730], 8250, 738]
    assert {p["額"] for p in v["点"]} >= {24000, 57500, 116500}


def test_賞与の算出率_境():
    v = 引く("源泉_賞与の算出率", "2026-11-25")
    assert v["甲"][0]["甲"][0] == [None, 82000]
    assert v["甲"][-1]["甲"][7] == [3717000, None]
    assert [(b["以上"], b["未満"]) for b in v["乙"]] == [(None, 224000), (224000, 295000), (295000, 527000),
                                                        (527000, 1118000), (1118000, None)]


def test_電算機の特例_令和8年分の段():
    v = 引く("源泉_電算機の特例", "2026-11-25")
    assert v["給与所得控除"]["段"][0] == {"以上": None, "以下": 158333, "定額": 54167}
    assert v["基礎控除"]["段"][0] == {"以上": None, "以下": 2120833, "定額": 48334}
    assert v["配偶者（特別）控除"] == 31667
