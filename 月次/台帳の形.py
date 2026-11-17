"""月次 が返す「台帳」を、型（初期設定/型.json）の台帳のタブの形にする 1 か所。

殻は返った表をそのまま台帳・マスタのタブへ書く（見出しの行が型と同じかを照らしてから 2 行目より下を足す）。
形を作るのはここだけ＝列の名と並びは型の口（初期設定/型の口.py）から引き、ここに列を写さない。

- 台帳「人ごと」: 芯/集計 の行（1 人×1 項目の縦）を 1 人 1 行の横へ。列は型の「人ごと」（会社・支給月・NO・氏名・状態・月の語）。
  型に無い月の語が来たら止める（月の語を足したら型の版を上げる＝直しを添える）。黙って落とさない。
- 台帳「勤怠」「勤怠の区間」「月の変動」・マスタ「人ごとの支給控除」: 入口の行（列名の dict）を型の列の並びへ。
  型に無い列に値が在れば止める（黙って落とさない）。`_` で始まる鍵は中の印＝書かない。
- 支給月は型の書き方（YYYY.MM支給）にそろえる（入口・芯は YYYY-MM で持つ）。
- 台帳「勤怠」の 氏名・出勤の時刻・退勤の時刻 と「勤怠の区間」の 氏名 は、人が台帳を見て確かめるための写し（ここで埋める）。
  氏名は社員のタブから NO で引く（引けない人は空）。出勤の時刻＝その日の労働の区間の最初の始め・退勤の時刻＝最後の終わり
  （区間の字のまま＝日またぎは 24 を足した字・組が幾つもある日も最初の組の始めと最後の組の終わり・労働の区間の無い日は空・
  最後に始まる労働の区間が打刻抜けなら退勤は空）。計算はこの列を読まない（芯は NO と区間で引く・台帳は答えの元にしない）。
"""
from __future__ import annotations

import importlib.util
import re
import sys
from decimal import Decimal
from pathlib import Path

_根 = Path(__file__).resolve().parent.parent


def _型の口():
    名 = "月次_型の口"
    if 名 not in sys.modules:
        spec = importlib.util.spec_from_file_location(名, _根 / "初期設定" / "型の口.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules[名] = m
        spec.loader.exec_module(m)
    return sys.modules[名]


台帳 = "04_台帳_<支給年>"
マスタ = "03_マスタ"
# 返す物の鍵 → (型のシート, タブ)
タブたち = {"勤怠": (台帳, "勤怠"), "勤怠の区間": (台帳, "勤怠の区間"), "月の変動": (台帳, "月の変動"),
         "人ごと": (台帳, "人ごと"), "人ごとの支給控除": (マスタ, "人ごとの支給控除")}
人の列 = ("会社", "支給月", "NO", "氏名", "状態")   # 人ごと の頭の列（後ろは月の語）


class 台帳の形の誤り(ValueError):
    """型の列に無い値を書こうとした（黙って落とさない）。"""


def 見出し(鍵: str) -> list[str]:
    return _型の口().見出し(*タブたち[鍵])


def 支給月の字(v) -> str:
    """YYYY-MM → YYYY.MM支給（型の書き方）。もう型の書き方の字・空はそのまま。"""
    s = "" if v is None else str(v).strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})", s)
    return f"{m.group(1)}.{m.group(2)}支給" if m else s


def _字(v) -> str:
    if v is None:
        return ""
    if isinstance(v, Decimal):
        s = format(v, "f")
        return s.rstrip("0").rstrip(".") if "." in s else s
    if isinstance(v, (list, tuple)):
        return "、".join(_字(x) for x in v)
    return str(v)


def _分(v) -> int | None:
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", _字(v).strip())
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def _日の鍵(r) -> tuple:
    return (支給月の字(r.get("支給月")), _字(r.get("会社")), _字(r.get("NO")), _字(r.get("日付")))


def 出勤と退勤(区間たち) -> dict[tuple, tuple[str, str]]:
    """表 B の行 → {(支給月, 会社, NO, 日付): (出勤の時刻, 退勤の時刻)}（台帳「勤怠」の写しの列へ）。

    労働の区間（始めが読める物）だけを見る。出勤＝始めの一番早い区間の始め。退勤＝一番遅く始まる区間に終わりが無ければ空
    （打刻抜け＝分からない・黙って前の組の終わりを出さない）、在れば終わりの一番遅い字。字は区間の字のまま（日またぎは 24 を足した字）。
    表 B の形（始めは必須・時刻は h:mm。勤怠の形.md §2）は入口が守る前提＝h:mm でない字は読めない時刻として扱う（始めなら区間を見ない・終わりなら打刻抜けと同じ）。"""
    労働: dict[tuple, list] = {}
    for b in 区間たち:
        if _字(b.get("区間の種別")) == "労働" and _分(b.get("始め")) is not None:
            労働.setdefault(_日の鍵(b), []).append(b)
    out = {}
    for k, bs in 労働.items():
        順 = sorted(bs, key=lambda b: (_分(b.get("始め")), _分(b.get("終わり")) is None, _分(b.get("終わり")) or 0))
        出 = _字(順[0].get("始め")).strip()
        終わり = [b for b in bs if _分(b.get("終わり")) is not None]
        退 = "" if _分(順[-1].get("終わり")) is None else _字(max(終わり, key=lambda b: _分(b.get("終わり"))).get("終わり")).strip()
        out[k] = (出, 退)
    return out


def _写しを足す(行たち, 写し) -> list[dict]:
    """入口の行に、人が見るための写しの列（写し(r) の dict）を足す。入口の行に値が在ればそれを残す。"""
    out = []
    for r in 行たち:
        足す = {c: v for c, v in 写し(r).items() if not _字(r.get(c)).strip()}
        out.append({**r, **足す})
    return out


def _表(鍵: str, 行たち) -> list[list[str]]:
    h = 見出し(鍵)
    out = [list(h)]
    for r in 行たち:
        外 = sorted(k for k, v in r.items() if k not in h and not str(k).startswith("_") and _字(v).strip())
        if 外:
            raise 台帳の形の誤り(f"{鍵}: 型の列に無い値 {外}（型を直すか、入口の行を型の列へ）")
        out.append([支給月の字(r.get(c)) if c == "支給月" else _字(r.get(c)) for c in h])
    return out


def 人ごとの表(集計の行, 人の状態=(), 氏名: dict | None = None) -> list[list[str]]:
    """芯/集計 の行（{支給月, 会社, NO, 項目, 値, 状態, …}）→ 型の「人ごと」の表（1 行目が見出し・1 人 1 行）。

    状態: 集計の人の状態（確認済・仮）。人の状態に無い人は行の状態（仮が 1 つでも在れば仮）。
    氏名: {NO: 氏名}（社員のタブから殻か 月次 が渡す・無ければ空）。"""
    h = 見出し("人ごと")
    語 = h[len(人の列):]
    if h[:len(人の列)] != list(人の列):
        raise 台帳の形の誤り(f"人ごと: 型の頭の列が {h[:len(人の列)]}（{list(人の列)} のはず）")
    氏名 = {str(k): v for k, v in (氏名 or {}).items()}
    状態 = {(str(a.get("支給月", "")), str(a.get("会社", "")), str(a.get("NO", ""))): str(a.get("状態", "")) for a in 人の状態}
    人たち: dict[tuple, dict] = {}
    for r in 集計の行:
        k = (str(r.get("支給月", "")), str(r.get("会社", "")), str(r.get("NO", "")))
        項目 = str(r.get("項目", ""))
        if 項目 not in 語:
            raise 台帳の形の誤り(f"人ごと: 型の列に無い月の語「{項目}」（芯/集計/形.py の 月の語 を足したら型の人ごとにも足し版を上げる）")
        d = 人たち.setdefault(k, {"_仮": False})
        if 項目 in d and 項目 == "年休を取った日":
            d[項目] = [*([d[項目]] if not isinstance(d[項目], list) else d[項目]), r.get("値")]
        else:
            d[項目] = r.get("値")
        d["_仮"] = d["_仮"] or str(r.get("状態", "")) == "仮"
    out = [list(h)]
    for k in sorted(人たち, key=lambda k: (k[0], k[1], (0, int(k[2]), k[2]) if k[2].isdigit() else (1, 0, k[2]))):
        d = 人たち[k]
        s = "仮" if 状態.get(k) == "仮" or d["_仮"] else "確認済"
        out.append([k[1], 支給月の字(k[0]), k[2], _字(氏名.get(k[2], "")), s] + [_字(d.get(c)) for c in 語])
    return out


def 台帳へ書く形(*, 勤怠=(), 勤怠の区間=(), 月の変動=(), 人ごとの支給控除=(), 集計の行=(), 人の状態=(),
            氏名: dict | None = None) -> dict[str, list[list[str]]]:
    """月次 の 台帳 の返す物: {タブの鍵: 表（1 行目が型の見出し）}。鍵は 勤怠・勤怠の区間・月の変動・人ごと（台帳）と
    人ごとの支給控除（マスタ）。
    氏名: {NO: 氏名}（社員のタブ）。人ごと・勤怠・勤怠の区間 の 氏名 の列へ。勤怠の 出勤の時刻・退勤の時刻 は 勤怠の区間 から作る。"""
    名 = {str(k): v for k, v in (氏名 or {}).items()}
    勤怠の区間 = list(勤怠の区間)
    出退 = 出勤と退勤(勤怠の区間)

    def 日の写し(r):
        出, 退 = 出退.get(_日の鍵(r), ("", ""))
        return {"氏名": _字(名.get(_字(r.get("NO")), "")), "出勤の時刻": 出, "退勤の時刻": 退}

    勤怠 = _写しを足す(勤怠, 日の写し)
    勤怠の区間 = _写しを足す(勤怠の区間, lambda r: {"氏名": _字(名.get(_字(r.get("NO")), ""))})
    return {"勤怠": _表("勤怠", 勤怠), "勤怠の区間": _表("勤怠の区間", 勤怠の区間), "月の変動": _表("月の変動", 月の変動),
            "人ごと": 人ごとの表(集計の行, 人の状態, 氏名), "人ごとの支給控除": _表("人ごとの支給控除", 人ごとの支給控除)}
