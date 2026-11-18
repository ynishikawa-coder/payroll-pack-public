"""出力の名と版（Drive の型.md §6）。名は出口が付ける（人が付けない・雛形から写さない）。

  3_月ごと/<月>/2_出す物/<物>_<会社>_<支給月>_v<n>
会社は会社の呼び名（Drive の型 §1: 全部のシートの列「会社」と同じ字。型に会社の番号は無い）＝月次 が渡す 会社名 のまま。
2_出す物/ には最新の版 1 つだけ（物で分けたフォルダは切らない）。出し直したら前の版を会社の根の `9_履歴/` へ移す。
出口は Drive を開かない: 殻が 2_出す物/ に今ある名と 9_履歴/ にある名を渡し、出口は新しい名と 9_履歴/ へ移す名を返す。

支給月の字の正本もここ 1 か所（`出す支給月`）: 名・証明（出口/証明.py）・出す前の照らし（plugins/payroll-agent/bin/出す前の照らし.py）は
どれも `出す支給月` で直した字（月 `YYYY-MM`・賞与 `YYYY-MM-賞与`）を書き、`名の頭`・`出す名か` で名の形を照らす（形を写さない）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .行 import 支給月を確かめる

出す置き場 = "2_出す物"   # 月の置き場（3_月ごと/<月>/）の中
履歴の置き場 = "9_履歴"   # 会社の根（10_会社/<会社>/）の中
# 出口が知る物 → 置く所（どれも 2_出す物/ の直下）。物の名は出す名の頭 `<物>_` にもなる
出す物の置き場 = {物: 出す置き場 for 物 in ("取り込み", "賞与の取り込み", "支給控除一覧_雇用", "支給控除一覧_業務委託", "有給休暇管理表", "明細")}


回たち = ("月", "賞与")
_殻の支給月 = re.compile(r"^(\d{4})\.(0[1-9]|1[0-2])支給$")


def 殻の支給月か(支給月) -> bool:
    """殻が月を回す・賞与を回す・出す前の照らし に渡す支給月の字 `YYYY.MM支給` か（課題の題と同じ字。出口の字は受けない）。"""
    return isinstance(支給月, str) and _殻の支給月.match(支給月) is not None and not 支給月.endswith("\n")


def 出す支給月(支給月: str, 回: str = "月") -> str:
    """名と証明が書く支給月の字（正本）: 月 `YYYY-MM`・賞与 `YYYY-MM-賞与`。
    受ける字は 殻・段の解決の `YYYY.MM支給` か、この形そのもの。ほかの形・回と合わない `-賞与`・知らない回は止める。"""
    if 回 not in 回たち:
        raise ValueError(f"回 {回!r} は {'・'.join(回たち)} のどれでもない")
    if not isinstance(支給月, str):
        raise ValueError(f"支給月の形が違う: {支給月!r}（YYYY.MM支給 か YYYY-MM か YYYY-MM-賞与）")
    m = _殻の支給月.match(支給月)
    if m:
        基 = f"{m[1]}-{m[2]}"
    else:
        try:
            支給月を確かめる(支給月)
        except ValueError:
            raise ValueError(f"支給月の形が違う: {支給月!r}（YYYY.MM支給 か YYYY-MM か YYYY-MM-賞与）") from None
        if 支給月.endswith("-賞与") and 回 != "賞与":
            raise ValueError(f"支給月 {支給月} は賞与の字で、回 {回} と合わない")
        基 = 支給月[:7]
    return 基 + ("-賞与" if 回 == "賞与" else "")


def 名の頭(物: str, 会社: str, 支給月: str) -> str:
    """出す名の版の番号の前まで `<物>_<会社>_<支給月>_v`。支給月は `出す支給月` の字だけ受ける。"""
    支給月を確かめる(支給月)
    return f"{物}_{会社}_{支給月}_v"


def 出す名か(名, 物: str, 会社: str, 支給月: str) -> bool:
    """名が `名を付ける` の付けた形 `<物>_<会社>_<支給月>_v<n>`（拡張子なし）か。支給月が出口の字でなければ False。"""
    try:
        頭 = 名の頭(物, 会社, 支給月)
    except ValueError:
        return False
    return isinstance(名, str) and re.fullmatch(re.escape(頭) + r"\d+", 名) is not None


@dataclass(frozen=True)
class 出す名:
    フォルダ: str          # 月の置き場の中の置き場（2_出す物）
    名: str                # 拡張子なし
    版: int
    履歴へ移す: tuple[str, ...]   # 2_出す物/ から会社の根の 9_履歴/ へ移す名（殻が渡した字のまま）


def 名を付ける(物: str, 会社: str, 支給月: str, 今ある名=(), 履歴にある名=()) -> 出す名:
    """今ある名＝2_出す物/ の直下の名・履歴にある名＝会社の根の 9_履歴/ の名（版の番号を戻さないために見る）。"""
    if 物 not in 出す物の置き場:
        raise ValueError(f"物「{物}」は {'・'.join(出す物の置き場)} の外")
    if not str(会社).strip() or str(会社) != str(会社).strip() or re.search(r'[/\\\x00-\x1f]', str(会社)):
        raise ValueError(f"会社は会社の呼び名（型の列「会社」と同じ字・前後の空白と / \\ と制御の字の無い字）で渡す: {会社!r}")
    頭 = 名の頭(物, 会社, 支給月)
    pat = re.compile(re.escape(頭) + r"(\d+)(\.[^./]*)?$")
    前 = []
    for n in 今ある名:
        m = pat.match(str(n))
        if m:
            前.append((int(m.group(1)), str(n)))
    古い = [int(m.group(1)) for m in map(pat.match, map(str, 履歴にある名)) if m]
    版 = max([v for v, _ in 前] + 古い, default=0) + 1
    return 出す名(フォルダ=出す物の置き場[物], 名=f"{頭}{版}", 版=版,
                 履歴へ移す=tuple(n for _, n in sorted(前)))
