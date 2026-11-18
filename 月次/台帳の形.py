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
- 台帳「勤怠」の 休憩の合計・労働の合計 は、芯が数えた日の値（芯/集計 の `日の要約`＝`日の休憩と労働` の 1 か所）を h:mm に書くだけ。
  ここで区間から数え直さない（休憩の表・長さの表・組の間の空き・始業前の打刻など芯の数え方を 2 か所に持たない）。
  日の要約が渡らない時（寄せの直しの途中など）はこの 2 列を書かない（空のまま）。
"""
from __future__ import annotations

import importlib.util
import re
import sys
from datetime import date as _date
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


曜日の字 = "月火水木金土日"


def 曜日(日付) -> str:
    """YYYY-MM-DD → 月〜日の 1 字（読めない日付は空）。"""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", _字(日付).strip())
    if not m:
        return ""
    try:
        return 曜日の字[_date(int(m.group(1)), int(m.group(2)), int(m.group(3))).weekday()]
    except ValueError:
        return ""


def 長さの字(分: int | None) -> str:
    """分 → h:mm（人が読む要約の列だけの書き方。計算に使う列は整数の分のまま）。"""
    return "" if 分 is None else f"{分 // 60}:{分 % 60:02d}"


def 日の要約の表(日の要約) -> dict[tuple, tuple[int | None, int | None]]:
    """芯/集計 の `日の要約`（[{支給月, 会社, NO, 日付, 休憩, 労働}]）→ {(支給月, 会社, NO, 日付): (休憩の分, 労働の分)}（台帳の行の鍵で引く）。"""
    return {_日の鍵(x): (x.get("休憩"), x.get("労働")) for x in 日の要約 or ()}


def _写しを足す(鍵: str, 行たち, 写し) -> list[dict]:
    """入口の行に、人が見るための写しの列（写し(r) の dict）を足す。

    行に値が在って道具の値と違えば止める（氏名がマスタと違う・要約が区間と食い違う＝どちらが正か分からない）。
    道具の値が空の列（区間が無い・社員のタブで引けない）は、行の値を残す。"""
    out = []
    for r in 行たち:
        足す = {}
        for c, v in 写し(r).items():
            前 = _字(r.get(c)).strip()
            if not 前:
                足す[c] = v
            elif v and 前 != v:
                raise 台帳の形の誤り(f"{鍵}: NO {_字(r.get('NO'))} {_字(r.get('日付'))} の {c} が「{前}」（道具の値は「{v}」＝"
                                 f"{'マスタ「社員」の氏名' if c == '氏名' else '区間から作った値'}）。入口の行か区間・マスタを直す")
        out.append({**r, **足す})
    return out


日付の形 = re.compile(r"\d{4}-\d{2}-\d{2}")
時刻の形 = re.compile(r"\d{1,2}:\d{2}")
支給月の形 = re.compile(r"\d{4}\.\d{2}支給")
# 書き方を 1 つに固定する列（型の列の意味の書き方）。台帳へ書く前に照らし、違えば止める
日付の列 = ("日付", "振替の相手の日", "代休の相手の日")
時刻の列 = ("出勤の時刻", "退勤の時刻", "所定の始業", "所定の終業", "始め", "終わり", "休憩の合計", "労働の合計")


def 書き方のずれ(鍵: str, h: list[str], 行: list[str]) -> list[str]:
    """型の書き方（支給月 YYYY.MM支給・日付 YYYY-MM-DD・時刻と要約の長さ h:mm）に合わない値（空は見ない）。"""
    out = []
    for c, v in zip(h, 行):
        v = v.strip()
        if not v:
            continue
        if c == "支給月" and not 支給月の形.fullmatch(v):
            out.append(f"{c}「{v}」（YYYY.MM支給）")
        elif c in 日付の列 and not 日付の形.fullmatch(v):
            out.append(f"{c}「{v}」（YYYY-MM-DD）")
        elif c in 時刻の列 and not 時刻の形.fullmatch(v):
            out.append(f"{c}「{v}」（h:mm）")
    return out


def _表(鍵: str, 行たち) -> list[list[str]]:
    h = 見出し(鍵)
    out = [list(h)]
    for r in 行たち:
        外 = sorted(k for k, v in r.items() if k not in h and not str(k).startswith("_") and _字(v).strip())
        if 外:
            raise 台帳の形の誤り(f"{鍵}: 型の列に無い値 {外}（型を直すか、入口の行を型の列へ）")
        行 = [支給月の字(r.get(c)) if c == "支給月" else _字(r.get(c)) for c in h]
        ずれ = 書き方のずれ(鍵, h, 行)
        if ずれ:
            raise 台帳の形の誤り(f"{鍵}: NO {_字(r.get('NO'))} {_字(r.get('日付'))} の書き方が型と違う {ずれ}")
        if "要確認の理由" in h and _字(r.get("読み取りの確かめ")).strip() == "要確認" and not _字(r.get("要確認の理由")).strip():
            raise 台帳の形の誤り(f"{鍵}: NO {_字(r.get('NO'))} {_字(r.get('日付'))} は 要確認 なのに 要確認の理由 が空（入口が理由を 1 行で書く）")
        out.append(行)
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


def _日の写し(r, 名: dict, 出退: dict, 要約: dict | None) -> dict:
    """台帳「勤怠」の 1 行の写しの列（氏名・曜日・出勤の時刻・退勤の時刻・休憩の合計・労働の合計）。
    要約: 日の要約の表（芯が数えた値）。None なら 休憩の合計・労働の合計 は出さない（書かない）。芯が出さない日は空。"""
    k = _日の鍵(r)
    出, 退 = 出退.get(k, ("", ""))
    out = {"氏名": _字(名.get(_字(r.get("NO")), "")), "曜日": 曜日(r.get("日付")), "出勤の時刻": 出, "退勤の時刻": 退}
    if 要約 is not None:
        休, 労 = 要約.get(k, (None, None))
        out |= {"休憩の合計": 長さの字(休), "労働の合計": 長さの字(労)}
    return out


def 台帳へ書く形(*, 勤怠=(), 勤怠の区間=(), 月の変動=(), 人ごとの支給控除=(), 集計の行=(), 人の状態=(),
            氏名: dict | None = None, 日の要約=None) -> dict[str, list[list[str]]]:
    """月次 の 台帳 の返す物: {タブの鍵: 表（1 行目が型の見出し）}。鍵は 勤怠・勤怠の区間・月の変動・人ごと（台帳）と
    人ごとの支給控除（マスタ）。
    氏名: {NO: 氏名}（社員のタブ）。氏名 の列の在る全タブへ（行に違う氏名が在れば止める）。勤怠の 曜日 は日付から、
    出勤の時刻・退勤の時刻 は 勤怠の区間 から、休憩の合計・労働の合計 は 日の要約（芯/集計 の返す `日の要約`＝芯が数えた日の値）
    から作る（行に違う値が在れば止める。日の要約を渡さなければこの 2 列は書かない）。"""
    名 = {str(k): v for k, v in (氏名 or {}).items()}
    勤怠の区間 = list(勤怠の区間)
    出退 = 出勤と退勤(勤怠の区間)
    要約 = None if 日の要約 is None else 日の要約の表(日の要約)

    def 人の写し(r):
        return {"氏名": _字(名.get(_字(r.get("NO")), ""))}

    勤怠 = _写しを足す("勤怠", 勤怠, lambda r: _日の写し(r, 名, 出退, 要約))
    勤怠の区間 = _写しを足す("勤怠の区間", 勤怠の区間, 人の写し)
    月の変動 = _写しを足す("月の変動", 月の変動, 人の写し)
    人ごとの支給控除 = _写しを足す("人ごとの支給控除", 人ごとの支給控除, 人の写し)
    return {"勤怠": _表("勤怠", 勤怠), "勤怠の区間": _表("勤怠の区間", 勤怠の区間), "月の変動": _表("月の変動", 月の変動),
            "人ごと": 人ごとの表(集計の行, 人の状態, 氏名), "人ごとの支給控除": _表("人ごとの支給控除", 人ごとの支給控除)}


def 写しの値(タブ: str, 行たち: list[dict], 氏名: dict | None = None, 区間たち=(), 日の要約=None) -> list[dict]:
    """既に在るタブの行（寄せの直しが列を足した後）に書く写しの値（行ごとの {列: 値}）。台帳へ書く形 と同じ作り方の 1 か所
    （寄せは前の月の行も埋めるので、ここは止めずに値だけ返す）。日の要約（芯/集計 の返す物）を渡さなければ
    休憩の合計・労働の合計 は返さない（寄せは直しを当て終えてから 道具/寄せ/勤怠の要約.py が芯で数えて埋める）。"""
    名 = {str(k): v for k, v in (氏名 or {}).items()}
    if タブ != "勤怠":
        return [{"氏名": _字(名.get(_字(r.get("NO")), ""))} for r in 行たち]
    出退 = 出勤と退勤(区間たち)
    要約 = None if 日の要約 is None else 日の要約の表(日の要約)
    return [_日の写し(r, 名, 出退, 要約) for r in 行たち]


def 氏名を埋める(鍵: str, 行たち, 氏名: dict | None) -> list[dict]:
    """月次 の返す台帳に無いタブ（台帳「委託」・マスタ「変更の記録」など 殻 が足す行）の 氏名 の列を、殻が書く前に埋める口。

    氏名: {NO: 氏名}（マスタ「社員」）。空の欄だけ埋め、行に違う氏名が在れば止める（台帳へ書く形 と同じ決まり）。
    NO が空の行（変更の記録の会社の行）・社員のタブで引けない NO は空のまま。"""
    名 = {str(k): v for k, v in (氏名 or {}).items()}
    return _写しを足す(鍵, 行たち, lambda r: {"氏名": _字(名.get(_字(r.get("NO")), ""))})
