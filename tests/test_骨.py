"""骨の自己検査。

1. 設計の目次（docs/設計/README.md）の全行の file・dir が在るか。
2. 版の約束（docs/版の出し方.md）: 「互換が切れる:」は行の頭・型の版の上げに印・呼び口を変えた枝は CHANGELOG も変える・出した版の節は印の時と同じ。
"""
import datetime
import difflib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parent.parent
目次 = 根 / "docs" / "設計" / "README.md"

# 目次から消えてはいけない最低限の行。
要る設計書 = {
    f"docs/設計/{名}.md" for 名 in ("勤怠の形", "会社の決まり", "Drive の型", "法の表", "確かめと仮", "入れてよい物")
}
要る置き場 = {
    "法の表/", "芯/計算/", "芯/集計/", "入口/", "出口/",
    "初期設定/", "有給/", "管理表/", "tests/作り物/",
}
見ない = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}


def 目次の行(text: str) -> list[str]:
    """表の行から path を拾う。path は行の中の最初の `…`。"""
    行たち = []
    for line in text.splitlines():
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        m = re.search(r"`([^`]+)`", line)
        if m:
            行たち.append(m.group(1))
    return 行たち


def test_目次が在る():
    assert 目次.is_file()


def test_目次に最低限の行がある():
    rows = set(目次の行(目次.read_text(encoding="utf-8")))
    assert 要る設計書 <= rows
    assert 要る置き場 <= rows


# ---- 2. 版の約束（docs/版の出し方.md の CHANGELOG）----
CHANGELOG = 根 / "CHANGELOG.md"
_spec = importlib.util.spec_from_file_location("changelog", 根 / "scripts" / "changelog.py")
記録 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(記録)


def 未リリースを含む記録(根_: Path = 根) -> str:
    """CHANGELOG.md の「未リリース」の決まった 1 行を、記録の断片（CHANGELOG.d/）の行に置き替えた文（印の照らしの元）。"""
    return 記録.with_unreleased((根_ / "CHANGELOG.md").read_text(encoding="utf-8"), 記録.gathered_lines(根_))
印 = "互換が切れる:"
印の無い最後の型の版 = 5  # v0.1.3 までの節は書き替えない（出した版の記録）。6 からは型の版の行に印が要る


def 版の節(text: str) -> dict[str, list[str]]:
    """CHANGELOG の `## ` 見出しごとの行（`- ` の行だけ）。"""
    out, 今 = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            今 = line[3:].strip()
            out[今] = []
        elif 今 is not None and line.startswith("- "):
            out[今].append(line)
    return out


def 印の誤り(text: str, 型の版: int) -> list[str]:
    赤 = []
    for 節, 行たち in 版の節(text).items():
        for line in 行たち:
            if "互換が切れる" in re.sub(r"`[^`]*`", "", line) and not line.startswith("- " + 印):  # `…` の中は語の話
                赤.append(f"{節}: 「互換が切れる」が行の頭の `- {印}` の形でない: {line[:40]}")
    if 型の版 > 印の無い最後の型の版:
        行たち = [l for ls in 版の節(text).values() for l in ls if re.search(rf"型の版 *{型の版}(?!\d)", l)]
        if not any(l.startswith("- " + 印) for l in 行たち):
            赤.append(f"型の版 {型の版} の行に `{印}` が無い（型の版の上げは殻の渡す形が変わる）")
    return 赤


def test_互換が切れるの印の形と型の版():
    型の版 = json.loads((根 / "初期設定" / "型.json").read_text(encoding="utf-8"))["版"]
    assert 印の誤り(未リリースを含む記録(), 型の版) == []


def test_印の誤りを見つけられる():
    t = "## 未リリース\n- 型の版 6: 列を足した\n- 寄せ: 互換が切れる 所がある\n## [v0.1.3] - 2026-11-12\n- 型の版 5\n"
    assert len(印の誤り(t, 6)) == 2
    assert 印の誤り("## 未リリース\n- 互換が切れる: 型の版 6: 列を足した\n- 決まり: 頭に `互換が切れる:` を書く\n", 6) == []
    assert 印の誤り("## [v0.1.3] - 2026-11-12\n- 型の版 5: 列\n", 5) == []


呼び口の形 = re.compile(r"\.(py|json|html)$")


def 呼び口を変えたのに_changelog_が無い(変えた: list[str]) -> list[str]:
    """main からの枝で変えた path → 記録（自分の断片 CHANGELOG.d/<日付>-<話題>.txt・版を出す PR は CHANGELOG.md の版の節）を
    変えていなければ、変えた呼び口の path（tests/ の外の .py・.json・.html）。"""
    if "CHANGELOG.md" in 変えた or any(p.startswith("CHANGELOG.d/") and p.endswith(".txt") for p in 変えた):
        return []
    return [p for p in 変えた if 呼び口の形.search(p) and not p.startswith(("tests/", ".github/", ".claude/"))]


def _main_からの変更() -> list[str] | None:
    def git(*a):
        return subprocess.run(["git", "-C", str(根), *a], capture_output=True, text=True, check=True).stdout
    for ref in ("origin/main", "main"):
        try:
            基 = git("merge-base", "HEAD", ref).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        return [l for l in git("-c", "core.quotepath=off", "diff", "--name-only", 基).splitlines() if l]
    return None


手元に無い_の頭 = "git の履歴・印が手元に無い: "


def _手元に無い(なぜ: str):
    """git の履歴・印が手元に無い時。手元（浅い clone など）は skip、CI（GITHUB_ACTIONS）では赤＝CI では必ず回す。"""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        pytest.fail(f"{なぜ}（CI の checkout は fetch-depth: 0 で履歴と印を全部取る＝.github/workflows/ci.yml）")
    pytest.skip(f"{手元に無い_の頭}{なぜ}（浅い clone など。git fetch --unshallow --tags origin で回る）")


def test_呼び口を変えた枝は_changelog_に行を足す():
    変えた = _main_からの変更()
    if 変えた is None:
        _手元に無い("main が手元に無い")
    assert 呼び口を変えたのに_changelog_が無い(変えた) == []


def test_呼び口を変えたのに_changelog_が無いを見つけられる():
    assert 呼び口を変えたのに_changelog_が無い(["有給/有給.py", "tests/有給/test_x.py", "docs/a.md"]) == ["有給/有給.py"]
    assert 呼び口を変えたのに_changelog_が無い(["有給/有給.py", "CHANGELOG.md"]) == []
    assert 呼び口を変えたのに_changelog_が無い(["有給/有給.py", "CHANGELOG.d/20990101-x.txt"]) == []
    assert 呼び口を変えたのに_changelog_が無い(["有給/有給.py", "CHANGELOG.d/README.md"]) == ["有給/有給.py"]


# 記録の断片（CHANGELOG.d/README.md・scripts/changelog.py）: 全部の PR が「未リリース」の同じ所へ足す形にしない。
def test_記録の断片の形():
    assert 記録.check(根) == []


def _記録の置き場(tmp_path: Path, 未リリース: str = None) -> Path:
    (tmp_path / "CHANGELOG.d").mkdir(parents=True)
    (tmp_path / "CHANGELOG.d" / "README.md").write_text("書き方", encoding="utf-8")
    本文 = 記録.UNRELEASED_TEXT if 未リリース is None else 未リリース
    (tmp_path / "CHANGELOG.md").write_text(
        f"# CHANGELOG\n\n## 未リリース\n{本文}\n\n## [v0.2.0] - 2099-01-02\n- 乙\n\n## [v0.1.0] - 2099-01-01\n- 甲\n",
        encoding="utf-8")
    return tmp_path


def test_記録の断片の誤りを見つけられる(tmp_path):
    d = _記録の置き場(tmp_path)
    assert 記録.check(d) == []  # 緑（断片が無い）
    (d / "CHANGELOG.d" / "20990103-sakumono.txt").write_text("- 足した\n- 互換が切れる: 型の版 9\n", encoding="utf-8")
    assert 記録.check(d) == []  # 緑
    (d / "CHANGELOG.md").write_text((d / "CHANGELOG.md").read_text(encoding="utf-8").replace(
        記録.UNRELEASED_TEXT, 記録.UNRELEASED_TEXT + "\n- 古い形で足した行"), encoding="utf-8")  # 壊す: 未リリースへ直に足す
    assert len(記録.check(d)) == 1
    _記録の置き場(tmp_path / "b")
    d = tmp_path / "b"
    (d / "CHANGELOG.d" / "sakumono.txt").write_text("- x\n", encoding="utf-8")  # 壊す: 名に日付が無い
    (d / "CHANGELOG.d" / "20990103-y.txt").write_text("- x\n  続きの行\n", encoding="utf-8")  # 壊す: 1 項が 2 行
    (d / "CHANGELOG.d" / "20990103-z.txt").write_text("\n", encoding="utf-8")  # 壊す: 中身が無い
    assert len(記録.check(d)) == 3
    # 断片の行も「互換が切れる」の印の照らしに入る（型の版の上げの印が断片に無ければ赤）
    d = _記録の置き場(tmp_path / "c")
    (d / "CHANGELOG.d" / "20990103-k.txt").write_text("- 型の版 9: 列を足した\n", encoding="utf-8")  # 壊す: 印が無い
    assert 印の誤り(未リリースを含む記録(d), 9) != []
    (d / "CHANGELOG.d" / "20990103-k.txt").write_text("- 互換が切れる: 型の版 9: 列を足した\n", encoding="utf-8")
    assert 印の誤り(未リリースを含む記録(d), 9) == []


def test_版を出すと断片が版の節になり断片は消える(tmp_path):
    d = _記録の置き場(tmp_path)
    (d / "CHANGELOG.d" / "20990103-a.txt").write_text("- 甲の直し\n", encoding="utf-8")
    (d / "CHANGELOG.d" / "20990104-b.txt").write_text("- 乙の直し\n- 丙の直し\n", encoding="utf-8")
    assert 記録.release("v0.3.0", "2099-01-04", d) == "## [v0.3.0] - 2099-01-04"
    text = (d / "CHANGELOG.md").read_text(encoding="utf-8")
    assert 版の見出しの誤り(text) == [] and 記録.check(d) == []
    節 = 版の節(text)["[v0.3.0] - 2099-01-04"]
    assert sorted(節) == ["- 丙の直し", "- 乙の直し", "- 甲の直し"] and 節.index("- 乙の直し") < 節.index("- 丙の直し")
    assert [p.name for p in (d / "CHANGELOG.d").iterdir()] == ["README.md"]
    with pytest.raises(SystemExit):
        記録.release("v0.4.0", "2099-01-05", d)  # 断片が無ければ版を作らない


def _g(d: Path, *a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(d), "-c", "user.name=t", "-c", "user.email=t@users.noreply.github.com",
                           "-c", "core.quotepath=off", *a], capture_output=True, text=True)


def test_古い形の行を断片へ移す_取り込みでぶつかった途中でも(tmp_path):
    # この形の前に枝を切った PR が main を取り込む時（CHANGELOG.d/README.md の手順どおり）。ぶつかった途中の CHANGELOG.md には
    # 自分の行が印の内側に残るので、そこを「すでに在る行」と読むと 0 行しか移らず、行が黙って消える（#280 のレビュー）
    d = tmp_path / "r"
    d.mkdir()
    _g(d, "init", "-q", "-b", "main")
    古い頭 = "# C\n\n## 未リリース\n- 甲（main の前の行）\n\n## [v0.1.0] - 2099-01-01\n- 初め\n"
    (d / "CHANGELOG.md").write_text(古い頭, encoding="utf-8")
    _g(d, "add", "-A"); _g(d, "commit", "-qm", "古い形")
    _g(d, "checkout", "-qb", "claude/20990102-mine")
    (d / "CHANGELOG.md").write_text(古い頭.replace("- 甲（main の前の行）\n", "- 甲（main の前の行）\n- 乙（自分の行）\n"), encoding="utf-8")
    _g(d, "commit", "-qam", "自分の行")
    _g(d, "checkout", "-q", "main")
    (d / "CHANGELOG.d").mkdir()
    (d / "CHANGELOG.d" / "README.md").write_text("書き方", encoding="utf-8")
    (d / "CHANGELOG.d" / "20990101-sono.txt").write_text("- 甲（main の前の行）\n", encoding="utf-8")
    (d / "CHANGELOG.md").write_text(
        f"# C\n\n## 未リリース\n{記録.UNRELEASED_TEXT}\n\n## [v0.1.0] - 2099-01-01\n- 初め\n", encoding="utf-8")
    _g(d, "add", "CHANGELOG.md", "CHANGELOG.d"); _g(d, "commit", "-qm", "断片の形")
    _g(d, "checkout", "-q", "claude/20990102-mine")
    assert _g(d, "merge", "-q", "main").returncode != 0  # ぶつかる
    assert "<<<<<<<" in (d / "CHANGELOG.md").read_text(encoding="utf-8")
    先 = d / "CHANGELOG.d" / "20990102-mine.txt"
    自分の = _g(d, "show", "HEAD:CHANGELOG.md").stdout
    assert 記録.adopt(自分の, 先, d, base="main") == ["- 乙（自分の行）"]  # main に在る 甲 は移さない・自分の 乙 は移す
    _g(d, "checkout", "main", "--", "CHANGELOG.md")
    assert 記録.check(d) == [] and 先.read_text(encoding="utf-8") == "- 乙（自分の行）\n"

    # 取り込む先が読めない時・断片にぶつかった印が残る時は止める（黙って 0 行で進まない）
    with pytest.raises(SystemExit):
        記録.adopt(自分の, d / "CHANGELOG.d" / "20990102-b.txt", d, base="無い枝")
    先.write_text("<<<<<<< HEAD\n- x\n=======\n- y\n>>>>>>> main\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        記録.adopt(自分の, d / "CHANGELOG.d" / "20990102-b.txt", d, base="main")


# 版を出す枝を切った後に main へ入った断片が、合流で断片のまま残り版の節から落ちる（v0.39.0 の版を出す PR のレビュー・原因の台帳）。
# 並びは main で比べる（枝の側で見ると、版の枝へ main を取り込んだ形を見逃し、ふつうの枝へ版の後の main を取り込んだ形を赤にする）。
def _版の並びの置き場(tmp_path: Path) -> Path:
    d = tmp_path / "r"
    d.mkdir()
    _g(d, "init", "-q", "-b", "main")
    (d / "CHANGELOG.d").mkdir()
    (d / "CHANGELOG.d" / "README.md").write_text("書き方", encoding="utf-8")
    (d / "CHANGELOG.md").write_text(
        f"# C\n\n## 未リリース\n{記録.UNRELEASED_TEXT}\n\n## [v0.1.0] - 2099-01-01\n- 初め\n", encoding="utf-8")
    _g(d, "add", "-A"); _g(d, "commit", "-qm", "初め")
    (d / "CHANGELOG.d" / "20990102-mae.txt").write_text("- 版の前の直し\n", encoding="utf-8")
    _g(d, "add", "-A"); _g(d, "commit", "-qm", "版の前の直し")
    return d


def _断片を足す(d: Path, 名: str, 行: str) -> None:
    (d / "CHANGELOG.d" / 名).write_text(行 + "\n", encoding="utf-8")
    _g(d, "add", "-A"); _g(d, "commit", "-qm", 名)


def _枝を_main_へ寄せる(d: Path, 枝: str) -> None:
    """枝を 1 つの commit にして main へ入れる（GitHub の squash の合流と同じ形）。"""
    _g(d, "checkout", "-q", "main")
    assert _g(d, "merge", "-q", "--squash", 枝).returncode == 0
    _g(d, "commit", "-qm", f"{枝} を寄せた")


def test_版の枝を切った後に入った断片が節から落ちると赤(tmp_path):
    d = _版の並びの置き場(tmp_path)
    _g(d, "checkout", "-qb", "claude/20990103-ban")
    記録.release("v0.2.0", "2099-01-03", d)
    _g(d, "commit", "-qam", "版 v0.2.0")
    _g(d, "checkout", "-q", "main")
    _断片を足す(d, "20990103-ato.txt", "- 枝を切った後の直し")  # 版の枝を切った後に main へ入った
    _g(d, "checkout", "-q", "claude/20990103-ban")
    assert 記録.取り残し(d, base="main") == []  # 取り込む前は断片が手元に無い（合流の時に落ちる）
    assert _g(d, "merge", "-q", "--no-edit", "main").returncode == 0  # 版の枝へ main を取り込んだ（ぶつからない）
    assert [e.split(":")[0] for e in 記録.取り残し(d, base="main")] == ["CHANGELOG.d/20990103-ato.txt"]
    assert 記録.取り残し(d, base="origin/main") is None  # base が無ければ照らしたと言わない
    _枝を_main_へ寄せる(d, "claude/20990103-ban")  # そのまま合流した main も赤（版の印は main の CI の緑の後だけ）
    assert [e.split(":")[0] for e in 記録.取り残し(d, base="main")] == ["CHANGELOG.d/20990103-ato.txt"]


def test_版の節を今の_main_から束ね直せば緑(tmp_path):
    d = _版の並びの置き場(tmp_path)
    _g(d, "checkout", "-qb", "claude/20990103-ban")
    _g(d, "checkout", "-q", "main")
    _断片を足す(d, "20990103-ato.txt", "- 枝を切った後の直し")
    _g(d, "checkout", "-q", "claude/20990103-ban")
    assert _g(d, "merge", "-q", "--no-edit", "main").returncode == 0  # 先に main を取り込んでから束ねる
    記録.release("v0.2.0", "2099-01-03", d)
    _g(d, "commit", "-qam", "版 v0.2.0")
    assert 記録.取り残し(d, base="main") == []
    _枝を_main_へ寄せる(d, "claude/20990103-ban")
    assert 記録.取り残し(d, base="main") == []
    _断片を足す(d, "20990104-tsugi.txt", "- 次の版の直し")  # 版の後に main へ入った断片は次の版の物＝緑
    assert 記録.取り残し(d, base="main") == []


def test_版の前に切ったふつうの枝が版の後の_main_を取り込んでも赤にしない(tmp_path):
    d = _版の並びの置き場(tmp_path)
    _g(d, "checkout", "-qb", "claude/20990103-futsuu")
    _断片を足す(d, "20990103-futsuu.txt", "- ふつうの直し")  # 版の前に切った枝の断片
    _g(d, "checkout", "-q", "main")
    記録.release("v0.2.0", "2099-01-03", d)
    _g(d, "commit", "-qam", "版 v0.2.0")
    _g(d, "checkout", "-q", "claude/20990103-futsuu")
    assert _g(d, "merge", "-q", "--no-edit", "main").returncode == 0
    assert 記録.取り残し(d, base="main") == []  # 自分の断片は main にまだ無い＝合流すると節より新しい
    _枝を_main_へ寄せる(d, "claude/20990103-futsuu")
    assert 記録.取り残し(d, base="main") == []


def test_版の節と同じ時に足した断片も赤(tmp_path):
    d = _版の並びの置き場(tmp_path)
    _g(d, "checkout", "-qb", "claude/20990103-ban")
    記録.release("v0.2.0", "2099-01-03", d)
    (d / "CHANGELOG.d" / "20990103-ban.txt").write_text("- 版の枝で足した直し\n", encoding="utf-8")  # 束ねた後に足した
    assert [e.split(":")[0] for e in 記録.取り残し(d, base="main")] == ["CHANGELOG.d/20990103-ban.txt"]
    _g(d, "add", "-A"); _g(d, "commit", "-qm", "版 v0.2.0 と断片")
    _枝を_main_へ寄せる(d, "claude/20990103-ban")  # main の同じ commit で入った節と断片は並びが分からない（1 つに畳んだ写し）＝赤にしない
    assert 記録.取り残し(d, base="main") == []


def test_この_repo_の断片は一番新しい版の節より後に入った物だけ():
    赤 = 記録.取り残し(根)
    if 赤 is None:  # 公開の写しは main だけを持つ（_main_からの変更 と同じ順）
        赤 = 記録.取り残し(根, base="main")
    if 赤 is None:
        _手元に無い("git の履歴か origin/main が手元に無い（版の節と断片の並びを照らせない）")
    assert 赤 == []


_AI_の枝 = re.compile(r"^claude/(\d{8}-.+)$")


def 枝の名と違う断片(枝: str, 足した: list[str]) -> list[str]:
    """AI の窓の枝 claude/<YYYYMMDD>-<話題> で足した断片が <YYYYMMDD>-<話題>.txt でなければ、その path（人の枝は見ない）。"""
    m = _AI_の枝.match(枝 or "")
    if not m:
        return []
    return [p for p in 足した if p.startswith("CHANGELOG.d/") and p.endswith(".txt") and p != f"CHANGELOG.d/{m.group(1)}.txt"]


def _足した断片() -> list[str] | None:
    def git(*a):
        return subprocess.run(["git", "-C", str(根), "-c", "core.quotepath=off", *a], capture_output=True, text=True, check=True).stdout
    # PR の向き先（GITHUB_BASE_REF）から数える。作業の枝へ向ける PR は、向き先の枝が main から足した断片を自分の物と数えない。
    向き先 = os.environ.get("GITHUB_BASE_REF")
    for ref in ((f"origin/{向き先}",) if 向き先 else ()) + ("origin/main", "main"):
        try:
            基 = git("merge-base", "HEAD", ref).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        # main から足した断片（commit 済み・索引）と、まだ git に足していない断片（手元で書いた直後も CI と同じに見る）
        足した = git("diff", "--name-only", "--diff-filter=A", 基, "--", "CHANGELOG.d").splitlines()
        足した += git("ls-files", "--others", "--exclude-standard", "--", "CHANGELOG.d").splitlines()
        return sorted({l for l in 足した if l})
    return None


def test_枝で足す断片は枝の名と同じ():
    足した = _足した断片()
    if 足した is None:
        _手元に無い("main が手元に無い")
    枝 = os.environ.get("GITHUB_HEAD_REF") or subprocess.run(
        ["git", "-C", str(根), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert 枝の名と違う断片(枝, 足した) == []


def test_枝の名と違う断片を見つけられる():
    assert 枝の名と違う断片("claude/20990101-sakumono", ["CHANGELOG.d/20990101-sakumono.txt"]) == []
    assert 枝の名と違う断片("claude/20990101-sakumono", ["CHANGELOG.d/20990101-hoka.txt"]) == ["CHANGELOG.d/20990101-hoka.txt"]
    assert 枝の名と違う断片("人の枝", ["CHANGELOG.d/20990101-hoka.txt"]) == []
    assert 呼び口を変えたのに_changelog_が無い(["tests/有給/test_x.py", "docs/a.md"]) == []


# 出した版の節は書き替えない（docs/版の出し方.md）: 版の印 vX.Y.Z が在る節は、その印の時の CHANGELOG の同じ節と 1 字も違わない。
# 節＝`## [vX.Y.Z]` の見出しの行から次の `## ` の前まで（見出しの日も含む・末の空行は見ない）。
# 印の時に自分の節が無かった版（v0.1.0・v0.1.1）は、今も節を持たない（後から足すのも書き替え）。
# 印の無い節は、一番新しい印より新しい版だけ（版の節を作って main へ入れ、印を打つまでの間）。
# ただしこれは CHANGELOG の版の全部に印を打つ repo（印を打つ workflow `.github/workflows/tag.yml` が在る＝この元の repo）だけ。
# 公開の写しは tag.yml を持たず、出した版にだけ印が付く（間の版は埋めない＝docs/版の出し方.md「公開版へ出す」）ので、
# 印の無い古い節が在って当たり前＝そこでは見ない（印の在る節が 1 字も違わないことはどちらでも見る）。
版の印の形 = re.compile(r"v(\d+)\.(\d+)\.(\d+)")


def 版の節の全文(text: str) -> dict[str, str]:
    out, 今 = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            m = re.match(r"## \[(v\d+\.\d+\.\d+)\]", line)
            今 = m.group(1) if m else None
            if 今:
                out[今] = []
        if 今:
            out[今].append(line)
    return {k: "\n".join(v).rstrip("\n ") for k, v in out.items()}


def _版の数(版: str) -> tuple[int, ...]:
    return tuple(int(x) for x in 版の印の形.fullmatch(版).groups())


def 出した版の節の書き替え(今: str, 印の時: dict[str, str], 全部の版に印を打つ: bool = True) -> list[str]:
    """今の CHANGELOG と {版の印: その印の時の CHANGELOG} → 書き替えた節の赤。

    全部の版に印を打つ＝False（公開の写し）なら、印の無い古い節は赤にしない。"""
    今の節 = 版の節の全文(今)
    赤 = []
    for 版, 前 in sorted(印の時.items(), key=lambda kv: _版の数(kv[0])):
        前の節 = 版の節の全文(前)
        if 版 not in 前の節:
            if 版 in 今の節:
                赤.append(f"{版}: 印の時の CHANGELOG に無かった節を後から足した")
        elif 版 not in 今の節:
            赤.append(f"{版}: 出した版の節を消した")
        elif 今の節[版] != 前の節[版]:
            違い = [l for l in difflib.unified_diff(前の節[版].splitlines(), 今の節[版].splitlines(), lineterm="", n=0)
                  if l[:1] in "+-" and not l.startswith(("+++", "---"))]
            赤.append(f"{版}: 出した版の節を書き替えた（印の時と違う行: {' / '.join(x[:60] for x in 違い[:4])}）")
    if 印の時 and 全部の版に印を打つ:
        一番新しい = max(印の時, key=_版の数)
        for 版 in 今の節:
            if 版 not in 印の時 and _版の数(版) <= _版の数(一番新しい):
                赤.append(f"{版}: 版の印が無いのに、一番新しい印 {一番新しい} より新しくない節")
    return 赤


def _印の時の_changelog() -> dict[str, str] | None:
    """{版の印: その印の時の CHANGELOG.md}。git・印・印の中身が手元に無い（浅い clone は印が欠ける）なら None。"""
    def git(*a):
        return subprocess.run(["git", "-C", str(根), *a], capture_output=True, text=True, check=True).stdout
    try:
        if git("rev-parse", "--is-shallow-repository").strip() != "false":
            return None
        印たち = [t for t in git("tag", "-l", "v*").split() if 版の印の形.fullmatch(t)]
        if not 印たち:
            return None
        return {t: git("show", f"{t}:CHANGELOG.md") for t in 印たち}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def test_出した版の節は印の時と同じ():
    印の時 = _印の時の_changelog()
    if 印の時 is None:
        _手元に無い("版の印（git の tag）とその時の CHANGELOG が手元に無い")
    assert 出した版の節の書き替え(CHANGELOG.read_text(encoding="utf-8"), 印の時, 全部の版に印を打つ()) == []


def 全部の版に印を打つ(根_: Path = 根) -> bool:
    """CHANGELOG の版の全部に印を打つ repo か＝印を打つ workflow が在るか（公開の写しは持っていかない）。"""
    return (根_ / ".github" / "workflows" / "tag.yml").exists()


def test_公開の写しでは印の無い古い節を赤にしない():
    # 公開の写しは間の版を埋めない（v0.2.0 を出さず v0.3.0 だけ出した）。印の在る節は同じ・印の無い節は古くても通る
    今 = "## 未リリース\n\n## [v0.3.0] - 2026-11-13\n- 丙\n\n## [v0.2.0] - 2026-11-13\n- 乙\n"
    印の時 = {"v0.3.0": 今}
    assert 出した版の節の書き替え(今, 印の時, 全部の版に印を打つ=False) == []
    assert 出した版の節の書き替え(今, 印の時) == ["v0.2.0: 版の印が無いのに、一番新しい印 v0.3.0 より新しくない節"]
    # 印の在る節の書き替えは写しでも赤
    assert 出した版の節の書き替え(今.replace("- 丙", "- 丁"), 印の時, 全部の版に印を打つ=False)


def test_出した版の節の書き替えを見つけられる():
    印の時 = {
        "v0.1.0": "## 未リリース\n- 初め\n",
        "v0.1.2": "## 未リリース\n\n## [v0.1.2] - 2026-11-12\n- 甲\n",
        "v0.2.0": "## 未リリース\n\n## [v0.2.0] - 2026-11-13\n- 乙\n\n## [v0.1.2] - 2026-11-12\n- 甲\n",
    }
    正 = "## 未リリース\n- 新\n\n## [v0.3.0] - 2026-11-14\n- 丙\n\n## [v0.2.0] - 2026-11-13\n- 乙\n\n## [v0.1.2] - 2026-11-12\n- 甲\n"
    assert 出した版の節の書き替え(正, 印の時) == []
    # 合流で未リリースの行が出した版の節へ紛れた（#174 の形）
    assert len(出した版の節の書き替え(正.replace("- 乙\n", "- 乙\n- 紛れた行\n"), 印の時)) == 1
    assert len(出した版の節の書き替え(正.replace("- 甲", "- 甲を直した"), 印の時)) == 1  # 字を替えた
    assert len(出した版の節の書き替え(正.replace("2026-11-13", "2026-11-15"), 印の時)) == 1  # 見出しの日
    assert len(出した版の節の書き替え(正.replace("## [v0.1.2] - 2026-11-12\n- 甲\n", ""), 印の時)) == 1  # 消した
    assert len(出した版の節の書き替え(正 + "\n## [v0.1.0] - 2026-11-11\n- 後から\n", 印の時)) == 1  # 印の時に無かった節
    assert len(出した版の節の書き替え(正 + "\n## [v0.1.5] - 2026-11-13\n- 印が無い\n", 印の時)) == 1  # 印の無い古い版



# 版の節の見出しの形（docs/版の出し方.md）: `## ` の見出しは `## 未リリース`（頭に 1 つ）と `## [vX.Y.Z] - YYYY-MM-DD` だけ。
# 形の崩れた見出し（日が抜けた・日の形が違う・暦に無い日）は版の印を打つ道具に版として読まれず、黙って印が打たれない＝赤。
# 版は上から下へ下がり続け（同じ版を 2 度書かない）、日は上の版ほど前でない。
版の見出しの形 = re.compile(r"## \[(v\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})")


def 版の見出しの誤り(text: str) -> list[str]:
    赤, 前 = [], None   # 前＝一つ上の版の (版の数, 日)
    見出したち = [l.rstrip() for l in text.splitlines() if l.startswith("## ")]
    if not 見出したち or 見出したち[0] != "## 未リリース":
        赤.append("一番上の見出しが `## 未リリース` でない")
    for 行 in 見出したち:
        if 行 == "## 未リリース":
            continue
        m = 版の見出しの形.fullmatch(行)
        if not m:
            赤.append(f"版の見出しの形（`## [vX.Y.Z] - YYYY-MM-DD`）でない: {行[:60]}")
            continue
        try:
            日 = datetime.date.fromisoformat(m.group(2))
        except ValueError:
            赤.append(f"{m.group(1)}: 暦に無い日 {m.group(2)}")
            continue
        数 = _版の数(m.group(1))
        if 前 is not None:
            if 数 >= 前[0]:
                赤.append(f"{m.group(1)}: 上の版より新しいか同じ（版は上から下へ下がり続ける）")
            elif 日 > 前[1]:
                赤.append(f"{m.group(1)}: 日 {日} が上の新しい版の日 {前[1]} より後")
        前 = (数, 日)
    if 見出したち.count("## 未リリース") > 1:
        赤.append("`## 未リリース` が 2 つ以上ある")
    return 赤


def test_版の見出しの形と並び():
    assert 版の見出しの誤り(CHANGELOG.read_text(encoding="utf-8")) == []


def test_版の見出しの誤りを見つけられる():
    正 = "# CHANGELOG\n\n## 未リリース\n- 新\n\n## [v0.3.0] - 2026-11-14\n- 丙\n\n## [v0.2.0] - 2026-11-13\n- 乙\n\n## [v0.1.2] - 2026-11-12\n- 甲\n"
    assert 版の見出しの誤り(正) == []
    assert 版の見出しの誤り(正.replace("## [v0.2.0] - 2026-11-13", "## [v0.2.0]")) != []            # 日が抜けた（v0.26.0 のレビューの穴）
    assert 版の見出しの誤り(正.replace("## [v0.2.0] - 2026-11-13", "## [v0.2.0] 2026-11-13")) != []   # 区切りが違う
    assert 版の見出しの誤り(正.replace("2026-11-13", "2026/11/13")) != []                           # 日の形が違う
    assert 版の見出しの誤り(正.replace("2026-11-13", "2026-11-31")) != []                           # 暦に無い日
    assert 版の見出しの誤り(正.replace("## [v0.2.0]", "## v0.2.0")) != []                           # 括弧が無い
    assert 版の見出しの誤り(正.replace("## [v0.2.0]", "## [0.2.0]")) != []                          # v が無い
    assert 版の見出しの誤り(正.replace("v0.2.0", "v0.4.0")) != []                                   # 版が逆順
    assert 版の見出しの誤り(正.replace("v0.2.0", "v0.3.0")) != []                                   # 同じ版を 2 度
    assert 版の見出しの誤り(正.replace("2026-11-13", "2026-11-15")) != []                           # 日が逆順
    assert 版の見出しの誤り(正.replace("## 未リリース\n- 新\n\n", "")) != []                      # 未リリースが無い
    assert 版の見出しの誤り(正 + "\n## 未リリース\n") != []                                       # 未リリースが 2 つ
    assert 版の見出しの誤り(正.replace("## [v0.1.2]", "## [v0.1.2 ]")) != []

