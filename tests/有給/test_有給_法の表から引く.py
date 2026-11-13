"""有給の付与日数は 法の表/有給_付与日数.json を芯/計算/引く口 の 1 つの口から、付与日に効く行で引く（docs/設計/法の表.md §1.2・§2）。

作り物の置き場（tmp_path）に効く範囲の違う 2 行を置き、付与日ごとに当たる行が替わることを見る。値は作り物（国の値でない）。
"""
import copy
import datetime as dt
import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("有給_表から", 根 / "有給" / "有給.py")
有給 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(有給)
if str(根) not in sys.path:
    sys.path.insert(0, str(根))
from 芯.計算 import 引く口  # noqa: E402

本の表 = json.loads((根 / "法の表" / "有給_付与日数.json").read_text(encoding="utf-8"))


def _置き場(tmp_path, 行たち):
    t = copy.deepcopy(本の表)
    t["行"] = 行たち
    (tmp_path / "有給_付与日数.json").write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def _行(始め, 終わり, 通常, 状態="出た"):
    値 = copy.deepcopy(本の表["行"][0]["値"])
    値["通常"] = 通常
    return {"鍵": {}, "効く始め": 始め, "効く終わり": 終わり, "状態": 状態, "値": 値 if 状態 == "出た" else None, "出典": None}


def _入力():
    return {"会社": "作り物の会社", "支給月": "2099.11支給", "基準の日": "2099-10-31", "会社の値": {},
            "人": [{"NO": "1", "氏名": "作り物", "入社日": "2097-04-01", "時間.週の所定日数": 5, "時間.週の所定": 40,
                    "有給.1日の時間": 480}], "勤怠": []}


def test_有給の表は法の表の置き場にあり有給の下に無い():
    assert (根 / "法の表" / "有給_付与日数.json").exists()
    assert not (根 / "有給" / "付与の表.json").exists()
    assert 本の表["基準"] in 引く口.基準たち and 本の表["欠けた時"] == "止める"


def test_有給の付与は引く口から付与日に効く行で引く(tmp_path):
    """2098-12-31 までの行と 2099-01-01 からの行。付与日 2098-10-01 は前の行・2099-10-01 は後の行で数える。"""
    置き場 = _置き場(tmp_path, [_行(None, "2098-12-31", [10, 11, 12, 14, 16, 18, 20]),
                              _行("2099-01-01", None, [10, 21, 22, 24, 26, 28, 30])])
    引く口._読む.cache_clear()
    assert 有給.法の表("2098-10-01", 置き場)["通常"][1] == 11
    assert 有給.法の表(dt.date(2099, 10, 1), 置き場)["通常"][1] == 21
    行 = 有給.管理表(_入力(), 置き場)["行"][0]
    # 今の付与（2099-10-01・勤続 2 年 6 月）は後の行の 22 日、繰越は前の行で付与した 2098-10-01 の 11 日
    assert (行["付与日"], 行["付与日数"], 行["繰越日数"], 行["状態"]) == ("2099-10-01", "22", "11", "確定")


def test_付与日に効く行が無ければ止める(tmp_path):
    置き場 = _置き場(tmp_path, [_行(None, "2098-12-31", [10, 11, 12, 14, 16, 18, 20]),
                              _行("2099-01-01", None, None, 状態="まだ")])
    引く口._読む.cache_clear()
    with pytest.raises(引く口.欠け):
        有給.管理表(_入力(), 置き場)


def test_次の付与日の行がまだなら次の付与日数は空で前の行で代えない(tmp_path):
    置き場 = _置き場(tmp_path, [_行(None, "2099-12-31", [10, 11, 12, 14, 16, 18, 20]),
                              _行("2100-01-01", None, None, 状態="まだ")])
    引く口._読む.cache_clear()
    行 = 有給.管理表(_入力(), 置き場)["行"][0]
    assert (行["付与日数"], 行["次の付与日"], 行["次の付与日数"]) == ("12", "2100-10-01", "")


def test_11月の検査で来年1月の有給の付与日数が引ける():
    """docs/設計/法の表.md §3: 来年 1 月 1 日の基準の日で `出た` 行に当たる（止める表なので当たらなければ赤）。"""
    来年 = dt.date.today().year + 1
    r = 引く口.引く("有給_付与日数", f"{来年}-01-01")
    assert not r.仮 and r.出所.startswith("法の表/有給_付与日数")
    assert r.値["通常"] == [10, 11, 12, 14, 16, 18, 20] and r.値["時効の年"] == 2
    assert r.値["比例の週の所定時間の上限（分）"] == Decimal(1800) or r.値["比例の週の所定時間の上限（分）"] == 1800
