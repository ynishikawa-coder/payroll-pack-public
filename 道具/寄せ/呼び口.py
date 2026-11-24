# -*- coding: utf-8 -*-
"""寄せる道具の呼び口 3 つ（と自己検査）。Drive を開かない。殻が読んだ JSON を受け、JSON を標準出力へ返す。

  python3 道具/寄せ/呼び口.py 寄せる --会社 会社.json --型 型.json [--今日 YYYY-MM-DD]
  python3 道具/寄せ/呼び口.py 配る   --会社たち a.json b.json … --型 型.json --管理表 会社.json [--今日 …]
  python3 道具/寄せ/呼び口.py 見回り --会社たち a.json … --型 型.json --管理表 会社.json [--窓 <置いた窓の役>] [--前の答え 答え.json] [--今日 …]
  python3 道具/寄せ/呼び口.py 消す   --会社たち a.json … --型 型.json --管理表 会社.json --答え 答え.json [--窓 …] [--前の答え …] [--今日 …]
--管理表 は管理表「会社」タブの今の値（get_values の JSON・寄せの印と最後に配った日をパックの 管理表.py で読む）。
消す は 見回り と同じ消す問いを今の Drive から作り、オーナーの答え（{"全部": "推奨どおり"} か {鍵: 消す｜原本へ移す:<置き場>｜残す:<日>}）を
当てた手順を返す（docs/設計/寄せる道具.md §4.4。誤りが 1 つでもあれば手順は空・終わりの値 1）。
  python3 道具/寄せ/呼び口.py 自己検査 --型 型.json [--前の型 前の版の型.json]
  python3 道具/寄せ/呼び口.py 質問と回答 --表 質問.json --読み替え 読み替え.json [--ファイル 00_事務所/質問と回答]
--型 は 初期設定/型.json（同じ置き場の 項目.json・雛形/ も読む）。
共通: [--直し <直しの dir>]（既定は 道具/寄せ/直し/）。終わりの値: 0＝書ける／緑、1＝寄せられない物が在る／赤、2＝使い方の誤りか落ちた（標準出力は空・訳は標準エラー）。
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import 当てる  # noqa: E402
import 管理表.管理表 as 管理表の口  # noqa: E402  当てる が パックの根を sys.path に置く
import 直し as 直しの形  # noqa: E402
import 見回り as 見回りの口  # noqa: E402
import 自己検査 as 検査  # noqa: E402
import 質問と回答 as 質問と回答の口  # noqa: E402


def 読む(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None) -> int:
    """落ちた時（読めない入力・直しの誤り・値の保ちの誤り・思わぬ誤り）は終わりの値 2＝寄せられない物の 1 と分ける
    （落ちた回を、標準出力が空の「寄せられない物の回」や「書く物の無い回」と読ませない）。"""
    try:
        return _main(argv)
    except Exception as e:  # noqa: BLE001  落ちた訳は名指しで標準エラーへ・終わりの値は 2 の 1 つ
        import traceback
        traceback.print_exc()
        print(f"呼び口が落ちた（{type(e).__name__}: {e}）＝何も返さない", file=sys.stderr)
        return 2


def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="呼び口.py")
    ap.add_argument("する", choices=["寄せる", "配る", "見回り", "消す", "自己検査", "質問と回答"])
    ap.add_argument("--会社")
    ap.add_argument("--会社たち", nargs="*", default=[])
    ap.add_argument("--型")
    ap.add_argument("--表")
    ap.add_argument("--読み替え")
    ap.add_argument("--ファイル", default=質問と回答の口.既定のファイル)
    ap.add_argument("--前の型")
    ap.add_argument("--直し", default=直しの形.置き場)
    ap.add_argument("--今日")
    ap.add_argument("--窓", default="")
    ap.add_argument("--前の答え")
    ap.add_argument("--管理表")
    ap.add_argument("--答え")
    a = ap.parse_args(argv)
    if a.する == "質問と回答":   # 会社の型の版の鎖に乗らない質問と回答 1 枚（型・直しは読まない）
        if not a.表 or not a.読み替え:
            ap.error("質問と回答 には --表 と --読み替え")
        try:
            r = 質問と回答の口.寄せる(読む(a.表), 読む(a.読み替え), a.ファイル)
        except (ValueError, 直しの形.直しの誤り) as e:
            print(str(e), file=sys.stderr)
            return 2
        出す(r)
        return 1 if r["寄せられない物"] else 0
    if not a.型:
        ap.error("--型 が要る")
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
    elif a.する in ("配る", "見回り", "消す"):
        if not a.管理表:
            ap.error(f"{a.する} には --管理表（管理表「会社」タブの今の値）＝寄せ中と写しの期限を読まずに回さない")
        if a.する == "消す" and not a.答え:
            ap.error("消す には --答え（オーナーの答え）")
        会社たち, 管理表 = [読む(p) for p in a.会社たち], 読む(a.管理表)
        try:
            if a.する == "配る":
                r = 見回りの口.配る(会社たち, 型, 直したち, 今日, 管理表=管理表)
                rc = 1 if any(x["寄せられない物"] for x in r["見通し"]) else 0
            else:
                r = 見回りの口.見回り(会社たち, 直したち, 当てる.型を読む(型)["版"], 今日, a.窓,
                                 前の答え=読む(a.前の答え) if a.前の答え else None, 型=型, 管理表=管理表)
                rc = 0   # 赤（書き方のずれ・置き場の検査）は r["赤"] で返す（終わりの値は前と同じ 0）
                if a.する == "消す":
                    r = {**見回りの口.答えを当てる(r["消す問い"], 読む(a.答え), 今日), "消す問い": r["消す問い"]}
                    rc = 1 if r["誤り"] else 0
        except 管理表の口.拒む as e:
            print(f"管理表が読めない: {e}", file=sys.stderr)
            return 2
    else:
        r = 検査.全部(型, 直したち, 当てる.型を開く(a.前の型) if a.前の型 else None)
        rc = 1 if any(r.values()) else 0
        r["判定"] = "赤" if rc else "緑"
    出す(r)
    return rc


def 出す(r) -> None:
    """結果を字に直し切ってから 1 度だけ標準出力へ書く（json.dump は書きながら直す＝途中で落ちると半端な JSON が
    標準出力に残る。直し切る前に落ちれば標準出力は空のまま終わりの値 2）。"""
    字 = json.dumps(r, ensure_ascii=False, indent=1) + "\n"
    sys.stdout.write(字)


if __name__ == "__main__":
    sys.exit(main())
