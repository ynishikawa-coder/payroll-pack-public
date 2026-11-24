"""計算の芯の 3 つの軸（純粋な関数・Drive を開かない・製品の名と形を持たない）。

- 軸1 量の絞り込み `量を絞る`: 日の種類（平日・所定休日・法定休日・祝日）× 曜日 × 時間帯（例 22:00-05:00）× 法の区分
  （所定内・法定内・法定外・60時間超）を条件で選び、その時間（時間の数）を返す。区間は 芯/集計 の日の結果を分けた物を受ける。
- 軸2 単価の表 `単価を引く`: 設定の `項目.単価`＝{名: {"式": …, "丸め": …}}。式は 名（`人.日給` などの値・`単価:<名>`・量の名）と
  数と + − × ÷ （ ） だけ。`単価:<名>` は表の別の単価を引く（巡りは止める）。丸めは 形.丸める の語（空＝しない）。
- 軸3 法の床 `法の床`: 会社の払い方で出した額と法の最低額を比べ、足りない分だけを割増に入れて仮の理由を付ける（黙って出さない）。
  固定残業（額で）の差額（`差額`）もこの軸の 1 つの形（覆う額を引いた残りを払う）。

法の値（率・8 時間など）はここに書かない（呼ぶ側が法の表から引いて渡す）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from .形 import 丸める, 数

日の種類たち = ("平日", "所定休日", "法定休日", "祝日")
法の区分たち = ("所定内", "法定内", "法定外", "60時間超")
曜日たち = "月火水木金土日"


class 式が無い(Exception):
    """パックに無い式（黙って別の式で計算しない＝起票する）。"""


# ---------------- 軸1 量の絞り込み ----------------

def _分(s) -> int:
    h, m = str(s).strip().replace("：", ":").split(":")
    return int(h) * 60 + int(m)


def 時間帯を読む(s: str) -> list[tuple[int, int]]:
    """`22:00-05:00` → 分の区間の並び（日をまたぐ帯は [22:00, 29:00) の 1 つ。量を絞る が前の日・次の日へずらして見る）。"""
    a, b = (x.strip() for x in str(s).replace("〜", "-").replace("～", "-").split("-", 1))
    始, 終 = _分(a), _分(b)
    if 始 < 終:
        return [(始, 終)]
    return [(始, 終 + 1440)]


def _重なり(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def 量を絞る(区間たち: list[dict], 条件: dict) -> Decimal:
    """区間: {"日の種類", "曜日", "始め"(分・0 時から。翌日は 1440 以上), "終わり", "法の区分"}。
    条件: {"日の種類": [...], "曜日": [...], "時間帯": "22:00-05:00", "法の区分": [...]}（無い鍵は絞らない）。
    条件の値が選べる値の外なら 式が無い（黙って全部を数えない）。返すのは時間（分÷60）。"""
    for 鍵, 選べる in (("日の種類", 日の種類たち), ("法の区分", 法の区分たち), ("曜日", tuple(曜日たち))):
        for x in 条件.get(鍵) or ():
            if x not in 選べる:
                raise 式が無い(f"量の条件の {鍵}「{x}」が軸の選べる語に無い")
    外 = set(条件) - {"日の種類", "曜日", "時間帯", "法の区分"}
    if 外:
        raise 式が無い(f"量の条件の鍵「{'・'.join(sorted(外))}」が軸の選べる語に無い")
    帯 = 時間帯を読む(条件["時間帯"]) if 条件.get("時間帯") else None
    分 = 0
    for r in 区間たち:
        if any(条件.get(鍵) and r.get(鍵) not in 条件[鍵] for 鍵 in ("日の種類", "曜日", "法の区分")):
            continue
        区 = (int(r["始め"]), int(r["終わり"]))
        if 帯 is None:
            分 += 区[1] - 区[0]
        else:   # 翌日へまたぐ区間（終わり > 1440）・0 時からの朝の分も、同じ帯を 1 日ずらして見る
            分 += sum(_重なり(区, (s + k, e + k)) for s, e in 帯 for k in (-1440, 0, 1440))
    return Decimal(分) / 60


def 日を数える(区間たち: list[dict], 条件: dict) -> int:
    """条件に当たる時間が 1 分でもある日の数（日で払う手当＝例 祝日の手当×日数）。区間に "日" が要る。"""
    return len({r["日"] for r in 区間たち if 量を絞る([r], 条件)})


def 日の所定の平均(曜日の所定: dict) -> Decimal | None:
    """曜日で所定が違う時の 1 日の所定（労基則 19 条 1 項 2 号: 日によって違う時は 1 週の 1 日平均）。
    曜日の所定が 0・空の曜日（休み）は数えない。曜日の鍵が 1 つも無ければ None。"""
    xs = [数(曜日の所定.get(c), "時間.日の所定") for c in 曜日たち]
    xs = [x for x in xs if x]
    if not xs:
        return None
    return sum(xs) / len(xs)


# ---------------- 軸2 単価の表 ----------------

_字 = re.compile(r"\s*(\d+(?:\.\d+)?|[+＋\-−－×*÷/()（）]|[^\s+＋\-−－×*÷/()（）]+)")


def _字に分ける(式: str) -> list[str]:
    s, i, out = str(式), 0, []
    while i < len(s):
        m = _字.match(s, i)
        if not m or not m.group(1):
            if s[i:].strip() == "":
                break
            raise 式が無い(f"単価の式「{式}」が読めない")
        out.append(m.group(1))
        i = m.end()
    return out


class _読み:
    def __init__(self, 字たち, 引く):
        self.t, self.i, self.引く = 字たち, 0, 引く

    def _見る(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def _取る(self):
        x = self._見る()
        self.i += 1
        return x

    def 式(self) -> Decimal:
        x = self.項()
        while self._見る() in ("+", "＋", "-", "−", "－"):
            op = self._取る()
            y = self.項()
            x = x + y if op in ("+", "＋") else x - y
        return x

    def 項(self) -> Decimal:
        x = self.元()
        while self._見る() in ("×", "*", "÷", "/"):
            op = self._取る()
            y = self.元()
            if op in ("÷", "/"):
                if not y:
                    raise 式が無い("単価の式で 0 で割る")
                x = x / y
            else:
                x = x * y
        return x

    def 元(self) -> Decimal:
        x = self._取る()
        if x is None:
            raise 式が無い("単価の式が途中で終わる")
        if x in ("(", "（"):
            v = self.式()
            if self._取る() not in (")", "）"):
                raise 式が無い("単価の式の括弧が閉じない")
            return v
        if re.fullmatch(r"\d+(?:\.\d+)?", x):
            return Decimal(x)
        return self.引く(x)


パックに無い単価の形 = {
    "年俸（賞与を含む）": "年俸に賞与を含む人の割増の基礎（賞与の分を年俸から分ける式）はパックに無い",
}


def 単価を引く(名: str, 単価の表: dict, 値たち: dict, _道: tuple = ()) -> Decimal:
    """`単価:<名>` の値。単価の表＝`項目.単価`（{名: {"式", "丸め", "形"?}}）。値たち＝式の中の名の値（人の値・量・その日の所定）。
    名が無い・値が無い・式が読めない・巡る・パックに無い形は 式が無い（黙って 0 にしない）。"""
    if 名 in _道:
        raise 式が無い(f"単価:{名} が巡る（{'→'.join(_道 + (名,))}）")
    e = (単価の表 or {}).get(名)
    if not isinstance(e, dict) or not str(e.get("式") or "").strip():
        raise 式が無い(f"項目.単価 に {名} が無い")
    if e.get("形") in パックに無い単価の形:
        raise 式が無い(パックに無い単価の形[e["形"]])

    def 引く(x: str) -> Decimal:
        if x.startswith("単価:"):
            return 単価を引く(x[3:], 単価の表, 値たち, _道 + (名,))
        v = 数(値たち.get(x), x) if x in 値たち else None
        if v is None:
            raise 式が無い(f"単価:{名} の式の {x} に値が無い")
        return v

    r = _読み(_字に分ける(e["式"]), 引く)
    x = r.式()
    if r._見る() is not None:
        raise 式が無い(f"単価:{名} の式「{e['式']}」が読めない")
    return 丸める(x, e.get("丸め") or "しない")


def 日ごとに丸めて足す(単価: Decimal, 日ごとの時間: list, 率: Decimal, 丸め: str) -> Decimal:
    """時給の端数を日ごとに丸める式: Σ 丸め(単価×その日の時間×率)。月にまとめてから丸めると 1 円ずれる形を分ける。"""
    return sum((丸める(単価 * Decimal(str(h)) * 率, 丸め) for h in 日ごとの時間), Decimal(0))


# ---------------- 軸3 法の床 ----------------

@dataclass
class 床の結果:
    払う: Decimal                     # 会社の額＋足りない分（＝法の床を下回らない額）
    足りない: Decimal                 # 法の床−会社の額（0 以上）。割増に入れる分
    理由: list = field(default_factory=list)   # 足りない時の仮の理由の文（黙って出さない）

    @property
    def 仮か(self) -> bool:
        return self.足りない > 0


def 法の床(会社の額: Decimal, 法の額: Decimal, 名: str) -> 床の結果:
    """会社の払い方で出した額と法の最低額を比べる。足りない分だけを割増に入れ、仮の理由を付ける。"""
    足りない = max(Decimal(0), 法の額 - 会社の額)
    理由 = [f"{名} の会社の払い方の額 {会社の額} が法の床 {法の額} を下回る（不足 {足りない} を割増に入れて仮）"] if 足りない else []
    return 床の結果(会社の額 + 足りない, 足りない, 理由)


def 差額(法の額: Decimal, 覆う額: Decimal) -> Decimal:
    """固定残業（額で）の形: 法で出した額のうち、固定の手当が覆う額を超えた分（払う差額）。覆う方が多ければ 0。"""
    return max(Decimal(0), 法の額 - 覆う額)


def 固定残業の床(固定額: Decimal, 法の額たち: dict, 覆う: tuple) -> tuple[dict, list]:
    """固定残業が覆う割増（時間外・休日・深夜のうち `覆う` に挙げた物）の法の額の和と固定額を比べ、
    足りない分だけを割増に入れる（覆う物から先に、挙げた順に当てる）。覆わない物は法の額のまま払う。
    返す: ({割増の名: 払う額}, 理由たち)。"""
    外 = [k for k in 覆う if k not in 法の額たち]
    if 外:
        raise 式が無い(f"固定残業が覆う「{'・'.join(外)}」の法の額が無い")
    払う = {k: v for k, v in 法の額たち.items() if k not in 覆う}
    残り = 固定額
    理由 = []
    for k in 覆う:
        当てる = min(残り, 法の額たち[k])
        残り -= 当てる
        払う[k] = 法の額たち[k] - 当てる
    不足 = sum(払う[k] for k in 覆う)
    if 不足:
        理由.append(f"固定残業 {固定額} が覆う割増（{'・'.join(覆う)}）の法の額 {sum(法の額たち[k] for k in 覆う)} に足りない"
                  f"（不足 {不足} を割増に入れて仮）")
    return 払う, 理由


重なりの扱いたち = ("高い方", "足す")


def 重なりの率(会社の率: Decimal, 法の率: Decimal, 扱い: str) -> Decimal:
    """1 つの時間に会社の率（例 所定休日を休日の率で）と法の率（例 60 時間超）が重なる時の率。
    高い方＝大きい方の率（割増の部分を重ねない）。足す＝1 を超えた分を足す（1＋(会社−1)＋(法−1)）。
    どちらでも法の率を下回らない。扱いが選べる値の外なら 式が無い（止まらず黙って片方にしない）。"""
    if 扱い == "高い方":
        return max(会社の率, 法の率)
    if 扱い == "足す":
        return 1 + (会社の率 - 1) + (法の率 - 1)
    raise 式が無い(f"率の重なりの扱い「{扱い}」は 高い方・足す の外")
