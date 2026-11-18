#!/usr/bin/env python3
"""給与エージェントの決まり（同じ plugin の 決まり.md）を窓の起動時に差し込む口。

使い方:
  python3 差し込む.py inject   SessionStart の hook が呼ぶ。決まり.md を窓の文脈へ差し込む。
  python3 差し込む.py check    決まり.md が上限の内か・読めるかを照らす（0=緑 / 1=上限を越えた / 2=読めない）。
inject は何が起きても 0 で抜ける（窓の起動を止めない）。読めない時は stderr に訳を出す。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
決まり = PLUGIN / "決まり.md"
# 常に読まれる量の上限（バイト・UTF-8）。数はここの 1 か所だけに置く。
上限 = 4800


def 差し込む文() -> str:
    text = 決まり.read_text(encoding="utf-8").rstrip("\n")
    return (text + "\n\n"
            + f"（この決まりは payroll-agent の plugin が起動時に差し込んだ。手順は skill payroll-steps、口の一覧は {PLUGIN / '口の一覧.md'}）\n")


def inject() -> int:
    try:
        text = 差し込む文()
    except OSError as e:
        print(f"payroll-agent: 決まり.md が読めない（{e}）＝決まりは差し込まれていない", file=sys.stderr)
        return 0
    out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


def check() -> int:
    try:
        n = len(決まり.read_text(encoding="utf-8").encode("utf-8"))
    except OSError as e:
        print(f"✗ 決まり.md が読めない: {e}")
        return 2
    if n > 上限:
        print(f"✗ 決まり.md が上限を越えた: {n} > {上限} バイト（手順は skill へ移す）")
        return 1
    print(f"✓ 決まり.md {n} バイト（上限 {上限}）")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "inject":
        sys.exit(inject())
    if cmd == "check":
        sys.exit(check())
    print(__doc__, file=sys.stderr)
    sys.exit(2)
