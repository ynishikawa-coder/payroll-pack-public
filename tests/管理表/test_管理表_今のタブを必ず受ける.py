"""立ち上げ は今のタブ（管理表の全部のタブ）を必ず受ける。省く・空・形の違う時は止める（注入の試験）。作り物だけ。

根（2026-11-19）: 出す物の版・問いの番号と同じ原因＝`今のタブ` の既定が空で、渡さないと在るタブを無いと読んで
「タブを足す」を返した（窓が当てると同じ名のタブがぶつかる・前の版の値の上に見出しを置く）。
"""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("管理表_試験_今のタブ", Path(__file__).resolve().parents[2] / "管理表" / "管理表.py")
管理表 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(管理表)


@pytest.mark.parametrize("入力", [{}, {"今のタブ": None}, {"今のタブ": {}}, {"今のタブ": []}, {"今のタブ": "月の状況"}])
def test_今のタブを渡さなければ足す手順を返さず止める(入力):
    with pytest.raises(管理表.拒む, match="今のタブ"):
        管理表.立ち上げ(入力)


@pytest.mark.parametrize("値", [None, "月の状況", {"会社": "x"}, [{"会社": "x"}]])
def test_タブの値が行の並びでなければ止める(値):
    with pytest.raises(管理表.拒む, match="行の並び"):
        管理表.立ち上げ({"今のタブ": {"シート1": [], "月の状況": 値}})


def test_値の無いタブは空の並びで渡せば見出しを置く():
    月 = 管理表.Driveのタブ("月の状況")
    手順 = 管理表.立ち上げ({"今のタブ": {月: []}})
    assert {"する": "行を足す", "タブ": 月}.items() <= 手順[0].items()
    assert all(x["タブ"] != 月 or x["する"] != "タブを足す" for x in 手順)


def _会社の今の値():
    return [管理表.見出し("会社")]


@pytest.mark.parametrize("版", ["省く", None, "", "十一", "３２", -1, True, 1.5])
def test_会社の行は型の版を数で渡さなければ0と書かず止める(版):
    c = {"会社": "作り物A", "組": "作り物の組"}
    if 版 != "省く":
        c["型の版"] = 版
    with pytest.raises(管理表.拒む, match="型の版 を数で渡す"):
        管理表.会社の行({"今の値": _会社の今の値(), "会社の一覧": [c]})


def test_会社の行は渡した型の版を書く():
    h = 管理表.見出し("会社")
    for 版 in (32, "32"):
        手順 = 管理表.会社の行({"今の値": [h], "会社の一覧": [{"会社": "作り物A", "組": "作り物の組", "型の版": 版}]})
        assert dict(zip(h, 手順[0]["値"]))["型の版"] == "32"
