"""説明（docstring）に、同じ module の定数の値を手で写さない見張り。

なぜ在るか（根治・2026-11-23）: 定数を直しても説明の写しが古いまま残った（育休の 14 日の決まりの始めの年月・
法の表の見張りの既定の日数）。説明は定数の名で指し、値は定数にだけ書く。
見る所: 芯/・入口/・出口/・道具/ の .py。module の頭と型の頭の定数（`名 = 値`・`名: 型 = 値`）の中の数
（整数・小数・`Decimal("…")`・組や表の中の数）を拾い、説明の中に同じ数が出たら写しと見て赤にする。
前は書き方（「YYYY-MM」「＝N」）を並べていたので「2022年10月」「90 日」「(90)」が抜けた。今は書き方でなく
数そのものを桁の境で照らす（全角の数字は半角に直してから・1 未満の小数は百分率の形も）。
1 桁の整数は説明に普通に出る数なので見ない。定数と同じ行の注釈（# …）は説明でないので見ない。
"""
from __future__ import annotations

import ast
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[1]
見る所 = ("芯", "入口", "出口", "道具")


def _数たち(n: ast.AST) -> list:
    """定数の式の中の数を全部拾う（組・並び・表の値・負の数・Decimal/Fraction の字）。"""
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
        return [n.value]
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
        return _数たち(n.operand)
    if (isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))
            and (n.func.id if isinstance(n.func, ast.Name) else n.func.attr) in ("Decimal", "Fraction")
            and n.args and isinstance(n.args[0], ast.Constant)):
        try:
            return [Decimal(str(n.args[0].value))]
        except InvalidOperation:
            return []
    if isinstance(n, (ast.Tuple, ast.List, ast.Set)):
        return [x for e in n.elts for x in _数たち(e)]
    if isinstance(n, ast.Dict):
        return [x for e in n.values for x in _数たち(e)]
    return []


def _写しの形(v) -> list[str]:
    """説明の中で写しと見る数の字（桁の境で照らす）。"""
    if isinstance(v, int):
        return [str(abs(v))] if abs(v) >= 10 else []
    d = Decimal(str(v)).normalize()
    if d == d.to_integral_value():
        return _写しの形(int(d))
    形 = [format(abs(d), "f")]
    if abs(d) < 1:
        形.append(format((abs(d) * 100).normalize(), "f") + "%")
    return 形


def _在るか(形: str, 行: str) -> bool:
    return re.search(r"(?<![\d.])" + re.escape(形) + r"(?!\.?\d)", 行) is not None


def 写し(名: str, 字: str) -> list[str]:
    t = ast.parse(字)
    定数: dict[str, ast.AST] = {}
    for 頭 in [t] + [n for n in ast.walk(t) if isinstance(n, ast.ClassDef)]:
        for n in 頭.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                定数[n.targets[0].id] = n.value
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None:
                定数[n.target.id] = n.value
    説明 = [unicodedata.normalize("NFKC", d)
            for n in ast.walk(t) if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            for d in [ast.get_docstring(n)] if d]
    out = []
    for k, v in 定数.items():
        for 形 in dict.fromkeys(f for x in _数たち(v) for f in _写しの形(x)):
            for d in 説明:
                for l in d.splitlines():
                    if _在るか(形, l):
                        out.append(f"{名}: 定数 {k} の値「{形}」を説明に写している: {l.strip()[:80]}")
    return out


def test_説明に定数の値を写していない():
    files = sorted(p for d in 見る所 for p in (根 / d).rglob("*.py"))
    assert files, "見る .py が 1 つも無い（見る所の名が変わった）"
    out = [x for p in files for x in 写し(p.relative_to(根).as_posix(), p.read_text(encoding="utf-8"))]
    assert out == [], "\n".join(out)


def test_注入_年月の定数を説明に写すと赤():
    字 = '始め = (2022, 10)\n\ndef f():\n    """2022-10 の月から。"""\n'
    assert 写し("作り物.py", 字)


def test_注入_日数の定数を説明に写すと赤():
    字 = '"""使い方: 日数＝90 で回す。"""\n既定の日数 = 90\n'
    assert len(写し("作り物.py", 字)) == 1


@pytest.mark.parametrize("定数, 説明", [
    ("始め = (2022, 10)", "2022年10月から数える。"),
    ("始め = (2022, 10)", "2022/10 から。"),
    ("既定の日数 = 90", "既定は 90 日。"),
    ("既定の日数 = 90", "既定は90日。"),
    ("既定の日数 = 90", "既定（90）で回す。"),
    ("既定の日数 = 90", "既定は ９０ 日（全角）。"),
    ("既定の日数: int = 90", "既定は 90 日（型の注釈つきの定数）。"),
    ("率 = Decimal('0.1021')", "率は 0.1021。"),
    ("率 = Decimal('0.1021')", "率は 10.21% で引く。"),
    ("率 = 0.05", "率は 5％。"),
    ("表 = {'甲': 1200, '乙': 3}", "甲は 1200 円。"),
    ("下限 = -15", "下限は -15。"),
])
def test_注入_定数の数を書き方を変えて写しても赤(定数, 説明):
    字 = f'from decimal import Decimal\n{定数}\n\ndef f():\n    """{説明}"""\n'
    assert 写し("作り物.py", 字), 説明


def test_名で指す説明と注釈と違う数は緑():
    字 = ('"""日数は `既定の日数`。"""\n既定の日数 = 90   # 日数＝90 は注釈なので見ない\n始め = (2022, 10)\n'
         'def f():\n    """`始め` の月から。1900 や 190・900・90.5 は別の数。"""\n')
    assert 写し("作り物.py", 字) == []
