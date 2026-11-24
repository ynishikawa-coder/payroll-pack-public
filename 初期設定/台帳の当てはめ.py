"""前任の台帳の列を、計算の芯の軸（軸1 量・軸2 単価）の名へ当てはめた案を返す（純粋な関数）。

Drive を開かない・製品の名と形を持たない（列名と値は殻が読んで渡す作り物でない実の物でも、ここには残さない）。
法の値（割増の率など）もここに書かない＝比べる率は呼ぶ側が法の表と会社の決まりから渡す。
案は初期設定の問いの材料で、計算の芯の答え合わせではない（芯へ渡さない）。

列ごとに次のどれか 1 つ:
- `単価×量×率`: その列に値のある全員で 値 ≒ 単価 × 量 × 率（差が 1 円未満＝丸めの分）になる 単価の名・量の名・率の組
- `出口の欄`: 出口の欄の名と同じ列（計算せず、出口へそのまま写す欄）
- `穴`: どれにも当たらない＝パックに無い式として起票する印（黙って捨てない・黙って近い式に寄せない）
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

単価量率, 出口の欄, 穴 = "単価×量×率", "出口の欄", "穴"


def _数(v) -> Decimal | None:
    if v is None or str(v).strip() == "":
        return None
    try:
        return Decimal(str(v).replace(",", "").strip())
    except InvalidOperation:
        return None


def 当てはめる(台帳: dict, 単価たち: dict, 量たち: dict, 率たち=(1,), 出口の欄たち=(), 鍵の列=("NO",)) -> list[dict]:
    """台帳＝{"列": [列名, …], "人": [{"NO": …, 列名: 値, …}, …]}。
    単価たち＝{NO: {単価の名: 値}}（軸2 の `単価:<名>` で引いた値）・量たち＝{NO: {量の名: 時間・日数}}（軸1 の名）。
    率たち＝比べる率（呼ぶ側が渡す・法の値をここに書かない）・出口の欄たち＝出口の欄の名・鍵の列＝当てはめない列（人の鍵）。
    返す: 列ごとに {"列", "当てはめ", "単価", "量", "率", "出口の欄", "他の候補", "訳"} の並び（列の順）。"""
    率たち = tuple(Decimal(str(r)) for r in 率たち)
    出口 = set(出口の欄たち)
    人たち = 台帳.get("人") or []
    案 = []
    for 列 in 台帳.get("列") or []:
        if 列 in 鍵の列:
            continue
        一つ = {"列": 列, "当てはめ": 穴, "単価": None, "量": None, "率": None, "出口の欄": None, "他の候補": [], "訳": ""}
        if 列 in 出口:
            一つ.update(当てはめ=出口の欄, 出口の欄=列, 訳="出口の欄の名と同じ列")
            案.append(一つ)
            continue
        値たち = [(p.get("NO"), _数(p.get(列))) for p in 人たち]
        値のある = [(n, x) for n, x in 値たち if x]
        読めない = [p.get("NO") for p in 人たち if str(p.get(列) or "").strip() and _数(p.get(列)) is None]
        if 読めない or not 値のある:
            一つ["訳"] = "値が数で読めない人がいる" if 読めない else "値のある人がいない（式を確かめられない）"
            案.append(一つ)
            continue
        単価の名 = sorted(set().union(*(set((単価たち.get(n) or {})) for n, _ in 値のある)))
        量の名 = sorted(set().union(*(set((量たち.get(n) or {})) for n, _ in 値のある)))
        候補 = []
        for u in 単価の名:
            for q in 量の名:
                for r in 率たち:
                    if all(_合う(x, (単価たち.get(n) or {}).get(u), (量たち.get(n) or {}).get(q), r) for n, x in 値のある):
                        候補.append((u, q, r))
        if 候補:
            u, q, r = 候補[0]
            一つ.update(当てはめ=単価量率, 単価=u, 量=q, 率=r, 他の候補=[list(c) for c in 候補[1:]],
                      訳=f"値のある {len(値のある)} 人で 単価:{u}×{q}×{r} に合う" + ("（候補が複数＝問いで選ぶ）" if 候補[1:] else ""))
        else:
            一つ["訳"] = "単価×量×率 のどの組にも合わない＝パックに無い式として起票する"
        案.append(一つ)
    return 案


def _合う(値: Decimal, 単価, 量, 率: Decimal) -> bool:
    u, q = _数(単価), _数(量)
    if u is None or q is None:
        return False
    return abs(値 - u * q * 率) < 1
