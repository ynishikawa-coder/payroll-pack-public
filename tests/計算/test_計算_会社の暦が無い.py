"""会社の暦（時間.暦）が無い人: 土日祝が休みで見当して仮＋問い 1 つ（黙って決めない。作り物の 1 人）。"""
from 作る_計算 import 回す, 決まり

問い = "「時間.暦」が無い"


def _問い(r):
    return [q["何が無いか"] for q in r["問い"]]


def test_暦で所定日数を数える人は暦が無ければ仮と問い(tmp_path):
    決 = {k: v for k, v in 決まり().items() if k != "時間.暦"}   # 既定の 年平均＝暦から数える
    r = 回す(tmp_path, 決=決)
    assert r["人"][0]["状態"] == "仮" and _問い(r).count(問い) == 1


def test_固定の値で数える人は暦が無くても仮にしない(tmp_path):
    決 = {k: v for k, v in 決まり(**{"時間.月の所定日数の出し方": "固定の値", "時間.月の所定日数": "20",
                                  "時間.月の所定時間の出し方": "固定の値", "時間.月の所定時間": "160"}).items() if k != "時間.暦"}
    r = 回す(tmp_path, 決=決)
    assert 問い not in _問い(r)


def test_暦があれば今までどおり(tmp_path):
    assert 問い not in _問い(回す(tmp_path))
