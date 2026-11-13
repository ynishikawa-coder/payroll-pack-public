"""読み口: 集計済み勤怠表（1 人 1 行の月の合計だけの表）→ 月の数字の口（勤怠の形.md 5 節・1 行＝1 人×1 項目）。

殻が渡す物: 表 {原本の名前, 見出し, 行} と、列の対応（見出し → 5 節の項目の語。人の欄は `勤怠の表記` か `NO`）、
時間の書き方（`60進`＝`160:30`・`160.30`／`10進`＝`160.5` 時間。マスタ③会社の「時間の書き方」）。列の対応は事務所の Drive（作業のルール「読み方と合わせ方」）に置き、
repo に置かない。見ない欄（部署・合計など）は 見ない に渡す。
決まり: 対応の無い欄に値がある人は要確認（写さない）／合計・小計の行は写さない／足し算の決まりが合わない人は要確認。
"""
from . import 口

種別 = "集計済み勤怠表"
合計の語 = ("合計", "小計", "計", "総計")


def 読む(表: dict, 文脈, 列の対応: dict, 時間の書き方: str = "60進", 見ない: tuple = ()) -> 口.結果:
    for h, k in 列の対応.items():
        if k not in 口.月の項目 and k not in ("勤怠の表記", "NO"):
            raise ValueError(f"列の対応の「{h}」→「{k}」は月の数字の口の語でない")
    見出し = [str(h).strip() for h in 表["見出し"]]
    out = 口.結果()
    for 行 in 表["行"]:
        x = dict(zip(見出し, [str(v if v is not None else "").strip() for v in 行]))
        表記 = next((x.get(h, "") for h, k in 列の対応.items() if k == "勤怠の表記"), "")
        no = next((x.get(h, "") for h, k in 列の対応.items() if k == "NO"), "")
        if not 表記 and not no or 表記 in 合計の語 or no in 合計の語:
            continue
        no = no or 文脈.社員.get(表記) or f"仮:{表記}"
        理由, 行たち = [], []
        if no.startswith("仮:"):
            理由.append("勤怠の表記がマスタの社員に無い（NO を引けない）")
        for h, v in x.items():
            k = 列の対応.get(h)
            if not v:
                continue
            if k is None:
                if h not in 見ない:
                    理由.append(f"欄「{h}」の対応が無い（写していない）")
                continue
            if k in ("勤怠の表記", "NO"):
                continue
            値, 備考 = _値(k, v, 時間の書き方, 文脈)
            if 値 is None:
                理由.append(f"{k}「{v}」が読めない")
            行たち.append((k, "" if 値 is None else 値, 備考))
        got = {k: int(v) for k, v, _ in 行たち if v != "" and 口.月の項目[k] == "分"}
        parts = ("所定内", "法定内残業", "法定外残業", "法定休日")
        if "総労働" in got and all(p in got for p in parts) and got["総労働"] != sum(got[p] for p in parts):
            理由.append("総労働＝所定内＋法定内残業＋法定外残業＋法定休日 が合わない")
        確 = 口.要確認 if 理由 else 口.確認済
        for k, v, 備考 in 行たち:
            out.月の数字.append({"支給月": 文脈.支給月, "会社": 文脈.会社, "NO": no, "勤怠の表記": 表記, "項目": k, "値": v,
                             "原本の名前": 表["原本の名前"], "原本の種別": 種別, "読み取りの確かめ": 確, "備考": 備考})
        for r in 理由:
            out.要確認.append({"NO": no, "勤怠の表記": 表記, "日付": "", "理由": r})
    return out


def _値(項目, v, 書き方, 文脈):
    単位 = 口.月の項目[項目]
    if 単位 == "分":
        m = 口.長さの分(v, 書き方)
        return (None, v) if m is None else (str(m), "")
    if 単位 == "日付":
        d = 口.日付を決める(v, 文脈)
        return (None, v) if d is None else (d, "")
    n = 口.日の数(v)
    if n is None or (単位 == "回" and n != int(n)):
        return None, v
    return (str(int(n)) if n == int(n) else str(n)), ""
