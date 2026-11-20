"""骨の自己検査。

1. 設計の目次（docs/設計/README.md）の全行の file・dir が在るか。
2. 顧客の語が repo に載っていないか（語の束は repo に持たない。環境から渡す。無ければ skip）。
3. 版の約束（docs/版の出し方.md）: 「互換が切れる:」は行の頭・型の版の上げに印・呼び口を変えた枝は CHANGELOG も変える・出した版の節は印の時と同じ・
   出した直し（道具/寄せ/直し/直し_NNNN.json）は一番新しい印の時と同じ。
4. 入れてよい物の線（docs/設計/入れてよい物.md）: 製品の名・事務所と側の名が載っていないか・直しはどの事務所にも当たる型の版の上げか。
   束と外しの一覧は tests/data/ の 1 か所。
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

from 名の字 import 束, 語, 語たち  # 束の読みと字の揺れのそろえは 1 か所（tests/名の字.py）

根 = Path(__file__).resolve().parent.parent
目次 = 根 / "docs" / "設計" / "README.md"

# 目次から消えてはいけない最低限の行。
要る設計書 = {
    f"docs/設計/{名}.md" for 名 in ("勤怠の形", "会社の決まり", "Drive の型", "法の表", "確かめと仮", "寄せる道具", "入れてよい物")
}
要る置き場 = {
    "法の表/", "芯/計算/", "芯/集計/", "入口/", "出口/",
    "初期設定/", "有給/", "管理表/", "道具/寄せ/", "tests/作り物/",
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


def 無い物(text: str, base: Path) -> list[str]:
    out = []
    for p in 目次の行(text):
        target = base / p
        if p.endswith("/"):
            if not (target / "README.md").is_file():
                out.append(p + "README.md")
        elif not target.is_file():
            out.append(p)
    return out


def test_目次が在る():
    assert 目次.is_file()


def test_目次の全行の物が在る():
    assert 無い物(目次.read_text(encoding="utf-8"), 根) == []


def test_目次に最低限の行がある():
    rows = set(目次の行(目次.read_text(encoding="utf-8")))
    assert 要る設計書 <= rows
    assert 要る置き場 <= rows


def test_無い物を見つけられる(tmp_path):
    text = "| file | 中身 |\n|---|---|\n| `在る.md` | a |\n| `無い.md` | b |\n| `空/` | c |\n"
    (tmp_path / "在る.md").write_text("x", encoding="utf-8")
    (tmp_path / "空").mkdir()
    assert 無い物(text, tmp_path) == ["無い.md", "空/README.md"]


def 顧客の語() -> list[str]:
    words = []
    path = os.environ.get("PAYROLL_NG_WORDS_FILE", "").strip()
    if path:
        words += Path(path).read_text(encoding="utf-8").splitlines()
    words += os.environ.get("PAYROLL_NG_WORDS", "").splitlines()
    return sorted({w.strip() for w in words if w.strip() and not w.strip().startswith("#")})


def 載っている所(base: Path, words: list[str]) -> list[str]:
    hits = []
    for f in sorted(base.rglob("*")):
        if not f.is_file() or 見ない & set(f.relative_to(base).parts):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        name = str(f.relative_to(base))
        for w in words:
            if 語(w).当たる(text) or 語(w).当たる(name):  # 字の揺れをそろえて当てる（tests/名の字.py）
                # 語そのものは出さない（出力に顧客の語を書かない）
                hits.append(f"{name}: 顧客の語の束の {words.index(w) + 1} 番目")
    return hits


def test_顧客の語が載っていない():
    words = 顧客の語()
    if not words:
        pytest.skip("顧客の語の束が渡されていない（PAYROLL_NG_WORDS_FILE / PAYROLL_NG_WORDS）")
    assert 載っている所(根, words) == []


def test_顧客の語を見つけられる(tmp_path):
    (tmp_path / "a.md").write_text("作り物の値だけ", encoding="utf-8")
    (tmp_path / "b.md").write_text("ここに禁じ語あり", encoding="utf-8")
    assert 載っている所(tmp_path, ["禁じ語"]) == ["b.md: 顧客の語の束の 1 番目"]
    (tmp_path / "b.md").write_text("ここに禁じ\u200b語あり", encoding="utf-8")  # 壊す: 幅の無い字を挟む
    assert 載っている所(tmp_path, ["禁じ語"]) == ["b.md: 顧客の語の束の 1 番目"]


# ---- 3. 版の約束（docs/版の出し方.md の CHANGELOG）----
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


def _手元に無い(なぜ: str):
    """git の履歴・印が手元に無い時。手元（浅い clone など）は skip、CI（GITHUB_ACTIONS）では赤＝CI では必ず回す。"""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        pytest.fail(f"{なぜ}（CI の checkout は fetch-depth: 0 で履歴と印を全部取る＝.github/workflows/ci.yml）")
    pytest.skip(f"{なぜ}（浅い clone など。git fetch --unshallow --tags origin で回る）")


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
    for ref in ("origin/main", "main"):
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


# 出した直しは書き替えない（docs/版の出し方.md・2026-11-18 オーナーの決定）: 版の印に入っている 道具/寄せ/直し/直し_NNNN.json は、
# それを持つ一番新しい印の時の中身と 1 字（1 byte）も違わない。消すのも赤。直したい時は新しい番号の直しを足す。
# 一番新しい印と比べる＝それより前の印の後の書き替え（直し 1・3 は v0.1.7 で、直し 20 は v0.23.0 で出した中身が今の正）は
# 出した事実として受け、これからを止める。印の時の中身は git から直に読む（写しの指紋の表を持たない）。
直しの置き場 = "道具/寄せ/直し/"
直しの名の形 = re.compile(r"直し_\d{4}\.json")


def 出した直しの書き替え(今: dict[str, bytes], 印の時: dict[str, dict[str, bytes]]) -> list[str]:
    """今の {直しの名: 中身} と {版の印: {直しの名: その印の時の中身}} → 書き替えた・消した直しの赤。"""
    最後: dict[str, tuple[str, bytes]] = {}
    for 版 in sorted(印の時, key=_版の数):
        for 名, 中身 in 印の時[版].items():
            最後[名] = (版, 中身)
    赤 = []
    for 名, (版, 前) in sorted(最後.items()):
        if 名 not in 今:
            赤.append(f"{名}: 出した直し（{版} に在る）を消した")
        elif 今[名] != 前:
            違い = [l for l in difflib.unified_diff(前.decode("utf-8", "replace").splitlines(),
                                                  今[名].decode("utf-8", "replace").splitlines(), lineterm="", n=0)
                  if l[:1] in "+-" and not l.startswith(("+++", "---"))]
            赤.append(f"{名}: 出した直しを書き替えた（{版} の時と違う行: {' / '.join(x[:60] for x in 違い[:4])}"
                      "・直したい時は新しい番号の直しを足す）")
    return 赤


def _今の直し(base: Path = 根) -> dict[str, bytes]:
    dir_ = base / 直しの置き場
    return {f.name: f.read_bytes() for f in sorted(dir_.glob("直し_*.json"))} if dir_.is_dir() else {}


def _印の時の直し() -> dict[str, dict[str, bytes]] | None:
    """{版の印: {直しの名: その印の時の中身}}。git・印・印の中身が手元に無い（浅い clone）なら None。"""
    def git(*a, input=None):
        return subprocess.run(["git", "-C", str(根), "-c", "core.quotepath=off", *a], input=input,
                              capture_output=True, check=True).stdout
    try:
        if git("rev-parse", "--is-shallow-repository").decode().strip() != "false":
            return None
        印たち = [t for t in git("tag", "-l", "v*").decode().split() if 版の印の形.fullmatch(t)]
        if not 印たち:
            return None
        印の時: dict[str, dict[str, str]] = {}
        for t in 印たち:
            印の時[t] = {}
            for 行 in git("ls-tree", "-z", t, "--", 直しの置き場).decode().split("\0"):
                if not 行:
                    continue
                頭, path = 行.split("\t", 1)
                名 = path.rsplit("/", 1)[-1]
                if 直しの名の形.fullmatch(名):
                    印の時[t][名] = 頭.split()[2]
        中身 = {}
        for sha in sorted({s for d in 印の時.values() for s in d.values()}):
            中身[sha] = git("cat-file", "blob", sha)
        return {t: {名: 中身[sha] for 名, sha in d.items()} for t, d in 印の時.items()}
    except (subprocess.CalledProcessError, FileNotFoundError, UnicodeDecodeError):
        return None


def test_出した直しは一番新しい印の時と同じ():
    印の時 = _印の時の直し()
    if 印の時 is None:
        _手元に無い("版の印（git の tag）とその時の直しが手元に無い")
    assert 出した直しの書き替え(_今の直し(), 印の時) == []


def test_出した直しの書き替えを見つけられる(tmp_path):
    a1, a3 = '{"版": 1}\n'.encode(), '{"版": 3}\n'.encode()
    印の時 = {
        "v0.1.0": {"直し_0001.json": '{"版": 1, "前の形": 1}\n'.encode()},
        "v0.1.2": {"直し_0001.json": a1, "直し_0002.json": '{"版": 2}\n'.encode()},
        "v0.2.0": {"直し_0001.json": a1, "直し_0002.json": '{"版": 2}\n'.encode(), "直し_0003.json": a3},
    }
    (tmp_path / 直しの置き場).mkdir(parents=True)

    def 置く(名, 中身):
        (tmp_path / 直しの置き場 / 名).write_bytes(中身)

    置く("直し_0001.json", a1)  # v0.1.0 の後に書き替えたが、一番新しい印 v0.2.0 の時と同じ＝出した事実として受ける
    置く("直し_0002.json", '{"版": 2}\n'.encode())
    置く("直し_0003.json", a3)
    置く("直し_0004.json", '{"版": 4, "まだ出していない": 1}\n'.encode())  # 印の無い新しい直しは見ない
    assert 出した直しの書き替え(_今の直し(tmp_path), 印の時) == []  # 緑
    置く("直し_0003.json", '{"版": 3 }\n'.encode())  # 壊す: 1 字（空白）を足した
    赤 = 出した直しの書き替え(_今の直し(tmp_path), 印の時)
    assert len(赤) == 1 and 赤[0].startswith("直し_0003.json: 出した直しを書き替えた（v0.2.0 の時と違う行")
    置く("直し_0003.json", a3)  # 戻す
    置く("直し_0001.json", '{"版": 1, "前の形": 1}\n'.encode())  # 壊す: 初めて出した印の時の中身へ戻した（一番新しい印と違う）
    assert len(出した直しの書き替え(_今の直し(tmp_path), 印の時)) == 1
    置く("直し_0001.json", a1)  # 戻す
    (tmp_path / 直しの置き場 / "直し_0002.json").unlink()  # 壊す: 出した直しを消した
    assert 出した直しの書き替え(_今の直し(tmp_path), 印の時) == ["直し_0002.json: 出した直し（v0.2.0 に在る）を消した"]
    置く("直し_0002.json", '{"版": 2}\n'.encode())  # 戻す
    assert 出した直しの書き替え(_今の直し(tmp_path), 印の時) == []  # 緑


# ---- 4. 入れてよい物の線（docs/設計/入れてよい物.md・⟦鍵:給与計算/パックの関所の機械の赤⟧）----
# a. 製品の名の束が .py・.json・.md・.html（md・html は <!-- 例 -->〜<!-- /例 --> の外）と file・dir の名に出たら赤
# b. 事務所・側の名の束が .py・.json に出たら赤（設計書の地の文は見ない）
# c. 直し（道具/寄せ/直し/直し_NNNN.json）に「どの事務所にも当たる型の版の上げ」の印が無ければ赤
#    （出た版の直しで印を持たない 2・4・5 だけ通す。中身は上の「出した直しは書き替えない」が印の時の file と照らして固定＝
#     名の番号と版が違う file は赤なので、版 ≤ 5 を名乗るだけの新しい file は通らない）
# 外し（tests/data/外し.json）は path ごと。外した file が当たらなくなったら、その行が赤（消し忘れを残さない）。
データ = 根 / "tests" / "data"
束を見ない = ("tests/data/", "CHANGELOG.md")  # 束そのもの・出した版の記録（書き替えない）
例の節 = re.compile(r"<!-- 例 -->.*?<!-- /例 -->", re.S)
# 出た版の直しのうち印を持たずに通る物。どの事務所にも当たると棚卸しした 2・4・5 だけ（中身は v0.1.2・v0.1.3 で出した時のまま＝
# test_出した直しは一番新しい印の時と同じ が git の印の時の file と照らす）。直し 1・3 は便 2 で前の形の読み替えを外し、印を持つ。
印の無い出た直し = frozenset({2, 4, 5})
当たるの印 = "全ての事務所"


def 外しの一覧(path: Path = データ / "外し.json") -> dict[str, dict[str, dict]]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return {k: {e["path"]: e for e in v} for k, v in d.items() if isinstance(v, list)}


def _files(base: Path):
    for f in sorted(base.rglob("*")):
        rel = f.relative_to(base)
        if 見ない & set(rel.parts) or not f.is_file():
            continue
        yield f, rel.as_posix()


def 製品の名の当たる所(base: Path, words: list) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for f, name in _files(base):
        if name.startswith(束を見ない):
            continue
        text = ""
        if f.suffix in (".py", ".json", ".md", ".html"):
            try:
                text = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                text = ""
            if f.suffix in (".md", ".html"):
                text = 例の節.sub("", text)
        for w in 語たち(words):
            if w.当たる(name):
                hits.setdefault(name, []).append(f"名に製品の名「{w}」")
            elif w.当たる(text):
                hits.setdefault(name, []).append(f"中に製品の名「{w}」")
    return hits


def 側の名の当たる所(base: Path, words: list) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for f, name in _files(base):
        if name.startswith(束を見ない) or f.suffix not in (".py", ".json"):
            continue
        text = f.read_text(encoding="utf-8")
        for w in 語たち(words):
            if w.当たる(text):
                hits.setdefault(name, []).append(f"中に事務所・側の名「{w}」")
    return hits


def 直しの当たらない所(base: Path, 型の版: int, 出た=印の無い出た直し) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    dir_ = base / "道具" / "寄せ" / "直し"
    for f in sorted(dir_.glob("直し_*.json")) if dir_.is_dir() else []:
        name = f.relative_to(base).as_posix()
        d = json.loads(f.read_text(encoding="utf-8"))
        版 = d.get("版")
        m = re.fullmatch(r"直し_(\d{4})\.json", f.name)
        if not m or not isinstance(版, int) or int(m.group(1)) != 版:
            hits[name] = [f"file の名の番号と版（{版}）が違う"]
            continue
        if 版 in 出た:
            continue  # 出た版の直し（どの事務所にも当たると棚卸し済み・中身は出した直しの照らしが固定）
        誤り = []
        if d.get("当たる") != 当たるの印:
            誤り.append(f"`\"当たる\": \"{当たるの印}\"` の印が無い（1 社のための直しは入れない）")
        if not isinstance(版, int) or d.get("前の版") != 版 - 1 or 版 > 型の版:
            誤り.append(f"型の版の上げの組でない（版 {版}・前の版 {d.get('前の版')}・初期設定/型.json の版 {型の版}）")
        if 誤り:
            hits[name] = 誤り
    return hits


def 線の赤(hits: dict[str, list[str]], 外し: dict[str, dict]) -> list[str]:
    赤 = [f"{p}: {m}" for p, ms in hits.items() if p not in 外し for m in ms]
    for p, e in 外し.items():
        if not str(e.get("なぜ", "")).strip() or not str(e.get("畳む", "")).strip():
            赤.append(f"外し {p}: なぜ と 畳む が要る")
        if p not in hits:
            赤.append(f"外し {p}: もう当たらない（外し.json からこの行を消す）")
    return 赤


def _型の版(base: Path = 根) -> int:
    return json.loads((base / "初期設定" / "型.json").read_text(encoding="utf-8"))["版"]


def test_製品の名が載っていない():
    hits = 製品の名の当たる所(根, 束(データ / "製品の名.txt"))
    assert 線の赤(hits, 外しの一覧()["製品の名"]) == []


def test_事務所と側の名が載っていない():
    hits = 側の名の当たる所(根, 束(データ / "側の名.txt"))
    assert 線の赤(hits, 外しの一覧()["側の名"]) == []


def test_直しはどの事務所にも当たる型の版の上げ():
    hits = 直しの当たらない所(根, _型の版())
    assert 線の赤(hits, 外しの一覧()["直しの当たる"]) == []


def test_外しの一覧の形():
    d = json.loads((データ / "外し.json").read_text(encoding="utf-8"))
    assert set(k for k, v in d.items() if isinstance(v, list)) == {"製品の名", "側の名", "直しの当たる"}
    for v in 外しの一覧().values():
        for p, e in v.items():
            assert (根 / p).is_file(), p


# 自己検査の試験: 壊すと赤・戻すと緑（作り物の語だけを使う）
def test_製品の名を見つけられる(tmp_path):
    (tmp_path / "芯").mkdir()
    (tmp_path / "芯" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "b.md").write_text("地の文\n<!-- 例 -->\n作り物ソフトの例\n<!-- /例 -->\n", encoding="utf-8")
    words = ["作り物ソフト"]
    assert 線の赤(製品の名の当たる所(tmp_path, words), {}) == []  # 緑（例の節の中は見ない）
    (tmp_path / "芯" / "a.py").write_text("形 = '作り物ソフト'\n", encoding="utf-8")  # 壊す: コードに
    (tmp_path / "docs" / "c.md").write_text("作り物ソフトの形\n", encoding="utf-8")  # 壊す: 例の節の外に
    (tmp_path / "入口" / "作り物ソフト").mkdir(parents=True)
    (tmp_path / "入口" / "作り物ソフト" / "README.md").write_text("x", encoding="utf-8")  # 壊す: dir の名に
    赤 = 線の赤(製品の名の当たる所(tmp_path, words), {})
    assert 赤 == ["docs/c.md: 中に製品の名「作り物ソフト」", "入口/作り物ソフト/README.md: 名に製品の名「作り物ソフト」",
                 "芯/a.py: 中に製品の名「作り物ソフト」"]
    外し = {"芯/a.py": {"なぜ": "作り物の移行", "畳む": "便 2 で畳む"}}
    assert len(線の赤(製品の名の当たる所(tmp_path, words), 外し)) == 2  # 外しは path ごと
    (tmp_path / "芯" / "a.py").write_text("x = 1\n", encoding="utf-8")  # 戻す
    (tmp_path / "docs" / "c.md").unlink()
    (tmp_path / "入口" / "作り物ソフト" / "README.md").unlink()
    assert 線の赤(製品の名の当たる所(tmp_path, words), {}) == []  # 緑
    assert 線の赤(製品の名の当たる所(tmp_path, words), 外し) == ["外し 芯/a.py: もう当たらない（外し.json からこの行を消す）"]


def test_側の名を見つけられる(tmp_path):
    (tmp_path / "a.json").write_text('{"側": "作り物の側"}', encoding="utf-8")
    (tmp_path / "b.md").write_text("作り物の側の窓が読む", encoding="utf-8")  # 地の文は見ない
    words = ["作り物の側"]
    assert 線の赤(側の名の当たる所(tmp_path, words), {}) == ["a.json: 中に事務所・側の名「作り物の側」"]  # 赤
    (tmp_path / "a.json").write_text('{"側": "入口"}', encoding="utf-8")  # 戻す
    assert 線の赤(側の名の当たる所(tmp_path, words), {}) == []  # 緑
    assert 線の赤({}, {"a.json": {"なぜ": "", "畳む": "便 2"}}) == [
        "外し a.json: なぜ と 畳む が要る", "外し a.json: もう当たらない（外し.json からこの行を消す）"]


def test_字の揺れた名も見つけられる(tmp_path):
    # 字のそのままの一致だと、全角・大小・幅の無い字を挟んだ名が束に当たらず通る（台帳 2026-11-20・#271 のレビュー）
    words = ["Sakumono", "作り物の側"]
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    assert 線の赤(側の名の当たる所(tmp_path, words), {}) == []  # 緑
    for 揺れ in ("Ｓａｋｕｍｏｎｏ", "SAKUMONO", "Saku\u200bmono", "Saku\u2060mo\ufeffno", "作り物の\u200d側"):
        (tmp_path / "a.py").write_text(f"x = '{揺れ}'\n", encoding="utf-8")  # 壊す: 揺れた字で名を書く
        assert len(線の赤(側の名の当たる所(tmp_path, words), {})) == 1, repr(揺れ)
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")  # 戻す
    assert 線の赤(側の名の当たる所(tmp_path, words), {}) == []
    # 製品の名は file・dir の名の揺れも拾う。〔大小を分ける〕の語だけは大小を分ける（地の英語と同じ綴りの名）
    (tmp_path / "ＳＡＫＵＭＯＮＯ").mkdir()
    (tmp_path / "ＳＡＫＵＭＯＮＯ" / "b.md").write_text("kumo と sakumono", encoding="utf-8")
    赤 = 線の赤(製品の名の当たる所(tmp_path, ["Sakumono", "Kumo〔大小を分ける〕"]), {})
    assert 赤 == ["ＳＡＫＵＭＯＮＯ/b.md: 名に製品の名「Sakumono」"]
    (tmp_path / "ＳＡＫＵＭＯＮＯ" / "b.md").write_text("Ｋｕ\u200bｍｏ", encoding="utf-8")  # 大小を分ける語も全角・幅の無い字は拾う
    assert "ＳＡＫＵＭＯＮＯ/b.md: 中に製品の名「Kumo」" in 線の赤(製品の名の当たる所(tmp_path, ["Kumo〔大小を分ける〕"]), {})


def test_本物の束は字の揺れをそろえて読む():
    # 本物の束の全部の語が、揺れた字（全角・大文字・幅の無い字を挟む）でも当たる（束の読みと当て方が 1 か所を通る）
    for f in ("製品の名.txt", "側の名.txt", "環境の名.txt"):
        for w in 束(データ / f):
            揺れ = "\u200b".join(w.字)
            assert w.当たる(揺れ), (f, str(w))
            if not w.大小を分ける:
                assert w.当たる(w.字.upper()) and w.当たる(w.字.lower()), (f, str(w))


def test_直しの印を見つけられる(tmp_path):
    dir_ = tmp_path / "道具" / "寄せ" / "直し"
    dir_.mkdir(parents=True)

    def 置く(版, 名=None, **k):
        d = {"版": 版, "前の版": 版 - 1, **k}
        (dir_ / (名 or f"直し_{版:04d}.json")).write_text(json.dumps(d), encoding="utf-8")
        return d

    置く(2)
    出た = {2}  # 印の無い出た版の直し（中身は test_出した直しの書き替えを見つけられる の照らしが固定）
    置く(1, 当たる=当たるの印)
    置く(6, 当たる=当たるの印)
    p = "道具/寄せ/直し/直し_{:04d}.json".format
    assert 線の赤(直しの当たらない所(tmp_path, 6, 出た), {}) == []  # 緑（2 は出た版・1 と 6 は印）
    assert 線の赤(直しの当たらない所(tmp_path, 6, set()), {}) == [
        f"{p(2)}: `\"当たる\": \"{当たるの印}\"` の印が無い（1 社のための直しは入れない）"]  # 出た版でない 2 は印が要る
    置く(2, 名="直し_0009.json")  # 壊す: 版 ≤ 5 を名乗る新しい file（名の番号と版が違う）
    assert 線の赤(直しの当たらない所(tmp_path, 6, 出た), {}) == [f"{p(9)}: file の名の番号と版（2）が違う"]
    (dir_ / "直し_0009.json").unlink()
    置く(7)  # 壊す: 印の無い新しい直し
    置く(8, 当たる="作り物の会社だけ")  # 壊す: 1 社のための直し
    赤 = 線の赤(直しの当たらない所(tmp_path, 8, 出た), {})
    assert len(赤) == 2 and all("印が無い" in r for r in 赤)
    assert len(線の赤(直しの当たらない所(tmp_path, 6, 出た), {})) == 4  # 壊す: 型の版を上げていない（7・8 が型の版 6 より上）
    外し = {p(7): {"なぜ": "作り物の移行", "畳む": "便 3 で畳む"}}
    assert len(線の赤(直しの当たらない所(tmp_path, 8, 出た), 外し)) == 1  # 外しは path ごと
    置く(7, 当たる=当たるの印)  # 戻す
    置く(8, 当たる=当たるの印)
    assert 線の赤(直しの当たらない所(tmp_path, 8, 出た), {}) == []  # 緑
    assert 線の赤(直しの当たらない所(tmp_path, 8, 出た), 外し) == [f"外し {p(7)}: もう当たらない（外し.json からこの行を消す）"]
