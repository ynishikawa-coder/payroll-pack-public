"""賞与の 1 回の元を年の台帳「賞与の支給一覧」から読み、`月次.賞与を回す` へ渡す形に直す口（読むだけ・Drive を開かない）。

  o = 月次.賞与の元を読む(表, 会社名, 支給月)   # 表＝台帳_<支給年>「賞与の支給一覧」の get_values（1 行目が見出し）
  月次.賞与を回す(支給月, 会社名, タブ, o["支給一覧"], 支給日=o["支給日"], **o["賞与の引数"], …)
  月次.計算の元(タブ, つなぎ, 給与のルール, 支給一覧=o["支給一覧"], 法の線=…, 賞与の引数={"支給日": o["支給日"], **o["賞与の引数"]})

列の名と並びは型の口（初期設定/型.json の 台帳_<支給年>「賞与の支給一覧」）から 月次/台帳の形.py を通して引く（ここに写さない）。
返す物:
  支給一覧: [{"会社", "NO", "額"(int), "原本の名前", "パックの版"}]（NO の順。パックの版＝賞与の回の始めに控えた版の写し。
            照らすのは 賞与を回す＝月を回す の締めた時の版と同じ部品・ここでは見ない）
  支給日: YYYY-MM-DD（その会社・支給月の行の全部で同じ日）
  賞与の引数: {"前月の課税対象額": {(会社, NO): int | None}（`前月の給与なし` の人は値 None＝芯/計算 の「前月の給与が無い」。鍵の無い人は芯が仮にする）,
             "前の標準賞与額": {(会社, NO): int}, "計算期間": {(会社, NO): {"始め", "終わり"}}（2 つとも空の人は置かない）}

止める（既定で止める・黙って見当しない）: 見出しが型と違う・get_values の形でない・その会社・支給月の行が 1 つも無い・NO が空か重なる・
額が空か円の数でない・支給日が無い／日付でない／行で違う／支給月の月の日でない・前月の課税対象額が空か円の数でも `前月の給与なし` でもない・
前の標準賞与額が空か円の数でない・計算期間の片方だけ／日付でない／始めが終わりより後・原本の名前が空・支給月の字が `YYYY.MM支給` でない行。
誤りは全部を並べて 1 回で止める（直す所を 1 度で見せる）。
"""
from __future__ import annotations

import re
from datetime import date

from . import 台帳の形 as 形   # 月次/__init__.py が先に読んだ同じ物（月次_台帳の形）

鍵 = "賞与の支給一覧"
前月の給与なし = "前月の給与なし"
_円 = re.compile(r"\d+")
_日 = re.compile(r"\d{4}-\d{2}-\d{2}")
_支給月 = re.compile(r"(\d{4})\.(\d{2})支給")


class 賞与の元の誤り(ValueError):
    """賞与の元が欠ける・形が違う（賞与を回さない＝出口へ何も出ない）。"""


def _日付(v: str) -> date | None:
    if not _日.fullmatch(v):
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


def 読む(表, 会社名: str, 支給月: str) -> dict:
    """台帳「賞与の支給一覧」の get_values → 賞与を回す へ渡す元（形はこの file の頭）。欠け・形の違いは 賞与の元の誤り で止める。"""
    m = _支給月.fullmatch(str(支給月 or "").strip())
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise 賞与の元の誤り(f"支給月 {支給月!r} は `YYYY.MM支給`（賞与を回す に渡す字）で渡す")
    年月 = f"{m.group(1)}-{m.group(2)}"
    xs = list(表 or ())
    if not xs or not isinstance(xs[0], (list, tuple)) or any(not isinstance(r, (list, tuple)) for r in xs):
        raise 賞与の元の誤り(f"{鍵}: 年の台帳の get_values の形（1 行目が見出しの 2 次元の並び）で渡す（見出しの無い表・dict の並びは読まない）")
    h = [str(c).strip() for c in xs[0]]
    if h != 形.見出し(鍵):
        raise 賞与の元の誤り(f"{鍵}: 見出しが型と違う（{h} ≠ {形.見出し(鍵)}）。型の版をそろえてから読む")
    誤り: list[str] = []
    行たち = []
    for i, r in enumerate(形.行たち(xs), 2):
        r = {k: 形.値の字(v).strip() for k, v in r.items()}
        if r.get("会社") != 会社名:
            continue
        if not _支給月.fullmatch(r.get("支給月", "")):
            誤り.append(f"{i} 行目: 支給月「{r.get('支給月', '')}」が `YYYY.MM支給` でない")
            continue
        if r["支給月"] == f"{m.group(1)}.{m.group(2)}支給":
            行たち.append((i, r))
    if not 行たち and not 誤り:
        raise 賞与の元の誤り(f"{鍵}: 会社 {会社名} の {支給月} の行が無い（支給一覧を台帳に置いてから回す。無い賞与を黙って 0 人で回さない）")
    一覧, 前月, 前の標準, 期間, 日たち, 見た = [], {}, {}, {}, {}, set()
    for i, r in 行たち:
        NO = r.get("NO", "")
        所 = f"{i} 行目（NO {NO or '空'}）"
        if not NO:
            誤り.append(f"{所}: NO が空")
            continue
        if NO in 見た:
            誤り.append(f"{所}: 同じ NO の行が 2 つある（1 人 1 行）")
            continue
        見た.add(NO)
        k = (会社名, NO)
        if not _円.fullmatch(r.get("額", "")):
            誤り.append(f"{所}: 額「{r.get('額', '')}」が円の数でない（空・カンマ・小数は読まない）")
        if not r.get("原本の名前"):
            誤り.append(f"{所}: 原本の名前 が空（額の出所の原本の名を書く）")
        d = _日付(r.get("支給日", ""))
        if d is None:
            誤り.append(f"{所}: 支給日「{r.get('支給日', '')}」が YYYY-MM-DD の在る日でない")
        else:
            日たち.setdefault(r["支給日"], []).append(NO)
            if r["支給日"][:7] != 年月:
                誤り.append(f"{所}: 支給日 {r['支給日']} が支給月 {支給月} の月の日でない（支給月と支給日の取り違え）")
        v = r.get("前月の課税対象額", "")
        if _円.fullmatch(v):
            前月[k] = int(v)
        elif v == 前月の給与なし:
            前月[k] = None
        else:
            誤り.append(f"{所}: 前月の課税対象額「{v}」が円の数でも `{前月の給与なし}` でもない（空は読まない＝黙って前月の給与なしにしない）")
        v = r.get("前の標準賞与額", "")
        if _円.fullmatch(v):
            前の標準[k] = int(v)
        else:
            誤り.append(f"{所}: 前の標準賞与額「{v}」が円の数でない（前の賞与が無ければ 0 と書く）")
        始, 終 = r.get("計算期間の始め", ""), r.get("計算期間の終わり", "")
        if 始 or 終:
            a, b = _日付(始), _日付(終)
            if a is None or b is None:
                誤り.append(f"{所}: 計算期間の始め「{始}」・終わり「{終}」は 2 つとも YYYY-MM-DD の在る日で書く（片方だけは読まない）")
            elif a > b:
                誤り.append(f"{所}: 計算期間の始め {始} が終わり {終} より後")
            else:
                期間[k] = {"始め": 始, "終わり": 終}
        if _円.fullmatch(r.get("額", "")) and r.get("原本の名前"):
            一覧.append({"会社": 会社名, "NO": NO, "額": int(r["額"]), "原本の名前": r["原本の名前"],
                       "パックの版": r.get("パックの版", "")})
    if len(日たち) > 1:
        違い = "・".join(f"{d}: NO {'、'.join(ns)}" for d, ns in sorted(日たち.items()))
        誤り.append(f"支給日が行で違う（{違い}）＝同じ回の賞与は 1 つの支給日")
    if 誤り:
        raise 賞与の元の誤り(f"{鍵}（会社 {会社名}・{支給月}）を読めない: " + " ／ ".join(誤り))
    return {"支給一覧": sorted(一覧, key=lambda x: x["NO"]), "支給日": next(iter(日たち)),
            "賞与の引数": {"前月の課税対象額": 前月, "前の標準賞与額": 前の標準, "計算期間": 期間}}
