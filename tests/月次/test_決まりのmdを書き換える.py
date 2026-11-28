"""月次/決まりのmdを書き換える: 答えの書き戻し の md を書き換える 手順を、今の中身を照らしてから 1_決まり の md へ当てる。
人の直しを上書きしない（前の印が今と違えば書かない）・無い md を作らない・同じ md の手順は最後の本文を 1 度だけ書く。
値は全部作り物（作り物のDrive・作り物の会社）。本物の Drive には触らない。"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(根))

import 月次  # noqa: E402
from drive口.作り物 import 作り物のDrive  # noqa: E402

_s = importlib.util.spec_from_file_location("決まりのmd_試験の例", 根 / "tests" / "月次" / "月次_試験の例.py")
例 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(例)
書 = 月次._書き戻し()
_s = importlib.util.spec_from_file_location("月次_決まりのmdを書き換える", 根 / "月次" / "決まりのmdを書き換える.py")
当 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(当)

顧, 月 = "C9001", "2099-02"
元 = "## 欠勤\n- 引く\n## 遅刻\n- 引く\n"


def _会社(給与=元, 作業="## 締め\n- 25 日\n"):
    d = 作り物のDrive()
    根id = d.根を作る("給与計算")
    決 = d.フォルダを作る(根id, "1_決まり")
    ids = {"給与のルール.md": d.ファイルを置く(決, "給与のルール.md", 給与.encode(), "text/markdown")}
    if 作業 is not None:
        ids["作業のルール.md"] = d.ファイルを置く(決, "作業のルール.md", 作業.encode(), "text/markdown")
    return d, {"1_決まり": 決, "顧客ID": 顧}, ids


def _手順(*振り分け, md=None):
    r = 書.振り分けの書き戻し(list(振り分け), 顧, 月, 今日="2099-02-01", md=md or {"給与のルール.md": 元})
    assert r["赤"] == [], r
    return r


def _読む(d, fid):
    return d.ファイルを読む(fid).decode()


def test_書き戻しのmdの手順は組んだ元の全文の前の印を持つ():
    r = _手順(例.例の振り分け("Q-作-41", 顧, 反映先="給与のルール.md", 何を="欠勤", 値="半日は引かない"))
    (x,) = [x for x in r["手順"] if x["する"] == "md を書き換える"]
    assert x["前の印"] == 書.md_の印(元)


def test_今の中身が組んだ元と同じなら最後の本文を書き_名と親と数は変えない():
    d, 置, ids = _会社()
    r = _手順(例.例の振り分け("Q-作-41", 顧, 反映先="給与のルール.md", 何を="欠勤", 値="半日は引かない"))
    前 = {k: dict(v) for k, v in d.物.items()}
    code, out = 当.当てる(d, 置, r)
    assert code == 0 and out["書いた"] == ["給与のルール.md"] and "赤" not in out
    assert "- ⟦答え:Q-作-41｜欠勤⟧ 半日は引かない" in _読む(d, ids["給与のルール.md"]).splitlines()
    assert set(d.物) == set(前) and d.物[ids["給与のルール.md"]]["name"] == "給与のルール.md"
    assert d.物[ids["給与のルール.md"]]["親"] == 前[ids["給与のルール.md"]]["親"]
    assert _読む(d, ids["作業のルール.md"]) == "## 締め\n- 25 日\n"
    # 打ち直しても同じ（既に当たっていた md は書かない）
    code, out = 当.当てる(d, 置, r)
    assert code == 0 and out["書いた"] == [] and out["既に当たっていた"] == ["給与のルール.md"]


def test_人が直した後なら書かずに止める():
    人の直し = 元 + "## 早退\n- 引く\n"
    d, 置, ids = _会社(給与=人の直し)
    r = _手順(例.例の振り分け("Q-作-41", 顧, 反映先="給与のルール.md", 何を="欠勤", 値="半日は引かない"))
    code, out = 当.当てる(d, 置, r)
    assert code == 2 and out["書いた"] == [] and out["残りの手順"] == []
    assert "人が直した" in out["赤"][0]
    assert _読む(d, ids["給与のルール.md"]) == 人の直し


def test_同じmdの手順が続けば最後の本文を1度だけ書く_続かなければ止める():
    d, 置, ids = _会社()
    r = _手順(例.例の振り分け("Q-作-41", 顧, 反映先="給与のルール.md", 何を="欠勤", 値="半日は引かない"),
             例.例の振り分け("Q-作-42", 顧, 反映先="給与のルール.md", 何を="遅刻", 値="5 分は引かない"))
    xs = [x for x in r["手順"] if x["する"] == "md を書き換える"]
    assert len(xs) == 2 and xs[1]["前の印"] == 書.md_の印(xs[0]["本文"])
    書いた回 = []
    元の書く = d.ファイルを書き換える
    d.ファイルを書き換える = lambda i, b: (書いた回.append(i), 元の書く(i, b))[1]
    code, out = 当.当てる(d, 置, r)
    assert code == 0 and 書いた回 == [ids["給与のルール.md"]]
    assert _読む(d, ids["給与のルール.md"]) == xs[1]["本文"]
    d2, 置2, ids2 = _会社()
    崩し = [xs[0], {**xs[1], "前の印": 書.md_の印("別の全文")}]
    code, out = 当.当てる(d2, 置2, 崩し)
    assert code == 2 and "続かない" in out["赤"][0] and _読む(d2, ids2["給与のルール.md"]) == 元


def test_無いmdは作らず止め_ほかのmdにも書かない():
    d, 置, ids = _会社(作業=None)
    r1 = _手順(例.例の振り分け("Q-作-41", 顧, 反映先="給与のルール.md", 何を="欠勤", 値="半日は引かない"))
    x = {"する": "md を書き換える", "先": "作業のルール.md", "本文": "## 締め\n- 20 日\n",
         "前の印": 書.md_の印("## 締め\n- 25 日\n")}
    n = len(d.物)
    code, out = 当.当てる(d, 置, [*r1["手順"], x])
    assert code == 2 and "作業のルール.md が無い" in out["赤"][0]
    assert len(d.物) == n and _読む(d, ids["給与のルール.md"]) == 元


@pytest.mark.parametrize("崩し, 訳", [
    ({"先": "ほかの.md"}, "でない"),
    ({"本文": 3}, "字でない"),
    ({"前の印": None}, "前の印が無い"),
])
def test_形の崩れた手順は当てない(崩し, 訳):
    d, 置, ids = _会社()
    x = {"する": "md を書き換える", "先": "給与のルール.md", "本文": "新", "前の印": 書.md_の印(元), **崩し}
    code, out = 当.当てる(d, 置, [x])
    assert code == 2 and 訳 in out["赤"][0] and _読む(d, ids["給与のルール.md"]) == 元


def test_md以外の手順は並びのまま残りの手順に返し_書き戻しが赤なら当てない():
    d, 置, ids = _会社()
    ほか = [{"する": "値を書く", "先": "作り物", "値": 1}, {"する": "行を足す", "先": "作り物", "行": []}]
    code, out = 当.当てる(d, 置, {"手順": ほか, "赤": []})
    assert code == 0 and out["残りの手順"] == ほか and out["書いた"] == []
    code, out = 当.当てる(d, 置, {"手順": ほか, "赤": ["作り物の赤"]})
    assert code == 2 and out["残りの手順"] == []


def test_試しに書かないは照らすだけで書かない():
    d, 置, ids = _会社()
    r = _手順(例.例の振り分け("Q-作-41", 顧, 反映先="給与のルール.md", 何を="欠勤", 値="半日は引かない"))
    code, out = 当.当てる(d, 置, r, 書かない=True)
    assert code == 0 and out["書く"] == ["給与のルール.md"] and _読む(d, ids["給与のルール.md"]) == 元


def test_書いた後の読み直しが違えば止める():
    d, 置, ids = _会社()
    r = _手順(例.例の振り分け("Q-作-41", 顧, 反映先="給与のルール.md", 何を="欠勤", 値="半日は引かない"))
    d.ファイルを書き換える = lambda i, b: None   # 書いたふりで書かない口
    code, out = 当.当てる(d, 置, r)
    assert code == 2 and "読み直した" in out["赤"][0]


def test_口は根が無ければ2で終わり_Driveを開かない():
    env = {k: v for k, v in os.environ.items() if k not in ("PAYROLL_OFFICE_ROOT_ID", "GOOGLE_DRIVE_SA_JSON")}
    p = subprocess.run([sys.executable, str(根 / "月次" / "決まりのmdを書き換える.py"), "--会社", 顧],
                       input=json.dumps({"手順": []}), capture_output=True, text=True, env=env)
    assert p.returncode == 2 and "根" in json.loads(p.stdout)["赤"][0]


def test_既に当たった本文がBOMとCRLFで置かれていても書き直さない():
    """読むのは口の 字を読む（BOM を落とし改行を LF にそろえる）＝改行・BOM の違いだけで書き直さない。"""
    d, 置, ids = _会社()
    r = _手順(例.例の振り分け("Q-作-41", 顧, 反映先="給与のルール.md", 何を="欠勤", 値="半日は引かない"))
    code, out = 当.当てる(d, 置, r)
    assert code == 0 and out["書いた"] == ["給与のルール.md"]
    fid = ids["給与のルール.md"]
    d.物[fid]["中身"] = b"\xef\xbb\xbf" + _読む(d, fid).replace("\n", "\r\n").encode()
    code, out = 当.当てる(d, 置, r)
    assert code == 0 and out["書いた"] == [] and out["既に当たっていた"] == ["給与のルール.md"]


def test_読む所で上限に当たれば当てるは上げ_口は何も書かずに2で終わる(monkeypatch, capsys):
    import drive口
    d, 置, ids = _会社()
    r = _手順(例.例の振り分け("Q-作-41", 顧, 反映先="給与のルール.md", 何を="欠勤", 値="半日は引かない"))
    前 = _読む(d, ids["給与のルール.md"])
    呼ばれた = []

    def 尽きた(i):
        呼ばれた.append(i)
        raise drive口.上限("読む")
    d.字を読む = 尽きた
    with pytest.raises(drive口.上限):
        当.当てる(d, 置, r)
    assert len(呼ばれた) == 1   # 残りの md で打ち重ねない
    monkeypatch.setattr(drive口, "開く", lambda **k: d)
    from drive口 import 置き場 as 置き場の口
    monkeypatch.setattr(置き場の口, "会社の置き場", lambda 口, 根, 会社: 置)
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(json.dumps(r, ensure_ascii=False)))
    assert 当.main(["--会社", 顧, "--根", "作り物の根"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["書いた"] == [] and "上限" in out["赤"][0]
    assert d.物[ids["給与のルール.md"]]["中身"].decode() == 前


@pytest.mark.parametrize("置く形", ["crlf", "bom", "bom_crlf"])
def test_元がCRLFやBOMで殻がその字のまま渡しても人の直しと取り違えず書く(置く形):
    """レビュー red（2026-11-29）: 前の印 は殻が渡した字のまま、今 は口の 字を読む でそろえた字の印だったので、
    Drive の md が CRLF・BOM だと中身が同じでも「人が直した」で止まり、組み直しても抜けなかった。印は両方そろえた字で取る。"""
    置く = 元.replace("\n", "\r\n") if "crlf" in 置く形 else 元
    if "bom" in 置く形:
        置く = "﻿" + 置く
    d, 置, ids = _会社(給与=置く)
    r = _手順(例.例の振り分け("Q-作-41", 顧, 反映先="給与のルール.md", 何を="欠勤", 値="半日は引かない"),
             md={"給与のルール.md": 置く})
    code, out = 当.当てる(d, 置, r)
    assert code == 0 and out["書いた"] == ["給与のルール.md"], out
    assert "- ⟦答え:Q-作-41｜欠勤⟧ 半日は引かない" in 月次_字(d, ids["給与のルール.md"]).splitlines()
    人の直し = 置く + "## 早退\r\n- 引く\r\n"
    d2, 置2, _ = _会社(給与=人の直し)
    code, out = 当.当てる(d2, 置2, r)
    assert code == 2 and "人が直した" in out["赤"][0]


def 月次_字(d, fid):
    import drive口
    return drive口.字にする(d.ファイルを読む(fid))
