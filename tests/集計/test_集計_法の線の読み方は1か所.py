"""法の線の読み方（芯の名 → 法の線.json の線と欄）は芯の中で 1 か所（芯/計算/法の線の読み方.py）。

芯/計算（支給控除）と 芯/集計（法の線の橋）が別々に表を持つと、片方だけ直して集計と計算が食い違う。
表の（線, 欄）の組が 法の線の読み方.py の外の芯の .py に字で出てきたら赤（2 つ目の表を書いた印）。
"""
import json
import re
from pathlib import Path

from 芯.計算 import 法の線の読み方 as 読み

根 = Path(__file__).resolve().parents[2]


def test_集計が引く名は読み方の表にある():
    assert set(読み.集計の要る + 読み.集計の任意) <= set(読み.読み方)
    assert not set(読み.集計の要る) & set(読み.集計の任意)


def test_線と欄の組は読み方の外の芯に書かない():
    組たち = {(線, 欄) for 線, 欄, _ in 読み.読み方.values()}
    外 = []
    for p in sorted((根 / "芯").rglob("*.py")):
        if p.name == "法の線の読み方.py":
            continue
        本文 = p.read_text(encoding="utf-8")
        外 += [f"{p.relative_to(根)}: {線}・{欄}" for 線, 欄 in 組たち
               if re.search(rf'"{re.escape(線)}"\s*,\s*' + (f'"{re.escape(欄)}"' if 欄 else "None"), 本文)]
    assert not 外, "法の線の（線, 欄）の組が 法の線の読み方.py の外に在る（読み方は 1 か所へ）:\n" + "\n".join(外)


def test_読み方の線は法の表にある():
    表 = json.loads((根 / "法の表" / "法の線.json").read_text(encoding="utf-8"))
    在る = {r["鍵"].get("線") for r in 表["行"]}
    assert {線 for 線, _, _ in 読み.読み方.values()} <= 在る


def test_前の表の形を戻すと赤():
    """照らしが空回りしていない（前の 支給控除 の 1 行の形を見つける）。"""
    線, 欄, _ = 読み.読み方["時間.日の法定"]
    assert re.search(rf'"{線}"\s*,\s*"{欄}"', '"時間.日の法定": ("法定労働時間", "日の時間", ""),')
