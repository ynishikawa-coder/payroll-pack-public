#!/usr/bin/env python3
"""決まりのmdを書き換える — 答えの書き戻しが返した「md を書き換える」手順を、会社の 1_決まり の md（給与のルール.md・
作業のルール.md）へ 1 つの命令で当てる口（パックが自分で Drive を開く。殻は Drive の口を直に打たない）。

使い方:
  python3 月次/答えの書き戻し.py < 書き戻しの入力.json > 書き戻し.json
  python3 月次/決まりのmdを書き換える.py --会社 <会社> [--根 <id>] [--鍵の変数名 GOOGLE_DRIVE_SA_JSON] [--試しに書かない] < 書き戻し.json

- 標準入力は 答えの書き戻し の返す物（{手順, …}）か手順の並び。md を書き換える 手順だけをここで当て、ほかの手順
  （値を書く・行を足す・行を消す・ファイルを作る）は並びのまま 残りの手順 に返す（殻が〔口: 書く手順を当てる〕で当てる）。
- 当てる前に今の中身を読み、手順の 前の印（`答えの書き戻し.md_の印`＝組んだ元の全文の印）と照らす。違えば（人が直した・
  別の手順が先に当たった）どの md にも書かず止める＝人の直しを上書きしない。同じ md の手順が 2 つ以上なら、前の手順の
  本文の印が次の 前の印 と続くかを照らし、最後の本文だけを 1 度書く。今の中身が既に最後の本文なら書かない（何度打っても同じ）。
- 書く先は 1_決まり の子を名で引く（`型の口.木()["決まりの物"]` の名だけ）。無い md は作らない（止める）。
  書くのは `ファイルを書き換える`（在る file の中身だけ・名と親を変えない）。書いた後に読み直して最後の本文と照らす。
- 根の id は --根 か環境の変数 PAYROLL_OFFICE_ROOT_ID。鍵は環境の変数の名で受ける（値は受けない・出さない）。
  stdout の JSON の訳から Drive の id の形は伏せる（`出口/出す.伏せる`）。
exit: 0＝当てた（か試しで通る・当てる md 手順が無い）／2＝止めた（1 つも書いていない。書く途中で落ちた時だけ 書いた に
当てた md が残る＝打ち直せば当たった md は飛ばす）。止めた時は 残りの手順 を返さない（書き戻しは全部か無しか）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent
根の場所 = ここ.parent
if str(根の場所) not in sys.path:
    sys.path.insert(0, str(根の場所))

import drive口  # noqa: E402
from 初期設定 import 型の口  # noqa: E402
from 出口.出す import 伏せる  # noqa: E402  訳から id を伏せる正本


def _読み込む(名: str, path: Path):
    if 名 in sys.modules:
        return sys.modules[名]
    spec = importlib.util.spec_from_file_location(名, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[名] = m
    spec.loader.exec_module(m)
    return m


書き戻し = _読み込む("月次_答えの書き戻し", ここ / "答えの書き戻し.py")
md_の印 = 書き戻し.md_の印
_する = "md を書き換える"


def 決まりのmdの名() -> tuple[str, ...]:
    """書いてよい md の名（1_決まり の子・型の口 の 決まりの物 の名）。"""
    return tuple(型の口.名(k) for k in 型の口.木()["決まりの物"])


def _手順を読む(入力) -> list:
    if isinstance(入力, dict):
        入力 = 入力.get("手順")
    if not isinstance(入力, list) or not all(isinstance(x, dict) for x in 入力):
        raise ValueError("手順の並び（答えの書き戻し の返す物の 手順）が要る")
    return 入力


def 当てる(口, 会社の置き場: dict, 入力, *, 書かない: bool = False) -> tuple[int, dict]:
    """md を書き換える 手順を 1_決まり の md へ当てる。返り: (exit, stdout に出す JSON)。止める時は何も書かない。"""
    code, out = _当てる(口, 会社の置き場, 入力, 書かない=書かない)
    if out.get("赤"):
        out["赤"] = 伏せる(out["赤"])
    return code, out


def _当てる(口, 会社の置き場: dict, 入力, *, 書かない: bool) -> tuple[int, dict]:
    def 止める(赤, 書いた=()):
        return 2, {"書いた": list(書いた), "既に当たっていた": [], "残りの手順": [], "赤": list(赤)}

    try:
        手順 = _手順を読む(入力)
    except ValueError as e:
        return 止める([f"形: {e}"])
    if isinstance(入力, dict) and 入力.get("赤"):
        return 止める(["書き戻しが赤（手順を当てない）: " + "・".join(map(str, 入力["赤"]))])
    残り = [x for x in 手順 if x.get("する") != _する]
    名たち = 決まりのmdの名()
    先ごと: dict[str, list[dict]] = {}
    赤 = []
    for i, x in enumerate(x for x in 手順 if x.get("する") == _する):
        先, 本文, 前 = x.get("先"), x.get("本文"), x.get("前の印")
        if 先 not in 名たち:
            赤.append(f"md の手順 {i + 1}: 先「{先}」は 1_決まり の md（{'・'.join(名たち)}）でない")
        elif not isinstance(本文, str):
            赤.append(f"md の手順 {i + 1}（{先}）: 本文が字でない")
        elif not isinstance(前, str) or not 前.startswith("sha256:"):
            赤.append(f"md の手順 {i + 1}（{先}）: 前の印が無い（今の 答えの書き戻し で組み直す＝今の中身と照らせない手順は当てない）")
        else:
            先ごと.setdefault(先, []).append(x)
    for 先, xs in 先ごと.items():
        for a, b in zip(xs, xs[1:]):
            if b["前の印"] != md_の印(a["本文"]):
                赤.append(f"{先}: 手順の 前の印 が前の手順の本文と続かない（同じ 1 回の 答えの書き戻し の手順でない）")
                break
    if 赤:
        return 止める(赤)
    if not 先ごと:
        return 0, {"書いた": [], "既に当たっていた": [], "残りの手順": 残り}

    親id = 会社の置き場.get(型の口.名("決まり"))
    if not 親id:
        return 止める([f"置き場: 会社の置き場に {型の口.名('決まり')} が無い（drive口.置き場.会社の置き場）"])
    当てる物, 既に = [], []
    for 先, xs in 先ごと.items():
        try:
            f = 口.名で引く(親id, 先)
        except drive口.上限:   # 上限＝引けない訳に化けさせず・残りの md で打ち重ねず main で止める
            raise
        except Exception as e:  # noqa: BLE001  同じ名が 2 つ等＝選ばず止める
            赤.append(f"{型の口.名('決まり')}/{先} が引けない（{type(e).__name__}: {e}）")
            continue
        if f is None:
            赤.append(f"{型の口.名('決まり')}/{先} が無い（作らない＝初期設定で置く）")
            continue
        try:
            今 = 口.字を読む(f["id"])   # BOM・改行の違いは口がそろえる（byte で比べない）
        except drive口.上限:   # 上限＝読めない訳に化けさせず・残りの md で打ち重ねず main で止める
            raise
        except Exception as e:  # noqa: BLE001  読めない＝照らせない
            赤.append(f"{型の口.名('決まり')}/{先} が読めない（{type(e).__name__}: {e}）")
            continue
        後 = xs[-1]["本文"]
        if drive口.同じ字(今, 後):
            既に.append(先)
        elif md_の印(今) != xs[0]["前の印"]:
            赤.append(f"{先}: 今の中身が手順を組んだ時と違う（人が直した・ほかの手順が先に当たった）＝書かない。"
                     "今の md を渡して 答えの書き戻し を組み直す")
        else:
            当てる物.append((先, f["id"], 後))
    if 赤:
        return 止める(赤)
    if 書かない:
        return 0, {"書いた": [], "既に当たっていた": 既に, "残りの手順": 残り, "試し": "書いていない",
                   "書く": [先 for 先, _, _ in 当てる物]}
    書いた = []
    for 先, fid, 後 in 当てる物:
        try:
            口.ファイルを書き換える(fid, 後.encode("utf-8"))
            if not drive口.同じ字(口.字を読む(fid), 後):
                raise RuntimeError("読み直した中身が書いた本文と違う")
        except Exception as e:  # noqa: BLE001  書く途中で落ちた＝残りを書かず止める（打ち直せば当たった md は飛ばす）
            return 止める([f"{先} を書く途中で止まった: {type(e).__name__}: {e}"], 書いた)
        書いた.append(先)
    return 0, {"書いた": 書いた, "既に当たっていた": 既に, "残りの手順": 残り}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="答えの書き戻し の md を書き換える 手順を 1_決まり の md へ当てる")
    ap.add_argument("--会社", required=True)
    ap.add_argument("--根")
    ap.add_argument("--鍵の変数名", default=drive口.鍵の変数名の既定)
    ap.add_argument("--試しに書かない", action="store_true")
    a = ap.parse_args(argv)

    def 出す(code, out):
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return code

    try:
        入力 = json.load(sys.stdin)
    except ValueError as e:
        return 出す(2, {"書いた": [], "残りの手順": [], "赤": [f"形: 標準入力が JSON でない（{e}）"]})
    根 = a.根 or os.environ.get(drive口.根の変数名の既定)
    if not 根:
        return 出す(2, {"書いた": [], "残りの手順": [], "赤": [f"根: --根 か 環境の変数 {drive口.根の変数名の既定} が要る"]})
    try:
        口 = drive口.開く(鍵の変数名=a.鍵の変数名)
        from drive口 import 置き場 as 置
        置き場 = 置.会社の置き場(口, 根, a.会社)
    except Exception as e:  # noqa: BLE001  開けない・置き場が引けない＝何も書かない
        return 出す(2, {"書いた": [], "残りの手順": [], "赤": 伏せる([f"Drive: {type(e).__name__}: {e}"])})
    try:
        return 出す(*当てる(口, 置き場, 入力, 書かない=a.試しに書かない))
    except drive口.上限 as e:   # 読む・引く所の上限＝まだ何も書いていない（書く途中の上限は 当てる が書いた物と返す）
        return 出す(2, {"書いた": [], "残りの手順": [], "赤": 伏せる([str(e)])})


if __name__ == "__main__":
    sys.exit(main())
