"""給与ソフトの形と、欄と項目の対応（書き口と読み口が同じ 1 つを使う）。

- 給与ソフトの欄の名・並び・文字コードは出口の中だけ（芯は知らない）。
- 会社ごとに違う対応は Drive のマスタ「項目」の給与ソフトの欄から殻が引数で渡す（`欄の対応`）。
- 書き口は対応を順に引き、読み口は同じ対応を逆に引く（読み用の対応を別に持たない・確かめと仮.md §2）。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_UP, Decimal

from .行 import 数にする

# 値の形（単位）。芯の値は 円＝整数・日＝数・分＝時間（勤怠の形.md §5 の単位）・回＝数。
値の形たち = ("円", "日", "分", "回")
# 時間の書き方（給与ソフトへ書く・読む字の形）。会社のマスタ「時間の書き方」から殻が渡す。
時間の書き方たち = ("60進", "時:分", "10進")


@dataclass(frozen=True)
class 欄:
    """1 項目 ↔ 1 欄。渡す＝取り込みに書く。受ける＝給与ソフトの出力から読む（突き合わせる）。"""
    項目: str
    欄: str
    形: str = "円"
    渡す: bool = True
    受ける: bool = True

    def __post_init__(self):
        if self.形 not in 値の形たち:
            raise ValueError(f"欄「{self.欄}」の形「{self.形}」は {'・'.join(値の形たち)} の外")
        if not (self.渡す or self.受ける):
            raise ValueError(f"欄「{self.欄}」は渡すも受けるも無い")


def 対応にする(rows) -> tuple[欄, ...]:
    """マスタ「項目」の給与ソフトの欄（殻が渡す dict の並び）を対応にする。1 項目に 1 欄・1 欄に 1 項目。"""
    out = []
    for d in rows:
        if isinstance(d, 欄):
            out.append(d)
            continue
        out.append(欄(項目=str(d["項目"]), 欄=str(d["欄"]), 形=str(d.get("形") or "円"),
                     渡す=_はい(d.get("渡す", True)), 受ける=_はい(d.get("受ける", True))))
    for 名 in ("項目", "欄"):
        seen = set()
        for x in out:
            v = getattr(x, 名)
            if v in seen:
                raise ValueError(f"対応に同じ{名}が 2 つ: {v}")
            seen.add(v)
    return tuple(out)


def _はい(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip() in ("はい", "true", "True", "1", "○")


@dataclass(frozen=True)
class 給与ソフトの形:
    """給与ソフトごとの取り込み・出力の file の形。欄の中身（項目）は `欄の対応` が持つ。"""
    名: str
    鍵の欄: str | None = None          # 人を引く欄（社員の番号）
    氏名の欄: str | None = None        # 書く時だけ。殻が NO→氏名 を渡した時に埋める
    後ろの欄: tuple[str, ...] = ()     # 書く時に後ろへ空で足す欄
    文字コード: str | None = None
    区切り: str = ","
    向き: str = "横"                   # 出力を読む時の向き。横＝人が行・縦＝人が列
    確かめた: bool = True              # False の所は公開の仕様で確かめていない＝殻が全部を渡すまで使えない
    要る: tuple[str, ...] = field(default=("鍵の欄", "文字コード"))

    def 使える形(self, **上書き) -> "給与ソフトの形":
        f = replace(self, **上書き) if 上書き else self
        無い = [k for k in f.要る if not getattr(f, k)]
        if 無い:
            raise ValueError(f"{f.名}: {'・'.join(無い)} が無い（事務所のルール「給与ソフトと取り込みの形」から殻が渡す）")
        if f.向き not in ("横", "縦"):
            raise ValueError(f"{f.名}: 向き「{f.向き}」は 横・縦 の外")
        return f


# 給与ソフトの形の値は持たない（⟦鍵:給与計算/パックに製品ごとの物を置かない⟧）。殻が事務所のルール.md
# 「## 1 給与ソフトと取り込みの形」から読んで 形を組む に渡す（置き場は docs/設計/Drive の型.md §4「製品ごとの値の置き場」）。
形の鍵たち = ("名", "鍵の欄", "氏名の欄", "後ろの欄", "文字コード", "区切り", "向き", "確かめた")


def 形を組む(値: "dict | 給与ソフトの形") -> 給与ソフトの形:
    """殻が事務所の設定から読んだ値（dict）か組んだ 給与ソフトの形 → 使える形。名・鍵の欄・文字コードが無ければ止まる。

    既定の形は持たない（黙って既定で書かない）。後ろの欄は 並び か 読点・カンマ区切りの字。確かめた は はい／いいえ。"""
    if isinstance(値, 給与ソフトの形):
        f = 値
    else:
        d = dict(値 or {})
        知らない = [k for k in d if k not in 形の鍵たち]
        if 知らない:
            raise ValueError(f"給与ソフトの形: 「{'・'.join(知らない)}」は {'・'.join(形の鍵たち)} の外")
        名 = str(d.get("名") or "").strip()
        if not 名:
            raise ValueError("給与ソフトの形: 名 が無い（事務所のルール「給与ソフトと取り込みの形」から殻が渡す）")
        後ろ = d.get("後ろの欄") or ()
        if isinstance(後ろ, str):
            後ろ = [x for x in 後ろ.replace("、", ",").split(",")]
        kw = {"名": 名, "後ろの欄": tuple(str(x).strip() for x in 後ろ if str(x).strip())}
        for k in ("鍵の欄", "氏名の欄", "文字コード", "区切り", "向き"):
            v = str(d.get(k) or "").strip()
            if v:
                kw[k] = v
        if "確かめた" in d:
            kw["確かめた"] = _はい(d["確かめた"])
        f = 給与ソフトの形(**kw)
    return f.使える形()


# ---- 値 ↔ 字 ----

def 字にする(値: Decimal, 形: str, 時間の書き方: str | None) -> str:
    if 形 == "円":
        if 値 != 値.to_integral_value():
            raise ValueError(f"円の値に端数がある: {値}（丸めは芯の決まりの後の値で渡す）")
        return str(int(値))
    if 形 == "分":
        return 分を字に(値, 時間の書き方)
    return _数の字(値)


def 字を数に(字: str, 形: str, 時間の書き方: str | None) -> Decimal | None:
    """空なら None。円の 1,234・¥ は外す。時間は分にそろえる。"""
    s = str(字).strip().replace(",", "").replace("¥", "").replace("円", "")
    if s == "":
        return None
    if 形 == "分":
        return 字を分に(s, 時間の書き方)
    return 数にする(s)


def _数の字(v: Decimal) -> str:
    v = v.normalize()
    if v == v.to_integral_value():
        return str(int(v))
    return format(v, "f")


def _書き方(時間の書き方):
    if 時間の書き方 not in 時間の書き方たち:
        raise ValueError(f"時間の書き方「{時間の書き方}」は {'・'.join(時間の書き方たち)} の外（会社のマスタから殻が渡す）")
    return 時間の書き方


def 分を字に(分: Decimal, 時間の書き方: str | None) -> str:
    w = _書き方(時間の書き方)
    if w == "10進":
        return format((Decimal(分) / 60).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")
    if 分 != 分.to_integral_value():
        raise ValueError(f"分に端数がある: {分}（60進では書けない）")
    m = int(分)
    sign, m = ("-", -m) if m < 0 else ("", m)
    sep = "." if w == "60進" else ":"
    return f"{sign}{m // 60}{sep}{m % 60:02d}"


def 字を分に(字: str, 時間の書き方: str | None) -> Decimal:
    w = _書き方(時間の書き方)
    s = 字.strip()
    if w == "10進":
        return 数にする(s) * 60
    sign = -1 if s.startswith("-") else 1
    s = s.lstrip("-")
    for sep in (":", "."):
        if sep in s:
            h, m = s.split(sep, 1)
            if len(m) != 2 or not (h.isdigit() and m.isdigit()) or int(m) >= 60:
                raise ValueError(f"時間の字が {w} の形でない: {字!r}")
            return Decimal(sign * (int(h) * 60 + int(m)))
    if s.isdigit():
        return Decimal(sign * int(s) * 60)
    raise ValueError(f"時間の字が {w} の形でない: {字!r}")
