"""給与の決まり「月の途中で版を変えない」の機械の照らし（型の版 33）。

月を回す は、その会社・その支給月の締めの記録の パックの版（締めた時の版）が今のパックの版と同じ時だけ回す。
違う・空・行で割れる時は止める（どちらの版で出すかはオーナーが毎回決める・2026-11-19 オーナー）。注入の試験。
"""
import pytest

import test_月次 as 月
from 出口 import 証明


def _締め(版たち: dict[str, str]):
    import 月次
    return [list(月次.勤怠の照らし.締めの列), *[[月.C, 月.支給月, NO, "", "締まった", "", "", 版] for NO, 版 in 版たち.items()]]


def _回す(tmp_path, 締め):
    return 月._回す(tmp_path, 締めの記録=締め)


def test_締めた時の版と今の版が同じなら回す(tmp_path):
    今 = 証明.パックの版()
    o = _回す(tmp_path, _締め({NO: 今 for NO in 月.人たち}))[2]
    assert o["証明"], "同じ版なら止めない"


@pytest.mark.parametrize("版たち, 訳", [
    (lambda 今, 人: {NO: "v0.0.1" for NO in 人}, "締めた時の版 v0.0.1 と今のパックの版"),      # 前の版で締めた月を新しい版で回す
    (lambda 今, 人: {NO: "" for NO in 人}, "締めた時の版が無い行"),                          # 版の分からない締め（直し 33 の前）
    (lambda 今, 人: {NO: (今 if i else "v0.0.1") for i, NO in enumerate(人)}, "行で割れている"),  # 途中で版を上げて締め直した人が混ざる
])
def test_締めた時の版が今と違えば月を回さない(tmp_path, 版たち, 訳):
    with pytest.raises(ValueError, match=訳) as e:
        _回す(tmp_path, _締め(版たち(証明.パックの版(), sorted(月.人たち))))
    assert "オーナーに選択肢の画面で聞く" in str(e.value)


def test_ほかの月の締めの版は見ない(tmp_path):
    今 = 証明.パックの版()
    締め = _締め({NO: 今 for NO in 月.人たち}) + [[月.C, "2000.01支給", "0001", "", "締まった", "", "", "v0.0.1"]]
    assert _回す(tmp_path, 締め)[2]["証明"]
