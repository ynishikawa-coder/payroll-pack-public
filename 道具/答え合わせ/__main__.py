"""呼び口（根で `python3 -m 道具.答え合わせ …`）。JSON を受けて JSON を返す。Drive を開かない。

  読む   --形 一覧表|明細 --会社 <番号> --支給月 YYYY-MM --つなぎ つなぎ.json [--時間の書き方 60進|時:分|10進]
         [--文字コード cp932] [--氏名からNO 氏名.json] --出す 答え.json <file>...
  照らす --芯 芯.json --答え 答え.json --つなぎ つなぎ.json [--前の記録 記録.json] [--N 3] --出す 差.json

つなぎ.json: {"欄": [{"項目", "欄", "形"}...], "読まない見出し": [...], "鍵の見出し": [...], "氏名の見出し": [...]}（欄の並びだけでもよい）
芯.json: {"行": [人×項目の行...], "人の状態": [{"支給月", "会社", "NO", "状態"}...]}（行の並びだけでもよい）
答え.json: 読む の出す物 {"行": [...], "要確認": [...]}
終わりの値: 読む＝要確認 0 で 0・あれば 1／照らす＝差の行 0 かつ要確認 0 で 0・ほかは 1。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import 答えの読み口, 照合の段
from .表 import 表にする


def _読む_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _つなぎ(p) -> dict:
    d = _読む_json(p)
    return {"欄": d} if isinstance(d, list) else d


def _数の字(v) -> str:
    v = v.normalize()
    return str(int(v)) if v == v.to_integral_value() else format(v, "f")


def _書く(p, d):
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def 読む(a) -> int:
    t = _つなぎ(a.つなぎ)
    要確認: list[str] = []
    表たち = []
    for f in a.files:
        表たち += 表にする(Path(f).name, Path(f).read_bytes(), a.文字コード, 要確認)
    口 = 答えの読み口.一覧表を読む if a.形 == "一覧表" else 答えの読み口.明細を読む
    r = 口(表たち, a.会社, a.支給月, t["欄"], a.時間の書き方,
          鍵の見出し=t.get("鍵の見出し", ("NO",)), 氏名の見出し=t.get("氏名の見出し", ("氏名",)),
          氏名からNO=_読む_json(a.氏名からNO) if a.氏名からNO else None, 読まない見出し=t.get("読まない見出し", ()))
    要確認 += list(r.要確認)
    _書く(a.出す, {"行": [{"支給月": x.支給月, "会社": x.会社, "NO": x.NO, "項目": x.項目, "値": _数の字(x.値),
                           "出所": x.出所, "状態": x.状態} for x in r.行たち], "要確認": 要確認})
    print(f"{a.出す}: {len(r.行たち)} 行・要確認 {len(要確認)} 件", file=sys.stderr)
    return 0 if not 要確認 else 1


def 照らす(a) -> int:
    芯 = _読む_json(a.芯)
    芯 = {"行": 芯} if isinstance(芯, list) else 芯
    状態 = {(x["支給月"], x["会社"], x["NO"]): x["状態"] for x in 芯.get("人の状態", [])}
    答え = _読む_json(a.答え)

    class _答え:
        行たち = 答え["行"]
        要確認 = tuple(答え.get("要確認", ()))

    前 = _読む_json(a.前の記録) if a.前の記録 else ()
    r = 照合の段.照らす(芯["行"], _答え, _つなぎ(a.つなぎ)["欄"], 人の状態=状態 or None, 前の記録=前, N=a.N)
    _書く(a.出す, r.字の形())
    差 = r.差の行の数
    print(f"{a.出す}: 照らした {len(r.差の表) - 1} 行・差 {差} 行・問い {len(r.問い)}・要確認 {len(r.要確認)} 件", file=sys.stderr)
    return 0 if 差 == 0 and not r.要確認 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m 道具.答え合わせ", description="開発の間だけの答え合わせ")
    sub = ap.add_subparsers(dest="口", required=True)
    p = sub.add_parser("読む")
    p.add_argument("--形", choices=("一覧表", "明細"), required=True)
    p.add_argument("--会社", required=True)
    p.add_argument("--支給月", required=True)
    p.add_argument("--つなぎ", required=True)
    p.add_argument("--時間の書き方", choices=("60進", "時:分", "10進"))
    p.add_argument("--文字コード", default="utf-8-sig")
    p.add_argument("--氏名からNO")
    p.add_argument("--出す", required=True)
    p.add_argument("files", nargs="+")
    q = sub.add_parser("照らす")
    q.add_argument("--芯", required=True)
    q.add_argument("--答え", required=True)
    q.add_argument("--つなぎ", required=True)
    q.add_argument("--前の記録")
    q.add_argument("--N", type=int, default=3)
    q.add_argument("--出す", required=True)
    a = ap.parse_args(argv)
    return 読む(a) if a.口 == "読む" else 照らす(a)


if __name__ == "__main__":
    sys.exit(main())
