"""締めた時の版は記録で、止めではない（2026-11-25 オーナー: 確定した勤怠は台帳に在り版が上がっても壊れない）。

月を回す は、締めの記録の パックの版（締めた時の版）が今のパックの版と違っても・空でも・行で割れていても回し、
証明に締めた時の版（`締めた時の版`）と計算した版（`パックの版`）の両方を残し、違えば知らせ「締めた時の版」に出す。注入の試験。
"""
import pytest

import test_月次 as 月
from 出口 import 証明


def _締め(版たち: dict[str, str]):
    import 月次
    return [list(月次.勤怠の照らし.締めの列), *[[月.C, 月.支給月, NO, "", "締まった", "", "", 版] for NO, 版 in 版たち.items()]]


def _回す(tmp_path, 締め):
    return 月._回す(tmp_path, 締めの記録=締め)[2]


def test_締めた時の版と今の版が同じなら知らせずに回す(tmp_path):
    今 = 証明.パックの版()
    o = _回す(tmp_path, _締め({NO: 今 for NO in 月.人たち}))
    assert o["証明"] and o["知らせ"]["締めた時の版"] == []
    assert {str(p["締めた時の版"]) for p in o["証明"].values()} == {str({"版たち": [今], "版の無い行": 0})}


@pytest.mark.parametrize("版たち, 締めた版, 知らせ", [
    (lambda 今, 人: {NO: "v0.0.1" for NO in 人}, lambda 今, n: {"版たち": ["v0.0.1"], "版の無い行": 0}, ["版 v0.0.1 で締めた行"]),
    (lambda 今, 人: {NO: "" for NO in 人}, lambda 今, n: {"版たち": [], "版の無い行": n}, ["版が空の行"]),
    (lambda 今, 人: {NO: (今 if i else "v0.0.1") for i, NO in enumerate(人)},
     lambda 今, n: {"版たち": sorted({今, "v0.0.1"}), "版の無い行": 0}, ["版 v0.0.1 で締めた行"]),
])
def test_締めた時の版が今と違っても回し証明に両方の版を残す(tmp_path, 版たち, 締めた版, 知らせ):
    今, 人 = 証明.パックの版(), sorted(月.人たち)
    o = _回す(tmp_path, _締め(版たち(今, 人)))
    assert o["証明"], "締めた版が違っても止めない"
    for p in o["証明"].values():
        assert p["締めた時の版"] == 締めた版(今, len(人)) and p["パックの版"] == 今
    assert [x for x in o["知らせ"]["締めた時の版"] if any(k in x for k in 知らせ)], o["知らせ"]["締めた時の版"]


def test_ほかの月の締めの版は読まない(tmp_path):
    今 = 証明.パックの版()
    締め = _締め({NO: 今 for NO in 月.人たち}) + [[月.C, "2000.01支給", "0001", "", "締まった", "", "", "v0.0.1"]]
    assert {p["締めた時の版"]["版たち"] == [今] for p in _回す(tmp_path, 締め)["証明"].values()} == {True}


def test_月の証明は締めた時の版を欠いて作れず照らしも通らない(tmp_path):
    o = _回す(tmp_path, _締め({NO: 証明.パックの版() for NO in 月.人たち}))
    物, p = next(iter(o["証明"].items()))
    d = next(x for x in [o.get("取り込み"), *(o.get("支給控除一覧") or ()), o.get("有給休暇管理表")] if x is not None and x.物 == 物)
    with pytest.raises(ValueError, match="締めた時の版"):
        証明.証明を付ける(d, 会社=p["会社"], 支給月=p["支給月"], 回="月", 外した人=0,
                     例の結果={"通った": True, "数": 1}, 入力={})
    for 崩れ in (None, {}, {"版たち": [""], "版の無い行": 0}, {"版たち": "v0.0.1", "版の無い行": 0},
                {"版たち": [], "版の無い行": -1}, {"版たち": [], "版の無い行": True}):
        r = 証明.照らす(d, {**p, "締めた時の版": 崩れ}, 入力={})
        assert not r["通す"] and any("締めた時の版" in x for x in r["赤"]), 崩れ
