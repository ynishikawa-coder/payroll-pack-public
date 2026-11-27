#!/usr/bin/env python3
"""出す — 1 会社・1 支給月・1 回を、読む → 回す → 出す前の照らし → 書く の 1 つの命令で出す（パックが自分で Drive を開く）。

使い方:
  python3 出口/出す.py --会社 <会社> --支給月 <YYYY-MM> --回 <給与|賞与> [--根 <id>]
                      [--鍵の変数名 GOOGLE_DRIVE_SA_JSON] [--試しに書かない] [--課題の材料 <json>]

- Drive は drive口（窓3）の 開く で開く。鍵は環境の変数の名で受ける（値は受けない・書かない）。根の id は --根 か
  環境の変数 PAYROLL_OFFICE_ROOT_ID。会社の置き場は drive口.置き場.会社の置き場 で引き、出す置き場へ で読む鍵へ写す
  （1_決まり の子と 3_月ごと/<月>/2_出す物 は名で引く・ここで id を組まない・書く前に何も作らない）。
- 回す・照らす・仮の判定はパックの在る口を呼ぶだけ（月次.月を回す／賞与を回す・月次.計算の元・
  plugins/payroll-agent/bin/出す前の照らし.py の 照らす・管理表の行・出した物の行）。ここで計算・照らしを足さない。
- 照らしが赤・仮が 1 人でも残る（月次の 待つ訳・外した人・仮の人の行）＝何も書かず、訳（誰の・どの照らし）を
  stdout に JSON で出して exit 2。課題の材料（開いた課題・起票していない穴の照らしの元）はパックが読めないので殻が
  --課題の材料 で渡す（渡さなければ照らしが赤）。緑の時だけ 2_出す物・9_履歴・管理表 へ書く。--試しに書かない は緑でも書かない（exit 0）。
exit: 0＝出した（か試しで緑）／2＝止めた（何も書いていない）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Callable

根の場所 = Path(__file__).resolve().parents[1]
if str(根の場所) not in sys.path:
    sys.path.insert(0, str(根の場所))

import drive口  # noqa: E402
from 出口 import 名と版  # noqa: E402
from 初期設定 import 型の口  # noqa: E402

出す置き = 名と版.出す置き場   # 名は型の正本から引く（直に書かない）
履歴置き = 名と版.履歴の置き場

回の名 = {"給与": "月", "月": "月", "賞与": "賞与"}
フォルダのmime = "application/vnd.google-apps.folder"
_照らしの場所 = 根の場所 / "plugins" / "payroll-agent" / "bin" / "出す前の照らし.py"


def _照らしの口():
    """出す前の照らし（判定の正本は plugin の 1 か所）を読む。写さない。"""
    bin_ = str(_照らしの場所.parent)
    if bin_ not in sys.path:
        sys.path.insert(0, bin_)
    spec = importlib.util.spec_from_file_location("出す前の照らし_出す道", _照らしの場所)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def 殻の支給月(支給月: str) -> str:
    """命令の `YYYY-MM` → 月次・照らしが受ける殻の字 `YYYY.MM支給`（字の正本は 出口/名と版.殻の支給月か で照らす）。"""
    from 出口 import 名と版
    s = str(支給月).strip()
    if 名と版.殻の支給月か(s):
        return s
    y, _, m = s.partition("-")
    x = f"{y}.{m.zfill(2)}支給" if y.isdigit() and m.isdigit() else s
    if not 名と版.殻の支給月か(x):
        raise ValueError(f"支給月 {支給月!r} は YYYY-MM でない")
    return x


# ── 1. 読む・回す（パックの月次を呼ぶだけ） ─────────────────────────────
def _タブ(口, シートid, タブ) -> list[list[str]]:
    return 口.表を読む(シートid, f"'{タブ}'!A1:ZZ")


def _字(口, file_id) -> str:
    return 口.ファイルを読む(file_id).decode("utf-8")


def 読んで回す(口, 置き場: dict, 会社: str, 支給月: str, 回: str) -> tuple[dict, dict, list[str]]:
    """会社の置き場から計算の元を読み、月次.月を回す／賞与を回す と 月次.計算の元 を呼ぶ。返り: (回した物, 計算の元, 赤)。
    読めない物が 1 つでもあれば赤（黙って空で回さない）。"""
    import 月次
    from 月次 import 年の台帳を起こす as 年
    from 出口 import 証明
    赤: list[str] = []
    要る = ["マスタ", "台帳", "給与のルール"] + (["作業のルール", "質問と回答"] if 回 == "月" else [])
    欠け = [k for k in 要る if not 置き場.get(k)]
    if 欠け:
        return {}, {}, [f"置き場: 会社 {会社} の置き場に {'・'.join(欠け)} が無い（drive口.置き場.会社の置き場）＝計算の元を読めない"]

    def 読む(シート, タブ, どこ):
        try:
            return _タブ(口, シート, タブ)
        except Exception as e:  # noqa: BLE001  読めない＝計算の元が欠ける＝止める
            赤.append(f"{どこ} の「{タブ}」が読めない（{type(e).__name__}: {e}）＝計算の元が欠ける")
            return None

    マスタ = {t: 読む(置き場.get("事務所") if t == "事務所" else 置き場["マスタ"], "既定" if t == "事務所" else t,
                  型の口.道("事務所", "事務所の設定") if t == "事務所" else 型の口.名("マスタ"))
            for t in 証明.計算が読むマスタのタブ()}
    賞与の元 = getattr(月次, "賞与の元", None)
    元のタブ = getattr(賞与の元, "鍵", None)
    台帳のタブ = tuple(getattr(月次, "タブの扱い", None) or ()) if 回 == "賞与" else \
        tuple(t for t in 年.台帳のタブ if t != 元のタブ)
    台帳 = {t: 読む(置き場["台帳"], t, "年の台帳") for t in 台帳のタブ}
    文 = {}
    for k in [k for k in ("給与のルール", "作業のルール") if 置き場.get(k)]:
        try:
            文[k] = _字(口, 置き場[k])
        except Exception as e:  # noqa: BLE001
            赤.append(f"{k}.md が読めない（{type(e).__name__}: {e}）")
    問いの表 = 読む(置き場["質問と回答"], "質問と回答", 型の口.道("決まり", "質問と回答")) if 置き場.get("質問と回答") else None
    if 赤:
        return {}, {}, 赤
    try:
        if 回 == "賞与":
            b = 月次.賞与の元を読む(_タブ(口, 置き場["台帳"], 元のタブ), 会社, 支給月)
            タブ = {**マスタ, **台帳}
            引数 = dict(b["賞与の引数"])
            o = 月次.賞与を回す(支給月, 会社, タブ, b["支給一覧"], 支給日=str(b["支給日"]), 出口={},
                            給与のルール=文["給与のルール"], 問いの表=問いの表, **引数)
            元 = 月次.計算の元(タブ, (), 文["給与のルール"], 支給一覧=b["支給一覧"], 法の線=None,
                          賞与の引数={"支給日": str(b["支給日"]), **引数})
            return o, 元, []
        import inspect
        params = inspect.signature(月次.月を回す).parameters
        kw = {t: v for t, v in 台帳.items() if t in params}
        タブ = {**マスタ, **{t: v for t, v in 台帳.items() if t not in params}}
        前 = None
        if 置き場.get("前の年の台帳"):
            前 = {t: _タブ(口, 置き場["前の年の台帳"], t) for t in 年.台帳のタブ}
        y = 年.前の年の確定した勤怠(int(支給月[:4]), 前, 社員=マスタ.get("社員"))
        材料 = dict(前の確定した勤怠=y["前の確定した勤怠"], 前の確定した勤怠の区間=y["前の確定した勤怠の区間"],
                  月の数字=[], 有給の値=None, 法の線=None)
        o = 月次.月を回す(支給月, 会社, タブ, **kw, **材料, 出口={}, 給与のルール=文["給与のルール"],
                       作業のルール=文.get("作業のルール"), 問いの表=問いの表, 前の締めの記録=y["前の締めの記録"])
        元 = 月次.計算の元(タブ, (), 文["給与のルール"],
                      **{k: kw[k] for k in ("確定した勤怠", "確定した勤怠の区間") if k in kw}, **材料)
        return o, 元, []
    except Exception as e:  # noqa: BLE001  パックの口が拒んだ＝出さない
        return {}, {}, [f"回す: パックの口が止めた（{type(e).__name__}: {e}）"]


# ── 2. 仮の判定・照らし（パックの口の返りを読むだけ） ─────────────────────
def 仮の赤(o: dict) -> list[str]:
    """月次の返りに仮が 1 人でも残れば赤（月次の 待つ訳・外した人・仮の人の行をそのまま訳にする）。"""
    赤 = [f"仮: {w}" for w in o.get("待つ訳") or ()]
    赤 += [f"仮: 外した人 NO {a.get('NO', '?')}（{'・'.join(a.get('理由') or ()) or '仮が残る'}）"
          for a in o.get("外した人") or ()]
    if not 赤 and o.get("仮の人の行"):
        NO = sorted({str(a.get("NO", "?")) for a in o["仮の人の行"]})
        赤 += [f"仮: NO {n} に仮が残る（仮の人の行）" for n in NO]
    return 赤


def 出す物たち(o: dict) -> list:
    xs = [o["取り込み"]] if o.get("取り込み") is not None else []
    xs += list(o.get("支給控除一覧") or ())
    return xs + ([o["有給休暇管理表"]] if o.get("有給休暇管理表") is not None else [])


def 前の版の名(口, 置き場: dict) -> tuple[dict, list[str]]:
    out, 赤 = {}, []
    for k, 置 in (("今ある名", 出す置き), ("履歴にある名", 履歴置き)):
        if not 置き場.get(置):
            赤.append(f"置き場: {置} が無い＝前の版の番号が分からない")
            continue
        try:
            out[k] = [x["name"] for x in 口.子を並べる(置き場[置]) if x.get("mimeType") != フォルダのmime]
        except Exception as e:  # noqa: BLE001
            赤.append(f"{置}/ の名が読めない（{type(e).__name__}: {e}）")
    return out, 赤


def _素の出す物(d) -> dict:
    return {"物": d.物, "名": {"フォルダ": d.名.フォルダ, "名": d.名.名}, "表": [list(r) for r in d.表]}


課題の材料の名 = ("課題", "課題の id", "閉じた状態", "月の本文")


def 照らしの入力(会社, 支給月, o, 元, 名たち, 課題の材料: dict | None = None) -> dict:
    """課題の材料（案件の置き場の課題・閉じた状態・月の本文）はパックが読めない＝殻が渡す。渡さなければ照らしが赤（黙って空で通さない）。"""
    from 出口 import 証明
    課題 = {k: (課題の材料 or {}).get(k) for k in 課題の材料の名}
    return {"会社": 会社, "支給月": 支給月, "出す物": [_素の出す物(d) for d in 出す物たち(o)], "証明": o.get("証明") or {},
            "外した人": len(o.get("外した人") or ()), "有給の止めた人": len(o.get("有給の止めた人") or ()), "納品": False,
            "材料": {"会社": 会社, "パックの版": 証明.パックの版(), "計算の元": 元, **課題, **名たち}}


# ── 3. 書く（緑の時だけ） ────────────────────────────────────────────
def _置く(口, 置き場, d, 書いた: list) -> dict:
    """新しい版を 2_出す物 に置き、置けてから前の版を 9_履歴 へ移す（2_出す物 には最新の版 1 つだけ）。
    移す口の有無は書く前に照らしてある（_移せない）。書けた物は 書いた に順に足す（途中で止まった時の訳）。"""
    if getattr(d, "渡し方", "表") == "CSV":
        fid = 口.ファイルを置く(置き場[出す置き], d.名.名, d.csvの中身(), "text/csv")
    else:
        fid = 口.シートを作る(置き場[出す置き], d.名.名)
        書いた.append(f"{出す置き}: {d.名.名}（作った・中身はまだ）")
        口.表へ書く(fid, f"'{d.物}'!A1", [list(r) for r in d.表])
        書いた.pop()
    書いた.append(f"{出す置き}: {d.名.名}")
    for n in d.名.履歴へ移す:
        前 = 口.名で引く(置き場[出す置き], n)
        if 前 is not None:
            口.移す(前["id"], 置き場[履歴置き])
            書いた.append(f"{履歴置き}へ移した: {n}")
    リンク = getattr(口, "リンク", None)   # drive口 にリンクの口が無い＝id を返し殻がリンクに直す（後でパックを直す一覧）
    return {"物": d.物, "名": d.名.名, "url": リンク(fid) if リンク else fid}


def _移せない(口, 置き場, xs) -> list[str]:
    """前の版が 2_出す物 に在るのに drive口 に 移す が無い＝写して残すと 2_出す物 に古い版が残り 9_履歴 に重なる。
    名と版の決まり（2_出す物 には最新の版 1 つだけ）を曲げず、何も置かずに止める（drive口 に 移す を足すのは後でパックを直す一覧）。"""
    if callable(getattr(口, "移す", None)):
        return []
    前 = [n for d in xs for n in d.名.履歴へ移す if 口.名で引く(置き場[出す置き], n) is not None]
    return [f"前の版 {n} を {出す置き} から {履歴置き} へ移せない（drive口 に 移す が無い・写して残すと最新の版 1 つだけの決まりが崩れる）"
            for n in 前]


def _管理表へ(口, 置き場, タブ, 行たち: list[dict]) -> None:
    """管理表のタブへ、見出しの並びで行を書く（会社・支給月の鍵が合う行は上書き・無ければ足す）。"""
    今 = _タブ(口, 置き場["管理表"], タブ)
    if not 今:
        raise RuntimeError(f"管理表の「{タブ}」に見出しが無い")
    h = 今[0]
    for 行 in 行たち:
        外 = sorted(set(行) - set(h))
        if 外:
            raise RuntimeError(f"管理表の「{タブ}」に無い列 {外}")
        鍵 = [k for k in ("会社", "支給月", "物") if k in 行 and k in h]
        当たり = [i for i, r in enumerate(今[1:], start=2)
                if all((r[h.index(k)] if h.index(k) < len(r) else "") == str(行[k]) for k in 鍵)]
        値 = [str(行.get(k, "")) for k in h]
        if 当たり:
            口.表へ書く(置き場["管理表"], f"'{タブ}'!A{当たり[0]}", [値])
        else:
            口.表へ足す(置き場["管理表"], f"'{タブ}'!A1", [値])


def 出す(口, 置き場: dict, 会社: str, 支給月: str, 回: str, *, 書かない: bool = False,
       回す: Callable | None = None, 課題の材料: dict | None = None) -> tuple[int, dict]:
    """1 つの命令の芯。返り: (exit, stdout に出す JSON)。止める時は何も書かない。"""
    回 = 回の名.get(回, "")
    if not 回:
        return 2, {"出した": False, "赤": ["形: 回は 給与 か 賞与"]}
    try:
        支給月 = 殻の支給月(支給月)
    except ValueError as e:
        return 2, {"出した": False, "赤": [f"形: {e}"]}
    o, 元, 赤 = (回す or 読んで回す)(口, 置き場, 会社, 支給月, 回)
    if 赤:
        return 2, {"出した": False, "赤": 赤}
    赤 = 仮の赤(o)
    if 赤:
        return 2, {"出した": False, "赤": 赤}
    名たち, 赤 = 前の版の名(口, 置き場)
    if 赤:
        return 2, {"出した": False, "赤": 赤}
    from 出口 import 名と版, 証明
    sys.path.insert(0, str(根の場所 / "plugins" / "payroll-agent" / "bin"))
    照 = _照らしの口()
    import パックの場所 as 場所
    入力 = 照らしの入力(会社, 支給月, o, 元, 名たち, 課題の材料)
    赤 = 照.照らす(入力, 置き場=場所.出す物の置き場(根の場所), 証明の口=証明, 名の口=名と版)
    if 赤:
        return 2, {"出した": False, "赤": [f"出す前の照らし: {r}" for r in 赤]}
    from 管理表 import 管理表 as 表
    回2, 管理表のタブ, 赤 = 照.回と管理表のタブ(入力, 表.回のタブ)
    if 赤:
        return 2, {"出した": False, "赤": 赤}
    xs = 出す物たち(o)
    結果 = {"出した": False, "通す": True, "会社": 会社, "支給月": 支給月, "回": 回2,
            "出す物": [d.名.名 for d in xs]}
    if 書かない:
        return 0, {**結果, "試し": "書いていない"}
    今の行 = _タブ(口, 置き場["管理表"], 管理表のタブ)
    今の理由 = ""
    if 今の行 and "止まりの理由" in 今の行[0]:
        h = 今の行[0]
        for r in 今の行[1:]:
            if len(r) > h.index("止まりの理由") and r[h.index("会社")] == 会社 and r[h.index("支給月")] == 支給月:
                今の理由 = r[h.index("止まりの理由")]
    行 = 照.管理表の行(入力, 今の理由)
    出した物の見出し = (_タブ(口, 置き場["管理表"], 表.出した物のタブ()) or [[]])[0]
    外 = [f"管理表の「{管理表のタブ}」に列 {k} が無い" for k in 行 if k not in (今の行[0] if 今の行 else [])]
    外 += [f"管理表の「{表.出した物のタブ()}」に列 {k} が無い" for k in ("会社", "支給月", "回", "物", "今の版", "リンク")
          if k not in 出した物の見出し]
    if 外:   # 置く前に照らす＝出す物だけ置いて管理表を書けない半端を作らない
        return 2, {"出した": False, "赤": [f"管理表: {x}" for x in 外]}
    赤 = _移せない(口, 置き場, xs)
    if 赤:
        return 2, {"出した": False, "赤": 赤}
    書いた: list[str] = []
    try:
        置いた = [_置く(口, 置き場, d, 書いた) for d in xs]
        出した物 = 照.出した物の行(入力, 回2, 置いた)
        今日 = date.today().isoformat()
        _管理表へ(口, 置き場, 管理表のタブ, [{**行, **({"更新日": 今日} if "更新日" in (今の行[0] if 今の行 else []) else {})}])
        書いた.append(f"管理表: {管理表のタブ}")
        _管理表へ(口, 置き場, 表.出した物のタブ(), 出した物)
        書いた.append(f"管理表: {表.出した物のタブ()}")
    except Exception as e:   # Drive の途中の失敗＝どこまで書いたかを JSON で返す（戻すのは人が 書いた を見て決める）
        return 2, {"出した": False, "赤": [f"書く途中で止まった: {type(e).__name__}: {e}"], "書いた": 書いた}
    return 0, {**結果, "出した": True, "置いた": 置いた, "書いた": 書いた}


def 出す置き場へ(口, 会社の置き場: dict, 支給月: str) -> tuple[dict, list[str]]:
    """drive口.置き場.会社の置き場 が返す {物の名: id} を、出す.py が読む鍵へ写す（ここで id を組まない・何も作らない）。
    マスタ←2_マスタ・台帳←台帳_<支給月の年>（前の年の台帳←台帳_<年-1>・在れば）・事務所←事務所の設定・
    給与のルール／作業のルール／質問と回答←1_決まり の子を名で引く・2_出す物←3_月ごと/<支給月の月のフォルダ>/2_出す物・
    9_履歴・管理表 はそのまま。引けない物は入れず赤に訳を足す（読んで回す・前の版の名 が欠けを止める）。"""
    from drive口 import 置き場 as 置
    from 芯 import 支給月の字
    p, 赤 = 会社の置き場, []
    try:
        年, 月 = int(支給月[:4]), int(支給月[5:7])
    except ValueError:
        return {}, [f"支給月: {支給月} が YYYY-MM でない"]
    out = {k: p[k] for k in (履歴置き, 型の口.名("管理表")) if p.get(k)}
    for 鍵, 名 in (("マスタ", 型の口.名("マスタ")), ("台帳", 型の口.台帳の名(年)),
                  ("前の年の台帳", 型の口.台帳の名(年 - 1)), ("事務所", 型の口.名("事務所の設定"))):
        if p.get(名):
            out[鍵] = p[名]
    決まり = p.get(型の口.名("決まり"))
    for 鍵 in ("給与のルール", "作業のルール", "質問と回答"):
        if not 決まり:
            break
        try:
            x = 口.名で引く(決まり, 型の口.名(鍵))
        except Exception as e:  # noqa: BLE001  同じ名が 2 つ等＝選ばず止める
            赤.append(f"置き場: {型の口.名('決まり')}/{型の口.名(鍵)} が引けない（{type(e).__name__}: {e}）")
            continue
        if x:
            out[鍵] = x["id"]
    月ごと = p.get(型の口.名("月ごと"))
    if 月ごと:
        try:
            当たり = [x["name"] for x in 口.子を並べる(月ごと)
                    if x.get("mimeType") == フォルダのmime
                    and (支給月の字.置き場の字を読む(x["name"]) or ())[:2] == (年, 月)]
            if len(当たり) != 1:
                赤.append(f"置き場: {型の口.名('月ごと')} に {支給月} 支給の月のフォルダが {len(当たり)} つ"
                         "（1 つでなければ選ばず止める）")
            else:
                out[出す置き] = 置.月の置き場(口, 月ごと, 当たり[0])[出す置き]
        except Exception as e:  # noqa: BLE001
            赤.append(f"置き場: {型の口.名('月ごと')} の月のフォルダが引けない（{type(e).__name__}: {e}）")
    return out, 赤


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="1 会社・1 支給月・1 回を出す")
    ap.add_argument("--会社", required=True)
    ap.add_argument("--支給月", required=True)
    ap.add_argument("--回", required=True)
    ap.add_argument("--根")
    ap.add_argument("--鍵の変数名", default=drive口.鍵の変数名の既定)
    ap.add_argument("--試しに書かない", action="store_true")
    ap.add_argument("--課題の材料", help="課題・課題の id・閉じた状態・月の本文 の JSON file（案件の置き場から殻が組む）")
    a = ap.parse_args(argv)
    課題の材料 = None
    if a.課題の材料:
        try:
            課題の材料 = json.loads(Path(a.課題の材料).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(json.dumps({"出した": False, "赤": [f"課題の材料が読めない: {e}"]}, ensure_ascii=False))
            return 2
    根 = a.根 or os.environ.get(drive口.根の変数名の既定)
    if not 根:
        print(json.dumps({"出した": False, "赤": [f"根: --根 か 環境の変数 {drive口.根の変数名の既定} が要る"]},
                         ensure_ascii=False))
        return 2
    try:
        口 = drive口.開く(鍵の変数名=a.鍵の変数名)
        from drive口 import 置き場 as 置
        置き場, 赤 = 出す置き場へ(口, 置.会社の置き場(口, 根, a.会社), a.支給月)
    except Exception as e:  # noqa: BLE001  開けない・置き場が引けない＝何も書かない
        print(json.dumps({"出した": False, "赤": [f"Drive: {type(e).__name__}: {e}"]}, ensure_ascii=False))
        return 2
    if 赤:   # 置き場が 1 つに決まらない＝何も書かない
        print(json.dumps({"出した": False, "赤": 赤}, ensure_ascii=False, indent=1))
        return 2
    code, out = 出す(口, 置き場, a.会社, a.支給月, a.回, 書かない=a.試しに書かない, 課題の材料=課題の材料)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
