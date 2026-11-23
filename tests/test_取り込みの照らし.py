"""取り込みの照らし（scripts/取り込みの照らし.py）の試験。

守る物: 枝へ main を取り込む commit が、片側の行を黙って落とさない（原因の台帳 420a40dc…81e9a178・積んだ枝が base の
古い先端で main の 1 行を落とし、試験は緑のままだった）。
ここは作り物の git の repo を手元に起こし、その故障をそのまま再現して赤（終わりの値 1）を見る（注入）。
わざと捨てた印・別の file へ動かした行・ぶつからない取り込みは緑。道具が働けない・壊れた時は 2。
最後に本物の repo の origin/main..HEAD を回す（CI は fetch-depth: 0 で origin/main を持つ＝無ければ赤・手元は skip）。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[1]
道具 = 根 / "scripts" / "取り込みの照らし.py"
_名 = {"GIT_AUTHOR_NAME": "作り物", "GIT_AUTHOR_EMAIL": "tsukurimono@example.invalid",
      "GIT_COMMITTER_NAME": "作り物", "GIT_COMMITTER_EMAIL": "tsukurimono@example.invalid"}


def _git(d: Path, *a: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=dict(os.environ, **_名))
    if check and r.returncode != 0:
        raise AssertionError(f"git {a}: {r.stderr}")
    return r.stdout


def _書く(d: Path, 名: str, 行: list[str] | bytes) -> None:
    p = d / 名
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(行, bytes):
        p.write_bytes(行)
    else:
        p.write_text("\n".join(行) + "\n", encoding="utf-8")
    _git(d, "add", 名)


def _commit(d: Path, 文: str) -> None:
    _git(d, "commit", "-q", "-m", 文)


def _回す(d: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(道具), *argv], cwd=d, capture_output=True, text=True, timeout=120)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    d = tmp_path / "r"
    d.mkdir()
    _git(d, "init", "-q", "-b", "main")
    _書く(d, "法の表.md", ["# 法の表", "行 1", "行 2"])
    _commit(d, "始め")
    return d


def _積んだ枝の事故(d: Path, 取り込みの文: str = "main を取り込む") -> None:
    """積んだ枝（stack）が base の古い先端を持ったまま、base を squash で入れた main を取り込み、ぶつかった file を枝の側で取る。"""
    _git(d, "checkout", "-q", "-b", "base")
    _書く(d, "法の表.md", ["# 法の表", "行 1", "base の行", "行 2"])
    _commit(d, "base の直し")
    _git(d, "checkout", "-q", "-b", "stack")            # base の古い先端から積む
    _書く(d, "積んだ物.md", ["積んだ枝の直し"])
    _commit(d, "積んだ枝の直し")
    _git(d, "checkout", "-q", "main")                   # main に別の PR の 1 行が入る（#297 の 法の表.md の行の役）
    _書く(d, "法の表.md", ["# 法の表", "行 1", "行 2", "main に入った大事な行"])
    _commit(d, "別の PR")
    _git(d, "checkout", "-q", "base")                   # base が main を取り込み、その後 squash で main へ
    _git(d, "merge", "-q", "--no-edit", "main")
    _git(d, "checkout", "-q", "main")
    _git(d, "merge", "-q", "--squash", "base")
    _commit(d, "base を squash で入れる")
    _git(d, "checkout", "-q", "stack")                  # 積んだ枝が main を取り込む: ぶつかった file を枝の側で取る
    _git(d, "merge", "-q", "--no-commit", "main", check=False)
    _git(d, "checkout", "HEAD", "--", "法の表.md")         # 枝の古い base の側へ戻す（ぶつからなくても同じ事故）
    _git(d, "add", "法の表.md")
    _commit(d, 取り込みの文)


def test_注入_積んだ枝が古いbaseの側を取りmainの行を黙って落とすと赤(repo: Path):
    _積んだ枝の事故(repo)
    assert "main に入った大事な行" not in (repo / "法の表.md").read_text(encoding="utf-8")  # 再現できている
    r = _回す(repo, "main", "stack")
    assert r.returncode == 1, (r.stdout, r.stderr)
    assert "法の表.md" in r.stdout and "'main に入った大事な行'" in r.stdout and r.stdout.splitlines()[-1].startswith("赤:")


def test_ぶつからない取り込みは緑(repo: Path):
    _git(repo, "checkout", "-q", "-b", "枝")
    _書く(repo, "法の表.md", ["# 法の表", "行 1", "枝の行", "行 2"])
    _commit(repo, "枝")
    _git(repo, "checkout", "-q", "main")
    _書く(repo, "別.md", ["main の別の file"])
    _commit(repo, "main")
    _git(repo, "checkout", "-q", "枝")
    _git(repo, "merge", "-q", "--no-edit", "main")
    r = _回す(repo, "main", "枝")
    assert r.returncode == 0 and r.stdout.splitlines()[-1].startswith("緑:") and "取り込み 1 個" in r.stdout, r.stdout


def test_取り込みの文に捨てたと書いた行は赤にせず知らせる(repo: Path):
    _積んだ枝の事故(repo, "main を取り込む\n\n取り込みで捨てた行: 法の表.md")
    r = _回す(repo, "main", "stack")
    assert r.returncode == 0, r.stdout
    assert "知らせ" in r.stdout and "'main に入った大事な行'" in r.stdout


def test_後のcommitの文に捨てたと書いても通る_書いていない別のfileは赤のまま(repo: Path):
    _積んだ枝の事故(repo)
    _書く(repo, "積んだ物.md", ["積んだ枝の直し", "後の直し"])
    _commit(repo, "後の直し\n\n取り込みで捨てた行: 法の表.md")
    assert _回す(repo, "main", "stack").returncode == 0
    # 書いた path と違う file の落ちた行は赤のまま
    _git(repo, "reset", "-q", "--hard", "HEAD~1")
    _書く(repo, "積んだ物.md", ["積んだ枝の直し", "後の直し"])
    _commit(repo, "後の直し\n\n取り込みで捨てた行: 別の表.md")
    assert _回す(repo, "main", "stack").returncode == 1


def test_取り込みの中で別のfileへ動かした行は落ちたと数えない(repo: Path):
    _git(repo, "checkout", "-q", "-b", "枝")
    _書く(repo, "記録.md", ["# 記録", "枝の記録の行"])
    _commit(repo, "枝")
    _git(repo, "checkout", "-q", "main")
    _書く(repo, "記録.md", ["# 記録", "main の記録の行"])
    _commit(repo, "main")
    _git(repo, "checkout", "-q", "枝")
    _git(repo, "merge", "-q", "--no-commit", "main", check=False)
    _書く(repo, "記録.md", ["# 記録", "main の記録の行"])        # 枝の行を断片へ移す（CHANGELOG の adopt の役）
    _書く(repo, "断片/枝.txt", ["枝の記録の行"])
    _commit(repo, "main を取り込み、枝の行を断片へ移す")
    r = _回す(repo, "main", "枝")
    assert r.returncode == 0, r.stdout


def test_注入_取り込みの中でどちらの枝も変えていない行を書き換えると赤(repo: Path):
    _git(repo, "checkout", "-q", "-b", "枝")
    _書く(repo, "枝.md", ["枝"])
    _commit(repo, "枝")
    _git(repo, "checkout", "-q", "main")
    _書く(repo, "別.md", ["main"])
    _commit(repo, "main")
    _git(repo, "checkout", "-q", "枝")
    _git(repo, "merge", "-q", "--no-commit", "main")
    _書く(repo, "法の表.md", ["# 法の表", "行 1 を書き換えた", "行 2"])
    _commit(repo, "main を取り込む")
    r = _回す(repo, "main", "枝")
    assert r.returncode == 1 and "'行 1'" in r.stdout, r.stdout


def test_注入_字でないfileを相手が変えたのに片側で取ると赤(repo: Path):
    _書く(repo, "絵.bin", b"\x00\x01old")
    _commit(repo, "絵")
    _git(repo, "checkout", "-q", "-b", "枝")
    _書く(repo, "枝.md", ["枝"])
    _commit(repo, "枝")
    _git(repo, "checkout", "-q", "main")
    _書く(repo, "絵.bin", b"\x00\x01new")
    _commit(repo, "main の絵")
    _git(repo, "checkout", "-q", "枝")
    _git(repo, "merge", "-q", "--no-commit", "main")
    _git(repo, "checkout", "枝", "--", "絵.bin")          # 枝の古い絵へ戻す
    _commit(repo, "main を取り込む")
    r = _回す(repo, "main", "枝")
    assert r.returncode == 1 and "絵.bin" in r.stdout and "字でない" in r.stdout, r.stdout


def test_働けない時は2_無い名_引数の崩れ(repo: Path):
    r = _回す(repo, "無い枝", "main")
    assert r.returncode == 2 and "照らせない" in r.stderr and r.stdout == "", (r.stdout, r.stderr)
    assert _回す(repo, "--help").returncode == 2
    assert _回す(repo, "a", "b", "c").returncode == 2


def test_道具が壊れた時は2で赤の1と混ぜない(repo: Path):
    _積んだ枝の事故(repo)
    code = ("import runpy, subprocess, sys\n"
            "def _壊す(*a, **k): raise RuntimeError('注入した故障')\n"
            "subprocess.run = _壊す\n"
            f"sys.argv = [{str(道具)!r}, 'main', 'stack']\n"
            f"runpy.run_path({str(道具)!r}, run_name='__main__')\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=repo, capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "道具が壊れた" in r.stderr and "注入した故障" in r.stderr, (r.stdout, r.stderr)


def test_本物のrepoの枝の取り込みは黙って行を落としていない():
    """CI（pull_request）は PR の枝の origin/main..HEAD を照らす＝枝で main を取り込んだ commit が全部当たる。"""
    # base は test_骨.py の _main_からの変更 と同じ順（origin/main・無ければ main＝公開の写しは main だけを持つ）
    base = next((ref for ref in ("origin/main", "main") if subprocess.run(
        ["git", "-C", str(根), "rev-parse", "--verify", "-q", ref], capture_output=True).returncode == 0), None)
    if base is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("main が無い（CI の checkout は fetch-depth: 0 で取る＝.github/workflows/ci.yml）")
        pytest.skip("手元に main が無い")
    r = _回す(根, base, "HEAD")
    assert r.returncode == 0, r.stdout + r.stderr
