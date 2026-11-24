# -*- coding: utf-8 -*-
"""古い形の会社の 1_決まり/質問と回答（タブ 質問）を今の形へ移す（docs/設計/寄せる道具.md §6）。

なぜ在るか（2026-11-24）: 前の道具で始めた会社は、質問と回答 の列の並びが前の形のまま・仮の答え（今の型の 見当）だけが書いてあり
答え（今の型の 回答）が空の問いが残る・置き場のタブや管理表「会社」の行が無い、のどれかで、確認ページと反映の照らしが回らない。

道具は Drive を開かない純粋な関数。殻が読んだ表の中身（get_values の形）を受け、移した後の中身・前→後の差・（書く時だけ）書く手順を返す。
書くのは殻。既定は試し（書く手順を出さない）。書く方は引数 書く=True（呼び口 --書く）で明示する。

する事（順に）:
  1. 列の並び: 事務所が渡す前の形の読み替え（列の名を変える など＝前の列の名はパックに置かない）→ 型の作り（列を足す・支給月の
     書き方・並び）。型の作りと見出しは 道具/寄せ/質問と回答.py（型の口 の 質問と回答）から引く（写さない）。
  2. 見当 → 回答: 回答が空・見当が在る問いのうち、反映先の値（2_マスタ の値・決まりの md の節）で決まる物だけ、見当を回答へ写し
     反映済み を 済 にする。決まる＝反映先が全部 マスタか md で、マスタはその値が見当と同じ（人の先は当たる人の全部）・md は節に
     問いの番号（出所）と見当の字が在り、かつ写した後の行が 設問.反映の照らし で全部 埋まった。ほかは動かさない（値を作らない）。
  3. 置き場: タブ 質問 が無ければ型の見出しで足す。管理表「会社」にその会社の行が無ければ足す（管理表/管理表.py 会社の行）。
  4. 差: 前→後を一覧で返す。寄せられない物が 1 つでも在れば書く手順は空（全部か無し）。

  python3 道具/寄せ/古い形を移す.py --入力 <入力の JSON> [--書く]
終わりの値: 0＝移せる（差 0 なら既に今の形）／1＝寄せられない物が在る／2＝使い方の誤り。
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path

import 当てる
import 直し as 直しの形
import 質問と回答

_根 = Path(__file__).resolve().parents[2]


def _読む(名: str, path: Path):
    s = importlib.util.spec_from_file_location(名, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


設問 = _読む("移す_設問", _根 / "初期設定" / "設問.py")
管理表 = _読む("移す_管理表", _根 / "管理表" / "管理表.py")

ファイル = 質問と回答.会社のファイル
タブ = 質問と回答.タブ
型の見出し = 質問と回答.型の見出し
管理表のファイル = 質問と回答.既定のファイル.split("/")[0] + "/" + 当てる.型の口.名("管理表")
管理表のタブ = "会社"
済 = [v for v in 当てる.型の口.問いの列("反映済み")["選べる値"] if v][0]
_マスタ = 当てる.型の口.シートの型("マスタ")["シート"]


def _字(v) -> str:
    return unicodedata.normalize("NFKC", str(v if v is not None else "")).strip()


def _読み替えを確かめる(読み替え) -> None:
    if not isinstance(読み替え, list) or not all(isinstance(op, dict) for op in 読み替え):
        raise ValueError("読み替えは操作の並び（[{\"する\": …}, …]）")
    誤り = 直しの形.形を確かめる({"版": 1, "前の版": 0, "なぜ": "古い形の読み替え", "操作": 読み替え}, "読み替え")
    for i, op in enumerate(読み替え, 1):
        if op.get("する") not in 質問と回答.使える操作:
            誤り.append(f"読み替え 操作{i}: {'・'.join(質問と回答.使える操作)} だけ（「{op.get('する')}」）")
        if op.get("ファイル") != ファイル or op.get("タブ") != タブ:
            誤り.append(f"読み替え 操作{i}: ファイル「{ファイル}」・タブ「{タブ}」への操作だけ（{op.get('ファイル')}/{op.get('タブ')}）")
    if 誤り:
        raise 直しの形.直しの誤り("\n".join(誤り))


def 並べる(会社: str, rows, 読み替え) -> tuple[list, list, list]:
    """1. 読み替え → 型の作り。返す物: (前, 後, 寄せられない物)。寄せられない物が在る時の 後 は前のまま。"""
    前 = 当てる.そろえる(rows)
    o = 当てる.物({"会社": 会社, "型の版": 0, "シート": {ファイル: {タブ: copy.deepcopy(前)}}})
    記 = 当てる.記録()
    K = {"ファイル": {ファイル: {タブ: [{"名": c} for c in 型の見出し]}}}
    for 番, op in enumerate(読み替え, 1):
        当てる.当てる操作(o, op, K, 記, 0, 番, {})
    where = f"{ファイル}/{タブ}"
    出せない = []
    訳 = 質問と回答.前の答え.見出しの訳(o.シート[ファイル][タブ])
    if 訳:   # 見出しを推し量らない
        出せない.append({"鍵": f"{where}/見出し", "種類": "形の合わない値", "所": where, "中身": f"質問と回答の{訳}",
                      "選べる答え": ["1 行目を型の見出しにしてからもう一度（人）"]})
        return 前, 前, 出せない
    for 番, op in enumerate(質問と回答.型の作り(ファイル), len(読み替え) + 1):
        当てる.当てる操作(o, op, K, 記, 0, 番, {})
    後 = o.シート[ファイル][タブ]
    for c in [c for c in 後[0] if c not in 型の見出し]:   # 型に無い列は消さず、行き先を推し量らない
        出せない.append({"鍵": f"{where}/列:{c}", "種類": "行き先の無い列", "所": where, "中身": f"型に無い列「{c}」",
                      "選べる答え": ["読み替えに 列の名を変える（前＝この列・後＝型の列）を足してもう一度（事務所の寄せの記録）"]})
    ki = 当てる.列の番号(後, "会社")
    他 = sorted({str(r[ki]).strip() for r in 後[1:] if str(r[ki]).strip() not in ("", 会社)}) if ki is not None else []
    if 他:
        出せない.append({"鍵": f"{where}/会社", "種類": "形の合わない値", "所": where,
                      "中身": f"列「会社」に {会社} でない字: {'・'.join(他[:5])}", "選べる答え": ["その会社の表へ移してからもう一度（人）"]})
    出せない += 質問と回答.番号を照らす(前, 後, where, 質問と回答.会社の答え)
    出せない = [{k: v for k, v in x.items() if k != "手がかり"} for x in 記.寄せられない] + 出せない
    if _値の数(前) + 記.数["足した"] != _値の数(後):
        出せない.append({"鍵": f"{where}/値の保ち", "種類": "直しの誤り", "所": where, "中身": "空でない値の数が合わない",
                      "選べる答え": ["読み替えを直す"]})
    return 前, (前 if 出せない else 後), 出せない


def _値の数(rows) -> int:
    """見出しの外の空でない値の数（見出しは数えない）。"""
    return sum(1 for r in rows[1:] for v in r if not 当てる.空か(v))


def _その会社の行(rows, 会社: str) -> list[dict]:
    """get_values の表 → 会社の列が空かその会社の行（見出しの名で引く dict）。"""
    rows = list(rows or ())
    if not rows:
        return []
    h = [str(c).strip() for c in rows[0]]
    out = [dict(zip(h, list(r) + [""] * (len(h) - len(r)))) for r in rows[1:]]
    return [d for d in out if str(d.get("会社", "")).strip() in ("", 会社)]


def _節(本文: str, 見出し: str) -> str:
    return 設問.md_の節(本文, 見出し) if 見出し else 本文


def 決まるか(q: dict, 会社: str, マスタ: dict, md: dict) -> tuple[bool, str]:
    """見当が反映先の値（マスタの値・決まりの md）で決まるか → (決まる, 訳)。"""
    見当 = _字(q.get("見当"))
    先たち = [w.strip() for w in re.split(r"[、,]", str(q.get("反映先") or "")) if w.strip()]
    if not 先たち:
        return False, "反映先が空"
    誰 = {w.strip() for w in re.split(r"[、,]", str(q.get("答えで変わる項目と人") or "")) if w.strip()}
    for 先 in 先たち:
        if "#" in 先 or 先.endswith(".md"):
            名, _, 見出し = 先.partition("#")
            if 名 not in md:
                return False, f"{名} の本文を渡されていない"
            節 = _節(md[名], 見出し)
            if 見当 not in _字(節) or str(q.get("問いの番号", "")).strip() not in 節:
                return False, f"{先} に 見当「{見当}」と出所の問いの番号が無い"
            continue
        部 = 先.split("/")
        if 部[0] != _マスタ or len(部) != 3:
            return False, f"{先} はマスタか md の先でない"
        タブ名, 名 = 部[1], 部[2]
        if タブ名 == "会社":
            v = 設問.会社の値(マスタ, 会社, q.get("支給月") or None).get(名)
            if v is None or _字(v) != 見当:
                return False, f"マスタ 会社 の {名} が「{'' if v is None else v}」"
            continue
        鍵 = {"勤務の型": "型の名", "社員": "NO"}.get(タブ名)
        行たち = _その会社の行(マスタ.get(タブ名, ()), 会社)
        当たる = [r for r in 行たち if 鍵 and str(r.get(鍵)) in 誰] if 鍵 else []
        if not 当たる or any(_字(r.get(名)) != 見当 for r in 当たる):
            return False, f"マスタ {タブ名} の {名} が見当と同じと決まらない（答えで変わる人の全部の行が要る）"
    return True, ""


def 答えへ写す(会社: str, rows: list, マスタ: dict, md: dict, 今日: str | None) -> tuple[list, list, list]:
    """2. 見当 → 回答（決まる物だけ）。rows は型の並びの表（写して返す）。返す物: (後, 写した, 残した)。"""
    後 = copy.deepcopy(rows)
    h = 後[0]
    i = {c: h.index(c) for c in ("問いの番号", "見当", "回答", "回答日", "反映済み")}
    写した, 残した = [], []
    for r in 後[1:]:
        q = dict(zip(h, r))
        if 当てる.空か(q["見当"]) or not 当てる.空か(q["回答"]):
            continue
        ok, 訳 = 決まるか(q, 会社, マスタ, md)
        if ok:   # 写した後の行が 反映の照らし で全部 埋まった時だけ（照らしの赤を作らない）
            新 = {**q, "回答": q["見当"], "反映済み": 済}
            照 = 設問.反映の照らし([h, [新[c] for c in h]], マスタ, 会社, md=md, 支給月=q.get("支給月") or None)
            if 照["赤"] or not 照["行たち"]:
                ok, 訳 = False, "・".join(照["赤"]) or "反映の照らしに行が無い"
        if not ok:
            残した.append({"問いの番号": q["問いの番号"], "訳": 訳})
            continue
        r[i["回答"]] = r[i["見当"]]
        r[i["反映済み"]] = 済
        if 今日:
            r[i["回答日"]] = 今日
        写した.append({"問いの番号": q["問いの番号"], "値": r[i["見当"]]})
    return 後, 写した, 残した


def 移す(入力: dict, 書く: bool = False) -> dict:
    """古い形の会社 1 社を今の形へ。

    入力: 会社・組・型の版（管理表「会社」の行を足す時だけ要る）・質問（タブ 質問 の get_values。タブが無ければ省くか null）・
          読み替え（前の形の読み替えの操作の並び・任意）・マスタ（{2_マスタのタブ: get_values}）・md（{md の名: 本文}）・
          管理表の会社（00_事務所/管理表 タブ 会社 の get_values）・今日（YYYY-MM-DD・任意＝回答日に書く）。
    書く: False（既定）＝試し。書く手順は出さない。True＝寄せられない物が無ければ書く手順と戻す手順を出す。
    返す物: 試し・後の値（{質問, 管理表の会社}）・差（前→後の一覧）・書く手順・戻す手順・寄せられない物・残した（決まらない見当）・知らせ。"""
    会社 = 入力["会社"]
    読み替え = 入力.get("読み替え") or []
    _読み替えを確かめる(読み替え)
    差, 出せない, 知らせ, 書く手順, 戻す手順 = [], [], [], [], []
    where = f"{ファイル}/{タブ}"

    # 3a. 置き場のタブ
    rows = 入力.get("質問")
    タブが無い = rows is None
    if タブが無い:
        rows = [list(型の見出し)]
        差.append({"何": "タブを足す", "所": where, "前": None, "後": list(型の見出し)})
    前, 並べた, 出 = 並べる(会社, rows, 読み替え)
    出せない += 出
    if not 出 and 並べた[0] != 前[0]:
        差.append({"何": "列の並び", "所": where, "前": 前[0], "後": 並べた[0]})
    elif not 出 and 並べた != 前:
        差.append({"何": "値をそろえる", "所": where, "前": None, "後": "型の書き方（支給月など）"})

    # 2. 見当 → 回答
    後 = 並べた
    残した = []
    if not 出:
        後, 写した, 残した = 答えへ写す(会社, 並べた, 入力.get("マスタ") or {}, 入力.get("md") or {}, 入力.get("今日"))
        for x in 写した:
            差.append({"何": "見当を回答へ", "所": f"{where}/{x['問いの番号']}", "前": "", "後": x["値"], "反映済み": 済})

    # 3b. 管理表「会社」の行
    管 = 入力.get("管理表の会社")
    管の後 = 管
    if 管 is not None:
        try:
            手 = 管理表.会社の行({"今の値": 管, "会社の一覧": [{"会社": 会社, "組": 入力.get("組", ""), "型の版": 入力.get("型の版")}]})
        except 管理表.拒む as e:
            手 = []
            出せない.append({"鍵": f"{管理表のファイル}/{管理表のタブ}/{会社}", "種類": "足りない値", "所": f"{管理表のファイル}/{管理表のタブ}",
                          "中身": str(e), "選べる答え": ["入力に 組 と 型の版 を渡してもう一度（殻）"]})
        if 手:
            管の後 = 当てる.そろえる(管) + [x["値"] for x in 手]
            for x in 手:
                差.append({"何": "管理表の行を足す", "所": f"{管理表のファイル}/{管理表のタブ}", "前": None, "後": x["値"]})
    else:
        知らせ.append("管理表の会社 を渡されていない＝管理表の行は見ていない")

    if 出せない:
        差 = []
    elif 書く and 差:
        if タブが無い:
            書く手順.append({"する": "タブを足す", "ファイル": ファイル, "タブ": タブ, "見出し": list(型の見出し)})
        if 後 != 前 or タブが無い:
            h, w = 当てる.大きさ(前, 後)
            範囲 = f"A1:{当てる.列の字(w)}{h}"
            書く手順.append({"する": "値を書く", "ファイル": ファイル, "タブ": タブ, "範囲": 範囲, "値": 当てる.敷く(後, h, w), "書き方": 当てる.字のまま})
            if not タブが無い:
                戻す手順.append({"する": "値を書く", "ファイル": ファイル, "タブ": タブ, "範囲": 範囲, "値": 当てる.敷く(前, h, w), "書き方": 当てる.字のまま})
        if 管の後 is not 管:
            for x in 管の後[len(当てる.そろえる(管)):]:
                書く手順.append({"する": "行を足す", "ファイル": 管理表のファイル, "タブ": 管理表のタブ, "値": x, "書き方": 当てる.字のまま})
    if not 出せない and not 差:
        知らせ.append(f"{会社} は既に今の形（差 0）")
    if not 書く and 差:
        知らせ.append("試し（書く手順は出さない。書くのは --書く で明示）")
    return {"試し": not 書く, "後の値": {"質問": 前 if 出せない else 後, "管理表の会社": 管 if 出せない else 管の後},
            "差": 差, "書く手順": 書く手順, "戻す手順": 戻す手順, "寄せられない物": 出せない, "残した": 残した, "知らせ": 知らせ}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="古い形の会社の 質問と回答 を今の形へ移す（既定は試し）")
    p.add_argument("--入力", required=True)
    p.add_argument("--書く", action="store_true", help="書く手順を出す（既定は試し）")
    a = p.parse_args(argv)
    try:
        r = 移す(json.loads(Path(a.入力).read_text(encoding="utf-8")), 書く=a.書く)
        out = json.dumps(r, ensure_ascii=False, indent=1)
    except (ValueError, KeyError, OSError, 直しの形.直しの誤り) as e:
        print(f"古い形を移す: {e}", file=sys.stderr)
        return 2
    print(out)
    return 1 if r["寄せられない物"] else 0


if __name__ == "__main__":
    sys.exit(main())
