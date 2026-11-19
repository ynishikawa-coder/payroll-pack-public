"""項目の辞書（初期設定/項目.json）の選べる値の字と、芯・出口が読む字（芯/設定の表.json・出口/形.py・芯/計算/承知.py）が食い違えば赤。

辞書の選べる値は人が読む字（後ろの（…）は説明）で、芯の表は芯が照らす字。辞書のとおりに書いた値が芯の照らしで外れると、
その会社の全員が仮になり出口が止まる（前は `手当の行ごとに 欠勤で減る`・`60進（h:mm）`・承知できる線の一覧の抜けで起きた）。
同じ物を 2 か所に持つ代わりに、ここで全部の項目を照らす（辞書の字 ⇔ 芯の字が 1 字でも違えば赤）。
"""
import json
from pathlib import Path

import pytest

from 出口 import 形 as 出口の形
from 芯 import 設定
from 芯.計算 import 承知

根 = Path(__file__).resolve().parents[2]
辞書 = {it["項目"]: it for it in json.loads((根 / "初期設定" / "項目.json").read_text(encoding="utf-8"))["項目"]}


def 片に分ける(字: str, 区切り: str = "・") -> list[str]:
    """括弧（…）・`…` の中の区切りでは切らない（`長さで（6 時間超 45 分・8 時間超 60 分）` は 1 つ）。"""
    out, 今, 深さ, 引用 = [], "", 0, False
    for c in 字:
        if c == "`":
            引用 = not 引用
        elif c == "（" and not 引用:
            深さ += 1
        elif c == "）" and not 引用:
            深さ -= 1
        if c == 区切り and 深さ == 0 and not 引用:
            out.append(今)
            今 = ""
        else:
            今 += c
    out.append(今)
    return [x.strip() for x in out if x.strip()]


def 片を読む(片: str, 値たち: set[str]) -> str | None:
    """辞書の 1 つの片 → 芯の字（当たらなければ None）。そのままか、後ろの（…）の説明を外した頭が芯の字なら当たり。"""
    s = 設定.揃える(片)
    while s:
        if s in 値たち:
            return s
        if not s.endswith("）"):
            return None
        深さ = 0   # 後ろの釣り合った（…）を 1 つ外す（値そのものが（…）を持つ `所定の始業から（時給の人は所定内）（説明）` も読む）
        for i in range(len(s) - 1, -1, -1):
            深さ += {"）": 1, "（": -1}.get(s[i], 0)
            if 深さ == 0:
                s = s[:i]
                break
        else:
            return None
    return None


def _選ぶ項目():
    return [(n, e) for n, e in sorted(設定.表().items()) if e["形"] in ("選ぶ", "区分") and n in 辞書]


@pytest.mark.parametrize("名,e", _選ぶ項目(), ids=[n for n, _ in _選ぶ項目()])
def test_選ぶ項目の辞書の字は芯の字と同じ(名, e):
    値たち = {設定.揃える(x) for x in e["選べる値"]}
    片たち = 片に分ける(str(辞書[名]["選べる値"]))
    外 = [x for x in 片たち if 片を読む(x, 値たち) is None]
    assert not 外, f"{名}: 辞書の選べる値の片 {外} が 芯/設定の表.json の選べる値 {e['選べる値']} に無い"
    抜け = 値たち - {片を読む(x, 値たち) for x in 片たち}
    assert not 抜け, f"{名}: 芯/設定の表.json の選べる値 {sorted(抜け)} が辞書の選べる値に無い（辞書へ足す）"


def test_組の項目の辞書の字は芯の欄の字と同じ():
    for 名, e in sorted(設定.表().items()):
        if e["形"] != "組" or 名 not in 辞書:
            continue
        組たち = [片に分ける(x) for x in str(辞書[名]["選べる値"]).split("／")]
        欄たち = list(e["欄"])
        for 組 in 組たち:
            assert len(組) == len(欄たち), (名, 組)
            for 欄, 字 in zip(欄たち, 組):
                assert 片を読む(字, {設定.揃える(x) for x in e["欄"][欄]}), (名, 欄, 字)
        for i, 欄 in enumerate(欄たち):
            assert {設定.揃える(組[i]) for 組 in 組たち} == {設定.揃える(x) for x in e["欄"][欄]}, (名, 欄)


def test_端数の語の項目の辞書の字は芯が読める():
    for 名, e in sorted(設定.表().items()):
        if e["形"] != "端数の語" or 名 not in 辞書:
            continue
        for 片 in 片に分ける(str(辞書[名]["選べる値"])):
            頭 = 片.split("（", 1)[0] if 片.endswith("）") and not 設定.選べる値の字か(名, 片) else 片
            assert 設定.選べる値の字か(名, 頭), f"{名}: 辞書の選べる値の片「{片}」を芯が端数の語として読めない"


def test_出口の時間の書き方は辞書の字のとおりに読む():
    片たち = 片に分ける(str(辞書["出口.時間の書き方"]["選べる値"]))
    assert 片たち
    for 片 in 片たち:
        w = 出口の形._書き方(片)
        assert w in 出口の形.時間の書き方たち and 片.startswith(w), 片
    assert 出口の形._書き方(辞書["出口.時間の書き方"]["既定"]) == "60進"
    with pytest.raises(ValueError):
        出口の形._書き方("12進（h.hh）")   # 外の字は今までどおり止める


def test_承知できる線の一覧は芯の承知できる線と同じ():
    字 = str(辞書["法の線.承知"]["選べる値"])
    頭, 印, 並び = 字.partition("線の名は ")
    assert 印, "法の線.承知 の選べる値に「線の名は 」の後ろの一覧が無い"
    assert 片に分ける(並び) == list(承知.承知できる線), "法の線.承知 の一覧は 芯/計算/承知.py の 承知できる線 と同じ順・同じ字で書く"


def test_照らしは食い違いを赤にする():
    """照らしが空回りしていない（前の字は外れと読む）。"""
    値たち = {設定.揃える(x) for x in 設定.表()["欠勤.控除の基礎"]["選べる値"]}
    assert 片を読む("手当の行ごとに `欠勤で減る`", 値たち) is None
    assert 片を読む("手当の行ごと（行の `欠勤で減る` で決める）", 値たち) == "手当の行ごと"
    assert 片に分ける("長さで（6 時間超 45 分・8 時間超 60 分）・実績") == ["長さで（6 時間超 45 分・8 時間超 60 分）", "実績"]
