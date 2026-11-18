#!/usr/bin/env python3
"""PreToolUse hook の入口: 止める見張り（../bin/止める見張り.py）の判定を呼び、止める時だけ deny を返す。判定はここに書かない。

殻（各社のエージェント）が環境で渡す口:
  PAYROLL_PACK_DIR            パックの dir（出す物の名の頭と確認ページの名の形を読む。無ければ plugin の上を辿る）
  PAYROLL_GUARD_LOOKUP_CMD    名を引く命令。`<命令> 名 <id>` → JSON {"name", "appProperties", "見えない"?}・
                              `<命令> 見出し <id> <タブ>` → JSON の 1 行目。0 でない終わり＝引けない（止める側）
  PAYROLL_SHIP_MARK           出荷の口が置いた本の印（appProperties の鍵）。無ければ名の頭だけで見る
  PAYROLL_GUARD_REPLACE_CMDS  Bash で `<命令> replace <id>` と打つと Drive の本を置き換える命令の名（読点か , 区切り）
入力が読めない・パックの場所が分からない時、見る道具なら止める（見分けられない＝止める側）。見ない道具は何もしない。
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
sys.path.insert(0, str(BIN))
import パックの場所 as 場所  # noqa: E402
import 止める見張り as 見張り  # noqa: E402

なぜ = ("給与の出す物の本と管理表の今の版は、パックの出口が作り証明を付けた表だけを、出荷の口が書く"
       "（出す前の照らしを通す）。{what}。上流（マスタ・決まりの台帳・パック）を直して出口で作り直し、出荷の口で出す")


def _引く(*args: str):
    cmd = os.environ.get("PAYROLL_GUARD_LOOKUP_CMD", "").strip()
    if not cmd:
        raise RuntimeError("PAYROLL_GUARD_LOOKUP_CMD が無い")
    r = subprocess.run([*shlex.split(cmd), *args], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200] or f"終わりの値 {r.returncode}")
    return json.loads(r.stdout)


def 口を組む(パック: Path) -> 見張り.口:
    return 見張り.口(
        名の頭たち=場所.名の頭たち(パック),
        名を引く=lambda fid: _引く("名", fid),
        見出しを引く=lambda sid, tab: _引く("見出し", sid, tab),
        印=os.environ.get("PAYROLL_SHIP_MARK", ""),
        置き換える命令=tuple(x.strip() for x in re.split(r"[,、]", os.environ.get("PAYROLL_GUARD_REPLACE_CMDS", "")) if x.strip()),
        確認ページの形=場所.確認ページの名の形(パック),
    )


def _拒む(訳: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": 訳}}, ensure_ascii=False))


def main(stdin=None) -> int:
    try:
        ev = json.load(stdin or sys.stdin)
        if not isinstance(ev, dict):
            raise ValueError("JSON の物でない")
    except ValueError:
        _拒む("給与の見張りの hook が入力を読めない＝見分けられないので止めた。もう一度打つ。続くなら plugin payroll-agent の hooks を見る")
        return 0
    tool = str(ev.get("tool_name", ""))
    if not 見張り.見るか(tool):
        return 0
    パック = 場所.探す()
    if パック is None:
        if tool == "Bash" and "replace" not in str((ev.get("tool_input") or {}).get("command", "")):
            return 0
        _拒む("給与の見張り: パックの場所が分からない（環境 PAYROLL_PACK_DIR）＝出す物の名の形を読めないので書く道具を止めた")
        return 0
    try:
        what = 見張り.判定(tool, ev.get("tool_input") or {}, 口を組む(パック))
    except Exception as e:  # noqa: BLE001  判定が落ちた＝見分けられない＝止める
        what = f"見張りの判定が落ちた（{type(e).__name__}: {e}）"
    if what:
        _拒む(なぜ.format(what=what))
    return 0


if __name__ == "__main__":
    sys.exit(main())
