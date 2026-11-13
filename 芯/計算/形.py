"""芯/計算 の形: 端数の語・仮の理由・人×項目の帳。

- 数は Decimal（円は整数にして返す）。float は受けない。
- 端数の語は会社の決まり（`docs/設計/会社の決まり.md` §2）の選べる値。語ごとの丸め方だけをここに持つ（法の値は持たない）。
- 仮は「理由」1 つにつき問い 1 つ。同じ理由で何人も仮になる時は 1 問に人を並べる（確かめと仮.md §3）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

確定 = "確定"
仮 = "仮"
確認済 = "確認済"


class 形の誤り(ValueError):
    """渡された値が形に合わない（呼ぶ側を直す）。"""


def 数(v, 名: str = "値") -> Decimal | None:
    """Decimal・int・数の字を Decimal に。空は None。float は受けない。"""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, bool) or isinstance(v, float):
        raise 形の誤り(f"{名} は Decimal・int・字で渡す（{type(v).__name__} は受けない）: {v!r}")
    if isinstance(v, Decimal):
        return v
    if isinstance(v, int):
        return Decimal(v)
    try:
        return Decimal(str(v).strip().replace(",", ""))
    except InvalidOperation:
        raise 形の誤り(f"{名} が数でない: {v!r}") from None


# ---- 端数の語（会社の決まり §2 の選べる値）→ Decimal の丸め ----
_丸めの語 = {
    "切捨て": ROUND_FLOOR,
    "切上げ": ROUND_CEILING,
    "四捨五入": ROUND_HALF_UP,
    "50銭未満切捨て以上切上げ": ROUND_HALF_UP,
    "50銭以下切捨て50銭超切上げ": ROUND_HALF_DOWN,
    "50銭以下切捨て": ROUND_HALF_DOWN,
}


def 語をそろえる(語) -> str:
    s = str(語 or "").strip()
    for a, b in (("切り捨て", "切捨て"), ("切り上げ", "切上げ"), (" ", ""), ("　", ""), ("・", ""), ("、", "")):
        s = s.replace(a, b)
    if s.startswith("特約"):
        s = s[2:].lstrip(":：（(").rstrip("）)")
    return s


def 丸めの語か(語) -> bool:
    s = 語をそろえる(語)
    return s in _丸めの語 or s == "しない"


def 丸める(x: Decimal, 語, 単位: Decimal = Decimal(1)) -> Decimal:
    """語の丸めで 単位（既定 1 円）に丸める。`しない` はそのまま。語の外は 形の誤り（呼ぶ側が仮にする）。"""
    s = 語をそろえる(語)
    if s == "しない":
        return x
    if s not in _丸めの語:
        raise 形の誤り(f"端数の語「{語}」は選べる値の外")
    return (x / 単位).quantize(Decimal(1), rounding=_丸めの語[s]) * 単位


def 円(x: Decimal) -> int:
    if x != x.to_integral_value():
        raise 形の誤り(f"円に端数が残っている: {x}")
    return int(x)


@dataclass(frozen=True)
class 理由:
    """仮の理由 1 つ＝問い 1 つの種。"""
    何が無いか: str
    見当: str = ""
    拠り所: str = ""
    答え方の例: str = "見当のとおり・値を書く・原本を送る"


@dataclass
class 値:
    """帳の 1 項目。仮の理由を持ち、足した値の理由を引き継ぐ。"""
    値: Decimal | None
    出所: str = ""
    理由たち: tuple = ()

    @property
    def 仮(self) -> bool:
        return bool(self.理由たち) or self.値 is None


@dataclass
class 帳:
    """1 人の支給控除（項目 → 値）。項目の並びは足した順。"""
    項目: dict = field(default_factory=dict)

    def 置く(self, 名: str, v: Decimal | None, 出所: str = "", 理由たち=()):
        self.項目[名] = 値(v, 出所, tuple(dict.fromkeys(理由たち)))
        return self.項目[名]

    def 足し合わせ(self, 名: str, 元たち, 符号=None, 出所: str = ""):
        """元たちの和（符号 {名: -1} で引く）。値の無い元は 0 で見当する（仮の理由は元から引き継ぐ）。"""
        符号 = 符号 or {}
        和, 理由たち = Decimal(0), []
        for n in 元たち:
            x = self.項目.get(n)
            if x is None:
                continue
            和 += (x.値 or 0) * 符号.get(n, 1)
            理由たち += list(x.理由たち)   # 値の無い元は、その元の理由（欠け・要る値）を計が後で引き継ぐ
        return self.置く(名, 和, 出所, 理由たち)
