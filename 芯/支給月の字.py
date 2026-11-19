"""支給月の字の読み書きの正本（入口・芯・出口・初期設定・月次の全部がここを読む。層ごとに字を組まない）。

字の形（docs/毎月の流れ.md「支給月の書き方」）:
  殻     `YYYY.MM支給`   殻・台帳とマスタのシートの行・問いの行が書く字
  比べる `YYYY.MM`       段の解決が月を比べる字
  中     `YYYY-MM`       パックの中（入口の表・芯の人×項目・出口の名と証明）の字。賞与は `YYYY-MM-賞与`
  置き場 `YYYY.MM支給（M月分）` 月の置き場（3_月ごと/<月>/）・管理表の行・確認事項の名の字。M は締めた期間の終わりの月
         （支給の月 当月＝支給月・翌月＝前の月・翌々月＝2 つ前の月）＝年月だけでは決まらないので `字にする` に 月分 を渡す
管理表の鍵のように「どの字で書かれていても同じ支給月か」を比べる所は `鍵の年月` を読む（殻と置き場の字だけ受け、ほかは None）。
読める字は `YYYY.MM支給`・`YYYY.MM`・`YYYY-MM`・`YYYY/MM`・`YYYY年M月`・`YYYY年M月支給`（全角・空白も読む）。
読めない字（空・月が 1〜12 の外・ほかの形）は `読む` が None を返し、使う側が止める（黙って月を見当しない）。
字を組むのは `字にする` 1 つだけ（ほかの関数もここも、字はそれを通して作る）。
"""
from __future__ import annotations

import re
import unicodedata

形たち = ("殻", "比べる", "中", "置き場")
_読める形 = re.compile(r"(\d{4})(?:[./-]|年)(\d{1,2})月?(?:支給.*)?")
_置き場の形 = re.compile(r"(\d{4})\.(\d{2})支給（(\d{1,2})月分）")
月分の離れ = (0, 1, 2)   # 支給の月 当月・翌月・翌々月＝M 月分は支給月の 0〜2 つ前の月


def 字にする(年: int, 月: int, 形: str = "中", 賞与: bool = False, 月分: int | None = None) -> str:
    """年と月 → 形の字（支給月の字を組む唯一の所）。賞与の字は 中 の形だけ（`YYYY-MM-賞与`）。
    置き場 の形は 月分（M 月分の M・支給月の 0〜2 つ前の月）が要る。ほかの形に 月分 は渡さない。"""
    if 形 not in 形たち:
        raise ValueError(f"支給月の字の形 {形!r} は {'・'.join(形たち)} のどれでもない")
    年, 月 = int(年), int(月)
    if not (1 <= 月 <= 12 and 0 < 年 <= 9999):
        raise ValueError(f"支給月の年月が無い月: {年}年{月}月")
    if 賞与 and 形 != "中":
        raise ValueError(f"賞与の字は 中 の形（YYYY-MM-賞与）だけ: 形 {形}")
    if (形 == "置き場") != (月分 is not None):
        raise ValueError(f"月分 は 置き場 の形だけに渡す（形 {形}・月分 {月分!r}）")
    if 形 == "置き場":
        月分 = int(月分)
        if not any((月 - 1 - d) % 12 + 1 == 月分 for d in 月分の離れ):
            raise ValueError(f"{年}.{月:02d}支給 の（{月分}月分）は支給月の 0〜2 つ前の月でない")
        return f"{年:04d}.{月:02d}支給（{月分}月分）"
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


def 置き場の字を読む(v) -> tuple[int, int, int] | None:
    """置き場の字 `YYYY.MM支給（M月分）` → (年, 月, M)。ちょうどその形（`字にする` が組む字）でなければ None。"""
    if not isinstance(v, str):
        return None
    m = _置き場の形.fullmatch(v)
    if not m:
        return None
    try:
        字 = 字にする(int(m[1]), int(m[2]), "置き場", 月分=int(m[3]))
    except ValueError:
        return None
    return (int(m[1]), int(m[2]), int(m[3])) if 字 == v else None


def 鍵の年月(v) -> tuple[int, int] | None:
    """管理表の鍵など、行を探す所が支給月を比べる (年, 月)。受けるのは殻の字 `YYYY.MM支給` と置き場の字
    `YYYY.MM支給（M月分）` のちょうどの形だけ（前後の空白・全角・桁の足りない月・ほかの形は None＝使う側が止める）。"""
    if その形か(v, "殻"):
        return 読む(v)
    x = 置き場の字を読む(v)
    return None if x is None else x[:2]


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
