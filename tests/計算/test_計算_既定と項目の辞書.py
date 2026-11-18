"""芯の既定（芯/計算/要る値.py の 既定）と、項目の辞書の既定（初期設定/項目.json＝正本）が食い違えば赤。

芯は初期設定を読まない（層: 初期設定 → 芯 の向きだけ）。芯は辞書の既定を芯の読む形で持ち、ここで辞書と照らす。
字は芯が読む時と同じ揃え方（形.語をそろえる＝空白・切り捨て の字の揺れ）で比べる。
芯の既定が dict の項目（休日.休日出勤の数え方）は、辞書の既定の「・」で区切った語の並びと照らす。
"""
import json
from pathlib import Path

from 芯.計算.形 import 語をそろえる
from 芯.計算.要る値 import 既定

辞書 = {it["項目"]: it for it in json.loads(
    (Path(__file__).resolve().parents[2] / "初期設定" / "項目.json").read_text(encoding="utf-8"))["項目"]}

# 辞書に項目が無く、芯だけが既定を持つ項目＝芯/設定の表.json の 項目の外 に訳を書いた名（訳の正本はその 1 か所）
芯だけ = {e["名"]: e["項目の外"] for e in json.loads(
    (Path(__file__).resolve().parents[2] / "芯" / "設定の表.json").read_text(encoding="utf-8"))["項目"] if e.get("項目の外")}


def _芯の字(v) -> str:
    return "・".join(v.values()) if isinstance(v, dict) else str(v)


def test_芯の既定は辞書の既定と同じ():
    違う = []
    for 名, v in 既定.items():
        if 名 in 芯だけ:
            continue
        assert 名 in 辞書, f"{名} が 初期設定/項目.json に無い（芯/設定の表.json の 項目の外 に訳を書くか辞書へ足す）"
        辞 = 辞書[名].get("既定")
        if 辞 is None or 語をそろえる(_芯の字(v)) != 語をそろえる(辞):
            違う.append(f"{名}: 芯={_芯の字(v)!r} 辞書={辞!r}")
    assert not 違う, "芯の既定と項目.json の既定が違う（項目.json が正本。芯/計算/要る値.py を合わせる）:\n" + "\n".join(違う)


def test_芯だけの既定は辞書に無い():
    assert not set(芯だけ) & set(辞書), "辞書に入ったので 芯/設定の表.json の 項目の外 を消し、上の照らしに入れる"


def test_照らしは食い違いを赤にする():
    """照らしが空回りしていない（辞書の字を 1 つ変えると違うと読む）。"""
    assert 語をそろえる("50 銭以下切捨て") != 語をそろえる(既定["社保.端数"])
    assert 語をそろえる("居住者（日本に住む）") != 語をそろえる(既定["源泉.住む所"])
