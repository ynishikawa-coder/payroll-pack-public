"""drive口/_google.py の _実行: 429（打ちすぎ）・5xx は待って打ち直し、上限で頭打ち・回数で止まる。ほかの赤はすぐ上げる。
本物の Google には触らない（頼みの作り物で照らす）。"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from drive口 import _google  # noqa: E402


class _赤(Exception):
    def __init__(self, 状態):
        super().__init__(f"作り物の赤 {状態}")
        self.resp = SimpleNamespace(status=状態)


class _頼み:
    def __init__(self, 赤たち, 値="済"):
        self.赤たち, self.値, self.打った = list(赤たち), 値, 0

    def execute(self):
        self.打った += 1
        if self.赤たち:
            raise self.赤たち.pop(0)
        return self.値


def test_429は待って打ち直し_通れば値を返す():
    眠り = []
    r = _頼み([_赤(429), _赤(429), _赤(503)])
    assert _google._実行(r, 眠る=眠り.append) == "済"
    assert r.打った == 4 and 眠り == [1, 2, 4]


def test_429が続けば上限で頭打ちして6回で上限の赤で止める():
    """読む頼み: 尽きたら drive口.上限（訳に「上限」・元の赤でない）。"""
    import drive口
    眠り = []
    r = _頼み([_赤(429)] * 10)
    with pytest.raises(drive口.上限, match="上限"):
        _google._実行(r, 眠る=眠り.append)
    assert r.打った == 6 and 眠り == [1, 2, 4, 8, 16]
    assert max(眠り) <= _google._待つ上限
    assert issubclass(drive口.上限, Exception)   # 書く流れの中の読みでも使う側の except Exception が知らせを残せる


def test_書く頼みで429が尽きたら上限で書けないで止める():
    """書く頼み: 尽きたら 上限で書けない（上限の子・訳に「上限」と「書けていない」）。"""
    import drive口
    r = _頼み([_赤(429)] * 10)
    with pytest.raises(drive口.上限で書けない, match="上限"):
        _google._実行(r, 眠る=lambda s: None, 書く=True)
    assert r.打った == 6


def test_5xxが尽きたら元の赤を上げる_上限と言わない():
    r = _頼み([_赤(503)] * 10)
    with pytest.raises(_赤):
        _google._実行(r, 眠る=lambda s: None)
    assert r.打った == 6


@pytest.mark.parametrize("状態", [403, 404, 400])
def test_打ち直さない赤はすぐ上げる(状態):
    眠り = []
    r = _頼み([_赤(状態)])
    with pytest.raises(_赤):
        _google._実行(r, 眠る=眠り.append)
    assert r.打った == 1 and 眠り == []


def test_状態の無い赤も打ち直さず上げる():
    r = _頼み([ValueError("作り物")])
    with pytest.raises(ValueError):
        _google._実行(r, 眠る=lambda s: None)
    assert r.打った == 1


@pytest.mark.parametrize("状態", [500, 502, 503, 504])
def test_二つできる頼みは5xxで打ち直さず_429だけ打ち直す(状態):
    """values.append・files.create は 2 回届けば 2 つできる＝5xx（書けたか分からない）では打ち直さず上げる。"""
    r = _頼み([_赤(状態)])
    with pytest.raises(_赤):
        _google._実行(r, 眠る=lambda s: None, 二つできる=True)
    assert r.打った == 1
    眠り = []
    r = _頼み([_赤(429), _赤(429)])
    assert _google._実行(r, 眠る=眠り.append, 二つできる=True) == "済"
    assert r.打った == 3 and 眠り == [1, 2]


def test_表へ足すとファイルを作るは二つできる頼みとして打つ():
    """表へ足す（values.append）・ファイルを置く・シートを作る（files.create）・行を消す（deleteDimension）が 二つできる で
    _実行 を呼ぶ（書き先で照らす）。"""
    import inspect
    字 = inspect.getsource(_google)
    assert 字.count("二つできる=True") == 4
