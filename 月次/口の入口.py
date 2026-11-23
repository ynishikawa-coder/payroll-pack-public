"""判断の口（殻が `python3 <file> <口> < 入力.json` で呼ぶ物）の入口の 1 つ。拒むの約束をここだけが持つ。

約束: 返りは JSON 1 つ。入力が JSON でない・形が崩れた・口の中で読めない物に当たった時は、どの例外でも
{"拒む": 訳} と終わりの値 2（殻は訳のまま止める）。traceback と終わりの値 1 で抜ける道を持たない。
判断の赤は口が {"赤": [...]} で返す（終わりの値 0）。

  from 月次.口の入口 import 拒む, 回す
  if __name__ == "__main__":
      回す(_口)
"""
import json
import sys


class 拒む(Exception):
    """入力の形が崩れた（判断の赤ではない）。"""


def 拒む訳(e: BaseException) -> str:
    """例外を拒むの訳に。口が決めた 拒む は訳のまま、それ以外は形が崩れた訳に型の名を添える。"""
    if isinstance(e, 拒む):
        return str(e)
    if isinstance(e, json.JSONDecodeError):
        return f"入力が JSON でない（{e.msg}・{e.lineno} 行 {e.colno} 字）"
    return f"入力の形が崩れた＝読めない（{type(e).__name__}: {e}）"


def 回す(口, argv=None, stdin=None, stdout=None) -> int:
    """argv[1] の口を stdin の JSON で回し、返りを stdout へ。拒む時は終わりの値 2 で抜ける。"""
    argv = sys.argv if argv is None else argv
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    try:
        out = 口(argv[1] if len(argv) > 1 else "", json.load(stdin))
        text = json.dumps(out, ensure_ascii=False, indent=1)
    except Exception as e:   # 既定で止める＝どの崩れも拒むの約束で返す
        json.dump({"拒む": 拒む訳(e)}, stdout, ensure_ascii=False)
        stdout.write("\n")
        sys.exit(2)
    stdout.write(text + "\n")
    return 0
