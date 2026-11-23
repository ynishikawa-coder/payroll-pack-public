"""選べる値・既定・役の字の正本は 1 か所（型.json・管理表/型.json・芯/設定の表.json・芯/計算/暦.py）。道具の .py は写さず引く。

前は 見当の拠り所 の頭（見込みでない拠り所）を 設問.py と 確認ページ.py が別々の正規表現で持ち、反映済み の書き方を 設問.py が
字の並びで持ち、確認ページ の 状況 の字・休日出勤の数え方の欄・時間.暦 の祝日の扱いを 段の解決.py と 確認ページ.py が写して持った
（正本の型に足した頭・値が道具に届かず、片方だけが知らない字を通した）。

ここは道具の .py（試験・文書の外）の構文木を読み、次を拒む:
1. 正本の値の組（拠り所の頭・反映済みの字・状況の字・休出の欄・祝日の扱い）から 2 つ以上を並べた並び（tuple・list・set）。
2. 正本の値の組から 2 つ以上を | でつないだ字（正規表現の写し）。
3. 管理表の 状況 の字（役と字の違う物＝お答え待ち・お答えいただいた）を直に書いた字。
4. 引数 誰が聞いた の既定を字で書いた所（既定の正本は 型.json の 質問と回答「質問」の 誰が聞いた）。

拒まない（残る穴）: 頭を 1 つだけ使った字（`法の線（…）` など）は値で、書く時に 型の口.問いの行 が型の頭で照らす。
芯/設定の表.json の 選ぶ 項目の一部を役の組で持つ所（月給の形・時間.制度の組・人.区分の組など）はまだ .py が字で持ち、ここは照らさない（原因の台帳に行き先つき）。
源泉.報酬 の 対象・対象でない は 芯/計算/委託.py と 段の解決.py がまだ別々に持つ（芯の設定の表の形が 字 で選べる値が無い）。
"""
import ast
import json
import re
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[1]
_型 = json.loads((根 / "初期設定" / "型.json").read_text(encoding="utf-8"))
_表 = json.loads((根 / "管理表" / "型.json").read_text(encoding="utf-8"))
_設定 = {e["名"]: e for e in json.loads((根 / "芯" / "設定の表.json").read_text(encoding="utf-8"))["項目"]}


def _問いの列(名: str) -> dict:
    for s in _型["シート"]:
        for t in s["タブ"]:
            if t["タブ"] == "質問":
                for c in t["列"]:
                    if c["名"] == 名:
                        return c
    raise KeyError(名)


def _状況() -> dict:
    t = next(t for t in _表["タブ"] if t["タブ"] == "確認ページ")
    return next(c for c in t["列"] if c["名"] == "状況")["値の役"]


def _祝日の扱い() -> set[str]:
    src = (根 / "芯" / "計算" / "暦.py").read_text(encoding="utf-8")
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "祝日の扱い" for t in n.targets):
            return {e.value for e in n.value.elts}
    raise AssertionError("芯/計算/暦.py に 祝日の扱い が無い")


反映済み = _問いの列("反映済み")
値の組 = {
    "見当の拠り所 の頭": {h["頭"] for h in _問いの列("見当の拠り所")["頭"]},
    "反映済み の字": {x for x in [*反映済み["選べる値"], *反映済み["同じに読む字"]] if x},
    "状況 の字": set(_状況().values()),
    **{f"休日出勤の数え方 の {k}": set(v) for k, v in _設定["休日.休日出勤の数え方"]["欄"].items()},
    "時間.暦 の祝日": _祝日の扱い(),
}
状況の直の字 = {v for k, v in _状況().items() if k != v}
正本のfile = {"時間.暦 の祝日": Path("芯/計算/暦.py")}


def _docs(t: ast.AST) -> set[int]:
    out = set()
    for n in ast.walk(t):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            b = n.body[0]
            if isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) and isinstance(b.value.value, str):
                out.add(id(b.value))
    return out


def 写した所(src: str, 所: Path | None = None) -> list[tuple[int, str]]:
    t = ast.parse(src)
    docs = _docs(t)
    組たち = {k: v for k, v in 値の組.items() if not (k in 正本のfile and 正本のfile[k] == 所)}
    out = []
    for n in ast.walk(t):
        if isinstance(n, (ast.Tuple, ast.List, ast.Set)):
            字 = {e.value for e in n.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
            for k, v in 組たち.items():
                if len(字 & v) >= 2:
                    out.append((n.lineno, f"{k} の並び {sorted(字 & v)}"))
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            片 = {x.strip("^$()?:") for x in re.split(r"\|", n.value)} if "|" in n.value else set()
            for k, v in 組たち.items():
                if len({x for x in 片 if any(x.startswith(w) for w in v)}) >= 2:
                    out.append((n.lineno, f"{k} を | でつないだ字"))
            if n.value in 状況の直の字:
                out.append((n.lineno, f"状況 の字 {n.value!r}"))
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = n.args
            for arg, d in [*zip(a.args[len(a.args) - len(a.defaults):], a.defaults), *zip(a.kwonlyargs, a.kw_defaults)]:
                if arg.arg == "誰が聞いた" and isinstance(d, ast.Constant) and isinstance(d.value, str):
                    out.append((n.lineno, f"誰が聞いた の既定 {d.value!r}"))
    return out


def _道具たち():
    for p in sorted(根.rglob("*.py")):
        r = p.relative_to(根)
        if r.parts[0] in ("tests", ".git") or "__pycache__" in r.parts:
            continue
        yield r


def test_正本の組は読める():
    assert all(len(v) >= 2 for v in 値の組.values()), 値の組
    assert 状況の直の字


def test_道具は選べる値と既定を写さない():
    外れ = [f"{r}:{n}: {v}" for r in _道具たち() for n, v in 写した所((根 / r).read_text(encoding="utf-8"), r)]
    assert not 外れ, "選べる値・既定は正本（型.json・管理表/型.json・芯/設定の表.json・芯/計算/暦.py）から引く:\n" + "\n".join(外れ)


@pytest.mark.parametrize("悪い", [
    'x = re.compile(r"^(?:|無し|既定|法の線.*|知らせ.*|原本と連絡から読んだ)$")',
    'x = ("無し", "既定")',
    'x = {"反映済", "反映済み", "済"}',
    'x = ("未", "未反映")',
    'x = {"状況": "お答え待ち"}',
    'x = "お答えいただいた"',
    'x = ["お答え待ち", "差し替え"]',
    'def f(a, 誰が聞いた: str = "AI"):\n    pass',
    'def f(*, 誰が聞いた="AI"):\n    pass',
    'x = ("入れない", "入れる")',
    'x = ("週の法定で判定", "休日の率で払う", "時間外の率で払う")',
    'x = ("休み", "出勤")',
])
def test_注入_写した値は拒む(悪い):
    assert 写した所("import re\n" + 悪い + "\n")


@pytest.mark.parametrize("良い", [
    'x = 型の口.拠り所に直す("法の線（法の表）")',
    'x = "法の線（答えまで法の線で計算する）"',
    'x = _表.値の字("確認ページ", "状況", "待ち")',
    'def f(誰が聞いた: str | None = None):\n    pass',
    'def f():\n    """状況は お答え待ち・お答えいただいた・差し替え"""',
    'x = "差し替え"',
    'x = ("休み", 1)',
])
def test_引く所と説明の文は拒まない(良い):
    assert not 写した所(良い + "\n")


def test_正本の_file_の祝日は拒まない():
    assert not 写した所('祝日の扱い = ("休み", "出勤")\n', Path("芯/計算/暦.py"))
