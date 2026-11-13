"""支払の期間・支給日・会社の暦（所定日数）。祝日は 法の表/祝日.json（1 年 1 行・値 {"日": {日付: 名}}）を引く口（引く口.py）から引く。

- 期間: `支払.締め日`（1〜28・末）と `支払.支給の月`（当月・翌月・翌々月）と支給月から、締めた期間の始めと終わりを出す。
- 支給日: `支払.支給日`（1〜28・末）。`支払.支給日が休日`（前倒し・後ろ倒し）で土日・祝日を避ける。
- 会社の暦: `時間.暦` = {"休みの曜日": ["土", "日"], "祝日": "休み"|"出勤", "会社の休み": ["YYYY-MM-DD", …]}。無ければ 土日祝が休み（会社の決まり §2 の既定）。
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from . import 引く口 as 口

曜日 = "月火水木金土日"
既定の暦 = {"休みの曜日": ["土", "日"], "祝日": "休み", "会社の休み": []}
_月のずれ = {"当月": 0, "翌月": 1, "翌々月": 2}


def 月を足す(年: int, 月: int, n: int) -> tuple[int, int]:
    k = 年 * 12 + (月 - 1) + n
    return k // 12, k % 12 + 1


def 日にする(年: int, 月: int, 日) -> date:
    末 = calendar.monthrange(年, 月)[1]
    if str(日).strip() == "末":
        return date(年, 月, 末)
    d = int(str(日).strip())
    if not 1 <= d <= 28:
        raise ValueError(f"日「{日}」は 1〜28・末 の外")
    return date(年, 月, d)


def 支給月を読む(支給月: str) -> tuple[int, int]:
    y, m = str(支給月)[:7].split("-")
    return int(y), int(m)


def 期間(支給月: str, 締め日, 支給の月) -> tuple[date, date]:
    if 支給の月 not in _月のずれ:
        raise ValueError(f"支払.支給の月「{支給の月}」は 当月・翌月・翌々月 の外")
    y, m = 月を足す(*支給月を読む(支給月), -_月のずれ[支給の月])
    終わり = 日にする(y, m, 締め日)
    py, pm = 月を足す(y, m, -1)
    始め = 日にする(py, pm, 締め日) + timedelta(days=1)
    return 始め, 終わり


def 祝日(年: int, 置き場=None) -> tuple[set[date], str, bool]:
    """その年の祝日（と出所・仮か）。表が無い・欠けは 口.欠け を投げる。"""
    r = 口.引く("祝日", f"{年}-01-01", 置き場=置き場)
    return {date.fromisoformat(str(d)) for d in r.値["日"]}, r.出所, r.仮


def 休みか(d: date, 暦: dict, 祝日たち: set[date]) -> bool:
    if 曜日[d.weekday()] in (暦.get("休みの曜日") or []):
        return True
    if 暦.get("祝日", "休み") == "休み" and d in 祝日たち:
        return True
    return d.isoformat() in {str(x) for x in 暦.get("会社の休み") or []}


def 所定日数(始め: date, 終わり: date, 暦: dict | None, 置き場=None) -> tuple[int, list[str], bool]:
    """始め〜終わり（両端を含む）の会社の暦の所定日数・出所・仮か。"""
    暦 = 暦 or 既定の暦
    祝, 出所, 仮 = set(), [], False
    for y in range(始め.year, 終わり.year + 1):
        s, o, k = 祝日(y, 置き場)
        祝 |= s
        出所.append(o)
        仮 |= k
    n, d = 0, 始め
    while d <= 終わり:
        n += not 休みか(d, 暦, 祝)
        d += timedelta(days=1)
    return n, 出所, 仮


def 支給日(支給月: str, 日, 休日の時: str = "前倒し", 置き場=None) -> date:
    """支給日（土日・祝日なら前倒し・後ろ倒し）。祝日が引けなければ 口.欠け を投げる（呼ぶ側が仮にする）。"""
    y, m = 支給月を読む(支給月)
    d = 日にする(y, m, 日)
    祝 = 祝日(y, 置き場)[0]
    step = timedelta(days=-1 if 休日の時 != "後ろ倒し" else 1)
    while d.weekday() >= 5 or d in 祝:
        d += step
    return d
