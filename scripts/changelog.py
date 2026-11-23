#!/usr/bin/env python3
"""変更の記録の断片（CHANGELOG.d/）を照らす・束ねる・版の節にする。決まりの正本は CHANGELOG.d/README.md。

全部の PR が CHANGELOG.md の「未リリース」の末尾へ 1 行を足すと、1 本入るたびに残りの PR が全部ぶつかり、git の自動の
取り込みが行を出した版の節へ紛れ込ませる事も起きた（#249・#252 の寄せ直し・台帳 2026-11-20）。そこで、PR ごとに
CHANGELOG.d/<YYYYMMDD>-<話題>.txt を 1 つ足し（枝の名と同じ＝2 本の PR が同じ file を作らない）、CHANGELOG.md の
「未リリース」には決まった 1 行だけを置く。版を出す時だけ、断片を束ねて版の節にし断片を消す（`版` の口）。
版の節（`## [vX.Y.Z] - YYYY-MM-DD`）の形と印の打ち方（tag.yml）は今までと同じ。

  python3 scripts/changelog.py check                     # 形を照らす（赤なら 1）
  python3 scripts/changelog.py                           # 未リリースの断片を、main に入った順（新しい物が上）で見せる
  python3 scripts/changelog.py 版 vX.Y.Z YYYY-MM-DD      # 断片を束ねて版の節を CHANGELOG.md に作り、断片を消す（版を出す PR）
  python3 scripts/changelog.py adopt <古い形の CHANGELOG.md|-> <断片の file> [<取り込む先・既定 origin/main>]
      # 古い形で「未リリース」に足した自分の行を断片へ移す（この形の前に枝を切った PR が main を取り込む時）。
      # すでに在る行は取り込む先の版から読む（作業中のぶつかった CHANGELOG.md からは読まない）

終わりの値: 0 緑・済んだ／1 赤・止めた（形が赤・出す物が無い・節が既に在る・ぶつかった印が残る）／
2 道具が働けない（使い方の誤り・取り込む先が読めない・道具そのものが壊れた）。2 は結果ではない（1 と混ぜない）。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR_NAME = "CHANGELOG.d"
# 断片の名: <YYYYMMDD>-<話題>.txt。話題は枝の名の日付の後と同じ字（日本語の枝の名もある＝空白と / だけを拒む）。
NAME_RE = re.compile(r"^\d{8}-[^\s/\\]+\.txt$")
# CHANGELOG.md の「未リリース」に置く決まった 1 行（記録の行は書かない）。
UNRELEASED_HEAD = "## 未リリース"
UNRELEASED_TEXT = "記録は 1 PR に 1 つの file で `CHANGELOG.d/` に置く（書き方は `CHANGELOG.d/README.md`。ここには行を足さない）。版を出す時に `python3 scripts/changelog.py 版` が節にする。"
VERSION_HEAD_RE = re.compile(r"^## \[(v\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$")


def fragments(root: Path = ROOT) -> list[Path]:
    d = root / DIR_NAME
    return sorted(p for p in d.iterdir() if p.name != "README.md") if d.is_dir() else []


def unreleased_body(text: str) -> str | None:
    """CHANGELOG.md の「未リリース」の節の中身（見出しの次から次の `## ` の前まで・前後の空白を落とす）。節が無ければ None。"""
    m = re.search(rf"^{re.escape(UNRELEASED_HEAD)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else None


def check(root: Path = ROOT) -> list[str]:
    """形の誤りを全部返す（空なら緑）。"""
    errs: list[str] = []
    main = root / "CHANGELOG.md"
    if not main.is_file():
        return ["CHANGELOG.md が無い"]
    body = unreleased_body(main.read_text(encoding="utf-8"))
    if body is None:
        errs.append(f"CHANGELOG.md に `{UNRELEASED_HEAD}` の節が無い")
    elif body != UNRELEASED_TEXT:
        errs.append(f"CHANGELOG.md の「未リリース」は決まった 1 行だけ（記録の行は自分の枝の {DIR_NAME}/<日付>-<話題>.txt に書く。"
                    f"古い形で足した行は `python3 scripts/changelog.py adopt` で移す・{DIR_NAME}/README.md）")
    d = root / DIR_NAME
    if not (d / "README.md").is_file():
        errs.append(f"{DIR_NAME}/README.md が無い")
    for p in fragments(root):
        if p.is_dir() or not NAME_RE.match(p.name):
            errs.append(f"{DIR_NAME}/{p.name}: 名は <YYYYMMDD>-<話題>.txt（枝 claude/<日付>-<話題> と同じ・空白と / は使わない）")
            continue
        lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            errs.append(f"{DIR_NAME}/{p.name}: 中身が無い")
        for n, line in enumerate(lines, 1):
            if not re.match(r"^- \S", line):
                errs.append(f"{DIR_NAME}/{p.name}:{n}: 1 項を 1 行で `- ` から書く（続きの行・見出し・空白で始まる行は書かない）")
    errs += 取り残し(root) or []
    return errs


def 取り残し(root: Path = ROOT, base: str = "origin/main") -> list[str] | None:
    """一番新しい版の節より前に main（base の first-parent の並び）へ入った断片が、節に入らず残っていれば誤りを返す。
    照らせない（git でない・履歴が浅い・base が無い）なら None（照らしたとは言わない＝呼ぶ側が試験で赤か skip にする）。
    main の同じ commit で入った節と断片（履歴を 1 つに畳んだ公開の写し）は並びが分からないので赤にしない。

    版を出す PR は枝を切った時の断片だけを束ねる。その後に main へ入った断片は、合流すると断片のまま残り、版の節に
    入らない（v0.39.0 の版を出す PR のレビュー・原因の台帳）。断片と節の見出しが main へ入った commit を main の並びで比べ、
    節より新しい断片だけを通す（次の版の物）。main にまだ無い物（今の枝で足した物）は一番新しい側に置く＝合流した時の並び。
    並びは今の枝でなく main で取る: 枝の側の並びで見ると、版の枝へ main を取り込んだ時は main の断片が枝の取り込みの
    commit で足された事になり見逃し、ふつうの枝へ版の後の main を取り込んだ時は自分の断片が節より古く見えて誤って赤にする。"""
    if _git(root, "rev-parse", "--is-inside-work-tree").returncode != 0:
        return None
    if _git(root, "rev-parse", "--is-shallow-repository").stdout.strip() != "false":
        return None
    if _git(root, "rev-parse", "--verify", "-q", f"{base}^{{commit}}").returncode != 0:
        return None
    main = root / "CHANGELOG.md"
    m = next((VERSION_HEAD_RE.match(l) for l in main.read_text(encoding="utf-8").splitlines() if VERSION_HEAD_RE.match(l)), None) \
        if main.is_file() else None
    if m is None:
        return []
    並び = {sha: i for i, sha in enumerate(_git(root, "rev-list", "--first-parent", base).stdout.split())}

    def 位置(*args: str) -> int:
        """その変更を main へ入れた commit の位置（0 が一番新しい）。main に無ければ -1（一番新しい側＝合流した時の並び）。"""
        shas = [s for s in _git(root, "log", "--first-parent", "--diff-merges=first-parent", "--format=%H", base, *args).stdout.split()
                if s in 並び]
        return 並び[shas[-1]] if shas else -1

    見出し = m.group(0)
    節 = 位置("-S", 見出し, "--", "CHANGELOG.md") if 見出し in _git(root, "show", f"{base}:CHANGELOG.md").stdout.splitlines() else -1
    errs = []
    for p in fragments(root):
        rel = str(p.relative_to(root))
        断 = 位置("--diff-filter=A", "-1", "--", rel) if _git(root, "cat-file", "-e", f"{base}:{rel}").returncode == 0 else -1
        if 断 > 節 or 断 == 節 == -1:  # main の同じ commit で入った節と断片は並びが分からない（1 つに畳んだ写し）＝赤にしない
            errs.append(f"{DIR_NAME}/{p.name}: 版 {m.group(1)} の節より前に main へ入った断片が、節に入らず残る（版を出す枝を切った後に"
                        f"入った断片。main を取り込み、この断片の行を版の節へ移して断片を消す）")
    return errs


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=off", *args], capture_output=True, text=True)


def ordered(root: Path = ROOT, ref: str = "HEAD") -> list[Path]:
    """断片を main に入った順の新しい物が上で並べる（ref の first-parent でその file が足された commit の時刻。
    まだ commit していない断片は一番上・同じ時は名の逆順）。git が無い・読めない時は名の逆順。"""
    rows = []
    for p in fragments(root):
        r = _git(root, "log", "--first-parent", "--diff-merges=first-parent", "--no-patch", "--diff-filter=A", "--format=%ct",
                 ref, "--", str(p.relative_to(root)))
        ts = r.stdout.split()
        key = int(ts[-1]) if r.returncode == 0 and ts else float("inf")
        rows.append((key, p.name, p))
    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
    return [p for _, _, p in rows]


def gathered_lines(root: Path = ROOT, ref: str = "HEAD") -> list[str]:
    """未リリースの断片の行の全部（新しい断片が上・断片の中の並びはそのまま）。"""
    out: list[str] = []
    for p in ordered(root, ref):
        out += [l.rstrip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return out


def _働けない(訳: str) -> None:
    """使い方の誤り・読めない元＝道具が働けない。終わりの値 2（1 の「赤・止めた」と混ぜない）で抜ける。"""
    print(f"✗ {訳}", file=sys.stderr)
    raise SystemExit(2)


def with_unreleased(text: str, lines: list[str]) -> str:
    """CHANGELOG.md の文の「未リリース」の決まった 1 行を、断片の行に置き替えた文（照らし・版の節を作る元）。"""
    return text.replace(f"{UNRELEASED_HEAD}\n{UNRELEASED_TEXT}\n", f"{UNRELEASED_HEAD}\n" + "".join(l + "\n" for l in lines), 1)


def release(version: str, date: str, root: Path = ROOT) -> str:
    """断片を束ねて版の節を「未リリース」の下に作り、断片を消す。作った節の見出しを返す。"""
    if not re.fullmatch(r"v\d+\.\d+\.\d+", version) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        _働けない("版は vX.Y.Z・日は YYYY-MM-DD")
    errs = check(root)
    if errs:
        raise SystemExit("形が赤のまま版を作らない:\n" + "\n".join(errs))
    lines = gathered_lines(root)
    if not lines:
        raise SystemExit("未リリースの断片が無い（出す物が無い）")
    main = root / "CHANGELOG.md"
    text = main.read_text(encoding="utf-8")
    head = f"## [{version}] - {date}"
    if head in text or f"## [{version}]" in text:
        raise SystemExit(f"{version} の節は既に在る")
    old = f"{UNRELEASED_HEAD}\n{UNRELEASED_TEXT}\n"
    new = f"{old}\n{head}\n" + "".join(l + "\n" for l in lines)
    main.write_text(text.replace(old, new, 1), encoding="utf-8")
    for p in fragments(root):
        p.unlink()
    return head


def adopt(source_text: str, target: Path, root: Path = ROOT, base: str = "origin/main") -> list[str]:
    """古い形の CHANGELOG.md（source_text）の「未リリース」の行で、取り込む先 base（既定 origin/main）の CHANGELOG.md と
    断片（base の CHANGELOG.d/ と作業中の CHANGELOG.d/）のどこにも無い物を target の頭へ足す。足した行を返す。

    「すでに在る行」は作業中の CHANGELOG.md から読まない: main を取り込んでぶつかった途中の CHANGELOG.md には、ぶつかった印の
    内側に自分の行がまだ残るので、全部を「すでに在る」と見なして 0 行しか移さず、行が黙って消える（#280 のレビュー）。
    base が読めない時と、作業中の断片にぶつかった印が残る時は止める（黙って進まない）。"""
    body = unreleased_body(source_text) or ""
    r = _git(root, "show", f"{base}:CHANGELOG.md")
    if r.returncode != 0:
        _働けない(f"取り込む先 {base} の CHANGELOG.md を読めない（git fetch origin main をしてから回す・別の先は 3 つ目の引数）: "
                f"{r.stderr.strip()[:200]}")
    have = set(r.stdout.splitlines())
    names = _git(root, "ls-tree", "--name-only", f"{base}:{DIR_NAME}")
    for name in names.stdout.splitlines() if names.returncode == 0 else []:
        if name != "README.md":
            have.update(l.rstrip() for l in _git(root, "show", f"{base}:{DIR_NAME}/{name}").stdout.splitlines())
    for p in fragments(root):
        text = p.read_text(encoding="utf-8")
        if re.search(r"^(<{7}|={7}|>{7})( |$)", text, re.M):
            raise SystemExit(f"{DIR_NAME}/{p.name} にぶつかった印が残る（先にぶつかりを解く）")
        have.update(l.rstrip() for l in text.splitlines())
    new = [l.rstrip() for l in body.splitlines() if l.startswith("- ") and l.rstrip() not in have]
    if new:
        old = target.read_text(encoding="utf-8") if target.exists() else ""
        target.write_text("\n".join(new) + "\n" + old, encoding="utf-8")
    return new


USAGE = "使い方: changelog.py ／ changelog.py check ／ changelog.py 版 vX.Y.Z YYYY-MM-DD ／ changelog.py adopt <古い形の CHANGELOG.md|-> <断片の file> [<取り込む先・既定 origin/main>]"


def main(argv: list[str]) -> int:
    a = argv[1:]
    if a == []:
        for line in gathered_lines():
            print(line)
        return 0
    if a == ["check"]:
        errs = check()
        for e in errs:
            print(e)
        print("changelog: 赤" if errs else "changelog: 緑")
        return 1 if errs else 0
    if len(a) == 3 and a[0] == "版":
        print(f"changelog: {release(a[1], a[2])} を作り、断片を消した")
        return 0
    if len(a) in (3, 4) and a[0] == "adopt":
        src = sys.stdin.read() if a[1] == "-" else Path(a[1]).read_text(encoding="utf-8")
        moved = adopt(src, Path(a[2]), base=a[3] if len(a) == 4 else "origin/main")
        print(f"changelog: {len(moved)} 行を {a[2]} へ移した")
        for line in moved:
            print(f"  {line[:80]}")
        return 0
    print(USAGE, file=sys.stderr)  # 知らない口は既定で止める（一覧へ落として緑で返さない）
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception as e:  # 道具そのものが壊れた＝終わりの値 2（1 の「見つかった・赤」と混ぜない）
        import traceback
        traceback.print_exc()
        print(f"✗ 道具が壊れた（版の記録の道具 changelog.py・終わりの値 2＝結果ではない）: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
