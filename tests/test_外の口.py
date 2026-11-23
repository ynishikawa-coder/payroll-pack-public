"""外の口の見張り: パックの file が、ほかの file の「_ で始まる名」（その file の中だけで使う名）を呼ばない。

なぜ在るか（根治・2026-11-23・台帳の束 K1）: 名の頭の _ は「この file の中だけで使う・黙って変えてよい」の印なのに、
ほかの file（パックの中の別の層・道具・plugin・パックの外の殻）がそれを呼んでいた。持ち主の file が名や形を変えると、
呼ぶ側が試験の外で黙って壊れる（約束の無い口に頼る）。ほかの file から使う物は _ の無い名（外の口）で出し、
_ の名は file の中だけで使う。数え方も同じ: 表の列の字（`chr(65 + …)`）は 芯/字.py の 列の字 だけが組む。

照らす事（試験の外＝ tests/ の中の呼び出しは見ない。試験は中を見てよい）:
- `from M import _x` で、M がパックの別の file で、_x がそこで定義した名。
- `何か._x` で、_x がパックの別の file の一番上で定義した名（関数・型・値）で、どの型の中の名でもない（物の _ の名は見ない）。
- `chr(65` を 芯/字.py の外で書かない（列の字を組む写しを作らない）。
"""
import ast
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
_見ない = {"tests", "__pycache__", ".git"}


def _fileたち(根: Path) -> list[Path]:
    return [p for p in sorted(根.rglob("*.py")) if not (_見ない & set(p.relative_to(根).parts))]


def _私の名(木: ast.Module) -> set[str]:
    """file の一番上で定義した _ の名（dunder は除く）。"""
    out = set()
    for n in 木.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.Assign):
            out |= {t.id for t in n.targets if isinstance(t, ast.Name)}
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            out.add(n.target.id)
    return {x for x in out if x.startswith("_") and not x.startswith("__")}


def _型の中の名(木: ast.Module) -> set[str]:
    out = set()
    for c in ast.walk(木):
        if isinstance(c, ast.ClassDef):
            for n in ast.walk(c):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.add(n.name)
                elif isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store):
                    out.add(n.attr)
                elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                    out.add(n.id)
                elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                    out.add(n.target.id)
    return out


def 外から呼ぶ私の名(根: Path) -> list[str]:
    """ほかの file の _ の名を呼ぶ所を `path:行: 名` で返す。"""
    木たち = {p: ast.parse(p.read_text(encoding="utf-8"), filename=str(p)) for p in _fileたち(根)}
    持ち主: dict[str, set[Path]] = {}
    for p, 木 in 木たち.items():
        for x in _私の名(木):
            持ち主.setdefault(x, set()).add(p)
    物の名 = set().union(*(_型の中の名(木) for 木 in 木たち.values()))
    out = []
    for p, 木 in 木たち.items():
        where = p.relative_to(根).as_posix()
        for n in ast.walk(木):
            if isinstance(n, ast.ImportFrom) and n.module:
                for a in n.names:
                    if a.name in 持ち主 and 持ち主[a.name] - {p}:
                        out.append(f"{where}:{n.lineno}: from {n.module} import {a.name}")
            elif isinstance(n, ast.Attribute) and n.attr in 持ち主 and n.attr not in 物の名:
                if 持ち主[n.attr] - {p}:
                    out.append(f"{where}:{n.lineno}: .{n.attr}")
    return out


def 列の字の写し(根: Path) -> list[str]:
    正本 = 根 / "芯" / "字.py"
    out = []
    for p in _fileたち(根):
        if p == 正本:
            continue
        for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "chr(65" in l.replace(" ", ""):
                out.append(f"{p.relative_to(根).as_posix()}:{i}")
    return out


def test_ほかのfileの私の名を呼ばない():
    assert 外から呼ぶ私の名(根) == []


def test_列の字は正本の1か所だけが組む():
    assert 列の字の写し(根) == []


def test_芯の列の字():
    import sys
    sys.path.insert(0, str(根))
    from 芯.字 import 列の字
    assert [列の字(n) for n in (0, 1, 26, 27, 52, 53, 702, 703)] == ["A", "A", "Z", "AA", "AZ", "BA", "ZZ", "AAA"]


# ---- 注入の試験: 誤りの類をわざと入れると、見張りが拒む

def _小さな根(tmp_path: Path, files: dict[str, str]) -> Path:
    for 名, 中 in files.items():
        q = tmp_path / 名
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(中, encoding="utf-8")
    return tmp_path


def test_注入_ほかのfileの私の名をfromで読むと拒む(tmp_path):
    根2 = _小さな根(tmp_path, {"甲/a.py": "def _中():\n    return 1\n", "乙/b.py": "from 甲.a import _中\n"})
    assert 外から呼ぶ私の名(根2) == ["乙/b.py:1: from 甲.a import _中"]


def test_注入_ほかのfileの私の名を点で呼ぶと拒む(tmp_path):
    根2 = _小さな根(tmp_path, {"甲/a.py": "_形 = 1\n", "乙/b.py": "import 甲.a as a\nx = a._形\n"})
    assert 外から呼ぶ私の名(根2) == ["乙/b.py:2: ._形"]


def test_注入_物の私の名と自分の名は拒まない(tmp_path):
    根2 = _小さな根(tmp_path, {
        "甲/a.py": "def _仮():\n    pass\nclass 人:\n    def _仮(self):\n        return 1\n",
        "乙/b.py": "def _自分():\n    pass\nx = _自分\ny = 人()._仮()\n",
    })
    assert 外から呼ぶ私の名(根2) == []


def test_注入_列の字の写しを書くと拒む(tmp_path):
    根2 = _小さな根(tmp_path, {"芯/字.py": "chr(65 + 0)\n", "出口/x.py": "s = chr(65 + r)\n"})
    assert 列の字の写し(根2) == ["出口/x.py:1"]
