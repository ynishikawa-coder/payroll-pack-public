"""芯が読む会社の決まりの 1 枚の表（`芯/設定の表.json`）の読み口。芯/集計 と 芯/計算 の両方がここだけを通して設定を照らす。

- 表に無い名は芯が読めない（`名を確かめる` が `表に無い名` を投げる＝試験で落ちる。芯/集計 の 決まり.引く が呼ぶ）。
- `照らす(値たち, 読む所)`: 計算の最初に、表の形が 選ぶ・端数の語・区分・組・休憩の表 の項目を全部照らす。
  字の揺れ（空白・全角半角の ＋ ：）は吸って表の字にそろえ、選べる値の外の字は既定（既定が無ければ見当）に替えて「外れ」を返す
  （呼ぶ側が仮＋問いにする＝既存の仮の線で出口の手前の関所が止める）。黙って違う形で計算する道を作らない。
- `選べる値の一覧()`: 殻がシートの欄をプルダウンにする材料（形が 選ぶ・区分・組 の項目の名・選べる値・既定）。
- `休憩の表を読む(字の並び)`: `時間.休憩の表` の 3 つの形（時間帯 `12:00〜13:00`・長さ `6:00超45分`・退勤の境 `退勤18:00超30分（パート）`／`退勤19:45超15分（女）`）。

形の正本はこの表。意味と置ける段は 初期設定/項目.json（既定の字が食い違えば tests/計算/test_計算_既定と項目の辞書.py が赤）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

表の置き場 = Path(__file__).resolve().parent / "設定の表.json"
照らす形 = ("選ぶ", "端数の語", "区分", "組", "休憩の表")
内の鍵 = ("勤務の型", "見当の値")   # 段の解決が作る内の鍵（会社の決まりの名でない）


class 表に無い名(KeyError):
    """芯が設定の表に無い名を読んだ（表に足すか、読む名を直す）。"""


@lru_cache(maxsize=1)
def 表() -> dict:
    d = json.loads(表の置き場.read_text(encoding="utf-8"))
    return {e["名"]: e for e in d["項目"]}


def 名を確かめる(名: str) -> dict | None:
    if 名 in 内の鍵:
        return None
    e = 表().get(名)
    if e is None:
        raise 表に無い名(f"「{名}」は 芯/設定の表.json に無い（表に足してから読む）")
    return e


def 揃える(v) -> str:
    """字の揺れを吸う: 空白を除き、半角の + : を全角の ＋ と半角の : にそろえる。"""
    if v is None:
        return ""
    s = "".join(str(v).split())
    return s.replace("+", "＋").replace("：", ":")


def _空(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or v == {} or v == []


@dataclass(frozen=True)
class 外れ:
    名: str
    字: str
    置いた: object      # 替えた値（既定か見当）。None なら値を外した（空として数える）
    型: str | None = None
    訳: str = "選べる値の外"

    def 文(self) -> str:
        所 = f"勤務の型「{self.型}」の " if self.型 else ""
        置 = f"「{self.置いた}」で数えた" if self.置いた is not None else "値を外して数えた"
        return f"{所}{self.名}「{self.字}」は{self.訳}（{置}）"


def _選ぶ(e: dict, v):
    """選べる値に当たれば表の字（括弧の説明つきならその括弧も残す）。外なら None。"""
    s = 揃える(v)
    値たち = {揃える(x): x for x in e.get("選べる値", ())}
    値たち.update({揃える(a): b for a, b in (e.get("揺れ") or {}).items()})
    if s in 値たち:
        return 値たち[s]
    if e.get("括弧") and s.endswith("）") and "（" in s:
        頭, 中 = s[:-1].split("（", 1)
        if 頭 in 値たち:
            return f"{値たち[頭]}（{中}）"
    return None


def _端数の語(e: dict, v):
    from 芯.計算.形 import 丸めの語か   # 端数の語の正本は 芯/計算/形.py（芯/計算 は 芯/設定 を import しても輪にならない）
    if 丸めの語か(v):
        return v
    return _選ぶ(e, v)


def _区分(e: dict, v):
    from 芯.計算.形 import 区分を読む
    return v if 区分を読む(v) is not None else None


def _組(e: dict, v):
    if not isinstance(v, dict):
        return None
    out = {}
    for 欄, x in v.items():
        if 欄 not in e["欄"]:
            return None
        y = _選ぶ({"選べる値": e["欄"][欄]}, x)
        if y is None:
            return None
        out[欄] = y
    return out


def _休憩の表(e: dict, v):
    try:
        休憩の表を読む(v)
    except ValueError:
        return None
    return v


_照らし = {"選ぶ": _選ぶ, "端数の語": _端数の語, "区分": _区分, "組": _組, "休憩の表": _休憩の表}


def 照らす(値たち: dict, 読む所: str) -> tuple[dict, list[外れ]]:
    """値たち（`分野.名` → 値・`勤務の型` → {型: {…}}）の、読む所（`集計`／`計算`）が読む項目を全部照らす。

    返す物: (直した値たち, 外れの並び)。選べる値に当たる字は表の字にそろえ、外の字は既定（無ければ見当、どちらも無ければ値を外す）に替える。
    外れは呼ぶ側がその人の全部の値に効く仮にする（効く項目を絞らない＝絞った項目が行に無い時に仮が落ちて確認済に見える道を作らない）。"""
    out = dict(値たち or {})
    外 = []

    def 照らす一つ(d: dict, 型):
        for 名, x in list(d.items()):
            e = 表().get(名)
            if e is None or e["形"] not in 照らす形 or 読む所 not in e["読む所"] or _空(x):
                continue
            y = _照らし[e["形"]](e, x)
            if y is not None:
                d[名] = y
                continue
            置く = e.get("既定") if e.get("既定") is not None else e.get("見当")
            if 置く is None:
                d.pop(名)
            else:
                d[名] = 置く
            外.append(外れ(名, x if isinstance(x, str) else json.dumps(x, ensure_ascii=False), 置く, 型))

    照らす一つ(out, None)
    if isinstance(out.get("勤務の型"), dict):
        out["勤務の型"] = {k: dict(x) if isinstance(x, dict) else x for k, x in out["勤務の型"].items()}
        for 型, d in out["勤務の型"].items():
            if isinstance(d, dict):
                照らす一つ(d, 型)
    return out, 外


def 既定で埋める() -> dict:
    """計算の前に空を既定で埋める項目（表の `埋める`）→ 既定。"""
    return {n: e["既定"] for n, e in 表().items() if e.get("埋める")}


def 必ず埋める() -> tuple[str, ...]:
    """既定を持たず、空ならその人を計算しない項目（表の `必ず埋める`）の名。名の順。"""
    return tuple(sorted(n for n, e in 表().items() if e.get("必ず埋める")))


def 選べる値の一覧() -> list[dict]:
    """殻がシートの欄をプルダウンにする材料。[{名, 形, 選べる値, 既定, 括弧?, 欄?}]（形が 選ぶ・区分・組 の項目・名の順）。
    W3（殻）の約束の形: 選ぶ・区分 は `選べる値` の字のどれか 1 つを書く（括弧＝True は後ろに（…）の説明を足してよい）。
    組 は `欄` の欄ごとに 1 つ選ぶ（dict で渡す）。この外の字は芯が既定で数えて仮＋問いにする。"""
    out = []
    for n, e in sorted(表().items()):
        if e["形"] not in ("選ぶ", "区分", "組"):
            continue
        x = {"名": n, "形": e["形"], "既定": e.get("既定")}
        if e["形"] == "組":
            x["欄"] = e["欄"]
        else:
            x["選べる値"] = list(e["選べる値"])
            if e.get("括弧"):
                x["括弧"] = True
        out.append(x)
    return out


def 選べる値の字か(名: str, v) -> bool:
    """名の値 v が表の選べる値に当たるか（寄せ・段の解決がマスタへ書く前に照らす）。照らさない形・空は True。"""
    e = 名を確かめる(名)
    if e is None or e["形"] not in 照らす形 or _空(v):
        return True
    return _照らし[e["形"]](e, v) is not None


# ---- 時間.休憩の表 の 3 つの形 ----
_境の形 = re.compile(r"^退勤(\d{1,2}:\d{2})超(\d+)分(?:（(.+)）)?$")
_長さの形 = re.compile(r"^(\d{1,2}(?::\d{2})?)超(\d+)分$")


@dataclass(frozen=True)
class 退勤の境:
    """退勤の時刻が境を越えた日（境ちょうどは越えない）に、長さの分の休憩を引く。
    区分が在ればその 人.区分 の人だけ。性別が在ればその 人.性別 の人だけ（性別の無い人は芯/集計 が仮にする＝黙ってどちらかの境で数えない）。"""
    境: int        # 0:00 からの分
    長さ: int      # 分
    区分: str | None = None
    性別: str | None = None


def 性別の語() -> dict:
    """`人.性別` の選べる値と揺れ → 表の字（境の（…）を読む時の正本＝芯/設定の表.json）。"""
    e = 表()["人.性別"]
    return {**{揃える(x): x for x in e["選べる値"]}, **{揃える(a): b for a, b in (e.get("揺れ") or {}).items()}}


def _分(s: str) -> int:
    h, _, m = s.partition(":")
    if not (h.isdigit() and len(m) == 2 and m.isdigit() and int(m) < 60):
        raise ValueError(f"時刻の形でない: {s}")
    return int(h) * 60 + int(m)


def 休憩の表を読む(v) -> dict:
    """`時間.休憩の表` の値（並びか 、で並べた字）→ {"時間帯": [(始め, 終わり)], "長さ": [(超える分, 休憩の分)], "境": [退勤の境]}。
    3 つの形のどれでもない字が 1 つでもあれば ValueError（黙って飛ばさない＝照らす が値を外して仮にする）。
    時間帯と境は 1 つの表に混ぜてよい（昼の 12:00〜13:00 と 退勤18:00超30分）。長さは混ぜない（段の解決が 時間.休憩の長さ に分ける形）。"""
    from 芯.集計.形 import 時間帯, 形の誤り   # 時間帯の読みの正本（終わりが始め以下なら次の日）
    並び = v if isinstance(v, (list, tuple)) else [w for w in re.split(r"[、,]", str(v or ""))]
    out = {"時間帯": [], "長さ": [], "境": []}
    for x in 並び:
        s = 揃える(x)
        if not s:
            continue
        m = _境の形.match(s)
        if m:
            区分 = 性別 = None
            括弧 = m.group(3)
            if 括弧 is not None:
                from 芯.計算.形 import 区分の語
                if 括弧 in 区分の語:
                    区分 = 括弧
                elif 括弧 in 性別の語():
                    性別 = 性別の語()[括弧]
                else:
                    raise ValueError(f"退勤の境の（{括弧}）は 人.区分 の語でも 人.性別 の語でもない")
            out["境"].append(退勤の境(_分(m.group(1)), int(m.group(2)), 区分, 性別))
            continue
        m = _長さの形.match(s)
        if m:
            a = m.group(1)
            out["長さ"].append((_分(a) if ":" in a else int(a) * 60, int(m.group(2))))
            continue
        try:
            out["時間帯"].append(時間帯(s))
        except 形の誤り:
            raise ValueError(f"時間.休憩の表 の形でない: {x}（`12:00〜13:00`・`6:00超45分`・`退勤18:00超30分` のどれか）") from None
    if out["長さ"] and (out["時間帯"] or out["境"]):
        raise ValueError("時間.休憩の表 に長さの形と時間帯・境の形が混ざっている")
    return out
