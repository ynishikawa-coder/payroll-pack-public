"""plugin payroll-agent の文（docstring・md）が「<path>.py の `<名>`」で指すパックの部品の名が、その file の上の段に在るかの試験。

防ぐ故障: 部品の名を変えた・消したのに、それを正本として指す文が古い名のまま残る（読む窓が無い名を探す）。
保証しない事: path を書かない指し方（`部品.名` の形は口の約束の道具が口の一覧について照らす）。
"""
import ast
import re

from 手伝い import PLUGIN, 根

指し方 = re.compile(r"`?([\w/ぁ-んァ-ヶ一-龥ー]+\.py)`?\s*の\s*`([^`\s(.]+)")


def _上の名(f):
    out = set()
    for n in ast.parse(f.read_text(encoding="utf-8")).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                out |= {x.id for x in ast.walk(t) if isinstance(x, ast.Name)}
    return out


def 死んだ名(text):
    外れ = []
    for m in 指し方.finditer(text):
        f = next((d / m.group(1) for d in (根, PLUGIN, PLUGIN / "bin") if (d / m.group(1)).is_file()), None)
        if f is not None and m.group(2) not in _上の名(f):
            外れ.append(f"{m.group(1)} に {m.group(2)} が無い")
    return 外れ


def test_plugin_の文が指す名は全部在る():
    files = sorted(p for p in PLUGIN.rglob("*") if p.suffix in (".py", ".md") and "__pycache__" not in p.parts)
    外れ = [f"{p.relative_to(根)}: {x}" for p in files for x in 死んだ名(p.read_text(encoding="utf-8"))]
    assert 外れ == []


def test_注入_消した名を指す文は赤():
    assert 死んだ名("正本: 初期設定/型の口.py の `作り物の消えた名`・") == ["初期設定/型の口.py に 作り物の消えた名 が無い"]
    assert 死んだ名("正本: 初期設定/型の口.py の `問いの番号の形`・") == []
