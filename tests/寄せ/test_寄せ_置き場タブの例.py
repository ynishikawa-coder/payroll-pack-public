"""Drive の型 §8「置き場」タブの例（組で束ねた会社は会社ごとの行）を、本物の置き場の検査の口に通す試験。作り物の値だけ。

例の表は §8 の <!-- 例 --> の中から直に読む（写さない）。組の 1 行にまとめて会社を空にした行は、置き場の検査の項目 6 が赤にする
（列「会社」は §1 のとおり全部のタブで空にしない）＝型と紙の例が食い違わない（台帳 2026-11-20・PR #279 のレビュー）。
"""
import datetime as dt
import re
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent
根 = ここ.parent.parent
sys.path.insert(0, str(根 / "道具" / "寄せ"))

import 当てる  # noqa: E402
import 見回り  # noqa: E402

紙 = 根 / "docs" / "設計" / "Drive の型.md"


def 例の表() -> list[list[str]]:
    """§8 の <!-- 例 --> の中の表（見出しの行を頭に）。"""
    text = 紙.read_text(encoding="utf-8")
    節 = re.search(r"^## 8\..*?(?=^## 9\.)", text, re.M | re.S).group(0)
    例 = re.search(r"<!-- 例 -->(.*?)<!-- /例 -->", 節, re.S).group(1)
    行たち = [[c.strip() for c in l.strip().strip("|").split("|")] for l in 例.splitlines() if l.strip().startswith("|")]
    return [r for r in 行たち if not all(set(c) <= set("-: ") for c in r)]


def _検査(行たち):
    型 = 当てる.型を開く(根 / "初期設定" / "型.json")
    一覧 = [["顧客ID", "会社", "組"]] + sorted({(r[0], r[1], r[2]) for r in 行たち[1:] if r[0] and r[1]})
    事務所 = {"会社": "作り物の事務所", "置き場": ["00_事務所/事務所の設定"],
            "シート": {"00_事務所/事務所の設定": {"置き場": 行たち, "会社の一覧": [list(x) for x in 一覧]}}}
    return [x for x in 見回り.置き場の検査(事務所, dt.date(2099, 1, 1), 型) if x["所"] == "00_事務所/事務所の設定/置き場"]


def test_例の表は会社ごとの行で組の会社は同じ組と同じID():
    表 = 例の表()
    assert 表[0] == ["顧客ID", "会社", "組", "物", "ID"]
    行 = [dict(zip(表[0], r)) for r in 表[1:]]
    組ごと = {}
    for r in 行:
        assert r["会社"] and r["顧客ID"], r  # 会社を空にした組の行を書かない・顧客ID を空にしない
        組ごと.setdefault((r["組"], r["物"]), set()).add((r["会社"], r["ID"]))
    assert len({(r["顧客ID"], r["物"]) for r in 行}) == len(行)  # 1 つの (顧客ID, 物) に 1 行
    assert any(当てる.型の口.台帳の名か(r["物"]) for r in 行)  # 台帳は年ごとの名
    束ねた = [v for v in 組ごと.values() if len({c for c, _ in v}) > 1]
    assert 束ねた, "例に組で束ねた会社（2 社以上）の行が要る"
    for v in 束ねた:
        assert len({i for _, i in v}) == 1, v  # 同じ組・同じ物は同じ ID


def test_例の表は置き場の検査を通り_会社を空にした組の行は赤():
    表 = 例の表()
    assert _検査(表) == []  # 緑（紙の例のとおり）
    組の行 = [["", "", 表[1][2], "3_月ごと", "id-作り物"]]  # 壊す: 組の 1 行にまとめて会社と顧客ID を空にする
    赤 = _検査(表 + 組の行)
    assert 6 in [x["項目"] for x in 赤] and any("会社 が空" in x["訳"] for x in 赤 if x["項目"] == 6), 赤
    assert any(x["項目"] == 8 and "顧客ID" in x["訳"] for x in 赤), 赤
