"""マスタの社員に 社員ID と前の番号の列（Drive の見出し NO）が並ぶ時: 内の NO は社員ID だけ・前の番号は 旧NO に読み、
人の照らし（止まりを集める・_止まりを仮へ・_氏名）は社員ID で当たる。読み替えで見出しが重なれば 引けない で止める。
社員ID と前の番号を違う字（E001 と 7）にして、取り違えが試験で見える形にする。作り物の値だけ。"""
import importlib.util
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(根))
import 月次  # noqa: E402
from drive口 import 置き場 as 置  # noqa: E402
from drive口.作り物 import 作り物のDrive  # noqa: E402
from 初期設定 import 型の口  # noqa: E402

_s = importlib.util.spec_from_file_location("社員IDと前の番号_試験の例", 根 / "tests" / "月次" / "月次_試験の例.py")
例 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(例)

マ = 型の口.名("マスタ")
顧, 月 = "C9001", "2099-02"
前の番号の列 = 型の口.Driveの列の読み替え(マ)["旧NO"]


def _行(頭, **値):
    return [値.get(c, "") for c in 頭]


def _マスタの置き場(頭):
    d = 作り物のDrive()
    根 = d.根を作る("給与計算")
    本 = d.シートを作る(根, 型の口.タブの本(マ, "社員"))
    d.物[本]["タブ"] = {型の口.タブの名(マ, "社員"): [頭,
                                                 _行(頭, 顧客ID=顧, 社員ID="E001", 氏名="作り物 一", **{前の番号の列: "7"}),
                                                 _行(頭, 顧客ID=顧, 社員ID="E002", 氏名="作り物 二", **{前の番号の列: "8"})]}
    return d, {型の口.タブの本(マ, "社員"): 本, "顧客ID": 顧, "会社": "作り物A"}


def _社員():
    d, p = _マスタの置き場(型の口.Driveの見出し(マ, "社員") + [前の番号の列])
    return 置.マスタを読む(d, p, "社員")


def test_内のNOは社員IDで_前の番号は旧NOに読む():
    人 = _社員()
    assert [(r["NO"], r["旧NO"]) for r in 人] == [("E001", "7"), ("E002", "8")]


def test_読み替えで見出しが重なれば引けないで止める(monkeypatch):
    換 = {k: v for k, v in 型の口.Driveの列の読み替え(マ).items() if k != "旧NO"}   # 前の番号の列の読み替えが無い型
    monkeypatch.setattr(型の口, "Driveの列の読み替え", lambda s: dict(換) if s == マ else {})
    d, p = _マスタの置き場(型の口.Driveの見出し(マ, "社員") + [前の番号の列])
    with pytest.raises(置.引けない, match="重なる"):
        置.マスタを読む(d, p, "社員")


def test_人の照らしは社員IDで当たり_前の番号では当たらない():
    人 = _社員()
    人たち = [r["NO"] for r in 人]
    表 = 例.例の表(顧, 振り分けたち=[例.例の振り分け("Q-作-91", 顧, 対象="E002"),
                                 例.例の振り分け("Q-作-92", 顧, 対象="8")])
    r = 月次.止まりを集める(表, 顧, 月, (), 人たち=人たち)
    assert {(s["対象"], s["問いの鍵"]) for s in r["止まり"]} == {("E002", "Q-作-91"), ("会社", "Q-作-92")}
    assert len(r["形の崩れ"]) == 1 and "8" in r["形の崩れ"][0]
    仮, _ = 月次._止まりを仮へ([s for s in r["止まり"] if s["対象"] != "会社"], "作り物A", 人たち)
    assert [p["NO"] for p in 仮] == ["E002"]
    assert 月次._氏名({"社員": 人}, "作り物A") == {"E001": "作り物 一", "E002": "作り物 二"}
