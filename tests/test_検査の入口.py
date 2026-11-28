"""検査の入口（scripts/check_all.sh）: 落ちた時に、落ちた試験の名が出力の終わりに残る・公開の検査に当たる字は赤。

作り物の試験を tmp に置いて入口に渡す（tests/ の全部は回さない）。
"""
import os
import subprocess
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[1]
# 入口の中から入口を呼ばない（入口が引数を読まず tests/ の全部を回す形に戻っても、ここで止まって赤で終わる）
pytestmark = pytest.mark.skipif(os.environ.get("PAYROLL_CHECK_ALL_NESTED") == "1", reason="入口の中の入口")


def _回す(*試験: Path) -> tuple[int, list[str]]:
    p = subprocess.run(["bash", str(根 / "scripts" / "check_all.sh"), *map(str, 試験)], capture_output=True, text=True, timeout=300,
                       env={**os.environ, "PAYROLL_CHECK_ALL_NESTED": "1"})
    return p.returncode, p.stdout.splitlines()


def test_落ちた試験の名と環境が最後の行の手前に出る(tmp_path):
    f = tmp_path / "test_作り物の入口.py"
    # 「…\\n」の直後に「@」を続けて書くと公開の検査がメールの形と読む＝字を分けて置く（check_all.sh の公開の検査の段が見る）
    f.write_text("\n\n\n".join(["import pytest", '@pytest.mark.parametrize("名", ["作り物"])\ndef test_わざと落ちる(名):\n'
                                   '    assert 名 == "違う"', "def test_通る():\n    pass\n"]), encoding="utf-8")
    rc, 行 = _回す(f)
    assert rc == 1
    assert 行[-1].startswith("赤: ")
    名 = [l for l in 行 if l.startswith("落ちた試験: ")]
    assert len(名) == 1 and "test_わざと落ちる" in 名[0], 名
    記録 = next(l for l in 行 if l.startswith("出力の全部: ")).split(": ", 1)[1]
    assert "test_わざと落ちる" in Path(記録).read_text(encoding="utf-8")
    Path(記録).unlink()


def test_通れば最後の行は緑で名も環境も出さない(tmp_path):
    f = tmp_path / "test_作り物の入口.py"
    f.write_text("def test_通る():\n    pass\n", encoding="utf-8")
    rc, 行 = _回す(f)
    assert rc == 0 and 行[-1] == "緑: 全部の検査が通った"
    assert not [l for l in 行 if l.startswith("落ちた試験: ")]


def test_試験の前に止まっても赤(tmp_path):
    f = tmp_path / "test_作り物の入口.py"
    f.write_text("import 作り物の無い部品\n", encoding="utf-8")
    rc, 行 = _回す(f)
    assert rc != 0 and 行[-1].startswith("赤: ")


# ---- 公開の検査の段（土台の public-guard を repo の中身の全部に当てる）----
# 公開の写しへ版を運ぶ時に当たる字（例 メールの形）を、手元と CI の入口で赤にする。作り物の小さな repo を tmp に作り、
# 入口の写しをその中で回す（本物の repo に当たる字を置かない）。当たる字そのものも字を分けて組む（この file が当たらない）。
_入口の部品 = ("scripts/check_all.sh", ".github/workflows/土台の版.json")


def _作り物のrepo(tmp_path: Path, 中身: str) -> Path:
    r = tmp_path / "repo"
    for 名 in _入口の部品:
        (r / 名).parent.mkdir(parents=True, exist_ok=True)
        (r / 名).write_bytes((根 / 名).read_bytes())
    (r / "tests").mkdir()
    (r / "tests" / "test_作り物.py").write_text("def test_通る():\n    pass\n", encoding="utf-8")
    (r / "作り物.md").write_text(中身, encoding="utf-8")
    for a in (["init", "-q"], ["add", "-A"]):
        subprocess.run(["git", *a], cwd=r, check=True, capture_output=True)
    return r


def _入口を回す(r: Path) -> tuple[int, list[str]]:
    env = {k: v for k, v in os.environ.items() if k not in ("AF_DENY_BUNDLE", "AF_DENY_WORDS", "AF_DENY_WORDS_FILE")}
    p = subprocess.run(["bash", str(r / "scripts" / "check_all.sh")], capture_output=True, text=True, timeout=300,
                       cwd=r, env={**env, "PAYROLL_CHECK_ALL_NESTED": "1"})
    return p.returncode, p.stdout.splitlines()


def test_公開の検査に当たらなければ通る(tmp_path):
    rc, 行 = _入口を回す(_作り物のrepo(tmp_path, "作り物の文\n"))
    assert rc == 0 and 行[-1] == "緑: 全部の検査が通った", 行[-6:]
    assert any(l.startswith("公開の検査（土台 v") for l in 行)


@pytest.mark.parametrize("字", [
    "import pytest\\n\\n\\n" + "@pytest.mark.parametrize",   # v0.25 から公開の写しへの運びを止めた形（\n の n がメールの頭に読まれる）
    "連絡は taro" + "@" + "kaisha.co.jp へ",                   # 本物のメールの形
])
def test_公開の検査に当たる字を置くと赤(tmp_path, 字):
    rc, 行 = _入口を回す(_作り物のrepo(tmp_path, 字 + "\n"))
    assert rc == 1 and 行[-1].startswith("赤: 公開の検査が通らない"), 行[-6:]
    assert any("作り物.md: メールアドレス" in l for l in 行)
    assert not any(l.startswith("緑: ") for l in 行)
