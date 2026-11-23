"""版の印は main の CI がその commit で緑に終わった後にだけ打つ（.github/workflows/tag.yml）。

前は main への push で CI の結果を待たずに印を打ち、CI が赤の commit に版の印が付きえた（原因の台帳 81c4a180）。
ここは 2 つを見る: (1) tag.yml の口が「ci の workflow_run の緑」と「手で打つ口」だけで、main への push で直に回らない。
(2) 印を打つ段の本文を、道具・gh・git を作り物に替えて回し、先が今回の CI の commit でない版・CI の緑が無い版に印を打たない。
pyyaml は CI に入れないので、tag.yml は字で読む。
公開の写しは tag.yml を持っていかない（scripts/public_mirror.py の OMIT）＝在る repo でだけ見る。
"""
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[1]
TAG = 根 / ".github" / "workflows" / "tag.yml"
if not TAG.exists():
    pytest.skip("tag.yml の無い公開の写し（印を打たない）", allow_module_level=True)


def _on(text: str) -> str:
    """`on:` の段（次の頭の鍵まで）。"""
    m = re.search(r"^on:\n(.*?)(?=^\S)", text, re.M | re.S)
    return m.group(1) if m else ""


def 口の外れ(text: str) -> list[str]:
    on = _on(text)
    out = []
    if re.search(r"^  push:", on, re.M):
        out.append("main への push で直に回る（CI を待たない）")
    if not re.search(r"^  workflow_run:\n    workflows: \[ci\]\n    types: \[completed\]\n    branches: \[main\]", on, re.M):
        out.append("ci の workflow_run（completed・main）で回らない")
    keys = set(re.findall(r"^  (\w+):", on, re.M))
    if keys - {"workflow_run", "workflow_dispatch"}:
        out.append(f"知らない口: {sorted(keys - {'workflow_run', 'workflow_dispatch'})}")
    for 要る in ("github.event.workflow_run.conclusion == 'success'", "github.event.workflow_run.event == 'push'",
                "github.ref == 'refs/heads/main'"):
        if 要る not in text:
            out.append(f"job の if に {要る} が無い")
    if "ref: ${{ github.event.workflow_run.head_sha || github.sha }}" not in text:
        out.append("CI が見た commit を取っていない")
    return out


def 打つ段(text: str) -> str:
    行s = text.splitlines()
    i = next(i for i, l in enumerate(行s) if l.strip() == "- name: まだ無い版の印を打つ")
    j = next(j for j in range(i, len(行s)) if 行s[j].strip() == "run: |")
    本文 = []
    for l in 行s[j + 1:]:
        if l.strip() and not l.startswith(" " * 10):
            break
        本文.append(l[10:])
    return "\n".join(本文) + "\n"


def test_tag_ymlはCIの緑の後にだけ回る():
    assert 口の外れ(TAG.read_text(encoding="utf-8")) == []


def test_注入_pushで直に回る形を拒む():
    今 = TAG.read_text(encoding="utf-8")
    前の形 = re.sub(r"^on:\n.*?(?=^\S)", "on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n", 今, flags=re.M | re.S)
    assert "main への push で直に回る（CI を待たない）" in 口の外れ(前の形)
    結果を見ない = 今.replace("github.event.workflow_run.conclusion == 'success' &&", "")
    assert any("conclusion" in x for x in 口の外れ(結果を見ない))
    先端を取る = 今.replace("ref: ${{ github.event.workflow_run.head_sha || github.sha }}", "ref: main")
    assert "CI が見た commit を取っていない" in 口の外れ(先端を取る)


A = "a" * 40
B = "b" * 40


def _回す(tmp: Path, 案: str, 緑: set[str], env: dict) -> tuple[subprocess.CompletedProcess, list[str]]:
    """打つ段を作り物の道具で回す。返す: (結果, 打った印 [版 sha])。"""
    bin_ = tmp / "bin"
    bin_.mkdir()
    記録 = tmp / "tags.log"

    def 置く(名, 中身):
        p = bin_ / 名
        p.write_text("#!/bin/bash\n" + 中身, encoding="utf-8")
        p.chmod(p.stat().st_mode | stat.S_IEXEC)

    置く("git", f'if [ "$1" = tag ]; then echo "$3 $4" >> "{記録}"; fi\nexit 0\n')
    緑の式 = " ".join(緑)
    置く("gh", f'for s in {緑の式}; do case "$*" in *head_sha=$s*) echo 1; exit 0;; esac; done\necho 0\n')
    道具 = tmp / ".agent-foundation-public" / "scripts" / "release"
    道具.mkdir(parents=True)
    (道具 / "tags_from_changelog.py").write_text(f"import sys\nsys.stdout.write({案!r})\n", encoding="utf-8")
    summary = tmp / "summary.md"
    r = subprocess.run(["bash", "-c", 打つ段(TAG.read_text(encoding="utf-8"))], cwd=tmp, capture_output=True, text=True,
                       env={**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "GITHUB_STEP_SUMMARY": str(summary),
                            "GITHUB_REPOSITORY": "作り物/パック", "GITHUB_EVENT_NAME": "workflow_run", "IN_VERSION": "", "IN_SHA": "", "CI_SHA": "", **env})
    打った = 記録.read_text(encoding="utf-8").split("\n")[:-1] if 記録.exists() else []
    return r, 打った


def test_自動の口は今回のCIのcommitが先の版だけ打つ(tmp_path):
    r, 打った = _回す(tmp_path, f"v0.2.0 {A}\nv0.3.0 {B}\n", {B}, {"CI_SHA": B})
    assert r.returncode == 0, r.stderr
    assert 打った == [f"v0.3.0 {B}"]                      # 先が別の commit の v0.2.0 はこの回では打たない


def test_注入_CIの緑が無い先には印を打たず止める(tmp_path):
    r, 打った = _回す(tmp_path, f"v0.3.0 {B}\n", set(), {"CI_SHA": B})
    assert r.returncode != 0 and 打った == []


def test_注入_手で打つ口も先のCIの緑を照らす(tmp_path):
    r, 打った = _回す(tmp_path, f"v0.1.0 {A}\n", set(), {"IN_VERSION": "v0.1.0", "IN_SHA": A})
    assert r.returncode != 0 and 打った == []
    (tmp_path / "緑").mkdir()
    r, 打った = _回す(tmp_path / "緑", f"v0.1.0 {A}\n", {A}, {"IN_VERSION": "v0.1.0", "IN_SHA": A})
    assert r.returncode == 0 and 打った == [f"v0.1.0 {A}"]


def test_打つ印が無い回は何もしない(tmp_path):
    r, 打った = _回す(tmp_path, "", set(), {"CI_SHA": B})
    assert r.returncode == 0 and 打った == []


def test_手で回す口は入力なしでも回り_版ごとに先のCIの緑を照らす(tmp_path):
    """前は入力なしの手で回す口が自動の口の枝へ入り、空の CI_SHA で道具を呼んで落ちた。"""
    r, 打った = _回す(tmp_path, f"v0.2.0 {A}\nv0.3.0 {B}\n", {A, B}, {"GITHUB_EVENT_NAME": "workflow_dispatch"})
    assert r.returncode == 0, r.stderr
    assert 打った == [f"v0.2.0 {A}", f"v0.3.0 {B}"]
    (tmp_path / "赤").mkdir()
    r, 打った = _回す(tmp_path / "赤", f"v0.2.0 {A}\nv0.3.0 {B}\n", {B}, {"GITHUB_EVENT_NAME": "workflow_dispatch"})
    assert r.returncode != 0 and 打った == []


def test_注入_自動の口でCIのcommitが空なら打たずに止める(tmp_path):
    r, 打った = _回す(tmp_path, f"v0.3.0 {B}\n", {B}, {"CI_SHA": ""})
    assert r.returncode != 0 and 打った == [] and "空" in r.stderr
