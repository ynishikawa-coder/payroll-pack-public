"""問いの相手（質問と回答「誰に」）はいつも事務所の担当者 1 人。字の正本は 型.json の 決まった値 で、
初期設定（始める・設問）と有給はそこから引く。種が別の相手（先方 など）を名乗れば止める（注入の試験）。作り物の値だけ。

根（2026-11-23）: 型.json の 誰に が「事務所・先方」と 2 つの相手を許し、3 つの .py が既定の字「先方」を
それぞれ写して書いていた（決まり「問いの相手はいつも事務所の担当者 1 人」と食い違う）。
"""
import ast
import importlib.util
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
ここ = Path(__file__).resolve().parent


def _読む(名, path):
    s = importlib.util.spec_from_file_location(名, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


口 = _読む("問いの相手_型の口", 根 / "初期設定" / "型の口.py")
始める = _読む("問いの相手_始める", 根 / "初期設定" / "始める.py")
設問の試験 = _読む("問いの相手_設問の試験", ここ / "test_初期設定_設問.py")
承知の試験 = _読む("問いの相手_承知の試験", 根 / "tests" / "有給" / "test_有給_付与の承知.py")

C, 支給月 = "作り物の会社", "2099.04支給"
相手 = 口.問いの相手()   # 試験も字を持たず正本（型.json の 決まった値）から引く
_種 = {"箱": "読み方", "何が無いか": "読み方: 作り物", "質問": "作り物の読み方を教えてください", "答え方の例": "A／B"}


def test_問いの相手は型の決まった値の1つだけ():
    assert 相手 == "事務所の担当者"   # 決まり「問いの相手はいつも事務所の担当者 1 人」の字はここで 1 回だけ照らす
    列 = next(c for c in 口.タブ("質問と回答", "質問")["列"] if c["名"] == "誰に")
    assert 列["決まった値"] == 相手 and "先方" not in 列["意味"]


@pytest.mark.parametrize("名乗り", ["先方", "顧問先", "会社", "オーナー", "事務所",
                                 " 事務所の担当者", "事務所の担当者 ", "事務所の　担当者"])
def test_種が別の相手を名乗れば止める(名乗り):
    with pytest.raises(ValueError, match="問いの相手"):
        口.問いの相手を当てる({"誰に": 名乗り})
    with pytest.raises(ValueError, match="問いの相手"):
        設問の試験.まとめる([{**_種, "誰に": 名乗り}], 会社=C, 支給月=支給月, 今日="2099-04-01")


@pytest.mark.parametrize("名乗り", [None, "", 相手])
def test_名乗りが無いか担当者なら担当者(名乗り):
    種 = {**_種} if 名乗り is None else {**_種, "誰に": 名乗り}
    m = 設問の試験.まとめる([種], 会社=C, 支給月=支給月, 今日="2099-04-01")
    assert m["問い"] and {q["誰に"] for q in m["問い"]} == {相手}


def test_始めるの問いも担当者():
    問い = 始める.問いを起こす({"会社": C, "組": "作り物の組", "最初の支給月": 支給月, "今日": "2099-03-01", "既にある": []})
    assert 問い and {q["誰に"] for q in 問い} == {相手}


def test_有給の問いも担当者():
    t = 承知の試験
    行たち = t.台帳("2026-09-16", "2026-10-31", NO="1") + t.台帳("2026-10-01", "2026-10-31", NO="2",
                                                              変える={"2026-10-05": t._台帳の試験.年休})
    結果 = t.有給.管理表(t.入力([{**t.付与しない人, **t.承知の印}], 行たち=行たち))
    assert 結果["問い"] and {q["誰に"] for q in 結果["問い"]} == {相手}


def test_誰にへ字を直に書くコードが無い():
    """「誰に」の値を字で書く .py が無い（正本の 型.json から引く道だけ）。"""
    外す = {"tests", ".git", "node_modules"}
    見つけた = []
    for p in 根.rglob("*.py"):
        if 外す & set(p.relative_to(根).parts):
            continue
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Dict):
                for k, v in zip(n.keys, n.values):
                    if isinstance(k, ast.Constant) and k.value == "誰に" and isinstance(v, ast.Constant):
                        見つけた.append(f"{p.relative_to(根)}:{n.lineno}")
            if isinstance(n, ast.Call) and getattr(n.func, "attr", "") in ("get", "setdefault") and n.args \
                    and isinstance(n.args[0], ast.Constant) and n.args[0].value == "誰に" and len(n.args) > 1:
                見つけた.append(f"{p.relative_to(根)}:{n.lineno}")
    assert 見つけた == []


def test_型の決まった値を替えれば読み手が全部追う(monkeypatch):
    """型.json の 決まった値 を書き替えると、始める・設問・有給の問いが替えた字を書き、元の字の名乗りは止まる
    （読み手が字を写さず正本から引く事の注入の試験）。"""
    替えた = "作り物の相手"
    元の読み = Path.read_text

    def 読む(self, *a, **k):
        t = 元の読み(self, *a, **k)
        if self.name == "型.json" and self.parent.name == "初期設定":
            t = t.replace(f'"決まった値": "{相手}"', f'"決まった値": "{替えた}"')
        return t

    monkeypatch.setattr(Path, "read_text", 読む)
    assert 口.問いの相手() == 替えた
    with pytest.raises(ValueError, match="問いの相手"):
        口.問いの相手を当てる({"誰に": 相手})
    m = 設問の試験.まとめる([_種], 会社=C, 支給月=支給月, 今日="2099-04-01")
    assert {q["誰に"] for q in m["問い"]} == {替えた}
    問い = 始める.問いを起こす({"会社": C, "組": "作り物の組", "最初の支給月": 支給月, "今日": "2099-03-01", "既にある": []})
    assert {q["誰に"] for q in 問い} == {替えた}
    t = 承知の試験
    行たち = t.台帳("2026-09-16", "2026-10-31", NO="1") + t.台帳("2026-10-01", "2026-10-31", NO="2",
                                                              変える={"2026-10-05": t._台帳の試験.年休})
    結果 = t.有給.管理表(t.入力([{**t.付与しない人, **t.承知の印}], 行たち=行たち))
    assert {q["誰に"] for q in 結果["問い"]} == {替えた}
