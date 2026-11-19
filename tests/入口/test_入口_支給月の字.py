"""入口の側の支給月の字は正本（芯/支給月の字.py の 字にする）から作る: 殻の字を渡すと入口の文脈の 支給月 は `YYYY-MM`。
入口の文脈・段の解決は字を自前で組まない＝正本の字の組み方がずれれば、この試験と出口の試験（test_出口_支給月の字）が同時に赤。"""
import importlib.util
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
if str(根) not in sys.path:
    sys.path.insert(0, str(根))
from 芯 import 支給月の字  # noqa: E402

_spec = importlib.util.spec_from_file_location("入口_支給月の字_文脈", 根 / "初期設定" / "入口の文脈.py")
文脈 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(文脈)
段 = 文脈.段


@pytest.mark.parametrize("字", ["2026.11支給", "2026.11", "2026-11", "2026/11", "2026年11月", "2026年11月支給", "２０２６．１１支給"])
def test_受ける字は全部_入口の字_YYYY_MM_になる(字):
    assert 段.月(字, "中") == "2026-11"
    assert 段.月(字) == "2026.11"
    assert 段.月(字, "殻") == "2026.11支給"


@pytest.mark.parametrize("字", ["", "2026.13支給", "2026.00", "26.11支給", "2026-11-賞与", "十一月"])
def test_読めない字は止める(字):
    with pytest.raises(段.段の誤り):
        段.月(字, "中")


def test_入口の文脈の支給月は正本の字():
    x = 文脈.入口の文脈("2026.11支給", "作り物の会社", {"決まり": {}, "人": {}})
    assert x["文脈"]["支給月"] == "2026-11" == 支給月の字.字にする(2026, 11)


def test_前と次の月は年をまたぐ():
    assert 支給月の字.ずらす("2027.01支給", -1, "殻") == "2026.12支給"
    assert 支給月の字.ずらす("2026-12", 1) == "2027-01"


def test_形がちょうど同じ字だけその形とみなす():
    assert 支給月の字.その形か("2026.11支給", "殻") and not 支給月の字.その形か("2026.1支給", "殻")
    assert not 支給月の字.その形か("2026.11支給\n", "殻") and not 支給月の字.その形か(" 2026-11", "中")
    assert 支給月の字.殻の字へ("2026-11") == "2026.11支給" and 支給月の字.殻の字へ("2026.11支給") == "2026.11支給"
