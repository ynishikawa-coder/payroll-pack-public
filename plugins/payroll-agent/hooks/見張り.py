#!/usr/bin/env python3
"""PreToolUse hook の入口。止めるのは 1 つだけ: GitHub の道具（mcp__github__*）と add_repo（mcp__claude-code-remote__add_repo）を、
引数の repo の名が payroll-pack か payroll-pack-public の時に止める（給与の窓はパックの repo を触らない。パックを直すのは開発の窓）。
名は owner の有無（`owner/repo`・owner と repo の別の引数）と大文字小文字を問わない。命令の文（Bash）は読まない。
Drive・シートの書き込みは止めない（出す物と管理表はパックの 1 命令 出口/出す.py が書き、AI が直に直してもよい）。
ほかに、オーナーへの選択肢の画面（AskUserQuestion）の文を照らして知らせる（止めない）。
入力が読めない時は止める（見分けられない＝止める側）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
sys.path.insert(0, str(BIN))
# 部品の読み込みも捕まえる（try の外で落ちると終わりの値 1＝Claude Code は止めない誤りとして道具の呼び出しを通す）。
_読めない: dict[str, str] = {}


def _部品(名: str):
    try:
        return __import__(名)
    except Exception as e:  # noqa: BLE001
        _読めない[名] = f"{type(e).__name__}: {e}"
        return None


場所 = _部品("パックの場所")
オーナーへの文 = _部品("オーナーへの文の照らし")

止める_repo = ("payroll-pack", "payroll-pack-public")
_repo_の鍵 = ("repo", "repository", "repo_name", "full_name", "name_with_owner")


def 見る道具か(tool: str) -> bool:
    return tool.startswith("mcp__github__") or tool == "mcp__claude-code-remote__add_repo"


def 止める_repo_の名(args: dict) -> str | None:
    """引数の repo の名（owner の有無・大文字小文字を問わない）が止める repo なら、その名を返す。"""
    for k in _repo_の鍵:
        v = args.get(k)
        if not isinstance(v, str):
            continue
        名 = v.strip().rstrip("/").rsplit("/", 1)[-1].lower()
        if 名.endswith(".git"):
            名 = 名[:-4]
        if 名 in 止める_repo:
            return 名
    return None


def _拒む(訳: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": 訳}}, ensure_ascii=False))


def _知らせる(訳: list[str]) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext":
                      "給与の見張り（知らせるだけ・止めない。決まりの正本は payroll-agent の 決まり.md「聞く」）: "
                      + " ／ ".join(訳) + "。答えを受けたら、同じ問いを直した文で出し直さず、決まりのとおり扱う"}},
                     ensure_ascii=False))


def main(stdin=None) -> int:
    try:
        ev = json.load(stdin or sys.stdin)
        if not isinstance(ev, dict):
            raise ValueError("JSON の物でない")
    except ValueError:
        _拒む("給与の見張りの hook が入力を読めない＝見分けられないので止めた。もう一度打つ。続くなら plugin payroll-agent の hooks を見る")
        return 0
    tool = str(ev.get("tool_name", ""))
    if tool == "AskUserQuestion":   # オーナーへの選択肢の画面の文: 種類の印の無い問い・番号だけの頼み・担当者へ聞く物を知らせる（止めない）
        try:
            if 場所 is None or オーナーへの文 is None:
                raise RuntimeError("部品を読めない: " + "・".join(f"{k}（{v}）" for k, v in _読めない.items()))
            パック = 場所.探す()
            try:
                形たち = 場所.番号の形たち(パック) if パック else None
            except Exception:  # noqa: BLE001  読めない＝番号は照らせないと知らせる（止めない）
                形たち = None
            args = ev.get("tool_input") or {}
            訳 = (オーナーへの文.印を照らす(args, オーナーへの文.許す印たち())
                 + オーナーへの文.照らす(オーナーへの文.選択肢の画面の文(args), 形たち, パック is not None))
        except Exception as e:  # noqa: BLE001  照らしが壊れた＝この問いは照らしていないと知らせる（この口は止めない）
            訳 = [f"給与の見張りが壊れた（オーナーへの文の照らし・{type(e).__name__}: {e}）＝この問いは照らしていない。plugin payroll-agent を直す"]
        if 訳:
            _知らせる(訳)
        return 0
    if not 見る道具か(tool):
        return 0
    args = ev.get("tool_input")
    if not isinstance(args, dict):
        _拒む(f"給与の見張り: {tool} の引数を読めない＝repo を見分けられないので止めた")
        return 0
    名 = 止める_repo_の名(args)
    if 名:
        _拒む(f"給与の見張り: 給与の窓は repo {名} を GitHub の道具・add_repo で触らない（{tool}）。"
             "パックを直すのは開発の窓（payroll-pack の枝と PR）。給与の仕事は版の印のパックの命令と Drive の口で進める")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 捕まえ残しも 1（止めない誤り）で抜けない: 2＝Claude Code は道具の呼び出しを止め、訳を窓へ渡す
        import traceback
        traceback.print_exc()
        print(f"✗ 道具が壊れた（給与の見張りの hook 見張り.py・終わりの値 2＝結果ではない）: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
