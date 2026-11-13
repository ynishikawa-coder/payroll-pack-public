# -*- coding: utf-8 -*-
"""寄せる道具の呼び口 3 つ（と自己検査）。Drive を開かない。殻が読んだ JSON を受け、JSON を標準出力へ返す。

  python3 道具/寄せ/呼び口.py 寄せる --会社 会社.json --型 型.json [--今日 YYYY-MM-DD]
  python3 道具/寄せ/呼び口.py 配る   --会社たち a.json b.json … --型 型.json [--今日 …]
  python3 道具/寄せ/呼び口.py 見回り --会社たち a.json … --型 型.json [--窓 <置いた窓の役>] [--前の答え 答え.json] [--今日 …]
  python3 道具/寄せ/呼び口.py 自己検査 --型 型.json [--前の型 前の版の型.json]
--型 は 初期設定/型.json（同じ置き場の 項目.json・雛形/ も読む）。
共通: [--直し <直しの dir>]（既定は 道具/寄せ/直し/）。終わりの値: 0＝書ける／緑、1＝寄せられない物が在る／赤、2＝使い方の誤り。
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import 当てる  # noqa: E402
import 直し as 直しの形  # noqa: E402
import 見回り as 見回りの口  # noqa: E402
import 自己検査 as 検査  # noqa: E402


def 読む(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="呼び口.py")
    ap.add_argument("する", choices=["寄せる", "配る", "見回り", "自己検査"])
    ap.add_argument("--会社")
    ap.add_argument("--会社たち", nargs="*", default=[])
    ap.add_argument("--型", required=True)
    ap.add_argument("--前の型")
    ap.add_argument("--直し", default=直しの形.置き場)
    ap.add_argument("--今日")
    ap.add_argument("--窓", default="")
    ap.add_argument("--前の答え")
    a = ap.parse_args(argv)
    今日 = dt.date.fromisoformat(a.今日) if a.今日 else dt.date.today()
    型 = 当てる.型を開く(a.型)
    直したち = 直しの形.読む(a.直し)

    if a.する == "寄せる":
        if not a.会社:
            ap.error("寄せる には --会社")
        c = 読む(a.会社)
        r = 当てる.見通す(c, 型, 直したち, 今日)
        r["消す問い"] += 見回りの口.置き場を見る(c, 今日, a.窓)
        r["人が見る物"] = 当てる.人が見る物(r)
        rc = 1 if r["寄せられない物"] else 0
    elif a.する == "配る":
        r = 見回りの口.配る([読む(p) for p in a.会社たち], 型, 直したち, 今日)
        rc = 1 if any(x["寄せられない物"] for x in r["見通し"]) else 0
    elif a.する == "見回り":
        r = 見回りの口.見回り([読む(p) for p in a.会社たち], 直したち, 当てる.型を読む(型)["版"], 今日, a.窓,
                         前の答え=読む(a.前の答え) if a.前の答え else None)
        rc = 0
    else:
        r = 検査.全部(型, 直したち, 当てる.型を開く(a.前の型) if a.前の型 else None)
        rc = 1 if any(r.values()) else 0
        r["判定"] = "赤" if rc else "緑"
    json.dump(r, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
