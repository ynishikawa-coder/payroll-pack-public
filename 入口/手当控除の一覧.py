"""読み口: 手当・控除の一覧（寮費・弁当代・組合費のような人ごとの書類。PDF・Excel どちらも）。表 A・B でなく、
台帳「月の変動」とマスタ「②人ごとの支給控除」へ足す行を返す（Drive の型.md §4）。書き込むのは殻。

殻が渡す物: 行たち（{勤怠の表記 か NO, 項目, 額 か 個数, 単価?, 適用開始?}）・原本の名前・
項目の辞書（マスタ④支給控除の項目の名 → {"毎月同じ": bool}）・単価（項目 → 円。個数で来る項目だけ）。
決まり: 毎月同じ額の項目 → 人ごとの支給控除（適用開始つき・前の行は消さない）／毎月変わる額 → 月の変動。
項目の辞書に無い項目は 月の変動 に書いて要確認（書類の言い方で項目を作らない）。額は正の数（控除も正）。
個数×単価はここで出す（AI が暗算しない）。
"""
from decimal import Decimal, InvalidOperation

from . import 口


def _額(v):
    try:
        d = Decimal(str(v).replace(",", "").replace("円", "").strip())
    except InvalidOperation:
        return None
    return d if d >= 0 and d == d.to_integral_value() else None


def 読む(行たち: list[dict], 文脈, 原本の名前: str, 項目の辞書: dict, 単価: dict | None = None) -> 口.結果:
    単価 = 単価 or {}
    out = 口.結果()
    for r in 行たち:
        表記 = str(r.get("勤怠の表記", "")).strip()
        no = str(r.get("NO", "")).strip() or 文脈.社員.get(表記) or f"仮:{表記}"
        項目 = str(r.get("項目", "")).strip()
        理由 = []
        if no.startswith("仮:"):
            理由.append("人をマスタの社員から引けない")
        if str(r.get("個数", "")).strip():
            n, u = _額(r["個数"]), _額(r.get("単価") or 単価.get(項目, ""))
            額 = n * u if n is not None and u is not None else None
            if 額 is None:
                理由.append(f"{項目} の個数か単価が無い・読めない")
        else:
            額 = _額(r.get("額", ""))
            if 額 is None:
                理由.append(f"{項目} の額「{r.get('額', '')}」が読めない")
        性質 = 項目の辞書.get(項目)
        if 性質 is None:
            理由.append(f"項目「{項目}」がマスタの支給控除の項目に無い")
        値 = "" if 額 is None else str(int(額))
        if 性質 and 性質.get("毎月同じ") and not 理由:
            開始 = str(r.get("適用開始", "")).strip()
            if not 開始:
                開始 = 文脈.支給月
                理由.append(f"{項目} の適用の月が書いてない（今月で仮に置いた）")
            out.人ごとの支給控除.append({"会社": 文脈.会社, "NO": no, "項目": 項目, "額": 値, "適用開始": 開始})
        else:
            out.月の変動.append({"会社": 文脈.会社, "支給月": 文脈.支給月, "NO": no, "項目": 項目, "値": 値,
                             "原本の名前": 原本の名前, "確認": 口.要確認 if 理由 else 口.確認済})
        for x in 理由:
            out.要確認.append({"NO": no, "勤怠の表記": 表記, "日付": "", "理由": x})
    return out
