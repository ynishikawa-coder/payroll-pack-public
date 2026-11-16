"""月次 が返す「台帳」を、型（初期設定/型.json）の台帳のタブの形にする 1 か所。

殻は返った表をそのまま台帳・マスタのタブへ書く（見出しの行が型と同じかを照らしてから 2 行目より下を足す）。
形を作るのはここだけ＝列の名と並びは型の口（初期設定/型の口.py）から引き、ここに列を写さない。

- 台帳「人ごと」: 芯/集計 の行（1 人×1 項目の縦）を 1 人 1 行の横へ。列は型の「人ごと」（会社・支給月・NO・氏名・状態・月の語）。
  型に無い月の語が来たら止める（月の語を足したら型の版を上げる＝直しを添える）。黙って落とさない。
- 台帳「勤怠」「勤怠の区間」「月の変動」・マスタ「人ごとの支給控除」: 入口の行（列名の dict）を型の列の並びへ。
  型に無い列に値が在れば止める（黙って落とさない）。`_` で始まる鍵は中の印＝書かない。
- 支給月は型の書き方（YYYY.MM支給）にそろえる（入口・芯は YYYY-MM で持つ）。
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
    人ごとの支給控除（マスタ）。"""
    return {"勤怠": _表("勤怠", 勤怠), "勤怠の区間": _表("勤怠の区間", 勤怠の区間), "月の変動": _表("月の変動", 月の変動),
            "人ごと": 人ごとの表(集計の行, 人の状態, 氏名), "人ごとの支給控除": _表("人ごとの支給控除", 人ごとの支給控除)}
