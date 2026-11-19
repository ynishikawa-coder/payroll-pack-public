"""有給の月の比べ（有給/有給.py `_月`）は正本（芯/支給月の字.py）で読み、読めない字は止める
（前は読めない字をそのまま比べ、その月の取得から黙って外していた）。"""
import importlib.util
from pathlib import Path

import pytest

_p = Path(__file__).resolve().parents[2] / "有給" / "有給.py"
_s = importlib.util.spec_from_file_location("有給_支給月の字", _p)
有給 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(有給)


@pytest.mark.parametrize("字", ["2026.11支給", "2026-11", "2026/11", "2026年11月"])
def test_受ける字は同じ月(字):
    assert 有給._月(字, "試験") == "2026-11"


@pytest.mark.parametrize("字", ["", None, "来月", "2026.13支給"])
def test_読めない字は止める(字):
    with pytest.raises(ValueError):
        有給._月(字, "試験")
