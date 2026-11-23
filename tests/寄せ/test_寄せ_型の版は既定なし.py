"""寄せの入力の 型の版 は既定を持たない（作り物の値だけ）。

前: 型の版 が無い入力を 0（前の道具の形）と読み、今の型で書いた会社に前の道具からの直しを全部当てた。
後: 型の版 が無い・空なら止める。前の道具の形は 0 を明示で渡せば今までどおり受ける。
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "道具" / "寄せ"))

import 当てる  # noqa: E402

シート = {"2_マスタ": {"社員": [["NO", "氏名"], ["0001", "作り物 一"]]}}


@pytest.mark.parametrize("入力", [{}, {"型の版": None}, {"型の版": ""}, {"型の版": " "}])
def test_型の版が無ければ止める(入力):
    with pytest.raises(ValueError, match="型の版"):
        当てる.物({"会社": "作り物の会社", "シート": シート, **入力})


@pytest.mark.parametrize("版, 読み", [(0, 0), ("0", 0), (33, 33), ("33", 33)])
def test_型の版を明示で渡せば受ける_0は前の道具の形(版, 読み):
    assert 当てる.物({"会社": "作り物の会社", "型の版": 版, "シート": シート}).版 == 読み
