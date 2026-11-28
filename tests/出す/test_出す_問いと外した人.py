"""出す.py が確認ページを読まない（選択肢の振り分けの正本は 質問と回答 の 振り分け のタブの候補の行）・月次へ 問いの行たち を
渡さない事、管理表の鍵の支給月を字の形でなく (年, 月) で比べる事、外した人の理由を管理表の行に載せる事の見張り。値は全部作り物。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_出す as 元  # noqa: E402
import test_出す_置き場 as 置  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "月次"))
from 月次_試験の例 import 例の問い, 例の表  # noqa: E402

手, 出す = 元.手, 元.出す
顧 = "C9001"


def _問いを書く(d, 本: str, 表) -> None:
    from 初期設定 import 質問と回答 as 問答
    行たち = [SimpleNamespace(**{k: x.get(k, "") for k in 問答._列["問い"]}) for x in 表.問いたち]
    d.表へ書く(本, f"'{問答.Driveのタブ('問い')}'!A1", [問答.見出し("問い"), *[問答._行の値("問い", x) for x in 行たち]])


def _置いて回す(monkeypatch, capsys, 回: str = "月", *, 前に=None, 試し: bool = True, 緑: bool = True):
    """聞いている問い（答えの無い問い）を置いて出す.main を試しで回す → (月次が受けた kw, 出す の JSON)。
    前に(d, ids) は回す前に置き場へ足す物・緑=False の時は (code, out, d) を返す。"""
    import drive口
    import 月次
    from 月次 import 年の台帳を起こす as 年
    d, 根, ids = 置._事務所()
    if 回 == "賞与":
        from 管理表 import 管理表 as 表
        d.物[ids["管理表"]]["タブ"][表.Driveのタブ("賞与の状況")] = [list(元.月の見出し)]
    _問いを書く(d, ids["質問と回答"], 例の表(顧, 問いたち=[{**例の問い("Q-作り物-1", 顧), "リンク": "作り物の無いid"}]))
    monkeypatch.setattr(drive口, "開く", lambda **_: d)
    受け: dict = {}

    def 回した物(支給月, 会社, kw, 物="取り込み", 回の字="月"):
        受け["kw"] = kw
        名 = 元.名と版.名を付ける(物, 会社, 元.名と版.出す支給月(支給月, 回の字), **置._前の版の名(kw))
        x = SimpleNamespace(物=物, 名=名, 表=元.copy.deepcopy(手.表), 渡し方="表", csvの中身=lambda: b"",
                            人=tuple(r[0] for r in 手.表[1:]))
        o = {"取り込み": x, "支給控除一覧": [], "外した人": [], "仮の人の行": [], "待つ訳": []}
        if 回の字 == "月":
            o["有給休暇管理表"] = 元.有給の作り物(x, 会社, 支給月, 置._前の版の名(kw))
        return o
    monkeypatch.setattr(月次, "月を回す", lambda 支給月, 会社, タブ, **kw: 回した物(支給月, 会社, kw))
    monkeypatch.setattr(月次, "賞与の元を読む", lambda *a, **k: {"賞与の引数": {}, "支給一覧": [], "支給日": "2099-01-25"})
    monkeypatch.setattr(月次, "賞与を回す", lambda 支給月, 会社, タブ, 支給一覧, **kw: 回した物(支給月, 会社, kw, 回の字="賞与"))
    monkeypatch.setattr(年, "前の年の確定した勤怠", lambda *a, **k: {"前の確定した勤怠": [], "前の確定した勤怠の区間": [],
                                                                "前の締めの記録": []})
    if 前に:
        前に(d, ids)
    code = 出す.main(["--会社", 手.会社, "--支給月", "2099-01", "--回", 回, "--根", 根, *(["--試しに書かない"] if 試し else [])])
    out = json.loads(capsys.readouterr().out)
    if not 緑:
        return code, out, d
    assert code == 0 and not out.get("赤"), out
    return 受け["kw"], out


def test_月を回すへ問いの行を渡さず確認ページを読まない(monkeypatch, capsys):
    import 月次
    assert not hasattr(月次, "_確認ページ")
    kw, out = _置いて回す(monkeypatch, capsys, "月")
    assert "問いの行たち" not in kw and kw["質問と回答"] is not None
    assert not any("確認ページ" in x for x in out.get("知らせ", [])), out


def test_賞与を回すへも問いの行を渡さない(monkeypatch, capsys):
    kw, _ = _置いて回す(monkeypatch, capsys, "賞与")
    assert "問いの行たち" not in kw


def test_管理表の鍵の支給月は字の形でなく年と月で比べる():
    f = 出す._同じ値
    assert f("支給月", "2099.01支給（1月分）", "2099.01支給")
    assert not f("支給月", "2099.02支給", "2099.01支給")
    for 読めない in ("作り物", "2099-01", "2099/1", " 2099.01支給"):   # 鍵の字でない＝止める（字のまま比べない）
        with pytest.raises(ValueError, match="読めない"):
            f("支給月", 読めない, "2099.01支給")
    assert f("会社", " 作り物の会社 ", "作り物の会社")


def test_管理表の行の支給月が別の形でも同じ行へ書く():
    from types import SimpleNamespace as N
    書いた: list = []
    口 = N(表へ書く=lambda 本, 所, v: 書いた.append(("書く", 所)), 表へ足す=lambda 本, 所, v: 書いた.append(("足す", 所)))
    今 = [["会社", "支給月", "外した人"], ["作り物の会社", "2099.01支給（1月分）", "0"]]
    import 管理表.管理表 as 表   # noqa: F401  Driveのタブ を引く
    出す._管理表へ(口, {出す._管理表の鍵(): "作り物の本"}, "月の状況", 今,
               [{"会社": "作り物の会社", "支給月": "2099.01支給", "外した人": "1"}])
    assert 書いた and 書いた[0][0] == "書く" and 書いた[0][1].endswith("!A2"), 書いた


def test_外した人の理由を管理表の行に載せ_月ごとに書き直す():
    o = {"待つ訳": ["NO 0003: 作り物の問い Q-作り物-1 の答えが無い"], "外した人": [], "仮の人の行": []}
    行 = 出す.管理表の行("作り物の会社", "2099.01支給", o, "外した人: NO 0009（前の月の訳） ／ 人の書いた作り物の訳")
    assert 行["外した人"] == "1"
    assert 行["止まりの理由"] == "外した人: NO 0003（作り物の問い Q-作り物-1 の答えが無い） ／ 人の書いた作り物の訳", 行
    assert 出す.管理表の行("作り物の会社", "2099.01支給", {}, 行["止まりの理由"])["止まりの理由"] == "人の書いた作り物の訳"


def test_読む途中の上限は別の訳に化けず何も書かずに止める(monkeypatch, capsys):
    import drive口
    d, 根, ids = 置._事務所()
    monkeypatch.setattr(drive口, "開く", lambda **_: d)

    def 上限で読めない(*a, **k):
        raise drive口.上限("作り物の読み")
    monkeypatch.setattr(d, "表を読む", 上限で読めない)
    code = 出す.main(["--会社", 手.会社, "--支給月", "2099-01", "--回", "月", "--根", 根])
    out = json.loads(capsys.readouterr().out)
    assert code == 2 and out["出した"] is False, out
    assert any("上限" in r for r in out["赤"]) and not any("計算の元が欠ける" in r for r in out["赤"]), out


@pytest.mark.parametrize("試し", [True, False])
def test_管理表の読めない支給月は物を置く前に止める_試しも同じ赤(monkeypatch, capsys, 試し):
    """出した物のタブの同じ会社の行の支給月が読めない字＝新しい版を置く・前の版を移す前に止める（書く途中で止めない）。"""
    import copy
    from 管理表 import 管理表 as 表

    def 読めない行を置く(d, ids):
        タブ = d.物[ids["管理表"]]["タブ"][表.Driveのタブ("出した物")]
        h = タブ[0]
        タブ.append(["2099-01" if k == "支給月" else (手.会社 if k == "会社" else "") for k in h])
    前の物 = {}

    def 置いて覚える(d, ids):
        読めない行を置く(d, ids)
        前の物["物"] = copy.deepcopy(d.物)
    code, out, d = _置いて回す(monkeypatch, capsys, 前に=置いて覚える, 試し=試し, 緑=False)
    assert code == 2 and out["出した"] is False, out
    assert any("'2099-01' が読めない" in r for r in out["赤"]) and not any("書く途中" in r for r in out["赤"]), out
    assert d.物 == 前の物["物"]   # 何も置かず・移さず・書かない
