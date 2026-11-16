"""見張り: 直し 9（型の版 8→9）。作り物の値だけ。

- 版 8 の会社: 社員に 社保.二以上事業所の按分、勤務の型に 時間.月の所定日数 の列が空で足り、型の並びになる（2 度目は書く手順が 0）
- 前の形の「二以上事業所の按分の率」は、事務所の前の形の読み替え（作り物の殻・版 9 の塊）で 社保.二以上事業所の按分 へ値ごと移る
"""
import datetime as dt
import json
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent
根 = ここ.parent.parent
sys.path.insert(0, str(根 / "道具" / "寄せ"))
sys.path.insert(0, str(ここ))
import 当てる  # noqa: E402
import 作り物の殻  # noqa: E402
import 直し as 直しの形  # noqa: E402

今日 = dt.date(2026, 11, 13)
M = "03_マスタ"
人の列, 型の列 = "社保.二以上事業所の按分", "時間.月の所定日数"


def 寄せる(会社):
    return 当てる.見通す(作り物の殻.前の形を渡す(会社), 当てる.型を開く(根 / "初期設定" / "型.json"), 直しの形.読む(), 今日)


def 今の版():
    return 当てる.型を開く(根 / "初期設定" / "型.json")["版"]


def 前の形():
    return json.loads((ここ / "作り物の前の形.json").read_text(encoding="utf-8"))


def 書く(会社):
    r = 寄せる(会社)
    assert r["寄せられない物"] == [], r["寄せられない物"]
    assert r["値の保ち"]["合う"]
    書いた = 当てる.手順を当てる(会社, r["書く手順"])
    書いた["型の版"] = r["寄せた後の値"]["型の版"]
    return r, 書いた


def test_版8の会社に列を空で足し並びをそろえる():
    _, 版9 = 書く(前の形())
    assert 版9["型の版"] == 今の版()   # 今の型の版（最後の直しまで当たる）
    版8 = json.loads(json.dumps(版9))
    版8["型の版"] = 8
    for t, c in (("社員", 人の列), ("勤務の型", 型の列)):
        rows = 版8["シート"][M][t]
        i = rows[0].index(c)
        for x in rows:
            del x[i]
    r, 後 = 書く(版8)
    assert [s for s in r["書く手順"]], "直し 9 が当たっていない"
    for t, c in (("社員", 人の列), ("勤務の型", 型の列)):
        assert 後["シート"][M][t] == 版9["シート"][M][t], t
        i = 後["シート"][M][t][0].index(c)
        assert all(x[i] == "" for x in 後["シート"][M][t][1:])   # 空で足す＝計算は変わらない
    assert 寄せる(後)["書く手順"] == []


def test_前の形の按分の率は前の形の読み替えで新しい項目へ移る():
    会社 = 前の形()
    社員 = 会社["シート"][M]["社員"]
    社員[1][社員[0].index("二以上事業所の按分の率")] = "0.4"   # 作り物の値
    r, 後 = 書く(会社)
    rows = r["寄せた後の値"]["シート"][M]["社員"]
    assert "二以上事業所の按分の率" not in rows[0]
    assert [x[rows[0].index(人の列)] for x in rows[1:]] == ["0.4", ""]
    assert 寄せる(後)["書く手順"] == []
