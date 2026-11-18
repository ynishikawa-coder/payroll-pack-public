"""芯の約束の見張り: 芯/ は 入口・出口・初期設定・月次・道具・有給・確認ページ・管理表 など芯の外を import しない。

芯の .py を全部 構文木で読み、import が「Python の標準の道具」か「芯の中」だけかを照らす（許す物を数える形＝外の dir が
増えても漏れない）。照らす import は 4 つ:
- `import X` / `from X import …`（絶対）
- `from . import …` / `from ..x import …`（相対。file の置き場から辿って芯の外へ出たら赤）
- `importlib.import_module("X")` / `__import__("X")`（字で渡す import。字でない物を渡すと照らせない＝赤）
芯の中から法の表などの data を Path で読むのは import でないので、ここでは見ない。
"""
import ast
import sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
芯の名 = "芯"
_標準 = set(sys.stdlib_module_names) | {"__future__"}


def _相対を解く(p: Path, 根: Path, level: int, mod: str | None) -> str:
    包 = list(p.relative_to(根).with_suffix("").parts)[:-1]   # file の入っている包（芯/計算/x.py → 芯.計算）
    if level - 1 > len(包):
        return "<根より上>"
    基 = 包[: len(包) - (level - 1)]
    return ".".join(基 + ([mod] if mod else [])) or "<根>"


def _許す(名: str) -> bool:
    頭 = 名.split(".")[0]
    return 頭 == 芯の名 or 頭 in _標準


def 外へのimport(根: Path) -> list[str]:
    """芯/ の .py から芯の外（標準の道具でも芯でもない物）への import を `path:行: 名` で返す。"""
    out = []
    for p in sorted((根 / 芯の名).rglob("*.py")):
        木 = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        where = p.relative_to(根).as_posix()
        for n in ast.walk(木):
            名s: list[str] = []
            if isinstance(n, ast.Import):
                名s = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                名s = [_相対を解く(p, 根, n.level, n.module) if n.level else (n.module or "")]
            elif isinstance(n, ast.Call):
                f = n.func
                呼び名 = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
                if 呼び名 in ("import_module", "__import__"):
                    a = n.args[0] if n.args else None
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        名s = [a.value if not a.value.startswith(".") else "<相対の字>"]
                    else:
                        名s = ["<字でない import の名＝照らせない>"]
            out += [f"{where}:{n.lineno}: {x}" for x in 名s if not _許す(x)]
    return out


def test_芯は外をimportしない():
    assert 外へのimport(根) == []


def test_芯の中のimportを数えている():
    # 照らしが空回りしていない（芯の中どうしの import を実際に読んでいる）
    assert any(p.read_text(encoding="utf-8").find("from 芯.") >= 0 for p in (根 / 芯の名).rglob("*.py"))


def test_外へのimportを見つける(tmp_path):
    # 注入の試験: わざと外を import する作り物の芯を置くと、4 つの形とも赤になる
    d = tmp_path / 芯の名 / "計算"
    d.mkdir(parents=True)
    (tmp_path / 芯の名 / "__init__.py").write_text("", encoding="utf-8")
    (d / "良い.py").write_text("import json\nfrom decimal import Decimal\nfrom 芯.計算 import 形\nfrom . import 形\n", encoding="utf-8")
    (d / "悪い.py").write_text(
        "import 入口.勤怠\n"
        "from 出口 import 明細\n"
        "from ...道具 import 答え合わせ\n"
        "import importlib\n"
        "m = importlib.import_module('確認ページ.確認ページ')\n"
        "n = __import__('管理表')\n"
        "名 = '有給'\n"
        "o = importlib.import_module(名)\n"
        "def f():\n    import 月次\n",
        encoding="utf-8")
    assert 外へのimport(tmp_path) == [
        "芯/計算/悪い.py:1: 入口.勤怠",
        "芯/計算/悪い.py:2: 出口",
        "芯/計算/悪い.py:3: 道具",
        "芯/計算/悪い.py:5: 確認ページ.確認ページ",
        "芯/計算/悪い.py:6: 管理表",
        "芯/計算/悪い.py:8: <字でない import の名＝照らせない>",
        "芯/計算/悪い.py:10: 月次",
    ]
