"""出口の指定の判断の口（月次/出口の指定.py）。試算（出口 null）か正式かと、正式の出口の欠けを殻でなくパックが決める。

根（2026-11-24）: 試算か正式か・正式の出口に何が要るかを殻（事務所の側の口）が自分で照らしていた＝パックの出口の形が
変わっても殻は古い照らしのまま。判断をパックの口 1 つに寄せた。
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parent.parent.parent
口 = 根 / "月次" / "出口の指定.py"
_s = importlib.util.spec_from_file_location("出口の指定_試験", 口)
指 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(指)

正式 = {"取り込み": {"道具": "作り物の給与ソフト"}, "支給控除一覧": {}}


def test_試算は赤でなく出さない():
    # 口の約束: 試算（出口 null）は計算だけ・何も出さない（出す では止める）
    got = 指.照らす(None)
    assert got["赤"] == [] and got["試算"] is True and got["出す時の赤"] and "何も出さない" in got["出す物が無い訳"]


def test_正式は通す():
    got = 指.照らす(正式)
    assert got == {**got, "赤": [], "試算": False, "出す時の赤": []}


@pytest.mark.parametrize("出口, 欠け", [
    ({"取り込み": {"道具": "作り物の給与ソフト"}}, "支給控除一覧"),
    ({"支給控除一覧": {}}, "取り込み"),
    ({"取り込み": {"道具": " "}, "支給控除一覧": {}}, "取り込み.道具"),
])
def test_正式の出口に欠けが在れば止める(出口, 欠け):
    # 口の約束: 正式は 2 つの出力の指定と 取り込み.道具 が全部要る
    assert f"正式の出口に {欠け} が無い" in 指.照らす(出口)["赤"][0]


def test_出口がdictでもnullでもなければ止める():
    assert "dict か null" in 指.照らす("作り物")["赤"][0]


def test_有給の値を渡す試算は出すで止めない():
    assert 指.照らす(None, 有給の値={"x": 1})["出す時の赤"] == []


def test_口から呼ぶ():
    r = subprocess.run([sys.executable, "-I", str(口), "照らす"], input=json.dumps({"出口": None, "回": "賞与"}),
                       capture_output=True, text=True, cwd=根)
    assert r.returncode == 0 and json.loads(r.stdout)["出す物が無い訳"].startswith("賞与を回す")


@pytest.mark.parametrize("入力, 訳", [
    ('{"出口": null}', "回 は"),                       # 回が欠けた＝月とみなさない
    ('{"出口": null, "回": "作り物の回"}', "回 は"),     # 知らない回
    ("[1", "JSON でない"),                             # JSON でない
    ("[]", "JSON の表"),                               # 表でない
])
def test_形の崩れた入力は拒む(入力, 訳):
    # 口の約束: 回が欠けた・知らない・形の崩れた入力は 拒む と終わりの値 2（月とみなして照らさない）
    r = subprocess.run([sys.executable, "-I", str(口), "照らす"], input=入力, capture_output=True, text=True, cwd=根)
    assert r.returncode == 2 and 訳 in json.loads(r.stdout)["拒む"]
