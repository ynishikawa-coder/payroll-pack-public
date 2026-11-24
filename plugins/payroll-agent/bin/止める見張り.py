#!/usr/bin/env python3
"""止める見張り（給与エージェント）の判定 — 出す物の本と管理表の出荷の欄を、出荷の口の外から窓が道具で直に書くのを止める。

なぜ在るか（根治・2026-11-17）: 窓が前の版の本を写して値を差し替え（シートの道具の書き込み）、管理表の今の版を手で書き換えて
  出せた。出す表を作れるのはパックの出口だけ、置く・管理表へ書くのは各社の出荷の口（窓の道具の外）だけにする。
  判定はパックのここ 1 か所に置き、両側の窓が同じ見張りで止める（hook の入口は ../hooks/見張り.py）。

止める物（道具の名は接続ごとの頭が付く＝末尾で見る）:
  1. シートの道具の書き込み（update_values・append_values・batch_clear_values・update_formulas・update_spreadsheet・
     insert_dimension・copy_sheet_to_another_spreadsheet）で、宛先の本の名が出す物の名の頭（パックの出口が知る物
     `<物>_`＝取り込み_・賞与の取り込み_・支給控除一覧_…・有給休暇管理表_）で始まる・出荷の口の印がある
  2. 同じ書き込みで、宛先の名に管理表の本の名（パックの 型.json の木）を含み、回の状況のタブ（月の状況・賞与の状況…＝パックの管理表の型で「回」を持つ
     タブの全部）とタブ 出した物（物ごとの今の版とリンク・型で 書くのは 出荷の口）＝パックの場所.守るタブたち の 取り込み・納品・
     今の版・リンク の欄に掛かる／止まりの理由 の欄に `今の版` を書く（前の取り違えの形を窓が作り直さない）／範囲の無い構造の書き込み
  3. Drive の道具の create_file・copy_file で名が 1 の頭で始まる物、update_file・copy_file の元が 1 の本
  4. Bash で、殻が渡した「置き換える命令」の名から次の区切りまでの引数に replace が在り（例 `<命令> replace <id>`）、宛先が
     1 の本。命令の文は字で分けて見る（replace の字が在るだけでは止めない）。分けられない文・見分けられない字は止める
  5. 名の照らし: Drive の道具で確認ページ（名の頭はパックの 確認ページ.py の 名の頭たち＝今の形と前の形）を作る時、名がパックの確認ページの名の形
     （確認ページ/確認ページ.py の 名の形）でない・置き場が違う（同じ所の 置き場の名たち＝名の 組 が 事務所 なら 事務所 の
     フォルダ・ほかは会社のフォルダ。正本は 初期設定/型.json の 木.確認事項の置き場）
  6. 年の台帳（名が `台帳_<支給年>`＝パックの 初期設定/型の口.台帳の名か が正本）へ、1 のシートの道具で直に書く・Drive の道具で
     その名の本を作る・写す・元を写す／移す／書き換える（9_履歴へ移すを含む）。書くのは 月次/台帳へ書く.py の書く手順を
     当てる口（殻の *_gate.py が Bash の python で呼ぶ）だけ＝道具の直の書き込みは止め、Bash で関所を呼ぶ道は 4 の外で止めない
宛先の名が引けない時は止める（引けない＝見分けられない）。名を引く口が「見えない」と返した本（出荷の口に見えない本）は通す。
名・タブ・見出し・値の字は、パックの字のそろえ方の正本（芯/字.py・口の 字）でそろえてから比べる（頭の空白・全角・幅の無い字で
抜けない）。
判定とそれが読む物は同じ版から読む（根治・2026-11-20・台帳の束 K-guardver）: 口が 字・守るタブ・管理表の名・確認ページの頭たち・台帳の名か を渡さない時（その版を知らない
前の入口・殻の入口）、判定は自分と同じ版のパック（この file の上を辿った repo・無ければ plugin を入れた同じ版の目録の複製）から
読む（`自分の版の部品`・入口ごとに写さない）。それでも字のそろえ方が読めない時は、守る物に掛かる命令だけを止める: シート・Drive の
道具の書き込み（宛先の名を照らせない）と、Bash で置き換える命令の置き換える先が在る・見分けられない文。守る物に掛からない Bash
（置き換える命令を含まない命令）は通す（前の形は echo まで全部止め、窓が動けなくなった）。
名を引く・見出しを引く手は殻が渡す（口）。ここは Drive を開かない。Python 3 の標準ライブラリだけ。
"""
from __future__ import annotations

import re
import shlex
import sys
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Callable

シートの書き込み = ("update_values", "append_values", "batch_clear_values", "update_formulas", "update_spreadsheet",
               "insert_dimension", "copy_sheet_to_another_spreadsheet")
構造 = ("update_spreadsheet", "batch_clear_values", "insert_dimension")
Driveの書き込み = ("create_file", "copy_file", "update_file")
出荷の欄 = ("取り込み", "納品", "今の版", "リンク")   # 回の状況のタブの出荷の欄と、タブ 出した物 の今の版とリンク
今の版の欄, 今の版の頭 = "止まりの理由", "今の版"


@dataclass
class 口:
    """外を引く口（殻が渡す・試験は差し替える）。"""
    名の頭たち: tuple[str, ...]                          # パックの出口が知る物の名の頭（パックの場所.名の頭たち）
    名を引く: Callable[[str], dict]                      # id → {"name", "appProperties", "見えない"?}。引けない時は例外
    見出しを引く: Callable[[str, str], list]             # (本の id, タブ) → 1 行目
    印: str = ""                                          # 出荷の口が置いた本の印（appProperties の鍵・値 "1"）
    置き換える命令: tuple[str, ...] = ()                   # Bash の `<命令> replace <id>` の命令の名（末尾で見る）
    確認ページの形: tuple[str, dict] | None = None         # (名の正規表現, {"会社": フォルダの名, "事務所": フォルダの名})＝パックの場所.確認ページの名の形。パックに無い版では None
    守るタブ: tuple[str, ...] = ()                        # 管理表の出荷の欄を持つタブの名（パックの場所.守るタブたち）。空＝判定と同じ版から読む・読めなければ止める
    管理表の名: str = ""                                  # 管理表の本の名（パックの場所.管理表の名）。空＝判定と同じ版から読む・読めなければ止める
    確認ページの頭たち: tuple[str, ...] = ()              # 確認ページの名の頭（パックの場所.確認ページの頭たち）。空＝判定と同じ版から読む・読めなければ止める
    台帳の名か: Callable[[str], bool] | None = None        # 年の台帳の名か（パックの場所.台帳の名か＝型の口.台帳の名か）。無い＝判定と同じ版から読む・読めなければ止める
    字: object = None                                     # 字のそろえ方の正本（パックの 芯.字）。無い＝判定と同じ版から読む・読めなければ止める
    引いた: list = field(default_factory=list)


def 出す物の本か(m: dict, k: 口) -> bool:
    名 = str(m.get("name", ""))
    印 = (m.get("appProperties") or {}).get(k.印) if k.印 else None
    return k.字.頭が(名, k.名の頭たち) or bool(k.印 and str(印).strip() == "1")


def _列(letters: str) -> int:
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def 範囲を読む(rng: str) -> tuple[str, int | None, int | None]:
    """'タブ'!B2:D9 → (タブ, 1, 3)。列の無い範囲（2:5・タブだけ）は (タブ, None, None)＝全部の列に掛かる。"""
    tab, _, cells = rng.partition("!")
    tab = tab.strip().strip("'")
    if not cells:
        return tab, None, None
    cols = re.findall(r"([A-Za-z]+)\d*", cells)
    if not cols:
        return tab, None, None
    a = _列(cols[0])
    b = _列(cols[-1]) if len(cols) > 1 else (None if ":" in cells else a)
    return tab, a, b


def 見るか(tool: str) -> bool:
    short = tool.rsplit("__", 1)[-1]
    return tool == "Bash" or short in シートの書き込み or short in Driveの書き込み


def _場所():
    """同じ bin の パックの場所（判定と同じ版）。"""
    b = str(Path(__file__).resolve().parent)
    if b not in sys.path:
        sys.path.insert(0, b)
    import パックの場所
    return パックの場所


def 自分の版のパック() -> Path | None:
    """判定と同じ版のパック（正本は パックの場所.同じ版のパック・環境 PAYROLL_PACK_DIR は見ない）。"""
    try:
        return _場所().同じ版のパック(Path(__file__))
    except Exception:  # noqa: BLE001  読めない＝同じ版が見つからない
        return None


# 口の欄 → パックの場所 の読む口。口が渡さない（空の）欄は判定と同じ版のパックから読む（入口ごとに写さない）
_同じ版から読む欄 = (("字", "字の口"), ("守るタブ", "守るタブたち"), ("管理表の名", "管理表の名"),
              ("確認ページの頭たち", "確認ページの頭たち"), ("台帳の名か", "台帳の名か"))


@lru_cache(maxsize=None)
def _部品(パック: str) -> dict:
    """{口の欄: 値}。読めない欄は入れない。パックの場所 の読む口と同じ所から読む（写さない）。"""
    場所 = _場所()
    out = {}
    for 欄, 読む口 in _同じ版から読む欄:
        try:
            out[欄] = getattr(場所, 読む口)(Path(パック))
        except Exception:  # noqa: BLE001  読めない＝その欄は空のまま（使う所が止める）
            pass
    return out


def 自分の版の部品() -> dict:
    """判定と同じ版の部品 {字, 守るタブ, 管理表の名, 確認ページの頭たち, 台帳の名か}。同じ版のパックが無ければ {}。
    試験はここを差し替える。"""
    p = 自分の版のパック()
    return {} if p is None else _部品(str(p))


def _空(欄: str, v) -> bool:
    return getattr(v, "そろえる", None) is None if 欄 == "字" else not v


def そろえた口(k: 口) -> 口:
    """口が渡さない欄（字・守るタブ・管理表の名・確認ページの頭たち・台帳の名か）を、判定と同じ版のパックから埋めた口
    （渡された物はそのまま使う）。"""
    空の欄 = [欄 for 欄, _ in _同じ版から読む欄 if _空(欄, getattr(k, 欄))]
    if not 空の欄:
        return k
    部品 = 自分の版の部品()
    return replace(k, **{欄: 部品[欄] for 欄 in 空の欄 if 欄 in 部品})


def 判定(tool: str, args: dict, k: 口) -> str | None:
    """止める訳（止めないなら None）。"""
    short = tool.rsplit("__", 1)[-1]
    args = args if isinstance(args, dict) else {}
    if not 見るか(tool):
        return None
    k = そろえた口(k)
    if getattr(k.字, "そろえる", None) is None:
        if tool == "Bash":   # 守る物に掛かる命令（置き換える命令の置き換える先が在る・見分けられない文）だけ止める
            try:
                if not 置き換える先たち(str(args.get("command", "")), k.置き換える命令):
                    return None
            except ValueError:
                pass
        return "字のそろえ方（パックの 芯/字.py）が判定と同じ版からも読めない＝守る物の名を見分けられない"
    if tool == "Bash":
        return _bash(str(args.get("command", "")), k)
    if short in Driveの書き込み:
        return _drive(short, args, k)
    if short not in シートの書き込み:
        return None
    if short == "copy_sheet_to_another_spreadsheet":
        sid = args.get("destinationSpreadsheetId") or args.get("destination_spreadsheet_id")
    else:
        sid = args.get("spreadsheetId") or args.get("spreadsheet_id")
    if not sid:
        return "書く先の本の id が無い＝出す物の本か見分けられない"
    try:
        m = k.名を引く(str(sid))
    except Exception:  # noqa: BLE001
        return f"書く先の本（{sid}）の名が引けない＝出す物の本か管理表か見分けられない"
    if 出す物の本か(m, k):
        return f"出す物の本（{m.get('name')}）へ道具で直に書く"
    台帳 = 年の台帳か(m.get("name", ""), k)
    if 台帳:
        return 台帳 if 台帳 is not True else f"年の台帳（{m.get('name')}）へシートの道具で直に書く（書くのは 月次/台帳へ書く.py の書く手順を当てる口だけ）"
    if not k.管理表の名:
        return f"管理表の本の名がパック（初期設定/型.json の木）から読めない＝書く先（{m.get('name')}）が管理表か見分けられない"
    if not k.字.含む(m.get("name", ""), k.管理表の名):
        return None
    if short in 構造:
        return f"管理表（{m.get('name')}）の形を道具で変える・範囲を消す"
    rng = str(args.get("range", ""))
    if "!" not in rng:
        return f"管理表（{m.get('name')}）へタブの名の無い範囲（{rng or '無い'}）で書く＝出荷の欄に掛かるか見分けられない"
    tab, a, b = 範囲を読む(rng)
    if not k.守るタブ:
        return f"管理表の守るタブ（回の状況のタブ）がパックから読めない＝{tab} が出荷の欄を持つタブか見分けられない"
    if not any(k.字.同じ(tab, t) for t in k.守るタブ):
        return None
    try:
        h = list(k.見出しを引く(str(sid), tab) or [])
    except Exception:  # noqa: BLE001
        return f"管理表の {tab} の見出しが引けない＝出荷の欄に掛かるか見分けられない"
    if not h:
        return f"管理表の {tab} の見出しが空＝出荷の欄に掛かるか見分けられない"
    lo = 0 if a is None else a
    hi = len(h) - 1 if b is None else b
    if short == "append_values":
        lo, hi = 0, len(h) - 1
    hit = [h[i] for i in range(lo, min(hi, len(h) - 1) + 1) if any(k.字.同じ(h[i], x) for x in 出荷の欄)]
    if hit:
        return f"管理表の {tab} の出荷の欄（{'・'.join(map(str, hit))}）を道具で直に書く"
    for j in [i for i, x in enumerate(h) if k.字.同じ(x, 今の版の欄)]:
        if lo <= j <= hi:
            for row in (args.get("values") or []) + (args.get("formulas") or []):
                i = j - lo
                if isinstance(row, list) and i < len(row) and k.字.含む(row[i], 今の版の頭):
                    return f"管理表の {今の版の欄} に「{今の版の頭}」を道具で直に書く"
    return None


def _drive(short: str, args: dict, k: 口) -> str | None:
    名 = str(args.get("name") or args.get("title") or (args.get("metadata") or {}).get("name") or "")
    if k.字.頭が(名, k.名の頭たち):
        return f"Drive の道具で出す物の本（{名}）を作る"
    台帳 = 年の台帳か(名, k) if short != "update_file" else None   # update_file の name は元の本の名＝下の元で照らす
    if 台帳:
        return 台帳 if 台帳 is not True else f"Drive の道具で年の台帳（{名}）を作る・写す（作るのは 月次/台帳へ書く.py の書く手順を当てる口だけ）"
    if not k.確認ページの頭たち:
        return f"確認ページの名の形（名の頭たち＝確認ページ/確認ページ.py）がパックから読めない＝{名 or '名の無い物'} が確認ページか見分けられない"
    if k.字.頭が(名, k.確認ページの頭たち):
        外れ = 確認ページの名の外れ(名, args, k)
        if 外れ:
            return 外れ
    src = args.get("fileId") or args.get("sourceFileId") or args.get("file_id")
    if short in ("copy_file", "update_file") and src:
        try:
            m = k.名を引く(str(src))
        except Exception:  # noqa: BLE001
            return f"元のファイル（{src}）の名が引けない＝出す物の本か見分けられない"
        if 出す物の本か(m, k):
            return f"Drive の道具で出す物の本（{m.get('name')}）を写す・書き換える"
        台帳 = 年の台帳か(m.get("name", ""), k)
        if 台帳:
            return 台帳 if 台帳 is not True else f"Drive の道具で年の台帳（{m.get('name')}）を写す・移す・書き換える"
    return None


def 年の台帳か(名, k: 口) -> bool | str:
    """名が年の台帳（`台帳_<支給年>`・名の形の正本はパックの 型の口.台帳の名か）か。字のそろえ方でそろえてから照らす。
    名の形がパックから読めない時は止める訳の字を返す（見分けられない）。"""
    if k.台帳の名か is None:
        return f"年の台帳の名の形（初期設定/型の口.台帳の名か）がパックから読めない＝{名 or '名の無い物'} が年の台帳か見分けられない"
    return bool(k.台帳の名か(k.字.そろえる(名)) or k.台帳の名か(str(名).strip()))


def 確認ページの名の外れ(名: str, args: dict, k: 口) -> str | None:
    """名の照らし: 確認ページは `確認事項_<組>_<支給月の名>_v<版>.html` を、組が 事務所 なら事務所のフォルダ（00_事務所）へ・
    ほかは会社のフォルダ（8_確認事項）へ。名の形とフォルダの名はパックの 1 か所から渡る（写さない）。"""
    if not k.確認ページの形:   # パックの名の形が無い・読めない＝見分けられない＝止める（形を写さない）
        return f"確認ページの名の形がパック（確認ページ/確認ページ.py の 名の形・置き場の名たち）から読めない＝{名} が正しい名か見分けられない"
    形, 置き場たち = k.確認ページの形
    m = re.fullmatch(形, 名)
    if not m:
        return f"確認ページの名 {名} が名の形（{形}）でない"
    組 = m.groupdict().get("組")
    if not 組 or not isinstance(置き場たち, dict):
        return f"確認ページ {名} の組か置き場の名たちが読めない＝置き場を見分けられない"
    置き場 = 置き場たち.get("事務所" if 組 == "事務所" else "会社")   # 鍵は役の名（会社の根の印の字はパックだけが持つ）
    if not 置き場:
        return f"確認ページ {名} の置き場の名がパックに無い＝置き場を見分けられない"
    parents = args.get("parents") or args.get("parentId") or args.get("parent_id") or (args.get("metadata") or {}).get("parents")
    pid = (parents[0] if isinstance(parents, list) and parents else parents) if parents else None
    if not pid:
        return f"確認ページ {名} の置き場が渡されない＝{置き場} か見分けられない"
    try:
        pm = k.名を引く(str(pid))
    except Exception:  # noqa: BLE001
        return f"確認ページの置き場（{pid}）の名が引けない＝{置き場} か見分けられない"
    if str(pm.get("name", "")) != 置き場:
        return f"確認ページ {名} の置き場が {pm.get('name')}（{置き場} へ置く）"
    return None


区切り = set("();&|<>")
_私用の字 = "".join(map(chr, range(0xE000, 0xE110)))                   # 字に出ない私用の字（仮の字の元）
_仮の字 = {c: _私用の字[i] for i, c in enumerate(sorted(区切り))}   # 引用・\ の中の区切りの字（ただの字）の仮の字
_本文の字 = {c: _私用の字[0x20 + i] for i, c in enumerate(sorted(区切り | set(" \t\n'\"\\")))}   # heredoc の本文の字（本文を 1 つの字にする）
_仮の字を戻す = {v: c for d in (_仮の字, _本文の字) for c, v in d.items()}
_fd = {str(d): _私用の字[0x100 + d] for d in range(10)}                # リダイレクトの頭の数字（`2>` の 2）の仮の字
_fdを戻す = {v: d for d, v in _fd.items()}
_fdの字 = "".join(_fd.values())
_リダイレクトの形 = "[" + _fdの字 + r"]*(?:<<<|<<-|<<|<>|<&|>&|&>>|&>|>>|>\||<|>)"
_リダイレクト = re.compile(_リダイレクトの形)
_置換 = re.compile(r"[<>]\(")                                         # プロセス置換 `<(…)`・`>(…)` の頭
_記号の並び = re.compile(r"[<>]\(|" + _リダイレクトの形 + r"|&&|\|\||;;|[;&|()]")


def _heredocの終わり(cmd: str, i: int) -> tuple[str, bool]:
    """i が `<<`・`<<-` の頭の時、その終わりの語（引用と \\ を外す）と、行の頭のタブを外すか。"""
    j = i + 2
    tabs = j < len(cmd) and cmd[j] == "-"
    j += 1 if tabs else 0
    while j < len(cmd) and cmd[j] in " \t":
        j += 1
    語, q = [], ""
    while j < len(cmd):
        c = cmd[j]
        if q:
            q = "" if c == q else q
            if q:
                語.append(c)
        elif c in "'\"":
            q = c
        elif c == "\\" and j + 1 < len(cmd):
            語.append(cmd[j + 1])
            j += 1
        elif c.isspace() or c in 区切り:
            break
        else:
            語.append(c)
        j += 1
    return "".join(語), tabs


def _印を付ける(cmd: str) -> str:
    """shell と同じに引用（'…'・"…"）・\\・注（語の頭の # から行の終わり）・改行・heredoc を見て、shlex で割れる字にする。
    - 引用や \\ の中の区切りの字は仮の字（ただの字）にする。`\\` と改行の続き（行の継ぎ）は shell と同じに消す。
    - 語の頭から < > の直前まで続く数字（`2>&1` の 2）は仮の字（リダイレクトの頭）にする。`>&`・`<&` の直後の数字
      （`2>&1` の 1）は写す先の語で、語の頭でない（`2>&1>log` の 1 を印にすると `>&1>` が 1 字句になり後ろを読み落とす）。
    - 引用の外の改行は命令の区切り（`;`）にする（改行の後は前の命令の引数でない）。
    - heredoc（`<<語`・`<<-語`）の本文（次の行から終わりの語の行まで）は 1 つの字にし、前後を区切る（本文は命令の引数でない）。
    shlex は引用を外すと `'>'` と `>` を見分けられず、`2>` を `2` と `>` に割り、改行を空白と読むため、割る前に印を付ける。"""
    out: list[str] = []
    待つ: list[tuple[str, bool]] = []                     # この行で始まった heredoc の終わりの語
    i, n, q = 0, len(cmd), ""
    while i < n:
        c = cmd[i]
        前 = cmd[i - 1] if i else ""
        語の頭 = i == 0 or 前.isspace() or (前 in 区切り and not (前 == "&" and i >= 2 and cmd[i - 2] in "<>"))
        if q == "'":
            out.append(_仮の字.get(c, c))
            q = "" if c == "'" else q
        elif c == "\\" and i + 1 < n and cmd[i + 1] == "\n":   # 行の継ぎ（引用の外と "…" の中）
            i += 1
        elif c == "\\" and i + 1 < n:                     # 引用の外と "…" の中の \ は次の字を字にする
            out += [c, _仮の字.get(cmd[i + 1], cmd[i + 1])]
            i += 1
        elif q == '"':
            out.append(_仮の字.get(c, c))
            q = "" if c == '"' else q
        elif c in "'\"":
            out.append(c)
            q = c
        elif c == "#" and 語の頭:
            j = cmd.find("\n", i)
            j = n if j < 0 else j
            out.append(cmd[i:j])
            i = j - 1
        elif c == "\n":
            out.append(" ; ")
            for 終わり, tabs in 待つ:                     # 本文を 1 つの字にして前後を区切る
                本文: list[str] = []
                while i + 1 < n:
                    j = cmd.find("\n", i + 1)
                    j = n if j < 0 else j
                    行 = cmd[i + 1:j]
                    i = j
                    if (行.lstrip("\t") if tabs else 行) == 終わり:
                        break
                    本文.append(行 + "\n")
                if 本文:
                    out.append("".join(_本文の字.get(x, x) for x in "".join(本文)) + " ; ")
            待つ = []
        elif c == "<" and cmd[i:i + 2] == "<<" and cmd[i:i + 3] != "<<<":
            待つ.append(_heredocの終わり(cmd, i))
            out.append("<<")
            i += 1
        elif c.isdigit() and 語の頭:
            j = i
            while j < n and cmd[j].isdigit():
                j += 1
            out.append("".join(_fd[d] for d in cmd[i:j]) if j < n and cmd[j] in "<>" else cmd[i:j])
            i = j - 1
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _語(cmd: str) -> list[tuple[str, str]]:
    """命令の文を字で分け、(字, 種) の並びにする。種は 語（ただの字。引用・\\ の中の < > ; なども語・heredoc の本文も 1 つの語）・
    リダイレクト（`2>&1`・`>`・`>>`・`<`・`&>`・`>|`・`<<` など＝次の語がその的）・置換（プロセス置換の頭 `<(`・`>(`）・
    区切り（; && || | & ( ) と改行）。shlex が続けて 1 字句にした記号（`;>`・`>>(` など）は記号ごとに割り直す。"""
    lex = shlex.shlex(_印を付ける(cmd), posix=True, punctuation_chars="();&|<>" + _fdの字)
    lex.whitespace_split = True
    words = []
    for w in lex:                                         # 閉じない引用は ValueError
        if set(w) <= 区切り | set(_fdを戻す):
            for x in _記号の並び.findall(w) if "".join(_記号の並び.findall(w)) == w else [w]:
                種 = "置換" if _置換.fullmatch(x) else "リダイレクト" if _リダイレクト.fullmatch(x) else "区切り"
                words.append(("".join(_fdを戻す.get(c, c) for c in x), 種))
        else:
            words.append(("".join(_仮の字を戻す.get(c, _fdを戻す.get(c, c)) for c in w), "語"))
    return words


def _置換の後(words: list[tuple[str, str]], j: int) -> int:
    """j 番の置換の頭（`<(`・`>(`）に対応する `)` の次の番。中は別の命令（呼ぶ側が別に読む）。"""
    深さ = 0
    while j < len(words):
        w, 種 = words[j]
        if 種 == "置換" or (種 == "区切り" and w == "("):
            深さ += 1
        elif 種 == "区切り" and w == ")":
            深さ -= 1
            if 深さ == 0:
                return j + 1
        j += 1
    return j


def _引数(words: list[tuple[str, str]], i: int) -> list[str]:
    """i 番の語の次から次の区切りまでの引数。リダイレクトとその的（次が語の時だけ）は命令の引数でないので外し、後ろを
    読み続ける。プロセス置換 `<(…)`・`>(…)` は 1 つの引数（中の字は別の命令＝この命令の引数でない）。"""
    引数: list[str] = []
    j = i + 1
    while j < len(words):
        w, 種 = words[j]
        if 種 == "区切り":
            break
        if 種 == "リダイレクト":
            j += 1
            if j < len(words) and words[j][1] == "語":
                j += 1
            elif j < len(words) and words[j][1] == "置換":
                j = _置換の後(words, j)
            continue
        if 種 == "置換":
            引数.append("(置換)")
            j = _置換の後(words, j)
            continue
        引数.append(w)
        j += 1
    return 引数


def _気になる(字: str, 命令たち: tuple[str, ...], 両方: bool = False) -> bool:
    """引用と \\ を外した字に replace・命令の名が在るか（両方=True は両方とも）。分け直す前の字は割られているため外して見る。"""
    生 = re.sub(r"[\\'\"]", "", 字)
    r, n = "replace" in 生, any(c in 生 for c in 命令たち)
    return (r and n) if 両方 else (r or n)


def 置き換える先たち(cmd: str, 命令たち: tuple[str, ...], 深さ: int = 0) -> list[str]:
    """Bash の命令の文を字で分け（引用・\\ は shell と同じに外す＝`re\\place`・`'re'place` も replace）、挙げた命令の名
    （末尾で見る・path 付きも）から次の区切り（; && || | & ( など）までの引数に `replace` が在る時、その次の字＝
    置き換える先の id を集める（旗や旗の値を挟んでも見る。`2>&1`・`>/dev/null`・`&>log`・`<in` などのリダイレクトと
    その的は区切りでなく引数から外して読み続ける。引用の中の `>` などはただの字）。名の前や別の部分命令の `replace`（python の str.replace・
    echo replace）は集めない。命令の名と replace を両方含む 1 つの字（`bash -c '…'`・heredoc の中の引用）は分け直して見、
    分け直しても置き換える先が出ない時は見分けられない＝ValueError。分けられない文で、引用と \\ を外した字に replace か
    命令の名が在る時も ValueError（呼ぶ側が止める）。"""
    if not 命令たち:
        return []
    try:
        words = _語(cmd)
    except ValueError:
        if _気になる(cmd, 命令たち):
            raise
        return []
    先たち: list[str] = []
    for i, (w, 種) in enumerate(words):
        if 種 != "語":
            continue
        if any(w.endswith(c) for c in 命令たち):
            引数 = _引数(words, i)
            if "replace" in 引数:
                j = 引数.index("replace")
                先たち.append(引数[j + 1] if j + 1 < len(引数) else "")
        elif _気になる(w, 命令たち, 両方=True):
            中 = 置き換える先たち(w, 命令たち, 深さ + 1) if 深さ < 3 and w != cmd else []
            if not 中:
                raise ValueError(f"命令の名と replace を含む字（{w[:60]}）を分けて見分けられない")
            先たち += 中
    return 先たち


def _bash(cmd: str, k: 口) -> str | None:
    try:
        先たち = 置き換える先たち(cmd, k.置き換える命令)
    except ValueError:
        return "命令の文を字で分けられない・置き換える命令か見分けられない（bash -c などは命令を直に打つ）"
    for fid in 先たち:
        if not fid:
            return "置き換える命令の置き換える先が無い＝出す物の本か見分けられない"
        try:
            m = k.名を引く(fid)
        except Exception:  # noqa: BLE001
            return f"置き換える先（{fid}）の名が引けない＝出す物の本か見分けられない"
        if 出す物の本か(m, k):
            return f"置き換える命令で出す物の本（{m.get('name')}）を置き換える"
        台帳 = 年の台帳か(m.get("name", ""), k)
        if 台帳:
            return 台帳 if 台帳 is not True else f"置き換える命令で年の台帳（{m.get('name')}）を置き換える（書くのは 月次/台帳へ書く.py の書く手順を当てる口だけ）"
    return None
