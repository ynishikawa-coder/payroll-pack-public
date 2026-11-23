"""外の口の見張り: パックの file が、ほかの file の「_ で始まる名」（その file の中だけで使う名）を呼ばない。

なぜ在るか（根治・2026-11-23・台帳の束 K1）: 名の頭の _ は「この file の中だけで使う・黙って変えてよい」の印なのに、
ほかの file（パックの中の別の層・道具・plugin・パックの外の殻）がそれを呼んでいた。持ち主の file が名や形を変えると、
呼ぶ側が試験の外で黙って壊れる（約束の無い口に頼る）。ほかの file から使う物は _ の無い名（外の口）で出し、
_ の名は file の中だけで使う。数え方も同じ: 表の列の字（`chr(65 + …)`）は 芯/字.py の 列の字 だけが組む。

照らす事（試験の外＝ tests/ の中の呼び出しは見ない。試験は中を見てよい）:
- `from M import _x` で、M がパックの別の file で、_x がそこで定義した名。
- `何か._x` で、_x がパックの別の file の一番上で定義した名（関数・型・値）で、どの型の中の名でもない（物の _ の名は見ない）。
- `getattr(何か, "_x")`・`hasattr`・`setattr`・`delattr`・`operator.attrgetter`・`何か.__getattribute__` で、_x がパックの
  別の file の一番上の名。名の字は定数・同じ file の字の定数・`+` や f 字でつないだ字まで解いて照らす。解けない字で
  頭が `_` の時（`"_" + 名`・`f"_{名}"`）は、どの名か分からないので既定で赤。
- `vars(何か)`・`何か.__dict__` で、ほかの物の名の表を丸ごと読まない（どの名を読むか木で見えない＝既定で赤）。
- 芯/字.py の外の `chr(…)` は、中身が定数の字だけ（`chr(10)` など）。名を経由した数（`A = 65; chr(A + i)`）・
  引数・物の値で組む chr は列の字の写しになり得るので既定で赤。`string.ascii_uppercase`・"ABC…Z" の字も同じ。
"""
import ast
from pathlib import Path

import pytest

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
    字の定数 = {p: _字の定数(木) for p, 木 in 木たち.items()}
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
            elif isinstance(n, ast.Call) and (字 := _引く名の字(n)) is not None:
                呼び = ast.unparse(n.func)
                値たち = _字の値たち(字, 字の定数[p])
                if 値たち is None:
                    if _頭が私の字(字, 字の定数[p]):
                        out.append(f"{where}:{n.lineno}: {呼び}(…, {ast.unparse(字)}) は名を組んで私の名を引く")
                    continue
                for x in sorted(値たち):
                    if x in 持ち主 and x not in 物の名 and 持ち主[x] - {p}:
                        out.append(f"{where}:{n.lineno}: {呼び}(…, {x!r})")
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "vars" and n.args:
                out.append(f"{where}:{n.lineno}: vars(…) で名の表を丸ごと読む")
            elif isinstance(n, ast.Attribute) and n.attr == "__dict__":
                out.append(f"{where}:{n.lineno}: .__dict__ で名の表を丸ごと読む")
    return out


_名を字で引く = {"getattr", "hasattr", "setattr", "delattr"}


def _引く名の字(n: ast.Call) -> ast.AST | None:
    """名を字で渡して物の名を引く呼び出しなら、その名の字の式を返す。"""
    f = n.func
    if isinstance(f, ast.Name) and f.id in _名を字で引く and len(n.args) >= 2:
        return n.args[1]
    if isinstance(f, ast.Attribute) and f.attr == "__getattribute__" and n.args:
        return n.args[-1]
    if ((isinstance(f, ast.Name) and f.id == "attrgetter") or (isinstance(f, ast.Attribute) and f.attr == "attrgetter")) \
            and n.args:
        return ast.Tuple(elts=list(n.args), ctx=ast.Load())
    return None


def _字の定数(木: ast.Module) -> dict[str, list[ast.AST]]:
    """file の中で `名 = 式` と置いた名ごとの式（どの深さでも。同じ名に何度も置けば全部）。"""
    out: dict[str, list[ast.AST]] = {}
    for n in ast.walk(木):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out.setdefault(t.id, []).append(n.value)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None:
            out.setdefault(n.target.id, []).append(n.value)
    return out


def _字の値たち(n: ast.AST, 定数: dict, 深さ: int = 0) -> set[str] | None:
    """字の式が取り得る字の全部。解けない所が在れば None。"""
    if 深さ > 20:
        return None
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return {n.value}
    if isinstance(n, ast.Name) and n.id in 定数:
        out: set[str] = set()
        for v in 定数[n.id]:
            x = _字の値たち(v, 定数, 深さ + 1)
            if x is None:
                return None
            out |= x
        return out
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
        a, b = _字の値たち(n.left, 定数, 深さ + 1), _字の値たち(n.right, 定数, 深さ + 1)
        return None if a is None or b is None else {x + y for x in a for y in b}
    if isinstance(n, ast.JoinedStr):
        out = {""}
        for v in n.values:
            x = _字の値たち(v.value if isinstance(v, ast.FormattedValue) else v, 定数, 深さ + 1)
            if x is None:
                return None
            out = {a + b for a in out for b in x}
        return out
    if isinstance(n, ast.IfExp):
        a, b = _字の値たち(n.body, 定数, 深さ + 1), _字の値たち(n.orelse, 定数, 深さ + 1)
        return None if a is None or b is None else a | b
    if isinstance(n, (ast.Tuple, ast.List)):
        out = set()
        for e in n.elts:
            x = _字の値たち(e, 定数, 深さ + 1)
            if x is None:
                return None
            out |= x
        return out
    return None


def _頭が私の字(n: ast.AST, 定数: dict) -> bool:
    """解けない字の式でも、頭が `_` で始まると分かるか（"_" + 名・f"_{名}"・"_%s" % 名 など）。"""
    if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Mod)):
        頭 = _字の値たち(n.left, 定数)
        return bool(頭) and any(x.startswith("_") for x in 頭) if 頭 is not None else _頭が私の字(n.left, 定数)
    if isinstance(n, ast.JoinedStr) and n.values:
        v = n.values[0]
        if isinstance(v, ast.Constant):
            return str(v.value).startswith("_")
        return _頭が私の字(v.value, 定数)
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("format", "join"):
        頭 = _字の値たち(n.func.value, 定数)
        return n.func.attr == "format" and 頭 is not None and any(x.startswith("_") for x in 頭)
    if isinstance(n, (ast.Tuple, ast.List)):
        return any(_頭が私の字(e, 定数) for e in n.elts)
    if isinstance(n, ast.Name) and n.id in 定数:
        return any(_頭が私の字(v, 定数) for v in 定数[n.id])
    return False


def _定数の式か(n: ast.AST) -> bool:
    """名・呼び出し・物の値を含まない、字の上で値が決まる式か（chr(10)・chr(0x30FB)・chr(0x30 + 1)）。"""
    return all(isinstance(x, (ast.Constant, ast.BinOp, ast.UnaryOp, ast.operator, ast.unaryop, ast.expr_context))
               for x in ast.walk(n))


def _列の字を組むか(n: ast.AST) -> bool:
    """chr(…) の中身が列の字（A の字の番号 64・65 からの足し引き）になり得るか。定数の式なら値で決め、
    名・引数・物の値を通る式は、どの数か木で決まらないので既定で「なり得る」とする。"""
    if not _定数の式か(n):
        return True
    for x in ast.walk(n):
        if isinstance(x, ast.BinOp) and isinstance(x.op, (ast.Add, ast.Sub)):
            for y in (x.left, x.right):
                if isinstance(y, ast.Constant) and y.value in (64, 65):
                    return True
    return False


_ABC = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def 列の字の写し(根: Path) -> list[str]:
    正本 = 根 / "芯" / "字.py"
    out = []
    for p in _fileたち(根):
        if p == 正本:
            continue
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"), filename=str(p))):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "chr" and n.args
                    and _列の字を組むか(n.args[0])):
                out.append(f"{p.relative_to(根).as_posix()}:{n.lineno}")
            elif (isinstance(n, ast.Attribute) and n.attr in ("ascii_uppercase", "ascii_letters")) or (
                    isinstance(n, ast.Constant) and isinstance(n.value, str) and _ABC in n.value.upper()):
                out.append(f"{p.relative_to(根).as_posix()}:{n.lineno}")
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


@pytest.mark.parametrize("字", [
    "s = chr(64 + n)\n",
    "s = chr( 65+ r )\n",
    "s = chr(ord('A') + r)\n",
    "s = chr((r % 26) + 65)\n",
    "s = chr(\n    65 + r)\n",
])
def test_注入_列の字の写しは書き方を変えても拒む(tmp_path, 字):
    根2 = _小さな根(tmp_path, {"芯/字.py": "chr(65 + 0)\n", "出口/x.py": 字})
    assert 列の字の写し(根2) == ["出口/x.py:1"]


def test_定数の字のchrは拒まない(tmp_path):
    根2 = _小さな根(tmp_path, {"芯/字.py": "", "出口/x.py": "a = chr(10)\nb = chr(0x30FB)\nc = chr(0x30 + 1)\n"})
    assert 列の字の写し(根2) == []


@pytest.mark.parametrize("字", [
    "A = 65\ns = chr(A + i)\n",
    "A = ord('A')\ns = chr(A + i)\n",
    "def f(i, A=65):\n    return chr(A + i)\n",
    "class 表:\n    A = 65\ns = chr(表.A + i)\n",
    "s = chr(n + 1)\n",
    "import string\ns = string.ascii_uppercase[i]\n",
    "s = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[i]\n",
])
def test_注入_名を経由した列の字も拒む(tmp_path, 字):
    根2 = _小さな根(tmp_path, {"芯/字.py": "chr(65 + 0)\n", "出口/x.py": 字})
    assert 列の字の写し(根2), 字


@pytest.mark.parametrize("呼び", ["getattr(a, '_形', None)", "hasattr(a, '_形')", "setattr(a, '_形', 2)"])
def test_注入_ほかのfileの私の名を字で引くと拒む(tmp_path, 呼び):
    根2 = _小さな根(tmp_path, {"甲/a.py": "_形 = 1\n", "乙/b.py": f"import 甲.a as a\nx = {呼び}\n"})
    assert 外から呼ぶ私の名(根2) == [f"乙/b.py:2: {呼び.split('(')[0]}(…, '_形')"]


def test_自分のfileの私の名と物の名を字で引くのは拒まない(tmp_path):
    根2 = _小さな根(tmp_path, {
        "甲/a.py": "class 人:\n    def _仮(self):\n        return 1\n",
        "乙/b.py": "_自分 = 1\nimport sys\nx = getattr(sys.modules[__name__], '_自分')\ny = getattr(人(), '_仮')\n",
    })
    assert 外から呼ぶ私の名(根2) == []


@pytest.mark.parametrize("呼び", [
    "getattr(a, '_' + '形')",
    "getattr(a, 頭 + '形')",
    "getattr(a, f'_{名}')",
    "getattr(a, '_' + 名)",
    "getattr(a, '_%s' % 名)",
    "getattr(a, '_{}'.format(名))",
    "getattr(a, 名2)",
    "a.__getattribute__('_形')",
    "operator.attrgetter('_形')(a)",
    "vars(a)['_形']",
    "vars(a).get('_形')",
    "a.__dict__['_形']",
    "a.__dict__.get('_' + 名)",
])
def test_注入_私の名を字を組んで引くか名の表から読むと拒む(tmp_path, 呼び):
    根2 = _小さな根(tmp_path, {
        "甲/a.py": "_形 = 1\n",
        "乙/b.py": f"import operator\nimport 甲.a as a\n頭 = '_'\n名 = '形'\n名2 = '_' + 名\nx = {呼び}\n",
    })
    assert 外から呼ぶ私の名(根2), 呼び


def test_字を組んでも外の口の名なら拒まない(tmp_path):
    根2 = _小さな根(tmp_path, {
        "甲/a.py": "形 = 1\n",
        "乙/b.py": "import 甲.a as a\n名 = '形'\nx = getattr(a, '' + 名)\ny = getattr(a, f'{名}')\nz = getattr(a, k)\n",
    })
    assert 外から呼ぶ私の名(根2) == []
