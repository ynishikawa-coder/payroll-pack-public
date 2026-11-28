"""問いの取り下げ — 聞いている問いを下げる手順を返す口（質問と回答「問い」の 状態 を 取り下げ・管理表の 確認ページ の状況を 取り下げ）。

なぜ在るか（2026-11-27 オーナー: 問いを下げる時も決まった口で・2026-11-28 質問と回答は 問い・答え・振り分け の 3 タブ）:
問いを閉じた印は 問い の 状態 の列の 1 つの正本に持つ（答えの文に `取り下げ→` の頭を書かない）。下げた問いへの後の答えは
確認ページ.貼り戻し が書かずに知らせる。ここは値を決めて手順を返すだけで、事務所の置き場を開かない。殻が当てる。

決め方（問いの鍵ごとに 質問と回答.読む で読んだ問い・同じ鍵が幾つもあれば下の行）:
  - 問いが無い＝止める。状態が 取り下げ＝何もしない（何度当てても同じ）。答えた＝止める（答えを黙って捨てない）。
  - 聞いている＝`質問と回答.取り下げる`（状態を 取り下げ）。訳は表に列が無い＝記録へ返す（事務所の記録の置き場へ殻が書く）。
  - 管理表 確認ページ: 会社と確認ページの URL の行。状況が 取り下げ＝何もしない・答えた／差し替え＝止める・
    問いの数が下げる問いの数より多い＝状況は変えない（残る問いへの答えは受け付ける・知らせ）・ほか＝状況を 取り下げ。
  - 赤が 1 つでも在れば手順は 0（ひとまとまりで当てる）。
返す物: {手順 (質問と回答「1_問い」への 値を書く), 管理表の行 [確認ページ タブの行], 記録 [{問いの鍵, する, 訳, 版, 日}], 知らせ, 赤}。
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent
根 = ここ.parent
if str(根) not in sys.path:
    sys.path.insert(0, str(根))


def _読み込む(名: str, path: Path):
    if 名 in sys.modules:
        return sys.modules[名]
    spec = importlib.util.spec_from_file_location(名, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[名] = m
    spec.loader.exec_module(m)
    return m


頁 = _読み込む("取り下げ_確認ページ", 根 / "確認ページ" / "確認ページ.py")
qa = 頁.qa   # 質問と回答（3 タブ）の読み書きの正本
_表 = 頁.表


class 取り下げの誤り(ValueError):
    pass


def _字(v) -> str:
    return "" if v is None else str(v).strip()


def _鍵(番号) -> str:
    return 頁._鍵(_字(番号))   # Q209904-01 と Q209904_01 を同じ問いに読む（ページの鍵の正本）


def _格子(表, 何: str) -> list[list[str]]:
    """get_values の形（1 行目が見出し）だけを受ける。"""
    if not isinstance(表, (list, tuple)) or not 表 or not isinstance(表[0], (list, tuple)):
        raise 取り下げの誤り(f"{何} は get_values の形（1 行目が見出しの格子）で渡す")
    h = [_字(c) for c in 表[0]]
    return [h, *[[_字(r[i]) if i < len(r) else "" for i in range(len(h))] for r in 表[1:]]]


def _台帳の行(確認ページの行たち, 会社: str, 確認ページ: str, 数: int, 赤: list, 知らせ: list) -> list[dict]:
    格 = _格子(確認ページの行たち, "確認ページの行たち（管理表「確認ページ」）")
    h = 格[0]
    for c in ("会社", "載せた日", "確認ページ", "問いの数", "状況"):
        if c not in h:
            赤.append(f"管理表「確認ページ」に見出し {c} が無い")
            return []
    行たち = [dict(zip(h, r)) for r in 格[1:] if r[h.index("会社")] == 会社 and r[h.index("確認ページ")] == 確認ページ]
    if not 行たち:
        赤.append("管理表「確認ページ」にその会社のその確認ページの行が無い＝受付を止めた印を書けない（配った版の URL を渡す）")
        return []
    行 = 行たち[-1]
    状 = 行["状況"]
    if 状 == _表.値の字("確認ページ", "状況", "取り下げ"):
        return []
    if 状 == _表.値の字("確認ページ", "状況", "答えた"):
        赤.append("その確認ページはもうお答えいただいた＝下げない（先に〔口: 答えを受け取る〕で書き戻す）")
        return []
    if 状 == _表.値の字("確認ページ", "状況", "差し替え"):
        赤.append("その確認ページは差し替えた前の版＝今配っている版の URL を渡す")
        return []
    try:
        全 = int(行["問いの数"] or 0)
    except ValueError:
        全 = 0
    if 全 > 数:
        知らせ.append(f"確認ページの問い {全} のうち {数} を下げた＝残る問いへの答えは受け付ける（状況は変えない）")
        return []
    return [頁.取り下げの行(行)]


def 取り下げの手順(格子たち: dict, 問いの鍵たち, 訳: str, *, 今日: str, 版: str | None = None, 会社: str | None = None,
              確認ページの行たち=None, 確認ページ: str | None = None) -> dict:
    """格子たち＝質問と回答の今のタブ（`質問と回答.読む` が受ける形・問い が要る）。会社＝管理表「確認ページ」の 会社 の字
    （確認ページの受付も止める時だけ要る）。"""
    赤, 知らせ, 手順, 記録 = [], [], [], []
    訳 = _字(訳)
    if not 訳:
        赤.append("取り下げの訳が空＝なぜ下げたかを 1 行で渡す")
    if "\n" in 訳:
        赤.append("取り下げの訳は 1 行で（改行は使わない）")
    if 版 is not None and not 頁.版の字の形.fullmatch(_字(版)):
        赤.append(f"版 {版!r} は 版の字（YYYY.MM-v<n>）でない")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", _字(今日)):
        赤.append(f"今日 {今日!r} は YYYY-MM-DD でない")
    鍵たち = list(dict.fromkeys(_字(x) for x in (問いの鍵たち or []) if _字(x)))
    if not 鍵たち:
        赤.append("下げる問いの鍵が無い")
    if not isinstance(格子たち, dict):
        赤.append("格子たち は 質問と回答 のタブの名 → 格子 で渡す")
    if 赤:
        return {"手順": [], "管理表の行": [], "記録": [], "知らせ": 知らせ, "赤": 赤}
    問いたち = {}
    for q in qa.読む(格子たち).問いたち:
        if q.鍵:
            問いたち[_鍵(q.鍵)] = q   # 同じ鍵が幾つもあれば下の行
    for 鍵 in 鍵たち:
        q = 問いたち.get(_鍵(鍵))
        if q is None or q.行 is None:
            赤.append(f"{鍵} : 質問と回答の 問い に無い＝下げられない")
        elif q.状態 == qa.取り下げ:
            continue
        elif q.状態 == qa.答えた:
            赤.append(f"{鍵} : もう答えた問い＝下げない（答えを黙って捨てない）")
        else:
            手順 += qa.取り下げる(q)
            記録.append({"問いの鍵": q.鍵, "する": "取り下げ", "訳": 訳, "版": _字(版), "日": _字(今日)})
    管理表の行 = []
    if 確認ページ is not None or 確認ページの行たち is not None:
        if not _字(確認ページ) or 確認ページの行たち is None or not _字(会社):
            赤.append("確認ページの受付を止めるには 会社・確認ページ（配った版の URL）・確認ページの行たち を渡す")
        else:
            管理表の行 = _台帳の行(確認ページの行たち, _字(会社), _字(確認ページ), len(鍵たち), 赤, 知らせ)
    if 赤:
        return {"手順": [], "管理表の行": [], "記録": [], "知らせ": 知らせ, "赤": 赤}
    return {"手順": 手順, "管理表の行": 管理表の行, "記録": 記録, "知らせ": 知らせ, "赤": []}


def _口(入力: dict) -> dict:
    return 取り下げの手順(入力["格子たち"], 入力["問いの鍵たち"], 入力.get("訳", ""), 今日=入力["今日"], 版=入力.get("版"),
                   会社=入力.get("会社"), 確認ページの行たち=入力.get("確認ページの行たち"), 確認ページ=入力.get("確認ページ"))


if __name__ == "__main__":
    try:
        out = _口(json.load(sys.stdin))
    except (取り下げの誤り, KeyError) as e:
        out = {"手順": [], "管理表の行": [], "記録": [], "知らせ": [], "赤": [f"{type(e).__name__}: {e}"]}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1, default=str)
    print()
    sys.exit(2 if out.get("赤") else 0)
