"""人×項目の縦の行（芯の出す物・読み口の出す物の両方がこの形）。

形の正本は docs/設計/確かめと仮.md §2・§3。出口は Drive を開かない。殻が渡す値を受けて返すだけ。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

確定 = "確定"
仮 = "仮"

_支給月の形 = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])(-賞与)?$")


def 支給月を確かめる(支給月: str) -> str:
    """`YYYY-MM` か `YYYY-MM-賞与` だけを通す。"""
    if not isinstance(支給月, str) or not _支給月の形.match(支給月):
        raise ValueError(f"支給月の形が違う: {支給月!r}（YYYY-MM か YYYY-MM-賞与）")
    return 支給月


def 賞与か(支給月: str) -> bool:
    return 支給月を確かめる(支給月).endswith("-賞与")


def 支給月の並び(支給月: str) -> tuple[int, int, int]:
    """並べる鍵。同じ月の賞与は給与の後ろ。"""
    m = _支給月の形.match(支給月を確かめる(支給月))
    return int(m.group(1)), int(m.group(2)), 1 if m.group(3) else 0


def 数にする(値) -> Decimal:
    """値を Decimal にする（float は受けない＝丸めの誤りを持ち込まない）。"""
    if isinstance(値, bool) or isinstance(値, float):
        raise TypeError(f"値は Decimal・int・字で渡す（{type(値).__name__} は受けない）: {値!r}")
    if isinstance(値, Decimal):
        return 値
    if isinstance(値, int):
        return Decimal(値)
    if isinstance(値, str):
        try:
            return Decimal(値.strip())
        except InvalidOperation:
            raise ValueError(f"数でない値: {値!r}") from None
    raise TypeError(f"値の形が違う: {値!r}")


@dataclass(frozen=True)
class 行:
    支給月: str
    会社: str
    NO: str
    項目: str
    値: Decimal
    出所: str = ""
    状態: str = ""          # 書かなければ仮に数える（関所は `確定` だけを通す）
    見当: str = ""
    見当の拠り所: str = ""
    問いの番号: tuple[str, ...] = field(default_factory=tuple)

    @property
    def 人(self) -> tuple[str, str, str]:
        return (self.支給月, self.会社, self.NO)

    @property
    def 鍵(self) -> tuple[str, str, str, str]:
        return (self.支給月, self.会社, self.NO, self.項目)


def 行にする(d) -> 行:
    """殻が渡す dict（列の名は設計書のまま）を 行 にする。"""
    if isinstance(d, 行):
        return d
    要る = ("支給月", "会社", "NO", "項目", "値")
    無い = [k for k in 要る if k not in d]
    if 無い:
        raise ValueError(f"人×項目の行に列が無い: {'・'.join(無い)}")
    問い = d.get("問いの番号") or ()
    if isinstance(問い, str):
        問い = tuple(x for x in re.split(r"[・,、\s]+", 問い) if x)
    値 = d["値"]
    return 行(
        支給月=支給月を確かめる(str(d["支給月"])),
        会社=str(d["会社"]),
        NO=str(d["NO"]),
        項目=str(d["項目"]),
        値=数にする(値) if 値 is not None and 値 != "" else None,
        出所=str(d.get("出所") or ""),
        状態=str(d.get("状態") or ""),
        見当=str(d.get("見当") or ""),
        見当の拠り所=str(d.get("見当の拠り所") or ""),
        問いの番号=tuple(問い),
    )


def 行たちにする(rows) -> list[行]:
    out = [行にする(r) for r in rows]
    見た = set()
    for r in out:
        if r.鍵 in 見た:
            raise ValueError(f"同じ人×項目が 2 行ある: {'・'.join(r.鍵)}")
        見た.add(r.鍵)
    return out
