"""tests/conftest.py（許しの表に無い飛ばしを赤に替える）の注入の試験。

作り物の tests の dir に conftest.py を写し、飛ばしの形ごとに pytest を別の process で回して、
許しの表に無い物は落ちた試験か集める時の誤りになり（終わりの値 1 か 2）、表に在る物だけが飛ばしのまま（終わりの値 0）かを見る。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import conftest as 飛ばしの許し

_conftest = Path(__file__).with_name("conftest.py")


# 「…\\n」の直後に「@」を続けて書くと公開の検査がメールの形と読む＝字を「" "」で分けて置く
def _回す(tmp_path: Path, 名: str, 字: str) -> subprocess.CompletedProcess:
    shutil.copy(_conftest, tmp_path / "conftest.py")
    (tmp_path / 名).write_text(字, encoding="utf-8")
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-rfEs", "-p", "no:cacheprovider", 名],
                          cwd=tmp_path, capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("字", [
    "import pytest\ndef test_a():\n    pytest.skip('まだ無い')\n",                                   # 本文の skip
    "import pytest\n" "@pytest.mark.skip(reason='後で')\ndef test_a():\n    pass\n",                      # 飾り
    "import pytest\n" "@pytest.mark.skipif(True, reason='版が違う')\ndef test_a():\n    pass\n",          # 版の条件
    "import pytest\npytest.importorskip('無い_部品_xyz')\ndef test_a():\n    pass\n",                  # file の頭
    "import pytest\npytest.skip('まだ', allow_module_level=True)\ndef test_a():\n    pass\n",          # file の頭
    "import pytest\n" "@pytest.fixture\ndef 物():\n    pytest.skip('道具が無い')\ndef test_a(物):\n    pass\n",  # fixture
    "import pytest\ndef _手伝い():\n    pytest.skip('無い')\ndef test_a():\n    _手伝い()\n",            # 手伝いの関数
])
def test_注入_許しの表に無い飛ばしは赤(tmp_path, 字):
    r = _回す(tmp_path, "test_作り物.py", 字)
    assert r.returncode in (1, 2), r.stdout + r.stderr  # 1＝落ちた試験・2＝集める時の誤り（file の頭の飛ばし）
    assert "許しの表に無い飛ばし" in r.stdout, r.stdout


def test_許しの表に在る飛ばしは飛ばしのまま(tmp_path):
    r = _回す(tmp_path, "test_前の置き場の名の見張り.py", "import pytest\ndef test_a():\n    pytest.skip('git が無い（作り物）')\n")
    assert r.returncode == 0 and "1 skipped" in r.stdout, r.stdout + r.stderr


def test_許しの表の訳の頭が違えば赤(tmp_path):
    r = _回す(tmp_path, "test_前の置き場の名の見張り.py", "import pytest\ndef test_a():\n    pytest.skip('別の訳')\n")
    assert r.returncode == 1 and "許しの表に無い飛ばし" in r.stdout, r.stdout


def test_xfailは扱わない(tmp_path):
    r = _回す(tmp_path, "test_作り物.py", "import pytest\n" "@pytest.mark.xfail(reason='既知')\ndef test_a():\n    assert 0\n")
    assert r.returncode == 0 and "1 xfailed" in r.stdout, r.stdout


def test_許しの表の行はどれも在る試験のfileを指す():
    根 = Path(__file__).resolve().parent
    無い = [f for f, _, _ in 飛ばしの許し.許す飛ばし if not (根 / f).is_file()]
    assert 無い == [], 無い
    assert all(頭.strip() and なぜ.strip() for _, 頭, なぜ in 飛ばしの許し.許す飛ばし)


# ── 走らない道の飛ばしも表に照らす ──
# CI は履歴を全部取るので、浅い clone の時だけ通る飛ばしは CI では一度も出ず、上の hook（走った時にだけ照らす）では
# 表に無いまま main へ入れた（test_骨.py の「git の履歴か origin/main が手元に無い」）。走らせずに、書いてある飛ばしの
# 訳の頭を構文の木から読み、表に照らす。訳の頭が字で読めない飛ばし（式だけの訳・importorskip）も赤＝読めない物を許さない。
import ast  # noqa: E402

_飛ばしの名 = {"skip", "skipif", "importorskip"}


def _字の値(節, 字の表: dict[str, str]) -> str | None:
    """訳の式の、頭から読める字。読めなければ None。f 字は頭から字・字の定数が続く所まで。"""
    if isinstance(節, ast.Constant) and isinstance(節.value, str):
        return 節.value
    if isinstance(節, ast.Name):
        return 字の表.get(節.id)
    if isinstance(節, ast.Attribute) and isinstance(節.value, ast.Name):
        return 字の表.get(f"{節.value.id}.{節.attr}")
    if isinstance(節, ast.JoinedStr):
        頭 = ""
        for v in 節.values:
            x = _字の値(v.value if isinstance(v, ast.FormattedValue) else v, 字の表)
            if x is None:
                break
            頭 += x
        return 頭 or None
    return None


def _字の定数(木: ast.Module) -> dict[str, str]:
    return {t.id: n.value.value for n in 木.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
            and isinstance(n.value.value, str) for t in n.targets if isinstance(t, ast.Name)}


def 書いてある飛ばし(根: Path) -> list[tuple[str, int, str | None]]:
    """根の下の試験の file の (根からの path, 行, 訳の頭 か None)。conftest.py とこの file は見ない（作り物の飛ばしを持つ）。"""
    out = []
    for f in sorted(根.rglob("*.py")):
        if f.name in ("conftest.py", Path(__file__).name) or "__pycache__" in f.parts:
            continue
        木 = ast.parse(f.read_text(encoding="utf-8"))
        字の表 = _字の定数(木)
        for 隣 in f.parent.glob("*.py"):   # 隣の file の字の定数（qa_htmlの検査.無い訳 の形）
            if 隣 != f:
                字の表.update({f"{隣.stem}.{k}": v for k, v in _字の定数(ast.parse(隣.read_text(encoding="utf-8"))).items()})
        for 節 in ast.walk(木):
            if not (isinstance(節, ast.Call) and isinstance(節.func, ast.Attribute) and 節.func.attr in _飛ばしの名):
                continue
            if 節.func.attr == "importorskip":
                訳 = None
            else:
                式 = next((k.value for k in 節.keywords if k.arg in ("reason", "msg")), None)
                if 式 is None and 節.func.attr == "skip" and 節.args:
                    式 = 節.args[0]
                訳 = _字の値(式, 字の表) if 式 is not None else None
            out.append((f.relative_to(根).as_posix(), 節.lineno, 訳))
    return out


def 表に無い飛ばし(根: Path) -> list[tuple[str, int, str | None]]:
    return [(f, 行, 訳) for f, 行, 訳 in 書いてある飛ばし(根) if 訳 is None or not 飛ばしの許し.許すか(f, 訳)]


def test_書いてある飛ばしはどれも許しの表に在る():
    assert 表に無い飛ばし(Path(__file__).resolve().parent) == []


@pytest.mark.parametrize("字", [
    "import pytest\ndef test_a():\n    pytest.skip('git の履歴か origin/main が手元に無い')\n",          # 走らない道の字の訳
    "import pytest\n頭 = '無い: '\ndef _無い(x):\n    pytest.skip(f'{頭}{x}')\n",                        # 定数の頭の f 字
    "import pytest\ndef _無い(x):\n    pytest.skip(x)\n",                                               # 訳が式だけ＝読めない
    "import pytest\npytest.importorskip('無い_部品_xyz')\n",                                            # importorskip
    "import pytest\n" "@pytest.mark.skipif(False)\ndef test_a():\n    pass\n",                          # 訳の無い skipif
])
def test_注入_走らない道の表に無い飛ばしは赤(tmp_path, 字):
    (tmp_path / "test_骨.py").write_text(字, encoding="utf-8")
    assert len(表に無い飛ばし(tmp_path)) == 1


def test_注入_表に在る頭の飛ばしは通す(tmp_path):
    (tmp_path / "test_骨.py").write_text(
        "import pytest\n頭 = 'git の履歴・印が手元に無い: '\ndef _無い(x):\n    pytest.skip(f'{頭}{x}（浅い clone）')\n",
        encoding="utf-8")
    assert 表に無い飛ばし(tmp_path) == []
