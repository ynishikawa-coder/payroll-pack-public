"""支給控除の項目の列（項目.行）の字が選べる値の外・必ず書く列が空でも、黙って既定へ倒さず仮＋問いにする（作り物の値だけ）。

前は 欠勤で減る「減らないです」が 減る と数えられ（欠勤控除に入る）、課税「非課税です」が 課税 と数えられ、
支給か控除 が空の行は支給にも控除にも入らず黙って落ちていた。今は 芯/設定.部品の行を照らす が 芯/支給控除の列.json で照らし、
その会社の人を仮＋問いにする ⟦鍵:給与計算/足りない時は仮で計算し出さない⟧（仮の人は出口へ出ない）。
"""
import json
from pathlib import Path

import pytest
from 作る_計算 import 回す, 決まり

from 芯 import 設定

根 = Path(__file__).resolve().parents[2]


def _問い(r):
    return [q["何が無いか"] for q in r["問い"]]


def _行を変えて(名, **列):
    行たち = [dict(x) for x in 決まり()["項目.行"]]
    for x in 行たち:
        if x["名"] == 名:
            x.update(列)
    return 決まり(**{"項目.行": 行たち})


@pytest.mark.parametrize(("名", "列", "字"), [
    ("通勤手当", "欠勤で減る", "減らないです"),
    ("職務手当", "課税", "非課税です"),
    ("職務手当", "割増の基礎", "入らない（作り物）"),
    ("職務手当", "日割する", "はい"),
    ("親睦会費", "支給か控除", "引く"),
])
def test_選べる値の外の字は仮と問い(tmp_path, 名, 列, 字):
    r = 回す(tmp_path, 決=_行を変えて(名, **{列: 字}))
    assert r["人"][0]["状態"] == "仮"
    assert [q for q in _問い(r) if q.startswith(f"支給控除の項目「{名}」の {列}「{字}」")]


def test_支給か控除が空の行は黙って落とさず仮(tmp_path):
    r = 回す(tmp_path, 決=_行を変えて("職務手当", 支給か控除=""))
    assert r["人"][0]["状態"] == "仮"
    assert [q for q in _問い(r) if q.startswith("支給控除の項目「職務手当」の 支給か控除")]


def test_字の揺れは吸って仮にしない(tmp_path):
    r = 回す(tmp_path, 決=_行を変えて("通勤手当", 欠勤で減る=" 減らない ", 課税="通勤の非課税"))
    assert r["人"][0]["状態"] == "確認済" and _問い(r) == []


def test_読まない列でも外の字は仮(tmp_path):
    r = 回す(tmp_path, 決=_行を変えて("親睦会費", **{"24条協定": "多分ある"}))
    assert r["人"][0]["状態"] == "仮"


def test_型の意味は選べる値を全部書く():
    # 初期設定/型.json（事務所が書く表の説明）と 芯/支給控除の列.json（芯が照らす正本）が食い違わない
    型 = json.loads((根 / "初期設定" / "型.json").read_text(encoding="utf-8"))
    タブ = next(t for s in 型["シート"] for t in s.get("タブ", ()) if isinstance(t, dict) and t.get("タブ") == "支給控除の項目")
    意味 = {c["名"]: c["意味"] for c in タブ["列"]}
    for 列, e in 設定.部品の列().items():
        assert 列 in 意味, f"型.json の 支給控除の項目 に列 {列} が無い"
        for 字 in e["選べる値"]:
            assert 字 in 意味[列], f"型.json の {列} の意味に選べる値「{字}」が無い"
