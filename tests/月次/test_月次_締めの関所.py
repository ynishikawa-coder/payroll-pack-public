"""締めの記録の判断の口（月次/締めの関所.py）。殻が持っていた締めるの判断をここで照らす。作り物の値だけ。

根（2026-11-24）: 型が古い台帳で締めるか を殻（事務所の側の口）が自分で決めていた＝パックの版を上げても殻の判断は古いまま。
判断をパックの口 1 つに寄せ、殻は台帳を読み書きするだけにした。
2026-11-25 オーナー: 月を版で割らない止め（締め直す・締めた時の版で回す）は畳んだ。締めた時の版は証明に残る記録だけ。
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parent.parent.parent
口 = 根 / "月次" / "締めの関所.py"
_s = importlib.util.spec_from_file_location("締めの関所_試験", 口)
関 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(関)

C, M = "作り物の会社", "2000.01支給"
見出し = ["会社", "支給月", "NO", "氏名", "状態", "締めた日", "締めた人"]


def _行(*NO):
    return [{"会社": C, "支給月": M, "NO": n, "状態": "締まった"} for n in NO]


def _記録(版たち: dict | None = None, 列=True):
    h = 見出し + (["パックの版"] if 列 else [])
    rows = [[C, M, n, "", "締まった", "", ""] + ([v] if 列 else []) for n, v in (版たち or {}).items()]
    return [h, *rows]


def _cli(何, x):
    r = subprocess.run([sys.executable, "-I", str(口), 何], input=json.dumps(x, ensure_ascii=False),
                       capture_output=True, text=True, cwd=根)
    return r.returncode, json.loads(r.stdout)


# ---- 締める
def test_今の版を押して締める():
    got = 関.締める(_行("0001"), _記録(), 版="v9.9.9", 型に列=True)
    assert got["赤"] == [] and got["書く行"][0]["パックの版"] == "v9.9.9" and got["パックの版"] == "v9.9.9"


def test_型が古い台帳では締めない():
    # 口の約束: 型に パックの版 の列が在るのに台帳に無い＝寄せてから締める（版を書かずに締めない）
    got = 関.締める(_行("0001"), _記録(列=False), 版="v9.9.9", 型に列=True)
    assert "型が古い台帳" in got["赤"][0] and "書く行" not in got


def test_同じ月を前の版で締めた行が在っても今の版で締める():
    got = 関.締める(_行("0002"), _記録({"0001": "v0.0.1"}), 版="v9.9.9", 型に列=True)
    assert got["赤"] == [] and got["書く行"][0]["パックの版"] == "v9.9.9"


def test_同じ版で締めた行の続きは締める():
    got = 関.締める(_行("0002"), _記録({"0001": "v9.9.9"}), 版="v9.9.9", 型に列=True)
    assert got["赤"] == []


@pytest.mark.parametrize("行, 訳", [
    ([], "1 行以上"),
    ([{"会社": C, "支給月": M, "NO": ""}], "鍵"),
    ([{"会社": C, "支給月": M, "NO": "1", "パックの版": "v1"}], "パックの版 を書かない"),
    ([{"会社": C, "支給月": M, "NO": "1"}, {"会社": "別の作り物の会社", "支給月": M, "NO": "2"}], "1社・1支給月"),
])
def test_締める行の形が崩れていれば締めない(行, 訳):
    assert 訳 in 関.締める(行, _記録(), 版="v9.9.9", 型に列=True)["赤"][0]


def test_置いたパックの型には版の列が在る():
    assert 関.型に版の列が在るか() is True


def test_口から呼んでも型が古い台帳を止める():
    rc, out = _cli("締める", {"行": _行("0001"), "締めの記録": _記録(列=False)})
    assert rc == 0 and "型が古い台帳" in out["赤"][0]


@pytest.mark.parametrize("何, 入力", [
    ("知らない", "{}"),                                                       # 知らない口
    ("締める", "{ 崩れた"),                                                   # JSON でない
    ("締める", "[]"),                                                         # 入力が表でない
    ("締める", json.dumps({"行": [{"会社": C, "支給月": M, "NO": "1"}], "締めの記録": [見出し, 5]})),  # 記録の行が列でない
    ("締めた時の版", "{}"),                                                   # 畳んだ口
    ("締め直す", "{}"),                                                       # 畳んだ口
])
def test_形の崩れた入力は拒む(何, 入力):
    # 口の約束: 形の崩れた入力はどの崩れでも 拒む と終わりの値 2（traceback と終わりの値 1 で抜けない）
    r = subprocess.run([sys.executable, "-I", str(口), 何], input=入力, capture_output=True, text=True, cwd=根)
    assert r.returncode == 2 and "拒む" in json.loads(r.stdout)
