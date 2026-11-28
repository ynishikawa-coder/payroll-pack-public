#!/usr/bin/env python3
"""出す — 1 会社・1 支給月・1 回を、読む → 回す → 仮の判定 → 書く の 1 つの命令で出す（パックが自分で Drive を開く）。

使い方:
  python3 出口/出す.py --会社 <会社> --支給月 <YYYY-MM> --回 <給与|賞与> [--根 <id>]
                      [--鍵の変数名 GOOGLE_DRIVE_SA_JSON] [--試しに書かない]

- Drive は drive口（窓3）の 開く で開く。鍵は環境の変数の名で受ける（値は受けない・書かない）。根の id は --根 か
  環境の変数 PAYROLL_OFFICE_ROOT_ID。会社の置き場は drive口.置き場.会社の置き場 で引き、出す置き場へ で読む鍵へ写す
  （1_決まり の子と 3_月ごと/<月>/2_出す物 は名で引く・ここで id を組まない・書く前に何も作らない）。
- 回すのはパックの在る口を呼ぶだけ（月次.月を回す／賞与を回す）。ここで計算を足さない。
  前の版の名（2_出す物/・9_履歴/ の名）は回す前に Drive から読み、月次へ渡す（版の番号を戻さない）。
- 仮が残る人（月次の 待つ訳・外した人・有給の外した人・仮の人の行の NO）は人ごとに除き、残りの人だけを 2_出す物・9_履歴・管理表 へ書く。
  除いた人と理由は stdout の JSON の 除いた人 に返す（会社の全員は待たせない）。出す人が 1 人も残らない・NO の無い
  待つ訳がある・除いた人の行が出す物に残る＝何も書かず exit 2。--試しに書かない は書かない（exit 0）。
- 給与の月は有給の値を毎月 {} から組んで渡し、有給休暇管理表を毎月出す（取り込みがあるのに組めていない＝exit 2）。
  有給の始めの日が空で数えられない人は給与は出し、有給休暇管理表の行だけ出さない（stdout の 有給の止めた人 に NO と理由・
  始めの日を聞く問いは月次の 問い の 有給 に出る）。
exit: 0＝出した（か試しで通る）／2＝止めた（何も書いていない）。
"""
from __future__ import annotations

import argparse
import json
import re
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
_取り込みの物 = ("取り込み", "賞与の取り込み")
有給を出さない頭 = "有給休暇管理表は出していない"   # 前の形（有給の値を渡さない月）の頭。読む時に外すだけ
有給に載せない頭 = "有給休暇管理表に載せていない人"   # 給与は出し、有給休暇管理表に行を出さない人（有給の止めた人）
外した頭 = "外した人"   # 仮が残って出口から外した人と理由（NO ごと・月ごとに書き直す）


def 月次の支給月(支給月: str) -> str:
    """命令の `YYYY-MM` → 月次が受ける字 `YYYY.MM支給`（字の正本は 出口/名と版.月次の支給月か で照らす）。"""
    s = str(支給月).strip()
    if 名と版.月次の支給月か(s):
        return s
    y, _, m = s.partition("-")
    x = f"{y}.{m.zfill(2)}支給" if y.isdigit() and m.isdigit() else s
    if not 名と版.月次の支給月か(x):
        raise ValueError(f"支給月 {支給月!r} は YYYY-MM でない")
    return x


# ── 1. 読む・回す（パックの月次を呼ぶだけ） ─────────────────────────────
# Drive のシート・タブの名はここで組まない: シートは 型の口.名、タブは役の名で渡し、Drive のタブの名（型 39 の 1_社員 など）
# は drive口.置き場 の タブを読む／マスタを読む が 型の口.タブの名・タブの本 で引く。


def _マスタの本たち() -> tuple[str, ...]:
    """マスタのタブが在る Drive の本の名（型 39: マスタ・マスタの変更の記録）。会社の置き場の鍵と同じ字。"""
    シート = 型の口.名("マスタ")
    return tuple(dict.fromkeys(型の口.タブの本(シート, t) for t in 型の口.マスタのタブたち()))


def _台帳を読む(口, シートid: str, タブたち, 赤: list, 知らせ: list, どこ: str) -> dict:
    """年の台帳のタブ（役の名）→ {役: 格子}。Drive の同じタブを 2 つの役が持つ時（型の「同じタブ」）は 1 回だけ読み、
    同居する役は持ち主も持ち主でない役（締めの記録）も、その役の列（型の口.見出し）だけを列の名で抜いて渡す
    （同居のタブはほかの役の列も持つ。前の年の台帳を起こす口は見出しが型と一字も違わない事を求める）。
    その役の列が無い・同じ名の列が 2 つある時は 赤 に足す（空と読まない・ほかの役の格子を黙って渡さない）。読めないタブも 赤。"""
    from drive口 import 置き場 as 置
    シート = 型の口.名("台帳")
    持ち主たち = {t.get("同じタブ") for x in 型の口.型()["シート"] if x["シート"] == シート for t in x["タブ"]} - {None}
    読んだ: dict[str, list | None] = {}
    out = {}
    for t in タブたち:
        名 = 型の口.タブの名(シート, t)
        if 名 not in 読んだ:
            try:
                読んだ[名] = 置.タブを読む(口, シートid, シート, t)
            except drive口.上限:   # 上限＝読めた物が欠けたのではない＝別の訳に化けさせず main で止める
                raise
            except Exception as e:  # noqa: BLE001  読めない＝計算の元が欠ける＝止める
                読んだ[名] = None
                赤.append(f"{どこ} の「{名}」が読めない（{type(e).__name__}: {e}）＝計算の元が欠ける")
        g = 読んだ[名]
        if g is None:
            continue
        if 型の口.タブ(シート, t).get("同じタブ") or t in 持ち主たち:
            g = _列の名で抜く(g, tuple(型の口.見出し(シート, t)), 赤, f"{どこ} の「{名}」の {t} の列")
            if g is None:
                continue
        out[t] = g
    return out


def _列の名で抜く(g: list, 列たち: tuple, 赤: list, どこ: str) -> list | None:
    """格子（get_values の形）→ 列たち だけの格子（見出しは 列たち・行は列の名で引いた値）。列が無い・同じ名が 2 つなら 赤 で None。"""
    頭 = [str(x).strip() for x in (g[0] if g else [])]
    無い = [c for c in 列たち if c not in 頭]
    二つ = [c for c in 列たち if 頭.count(c) > 1]
    if 無い or 二つ:
        赤.append(f"{どこ}: " + "・".join(
            ([f"見出しに {'・'.join(無い)} が無い"] if 無い else []) + ([f"同じ名の列 {'・'.join(二つ)} が 2 つある"] if 二つ else []))
            + "＝読めないので止める（空と読まない）")
        return None
    位置 = [頭.index(c) for c in 列たち]
    return [list(列たち), *[[(r[i] if i < len(r) else "") for i in 位置] for r in g[1:]]]


def _字(口, file_id) -> str:
    return 口.字を読む(file_id)


def 読んで回す(口, 置き場: dict, 会社: str, 支給月: str, 回: str) -> tuple[dict, list[str]]:
    """会社の置き場から計算の元を読み、月次.月を回す／賞与を回す を呼ぶ。返り: (回した物, 赤)。
    読めない物が 1 つでもあれば赤（黙って空で回さない）。前の版の名は Drive の 2_出す物/・9_履歴/ から読んで月次へ渡す。"""
    import 月次
    from 月次 import 年の台帳を起こす as 年
    名たち, 赤 = 前の版の名(口, 置き場)   # 止める訳は全部集めて最後に 1 回で返す（最初の誤りで返さない）
    要る = [*_マスタの本たち(), "顧客ID", "台帳", "給与のルール", "事務所のルール", "質問と回答"] + \
        (["作業のルール"] if 回 == "月" else [])
    欠け = [k for k in 要る if not 置き場.get(k)]
    if 欠け:
        赤.append(f"置き場: 会社 {会社} の置き場に {'・'.join(欠け)} が無い（drive口.置き場.会社の置き場）＝計算の元を読めない")
    if not 置き場.get("台帳") or not 置き場.get("事務所のルール"):   # この 2 つが無いと下の読みが組めない＝ここまでの訳で返す
        return {}, 赤

    from drive口 import 置き場 as 置
    知らせ: list[str] = []

    def 読む(f, どこ, タブ):
        try:
            return f()
        except drive口.上限:   # 上限＝読めた物が欠けたのではない＝別の訳に化けさせず main で止める
            raise
        except Exception as e:  # noqa: BLE001  読めない＝計算の元が欠ける＝止める
            赤.append(f"{どこ} の「{タブ}」が読めない（{type(e).__name__}: {e}）＝計算の元が欠ける")
            return None

    シート = 型の口.名("マスタ")
    マスタ = {t: 読む(lambda t=t: 置.マスタを読む(口, 置き場, t), 型の口.タブの本(シート, t), 型の口.タブの名(シート, t))
            for t in 型の口.マスタのタブたち() if 置き場.get(型の口.タブの本(シート, t))}
    if 置き場.get("事務所"):   # 事務所の設定が在る置き場だけ（無い置き場では読まない＝無いだけで止めない）
        設定 = 型の口.名("事務所の設定")
        マスタ["事務所"] = 読む(lambda: 置.タブを読む(口, 置き場["事務所"], 設定, "既定"),
                            型の口.Driveの名("事務所の設定"), 型の口.タブの名(設定, "既定"))
    賞与の元 = getattr(月次, "賞与の元", None)
    元のタブ = getattr(賞与の元, "鍵", None)
    台帳のタブ = tuple(getattr(月次, "タブの扱い", None) or ()) if 回 == "賞与" else \
        tuple(t for t in 年.台帳のタブ if t != 元のタブ)
    台帳の名 = 型の口.台帳の名(int(支給月[:4]))
    台帳 = _台帳を読む(口, 置き場["台帳"], 台帳のタブ, 赤, 知らせ, 台帳の名)
    賞与の格子 = None
    if 回 == "賞与":
        賞与の格子 = _台帳を読む(口, 置き場["台帳"], (元のタブ,), 赤, 知らせ, 台帳の名).get(元のタブ)
    前 = None
    if 回 == "月" and 置き場.get("前の年の台帳"):
        前 = _台帳を読む(口, 置き場["前の年の台帳"], 年.台帳のタブ, 赤, 知らせ, 型の口.台帳の名(int(支給月[:4]) - 1))
    文 = {}
    for k in [k for k in ("給与のルール", "作業のルール") if 置き場.get(k)]:
        try:
            文[k] = _字(口, 置き場[k])
        except drive口.上限:   # 上限＝読めた物が欠けたのではない＝別の訳に化けさせず main で止める
            raise
        except Exception as e:  # noqa: BLE001
            赤.append(f"{k}.md が読めない（{type(e).__name__}: {e}）")
    出口 = _出口を組む(口, 置き場, 名たち, 赤)
    表 = _質問と回答を読む(口, 置き場, 赤) if 置き場.get("質問と回答") else None
    出し済み = 出し済みの月たち(口, 置き場, 会社, 赤)
    if 赤:
        return {}, 赤
    try:
        if 回 == "賞与":
            b = 月次.賞与の元を読む(賞与の格子, 会社, 支給月)
            タブ = {**マスタ, **台帳}
            引数 = dict(b["賞与の引数"])
            o = 月次.賞与を回す(支給月, 会社, タブ, b["支給一覧"], 支給日=str(b["支給日"]), 出口=出口,
                            給与のルール=文["給与のルール"], 質問と回答=表, 顧客ID=置き場["顧客ID"],
                            出し済みの月たち=出し済み, **引数)
            return _知らせを付ける(o, 知らせ), []
        import inspect
        params = inspect.signature(月次.月を回す).parameters
        kw = {t: v for t, v in 台帳.items() if t in params}
        タブ = {**マスタ, **{t: v for t, v in 台帳.items() if t not in params}}
        y = 年.前の年の確定した勤怠(int(支給月[:4]), 前, 社員=マスタ.get("社員"))
        材料 = dict(前の確定した勤怠=y["前の確定した勤怠"], 前の確定した勤怠の区間=y["前の確定した勤怠の区間"],
                  # 有給の値は毎月 {} から組んで渡す（有給休暇管理表を毎月出す・有給の関所を毎月通す）。法の線は渡さない＝
                  # 月を回す が法の表/ から期間で引く（賞与 と同じ道）
                  月の数字=[], 有給の値={})
        o = 月次.月を回す(支給月, 会社, タブ, **kw, **材料, 出口=出口, 給与のルール=文["給与のルール"],
                       作業のルール=文.get("作業のルール"), 質問と回答=表, 顧客ID=置き場["顧客ID"],
                       出し済みの月たち=出し済み, 前の締めの記録=y["前の締めの記録"],
                       締めの記録が要る=True)
        return _知らせを付ける(o, 知らせ), []
    except drive口.上限:   # 上限＝読めた物が欠けたのではない＝別の訳に化けさせず main で止める
        raise
    except Exception as e:  # noqa: BLE001  パックの口が拒んだ＝出さない
        return {}, [f"回す: パックの口が止めた（{type(e).__name__}: {e}）"]


def _質問と回答を読む(口, 置き場: dict, 赤: list[str]):
    """事務所の 質問と回答（1 冊・3 タブ 問い・答え・振り分け）を 初期設定/質問と回答.py の 読む で読んだ表にする。
    読む口はその 1 つだけ（タブの名・列をここで組まない）。口が無い・読めない時は赤（照らさずに回さない）。"""
    try:
        from 初期設定 import 質問と回答 as 問答
    except ImportError:
        赤.append("質問と回答: 3 タブを読む口（初期設定/質問と回答.py の 読む）が無い＝止まりを照らせないので回さない")
        return None
    try:
        sid = 置き場["質問と回答"]
        return 問答.読む({名: 口.表を読む(sid, drive口.範囲(名)) for 名 in 口.タブを並べる(sid)})
    except drive口.上限:   # 上限＝読めた物が欠けたのではない＝別の訳に化けさせず main で止める
        raise
    except Exception as e:  # noqa: BLE001
        赤.append(f"質問と回答: 読めない（{type(e).__name__}: {e}）＝止まりを照らせないので回さない")
        return None


def 出し済みの月たち(口, 置き場: dict, 会社: str, 赤: list[str]) -> list[str]:
    """管理表「月の状況」の、この会社の 取り込み が空でない行（済・仮＝出した）の支給月。出し直しの候補を分ける元。
    管理表が無い置き場では空（前の月に効く振り分けは止まりのまま＝黙って出し済みと読まない）。読めない時は赤。"""
    if not 置き場.get(_管理表の鍵()):
        return []
    from 管理表 import 管理表 as 表
    try:
        g = _管理表を読む(口, 置き場, 表.回のタブ("月"))
    except drive口.上限:   # 上限＝読めた物が欠けたのではない＝別の訳に化けさせず main で止める
        raise
    except Exception as e:  # noqa: BLE001
        赤.append(f"管理表: 月の状況が読めない（{type(e).__name__}: {e}）＝出し済みの月が分からない")
        return []
    if not g or not {"会社", "支給月", "取り込み"} <= set(g[0]):
        return []
    h = g[0]
    def 値(r, k):
        i = h.index(k)
        return str(r[i]).strip() if i < len(r) else ""
    return sorted({値(r, "支給月") for r in g[1:] if 値(r, "会社") == 会社 and 値(r, "取り込み")} - {""})


def _出口を組む(口, 置き場: dict, 名たち: dict, 赤: list[str]) -> dict | None:
    """月次へ渡す 出口 を組む: 前の版の名（2_出す物/・9_履歴/）＋取り込み（道具＝給与ソフトの呼び名・形）＋支給控除一覧。
    形は事務所のルール.md「給与ソフトと取り込みの形」（会社の呼び名か顧客IDの小見出しが上書き・`形.形をmdから読む`）。
    道具は形の 名＝⑥つなぎ の 道具 と同じ呼び名（欄の対応・渡さない人を口がつなぎから組む鍵）。
    時間の書き方 は月次が会社のマスタ `出口.時間の書き方` から読む（ここで渡さない）。読めない・形が組めない時は赤。"""
    from 出口 import 形 as 形の口
    try:
        d = 形の口.形をmdから読む(_字(口, 置き場["事務所のルール"]), (置き場.get("会社"), 置き場.get("顧客ID")))
        f = 形の口.形を組む(d)
    except drive口.上限:   # 上限＝読めた物が欠けたのではない＝別の訳に化けさせず main で止める
        raise
    except Exception as e:  # noqa: BLE001  形が無い＝取り込みを作れない＝止める
        赤.append(f"{型の口.Driveの名('事務所のルール')} の給与ソフトの形が読めない（{type(e).__name__}: {e}）")
        return None
    出口 = {**名たち, "取り込み": {"道具": f.名, "形": d}, "支給控除一覧": {}}
    from 月次.出口の指定 import 出口の赤   # 正式の出口の形の照らしの正本（月を回す の奥でなく回す前に止める）
    赤.extend(出口の赤(出口))
    return 出口


def _知らせを付ける(o: dict, 知らせ: list[str]) -> dict:
    """読みの知らせ（止めないが人に見せる事）を回した物に付ける。出す の JSON の 知らせ に出る。"""
    if 知らせ and isinstance(o, dict):
        o = {**o, "読みの知らせ": list(知らせ)}
    return o


# ── 2. 仮の判定・照らし（パックの口の返りを読むだけ） ─────────────────────
def 除く人(o: dict) -> tuple[list[dict], list[str]]:
    """月次の返りの 待つ訳・外した人・有給の外した人・仮の人の行 から仮が残る人を NO ごとに集める。返り: (除いた人 [{NO, 理由}], 赤)。
    NO の読めない待つ訳・NO の無い外した人／仮の人の行は誰を除くか決められない＝赤（会社ごと止める）。"""
    理由: dict[str, list[str]] = {}
    赤: list[str] = []
    def 足す(NO, 訳):
        r = 理由.setdefault(str(NO), [])
        if 訳 and 訳 not in r:
            r.append(訳)
    for w in o.get("待つ訳") or ():
        if re.match(r"\s*会社\s*[:：]", str(w)):   # 会社の止まり＝会社の全員が 外した人 に居る（月次 の _止まりを仮へ）。人は下で数える
            continue
        m = re.match(r"\s*NO\s+(\S+?)\s*[:：]\s*(.*)$", str(w))
        if m:
            足す(m.group(1), m.group(2).strip())
        else:
            赤.append(f"仮: 誰の訳か読めない: {w}")
    for 鍵 in ("外した人", "有給の外した人", "仮の人の行"):
        for a in o.get(鍵) or ():
            NO = str(a.get("NO", "")).strip()
            if not NO:   # 誰を除くか決められない＝待つ訳と同じく赤（黙って飛ばさない）
                赤.append(f"仮: NO の無い{鍵}: {a}")
                continue
            足す(NO, "")
            for x in a.get("理由") or ():
                足す(NO, str(x))
    return [{"NO": n, "理由": r or ["仮が残る"]} for n, r in sorted(理由.items())], 赤


def 載せた人(d) -> tuple[set[str] | None, str]:
    """出す物に載せた人の NO（作る口＝書き口・月次 が 出す物.人 に付けた正本を読む。見出しの名から人を当てない＝
    鍵の欄の名・向き（横／縦）に頼らない）。人を持たない・NO が空の出す物は (None, 赤)＝黙って 0 人と読まない。"""
    人 = getattr(d, "人", None)
    物 = getattr(d, "物", "?")
    if 人 is None:
        return None, f"形: 出す物 {物} が載せた人（人）を持たない＝誰を出すか照らせない"
    NO = {str(n).strip() for n in 人}
    if "" in NO:
        return None, f"形: 出す物 {物} の人に NO の無い人が居る"
    return NO, ""


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
        except drive口.上限:   # 上限＝読めた物が欠けたのではない＝別の訳に化けさせず main で止める
            raise
        except Exception as e:  # noqa: BLE001
            赤.append(f"{置}/ の名が読めない（{type(e).__name__}: {e}）")
    return out, 赤


def 回のタブ(回: str) -> tuple[str | None, list[str]]:
    """命令の回（月・賞与）→ 管理表の回のタブ。型に回のタブが無い時は赤（黙って 月の状況 に書かない）。"""
    from 管理表 import 管理表 as 表
    try:
        return 表.回のタブ(回), []
    except Exception as e:  # noqa: BLE001  管理表の 拒む
        return None, [f"管理表の行: {e}"]


def 有給の止めた人(o: dict) -> list[dict]:
    """月次の 有給の止めた人 → [{NO, 理由}]（給与は出す・有給休暇管理表に行を出さない人）。"""
    return [{"NO": str(a.get("NO", "")).strip(), "理由": str(a.get("理由", ""))} for a in o.get("有給の止めた人") or ()]


def 管理表の行(会社: str, 支給月: str, o: dict, 今の止まりの理由: str) -> dict:
    """管理表の回のタブ（月の状況・賞与の状況）へ書く行。除いた人が 0 でない月は 取り込み を 済 にしない。
    前の形の「今の版: …」は止まりの理由から外す（物ごとの今の版とリンクはタブ 出した物 が持つ）。
    有給休暇管理表に行を出さなかった人（有給の止めた人）は NO を止まりの理由の頭に残す（月ごとに書き直す）。
    前の形の「有給休暇管理表は出していない: …」も外す（有給休暇管理表は毎月出す）。"""
    外した = len(除く人(o)[0])   # 待つ訳・仮の人の行・有給の外した人 だけの人も数える（除いた人の数）
    物たち = {d.物 for d in 出す物たち(o)}
    前 = [x.strip() for x in re.split(r"\s*／\s*", str(今の止まりの理由 or ""))
         if x.strip() and not x.strip().startswith(("今の版", 有給を出さない頭, 有給に載せない頭, 外した頭))]
    除いた = 除く人(o)[0]
    if 除いた:   # 外した人ごとの理由（月ごとに書き直す）。出す の JSON の 除いた人 と同じ値
        前 = [f"{外した頭}: " + "・".join(f"NO {a['NO']}（{'・'.join(a['理由'])}）" for a in 除いた), *前]
    行 = {"会社": 会社, "支給月": 支給月, "外した人": str(外した), "止まりの理由": " ／ ".join(前)}
    if 物たち & set(_取り込みの物):
        行["取り込み"] = "済" if 外した == 0 else "仮"
    止めた = [a["NO"] for a in 有給の止めた人(o)]
    if 止めた:
        行["止まりの理由"] = " ／ ".join([f"{有給に載せない頭}: NO {'・'.join(止めた)}", *前])
    return 行


def 出した物の行(会社: str, 支給月: str, 回: str, 置いた: list[dict]) -> list[dict]:
    """管理表のタブ 出した物 へ書く行（物ごとに 1 行・今の版の名とリンク）。列は 出した物の列。"""
    return [dict(zip(出した物の列, (会社, 支給月, 回, p["物"], p["名"], p["url"]))) for p in 置いた]


# ── 3. 書く（緑の時だけ） ────────────────────────────────────────────
def _組む(口, 置き場, xs) -> list[dict]:
    """書く物を全部、書く前に組む（CSV の中身・表の行・移す前の版の id）。途中で止まりうる組み立てはここで済ませ、
    書き始めてから組み立ての誤りで止まる道を作らない。返り: 物ごとに {d, 中身, 前の版}。"""
    組 = []
    for d in xs:
        if getattr(d, "渡し方", "表") == "CSV":
            中身 = d.csvの中身()
        else:
            中身 = [list(r) for r in d.表]
        前 = []
        for n in d.名.履歴へ移す:
            x = 口.名で引く(置き場[出す置き], n)
            if x is not None:
                前.append({"名": n, "id": x["id"]})
        組.append({"d": d, "中身": 中身, "前の版": 前})
    return 組


def _置く(口, 置き場, g, 残る: list) -> dict:
    """組んだ 1 物の新しい版を 2_出す物 に置く（前の版はまだ動かさない）。シートは物の名のタブを付けて作り、そこへ書く。
    作った file は書く前に 残る へ足し、中身まで書けたら印を替える（途中で止まった時に id ごと返す）。"""
    d = g["d"]
    if getattr(d, "渡し方", "表") == "CSV":
        fid = 口.ファイルを置く(置き場[出す置き], d.名.名, g["中身"], "text/csv")
        残る.append({"所": 出す置き, "名": d.名.名, "id": fid, "中身": "書けた"})
    else:
        fid = 口.シートを作る(置き場[出す置き], d.名.名, [d.物])
        残る.append({"所": 出す置き, "名": d.名.名, "id": fid, "中身": "まだ（空のシート）"})
        要る = drive口.要る格子("A1", g["中身"])
        if 要る[0] > drive口.新しいタブの格子[0] or 要る[1] > drive口.新しいタブの格子[1]:
            口.格子を広げる(fid, d.物, *要る)   # 新しいタブの格子（1000 行 × 26 列）の外へは Google が 400 で書かない
        口.表へ書く(fid, drive口.範囲(d.物, "A1"), g["中身"])
        残る[-1]["中身"] = "書けた"
    リンク = getattr(口, "リンク", None)   # drive口 にリンクの口が無い＝id をそのまま返す
    return {"物": d.物, "名": d.名.名, "url": リンク(fid) if リンク else fid}


def _移せない(口, 置き場, xs) -> list[str]:
    """前の版が 2_出す物 に在るのに drive口 に 移す が無い＝写して残すと 2_出す物 に古い版が残り 9_履歴 に重なる。
    名と版の決まり（2_出す物 には最新の版 1 つだけ）を曲げず、何も置かずに止める（drive口 に 移す を足すのは後でパックを直す一覧）。"""
    if callable(getattr(口, "移す", None)):
        return []
    前 = [n for d in xs for n in d.名.履歴へ移す if 口.名で引く(置き場[出す置き], n) is not None]
    return [f"前の版 {n} を {出す置き} から {履歴置き} へ移せない（drive口 に 移す が無い・写して残すと最新の版 1 つだけの決まりが崩れる）"
            for n in 前]


出した物の列 = ("会社", "支給月", "回", "物", "今の版", "リンク")   # 出した物の行 の鍵（書く前に見出しを照らす）


def _欠けた列(タブ, 今: list, 列) -> list[str]:
    """管理表のタブの今の値（1 行目が見出し）に、書く行の列が全部在るか。在れば空。物を置く前に呼ぶ（途中まで書かない）。"""
    if not 今:
        return [f"管理表の行: 管理表の「{タブ}」に見出しが無い"]
    外 = sorted(set(列) - set(今[0]))
    return [f"管理表の行: 管理表の「{タブ}」に無い列 {外}"] if 外 else []


def _管理表の鍵() -> str:
    return 型の口.Driveの名("管理表")


def _管理表を読む(口, 置き場, タブ) -> list[list[str]]:
    """管理表のタブ（役の名・例 月の状況）→ Drive のタブの名（管理表.Driveのタブ・型 39 は 1_月の状況）で読む。"""
    from 管理表 import 管理表 as 表
    return 口.表を読む(置き場[_管理表の鍵()], drive口.範囲(表.Driveのタブ(タブ)))


def _同じ値(列: str, 今, 書く) -> bool:
    """管理表の鍵の列の値が同じか。支給月 は殻の字 `YYYY.MM支給` と置き場の字 `YYYY.MM支給（M月分）` を (年, 月) で比べる
    （芯/支給月の字.鍵の年月 の 1 か所＝管理表/管理表.py と同じ読み）。読めない字は ValueError で止める（黙って別の行・行無しにしない）。"""
    if 列 == "支給月":
        from 芯 import 支給月の字
        a, b = 支給月の字.鍵の年月(今), 支給月の字.鍵の年月(書く)
        if a is None or b is None:
            raise ValueError(f"管理表の支給月 {(今 if a is None else 書く)!r} が読めない"
                             "（`YYYY.MM支給（M月分）` か `YYYY.MM支給`。docs/毎月の流れ.md「支給月の書き方」）")
        return a == b
    return str(今).strip() == str(書く).strip()


def _読めない支給月(タブ, 今: list, 会社: str, 支給月: str) -> list[str]:
    """_管理表へ が行を当てる時に _同じ値 で比べる支給月（書く字と、同じ会社の今の行の字）が全部読めるか。読めない字ごとに赤。
    物を置く前に呼ぶ（_管理表へ の ValueError は書く途中＝新しい版を置き前の版を移した後に上がるので、ここで先に止める）。"""
    from 芯 import 支給月の字
    if not 今 or "支給月" not in 今[0]:
        return []
    h = 今[0]
    字たち = [支給月] + [r[h.index("支給月")] if h.index("支給月") < len(r) else "" for r in 今[1:]
                       if "会社" not in h or _同じ値("会社", r[h.index("会社")] if h.index("会社") < len(r) else "", 会社)]
    return [f"管理表の行: 管理表の「{タブ}」の支給月 {字!r} が読めない"
            "（`YYYY.MM支給（M月分）` か `YYYY.MM支給`。docs/毎月の流れ.md「支給月の書き方」）"
            for 字 in dict.fromkeys(字たち) if 支給月の字.鍵の年月(字) is None]


def _管理表へ(口, 置き場, タブ, 今: list, 行たち: list[dict]) -> None:
    """管理表のタブへ、見出しの並びで行を書く（会社・支給月・回・物の鍵のうち行と見出しに在る物が合う行は上書き・無ければ足す）。
    今 は物を置く前に読み、_欠けた列 で照らした値（見出しの欠けはここへ来ない）。"""
    from 管理表 import 管理表 as 表
    h, 本, 名 = 今[0], 置き場[_管理表の鍵()], 表.Driveのタブ(タブ)
    for 行 in 行たち:
        鍵 = [k for k in ("会社", "支給月", "回", "物") if k in 行 and k in h]
        当たり = [i for i, r in enumerate(今[1:], start=2)
                if all(_同じ値(k, r[h.index(k)] if h.index(k) < len(r) else "", 行[k]) for k in 鍵)]
        値 = [str(行.get(k, "")) for k in h]
        if 当たり:
            口.表へ書く(本, drive口.範囲(名, f"A{当たり[0]}"), [値])
        else:
            口.表へ足す(本, drive口.範囲(名, "A1"), [値])


_idの形 = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{25,}(?![A-Za-z0-9_-])")


def 伏せる(x):
    """止める訳（赤）の字から Drive の id の形（25 字以上の英数・_・-）を <id> に替える。ログ・管理表へ id を出さない。"""
    if isinstance(x, str):
        return _idの形.sub("<id>", x)
    if isinstance(x, list):
        return [伏せる(v) for v in x]
    if isinstance(x, dict):
        return {k: 伏せる(v) for k, v in x.items()}
    return x


def _止まりを返す(o) -> dict:
    """月次の返りの 止まり・出し直しの候補・形の崩れ を出す の JSON へ（止めない物も人に見せる）。"""
    if not isinstance(o, dict):
        return {}
    return {k: list(o[k]) for k in ("止まり", "出し直しの候補", "形の崩れ") if o.get(k)}


def 出す(口, 置き場: dict, 支給月: str, 回: str, *, 書かない: bool = False,
       回す: Callable | None = None) -> tuple[int, dict]:
    """出す の芯（_出す）を呼び、人に見せる文（赤・止まり・出し直しの候補・形の崩れ）から id を伏せて返す（伏せるのはここ 1 か所）。"""
    code, out = _出す(口, 置き場, 支給月, 回, 書かない=書かない, 回す=回す)
    return code, {k: 伏せる(v) if k in _伏せる鍵 else v for k, v in out.items()}


_伏せる鍵 = ("赤", "止まり", "出し直しの候補", "形の崩れ")


def _出す(口, 置き場: dict, 支給月: str, 回: str, *, 書かない: bool = False,
        回す: Callable | None = None) -> tuple[int, dict]:
    """1 つの命令の芯。返り: (exit, stdout に出す JSON)。止める時は何も書かない。
    会社の字は 置き場["会社"]（drive口.置き場.会社の置き場 が会社の一覧で 1 度だけ決めた呼び名）の 1 つだけ＝
    月を回す・管理表の行・出した物の行へ同じ値を渡す（--会社 の字を別に持たない・顧客ID で渡しても絞りが合う）。"""
    会社 = 置き場.get("会社", "")
    if not 会社:
        return 2, {"出した": False, "赤": ["置き場: 会社（会社の一覧の呼び名）が無い（drive口.置き場.会社の置き場 で決める）"]}
    回 = 回の名.get(回, "")
    if not 回:
        return 2, {"出した": False, "赤": ["形: 回は 給与 か 賞与"]}
    try:
        支給月 = 月次の支給月(支給月)
    except ValueError as e:
        return 2, {"出した": False, "赤": [f"形: {e}"]}
    o, 赤 = (回す or 読んで回す)(口, 置き場, 会社, 支給月, 回)
    if 赤:
        return 2, {"出した": False, "赤": 赤}
    止まり = _止まりを返す(o)
    除いた, 赤 = 除く人(o)
    if 赤:
        return 2, {"出した": False, "赤": 赤, "除いた人": 除いた, **止まり}
    物の名 = {d.物 for d in 出す物たち(o)}
    if 回 == "月" and "取り込み" in 物の名 and "有給休暇管理表" not in 物の名:   # 毎月出す物＝黙って欠かさない
        return 2, {"出した": False, "除いた人": 除いた, **止まり,
                   "赤": ["形: 取り込みはあるのに有給休暇管理表が組めていない（月を回す に有給の値と出口を渡したか見る）"]}
    除くNO = {a["NO"] for a in 除いた}
    出す人: set[str] = set()
    for d in 出す物たち(o):
        NO, 赤 = 載せた人(d)
        if NO is None:
            return 2, {"出した": False, "除いた人": 除いた, "赤": [赤]}
        if NO & 除くNO:   # 月次が外した人の行が出す物に残る＝出口の形が崩れた。黙って書かない
            return 2, {"出した": False, "除いた人": 除いた,
                       "赤": [f"仮: 除いた人 NO {n} の行が {d.物} に残る" for n in sorted(NO & 除くNO)]}
        出す人 |= NO
    if 除いた and not 出す人:
        return 2, {"出した": False, "除いた人": 除いた, **止まり,
                   "赤": [f"仮: 出す人が残らない（全員が仮: NO {'・'.join(a['NO'] for a in 除いた)}）"]}
    from 管理表 import 管理表 as 表
    回2 = 回
    管理表のタブ, 赤 = 回のタブ(回)
    if 赤:
        return 2, {"出した": False, "赤": 赤}
    xs = 出す物たち(o)
    結果 = {"出した": False, "通す": True, "会社": 会社, "支給月": 支給月, "回": 回2,
            "出す物": [d.名.名 for d in xs], "除いた人": 除いた, **止まり}
    if 有給の止めた人(o):   # 給与は出すが有給休暇管理表に行を出さない人（NO と理由）。答えれば次の月から出る
        結果["有給の止めた人"] = 有給の止めた人(o)
    if isinstance(o, dict) and o.get("読みの知らせ"):
        結果["知らせ"] = list(o["読みの知らせ"])
    今の行 = _管理表を読む(口, 置き場, 管理表のタブ)
    今の出した物 = _管理表を読む(口, 置き場, 表.出した物のタブ())
    # 書く行を当てる鍵（_管理表へ の _同じ値）が読めない支給月は、物を置く前に全部照らす（書く途中で止まらない・試しも同じ赤）
    赤 = _読めない支給月(管理表のタブ, 今の行, 会社, 支給月) + _読めない支給月(表.出した物のタブ(), 今の出した物, 会社, 支給月)
    if 赤:
        return 2, {"出した": False, "赤": 赤}
    今の理由 = ""
    if 今の行 and {"止まりの理由", "会社", "支給月"} <= set(今の行[0]):   # 欠けた列は下の _欠けた列 が名指しで赤
        h = 今の行[0]
        for r in 今の行[1:]:
            if len(r) > h.index("止まりの理由") and _同じ値("会社", r[h.index("会社")], 会社) \
                    and _同じ値("支給月", r[h.index("支給月")], 支給月):
                今の理由 = r[h.index("止まりの理由")]
    行 = 管理表の行(会社, 支給月, o, 今の理由)
    if 今の行 and "更新日" in 今の行[0]:
        行["更新日"] = date.today().isoformat()
    赤 = (_欠けた列(管理表のタブ, 今の行, 行) + _欠けた列(表.出した物のタブ(), 今の出した物, 出した物の列)
         + _移せない(口, 置き場, xs))
    if 赤:
        return 2, {"出した": False, "赤": 赤}
    if 書かない:   # 試しも列の欠け・移す口の無さまで照らしてから返す（試しが緑で本番だけ赤にならない）
        return 0, {**結果, "試し": "書いていない"}
    組 = _組む(口, 置き場, xs)          # 書く物を全部組み終えてから書き始める（組めなければ何も書かずに止まる）
    # 書く順: ① 新しい版を全部置く → ② 前の版を 9_履歴 へ移す → ③ 管理表。① の途中で止まれば前の版は 2_出す物 に残ったまま。
    # 止まった時は消さない（drive口 に消す口は無く、消すのは人に聞く操作）＝止まった事と、その回に作った・動かした物の id を返す。
    書いた: list[str] = []
    残る: list[dict] = []
    移した: list[dict] = []
    try:
        置いた = [_置く(口, 置き場, g, 残る) for g in 組]
        書いた += [f"{出す置き}: {x['名']}" for x in 残る]
        for g in 組:
            for p in g["前の版"]:
                口.移す(p["id"], 置き場[履歴置き])
                移した.append({"所": 履歴置き, "名": p["名"], "id": p["id"], "元": 出す置き})
                書いた.append(f"{履歴置き}へ移した: {p['名']}")
        _管理表へ(口, 置き場, 管理表のタブ, 今の行, [行])
        書いた.append(f"管理表: {管理表のタブ}")
        _管理表へ(口, 置き場, 表.出した物のタブ(), 今の出した物, 出した物の行(会社, 支給月, 回2, 置いた))
        書いた.append(f"管理表: {表.出した物のタブ()}")
    except Exception as e:   # Drive の途中の失敗＝黙って残さない。作った物・移した物の id と、どこまで書いたかを返す
        if not 書いた:   # ① の途中＝中身まで書けた物だけが「書いた」
            書いた = [f"{x['所']}: {x['名']}" for x in 残る if x["中身"] == "書けた"]
        return 2, {"出した": False, "赤": [f"書く途中で止まった: {type(e).__name__}: {e}"], "書いた": 書いた,
                   "残った物": 残る, "移した物": 移した,
                   "戻し方": "残った物 は今回 2_出す物 に作った物（前の版はまだ在る）・移した物 は前の版を 9_履歴 へ移した物。"
                            "消す・戻すかは人が id を見て決める（出す.py は消さない）"}
    return 0, {**結果, "出した": True, "置いた": 置いた, "書いた": 書いた}


def 出す置き場へ(口, 会社の置き場: dict, 支給月: str) -> tuple[dict, list[str]]:
    """drive口.置き場.会社の置き場 が返す {物の名: id} を、出す.py が読む鍵へ写す（ここで id を組まない・何も作らない）。
    マスタの本たち（型 39: マスタ・マスタの変更の記録＝型の口.タブの本）と 顧客ID・会社 はそのまま（drive口.置き場.マスタを読む が
    この鍵で引く）・台帳←台帳_<支給月の年>（前の年の台帳←台帳_<年-1>・在れば）・事務所←事務所の設定・事務所のルール←事務所のルール.md（型の口.Driveの名）・
    給与のルール／作業のルール←1_決まり の子を名で引く・質問と回答←事務所の根の 1 冊（型 41・事務所の物）・2_出す物←3_月ごと/<支給月の月のフォルダ>/2_出す物・
    9_履歴・管理表 はそのまま。引けない物は入れず赤に訳を足す（読んで回す・前の版の名 が欠けを止める）。"""
    from drive口 import 置き場 as 置
    from 芯 import 支給月の字
    p, 赤 = 会社の置き場, []
    try:
        年, 月 = int(支給月[:4]), int(支給月[5:7])
    except ValueError:
        return {}, [f"支給月: {支給月} が YYYY-MM でない"]
    out = {k: p[k] for k in (履歴置き, _管理表の鍵(), *_マスタの本たち(), "顧客ID", "会社") if p.get(k)}
    for 鍵, 名 in (("台帳", 型の口.台帳の名(年)),
                  ("前の年の台帳", 型の口.台帳の名(年 - 1)), ("事務所", 型の口.Driveの名("事務所の設定")),
                  ("事務所のルール", 型の口.Driveの名("事務所のルール"))):
        if p.get(名):
            out[鍵] = p[名]
    # 質問と回答 は事務所の根の 1 冊（型 41・事務所の物）。決まりの md は 1_決まり の子を名で引く
    if p.get(型の口.Driveの名("質問と回答")):
        out["質問と回答"] = p[型の口.Driveの名("質問と回答")]
    for 親, 物 in (("決まり", "決まりの物"),):
        親id = p.get(型の口.名(親))
        for 鍵 in (型の口.木()[物] if 親id else ()):
            try:
                x = 口.名で引く(親id, 型の口.名(鍵))
            except drive口.上限:   # 上限＝読めた物が欠けたのではない＝別の訳に化けさせず main で止める
                raise
            except Exception as e:  # noqa: BLE001  同じ名が 2 つ等＝選ばず止める
                赤.append(f"置き場: {型の口.名(親)}/{型の口.名(鍵)} が引けない（{type(e).__name__}: {e}）")
                continue
            if x:
                out[鍵] = x["id"]
    月ごと = p.get(型の口.名("月ごと"))
    if not 月ごと:
        赤.append(f"この月の勤怠が来ていない（{支給月} の月のフォルダが無い・{型の口.名('月ごと')} のフォルダも無い）")
    else:
        try:
            当たり = [x["name"] for x in 口.子を並べる(月ごと)
                    if x.get("mimeType") == フォルダのmime
                    and (支給月の字.置き場の字を読む(x["name"]) or ())[:2] == (年, 月)]
            if not 当たり:
                赤.append(f"この月の勤怠が来ていない（{支給月} の月のフォルダが無い）。隠れた訳もありうる: "
                         f"フォルダの名が月と読めない・{型の口.名('月ごと')} の外に置いた・まだ作っていない・"
                         f"共有が切れて見えない（名を {年}.{月:02d}支給 の形にして {型の口.名('月ごと')} の下に置く）")
            elif len(当たり) != 1:
                赤.append(f"置き場: {型の口.名('月ごと')} に {支給月} 支給の月のフォルダが {len(当たり)} つ"
                         "（1 つでなければ選ばず止める）")
            else:
                out[出す置き] = 置.月の置き場(口, 月ごと, 当たり[0])[出す置き]
        except drive口.上限:   # 上限＝読めた物が欠けたのではない＝別の訳に化けさせず main で止める
            raise
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
    a = ap.parse_args(argv)
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
        print(json.dumps({"出した": False, "赤": 伏せる([f"Drive: {type(e).__name__}: {e}"])}, ensure_ascii=False))
        return 2
    if 赤:   # 置き場が 1 つに決まらない＝何も書かない
        print(json.dumps({"出した": False, "赤": 伏せる(赤)}, ensure_ascii=False, indent=1))
        return 2
    try:
        code, out = 出す(口, 置き場, a.支給月, a.回, 書かない=a.試しに書かない)   # 会社は置き場の 1 つ（a.会社 を渡さない）
    except drive口.上限 as e:   # 読む途中の上限（書く途中の上限は _出す が残った物と一緒に返す）＝何も書いていない
        print(json.dumps({"出した": False, "赤": [str(e)]}, ensure_ascii=False, indent=1))
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
