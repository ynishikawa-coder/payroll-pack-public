#!/usr/bin/env python3
"""穴の照らし（給与エージェント）— 引き継ぎ・返し・月の本文に「穴」「表せない」「直されていない」と書いた行が課題の行に
なっているか、会社に開いた課題が残っていないかを照らす判定。

なぜ在るか（根治・2026-11-17）: パックが表せない決まりが引き継ぎに文で書かれただけで、計算は止まらず違う形で数えた。
  穴は文で終わらせず課題の行にし、開いた課題・起票していない穴のある会社の月は 出す前の照らし.py が通さない。
  課題の行を読む・立てる手（記録の置き場）は各社のエージェントが持ち、読んだ行をここへ渡す。

使い方:
  python3 穴の照らし.py 拾う <file|->                      # 穴の語を書いた行を出す（引き継ぎを書く前の点検）
  python3 穴の照らし.py 照らす <材料.json> --支給月 <YYYY.MM支給>
      材料: {"課題": [{"題", "状態", "url", "id"}], "課題の id": [...], "閉じた状態": [...], "月の本文", "読めない": [...]}
      開いた課題と起票していない穴を出す。1 つでもあれば exit 2（出す前の照らしと同じ判定）
  python3 穴の照らし.py 起票の案 <材料.json> --支給月 <…>   # 起票していない穴ごとに、課題の行の題と月の本文へ足す行の雛形
Python 3 の標準ライブラリだけ。外を開かない。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

穴の語 = ("穴", "表せない", "直されていない")
課題の頭 = "課題:"
# 穴の語を含むが穴そのものでない仕組みの名（見出し・窓の題に出る）。照らす前に字から外す。
仕組みの名 = ("穴の起票", "穴の照らし", "穴の語", "穴の行")
_月の字 = re.compile(r"\d{4}[./年-]\s*\d{1,2}")


def 穴の語がある(行: str) -> bool:
    for n in 仕組みの名:
        行 = 行.replace(n, "")
    return any(w in 行 for w in 穴の語)


def 拾う(字: str) -> list[str]:
    return [x.strip() for x in 字.splitlines() if x.strip() and 穴の語がある(x)]


def _ならす(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _id(s: str) -> str:
    return str(s).replace("-", "").lower()


def _引く_id(行: str, ids: set[str]) -> set[str]:
    """行の中に在る課題の id（ハイフンの有無を問わない）。リンクの形（どの記録の置き場か）は見ない。"""
    flat = _id(行)
    return {i for i in ids if i and i in flat}


def 起票していない穴(字: str, 課題の_id: set[str]) -> list[str]:
    """穴の語を含む行のうち、課題の行（課題の_id のどれか・開いた物も閉じた物も）を指していない行。
    起票の行（`- 課題 <リンク>: 「<穴の行の頭>」`）がその行を引いていれば起票済み。"""
    ids = {_id(i) for i in 課題の_id if str(i).strip()}
    lines = [x.strip() for x in 字.splitlines() if x.strip()]
    結んだ = [_ならす(x) for x in lines if _引く_id(x, ids)]
    out = []
    for s in lines:
        if not 穴の語がある(s) or _引く_id(s, ids):
            continue
        頭 = _ならす(re.sub(r"https?://\S+", "", s)).lstrip("-・*")[:40]
        if 頭 and any(頭 in x and x != _ならす(s) for x in 結んだ):
            continue
        out.append(s[:160])
    return out


def 開いた課題(課題: list[dict], 支給月: str, 閉じた状態) -> list[dict]:
    """題が `課題:` で始まり、状態が閉じていない課題のうち、題にその支給月か「全月」を含むか、月の無い題（全月として数える＝止める側）。"""
    閉じた = set(閉じた状態 or ())
    out = []
    for r in 課題 or ():
        題, 状態 = str(r.get("題", "")), str(r.get("状態", ""))
        if not 題.startswith(課題の頭) or 状態 in 閉じた:
            continue
        if 支給月 not in 題 and "全月" not in 題 and _月の字.search(題):
            continue
        out.append({"題": 題, "状態": 状態, "url": r.get("url", "")})
    return out


def 課題と穴の赤(材料: dict, 支給月: str) -> list[str]:
    """出す前の照らしの 6・7。材料が欠けた時は照らせない＝赤。"""
    赤 = []
    無い = [k for k in ("課題", "課題の id", "閉じた状態", "月の本文") if 材料.get(k) is None]
    if 無い:
        return [f"課題と穴を照らせない（材料に {'・'.join(無い)} が無い）＝通さない"]
    if not 材料.get("閉じた状態"):
        return ["課題と穴を照らせない（閉じた状態 が空＝どの課題が閉じたか分からない）＝通さない"]
    for i in 開いた課題(材料["課題"], 支給月, 材料["閉じた状態"]):
        赤.append(f"開いた課題がある: {i['題']}（{i['状態']}・{i['url']}）＝閉じるまで出さない")
    for 行 in 起票していない穴(str(材料["月の本文"]), set(map(str, 材料["課題の id"]))):
        赤.append(f"起票していない穴（月の本文）: 「{行}」＝穴の照らし.py 起票の案 で課題の行を立て、行にリンクを足す")
    return 赤


def 起票の案(穴たち: list[str], 支給月: str) -> list[dict]:
    out = []
    for h in 穴たち:
        頭 = re.sub(r"https?://\S+", "", h).strip().lstrip("-・* ")[:60]
        out.append({"題": f"{課題の頭} {支給月} {頭[:40]}",
                    "本文": f"穴の行（月の本文から）: 「{h}」\n直し方: パックの枝と PR で表せるようにし、版の印の後にその会社の例を通す。",
                    "月の本文に足す行": f"- 課題 <課題の行の URL>: 「{頭}」"})
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("拾う", "照らす", "起票の案"):
        print(__doc__.split("使い方:")[1].split("Python 3")[0], file=sys.stderr)
        return 2
    src = sys.stdin.read() if argv[1] == "-" else Path(argv[1]).read_text(encoding="utf-8")
    if argv[0] == "拾う":
        for h in 拾う(src):
            print(h)
        return 0
    if "--支給月" not in argv or argv.index("--支給月") + 1 >= len(argv):
        print("--支給月 が要る", file=sys.stderr)
        return 2
    月 = argv[argv.index("--支給月") + 1]
    材料 = json.loads(src)
    if argv[0] == "照らす":
        赤 = 課題と穴の赤(材料, 月)
        print(json.dumps({"通す": not 赤, "赤": 赤}, ensure_ascii=False, indent=1))
        return 2 if 赤 else 0
    穴たち = 起票していない穴(str(材料.get("月の本文", "")), set(map(str, 材料.get("課題の id") or ())))
    print(json.dumps(起票の案(穴たち, 月), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
