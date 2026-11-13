"""答えの file（xlsx・CSV・zip）を、タブごとの字の表にする。開発の間だけの道具（`道具/答え合わせ/`）。

- 形は名前でなく中身で見る（PK＋xl/workbook.xml＝xlsx・ほかの PK＝zip・ほかは字の表＝CSV か TSV）。
- xlsx は zip の中の XML を標準の xml.etree で読む（読み仮名 rPh は捨てる・時刻の書式のセルは `時:分` の字にする）。
- zip は中を開く（UTF-8 の印の無い名は cp932 に直す）。PDF は読まない（要確認に出す。xlsx か CSV で出し直してもらう）。
- 読めない物は黙って捨てず `要確認` に返す。Drive は開かない（開発の窓が落とした file の中身を受ける）。
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


@dataclass(frozen=True)
class 表:
    名: str                         # `<file の名>#<タブの名>`（CSV はタブの名なし）。読んだ行の出所になる
    升: tuple[tuple[str, ...], ...]  # 行 × 列 の字


def 表にする(file名: str, 中身: bytes, 文字コード: str = "utf-8-sig", 要確認: list | None = None) -> list[表]:
    """1 つの file の中身 → 表の並び。要確認（list）を渡せば読めない物の知らせを足す。"""
    要確認 = 要確認 if 要確認 is not None else []
    return _開く(file名, 中身, 文字コード, 要確認, 0)


def _形(中身: bytes) -> str:
    if 中身[:4] == b"%PDF":
        return "pdf"
    if 中身[:2] == b"PK":
        try:
            名たち = zipfile.ZipFile(io.BytesIO(中身)).namelist()
        except zipfile.BadZipFile:
            return "壊れた zip"
        return "xlsx" if "xl/workbook.xml" in 名たち else "zip"
    return "字"


def _開く(名, 中身, 文字コード, 要確認, 深さ) -> list[表]:
    f = _形(中身)
    if f == "pdf":
        要確認.append(f"{名}: PDF は読まない（給与ソフトから xlsx か CSV で出し直す）")
        return []
    if f == "壊れた zip":
        要確認.append(f"{名}: zip として開けない（読んでいない）")
        return []
    if f == "xlsx":
        return _xlsx(名, 中身, 要確認)
    if f == "zip":
        if 深さ >= 2:
            要確認.append(f"{名}: zip の中の zip が深すぎる（読んでいない）")
            return []
        out = []
        z = zipfile.ZipFile(io.BytesIO(中身))
        for info in z.infolist():
            if info.is_dir() or "__MACOSX" in info.filename:
                continue
            n = _zipの名(info)
            if n.rsplit("/", 1)[-1].startswith("."):
                continue
            out += _開く(f"{名}/{n}", z.read(info), 文字コード, 要確認, 深さ + 1)
        return out
    try:
        字 = 中身.decode(文字コード)
    except UnicodeDecodeError:
        要確認.append(f"{名}: 文字コード {文字コード} で読めない（--文字コード を渡す）")
        return []
    return [_字の表(名, 字)]


def _zipの名(info) -> str:
    n = info.filename
    if not info.flag_bits & 0x800:   # UTF-8 の印が無い＝Python は cp437 で読む＝元は cp932
        try:
            n = n.encode("cp437").decode("cp932")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return n


def _字の表(名: str, 字: str) -> 表:
    字 = 字.lstrip("﻿")
    頭 = 字.split("\n", 1)[0]
    区切り = "\t" if 頭.count("\t") > 頭.count(",") else ","
    rows = [tuple(c.strip() for c in r) for r in csv.reader(io.StringIO(字, newline=""), delimiter=区切り)]
    return 表(名, tuple(rows))


# ---- xlsx ----

def _列の番号(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def _時刻の書式(z) -> set[int]:
    """時刻の書式（[h]:mm など）のセルの書式の番号。値は日の小数。"""
    try:
        st = ET.fromstring(z.read("xl/styles.xml"))
    except KeyError:
        return set()
    書式 = {int(f.get("numFmtId")): f.get("formatCode", "") for f in st.iterfind("m:numFmts/m:numFmt", _NS)}

    def 時刻か(i: int) -> bool:
        if i in (18, 19, 20, 21, 45, 46, 47):
            return True
        c = re.sub(r'"[^"]*"|\[\$[^]]*\]', "", 書式.get(i, "")).lower()
        return bool(c) and "h" in c and not re.search(r"[yd]", c)

    return {n for n, x in enumerate(st.iterfind("m:cellXfs/m:xf", _NS)) if 時刻か(int(x.get("numFmtId", 0)))}


def _字(si) -> str:
    """共有文字列・inlineStr の字（読み仮名 rPh は捨てる）。"""
    T, R = "{%s}t" % _NS["m"], "{%s}r" % _NS["m"]
    out = []
    for c in si:
        if c.tag == T:
            out.append(c.text or "")
        elif c.tag == R:
            out += [x.text or "" for x in c.iterfind("m:t", _NS)]
    return "".join(out)


def _数の字(v: str) -> str:
    """xlsx の数の字（浮動小数のくずを 6 桁で丸める）。"""
    try:
        d = Decimal(v)
    except InvalidOperation:
        return v
    if d != d.to_integral_value() and len(v.split(".", 1)[-1]) > 6:
        d = d.quantize(Decimal("0.000001"))
    d = d.normalize()
    return str(int(d)) if d == d.to_integral_value() else format(d, "f")


def _xlsx(名: str, 中身: bytes, 要確認: list) -> list[表]:
    z = zipfile.ZipFile(io.BytesIO(中身))
    共有 = []
    if "xl/sharedStrings.xml" in z.namelist():
        共有 = [_字(si) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iterfind("m:si", _NS)]
    時刻 = _時刻の書式(z)
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    out = []
    for sh in ET.fromstring(z.read("xl/workbook.xml")).iterfind("m:sheets/m:sheet", _NS):
        tgt = rels[sh.get(_REL)].lstrip("/")
        path = tgt if tgt.startswith("xl/") else "xl/" + tgt
        タブ = sh.get("name")
        升: dict[tuple[int, int], str] = {}
        for c in ET.fromstring(z.read(path)).iter("{%s}c" % _NS["m"]):
            t, v = c.get("t"), c.find("m:v", _NS)
            if t == "s":
                val = 共有[int(v.text)] if v is not None else ""
            elif t == "inlineStr":
                val = "".join(_字(x) for x in c.iterfind("m:is", _NS))
            else:
                val = (v.text if v is not None else None) or ""
                if not val and c.find("m:f", _NS) is not None:
                    要確認.append(f"{名}#{タブ} {c.get('r')}: 式の値が残っていない（Excel で開いて保存し直す）")
                if val and t in (None, "n"):
                    if int(c.get("s", 0)) in 時刻:   # 日の小数 → 時:分
                        m = int((Decimal(val) * 24 * 60).quantize(Decimal(1)))
                        val = f"{'-' if m < 0 else ''}{abs(m) // 60}:{abs(m) % 60:02d}"
                    else:
                        val = _数の字(val)
            r = re.match(r"[A-Z]+(\d+)", c.get("r"))
            升[(int(r.group(1)) - 1, _列の番号(c.get("r")))] = val.strip()
        if 升:
            nr, nc = max(k[0] for k in 升) + 1, max(k[1] for k in 升) + 1
            out.append(表(f"{名}#{タブ}", tuple(tuple(升.get((i, j), "") for j in range(nc)) for i in range(nr))))
    return out
