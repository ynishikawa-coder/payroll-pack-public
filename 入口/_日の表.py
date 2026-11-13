"""日ごとの時刻の表を読む共通の手（PDF タイムカード・Excel 出勤簿・勤怠システムの月報が使う。会社ごとに作らない）。

1 枚の表＝1 人。殻は表の字を 見出し と 行（字の list）で渡す。見出しの語は 欄の役 へ読み替える:
  日・出・退（2 組目からも 出・退 と並べてよい）・外出・戻・休憩（長さ）・区分・備考・時間数（印字の 退−出）・
  それと 原本の時間 へ写す欄（総労働・所定内・深夜 など 5 節の語）。どの役にも当たらない欄は 備考 へ字のまま。
"""
from __future__ import annotations

import re

from . import 口
from .口 import 日の材料, 分, 長さの分, 時刻

役たち = {"日", "出", "退", "外出", "戻", "休憩", "区分", "備考", "時間数"}
合計の語 = ("合計", "小計", "計", "総計")


def セル(v, 役: str) -> tuple[str, str, list, list, list]:
    """1 つの時刻の欄 → (時刻の字, 時刻の出所, 印, 備考, 要確認の理由)。
    黒塗り・取消は入れない／手書き の印／1 欄に 2 つの時刻は 出＝早い方・退＝遅い方（印 二重打刻）／
    `*` は勤怠システムで手で直した／`!` と式のエラーは要確認。"""
    s = str(v if v is not None else "").strip()
    出所, 印, 備考, 理由 = "打刻", [], [], []
    if not s:
        return "", 出所, 印, 備考, 理由
    if any(w in s for w in ("黒塗り", "■", "取消")):
        return "", 出所, 印, [f"{役} 黒塗り"], 理由
    if s.startswith("#"):
        return "", 出所, 印, [f"{役} {s}"], [f"{役}の欄が式のエラー（{s}）"]
    if "!" in s or "！" in s:
        理由.append(f"{役}の欄に打刻エラーの印")
        備考.append(f"{役} !打刻エラー")
        s = s.replace("!", "").replace("！", "").strip()
    if "*" in s or "＊" in s:
        出所 = "申請で直した"
        印.append("手で直した")
        s = s.replace("*", "").replace("＊", "").strip()
    if "(手)" in s or "（手）" in s or "手書き" in s:
        出所 = "手書き"
        備考.append("手書き")
        s = re.sub(r"\(手\)|（手）|手書き", "", s).strip()
    parts = [p for p in re.split(r"[\s/／,、]+", s) if p]
    if len(parts) > 1:
        ms = [分(p) for p in parts]
        if all(m is not None for m in ms):
            pick = min(ms) if 役 in ("出", "外出") else max(ms)
            印.append("二重打刻")
            備考.append(f"{役} {s}")
            return 時刻(pick), 出所, 印, 備考, 理由
    if 分(s) is None and parts:
        return "", 出所, 印, [f"{役} {s}"], [f"{役}の時刻「{s}」が読めない"]
    return 時刻(分(s)), 出所, 印, 備考, 理由


def 読む(表記: str, 原本の名前: str, 見出し: list, 行たち: list, 文脈, 読み替え: dict,
       原本の時間の語: dict, 書き方: str = "分") -> tuple[list[日の材料], list[str]]:
    """→ (材料たち, その人の表の全体に掛かる要確認の理由)。"""
    役 = 口.欄の役(見出し, 読み替え)
    時の書き方 = "10進" if 書き方 == "10進" else "60進"  # 時間数・原本の時間の数だけの字は時間で読む（休憩は 書き方）
    材料たち, 表の理由 = [], []
    合計 = None
    for 行 in 行たち:
        x = 口.組にする(役, 行)
        日字 = str(x.get("日", "")).strip()
        if 日字 in 合計の語:
            合計 = x
            continue
        if not 日字 and not any(str(v).strip() for v in x.values()):
            continue
        d = 口.日付を決める(日字, 文脈)
        if d is None:
            表の理由.append(f"日「{日字}」が期間の中の日付に読めない")
            continue
        m = 日の材料(表記, d, 原本の名前)
        n = 1
        while f"出_{n}" in x or f"退_{n}" in x:
            a = セル(x.get(f"出_{n}"), "出")
            b = セル(x.get(f"退_{n}"), "退")
            m.印 += a[2] + b[2]
            m.備考 += a[3] + b[3]
            m.理由 += a[4] + b[4]
            出所 = next((o for o in (a[1], b[1]) if o != "打刻"), "打刻")
            m.労働(a[0], b[0], 出所, 名="出退" if n == 1 else f"出退の {n} 組目")
            n += 1
        n = 1
        while f"外出_{n}" in x:
            a, b = セル(x.get(f"外出_{n}"), "外出"), セル(x.get(f"戻_{n}"), "戻")
            m.備考 += a[3] + b[3]
            m.理由 += a[4] + b[4]
            if a[0] or b[0]:
                s, e = 分(a[0]), 分(b[0])
                if s is None or e is None:
                    m.理由.append("外出と戻が組にならない")
                else:
                    m.区間.append(("外出", s, e + 1440 if e <= s else e, a[1]))
            n += 1
        休 = str(x.get("休憩", "")).strip()
        if 休:
            v = 長さの分(休, 書き方)
            if v is None:
                m.理由.append(f"休憩「{休}」が読めない")
                m.備考.append(f"休憩 {休}")
            else:
                m.事実["時刻の無い休憩"] = str(v)
        if str(x.get("区分", "")).strip():
            m.区分を足す(x["区分"], 文脈)
        if str(x.get("備考", "")).strip():
            m.備考.append(str(x["備考"]).strip())
        時 = str(x.get("時間数", "")).strip()
        if 時:
            v = 長さの分(時, 時の書き方)
            労 = [(s, e) for k, s, e, _ in m.区間 if k == "労働"]
            if v is None or not 労 or any(e is None for _, e in 労) or sum(e - s for s, e in 労) != v:
                m.理由.append(f"印字の時間数「{時}」と 退−出 が合わない")
                m.備考.append(f"印字 {時}")
        for k, v in x.items():
            base = k.split("_")[0]
            if base in 役たち or not str(v).strip():
                continue
            語 = 原本の時間の語.get(k)
            if 語:
                w = 長さの分(v, 時の書き方)
                if w is None:
                    w = 分(v)  # `7:30:00`・Excel の小数（0.3125＝7:30）
                if w is None:
                    m.備考.append(f"{k} {v}")
                else:
                    m.原本の時間[語] = w
            else:
                m.備考.append(f"{k} {str(v).strip()}")
        材料たち.append(m)
    if 合計 is not None and str(合計.get("時間数", "")).strip():
        want = 長さの分(合計["時間数"], 時の書き方)
        got = sum(e - s for m in 材料たち for k, s, e, _ in m.区間 if k == "労働" and e is not None)
        if want != got:
            表の理由.append(f"表の合計の時間数「{合計['時間数']}」と日ごとの和（{時刻(got)}）が合わない")
            for m in 材料たち:
                m.備考.append(f"表の合計 {合計['時間数']}")
    return 材料たち, 表の理由


def 人ごとに読む(表たち: list[dict], 文脈, 種別: str, 読み替え: dict, 原本の時間の語: dict, 書き方: str = "分"):
    """表（1 人 1 枚）の list → 結果。表 = {勤怠の表記, 原本の名前, 見出し, 行, 読み替え?(その様式の見出しの語)}"""
    全部 = []
    for t in 表たち:
        rw = dict(読み替え)
        rw.update(t.get("読み替え", {}))
        ms, 表の理由 = 読む(t["勤怠の表記"], t["原本の名前"], t["見出し"], t["行"], 文脈, rw, 原本の時間の語, 書き方)
        if 表の理由:
            if not ms:  # 1 日も読めない表でも人は出す（全日が 原本に無い になる）
                d = 文脈.日付たち()[0]
                ms = [日の材料(t["勤怠の表記"], d, t["原本の名前"], 行がある=False)]
            for m in ms:
                m.理由 += 表の理由
        全部 += ms
    return 口.仕上げる(全部, 文脈, 種別)
