"""締まらない人も芯で計算して値を仮にし、仮が 1 つでも残る人だけ出さない（決定 2026-11-27）の受け入れの試験。作り物の会社 C1 の値だけ。

⟦鍵:給与計算/足りない時は仮で計算し出さない⟧
1. 締まっていない人が 1 人: 全員を計算し、その人は全部が仮・問いを出し、その人だけ出さず、ほかの人は出す。
2. 必ず埋める欄が空の人が 1 人: 同じ。
3. 仮が 0: 出す物は今までどおり全員が出る。
4. 仮の人は出す物（出口へ渡す 1 つの口 `_出口へ`）に入らない。ほかの人は待たせない（会社の全員を待たせる止めは 2026-11-27 に畳んだ）。月も賞与も。
"""
import importlib.util
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(根))
sys.path.insert(0, str(Path(__file__).resolve().parent))
_spec = importlib.util.spec_from_file_location("全員を仮で計算_試験_月次", 根 / "tests" / "月次" / "test_月次.py")
月の試験 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(月の試験)
_spec = importlib.util.spec_from_file_location("全員を仮で計算_試験_賞与", 根 / "tests" / "月次" / "test_賞与の関所.py")
賞与の試験 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(賞与の試験)

import 月次  # noqa: E402

人たち = 月の試験.人たち
出す物 = ("取り込み", "支給控除一覧", "有給休暇管理表")


def _台帳の状態(o) -> dict:
    h, *行 = o["台帳"]["人ごとの月の数字"]
    return {r[h.index("NO")]: r[h.index("状態")] for r in 行}


def _全員を計算し_その人だけ全部が仮で_その人だけ出ない(o, NO):
    # 全員を計算する: 台帳へ書く月の数字と見当の額に全員が居る
    assert set(_台帳の状態(o)) == set(人たち) and set(o["見当の額"]) == set(人たち)
    # その人の額は仮・ほかの人は仮でない
    assert o["見当の額"][NO]["仮"] is True
    assert all(o["見当の額"][n]["仮"] is False for n in 人たち if n != NO), o["見当の額"]
    # その人だけが関所で外れ、ほかの人は通って出す物に出る
    assert {a["NO"] for a in o["外した人"]} == {NO}
    assert {r.NO for r in o["関所を通った"].行たち} == set(人たち) - {NO}
    出 = 月の試験._出た人(o)
    assert 出["取り込み"] == set(人たち) - {NO} and 出["支給控除一覧"] == set(人たち) - {NO}, 出
    assert any(訳.startswith(f"NO {NO}:") for 訳 in o["待つ訳"]), o["待つ訳"]


def test_1_締まっていない人が1人なら全員を計算し_その人は全部が仮で問いを出し_その人だけ出さない(tmp_path):
    tabs, 置き場, 表 = 月の試験._確定の表(tmp_path)
    o = 月の試験._確定から回す(tabs, 置き場, 表, 締めの記録=月の試験._締め({"0002": "まだ"}))
    _全員を計算し_その人だけ全部が仮で_その人だけ出ない(o, "0002")
    assert [x["NO"] for x in o["締まっていない人"]] == ["0002"]
    assert _台帳の状態(o)["0002"] == "仮"   # 締まっていない人は勤怠の数も仮
    assert [q["NO"] for q in o["問い"]["締め"]] == ["0002"]   # 仮の値と問いはまとめて出す


def test_2_必ず埋める欄が空の人が1人なら全員を計算し_その人は全部が仮で問いを出し_その人だけ出さない(tmp_path):
    tabs, 置き場, 表 = 月の試験._確定の表(tmp_path)
    tabs = {**tabs, "社員": [{**a, "源泉.欄": ""} if a["NO"] == "0003" else a for a in tabs["社員"]]}
    o = 月の試験._確定から回す(tabs, 置き場, 表)
    _全員を計算し_その人だけ全部が仮で_その人だけ出ない(o, "0003")
    assert o["待つ訳"] == ["NO 0003: 必ず埋める欄が空: 源泉.欄"]
    行 = [r for r in o["仮の人の行"] if str(r["NO"]) == "0003"]   # 芯が見当で計算し、その人の計算の項目は全部が仮
    assert 行 and all(r["状態"] == "仮" for r in 行 if r.get("出所", "計算") == "計算"), 行
    assert any(("C1", "0003") in q["人"] and "源泉.欄" in q["何が無いか"] for q in o["問い"]["計算"]), o["問い"]["計算"]


def test_3_仮が0なら出す物は今までどおり全部出る(tmp_path):
    tabs, 置き場, 表 = 月の試験._確定の表(tmp_path)
    o = 月の試験._確定から回す(tabs, 置き場, 表)
    assert o["待つ訳"] == [] and o["外した人"] == [] and o["締まっていない人"] == []
    assert set(_台帳の状態(o).values()) != {"仮"} and all(not v["仮"] for v in o["見当の額"].values())
    出 = 月の試験._出た人(o)
    assert 出["取り込み"] == set(人たち) and 出["支給控除一覧"] == set(人たち)
    assert {"取り込み", "支給控除一覧"} <= set(o)


def _出口へを見張る(monkeypatch) -> list:
    呼んだ: list = []
    元の出口へ = 月次._出口へ

    def 出口へ(通, *a, **k):
        呼んだ.append({r.NO for r in 通.行たち})
        return 元の出口へ(通, *a, **k)

    monkeypatch.setattr(月次, "_出口へ", 出口へ)
    return 呼んだ


@pytest.mark.parametrize("名", ["締めの記録がまだ", "確定した勤怠が無い", "必ず埋める欄が空", "段の解決の仮"])
def test_4_仮の人は出口へ渡らず_ほかの人は渡る_月(tmp_path, monkeypatch, 名):
    tabs, 置き場, 表 = 月の試験._確定の表(tmp_path)
    引数 = {}
    if 名 == "締めの記録がまだ":
        引数["締めの記録"] = 月の試験._締め({"0001": "まだ"})
    elif 名 == "確定した勤怠が無い":
        表 = {k: [v[0], *(r for r in v[1:] if r[v[0].index("NO")] != "0002")] for k, v in 表.items()}
    elif 名 == "必ず埋める欄が空":
        tabs = {**tabs, "社員": [{**a, "源泉.欄": ""} if a["NO"] == "0001" else a for a in tabs["社員"]]}
    else:
        tabs = {**tabs, "変更の記録": 月の試験.作._記録}
    呼んだ = _出口へを見張る(monkeypatch)
    o = 月の試験._確定から回す(tabs, 置き場, 表, **引数)
    仮 = {a["NO"] for a in o["外した人"]}
    assert 仮 and {r.NO for r in o["関所を通った"].行たち} == set(人たち) - 仮, 名
    # 出口へ渡す口へは関所を通った人だけが渡る（仮の人は渡らない）
    assert 呼んだ and all(渡 == set(人たち) - 仮 for 渡 in 呼んだ), (名, 呼んだ)
    出 = 月の試験._出た人(o)
    assert not 仮 & (出["取り込み"] | 出["支給控除一覧"]), (名, 出)


def test_4_仮の人は出口へ渡らず_ほかの人は渡る_賞与(tmp_path, monkeypatch):
    呼んだ = _出口へを見張る(monkeypatch)
    o = 賞与の試験._回す(tmp_path, タブ=賞与の試験.作._タブ(変更の記録=賞与の試験.作._記録))
    仮 = {a["NO"] for a in o["外した人"]}
    assert 仮 and {r.NO for r in o["関所を通った"].行たち}
    assert 呼んだ and all(not 仮 & 渡 for 渡 in 呼んだ), 呼んだ
