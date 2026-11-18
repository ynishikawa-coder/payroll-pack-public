"""検査の入口の最初の段（scripts/check_python_version.py）: CI と同じ版の Python の文法で読めない .py を赤にする。

PR #201 で、名に U+30FB を持つ試験の関数が手元の Python 3.13 では通り、CI の 3.12 で SyntaxError になった。
ast.parse(feature_version=…) では捕まらない（名に使える字は Unicode の版で決まる）＝CI の版の python そのもので照らす。
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[1]
道具 = 根 / "scripts" / "check_python_version.py"
_spec = importlib.util.spec_from_file_location("check_python_version", 道具)
照らし = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(照らし)
# 期待の版も正本（ci.yml）から取る＝CI の版を上げる時に試験を直す 2 か所目を作らない
CIの版 = 照らし.CIの版((根 / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))


def _回す(*file: Path) -> tuple[int, list[str]]:
    p = subprocess.run([sys.executable, str(道具), *map(str, file)], capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout.splitlines()


@pytest.mark.skipif(tuple(map(int, CIの版.split("."))) >= (3, 13),
                    reason="CI の版が 3.13 以上（Unicode 15.1）なら U+30FB は名に使える字＝この作り物は赤にならない")
def test_名に中黒を持つ関数はCIの版で読めないと赤(tmp_path):
    f = tmp_path / "test_作り物の名.py"
    f.write_text(f"def test_あ{chr(0x30FB)}い():\n    pass\n", encoding="utf-8")   # 3.13 では通り 3.12 では SyntaxError
    rc, 行 = _回す(f)
    assert rc == 1, 行
    assert any(l.startswith(f"読めない: {f}:1: ") and "U+30FB" in l for l in 行), 行
    assert 行[-1].startswith(f"赤: CI の Python {CIの版} の文法で読めない .py が 1 個在る")


def test_読める物は通りCIの版のpythonを出す(tmp_path):
    f = tmp_path / "test_作り物の名.py"
    f.write_text("def test_あい():\n    pass\n", encoding="utf-8")
    rc, 行 = _回す(f)
    assert rc == 0, 行
    assert 行[0].startswith("PYTHON=") and 行[-1].startswith(f"Python の版の照らし: CI の Python {CIの版} の文法で .py 1 個が読めた")


@pytest.mark.parametrize("字, 版", [
    ('      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.12"\n', "3.12"),
    ("          python-version: '3.13'\n", "3.13"),
    ("          python-version: 3.11\n", "3.11"),
])
def test_版を定義の字から読む(字, 版):
    assert 照らし.CIの版(字) == 版


@pytest.mark.parametrize("字", [
    "steps:\n  - run: x\n",                                                             # 無い
    '  python-version: "3.x"\n',                                                       # 読めない
    '  python-version: "3.12"\n  python-version: "3.13"\n',                            # 1 つに決まらない
    "  python-version: [\"3.12\", \"3.13\"]\n",                                       # 並び
])
def test_版が決まらなければ止める(字):
    with pytest.raises(ValueError):
        照らし.CIの版(字)
