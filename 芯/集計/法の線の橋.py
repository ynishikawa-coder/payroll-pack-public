"""法の表/法の線.json の行 → 芯/集計 の法の線（`時間.日の法定` 等の dict。形.法の線.読む が読む形）。

法の表を引く口は芯に 1 つだけ（芯/計算/引く口.py）。ここはそれを使い、別の読み口を持たない。
法の値も、表の値の名と集計の名の対応もここに書かない（対応は 芯/計算/法の線の読み方.py）。

期間の始めと終わりの両方で引き、値が違えば止める（期間の中で法の線が変わる月は、手で分けて渡す）。
"""
from __future__ import annotations

from datetime import date

from 芯.計算 import 法の線の読み方 as 読み
from 芯.計算.引く口 import 欠け, 引く

from .形 import 形の誤り

表の名 = "法の線"

# 芯の名 → 法の線.json の (線, 値の欄) と値の取り出しは 芯/計算/法の線の読み方.py の 1 か所（芯/計算 と同じ表）。


def _一日(日: str, 置き場) -> tuple[dict, list[str]]:
    線, 出所 = {}, []
    for 名 in 読み.集計の要る + 読み.集計の任意:
        線の名, 欄, _ = 読み.読み方[名]
        try:
            r = 引く(表の名, 日, 置き場=置き場, 線=線の名)
        except 欠け:
            if 名 in 読み.集計の要る or 線の名 not in 読み.前は無い線:
                raise
            continue
        v = 読み.欄の値(名, r.値)
        if v is None or v == []:
            if 名 in 読み.集計の要る:
                raise 形の誤り(f"法の表「{表の名}」の線「{線の名}」に {欄} が無い")
            continue
        線[名] = v
        if r.出所 not in 出所:
            出所.append(r.出所)
    return 線, 出所


def 法の線を引く(始め: date | str, 終わり: date | str | None = None, *, 置き場=None) -> dict:
    """集計する(法の線=…) へそのまま渡す dict。始め〜終わりは集計の期間（労働した日）。

    返す dict には `出所`（引いた行の字の並び）も入る（形.法の線.読む は読まない）。
    表の行が無い・状態が `出た` でない線は 欠け を投げる（表の `欠けた時` は `止める`）。
    """
    a = 始め.isoformat() if isinstance(始め, date) else str(始め)
    b = (終わり.isoformat() if isinstance(終わり, date) else str(終わり)) if 終わり is not None else a
    線a, 出所 = _一日(a, 置き場)
    if b != a:
        線b, _ = _一日(b, 置き場)
        if 線a != 線b:
            違う = sorted(k for k in set(線a) | set(線b) if 線a.get(k) != 線b.get(k))
            raise 形の誤り(f"期間 {a}〜{b} の中で法の線が変わる（{'・'.join(違う)}）＝期間を分けて渡す")
    return {**線a, "出所": 出所}
