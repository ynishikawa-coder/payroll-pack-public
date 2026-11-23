"""芯/計算 の形: 端数の語・仮の理由・人×項目の帳。

- 数は Decimal（円は整数にして返す）。float は受けない。
- 端数の語は会社の決まり（`docs/設計/会社の決まり.md` §2）の選べる値。語ごとの丸め方だけをここに持つ（法の値は持たない）。
- 仮は「理由」1 つにつき問い 1 つ。同じ理由で何人も仮になる時は 1 問に人を並べる（確かめと仮.md §3）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from fractions import Fraction
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


def 名の数(d, 名: str) -> tuple[Decimal | None, str]:
    """d（dict）の 名 の数を、名が無い と 名は在るのに値が足りない に分けて読む（空と無しを分ける 1 か所）。

    - 名が無い（d が dict でない時も）＝(None, "")＝足りない値ではない（呼ぶ側の既定＝例 0 で確定してよい）。
    - 名は在るのに 空・数でない・負＝(None, 訳)＝足りない値。呼ぶ側は見当で計算して仮にする
      （⟦鍵:給与計算/足りない時は仮で計算し出さない⟧。`数(..) or 0` で空を黙って 0 に読まない）。
    - 読めた＝(数, "")。
    殻（段の解決）は空のセルを渡さないので、名が在って空なのは渡し方が崩れた時だけ。"""
    if not isinstance(d, dict) or 名 not in d:
        return None, ""
    x = d[名]
    try:
        n = 数(x, 名)
    except 形の誤り:
        return None, f"数でない（{x!r}）"
    if n is None:
        return None, f"空（{x!r}）"
    if n < 0:
        return None, f"負（{x!r}）"
    return n, ""


def 日付(v, 名: str = "値") -> date | None:
    """date か YYYY-MM-DD の字を date に。None と "" だけ None。読めない字は 形の誤り（素の ValueError で月を止めず、
    計算する の口でその人だけ値なしの仮＋問いにする 1 か所）。芯/計算 で日付の字を読む所はここを通す。
    空白だけの字も 形の誤り（真の字なのに None を返すと、`if 字 and 日付(字) < x` の呼ぶ側が None と比べて素の例外で月を止める）。
    偽の値（None・""）だけを「無し」とするので、呼ぶ側の `if 字` と食い違わない。"""
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v).strip())
    except ValueError:
        raise 形の誤り(f"{名}「{v}」が日付（YYYY-MM-DD）でない") from None


def 時間(v, 名: str = "値") -> Fraction | None:
    """時間の値（時間の数〔Decimal・int・数の字〕か h:mm の字）→ 時間の Fraction。空は None。float は受けない。
    h:mm は分数のまま持つ（`161:20`→161⅓ 時間。10 進に直すと循環小数で、割った単価が丸めで 1 円ずれうる）。"""
    if isinstance(v, str):
        m = re.fullmatch(r"(\d+):([0-5]\d)", v.strip())
        if m:
            return Fraction(int(m.group(1)) * 60 + int(m.group(2)), 60)
    x = 数(v, 名)
    return None if x is None else Fraction(x)


def 分数を小数に(f: Fraction) -> Decimal:
    """分数 → Decimal（割り切れる時は丸めの前の値がちょうど整数のまま。分の時間を 10 進に直す誤差で 1 円ずれないため）。
    割り切れない分数も、丸めの境（整数・0.5）にちょうど当たる値は 10 進で表せるので、丸めた後の円は分数で丸めたのと同じ。"""
    return Decimal(f.numerator) / Decimal(f.denominator)


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


# ---- 人.区分（初期設定/項目.json の 人.区分 の選べる値）----
区分の語 = ("社員", "パート", "役員", "兼務役員", "委託", "委託の併用")
併せ持てる区分 = (frozenset({"役員", "委託の併用"}),)   # 辞書の書き方 `役員＋委託の併用`（役員報酬と委託分を 1 枚に）


def 区分を読む(v) -> frozenset | None:
    """`人.区分` → 区分の語の組。項目の辞書の書き方のとおり空白と後ろの括弧の説明を除いて読み
    （`委託の併用（雇用と委託を 1 枚の明細に）` と `委託の併用` を同じに）、`＋` で並べた語は併せ持つ（今は `役員＋委託の併用` だけ）。
    空は空の組（既定の 社員 は 要る値 が埋める）。知らない語・併せ持てない組は None（読めない＝要る値 が仮＋問い）。"""
    s = "".join(str(v if v is not None else "").split()).replace("+", "＋")
    if s.endswith("）") and "（" in s and not s.startswith("（"):
        s = s.split("（", 1)[0]
    if not s:
        return frozenset()
    部 = frozenset(s.split("＋"))
    if not 部 <= set(区分の語) or len(s.split("＋")) != len(部):
        return None
    if len(部) > 1 and 部 not in 併せ持てる区分:
        return None
    return 部


def 区分か(v, *語) -> bool:
    """値たち v の `人.区分` が 語 のどれかを含むか（`役員＋委託の併用` は 役員 でも 委託の併用 でもある）。読めない区分は偽。"""
    return bool((区分を読む(v.get("人.区分")) or frozenset()) & set(語))


def 区分だけか(v, 語) -> bool:
    """値たち v の `人.区分` がちょうど 語 1 つか（例 委託だけ・役員だけ）。"""
    return 区分を読む(v.get("人.区分")) == frozenset({語})


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
