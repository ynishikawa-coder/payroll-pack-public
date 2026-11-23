"""呼び口（根で `python3 -m 道具.答え合わせ …`）。初期設定の照らし（本番の 0 段の手順・確かめと仮.md §1）。
JSON を受けて JSON を返す。Drive を開かない。

  読む   --形 一覧表|明細 --会社 <番号> --支給月 YYYY-MM --つなぎ つなぎ.json [--時間の書き方 60進|時:分|10進]
         [--文字コード cp932] [--氏名からNO 氏名.json] --出す 答え.json <file>...
  照らす --芯 芯.json --答え 答え.json --つなぎ つなぎ.json [--前の記録 記録.json] [--N <数・省くと項目の辞書の既定>] --出す 差.json
  出所を見る --変更の記録 記録.json --答え 答え.json [--答えの資料 名...] [--質問と回答 問い.json] [--会社 名]
            [--事務所の質問と回答 問い.json] [--md md.json] [--台帳 台帳.json] [--照らし 差.json] [--例 例.json] --出す 出所.json

つなぎ.json: {"欄": [{"項目", "欄", "形"}...], "読まない見出し": [...], "鍵の見出し": [...], "氏名の見出し": [...]}（欄の並びだけでもよい）
芯.json: {"行": [人×項目の行...], "人の状態": [{"支給月", "会社", "NO", "状態"}...]}（行の並びだけでもよい）
答え.json: 読む の出す物 {"行": [...], "要確認": [...]}
差.json の 問いの種: 設問.まとめる の種の形（殻がほかの種と 1 枚にまとめ、確認ページ.作る で聞く）。
記録.json・問い.json: マスタ「変更の記録」・質問と回答 の行（列名の dict の並び）。
終わりの値: 読む＝要確認 0 で 0・あれば 1／照らす＝差の行 0 かつ要確認 0 で 0・ほかは 1／
出所を見る＝照らしで確かめていない過去の結果を出所とする値（と出所の無い値）が 0 で 0・あれば 1（毎月へ進まない）。
どの口も、道具そのものが壊れた（読めない file・形の違う JSON・使い方の誤りなど）時は 2＝結果ではない（出す file は書かれない・毎月へ進まない）。
過去の結果の照らし（`過去の結果 <支給月> <資料の名> <NO>:<項目> 一致`）を出所にした値は --照らし の差の表で差 0 の時だけ通す。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import 出所を見る as 出所, 答えの読み口, 照合の段
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
    if not isinstance(芯, dict) or "人の状態" not in 芯:   # 前: 行だけの並び・人の状態の無い JSON を「状態の無い人＝確定」と読んだ
        raise ValueError(f"{a.芯}: 芯の JSON に 人の状態 が無い（芯の返す {{行, 人の状態}} を渡す・仮の人が居なければ \"人の状態\": [] を明示）")
    状態 = {(x["支給月"], x["会社"], x["NO"]): x["状態"] for x in 芯["人の状態"]}
    答え = _読む_json(a.答え)

    class _答え:
        行たち = 答え["行"]
        要確認 = tuple(答え.get("要確認", ()))

    前 = _読む_json(a.前の記録) if a.前の記録 else ()
    r = 照合の段.照らす(芯["行"], _答え, _つなぎ(a.つなぎ)["欄"], 人の状態=状態, 前の記録=前, N=a.N,
                     仮の人の行=芯.get("仮の人の行", ()))
    _書く(a.出す, r.字の形())
    差 = r.差の行の数
    print(f"{a.出す}: 照らした {len(r.差の表) - 1} 行・差 {差} 行・問いの種 {len(r.問いの種)}・要確認 {len(r.要確認)} 件",
          file=sys.stderr)
    return 0 if 差 == 0 and not r.要確認 else 1


def 出所を見る(a) -> int:
    資料 = 出所.答えの資料(_読む_json(a.答え)["行"]) | set(a.答えの資料 or ())
    r = 出所.見る(_読む_json(a.変更の記録), 資料, _読む_json(a.質問と回答) if a.質問と回答 else (), a.会社,
               事務所の質問と回答=_読む_json(a.事務所の質問と回答) if a.事務所の質問と回答 else (),
               md=_読む_json(a.md) if a.md else None, 台帳=_読む_json(a.台帳) if a.台帳 else None,
               照らし=_読む_json(a.照らし) if a.照らし else None, 答えの行=_読む_json(a.答え)["行"],
               例=_読む_json(a.例) if a.例 else None)
    _書く(a.出す, r.字の形())
    print(f"{a.出す}: 見た {r.見た行の数} 行・外れ {len(r.外れ)} 件" + ("（毎月へ進まない）" if r.止める else ""), file=sys.stderr)
    return 1 if r.止める else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m 道具.答え合わせ", description="初期設定の照らし（過去の結果と人×項目で照らす本番の 0 段の手順）")
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
    q.add_argument("--N", type=int, default=None, help="省くと 初期設定/項目.json の 突き合わせ.差0の月数の目安 の既定")
    q.add_argument("--出す", required=True)
    o = sub.add_parser("出所を見る")
    o.add_argument("--変更の記録", required=True)
    o.add_argument("--答え", required=True)
    o.add_argument("--答えの資料", nargs="*")
    o.add_argument("--質問と回答")
    o.add_argument("--会社")
    o.add_argument("--事務所の質問と回答")
    o.add_argument("--md", help="{md の名: 字} の JSON（［出所］の行を見る）")
    o.add_argument("--台帳", help="{タブの名: 行} の JSON（確定した勤怠の 直した訳 の 問い:<番号> を見る）")
    o.add_argument("--照らし", help="照らす の出す 差.json（過去の結果の照らしを出所にした値の人×項目の一致を見る）")
    o.add_argument("--例", help="例の行の JSON（確かめた人 の過去の結果の照らしを見る。md の給与のルールの例も読む）")
    o.add_argument("--出す", required=True)
    a = ap.parse_args(argv)
    return {"読む": 読む, "照らす": 照らす, "出所を見る": 出所を見る}[a.口](a)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 道具そのものが壊れた＝終わりの値 2（1 の「見つかった・赤」と混ぜない）
        import traceback
        traceback.print_exc()
        print(f"✗ 道具が壊れた（答え合わせの道具・終わりの値 2＝結果ではない）: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
