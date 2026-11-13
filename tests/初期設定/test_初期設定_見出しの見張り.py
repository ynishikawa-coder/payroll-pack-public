"""見張り: 型から出す見出しの並びが黙って変わらない。

型を直した時は、型.json の版を上げ、道具/寄せ/直し/ に直しを置き、この写し（見出しの並び.json）も同じ PR で直す。
"""
import importlib.util
import json
from pathlib import Path

ここ = Path(__file__).resolve().parent
根 = ここ.parent.parent
_spec = importlib.util.spec_from_file_location("初期設定_型の口_試験", 根 / "初期設定" / "型の口.py")
口 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(口)


def _写し(名):
    return json.loads((ここ / 名).read_text(encoding="utf-8"))


def test_シートの見出しの並びが写しと同じ():
    写し = _写し("見出しの並び.json")
    assert 口.版() == 写し["版"]
    assert 口.全部の見出し() == 写し["見出し"]


def test_md_の雛形の見出しが写しと同じ():
    写し = _写し("md_の見出しの並び.json")
    assert 口.全部の_md_の見出し() == 写し["md"]


def test_組のシートの全タブの1列目は会社():
    for 鍵, 見出し in 口.全部の見出し().items():
        if not 鍵.startswith("事務所の設定/"):
            assert 見出し[0] == "会社", 鍵
    for 鍵, 見出し in 口.全部の見出し().items():
        if 鍵.startswith("04_台帳_"):
            assert 見出し[1] == "支給月", 鍵
