"""格子: 実の Sheets はタブの格子（行の数 × 列の数）の外のセルへの書きを 400 で拒む。作り物も同じに拒み、
格子を広げる は今より狭めず・足りていれば何も書かない。値は全部作り物。"""
import pytest

import drive口
from drive口 import _google
from drive口.作り物 import 作り物のDrive, 格子の外



class _呼び:
    """Google の API の呼び方（spreadsheets().get(...).execute()）を真似る作り物。受けた引数を記録する。"""
    def __init__(self, 返し, 記録):
        self._返し, self._記録 = 返し, 記録

    def __getattr__(self, 名):
        def f(*a, **k):
            self._記録.append((名, k))
            return _呼び(self._返し, self._記録)
        return f

    def execute(self):
        return self._返し.pop(0)


def _シート(格子=(500, 8)):
    d = 作り物のDrive()
    根 = d.根を作る()
    s = d.シートを作る(根, "作り物の表", ["タブ"])
    d.格子を決める(s, "タブ", *格子)
    return d, s


def test_セルの番地と要る格子():
    assert drive口.セルの番地("I1") == (1, 9)
    assert drive口.セルの番地("AA10") == (10, 27)
    assert drive口.要る格子("I1", [["x", "y"]]) == (1, 10)
    assert drive口.要る格子("A1", [["a"] * 39] * 3) == (3, 39)


def test_作り物は格子の外へ書かず足さない():
    d, s = _シート()
    with pytest.raises(格子の外):
        d.表へ書く(s, "タブ!I1", [["x"]])
    with pytest.raises(格子の外):
        d.表へ足す(s, "タブ!A1", [["x"] * 9])
    d.表へ書く(s, "タブ!H500", [["x"]])
    with pytest.raises(格子の外):
        d.表へ書く(s, "タブ!A501", [["x"]])
    d.表へ足す(s, "タブ!A1", [["y"] * 8])   # 足す（行を差し込む）は行の格子を超えてよい
    assert d.格子を読む(s)["タブ"] == (501, 8)


def test_作り物の格子の照らしは範囲の読みと同じ():
    # 行の無いセル（タブ!A:C）・列だけの範囲も、書く所と同じ読みで照らす（ValueError で止めない）
    d, s = _シート()
    d.表へ書く(s, "タブ!A:C", [["x", "y", "z"]])
    with pytest.raises(格子の外):
        d.表へ書く(s, "タブ!G:I", [["x", "y", "z"]])


def test_作り物の新しいシートは既定の格子():
    d = 作り物のDrive()
    s = d.シートを作る(d.根を作る(), "作り物の表", ["タブ"])
    assert d.格子を読む(s) == {"タブ": drive口.新しいタブの格子}
    with pytest.raises(格子の外):
        d.表へ書く(s, "タブ!A1", [["x"] * (drive口.新しいタブの格子[1] + 1)])


def test_格子を広げるは狭めず_足りていれば版を変えない():
    d, s = _シート()
    版 = d.版を読む(s)
    d.格子を広げる(s, "タブ", 10, 8)
    assert d.格子を読む(s)["タブ"] == (500, 8) and d.版を読む(s) == 版
    d.格子を広げる(s, "タブ", 10, 10)
    assert d.格子を読む(s)["タブ"] == (500, 10)
    d.表へ書く(s, "タブ!I1", [["確認", "原本の名前"]])
    assert d.表を読む(s, "タブ")[0][8:] == ["確認", "原本の名前"]


def _gの返し(行, 列):
    return {"sheets": [{"properties": {"sheetId": 7, "title": "タブ", "gridProperties": {"rowCount": 行, "columnCount": 列}}},
                       {"properties": {"sheetId": 8, "title": "別", "gridProperties": {"rowCount": 1, "columnCount": 1}}}]}


def test_Googleの口の格子を広げるは大きさを決めて渡し_狭めない():
    記録 = []
    口 = _google.Googleの口(None, _呼び([_gの返し(500, 8), None], 記録))
    口.格子を広げる("作り物-表", "タブ", 10, 10)
    頼み = [k for 名, k in 記録 if 名 == "batchUpdate"]
    assert 頼み == [{"spreadsheetId": "作り物-表", "body": {"requests": [{"updateSheetProperties": {
        "properties": {"sheetId": 7, "gridProperties": {"rowCount": 500, "columnCount": 10}},
        "fields": "gridProperties.rowCount,gridProperties.columnCount"}}]}}]


def test_Googleの口の格子を広げるは足りていれば書かず_無いタブは止める():
    記録 = []
    口 = _google.Googleの口(None, _呼び([_gの返し(500, 8)], 記録))
    口.格子を広げる("作り物-表", "タブ", 10, 8)
    assert not [名 for 名, _ in 記録 if 名 == "batchUpdate"]
    with pytest.raises(KeyError):
        _google.Googleの口(None, _呼び([_gの返し(500, 8)], [])).格子を広げる("作り物-表", "無い", 1, 1)


def test_Googleの口の格子を読む():
    口 = _google.Googleの口(None, _呼び([_gの返し(500, 8)], []))
    assert 口.格子を読む("作り物-表") == {"タブ": (500, 8), "別": (1, 1)}


def test_出すの置くは新しいタブの格子より広い中身を広げてから書く():
    from types import SimpleNamespace
    from 出口 import 出す as 出
    d = 作り物のDrive()
    置き場 = {出.出す置き: d.フォルダを作る(d.根を作る(), "作り物の置き場")}
    幅 = drive口.新しいタブの格子[1] + 13
    中身 = [[f"列{j}" for j in range(幅)], ["1"] * 幅]
    g = {"d": SimpleNamespace(物="作り物の物", 名=SimpleNamespace(名="作り物の名"), 渡し方="表"), "中身": 中身}
    残る = []
    出._置く(d, 置き場, g, 残る)
    assert 残る[-1]["中身"] == "書けた"
    assert d.格子を読む(残る[-1]["id"])["作り物の物"] == (drive口.新しいタブの格子[0], 幅)
    assert d.表を読む(残る[-1]["id"], "作り物の物") == 中身
