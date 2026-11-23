#!/usr/bin/env python3
"""PreToolUse hook の入口: 止める見張り（../bin/止める見張り.py）の判定を呼び、止める時だけ deny を返す。判定はここに書かない。

殻（各社のエージェント）が環境で渡す口:
  PAYROLL_PACK_DIR            パックの dir（出す物の名の頭と確認ページの名の形を読む。無ければ plugin の上を辿り、plugin を入れた同じ版の目録の複製を使う）
  PAYROLL_GUARD_LOOKUP_CMD    名を引く命令。`<命令> 名 <id>` → JSON {"name", "appProperties", "見えない"?}・
                              `<命令> 見出し <id> <タブ>` → JSON の 1 行目。0 でない終わり＝引けない（止める側）
  PAYROLL_SHIP_MARK           出荷の口が置いた本の印（appProperties の鍵）。無ければ名の頭だけで見る
  PAYROLL_GUARD_REPLACE_CMDS  Bash で `<命令> replace <id>` と打つと Drive の本を置き換える命令の名（読点か , 区切り）
入力が読めない・パックの場所が分からない時、見る道具なら止める（見分けられない＝止める側）。ただし Bash は判定と同じ見分け
（置き換える命令の名の後の引数に replace・分けられない文）の時だけ止める。見ない道具は何もしない。
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
# 部品の読み込みも捕まえる（try の外で落ちると終わりの値 1＝Claude Code は止めない誤りとして道具の呼び出しを通す）。
# 読めない部品は None にし、main が道具ごとに「止める（見る道具）・知らせる（選択肢の画面・判定そのものが読めない）」へ分ける。
_読めない: dict[str, str] = {}


def _部品(名: str):
    try:
        return __import__(名)
    except Exception as e:  # noqa: BLE001
        _読めない[名] = f"{type(e).__name__}: {e}"
        return None


場所 = _部品("パックの場所")
見張り = _部品("止める見張り")
オーナーへの文 = _部品("オーナーへの文の照らし")

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


def _置き換える命令() -> tuple[str, ...]:
    return tuple(x.strip() for x in re.split(r"[,、]", os.environ.get("PAYROLL_GUARD_REPLACE_CMDS", "")) if x.strip())


def 口を組む(パック: Path) -> 見張り.口:
    return 見張り.口(
        名の頭たち=場所.名の頭たち(パック),
        名を引く=lambda fid: _引く("名", fid),
        見出しを引く=lambda sid, tab: _引く("見出し", sid, tab),
        印=os.environ.get("PAYROLL_SHIP_MARK", ""),
        置き換える命令=_置き換える命令(),
        確認ページの形=場所.確認ページの名の形(パック),
        守るタブ=_読めれば(場所.守るタブたち, パック, ()),
        字=_読めれば(場所.字の口, パック, None),
    )


def _読めれば(読む, パック: Path, 無い時):
    """読めない版のパックでは 無い時 の値（空・None）を渡す＝判定がその物を見分けられないと名指しして止める。"""
    try:
        return 読む(パック)
    except Exception:  # noqa: BLE001
        return 無い時


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
    if 見張り is None:   # 見る道具かを見分ける判定そのものが読めない＝止めずに、照らしていないと知らせる（全部の道具を止める事はオーナーの判断の行）
        _知らせる([f"給与の見張りが壊れた（止める見張りを読めない・{_読めない.get('止める見張り', '')}）＝この道具の呼び出しは照らしていない。plugin payroll-agent を直す"])
        print("✗ 道具が壊れた（給与の見張りの hook・止める見張りを読めない）＝照らしていない", file=sys.stderr)
        return 0
    if not 見張り.見るか(tool):
        return 0
    try:
        if 場所 is None:
            raise RuntimeError("パックの場所を読めない: " + _読めない.get("パックの場所", ""))
        パック = 場所.探す()
    except Exception as e:  # noqa: BLE001  見る道具で場所を探せない＝見分けられない＝止める（下の「パックの場所が分からない」と同じ側）
        _拒む(f"給与の見張りが壊れた（{type(e).__name__}: {e}）＝見分けられないので書く道具を止めた。plugin payroll-agent を直す")
        return 0
    if パック is None:
        if tool == "Bash":   # 判定と同じ見分け（置き換える命令の名の直後が replace の時・分けられない文）だけ止める
            try:
                if not 見張り.置き換える先たち(str((ev.get("tool_input") or {}).get("command", "")), _置き換える命令()):
                    return 0
            except ValueError:
                pass
        _拒む("給与の見張り: " + 場所.分からない訳("出す物の名の形を読めないので書く道具を止めた"))
        return 0
    try:
        what = 見張り.判定(tool, ev.get("tool_input") or {}, 口を組む(パック))
    except Exception as e:  # noqa: BLE001  判定が落ちた＝見分けられない＝止める
        what = f"見張りの判定が落ちた（{type(e).__name__}: {e}）"
    if what:
        _拒む(なぜ.format(what=what))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 捕まえ残しも 1（止めない誤り）で抜けない: 2＝Claude Code は道具の呼び出しを止め、訳を窓へ渡す
        import traceback
        traceback.print_exc()
        print(f"✗ 道具が壊れた（給与の見張りの hook 見張り.py・終わりの値 2＝結果ではない）: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
