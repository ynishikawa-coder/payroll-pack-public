"""名の束（tests/data/ の 製品の名・側の名・環境の名）を読み、字の揺れをそろえて当てる部品（1 か所）。

名の線（tests/test_骨.py の「4. 入れてよい物の線」・tests/test_給与エージェントの器.py の「2. 線」）は、ここで
束を読み、語と相手の字を同じ形にそろえてから当てる。字のそのままの一致で当てると、全角の英字・大文字と小文字の
違い（全部を大文字で書いた名）・幅の無い字（U+200B など）を挟んだ名が束に当たらず通る（台帳 2026-11-20・#271 のレビュー）。

そろえ方の正本は 芯/字.py（NFKC → 書式の字 Cf を消す → 字の大小をそろえる。ここでは空白を消さず 1 つにまとめる）。束の語の末尾に `〔大小を分ける〕` が在る語だけは字の大小を分ける（英語の言葉と同じ綴りの
製品の名を、小文字の地の語〔変数の名など〕と誤らないため）。NFKC と書式の字の消しは、どの語にも当てる。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # パックの根（芯/字.py を読む）
from 芯 import 字 as _字  # noqa: E402  そろえ方の正本（写さない）

大小を分ける印 = "〔大小を分ける〕"


def そろえる(字: str, 大小も: bool = True) -> str:
    """芯/字.py の そろえる（空白は 1 つにまとめて残す＝語の切れ目をまたいで当てない）。"""
    return _字.そろえる(字, 大小も, 空白も=False)


class 語:
    """束の 1 語。当たるかは `語.当たる(相手の字)`（相手は呼ぶ側で そろえる 前の生の字を渡す）。"""

    def __init__(self, 行: str):
        self.大小を分ける = 行.endswith(大小を分ける印)
        self.字 = 行.removesuffix(大小を分ける印).strip()
        self._形 = そろえる(self.字, not self.大小を分ける)

    def 当たる(self, 相手: str) -> bool:
        return bool(self._形) and self._形 in そろえる(相手, not self.大小を分ける)

    def __str__(self) -> str:
        return self.字

    def __repr__(self) -> str:
        return f"語({self.字!r})"


def 束(path: Path) -> list[語]:
    """1 行 1 語・# から後は注・空の行と重なりは落とす。"""
    out: list[語] = []
    seen: set[str] = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        w = line.split("#", 1)[0].strip()
        if w and w not in seen:
            seen.add(w)
            out.append(語(w))
    return out


def 語たち(字たち) -> list[語]:
    """試験の作り物の語（字の並び）を 語 にする。"""
    return [w if isinstance(w, 語) else 語(w) for w in 字たち]
