"""出口/出す.py（1 会社・1 支給月・1 回を 読む → 回す → 出す前の照らし → 書く）の試験。値は作り物だけ。

防ぐ故障: 照らしが赤・仮が残る人がいる月の物が 2_出す物・9_履歴・管理表 に 1 つでも書かれる（半端な出荷）。
  緑なのに 2_出す物 の新しい版・前の版の 9_履歴 への写し・管理表（回のタブと 出した物）のどれかが欠ける。
回す口は作り物（会社の一揃いを置かない）。照らしは本物の 出す前の照らし.照らす と 出口/証明.py を当てる（版だけ作り物の版）。
"""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

根 = Path(__file__).resolve().parents[2]
for p in (str(根 / "tests" / "給与エージェント"), str(根)):
    if p not in sys.path:
        sys.path.insert(0, p)

import 手伝い as 手  # noqa: E402
import 出口.証明 as 証  # noqa: E402
import 出口.名と版 as 名と版  # noqa: E402
from drive口.作り物 import 作り物のDrive  # noqa: E402

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("出す_試験", 根 / "出口" / "出す.py")
出す = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(出す)

課題 = {k: 手.材料()[k] for k in ("課題", "課題の id", "閉じた状態", "月の本文")}
月の見出し = ["会社", "支給月", "取り込み", "納品", "外した人", "止まりの理由"]
出した物の見出し = ["会社", "支給月", "回", "物", "今の版", "リンク"]


@pytest.fixture(autouse=True)
def _版(monkeypatch):
    monkeypatch.setattr(証, "パックの版", lambda: 手.版)


def 置き場を作る(前の版=False):
    口 = 作り物のDrive()
    根id = 口.根を作る()
    置き場 = {"2_出す物": 口.フォルダを作る(根id, "2_出す物"), "9_履歴": 口.フォルダを作る(根id, "9_履歴"),
            "管理表": 口.シートを作る(根id, "管理表")}
    口.表へ書く(置き場["管理表"], "'月の状況'!A1", [月の見出し, [手.会社, 手.月, "", "", "", ""]])
    口.表へ書く(置き場["管理表"], "'出した物'!A1", [出した物の見出し])
    if 前の版:
        d = 手.出す物("取り込み")
        sid = 口.シートを作る(置き場["2_出す物"], d["名"]["名"])
        口.表へ書く(sid, "'取り込み'!A1", d["表"])
    return 口, 置き場


def 回す口(*, 仮=None, 表を変える=False):
    """作り物の 月次.月を回す の返り（出す物の名は 2_出す物/9_履歴 を読んで本物の 名を付ける で付ける・証明は本物の 証明を付ける）。"""
    def 回す(口, 置き場, 会社, 支給月, 回):
        今 = [x["name"] for x in 口.子を並べる(置き場["2_出す物"])]
        履歴 = [x["name"] for x in 口.子を並べる(置き場["9_履歴"])]
        名 = 名と版.名を付ける("取り込み", 会社, 名と版.出す支給月(支給月, 回), 今ある名=今, 履歴にある名=履歴)
        d = {"物": "取り込み", "名": {"フォルダ": 名.フォルダ, "名": 名.名}, "表": copy.deepcopy(手.表)}
        c = 手.証明(d)
        表 = copy.deepcopy(手.表)
        if 表を変える:
            表[1][2] = "9999"   # 証明の後に値を差し替えた表
        x = SimpleNamespace(物="取り込み", 名=名, 表=表, 渡し方="表", csvの中身=lambda: b"")
        o = {"取り込み": x, "支給控除一覧": [], "証明": {"取り込み": c}, "外した人": [], "仮の人の行": [], "待つ訳": []}
        o.update(仮 or {})
        return o, 手.計算の元(), []
    return 回す


def 移せる(口):
    """作り物の Drive に 移す を足す（親を替えるだけ）。drive口 に 移す が入るまでの試験の口。"""
    def 移す(fid, 親id):
        口.物[fid]["親"] = 親id
    口.移す = 移す
    return 口


def _中身(口):
    return {k: (v["name"], v["親"]) for k, v in 口.物.items()}


def test_緑なら_2_出す物と_9_履歴と管理表へ書く():
    口, 置き場 = 置き場を作る(前の版=True)
    移せる(口)
    前の名 = [x["name"] for x in 口.子を並べる(置き場["2_出す物"])]
    code, out = 出す.出す(口, 置き場, 手.会社, "2099-01", "給与", 課題の材料=課題, 回す=回す口())
    assert code == 0, out
    assert out["出した"] is True
    新 = out["置いた"][0]["名"]
    assert 新.endswith("v2") or 新.endswith("2")
    assert [x["name"] for x in 口.子を並べる(置き場["2_出す物"])] == [新]   # 2_出す物 には最新の版 1 つだけ
    assert [x["name"] for x in 口.子を並べる(置き場["9_履歴"])] == 前の名   # 前の版を 9_履歴 へ移す
    月 = 口.表を読む(置き場["管理表"], "'月の状況'!A1:Z")
    assert 月[1][月の見出し.index("取り込み")] == "済" and len(月) == 2   # 同じ会社・支給月の行を上書き（足さない）
    出 = 口.表を読む(置き場["管理表"], "'出した物'!A1:Z")
    assert 出[1][:5] == [手.会社, 手.月, "月", "取り込み", 新] and 出[1][5] == 口.名で引く(置き場["2_出す物"], 新)["id"]   # リンクの口が無い drive口 は id を返す（殻がリンクに直す）
    json.dumps(out, ensure_ascii=False)


def test_3回出しても_2_出す物は最新だけ_9_履歴は重ならない():
    口, 置き場 = 置き場を作る()
    移せる(口)
    名たち = []
    for _ in range(3):
        code, out = 出す.出す(口, 置き場, 手.会社, "2099-01", "給与", 課題の材料=課題, 回す=回す口())
        assert code == 0, out
        名たち.append(out["置いた"][0]["名"])
    assert len(set(名たち)) == 3
    assert [x["name"] for x in 口.子を並べる(置き場["2_出す物"])] == 名たち[-1:]
    assert sorted(x["name"] for x in 口.子を並べる(置き場["9_履歴"])) == sorted(名たち[:-1])
    出 = 口.表を読む(置き場["管理表"], "'出した物'!A1:Z")
    assert len(出) == 2 and 出[1][4] == 名たち[-1]   # 出した物 は今の版を上書き（行を積まない）


def test_移す口が無く前の版が在れば何も置かず止める():
    口, 置き場 = 置き場を作る(前の版=True)
    前 = _中身(口), copy.deepcopy(口.物[置き場["管理表"]]["タブ"])
    code, out = 出す.出す(口, 置き場, 手.会社, "2099-01", "給与", 課題の材料=課題, 回す=回す口())
    assert code != 0 and out["出した"] is False
    assert any("移す が無い" in r for r in out["赤"]), out
    assert (_中身(口), 口.物[置き場["管理表"]]["タブ"]) == 前


def test_書く途中でDriveが落ちたら_どこまで書いたかをJSONで返す():
    口, 置き場 = 置き場を作る(前の版=True)
    def 落ちる(fid, 親id):
        raise OSError("作り物の Drive が落ちた")
    口.移す = 落ちる
    code, out = 出す.出す(口, 置き場, 手.会社, "2099-01", "給与", 課題の材料=課題, 回す=回す口())
    assert code == 2 and out["出した"] is False
    assert out["赤"] == ["書く途中で止まった: OSError: 作り物の Drive が落ちた"]
    assert out["書いた"] == [f"2_出す物: {名}" for 名 in [x["name"] for x in 口.子を並べる(置き場["2_出す物"])][1:]]
    json.dumps(out, ensure_ascii=False)


def test_照らしが赤なら何も書かず訳を返す():
    口, 置き場 = 置き場を作る()
    前 = _中身(口), copy.deepcopy(口.物[置き場["管理表"]]["タブ"])
    code, out = 出す.出す(口, 置き場, 手.会社, "2099-01", "給与", 課題の材料=課題, 回す=回す口(表を変える=True))
    assert code != 0 and out["出した"] is False
    assert out["赤"] and all(r.startswith("出す前の照らし: ") for r in out["赤"])
    assert (_中身(口), 口.物[置き場["管理表"]]["タブ"]) == 前


@pytest.mark.parametrize("仮, 当たる", [
    ({"外した人": [{"NO": "2", "理由": ["基本給が仮"]}]}, "NO 2"),
    ({"仮の人の行": [{"NO": "7"}]}, "NO 7"),
    ({"待つ訳": ["作り物の勤怠が届いていない"]}, "届いていない"),
])
def test_仮が残れば何も書かず誰のどの訳かを返す(仮, 当たる):
    口, 置き場 = 置き場を作る()
    前 = _中身(口), copy.deepcopy(口.物[置き場["管理表"]]["タブ"])
    code, out = 出す.出す(口, 置き場, 手.会社, "2099-01", "給与", 課題の材料=課題, 回す=回す口(仮=仮))
    assert code != 0 and out["出した"] is False
    assert any(r.startswith("仮: ") and 当たる in r for r in out["赤"]), out
    assert (_中身(口), 口.物[置き場["管理表"]]["タブ"]) == 前


def test_試しに書かないは緑でも書かない():
    口, 置き場 = 置き場を作る()
    前 = _中身(口)
    code, out = 出す.出す(口, 置き場, 手.会社, "2099-01", "給与", 課題の材料=課題, 書かない=True, 回す=回す口())
    assert code == 0 and out["出した"] is False and out["通す"] is True
    assert _中身(口) == 前


def test_管理表の列が足りなければ何も置かない():
    口, 置き場 = 置き場を作る()
    口.物[置き場["管理表"]]["タブ"]["出した物"] = [["会社", "支給月"]]
    code, out = 出す.出す(口, 置き場, 手.会社, "2099-01", "給与", 課題の材料=課題, 回す=回す口())
    assert code != 0 and any("リンク" in r for r in out["赤"])
    assert 口.子を並べる(置き場["2_出す物"]) == []


def test_課題の材料を渡さなければ止める():
    口, 置き場 = 置き場を作る()
    code, out = 出す.出す(口, 置き場, 手.会社, "2099-01", "給与", 回す=回す口())
    assert code != 0 and any("課題と穴を照らせない" in r for r in out["赤"])
    assert 口.子を並べる(置き場["2_出す物"]) == []


def test_根が無ければ止める(monkeypatch, capsys):
    monkeypatch.delenv("PAYROLL_OFFICE_ROOT_ID", raising=False)
    assert 出す.main(["--会社", 手.会社, "--支給月", "2099-01", "--回", "給与"]) == 2
    assert "根" in json.loads(capsys.readouterr().out)["赤"][0]


def test_支給月の字():
    assert 出す.殻の支給月("2099-01") == "2099.01支給"
    with pytest.raises(ValueError):
        出す.殻の支給月("2099/01")
