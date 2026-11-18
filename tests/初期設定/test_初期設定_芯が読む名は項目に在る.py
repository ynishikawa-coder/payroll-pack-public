"""芯が読む会社の決まりの名（芯/設定の表.json）は、全部 項目の辞書（初期設定/項目.json）に在る。

辞書に無い名は、マスタの変更の記録の 項目 に書くと段の解決が「今の項目に無い名」と読んでその人を仮にし、寄せも項目の名と読めない
（手当.通勤の限度を超えた分の行 が辞書に無かった）。辞書の外に置いてよいのは 2 つだけ:
- 社員の決まった列を段の解決が名を替えて渡す名（段の解決.社員の列の名 の値＝その表を直に読む）
- 芯/設定の表.json の 項目の外 に訳を書いた名（段の解決が作る鍵・まだマスタに列が無い名）
"""
import importlib.util
import json
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("初期設定_段の解決_芯が読む名", 根 / "初期設定" / "段の解決.py")
段 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(段)


def _表():
    return json.loads((根 / "芯" / "設定の表.json").read_text(encoding="utf-8"))["項目"]


def _辞書():
    return {it["項目"] for it in json.loads((根 / "初期設定" / "項目.json").read_text(encoding="utf-8"))["項目"]}


def 辞書に無い名(表: list[dict], 辞書: set[str]) -> list[str]:
    """芯が読むのに辞書に無く、訳も無い名。"""
    社員の列 = set(段.社員の列の名.values())
    return sorted(e["名"] for e in 表 if e["名"] not in 辞書 and e["名"] not in 社員の列 and not e.get("項目の外"))


def test_芯が読む名は全部項目の辞書に在る():
    assert 辞書に無い名(_表(), _辞書()) == [], "芯/設定の表.json の名を 初期設定/項目.json に足す（足せない訳があれば 項目の外 に書く）"


def test_項目の外の訳の名は辞書に無い():
    """辞書に入った名の 項目の外 は消す（訳が古いまま残らない）。"""
    assert not {e["名"] for e in _表() if e.get("項目の外")} & _辞書()


def test_人ごとの支給控除の行の束は辞書に在る():
    """段の解決が人ごとの支給控除の 項目 として受ける名（人の行の束）も辞書に在る（変更の記録・寄せが名と読める）。"""
    assert set(段.人の行の束) <= _辞書()


@pytest.mark.parametrize("名", ["手当.通勤の限度を超えた分の行", "雇保.本人負担率", "社保.支援金を健保に含める"])
def test_辞書に無い名を入れると赤(名):
    """注入: 辞書からその名を抜くと見つける（照らしが空回りしていない）。"""
    assert 辞書に無い名(_表(), _辞書() - {名}) == [名]


def test_訳の無い新しい名を表に足すと赤():
    assert 辞書に無い名(_表() + [{"名": "作り物.新しい決まり", "形": "字"}], _辞書()) == ["作り物.新しい決まり"]

