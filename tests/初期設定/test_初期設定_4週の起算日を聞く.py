"""`休日.法定休日の決め方` を字だけ（`4週4休`）で書いても、項目の辞書の書き方（`4 週 4 休（起算日つき）`）と同じに読み、起算日を聞く。"""
import importlib.util
from pathlib import Path

根 = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("初期設定_始める_4週の起算日", 根 / "初期設定" / "始める.py")
始める = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(始める)


def _起算日を聞くか(書き方):
    入力 = {"会社の値": {"休日.法定休日の決め方": 書き方}}
    return any(q["項目"] == "休日.4週の起算日" for q in 始める.足りない値(入力))


def test_どの書き方でも起算日を聞く():
    for 書き方 in ("4 週 4 休（起算日つき）", "4週4休", "4 週 4 休"):
        assert _起算日を聞くか(書き方), 書き方


def test_曜日で決める会社には聞かない():
    assert not _起算日を聞くか("曜日を決める")
