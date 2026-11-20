#!/usr/bin/env python3
"""止める見張り（給与エージェント）の判定 — 出す物の本と管理表の出荷の欄を、出荷の口の外から窓が道具で直に書くのを止める。

なぜ在るか（根治・2026-11-17）: 窓が前の版の本を写して値を差し替え（シートの道具の書き込み）、管理表の今の版を手で書き換えて
  出せた。出す表を作れるのはパックの出口だけ、置く・管理表へ書くのは各社の出荷の口（窓の道具の外）だけにする。
  判定はパックのここ 1 か所に置き、両側の窓が同じ見張りで止める（hook の入口は ../hooks/見張り.py）。

止める物（道具の名は接続ごとの頭が付く＝末尾で見る）:
  1. シートの道具の書き込み（update_values・append_values・batch_clear_values・update_formulas・update_spreadsheet・
     insert_dimension・copy_sheet_to_another_spreadsheet）で、宛先の本の名が出す物の名の頭（パックの出口が知る物
     `<物>_`＝取り込み_・賞与の取り込み_・支給控除一覧_…・有給休暇管理表_）で始まる・出荷の口の印がある
  2. 同じ書き込みで、宛先の名に `管理表` を含み、回の状況のタブ（月の状況・賞与の状況…＝パックの管理表の型で「回」を持つ
     タブの全部・パックの場所.守るタブたち）の 取り込み・納品 の欄に掛かる／止まりの理由 の欄に `今の版` を書く／範囲の無い構造の書き込み
  3. Drive の道具の create_file・copy_file で名が 1 の頭で始まる物、update_file・copy_file の元が 1 の本
  4. Bash で、殻が渡した「置き換える命令」の名から次の区切りまでの引数に replace が在り（例 `<命令> replace <id>`）、宛先が
     1 の本。命令の文は字で分けて見る（replace の字が在るだけでは止めない）。分けられない文・見分けられない字は止める
  5. 名の照らし: Drive の道具で確認ページ（名の頭 `確認事項_`・前の形 `確認ページ_`）を作る時、名がパックの確認ページの名の形
     （確認ページ/確認ページ.py の 名の形）でない・置き場が違う（同じ所の 置き場の名たち＝名の 組 が 事務所 なら 事務所 の
     フォルダ〔00_事務所〕・ほかは会社のフォルダ〔8_確認事項〕。正本は docs/設計/Drive の型.md §3 の表）
宛先の名が引けない時は止める（引けない＝見分けられない）。名を引く口が「見えない」と返した本（出荷の口に見えない本）は通す。
名・タブ・見出し・値の字は、パックの字のそろえ方の正本（芯/字.py・口の 字）でそろえてから比べる（頭の空白・全角・幅の無い字で
抜けない）。そろえ方が渡らない口は見分けられない＝止める。
名を引く・見出しを引く手は殻が渡す（口）。ここは Drive を開かない。Python 3 の標準ライブラリだけ。
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Callable

シートの書き込み = ("update_values", "append_values", "batch_clear_values", "update_formulas", "update_spreadsheet",
               "insert_dimension", "copy_sheet_to_another_spreadsheet")
構造 = ("update_spreadsheet", "batch_clear_values", "insert_dimension")
Driveの書き込み = ("create_file", "copy_file", "update_file")
管理表の語 = "管理表"
出荷の欄 = ("取り込み", "納品")
今の版の欄, 今の版の頭 = "止まりの理由", "今の版"
確認ページの頭たち = ("確認事項_", "下書き_確認事項_", "確認ページ_", "下書き_確認ページ_")   # 今の形と前の形（前の形は名の形に合わない＝止める）


@dataclass
class 口:
    """外を引く口（殻が渡す・試験は差し替える）。"""
    名の頭たち: tuple[str, ...]                          # パックの出口が知る物の名の頭（パックの場所.名の頭たち）
    名を引く: Callable[[str], dict]                      # id → {"name", "appProperties", "見えない"?}。引けない時は例外
    見出しを引く: Callable[[str, str], list]             # (本の id, タブ) → 1 行目
    印: str = ""                                          # 出荷の口が置いた本の印（appProperties の鍵・値 "1"）
    置き換える命令: tuple[str, ...] = ()                   # Bash の `<命令> replace <id>` の命令の名（末尾で見る）
    確認ページの形: tuple[str, dict] | None = None         # (名の正規表現, {"<会社>": フォルダの名, "事務所": フォルダの名})。パックに無い版では None
    守るタブ: tuple[str, ...] = ()                        # 管理表の回の状況のタブの名（パックの場所.守るタブたち）。空＝見分けられない＝止める
    字: object = None                                     # 字のそろえ方の正本（パックの 芯.字）。無い＝見分けられない＝止める
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


def 判定(tool: str, args: dict, k: 口) -> str | None:
    """止める訳（止めないなら None）。"""
    short = tool.rsplit("__", 1)[-1]
    args = args if isinstance(args, dict) else {}
    if 見るか(tool) and getattr(k.字, "そろえる", None) is None:
        return "字のそろえ方（パックの 芯/字.py）が渡らない＝名を見分けられない"
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
    if not k.字.含む(m.get("name", ""), 管理表の語):
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
    if k.字.頭が(名, 確認ページの頭たち):
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
    return None


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
    置き場 = 置き場たち.get("事務所" if 組 == "事務所" else "<会社>")
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


def _語(cmd: str) -> list[str]:
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)                                      # 閉じない引用は ValueError


def _気になる(字: str, 命令たち: tuple[str, ...], 両方: bool = False) -> bool:
    """引用と \\ を外した字に replace・命令の名が在るか（両方=True は両方とも）。分け直す前の字は割られているため外して見る。"""
    生 = re.sub(r"[\\'\"]", "", 字)
    r, n = "replace" in 生, any(c in 生 for c in 命令たち)
    return (r and n) if 両方 else (r or n)


def 置き換える先たち(cmd: str, 命令たち: tuple[str, ...], 深さ: int = 0) -> list[str]:
    """Bash の命令の文を字で分け（引用・\\ は shell と同じに外す＝`re\\place`・`'re'place` も replace）、挙げた命令の名
    （末尾で見る・path 付きも）から次の区切り（; && | 改行の前の ( など）までの引数に `replace` が在る時、その次の字＝
    置き換える先の id を集める（旗や旗の値を挟んでも見る）。名の前や別の部分命令の `replace`（python の str.replace・
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
    for i, w in enumerate(words):
        if any(w.endswith(c) for c in 命令たち):
            for j in range(i + 1, len(words)):
                if set(words[j]) <= 区切り:
                    break
                if words[j] == "replace":
                    fid = words[j + 1] if j + 1 < len(words) else ""
                    先たち.append("" if set(fid) <= 区切り else fid)
                    break
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
    return None
