"""シフトの型（時間.暦＝{"シフト": "勤務した日"}）の人は働いた日が全部 勤務＝休日の足りない週は法定休日の労働の日が決まらない＝仮。"""
from datetime import date, timedelta

from 作る_集計 import 区, 数える, 既定の決まり, 日


def _月(休む日):
    A, B = [], []
    for i in range(30):
        s = (date(2026, 11, 1) + timedelta(days=i)).isoformat()
        if s in 休む日:
            A.append(日(s, "休日", 勤務の型="シフト"))
        else:
            A.append(日(s, 勤務の型="シフト"))
            B += [区(s, 1, "9:00", "17:00"), 区(s, 2, "12:00", "13:00", "休憩")]
    return A, B


def _決(**足す):
    return 既定の決まり(**{"時間.週の起算": "日", "勤務の型": {"シフト": {"時間.暦": {"シフト": "勤務した日"}}}, **足す})


def test_週に休日が在れば仮にしない():
    休む = {(date(2026, 11, 1) + timedelta(days=7 * w + 3)).isoformat() for w in range(5)}
    x = 数える(*_月(休む), _決())
    assert x["人"][0]["状態"] == "確認済", x["問い"]


def test_休日の無い週の勤務の日は仮():
    休む = {(date(2026, 11, 1) + timedelta(days=7 * w + 3)).isoformat() for w in range(5) if w != 1}
    x = 数える(*_月(休む), _決())
    assert x["人"][0]["状態"] == "仮"
    (q,) = [q for q in x["問い"] if "シフトの人" in q["何が無いか"]]
    assert q["日付"][0] == "2026-11-08" and len(q["日付"]) == 7


def test_シフトでない型の人は見ない():
    A, B = _月(set())
    A = [dict(a, 勤務の型="") for a in A]
    x = 数える(A, B, 既定の決まり(**{"時間.週の起算": "日"}))
    assert not [q for q in x["問い"] if "シフトの人" in q["何が無いか"]]
