# -*- coding: utf-8 -*-
"""台帳「読んだままの勤怠」「確定した勤怠」の写し `休憩の合計`・`労働の合計` を、芯が数えた日の値で埋める・直す（型の版を上げない読み・どの版の会社にも毎回当てる）。

作り方は 1 か所＝芯/集計 の `日の休憩と労働`（集計する の返す `日の要約`）。月次 の台帳（月次/台帳の形.py）と同じ値を書く。
寄せはここで区間から数え直さない（前は 月次/台帳の形.py が休憩の区間だけを足していた＝休憩の表・長さの表で休憩を引く会社・
組の間の空きを休憩とする会社・始業前の打刻を所定の始業から数える会社で、休憩の合計が 0:00・労働の合計が出勤から退勤までの長さに
なり、芯の数え〔台帳「人ごと」の 総労働〕と食い違った）。

- 直しの鎖を当て終えた後の形（今の型）で、マスタ（会社・勤務の型・社員・変更の記録）と 00_事務所 の既定から段の解決で
  その支給月の決まりを解き、台帳の 勤怠（表 A）・勤怠の区間（表 B）を支給月ごとに 芯/集計.集計する に通す。
- 写しの 2 列は道具が書く列（手で書かない）＝芯の値と違えば直す（前の寄せが書いた違う値も直す）。芯が空を返す日
  （勤務の日でない・形の誤り・打刻抜け）は空にする（前の値は寄せの写しに在る＝持たない に数える）。
- 決まりの解けない月・社員に居ない人・法の線の引けない月は触らない（知らせ）。書く値はどれも h:mm（型の書き方）。
"""
import importlib.util as _imp
import sys
from pathlib import Path as _Path

import 当てる as 当

_根 = _Path(__file__).resolve().parents[2]
if str(_根) not in sys.path:
    sys.path.insert(0, str(_根))

_sp = _imp.spec_from_file_location("初期設定_段の解決_勤怠の要約", _根 / "初期設定" / "段の解決.py")
段 = _imp.module_from_spec(_sp)
_sp.loader.exec_module(段)

列たち = ("休憩の合計", "労働の合計")
決まりのタブ = ("会社", "勤務の型", "社員", "変更の記録")   # 日の休憩と労働に効く決まり（時間.* の段: 人・勤務の型・会社）


def _事務所(o) -> list:
    for f, tabs in o.シート.items():
        if f.endswith("事務所の設定") and tabs.get("既定"):
            return tabs["既定"]
    return []


def _月の要約(o, 支給月: str, 日たち: list[dict], 区間たち: list[dict], 知らせ: list) -> list[dict] | None:
    """その支給月の台帳の行を芯で数えた 日の要約（決まりが解けない・法の線が引けない月は None）。"""
    from 芯.集計 import 集計する
    from 芯.集計.法の線の橋 import 法の線を引く
    マスタ = {}
    for f in 当.ファイルたち(o, "2_マスタ"):
        for t in 決まりのタブ:
            if o.シート[f].get(t):
                マスタ.setdefault(t, o.シート[f][t])
    月 = 段.月にそろえる(支給月)
    if 月 is None:
        知らせ.append(f"支給月「{支給月}」が読めない（休憩の合計・労働の合計 は触らない）")
        return None
    try:
        r = 段.解く(月 + "支給", **マスタ, 事務所=_事務所(o))
    except Exception as e:  # 決まりが解けない月は写しを書かない（黙って既定の決まりで数えない）
        知らせ.append(f"{支給月}: 決まりが解けない（{e}）＝休憩の合計・労働の合計 は触らない")
        return None
    会社たち = {str(a.get("会社", "")) for a in 日たち}
    決まり = {k: v for k, v in r["決まり"].items() if str(k[0]) in 会社たち}
    居る = {(str(k[0]), str(k[1])) for k in 決まり}
    居ない = sorted({str(a.get("NO", "")) for a in 日たち if (str(a.get("会社", "")), str(a.get("NO", ""))) not in 居る})
    if 居ない:
        知らせ.append(f"{支給月}: 2_マスタ「社員」に居ない NO {'・'.join(居ない)}（休憩の合計・労働の合計 は触らない）")
    日たち = [a for a in 日たち if (str(a.get("会社", "")), str(a.get("NO", ""))) in 居る]
    区間たち = [b for b in 区間たち if (str(b.get("会社", "")), str(b.get("NO", ""))) in 居る]
    日付 = sorted(str(a.get("日付", "")).strip() for a in 日たち if str(a.get("日付", "")).strip())
    if not 日付:
        return None
    try:
        線 = 法の線を引く(日付[0], 日付[-1])
    except Exception as e:
        知らせ.append(f"{支給月}: 法の線が引けない（{e}）＝休憩の合計・労働の合計 は触らない")
        return None
    return 集計する(日たち, 区間たち, 決まり=決まり, 法の線=線)["日の要約"]


def 当てる(o, 記):
    形 = 当._台帳の形()
    for f, tabs in o.シート.items():
        if not f.startswith("台帳"):
            continue
        for 日のタブ, 区間のタブ in zip(形.日のタブ, 形.区間のタブ):   # 読んだままの勤怠・確定した勤怠（型の版 27）
            rows = tabs.get(日のタブ)
            if not rows or any(c not in rows[0] for c in 列たち) or (f, 日のタブ) in 記.待つタブ:
                continue
            h = [str(c) for c in rows[0]]
            区間 = 当._行の辞書(tabs.get(区間のタブ) or [])
            行たち = 当._行の辞書(rows)
            月たち: dict[str, list[int]] = {}
            for n, a in enumerate(行たち):
                if any(not 当.空か(v) for v in a.values()):
                    月たち.setdefault(str(a.get("支給月", "")).strip(), []).append(n)
            知らせ, 埋めた, 直した, 空にした = [], 0, 0, 0
            for 支給月, ns in sorted(月たち.items()):
                日たち = [行たち[n] for n in ns]
                区間たち = [b for b in 区間 if str(b.get("支給月", "")).strip() == 支給月]
                要約 = _月の要約(o, 支給月, 日たち, 区間たち, 知らせ)
                if 要約 is None:
                    continue
                居る = {(str(x["会社"]), str(x["NO"])) for x in 要約}
                写し = 形.写しの値(日のタブ, 日たち, None, 区間たち, 日の要約=要約)
                for n, a, w in zip(ns, 日たち, 写し):
                    if (str(a.get("会社", "")), str(a.get("NO", ""))) not in 居る:
                        continue
                    r = rows[n + 1]
                    for c in 列たち:
                        i = h.index(c)
                        前, 後 = str(r[i]).strip() if i < len(r) else "", w[c]
                        if 前 == 後:
                            continue
                        r[i] = 後
                        if not 前:
                            埋めた += 1
                            記.数["足した"] += 1
                        elif 後:
                            直した += 1
                        else:
                            空にした += 1
                            記.数["捨てた（直しの持たない）"] += 1
                        記.当てた.append((0, 0, "勤怠の要約を芯の数えで書く", f"{f}/{日のタブ}/{c}/{n + 2}行目"))
            if 空にした:
                記.持たない.append((f"{f}/{日のタブ}", 空にした, "休憩の合計・労働の合計 の写しを芯の数えにそろえた（芯が数えない日の前の写しは空に。前の値は寄せの写しに在る）"))
            if 埋めた or 直した or 空にした:
                知らせ.append(f"休憩の合計・労働の合計 を芯の数えで書いた（埋めた {埋めた}・直した {直した}・空にした {空にした}）")
            記.知らせ += [f"{f}/{日のタブ}: {x}" for x in 知らせ]
