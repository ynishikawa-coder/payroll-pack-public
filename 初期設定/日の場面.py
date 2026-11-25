"""日の場面: 勤怠の日に起きる場面（休憩を書いていない日など）と、その場面の日にだけ数えが分かれる決まりを、1 か所で引く部品。

決まり→場面の正本は `初期設定/型ごとの網.json` の `日の場面`（ここは写さない）。ここが持つのは場面ごとの見つけ方（表 A・B の
どの日がその場面か）だけ。例の確かめ（`月次/例の確かめ.py`）と設問（`初期設定/設問.py` の `_今月に当たるか`）が同じこの部品を呼ぶ:
  - 例の確かめは、場面に結んだ決まりの例を、その場面に当たる人が居る時だけ求め、例が無い時はその人だけを止める。
  - 設問は、場面に結んだ決まりの種を、その場面が今月に起きた時だけ今月に当てる。
表 A・B が渡されない・読めない時は「分からない」（None）を返す＝呼ぶ側は今までどおり会社の全員で見る（守りを残す）。
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

_根 = Path(__file__).resolve().parent.parent
if str(_根) not in sys.path:
    sys.path.insert(0, str(_根))

from 芯.集計.日 import 休憩の出し方で数える日  # noqa: E402  (場面の日の線の正本は芯の数え方＝ここに写さない)

_網 = Path(__file__).resolve().parent / "型ごとの網.json"


def _字(v) -> str:
    return "" if v is None else str(v).strip()


def _休憩を書いていない日(日の行: dict | None, 区間たち: list[dict]) -> bool:
    """芯（芯/集計/日.py）が休憩を 時間.休憩の出し方 で数える日＝芯の 休憩の出し方で数える日 をそのまま当てる（組が 1 つでも当たる）。"""
    種別 = [_字(b.get("区間の種別")) for b in 区間たち]
    無い休憩 = _字((日の行 or {}).get("時刻の無い休憩"))
    return 休憩の出し方で数える日([k for k in 種別 if k == "労働"], [k for k in 種別 if k == "休憩"], 無い休憩 or None)


# 場面ごとの見つけ方（場面の名と決まりは 型ごとの網.json の 日の場面 が正本）
_見つけ方 = {"休憩を書いていない日": _休憩を書いていない日}


@lru_cache(maxsize=1)
def 場面たち() -> dict[str, frozenset]:
    """{場面: 決まりの名たち}（型ごとの網.json の 日の場面）。見つけ方の無い場面・場面の無い見つけ方は止める（黙って当てない）。"""
    d = json.loads(_網.read_text(encoding="utf-8")).get("日の場面") or {}
    out = {k: frozenset(v.get("決まり") or ()) for k, v in d.items() if k != "説明"}
    if set(out) != set(_見つけ方):
        raise RuntimeError(f"日の場面の名が 型ごとの網.json（{sorted(out)}）と見つけ方（{sorted(_見つけ方)}）で違う")
    return out


def 決まりの場面(名たち) -> set[str]:
    """決まりの名たち のどれかが結ばれた場面。"""
    名たち = set(名たち)
    return {k for k, v in 場面たち().items() if v & 名たち}


def 当たる人(表A, 表B, 会社名: str | None = None) -> dict[str, set[str]] | None:
    """{場面: その場面の日がある人の NO たち}。表 A・B が無い・行が読めない時は None（分からない）。"""
    if 表A is None or 表B is None:
        return None
    try:
        A = {(_字(a["NO"]), _字(a["日付"])): a for a in 表A if 会社名 is None or _字(a.get("会社")) in ("", 会社名)}
        区間: dict[tuple, list] = {}
        for b in 表B:
            if 会社名 is None or _字(b.get("会社")) in ("", 会社名):
                区間.setdefault((_字(b["NO"]), _字(b["日付"])), []).append(b)
    except (KeyError, TypeError, AttributeError):
        return None
    return {k: {NO for (NO, d), bs in 区間.items() if f(A.get((NO, d)), bs)} for k, f in _見つけ方.items()}


def 起きた場面(表A, 表B, 会社名: str | None = None) -> list[str] | None:
    """今月に起きた場面の名（当たる人が 1 人でも居る場面）。分からない時は None。"""
    人 = 当たる人(表A, 表B, 会社名)
    return None if 人 is None else sorted(k for k, v in 人.items() if v)
