"""出口の手前の関所（確かめと仮.md §3）。出口に 1 つだけ。

仮が 1 つでも残る人を、取り込み・支給控除一覧・突き合わせ・納品の全部から外す（印つきで出さない）。
外した人の一覧（支給月・会社・NO・仮の数・待っている問いの番号）を返す。
後ろの部品（書き口・突き合わせ）は `関所を通った` だけを受ける＝関所を飛ばした行は型で止まる。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .行 import 確定, 数にする, 行, 行たちにする


def 仮の値か(r: 行) -> bool:
    """状態が `確定` で値がある時だけ確定。ほか（`仮`・空・知らない語）は全部仮に数える。"""
    return r.状態 != 確定 or r.値 is None


@dataclass(frozen=True)
class 外した人:
    支給月: str
    会社: str
    NO: str
    仮の数: int
    問いの番号: tuple[str, ...]

    def 行(self) -> dict:
        return {"支給月": self.支給月, "会社": self.会社, "NO": self.NO,
                "仮の数": self.仮の数, "問いの番号": "・".join(self.問いの番号)}


_関所の印 = object()   # 関所の外で 関所を通った を作らせない印（通す() だけが渡す）
確認済 = "確認済"


@dataclass(frozen=True)
class 関所を通った:
    """確定の人の行だけ。書き口・突き合わせはこれしか受けない。

    型だけで守らず中身でも守る: 関所の印が無い・仮の値の行がある・外した人の行がある時は作れない
    （直に作る・dataclasses.replace で行を足す道を止める）。
    """
    行たち: tuple[行, ...]
    外した人たち: tuple[外した人, ...]
    印: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self.印 is not _関所の印:
            raise TypeError("関所を通った は 出口.関所.通す だけが作る")
        外した = self.外した人の鍵()
        for r in self.行たち:
            if not isinstance(r, 行) or 仮の値か(r) or r.人 in 外した:
                raise ValueError(f"関所を通った に仮の行か外した人の行がある: {getattr(r, '鍵', r)}")

    def 人たち(self) -> list[tuple[str, str, str]]:
        return sorted({r.人 for r in self.行たち})

    def 外した人の鍵(self) -> set[tuple[str, str, str]]:
        return {(x.支給月, x.会社, x.NO) for x in self.外した人たち}


def 通す(rows, 人の状態: dict | None = None) -> 関所を通った:
    """芯の人×項目の行（状態つき）を受け、仮の人を外す。

    人の状態: 芯が返す人ごとの状態 {(支給月, 会社, NO): '確認済'|'仮'}（任意）。
      行に仮が無くても、人の状態が `確認済` でない人（`仮`・知らない語）は外す（どちらか一方でも仮なら外す）。
    """
    rs = 行たちにする(rows)
    仮の行: dict[tuple, list[行]] = {}
    for r in rs:
        if 仮の値か(r):
            仮の行.setdefault(r.人, []).append(r)
    for k, v in (人の状態 or {}).items():
        k = tuple(str(x) for x in k)
        if v != 確認済 and k not in 仮の行:
            仮の行[k] = []
    外す = []
    for k in sorted(仮の行):
        問い = []
        for r in 仮の行[k]:
            for q in r.問いの番号:
                if q not in 問い:
                    問い.append(q)
        外す.append(外した人(*k, 仮の数=len(仮の行[k]), 問いの番号=tuple(問い)))
    残す = tuple(r for r in rs if r.人 not in 仮の行)
    return 関所を通った(行たち=残す, 外した人たち=tuple(外す), 印=_関所の印)


# 勤怠の欄で出口へ渡せる単位（出口/形.py の 値の形 のうち勤怠の物）。円は計算の行が持つ。
勤怠の単位 = ("日", "分", "回")


def 勤怠の行を分ける(rows) -> tuple[list[dict], list[dict]]:
    """芯/集計 の行（人×項目の縦・単位つき）を、関所へ混ぜる行と出口へ出さない行に分ける。

    渡す: 単位が 日・分・回 で値が数（か空＝仮）の行。計算の行と一緒に `通す` へ渡す（状態はそのまま関所が見る）。
    出さない: 単位が数の外（`年休を取った日` の日付など）・単位が無い・値が数でない行。関所で止めずに分けて返す（黙って捨てない）。
    集計の行の `問い`（問の番号）は `問いの番号` に写す（外した人の一覧に集計の問いも出る）。
    """
    渡す, 出さない = [], []
    for r in rows:
        r = dict(r)
        値 = r.get("値")
        if r.get("単位") not in 勤怠の単位:
            出さない.append(r)
            continue
        if 値 is not None and 値 != "":
            try:
                数にする(値)
            except (TypeError, ValueError):
                出さない.append(r)
                continue
        if not r.get("問いの番号") and r.get("問い"):
            r["問いの番号"] = r["問い"]
        渡す.append(r)
    return 渡す, 出さない


def 通ったかを確かめる(x) -> 関所を通った:
    if not isinstance(x, 関所を通った):
        raise TypeError("出口の部品は関所を通った行だけを受ける（出口.関所.通す を先に回す）")
    x.__post_init__()   # 作った後に中身を替えられていないかをもう一度見る
    return x
