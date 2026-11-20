"""字のそろえ方の正本（字の揺れをそろえてから意味を決める所は、全部ここを通す。層ごとに そろえ方を組まない）。

なぜ在るか（根治・2026-11-20・台帳の束 K3）: 名・頭の字・語で意味を決める所が、字のそのままの一致や startswith で照らしていた。
全角で書いた「課題：」・頭に空白のある本の名・幅の無い字（U+200B など）を挟んだ語・半角の括弧で書いた選択が、
当たらずに黙って通った（止めるべき物が止まらない・数えるべき物が数えられない）。そろえ方を 1 か所に置き、比べる両側を
同じ形にしてから比べる。

そろえ方（`そろえる`）: Unicode の NFKC（全角→半角・半角カナ→全角カナ・丸数字や合字をほどく）→ 書式の字（Cf: 幅の無い空白・
つなぎ・向きの印・BOM など）を消す → 空白（全角の空白も）を消す → （大小も なら）字の大小をそろえる（casefold）。
比べる時は両側を そろえる に通す（`同じ`・`頭が`・`含む`）。標準の道具だけ（芯の外を import しない＝plugin の照らしもパックの
場所からこれを読む）。
"""
from __future__ import annotations

import unicodedata


def そろえる(字, 大小も: bool = True, 空白も: bool = True) -> str:
    """字 → そろえた字。None は空の字。空白も=False は空白を 1 つの半角の空白にまとめて残す（語の切れ目を見る所）。"""
    s = "".join(c for c in unicodedata.normalize("NFKC", "" if 字 is None else str(字))
                if unicodedata.category(c) != "Cf")
    s = "".join(s.split()) if 空白も else " ".join(s.split())
    return s.casefold() if 大小も else s


def 同じ(a, b, 大小も: bool = True) -> bool:
    """2 つの字が、そろえると同じか（空どうしは同じでない＝空で当てない）。"""
    x = そろえる(a, 大小も)
    return bool(x) and x == そろえる(b, 大小も)


def 頭が(字, 頭たち, 大小も: bool = True) -> bool:
    """そろえた字が、そろえた頭たち（1 つの字か並び）のどれかで始まるか（空の頭では当てない）。"""
    s = そろえる(字, 大小も)
    return any(h and s.startswith(h) for h in (そろえる(x, 大小も) for x in _並び(頭たち)))


def 含む(字, 語たち, 大小も: bool = True) -> bool:
    """そろえた字が、そろえた語たち（1 つの字か並び）のどれかを含むか（空の語では当てない）。"""
    s = そろえる(字, 大小も)
    return any(w and w in s for w in (そろえる(x, 大小も) for x in _並び(語たち)))


def どれと同じか(字, 候補たち, 大小も: bool = True):
    """そろえると 字 と同じになる候補（元の字のまま返す）。無ければ None。2 つ以上に当たれば ValueError（見分けられない）。"""
    当たり = [c for c in _並び(候補たち) if 同じ(字, c, 大小も)]
    if len(当たり) > 1:
        raise ValueError(f"{字!r} がそろえると 2 つ以上の候補（{'・'.join(map(str, 当たり))}）と同じ＝見分けられない")
    return 当たり[0] if 当たり else None


def _並び(x) -> tuple:
    return (x,) if isinstance(x, str) else tuple(x or ())
