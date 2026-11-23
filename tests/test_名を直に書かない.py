"""Drive の木と名の正本は 初期設定/型.json の 1 か所（「木」「名の形」・シートの「シート」・md の雛形の「名」）。
道具は 初期設定/型の口.py の 名()・道()・物たち()・台帳の名()・シートの型() で引き、名を直に書かない。

前は道具ごとに `2_マスタ`・`10_会社/`・`台帳_<年>`・タブの名の並びを直に書き、型.json と Drive の型.md と道具が
別々に名を持った（台帳の名が 台帳_<年> と 台帳_<支給年> の 2 つになり、文書のタブの数が型とずれた）。
ここは道具の .py（試験・文書の外）の字の値を読み、木の名・シートの名・md の名を直に書いた所と、
1 つのシートのタブを全部並べた所（タブの数え上げの写し＝タブを足すとずれる）を拒む。docstring・説明の文の中の名（字の 1 区切りが名そのものでない物）は拒まない。

拒まない（残る穴）: タブの名を選んで並べた所（全部でない並び＝道具がどのタブを扱うかの鍵。タブの名はタブを引く鍵で、木の名と違い型で役を持たない）。 役の名と Drive の名が同じ字の物（管理表・質問と回答・事務所の設定・受け取り口）は、
役で引く呼び出しと見分けられないので見ない。出す物の「物」（支給控除一覧_雇用 など）は名の形の部品＝識別の鍵なので見ない。
"""
import ast
import json
import re
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[1]
型 = json.loads((根 / "初期設定" / "型.json").read_text(encoding="utf-8"))


def _拒む名() -> set[str]:
    """役の名と字の違う Drive の名（直に書くと型.json とずれうる物）。"""
    木の名 = dict(型["木"]["名"])
    木の名.update({s["役"]: s["シート"] for s in 型["シート"]})
    木の名.update({m["役"]: m["名"] for m in 型["md の雛形"]})
    return {名 for 役, 名 in 木の名.items() if 名 != 役 and not 名.startswith("<")}


拒む名 = _拒む名()
台帳の頭 = 型["名の形"]["台帳"]["形"].split("<", 1)[0]            # 台帳_
シートのタブ = [{t["タブ"] for t in s["タブ"]} for s in 型["シート"]]


def _区切りが名か(区切り: str) -> bool:
    x = 区切り.strip()
    return x in 拒む名 or (x.startswith(台帳の頭) and x != 台帳の頭.rstrip("_")) or x == 台帳の頭


def _直に書いた所(src: str) -> list[tuple[int, str]]:
    t = ast.parse(src)
    docs = set()
    for n in ast.walk(t):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            b = n.body[0]
            if isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) and isinstance(b.value.value, str):
                docs.add(id(b.value))
    out = []
    for n in ast.walk(t):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            if any(_区切りが名か(s) for s in re.split(r"[/\\]", n.value)):
                out.append((n.lineno, n.value))
        if isinstance(n, (ast.Tuple, ast.List, ast.Set)):
            字 = [e.value for e in n.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if len(字) == len(n.elts) and len(ts := set(字)) >= 2 and ts in シートのタブ:
                out.append((n.lineno, "タブの名の並び " + "・".join(字)))
    return out


def _道具たち():
    for p in sorted(根.rglob("*.py")):
        r = p.relative_to(根)
        if r.parts[0] in ("tests", ".git") or "__pycache__" in r.parts:
            continue
        yield r


def test_道具は木とシートとmdの名を直に書かない():
    外れ = [f"{r}:{n}: {v!r}" for r in _道具たち() for n, v in _直に書いた所((根 / r).read_text(encoding="utf-8"))]
    assert not 外れ, "名は 初期設定/型の口.py の 名()・道()・台帳の名()・シートの型() から引く:\n" + "\n".join(外れ)


@pytest.mark.parametrize("悪い", [
    'x = "2_マスタ"',
    'x = f"10_会社/{組}/1_決まり/"',
    'x = "台帳_" + 年',
    'x = "台帳_<支給年>"',
    'x = re.compile(r"台帳_\\d{4}")',
    'x = ["00_事務所", y]',
    'x = "3_月ごと/<支給月>/2_出す物"',
    'x = "給与のルール.md"',
    'x = ("社員", "人ごとの支給控除", "会社", "支給控除の項目", "勤務の型", "つなぎ", "変更の記録")',
    'x = {"既定", "会社の一覧", "置き場"}',
])
def test_注入_直に書いた名は拒む(悪い):
    assert _直に書いた所("import re\n" + 悪い + "\n")


@pytest.mark.parametrize("良い", [
    'x = 型の口.名("マスタ")',
    'x = 型の口.道("会社の根", "確認事項")',
    'x = "型に マスタ のシートが無い"',
    'x = f"{型の口.名(\'マスタ\')} が読めない（2_マスタ の社員）"',
    'def f():\n    """2_マスタ/社員 を読む"""',
    'x = "社員"',
    'x = ("社員", 1)',
    'x = ("勤務の型", "社員", "会社")',   # 選んだタブの並び（全部でない）は扱うタブの鍵
    'x = ("社員", "質問", "既定")',   # 別のシートのタブの寄せ集めは数え上げでない
])
def test_役で引く所と説明の文は拒まない(良い):
    assert not _直に書いた所(良い + "\n")
