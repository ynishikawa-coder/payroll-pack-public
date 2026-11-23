# -*- coding: utf-8 -*-
"""マスタ・台帳の 支給月・日付・時刻 の字を型の書き方へそろえる（型の版を上げない読み・どの版の会社にも毎回当てる）。

型の書き方（docs/設計/Drive の型.md §「書き方を 1 つに固定」）: 支給月 `YYYY.MM支給`・日付 `YYYY-MM-DD`・時刻 `h:mm`。
照らす列と形は見回りの赤（見回り.書き方を見る）と同じ 1 か所＝月次/台帳の形.py の `書き方のずれ`。
ずれた字のうち **字だけで同じ値に決まる物** を型の書き方の字へ置き換える（値の意味は変えない。行も列も動かさない）:
- 支給月: 段の解決が同じ支給月と読む字（初期設定/段の解決.py の `月にそろえる`＝`YYYY-MM`・`YYYY.MM`・`YYYY/MM`・`YYYY年M月`・
  `YYYY.MM支給（M月分）` など。芯は前からこの字を同じ支給月と読んでいる）→ `YYYY.MM支給`。月分の読み替え（締め日・支給日から
  勤務の月を出す）はしない＝字に支給月が無い物は直さない。
- 日付: `YYYY/M/D`・`YYYY.M.D`・`YYYY-M-D`・`YYYY年M月D日`（暦に在る日だけ）→ `YYYY-MM-DD`。
- 時刻: `h:mm:00`（秒が 0）・全角 → `h:mm`（時の頭の 0 は落とす）。秒が 0 でない字は直さない（分を丸めると値が変わる）。
決まらない字は「寄せられない物」（種類 書き方の合わない値）として問いに残す。答え `値:<型の書き方の字>`（その形でなければ問いのまま）。
1 社は全部か無し（寄せの決まり）＝1 つでも残れば何も書かない。直した所は `知らせ` に列ごとの数で出す。値の数は変わらない（値の保ちはそのまま）。
"""
import datetime as dt
import importlib.util as _imp
import re
import unicodedata
from pathlib import Path as _Path

import 当てる as 当

_sp = _imp.spec_from_file_location("初期設定_段の解決_書き方", _Path(__file__).resolve().parents[2] / "初期設定" / "段の解決.py")
段 = _imp.module_from_spec(_sp)
_sp.loader.exec_module(段)

照らすファイルの頭 = ("2_マスタ", "台帳")   # 見回り.書き方を見る と同じ
種類 = "書き方の合わない値"


def _字(v) -> str:
    return "".join(unicodedata.normalize("NFKC", "" if v is None else str(v)).split())


def 支給月の字(v) -> str | None:
    """支給月の字 → 型の書き方 `YYYY.MM支給`（字は正本 芯/支給月の字.py が組む・段の解決 と同じ読み）。読めなければ None。"""
    return 段.支給月の字.そろえる(v, "殻")


def 日付の字(v) -> str | None:
    m = re.fullmatch(r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", _字(v))
    if not m:
        return None
    try:
        return dt.date(int(m[1]), int(m[2]), int(m[3])).isoformat()
    except ValueError:
        return None


def 時刻の字(v) -> str | None:
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::00)?", _字(v))
    if not m or int(m[2]) >= 60:
        return None
    return f"{int(m[1])}:{m[2]}"


def 直す字(列: str, v) -> str | None:
    """型の書き方の字（直せなければ None）。照らす列でなければ None。"""
    形 = 当.台帳の形()
    if 列 == "支給月":
        return 支給月の字(v)
    if 列 in 形.日付の列:
        return 日付の字(v)
    if 列 in 形.時刻の列:
        return 時刻の字(v)
    return None


def _合う(列: str, w: str, f: str, t: str) -> bool:
    return not 当.台帳の形().書き方のずれ(t, [列], [w])


def 当てる(o, 記):
    形 = 当.台帳の形()
    列たち = ("支給月", *形.日付の列, *形.時刻の列)
    直した: dict = {}
    for f, tabs in o.シート.items():
        if not f.startswith(照らすファイルの頭):
            continue
        for t, rows in tabs.items():
            if not rows or t.startswith(当.旧の頭) or (f, t) in 記.待つタブ:   # 待つタブ＝消す問いへ回したタブ（畳んだタブも）
                continue
            h = [str(x) for x in rows[0]]
            for i, c in enumerate(h):
                if c not in 列たち:
                    continue
                for r in range(1, len(rows)):
                    v = str(rows[r][i]).strip() if i < len(rows[r]) else ""
                    if not v or _合う(c, v, f, t):
                        continue
                    鍵 = f"{f}/{t}/書き方:{c}/{r + 1}行目"
                    w = 直す字(c, v)
                    ans = str(o.人の答え.get(鍵, "")).strip()
                    if w is None and ans.startswith("値:") and _合う(c, ans[2:].strip(), f, t):
                        w = ans[2:].strip()
                    if w is None or not _合う(c, w, f, t):
                        書き方 = "YYYY.MM支給" if c == "支給月" else "YYYY-MM-DD" if c in 形.日付の列 else "h:mm"
                        記.出せない(鍵, 種類, f"{f}/{t}", f"{r + 1} 行目の {c}「{v}」が型の書き方（{書き方}）でなく、字だけでは同じ値の字に決まらない",
                                  [f"値:<{書き方}>"], "前の値は変えない。人が同じ値を型の書き方で答える（答えが型の書き方でなければ問いのまま）")
                        continue
                    rows[r][i] = w
                    記.当てた.append((0, 0, "書き方をそろえる", f"{f}/{t}/{c}/{r + 1}行目"))
                    直した.setdefault((f, t, c), {}).setdefault((v, w), 0)
                    直した[(f, t, c)][(v, w)] += 1
    for (f, t, c), d in 直した.items():
        並び = "・".join(f"「{v}」→「{w}」{n}" for (v, w), n in sorted(d.items()))
        記.知らせ.append(f"{f}/{t}: {c} の字を型の書き方へそろえた（{sum(d.values())} か所・{並び}）。値の意味は変えていない")
