#!/usr/bin/env python3
"""取り込みの照らし — 枝の取り込み（merge の commit）が、片側の行を黙って落としていないかを見る。

防ぐ故障: 積んだ枝の base の PR が squash で main に入った後、枝へ main を取り込む窓が、ぶつかった file を枝の側で取る。
枝が持っていたのは base の古い先端なので、base がその後に取り込んだ main の行が、誰も消すと決めていないのに落ちる
（法の表.md の 1 行が落ち、試験は緑のままだった・原因の台帳 420a40dc…81e9a178）。
人が「main と base の先端が同じ」を確かめる手順に頼らず、取り込みの commit そのものを機械で照らす。

照らし方: 2 つの親を持つ取り込みの commit M・親 A・B・その分かれ目 O（merge-base）について、file ごとに
  「A に在って M に無い行」は「B が O から消した行」でなければならない（A と B を入れ替えても同じ）。
片側の行が M から消えたのに、もう片側の枝がその行を消していない＝取り込みで黙って落ちた行＝赤。
行は字のまま数で照らす（同じ字の行が 2 つ落ちれば 2 つ数える・行を動かしただけ・空白だけの行は数えない）。中身が字でない file は、変わったのに相手の枝が
変えていなければ赤。照らすのは file の名ごと。取り込みの commit の中で別の file へ動かした行（取り込みそのものが別の file に
足した同じ字の行）は落ちたと数えない（例 CHANGELOG.md の行を断片へ移す）。

わざと落とした行（ぶつかりを手で合わせ、片側の行を書き直した・消した）は、取り込みの commit の文に
`取り込みで捨てた行: <file の path>` を 1 行ずつ書く（取り込みの commit を書き直せない時は、同じ範囲の後の commit の文に書く）。その file の落ちた行は赤にせず「捨てた」と出す（黙って通さない）。

使い方:
  python3 scripts/取り込みの照らし.py [<base>] [<先端>]
      # base..先端 の取り込みの commit を全部照らす。既定は origin/main と HEAD
      #（git merge origin/main の後にそのまま回す・試験 tests/test_取り込みの照らし.py が CI で同じ範囲を回す）
終わりの値: 0 緑（落ちた行が無い）／1 赤（黙って落ちた行が在る）／2 道具が働けない（git が読めない・commit が無い・
道具が壊れた＝結果ではない）。
"""
from __future__ import annotations

import subprocess
import sys
from collections import Counter

捨てた印 = "取り込みで捨てた行:"


class 働けない(Exception):
    pass


def _git(*args: str, cwd: str | None = None, 字で: bool = True) -> str | bytes:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if r.returncode != 0:
        raise 働けない(f"git {' '.join(args)}: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode("utf-8") if 字で else r.stdout


def _中身(rev: str, path: str, cwd: str | None) -> bytes | None:
    """rev の path の中身。無い file は None。"""
    r = subprocess.run(["git", "cat-file", "-e", f"{rev}:{path}"], cwd=cwd, capture_output=True)
    if r.returncode != 0:
        return None
    return _git("cat-file", "blob", f"{rev}:{path}", cwd=cwd, 字で=False)


def _行(b: bytes | None) -> list[str] | None:
    """字の file なら行の列。無い file は []。字でない（NUL を含む・utf-8 で読めない）なら None。"""
    if b is None:
        return []
    if b"\0" in b:
        return None
    try:
        return b.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return None


def _消えた行(前: list[str], 後: list[str]) -> Counter:
    """前より後で数の減った行（字のまま数で比べる＝行を動かしただけなら減らない）。空白だけの行は数えない。"""
    前の数 = Counter(l for l in 前 if l.strip())
    後の数 = Counter(l for l in 後 if l.strip())
    return 前の数 - 後の数


def _捨てたと書いた(文: str) -> set[str]:
    return {l.split(":", 1)[1].strip() for l in 文.splitlines() if l.strip().startswith(捨てた印)}


def 照らす(m: str, cwd: str | None = None, 範囲で捨てた: set[str] = frozenset()) -> tuple[list[str], list[str]]:
    """取り込みの commit m を照らす。返す: (黙って落ちた行の知らせ, 捨てたと書いた行の知らせ)。
    範囲で捨てた: 同じ範囲の後の commit の文に書いた `取り込みで捨てた行:` の path（取り込みの commit の文を後から
    書き直せない＝強制の push をしない時に、後の commit で書く）。"""
    親 = _git("rev-list", "--parents", "-n", "1", m, cwd=cwd).split()[1:]
    if len(親) != 2:
        raise 働けない(f"{m[:12]} は親が 2 つの取り込みの commit でない（親 {len(親)} 個）")
    a, b = 親
    o = _git("merge-base", a, b, cwd=cwd).strip()
    捨てた = _捨てたと書いた(_git("log", "-1", "--format=%B", m, cwd=cwd)) | set(範囲で捨てた)

    落ちた: list[str] = []
    捨てた知らせ: list[str] = []
    for 片, 相手 in ((a, b), (b, a)):
        変わった = [p for p in _git("diff", "--name-only", "-z", "--no-renames", 片, m, cwd=cwd).split("\0") if p]
        file_ごと: list[tuple[str, Counter | str]] = []
        取り込みが足した: Counter = Counter()   # 取り込みの commit そのものが足した行（どちらの枝も足していない＝動かした先）
        for p in 変わった:
            片の中, m_中 = _中身(片, p, cwd), _中身(m, p, cwd)
            o_中, 相手の中 = _中身(o, p, cwd), _中身(相手, p, cwd)
            片の行, m_行, o_行, 相手の行 = map(_行, (片の中, m_中, o_中, 相手の中))
            if None in (片の行, m_行, o_行, 相手の行):
                # 字でない file: 片側から変わったのに、相手の枝が O から変えていない＝相手の側の変更でない
                if o_中 == 相手の中:
                    file_ごと.append((p, f"{p}: 字でない file が {片[:12]} の側から変わったが、{相手[:12]} の側はこの file を変えていない"))
                continue
            file_ごと.append((p, _消えた行(片の行, m_行) - _消えた行(o_行, 相手の行)))
            取り込みが足した += _消えた行(m_行, 片の行) - _消えた行(相手の行, o_行)
        for p, 残り in file_ごと:
            if isinstance(残り, str):
                知らせ = [残り]
            else:
                # 取り込みの中で別の file へ動かした行（例 CHANGELOG.md の行を断片へ移した）は落ちていない
                動かした = 残り & 取り込みが足した
                取り込みが足した -= 動かした
                残り = 残り - 動かした
                知らせ = [f"{p}: {片[:12]} の側の行が落ちた（{相手[:12]} の側は消していない）: {行!r}"
                         for 行, n in sorted(残り.items()) for _ in range(n)]
            if 知らせ:
                (捨てた知らせ if p in 捨てた else 落ちた).extend(知らせ)
    return 落ちた, 捨てた知らせ


def 範囲の取り込み(base: str, 先端: str, cwd: str | None = None) -> list[str]:
    """base..先端 の取り込みの commit（親が 2 つ以上）。古い順。"""
    return _git("rev-list", "--merges", "--reverse", f"{base}..{先端}", cwd=cwd).split()


def 走る(base: str, 先端: str, cwd: str | None = None) -> tuple[int, str]:
    行s: list[str] = []
    赤 = False
    ms = 範囲の取り込み(base, 先端, cwd)
    範囲で捨てた = _捨てたと書いた(_git("log", "--format=%B", f"{base}..{先端}", cwd=cwd)) if ms else set()
    for m in ms:
        落ちた, 捨てた = 照らす(m, cwd, 範囲で捨てた)
        題 = _git("log", "-1", "--format=%s", m, cwd=cwd).strip()
        for x in 落ちた:
            行s.append(f"✗ {m[:12]}（{題}）: {x}")
        for x in 捨てた:
            行s.append(f"知らせ {m[:12]}（{題}）: 取り込みで捨てたと書いた行: {x}")
        赤 = 赤 or bool(落ちた)
    if 赤:
        行s.append(f"赤: 取り込みで黙って落ちた行が在る（{base}..{先端}・取り込み {len(ms)} 個）。"
                  f"落ちた行を戻すか、わざと捨てたなら取り込みの commit の文に `{捨てた印} <file>` を書く")
        return 1, "\n".join(行s)
    行s.append(f"緑: 取り込みで黙って落ちた行は無い（{base}..{先端}・取り込み {len(ms)} 個）")
    return 0, "\n".join(行s)


def main(argv: list[str]) -> int:
    if len(argv) > 2 or any(a.startswith("-") for a in argv):
        print(__doc__.split("使い方:")[1].split("終わりの値")[0].strip(), file=sys.stderr)
        return 2
    base = argv[0] if argv else "origin/main"
    先端 = argv[1] if len(argv) > 1 else "HEAD"
    try:
        rc, 出す = 走る(base, 先端)
    except 働けない as e:
        print(f"✗ 照らせない（終わりの値 2＝結果ではない）: {e}", file=sys.stderr)
        return 2
    print(出す)
    return rc


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:  # noqa: BLE001 — 道具の故障は 2（赤の 1 と混ぜない）
        print(f"✗ 道具が壊れた（{type(e).__name__}: {e}・終わりの値 2＝結果ではない）", file=sys.stderr)
        sys.exit(2)
