"""芯/集計 の形: 値の読み方・月の数字の語・決まりと法の線の引き方。

値の形は docs/設計/勤怠の形.md の「共通の値の形」に合わせる。
時間・分は整数の分、日数は Decimal（0.5 刻み）。法の値（日 8 時間・週 40 時間・深夜帯など）はここに書かない＝法の線（引数）で受ける。
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

# 月の数字の語（勤怠の形.md 5 節「月の数字から入る口」の項目と単位）。出す順もこの順。
月の語: tuple[tuple[str, str], ...] = (
    ("所定日数", "日"),
    ("出勤日数", "日"),
    ("休日勤務日数（法定）", "日"),
    ("休日勤務日数（所定）", "日"),
    ("年休（全日）", "日"),
    ("年休（半日）", "回"),
    ("年休（時間）", "分"),
    ("特別休暇（有給）", "日"),
    ("特別休暇（無給）", "日"),
    ("欠勤", "日"),
    ("休業", "日"),
    ("総労働", "分"),
    ("所定内", "分"),
    ("法定内残業", "分"),
    ("法定外残業", "分"),
    ("60 時間超", "分"),
    ("深夜", "分"),
    ("法定休日", "分"),
    ("所定休日", "分"),
    ("遅刻早退", "分"),
    ("夜勤の回数", "回"),
    ("年休を取った日", "日付"),
)
単位 = dict(月の語)
時間の語 = ("総労働", "所定内", "法定内残業", "法定外残業", "60 時間超", "深夜", "法定休日", "所定休日", "遅刻早退")
分ける語 = ("所定内", "法定内残業", "法定外残業", "60 時間超")  # 週・制度の判定で変わる語

曜日 = "月火水木金土日"  # date.weekday() の順


class 形の誤り(ValueError):
    """表 A・B・決まり・法の線の値が形に合わない。"""


def 空(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def 分(v) -> int | None:
    """時刻 `h:mm`（0:00〜47:59）を 0:00 からの分に。空は None。"""
    if 空(v):
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    h, _, m = s.partition(":")
    if not (h.isdigit() and len(m) == 2 and m.isdigit() and int(m) < 60):
        raise 形の誤り(f"時刻の形でない: {s}")
    return int(h) * 60 + int(m)


def 整数(v) -> int | None:
    """分などの整数。空は None。"""
    if 空(v):
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if not s.lstrip("-").isdigit():
        raise 形の誤り(f"整数でない: {s}")
    return int(s)


def 数(v) -> Decimal | None:
    if 空(v):
        return None
    try:
        return Decimal(str(v).strip())
    except InvalidOperation:
        raise 形の誤り(f"数でない: {v}") from None


def 時間の分(v) -> int | None:
    """決まり・法の線の「時間」（`8`・`7.5`・`7:30`）を分に。"""
    if 空(v):
        return None
    if isinstance(v, str) and ":" in v:
        return 分(v)
    d = 数(v) * 60
    if d != d.to_integral_value():
        raise 形の誤り(f"分に割り切れない時間: {v}")
    return int(d)


def 日付(v) -> date:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v).strip())
    except ValueError:
        raise 形の誤り(f"日付の形でない: {v}") from None


def 語たち(v) -> list[str]:
    return [] if 空(v) else [w.strip() for w in str(v).split("、") if w.strip()]


def 時間帯(v) -> tuple[int, int]:
    """`22:00〜5:00` を (始め, 終わり) の分に。終わりが始め以下なら次の日（+1440）。"""
    a, sep, b = str(v).partition("〜")
    if not sep:
        raise 形の誤り(f"時間帯の形でない: {v}")
    s, e = 分(a), 分(b)
    return (s, e + 1440 if e <= s else e)


def 詰め(v) -> str:
    """選べる値の語の空白を除く（`1 勤務 = 2 日` と `1勤務=2日` を同じに読む）。"""
    return "".join(str(v).split()) if not 空(v) else ""


@dataclass
class 決まり:
    """その人のその月に効く値（会社の決まり.md の `分野.名` の項目）。

    段の解決（人→勤務の型→会社→事務所→仕組み）は芯の手前で済ませて渡す（会社の決まり.md §1.1）。
    勤務の型ごとに違う値は `勤務の型` に {型の鍵: {項目: 値}} で渡す（表 A の「勤務の型」の列で引く）。
    """
    値たち: dict = field(default_factory=dict)

    def 引く(self, 名: str, 型: str | None = None):
        if 型:
            v = (self.値たち.get("勤務の型") or {}).get(型, {}).get(名)
            if not 空(v):
                return v
        v = self.値たち.get(名)
        return None if 空(v) else v

    def 曜日の値(self, 名: str, d: date, 型: str | None = None):
        """曜日ごとに置ける値（{曜日: 値} の形）は日付の曜日で引く。"""
        v = self.引く(名, 型)
        if isinstance(v, dict):
            v = v.get(曜日[d.weekday()])
        return None if 空(v) else v


@dataclass
class 法の線:
    """法の値（引数で受ける。コードに書かない）。

    要る: `時間.日の法定`（時間）・`時間.週の法定`（時間）・`割増.深夜の時間帯`（`22:00〜5:00` の形）
    任意: `時間.週の法定の特例`（時間。労基則 25 条の 2 の特例の線）・`割増.60時間超の境`（月の時間）・
          `時間.休憩の長さ`（[[超える時間, 休憩の分], …]。34 条）・`休日.4週の休日数`（35 条 2 項）
    """
    日の法定: int
    週の法定: int
    深夜帯: tuple[int, int]
    週の法定の特例: int | None = None
    六十時間: int | None = None
    休憩の長さ: tuple[tuple[int, int], ...] = ()
    四週の休日数: int | None = None

    @classmethod
    def 読む(cls, d: dict) -> "法の線":
        for k in ("時間.日の法定", "時間.週の法定", "割増.深夜の時間帯"):
            if 空(d.get(k)):
                raise 形の誤り(f"法の線に {k} が無い")
        return cls(
            日の法定=時間の分(d["時間.日の法定"]),
            週の法定=時間の分(d["時間.週の法定"]),
            深夜帯=時間帯(d["割増.深夜の時間帯"]),
            週の法定の特例=時間の分(d.get("時間.週の法定の特例")),
            六十時間=時間の分(d.get("割増.60時間超の境")),
            休憩の長さ=tuple(sorted((時間の分(a), 整数(b)) for a, b in d.get("時間.休憩の長さ") or ())),
            四週の休日数=整数(d.get("休日.4週の休日数")),
        )


@dataclass
class 仮:
    """値を仮にする理由。項目が None なら、その人の全部の項目に効く。"""
    理由: str
    日付: date | None = None
    項目: frozenset | None = None


def 区間の差(元: list[tuple[int, int]], 引く: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """元の区間から引く区間を除いた区間（どちらも [始め, 終わり)）。"""
    out = []
    for s, e in 元:
        片 = [(s, e)]
        for a, b in 引く:
            次 = []
            for x, y in 片:
                if b <= x or y <= a:
                    次.append((x, y))
                    continue
                if x < a:
                    次.append((x, a))
                if b < y:
                    次.append((b, y))
            片 = 次
        out += 片
    return sorted(out)


def 重なり(区間: list[tuple[int, int]], a: int, b: int) -> int:
    return sum(max(0, min(e, b) - max(s, a)) for s, e in 区間)


def 長さ(区間: list[tuple[int, int]]) -> int:
    return sum(e - s for s, e in 区間)
