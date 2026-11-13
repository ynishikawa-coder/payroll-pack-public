"""出力の名と版（Drive の型.md §6）。名は出口が付ける（人が付けない・雛形から写さない）。

  10_月ごと/<月>/03_出力/<番号フォルダ>/<物>_<会社>_<支給月>_v<n>
各番号フォルダには最新の版 1 つだけ。出し直したら前の版を同じフォルダの `旧版/` へ移す。
出口は Drive を開かない: 殻がそのフォルダに今ある名を渡し、出口は新しい名と旧版へ移す名を返す。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .行 import 支給月を確かめる

番号フォルダ = {
    "取り込み": "01_取り込み",
    "賞与の取り込み": "01_取り込み",
    "支給控除一覧_雇用": "02_支給控除一覧",
    "支給控除一覧_業務委託": "02_支給控除一覧",
    "有給休暇管理表": "03_有給休暇管理表",
    "明細": "04_明細",
}
旧版 = "旧版"


@dataclass(frozen=True)
class 出す名:
    フォルダ: str          # 03_出力/ の下の番号フォルダ
    名: str                # 拡張子なし
    版: int
    旧版へ移す: tuple[str, ...]   # 今のフォルダから `旧版/` へ移す名（殻が渡した字のまま）


def 名を付ける(物: str, 会社: str, 支給月: str, 今ある名=(), 旧版にある名=()) -> 出す名:
    """今ある名＝番号フォルダの直下の名・旧版にある名＝その `旧版/` の名（版の番号を戻さないために見る）。"""
    if 物 not in 番号フォルダ:
        raise ValueError(f"物「{物}」は {'・'.join(番号フォルダ)} の外")
    if not re.fullmatch(r"[0-9A-Za-z]+", str(会社)):
        raise ValueError(f"会社は番号で渡す（名は書かない）: {会社!r}")
    支給月を確かめる(支給月)
    頭 = f"{物}_{会社}_{支給月}_v"
    pat = re.compile(re.escape(頭) + r"(\d+)(\.[^./]*)?$")
    前 = []
    for n in 今ある名:
        m = pat.match(str(n))
        if m:
            前.append((int(m.group(1)), str(n)))
    古い = [int(m.group(1)) for m in map(pat.match, map(str, 旧版にある名)) if m]
    版 = max([v for v, _ in 前] + 古い, default=0) + 1
    return 出す名(フォルダ=番号フォルダ[物], 名=f"{頭}{版}", 版=版,
                 旧版へ移す=tuple(n for _, n in sorted(前)))
