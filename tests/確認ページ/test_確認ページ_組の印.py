"""会社の根と確認事項の名の印は、型.json の 置き場（`10_会社/<組>`）1 つに揃う（台帳 815d）。
パックの場所は印の字を持たず、パックの確認ページ.py から読む（字で写せば落ちる）。

前は紙（Drive の型・毎月の流れ・README）が `10_会社/<会社>`・`確認事項_<会社>_` と書き、道具と型.json は `<組>` を読んだ。
組と会社の名が違う束では、紙どおりの置き場が実の木に無く、名で数える版がずれた。紙・道具・見張りのどこかが
別の印に戻れば、この試験が名指しで落ちる。"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
見る物 = [p for g in ("docs/**/*.md", "*/README.md", "初期設定/*.md", "確認ページ/*.py", "出口/*.py", "道具/**/*.py",
                    "plugins/payroll-agent/**/*.py", "plugins/payroll-agent/**/*.md")
         for p in 根.glob(g) if "CHANGELOG" not in p.name]
_根の印 = re.compile(r"10_会社/(<[^>/]+>)")
_名の印 = re.compile(r"確認事項_(<[^>_]+>)_")


def _型の印() -> str:
    型 = json.loads((根 / "初期設定/型.json").read_text(encoding="utf-8"))
    印たち = set(_根の印.findall(json.dumps(型, ensure_ascii=False)))
    assert len(印たち) == 1, f"型.json の 置き場 の印が 1 つでない: {印たち}"
    return 印たち.pop()


def 外れ(印: str, 文たち: dict[str, str]) -> list[str]:
    return [f"{名}: {m}" for 名, 文 in 文たち.items() for pat in (_根の印, _名の印) for m in pat.findall(文) if m != 印]


def test_紙と道具の会社の根と確認事項の名は型の印だけを使う():
    印 = _型の印()
    assert 印 == "<組>"
    文たち = {str(p.relative_to(根)): p.read_text(encoding="utf-8") for p in 見る物}
    assert 外れ(印, 文たち) == []


def test_確認ページの印は型の印と同じ():
    import importlib.util
    spec = importlib.util.spec_from_file_location("確認ページ", 根 / "確認ページ/確認ページ.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.会社の印 == _型の印()


@pytest.mark.parametrize("文", ["`10_会社/<会社>/8_確認事項/`", "確認事項_<会社>_<支給月>_v<版>.html"])
def test会社の印に戻した紙は拒む(文):
    assert 外れ("<組>", {"作り物.md": 文}) != []


_道具たち = ("plugins/payroll-agent/bin/パックの場所.py",)
_印の字 = re.compile(r"<[^<>\s]+>")


def 道具が持つ印の字(文: str) -> list[str]:
    """コードの字の値（docstring を除く）のうち、`<…>` の印そのものの字。道具は会社の根の印を写さずパックから読む。"""
    木 = ast.parse(文)
    説明 = {id(n.body[0].value) for n in ast.walk(木)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    return [n.value for n in ast.walk(木)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in 説明 and _印の字.fullmatch(n.value)]


@pytest.mark.parametrize("道具", _道具たち)
def test_パックの場所は会社の根の印を字で持たない(道具):
    assert 道具が持つ印の字((根 / 道具).read_text(encoding="utf-8")) == []


def test_パックの場所が読む会社の置き場は型の印の行():
    """パックの場所は 置き場の名たち の `型.json の印` の行を 会社 として返す（印の字は確認ページ.py から読む）。"""
    sys.path.insert(0, str(根 / "plugins/payroll-agent/bin"))
    try:
        spec = importlib.util.spec_from_file_location("組の印_パックの場所", 根 / _道具たち[0])
        場所 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(場所)
    finally:
        sys.path.remove(str(根 / "plugins/payroll-agent/bin"))
    確認 = importlib.util.spec_from_file_location("組の印_確認ページ", 根 / "確認ページ/確認ページ.py")
    m = importlib.util.module_from_spec(確認)
    確認.loader.exec_module(m)
    assert 場所.確認ページの名の形(根)[1] == {"会社": m.置き場の名たち[_型の印()], "事務所": m.置き場の名たち["事務所"]}


@pytest.mark.parametrize("文", ['x = d.get("<会社>")', 'x = d.get("<組>")', 'K = {"<組>": 1}'])
def test_印を字で写した道具は拒む(文):
    assert 道具が持つ印の字(文) != []
