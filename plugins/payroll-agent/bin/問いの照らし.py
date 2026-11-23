#!/usr/bin/env python3
"""問いの照らし（給与エージェント）— 事務所の担当者へ出す問いを、質問と回答の答え済みと照らす。芯はパックの `確認ページ/前の答え.py`。

ここは照らしを写さない: 殻（各社のエージェント）が質問と回答のタブ 質問 を読んで file に置き、その path を渡す。
パックの dir を見つけ、前の答えの口へ同じ引数と標準入力で渡し、出力と exit をそのまま返す。
使い方: python3 問いの照らし.py --rows <質問の表の JSON> [--company <会社>] [--questions <1 行 1 問の file>] [--パック <dir>]
  標準入力は qa-prior/1（確認ページの検査の --prior-input の出力）。--questions の時は読まない。
パックの場所が分からない・その版に前の答えの口が無い・表が渡されない時は、照らせない＝exit 2（黙って通さない）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import パックの場所 as 場所  # noqa: E402

前の答えの口 = Path("確認ページ") / "前の答え.py"


def main(argv: list[str], runner=subprocess.run, stdin=None) -> int:
    argv = list(argv)
    パック引数 = None
    if "--パック" in argv:
        i = argv.index("--パック")
        パック引数 = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    if "--rows" not in argv:
        print("質問と回答の表が渡されない（殻がタブ 質問 を読んで file に置き、--rows で渡す）＝照らせない", file=sys.stderr)
        return 2
    パック = 場所.探す(パック引数)
    if パック is None:
        print(場所.分からない訳("前の答えを照らす口を読めないので照らせない", パック引数), file=sys.stderr)
        return 2
    if not (パック / 前の答えの口).is_file():
        print(f"パック {パック} の版に前の答えを照らす口（{前の答えの口}）が無い＝照らせない（その口の在る版のパックを使う）", file=sys.stderr)
        return 2
    feed = None if "--questions" in argv else (stdin if stdin is not None else sys.stdin.read())
    r = runner([sys.executable, str(パック / 前の答えの口), *argv], input=feed, capture_output=True, text=True)
    sys.stdout.write(r.stdout or "")
    sys.stderr.write(r.stderr or "")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
