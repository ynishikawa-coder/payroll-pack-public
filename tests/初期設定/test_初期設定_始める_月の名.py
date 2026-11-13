"""始める の置き場の（M月分）が会社の `支払.支給の月` から出ること（確認ページの名と同じ 1 か所の式）。作り物の会社だけ。"""
import importlib.util
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("初期設定_始める_月の名", 根 / "初期設定" / "始める.py")
始める = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(始める)


def _入力(**会社の値):
    return {"会社": "作り物の会社", "組": "作り物の組", "最初の支給月": "2099.04支給", "今日": "2099-03-01",
            "会社の値": {k: {"値": v, "書類の名": "書類_2099-03-01_作り物"} for k, v in 会社の値.items()}}


@pytest.mark.parametrize("支給の月, 月分", [("当月", 4), ("翌月", 3), ("翌々月", 2), (None, 3)])
def test_始めるの置き場は会社の支給の月で月分を出す(支給の月, 月分):
    r = 始める.始める(_入力(**({"支払.支給の月": 支給の月} if 支給の月 else {})))
    月 = f"2099.04支給（{月分}月分）"
    assert f"10_会社/作り物の組/10_月ごと/{月}/01_原本" in r["置き場"]
    assert f"10_会社/作り物の組/20_配る物/{月}" in r["置き場"]
    assert r["知らせ"] == []   # 無ければ項目の既定（翌月）＝知らせは要らない
    assert 月 == 始める.確認ページ.支給月の名("2099.04支給", 支給の月)


def test_始めるの支給の月が読めない時は翌月で知らせる():
    r = 始める.始める(_入力(**{"支払.支給の月": "来月"}))
    assert "10_会社/作り物の組/20_配る物/2099.04支給（3月分）" in r["置き場"]
    assert len(r["知らせ"]) == 1 and "読めない" in r["知らせ"][0]
