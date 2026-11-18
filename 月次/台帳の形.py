"""月次 が返す「台帳」を、型（初期設定/型.json）の台帳のタブの形にする 1 か所。

殻は返った表をそのまま台帳・マスタのタブへ書く（見出しの行が型と同じかを照らしてから 2 行目より下を足す）。
形を作るのはここだけ＝列の名と並びは型の口（初期設定/型の口.py）から引き、ここに列を写さない。

- 台帳「人ごと」: 芯/集計 の行（1 人×1 項目の縦）を 1 人 1 行の横へ。列は型の「人ごと」（会社・支給月・NO・氏名・状態・月の語）。
  型に無い月の語が来たら止める（月の語を足したら型の版を上げる＝直しを添える）。黙って落とさない。
- 台帳の日のタブ（読んだままの勤怠・確定した勤怠）と区間のタブ・マスタ「人ごとの支給控除」: 表 A・B の行（列名の dict）を型の列の並びへ（勤怠の表たち）。確定した勤怠を芯の表 A・B へ読み戻すのも ここ 1 か所（確定した勤怠を読む）。
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


台帳 = "台帳_<支給年>"
マスタ = "2_マスタ"
# 返す物の鍵 → (型のシート, タブ)
タブたち = {"読んだままの勤怠": (台帳, "読んだままの勤怠"), "読んだままの勤怠の区間": (台帳, "読んだままの勤怠の区間"),
         "確定した勤怠": (台帳, "確定した勤怠"), "確定した勤怠の区間": (台帳, "確定した勤怠の区間"),
         "その月だけの指示": (台帳, "その月だけの指示"), "人ごとの月の数字": (台帳, "人ごとの月の数字"),
         "締めの記録": (台帳, "締めの記録"), "人ごとの支給控除": (マスタ, "人ごとの支給控除")}
# 日のタブ（読んだまま・確定）と区間のタブ。確定は末尾に 直した訳 の列を持つ
日のタブ = ("読んだままの勤怠", "確定した勤怠")
区間のタブ = ("読んだままの勤怠の区間", "確定した勤怠の区間")
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
    h = 見出し("人ごとの月の数字")
    語 = h[len(人の列):]
    if h[:len(人の列)] != list(人の列):
        raise 台帳の形の誤り(f"人ごとの月の数字: 型の頭の列が {h[:len(人の列)]}（{list(人の列)} のはず）")
    氏名 = {str(k): v for k, v in (氏名 or {}).items()}
    状態 = {(str(a.get("支給月", "")), str(a.get("会社", "")), str(a.get("NO", ""))): str(a.get("状態", "")) for a in 人の状態}
    人たち: dict[tuple, dict] = {}
    for r in 集計の行:
        k = (str(r.get("支給月", "")), str(r.get("会社", "")), str(r.get("NO", "")))
        項目 = str(r.get("項目", ""))
        if 項目 not in 語:
            raise 台帳の形の誤り(f"人ごとの月の数字: 型の列に無い月の語「{項目}」（芯/集計/形.py の 月の語 を足したら型の人ごとの月の数字にも足し版を上げる）")
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


# 日のタブの写しの列（人が見るための写し・芯は読まない）
写しの列 = ("氏名", "曜日", "出勤の時刻", "退勤の時刻", "休憩の合計", "労働の合計")
分の列 = ("休暇の時間", "所定時間", "遅延証明の分", "申請の残業", "時刻の無い休憩", "時刻の無い労働時間")
直した訳の列 = "直した訳"
直した訳の形 = re.compile(r"(決まり|問い):\S.*")


def _確定のタブへ(鍵: str, 行たち) -> list[dict]:
    """確定した勤怠へ書く行: 要確認の行は書かない（止める）。読み取りの確かめ が空なら 確認済（締めた＝確かめ終えた日）。"""
    out = []
    for r in 行たち:
        if _字(r.get("読み取りの確かめ")).strip() == "要確認":
            raise 台帳の形の誤り(f"{鍵}: NO {_字(r.get('NO'))} {_字(r.get('日付'))} は 要確認 のまま（確かめた日だけを確定した勤怠へ書く）")
        out.append({**r, "読み取りの確かめ": "確認済"})
    return out


def 勤怠の表たち(*, 確定: bool, 勤怠=(), 勤怠の区間=(), 氏名: dict | None = None, 日の要約=None) -> dict[str, list[list[str]]]:
    """表 A・B の行 → 年の台帳の日のタブと区間のタブの表（1 行目が型の見出し）。確定＝False なら 読んだままの勤怠（1 次）、
    True なら 確定した勤怠（2 次・行の 直した訳 を書く＝1 次と違う行だけ `決まり:<見出し>` か `問い:<問いの番号>`）。
    氏名・曜日・出勤の時刻・退勤の時刻 は写し（ここで埋める）。休憩の合計・労働の合計 は 日の要約（芯/集計 の返す物）を渡した時だけ。
    確定した勤怠には 要確認 の行を書けない（止める）。"""
    日, 区 = (日のタブ[1], 区間のタブ[1]) if 確定 else (日のタブ[0], 区間のタブ[0])
    名 = {str(k): v for k, v in (氏名 or {}).items()}
    勤怠の区間 = list(勤怠の区間)
    出退 = 出勤と退勤(勤怠の区間)
    要約 = None if 日の要約 is None else 日の要約の表(日の要約)
    for r in [*勤怠, *勤怠の区間]:
        訳 = _字(r.get(直した訳の列)).strip()
        if 訳 and not 直した訳の形.fullmatch(訳):
            raise 台帳の形の誤り(f"直した訳「{訳}」は `決まり:<見出し>` か `問い:<問いの番号>`")
    行 = _写しを足す(日, _確定のタブへ(日, 勤怠) if 確定 else list(勤怠), lambda r: _日の写し(r, 名, 出退, 要約))
    区間 = _写しを足す(区, 勤怠の区間, lambda r: {"氏名": _字(名.get(_字(r.get("NO")), ""))})
    return {日: _表(日, 行), 区: _表(区, 区間)}


def 台帳へ書く形(*, 集計の行=(), 人の状態=(), 氏名: dict | None = None) -> dict[str, list[list[str]]]:
    """月次.月を回す の 台帳 の返す物: {"人ごとの月の数字": 表（1 行目が型の見出し・1 人 1 行）}。
    勤怠は書かない（月を回す は確定した勤怠を読むだけ。日のタブを作るのは 勤怠の表たち）。"""
    return {"人ごとの月の数字": 人ごとの表(集計の行, 人の状態, 氏名)}


def 行たち(表) -> list[dict]:
    """タブの値（列名 → 値 の dict の並び、か 1 行目が見出しの 2 次元の並び＝get_values の形）→ dict の並び。"""
    xs = list(表 or ())
    if xs and isinstance(xs[0], (list, tuple)):
        h = [str(c).strip() for c in xs[0]]
        return [{c: (r[i] if i < len(r) else "") for i, c in enumerate(h)} for r in xs[1:]]
    return [dict(r) for r in xs]


def _見出しを照らす(鍵: str, 表) -> None:
    xs = list(表 or ())
    if xs and isinstance(xs[0], (list, tuple)):
        h = [str(c).strip() for c in xs[0]]
        if h != 見出し(鍵):
            raise 台帳の形の誤り(f"{鍵}: 見出しが型と違う（{h} ≠ {見出し(鍵)}）。型の版をそろえてから読む")


def _確定の行(鍵: str, r: dict, 整数の列: tuple) -> dict:
    h = 見出し(鍵)
    外 = sorted(k for k, v in r.items() if k not in h and not str(k).startswith("_") and _字(v).strip())
    if 外:
        raise 台帳の形の誤り(f"{鍵}: 型の列に無い値 {外}")
    訳 = _字(r.get(直した訳の列)).strip()
    if 訳 and not 直した訳の形.fullmatch(訳):
        raise 台帳の形の誤り(f"{鍵}: NO {_字(r.get('NO'))} {_字(r.get('日付'))} の 直した訳「{訳}」は `決まり:<見出し>` か `問い:<問いの番号>`")
    out = {}
    for c in h:
        v = _字(r.get(c)).strip()
        if not v or c == 直した訳の列 or c in 写しの列:
            continue
        if c == "支給月":
            m = re.fullmatch(r"(\d{4})\.(\d{2})支給|(\d{4})-(\d{2})", v)
            if not m:
                raise 台帳の形の誤り(f"{鍵}: NO {_字(r.get('NO'))} の 支給月「{v}」（YYYY.MM支給）")
            v = f"{m.group(1) or m.group(3)}-{m.group(2) or m.group(4)}"
        elif c in 整数の列:
            if not re.fullmatch(r"\d+", v):
                raise 台帳の形の誤り(f"{鍵}: NO {_字(r.get('NO'))} {_字(r.get('日付'))} の {c}「{v}」は整数（分・番号）")
            out[c] = int(v)
            continue
        out[c] = v
    for c in ("会社", "支給月", "NO", "日付"):
        if not out.get(c):
            raise 台帳の形の誤り(f"{鍵}: {c} が空の行（{r}）")
    return out


def 確定した勤怠を読む(勤怠, 勤怠の区間=()) -> tuple[list[dict], list[dict]]:
    """年の台帳の 確定した勤怠・確定した勤怠の区間（get_values の形か dict の並び）→ 芯へ渡す表 A・表 B（勤怠の形.md §1・§2）。

    月を回す が勤怠として読むのはここを通った行だけ（原本は読まない）。写しの列（氏名・曜日・出勤と退勤の時刻・休憩と労働の合計）
    と 直した訳 は芯へ渡さない（計算は表 A の事実と区間を読む）。確定した勤怠は締めた＝確かめ終えた日なので、
    読み取りの確かめ は 確認済（空も・それ以外の字は止める）。見出しが型と違う・型に無い列に値・支給月や分が読めない・
    直した訳の書き方が違う 行は止める（黙って読み替えない）。"""
    _見出しを照らす("確定した勤怠", 勤怠)
    _見出しを照らす("確定した勤怠の区間", 勤怠の区間)
    表A = []
    for r in 行たち(勤怠):
        a = _確定の行("確定した勤怠", r, 分の列)
        if a.get("読み取りの確かめ", "確認済") != "確認済":
            raise 台帳の形の誤り(f"確定した勤怠: NO {a['NO']} {a['日付']} の 読み取りの確かめ が「{a['読み取りの確かめ']}」（確定した勤怠は確かめ終えた日だけ）")
        表A.append({**a, "読み取りの確かめ": "確認済"})
    表B = [_確定の行("確定した勤怠の区間", r, ("区間の番号",)) for r in 行たち(勤怠の区間)]
    return 表A, 表B


def 写しの値(タブ: str, 行たち: list[dict], 氏名: dict | None = None, 区間たち=(), 日の要約=None) -> list[dict]:
    """既に在るタブの行（寄せの直しが列を足した後）に書く写しの値（行ごとの {列: 値}）。勤怠の表たち と同じ作り方の 1 か所
    （寄せは前の月の行も埋めるので、ここは止めずに値だけ返す）。日の要約（芯/集計 の返す物）を渡さなければ
    休憩の合計・労働の合計 は返さない（寄せは直しを当て終えてから 道具/寄せ/勤怠の要約.py が芯で数えて埋める）。"""
    名 = {str(k): v for k, v in (氏名 or {}).items()}
    if タブ not in (*日のタブ, "勤怠"):
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
