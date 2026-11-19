"""支給月の字の読み書きの正本（入口・芯・出口・初期設定・月次の全部がここを読む。層ごとに字を組まない）。

字の形（docs/毎月の流れ.md「支給月の書き方」）:
  殻     `YYYY.MM支給`   殻・台帳とマスタのシートの行・問いの行が書く字
  比べる `YYYY.MM`       段の解決が月を比べる字
  中     `YYYY-MM`       パックの中（入口の表・芯の人×項目・出口の名と証明）の字。賞与は `YYYY-MM-賞与`
読める字は `YYYY.MM支給`・`YYYY.MM`・`YYYY-MM`・`YYYY/MM`・`YYYY年M月`・`YYYY年M月支給`（全角・空白も読む）。
読めない字（空・月が 1〜12 の外・ほかの形）は `読む` が None を返し、使う側が止める（黙って月を見当しない）。
字を組むのは `字にする` 1 つだけ（ほかの関数もここも、字はそれを通して作る）。
"""
from __future__ import annotations

import re
import unicodedata

形たち = ("殻", "比べる", "中")
_読める形 = re.compile(r"(\d{4})(?:[./-]|年)(\d{1,2})月?(?:支給.*)?")


def 字にする(年: int, 月: int, 形: str = "中", 賞与: bool = False) -> str:
    """年と月 → 形の字（支給月の字を組む唯一の所）。賞与の字は 中 の形だけ（`YYYY-MM-賞与`）。"""
    if 形 not in 形たち:
        raise ValueError(f"支給月の字の形 {形!r} は {'・'.join(形たち)} のどれでもない")
    年, 月 = int(年), int(月)
    if not (1 <= 月 <= 12 and 0 < 年 <= 9999):
        raise ValueError(f"支給月の年月が無い月: {年}年{月}月")
    if 賞与 and 形 != "中":
        raise ValueError(f"賞与の字は 中 の形（YYYY-MM-賞与）だけ: 形 {形}")
    return {"殻": f"{年:04d}.{月:02d}支給", "比べる": f"{年:04d}.{月:02d}", "中": f"{年:04d}-{月:02d}"}[形] + (
        "-賞与" if 賞与 else "")


def 読む(v) -> tuple[int, int] | None:
    """支給月の字（上の読める字）→ (年, 月)。読めなければ None。"""
    if v is None:
        return None
    m = _読める形.fullmatch("".join(unicodedata.normalize("NFKC", str(v)).split()))
    if not m or not 1 <= int(m[2]) <= 12:
        return None
    return int(m[1]), int(m[2])


def そろえる(v, 形: str = "中") -> str | None:
    """支給月の字 → 形の字。読めなければ None（使う側が止める）。"""
    x = 読む(v)
    return None if x is None else 字にする(*x, 形)


def ずらす(v, 月数: int, 形: str = "中") -> str | None:
    """支給月の字を 月数 だけ前後へ（-1＝前の支給月・1＝次の支給月）。読めなければ None。"""
    x = 読む(v)
    if x is None:
        return None
    n = x[0] * 12 + (x[1] - 1) + int(月数)
    return 字にする(n // 12, n % 12 + 1, 形)


def その形か(v, 形: str) -> bool:
    """v がちょうど 形 の字か（前後の空白・全角・桁の足りない月も外す＝読み直して同じ字になる物だけ）。"""
    return isinstance(v, str) and そろえる(v, 形) == v


def 見本の形(見本) -> str:
    """呼ぶ側が渡した支給月の字の形（返す字を同じ書き方にそろえる時に使う）: `YYYY-MM…` は 中・`…支給` は 殻・ほかは 比べる。"""
    s = str(見本).strip()
    if len(s) >= 7 and s[4] == "-":
        return "中"
    return "殻" if s.endswith("支給") else "比べる"


def 殻の字へ(v) -> str:
    """台帳・マスタの行へ書く字: 中の字 `YYYY-MM` なら殻の字 `YYYY.MM支給` に。ほかの字（もう殻の字・空）はそのまま。"""
    s = "" if v is None else str(v).strip()
    return そろえる(s, "殻") if その形か(s, "中") else s
