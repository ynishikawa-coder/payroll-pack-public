"""給与ソフトごとの読み口（確かめと仮.md §2）。給与ソフトの計算結果を人×項目の縦の行へ直すだけで、比べない。

欄と項目の対応は書き口と同じ 1 つ（受ける欄）を逆に引く。出所は給与ソフトの出力の file の名。
人の行があり欄もある空のセルは 0 と読む（給与ソフトは 0 を空で出す）。人の行が無い人は読まない（突き合わせで「片方だけ」）。
読めない物（知らない欄・鍵の無い行・数でない値）は黙って捨てず `要確認` に返す。
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from .形 import 給与ソフトの形, 字を数に, 対応にする, 形を組む
from .行 import 確定, 行, 支給月を確かめる


@dataclass(frozen=True)
class 読んだ物:
    行たち: tuple[行, ...]
    要確認: tuple[str, ...]


def 読む(中身: bytes | str, file名: str, 会社: str, 支給月: str, 欄の対応, 形: 給与ソフトの形,
       時間の書き方: str | None = None) -> 読んだ物:
    支給月を確かめる(支給月)
    形 = 形を組む(形)  # 殻が渡した形（dict でもよい）。名・鍵の欄・文字コードが無ければ止まる
    if isinstance(中身, bytes):
        if not 形.文字コード:
            raise ValueError(f"{形.名}: 文字コードが無い")
        中身 = 中身.decode(形.文字コード)
    中身 = 中身.lstrip("﻿")
    表 = [r for r in csv.reader(io.StringIO(中身, newline=""), delimiter=形.区切り) if any(c.strip() for c in r)]
    if 形.向き == "縦":   # 人が列・欄が行 → 横へ直す
        w = max((len(r) for r in 表), default=0)
        表 = [list(c) for c in zip(*[r + [""] * (w - len(r)) for r in 表])]
    要確認: list[str] = []
    if not 表:
        return 読んだ物((), (f"{file名}: 中身が空",))
    頭 = [c.strip() for c in 表[0]]
    if 形.鍵の欄 not in 頭:
        raise ValueError(f"{file名}: 鍵の欄「{形.鍵の欄}」が無い（見出し: {'・'.join(頭)}）")
    対応 = {x.欄: x for x in 対応にする(欄の対応) if x.受ける}
    知る = {形.鍵の欄, 形.氏名の欄, *形.後ろの欄} - {None}
    for c in 頭:
        if c and c not in 対応 and c not in 知る:
            要確認.append(f"{file名}: 対応に無い欄「{c}」（読んでいない）")
    for c in 対応:
        if c not in 頭:
            要確認.append(f"{file名}: 対応の欄「{c}」が出力に無い")
    i鍵 = 頭.index(形.鍵の欄)
    out: list[行] = []
    見た = set()
    for n, r in enumerate(表[1:], start=2):
        r = r + [""] * (len(頭) - len(r))
        no = r[i鍵].strip()
        if not no:
            要確認.append(f"{file名}: {n} 行目に鍵（{形.鍵の欄}）が無い（読んでいない）")
            continue
        if no in 見た:
            要確認.append(f"{file名}: {no} が 2 行ある（後の行は読んでいない）")
            continue
        見た.add(no)
        for i, c in enumerate(頭):
            x = 対応.get(c)
            if x is None:
                continue
            try:
                v = 字を数に(r[i], x.形, 時間の書き方)
            except ValueError as e:
                要確認.append(f"{file名}: {no} {c}: {e}")
                continue
            if v is None:   # 人の行があり欄もある空のセル＝給与ソフトが 0 を空で出した
                v = 字を数に("0", x.形, 時間の書き方)
            out.append(行(支給月=支給月, 会社=str(会社), NO=no, 項目=x.項目, 値=v, 出所=file名, 状態=確定))
    return 読んだ物(tuple(out), tuple(要確認))
