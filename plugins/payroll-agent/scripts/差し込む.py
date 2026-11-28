#!/usr/bin/env python3
"""給与エージェントの決まり（同じ plugin の 決まり.md）を窓の起動時に差し込む口。

使い方:
  python3 差し込む.py inject   SessionStart の hook が呼ぶ。決まり.md を窓の文脈へ差し込む。
inject は何が起きても 0 で抜ける（窓の起動を止めない）。読めない・壊れた時は stderr に訳を出す。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
決まり = PLUGIN / "決まり.md"


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


def 走らせる(cmd: str) -> int:
    """口を回す。道具そのものが壊れても 0（窓の起動を止めない）。"""
    if cmd != "inject":
        print(__doc__, file=sys.stderr)
        return 2
    try:
        return inject()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"payroll-agent: 決まりを差し込む口が壊れた（{type(e).__name__}: {e}）＝決まりは差し込まれていない", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(走らせる(sys.argv[1] if len(sys.argv) > 1 else ""))
