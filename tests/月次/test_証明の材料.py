"""計算が読む材料の一覧と、出す前の証明（出口/証明.py）が結ぶ材料の一覧を機械で照らす試験。作り物の会社 C1 の値だけ。

根: 計算が読むのに証明の 入力の指紋 に無い材料（前の月・前の年の確定した勤怠・月の数字・法の線・賞与の支給一覧など）は、
証明を作った後に書き換えても照らしが通ってしまう。`月次.引数の扱い`（引数ごとに結ぶ名か結ばない訳）を、月を回す・賞与を回す の
引数の並び・段の解決と入口の文脈が読むタブ・証明の 入力の名・実際に渡した計算の元 と照らし、片方にしか無い物があれば赤にする
（扱いの決まらない新しい材料が入れない）。注入: 前の月の確定した勤怠を証明の後に書き換えると照らしが赤。
"""
import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(根))
sys.path.insert(0, str(根 / "tests" / "計算"))
sys.path.insert(0, str(根 / "tests" / "集計"))
_spec = importlib.util.spec_from_file_location("証明の材料_試験_作り物", 根 / "tests" / "初期設定" / "test_初期設定_給与の関所.py")
作 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(作)

import 作る_計算  # noqa: E402
import 作る_集計  # noqa: E402
import 月次  # noqa: E402
from 出口 import 証明  # noqa: E402

C, 支給月 = 作.C, 作.支給月
版 = "v9.9.9"
口 = {"月": 月次.月を回す, "賞与": 月次.賞与を回す}


@pytest.fixture(autouse=True)
def _版(monkeypatch):
    monkeypatch.setattr(証明, "パックの版", lambda: 版)


@pytest.mark.parametrize("回", ["月", "賞与"])
def test_引数の全部に結ぶ名か結ばない訳がある(回):
    引数 = set(inspect.signature(口[回]).parameters)
    扱い = 月次.引数の扱い[回]
    assert 引数 == set(扱い), f"扱いの無い引数 {sorted(引数 - set(扱い))}・引数に無い扱い {sorted(set(扱い) - 引数)}"
    for k, v in 扱い.items():
        assert (isinstance(v, tuple) and v) or (isinstance(v, str) and v.strip()), k


@pytest.mark.parametrize("回", ["月", "賞与"])
def test_結ぶ名は証明の入力の名と同じ(回):
    結ぶ = {n for v in 月次.引数の扱い[回].values() if isinstance(v, tuple) for n in v}
    assert 結ぶ == set(証明.入力の名[回]), (sorted(結ぶ - set(証明.入力の名[回])), sorted(set(証明.入力の名[回]) - 結ぶ))


def test_段の解決と入口の文脈が読むタブは全部結ぶ():
    段の名 = {v: k for k, v in 月次.台帳のタブの名.items()}   # 段の解決の読む名 → 殻の渡す名
    読む = set()
    for f, 外 in ((月次.段.解く, {"支給月"}), (月次.繋.入口の文脈, {"支給月", "会社名", "解いた", "置き場", "質問と回答"}),
                 (月次.繋.有給の入力, {"支給月", "会社名", "解いた", "表A", "勤怠の始め", "出勤率が足りない付与日"})):
        読む |= {段の名.get(p.name, p.name) for p in inspect.signature(f).parameters.values()
                 if p.kind is p.KEYWORD_ONLY and p.name not in 外}
    結ぶタブ = set(証明.計算が読むマスタのタブ()) | set(月次.タブの扱い)
    assert 読む <= 結ぶタブ, f"計算が読むのに証明が結ばないタブ {sorted(読む - 結ぶタブ)}"
    assert set(月次.タブの扱い.values()) <= set(証明.入力の名["月"]) & set(証明.入力の名["賞与"])


def _回す(tmp_path, monkeypatch, **引数):
    """月を回す（試験の道）。証明に渡した計算の元も返す（`_証明たち` の入力を覗く）。"""
    見た = {}
    元の口 = 月次._証明たち

    def 覗く(out, 会社名, 支給月_, 回, 例の結果, 入力):
        見た["入力"] = 入力
        return 元の口(out, 会社名, 支給月_, 回, 例の結果, 入力)
    monkeypatch.setattr(月次, "_証明たち", 覗く)
    o = 作.確定して回す(支給月, C, 作._タブ(), [{"部品": "Excel出勤簿", "値": 作._出勤簿()}], 法の線=作る_集計.法の線,
                   置き場=作る_計算.置き場(tmp_path), 例=作._例(), 出口={"支給控除一覧": {"今ある名": [], "履歴にある名": []}}, **引数)
    return o, 見た["入力"]


def test_月を回すが証明に渡す計算の元は要る名の全部(tmp_path, monkeypatch):
    o, 元 = _回す(tmp_path, monkeypatch)
    assert set(元) == set(証明.計算の元に要る名("月"))
    d = o["支給控除一覧"][0]
    assert set(o["証明"][d.物]["入力の指紋"]) == set(証明.入力の名["月"])
    assert 証明.照らす(d, o["証明"][d.物], 入力=元) == {"通す": True, "赤": []}


def _前の月へ(表):
    """確定した勤怠の表（get_values の形）の 支給月 の列を 1 つ前の支給月にする。"""
    h, *行 = [list(r) for r in 表]
    i = h.index("支給月")
    前 = 月次.前の支給月(支給月)   # 台帳の行の字（YYYY.MM支給）
    return [h, *[[*r[:i], 前, *r[i + 1:]] for r in 行]]


def _1字変える(表, 列):
    h, *行 = [list(r) for r in 表]
    行[0][h.index(列)] = str(行[0][h.index(列)]) + "・"
    return [h, *行]


@pytest.mark.parametrize("名,列", [("前の確定した勤怠", "備考"), ("前の確定した勤怠の区間", "区間の番号")])
def test_前の月の確定した勤怠を証明の後に書き換えると照らしが赤(tmp_path, monkeypatch, 名, 列):
    """注入: 月の頭の週・有給の数えに読む前の月の確定した勤怠を、証明を作った後に 1 字書き換える → 照らすが通さない。"""
    今 = 作.確定して回す(支給月, C, 作._タブ(), [{"部品": "Excel出勤簿", "値": 作._出勤簿()}], 法の線=作る_集計.法の線,
                   置き場=作る_計算.置き場(tmp_path / "前"), 例=作._例(),
                   出口={"支給控除一覧": {"今ある名": [], "履歴にある名": []}})["確定した勤怠"]
    前 = {k: _前の月へ(v) for k, v in 今.items()}   # 作り物の出勤簿を前の支給月の確定した勤怠にした物
    assert len(前[名.removeprefix("前の")]) > 1
    o, 元 = _回す(tmp_path, monkeypatch, 前の確定した勤怠=前["確定した勤怠"], 前の確定した勤怠の区間=前["確定した勤怠の区間"])
    d = o["支給控除一覧"][0]
    p = o["証明"][d.物]
    assert 証明.照らす(d, p, 入力=元)["通す"]
    改 = {**元, 名: _1字変える(元[名], 列)}
    r = 証明.照らす(d, p, 入力=改)
    assert not r["通す"] and any("入力の指紋が合わない（前の確定した勤怠）" in x for x in r["赤"]), r
    # 前の月の勤怠を渡さなかった事にする（鍵ごと消す）のも照らせない＝通さない
    r = 証明.照らす(d, p, 入力={k: v for k, v in 元.items() if k != 名})
    assert not r["通す"] and any(名 in x and "無い" in x for x in r["赤"]), r


# --- 殻の出荷の道: 月を回す に渡した物から公開の 月次.計算の元 で元を組み、出す前の照らし（plugin）へそのまま渡す ---

def _出荷の入力(tmp_path, monkeypatch):
    """月を回す（試験の道）に渡した引数を覚え、殻と同じに 月次.計算の元（公開の口）で計算の元を組む。
    支給月は 月を回す に渡した `YYYY.MM支給` のまま、出す物の名と証明は出口が返したまま渡す（字を組み直さない）。"""
    sys.path.insert(0, str(根 / "plugins" / "payroll-agent" / "bin"))
    渡した = {}
    元の口 = 月次.月を回す

    def 覚える(支給月_, 会社, タブ, **kw):
        渡した.update(タブ=タブ, **kw)
        return 元の口(支給月_, 会社, タブ, **kw)
    monkeypatch.setattr(月次, "月を回す", 覚える)
    o = 作.確定して回す(支給月, C, 作._タブ(), [{"部品": "Excel出勤簿", "値": 作._出勤簿()}], 法の線=作る_集計.法の線,
                   置き場=作る_計算.置き場(tmp_path), 例=作._例(), 出口={"支給控除一覧": {"今ある名": [], "履歴にある名": []}})
    k = 渡した
    元 = 月次.計算の元(k["タブ"], k.get("つなぎ", ()), k.get("給与のルール"),
                 **{n: k.get(n, d) for n, d in (("確定した勤怠", None), ("確定した勤怠の区間", None),
                                                ("前の確定した勤怠", ()), ("前の確定した勤怠の区間", ()), ("月の数字", ()),
                                                ("有給の値", None), ("法の線", None))})
    出す物たち = list(o["支給控除一覧"])
    assert 出す物たち
    return {"会社": C, "支給月": 支給月, "外した人": 0,
            "出す物": [{"物": d.物, "名": {"フォルダ": d.名.フォルダ, "名": d.名.名}, "表": [list(r) for r in d.表]} for d in 出す物たち],
            "証明": dict(o["証明"]),
            "材料": {"パックの版": 版, "今ある名": [], "履歴にある名": [], "計算の元": 元, "課題": [], "課題の id": [], "閉じた状態": ["完了"], "月の本文": ""}}


def _出す前の照らし(x):
    import 出す前の照らし as G
    from 出口 import 名と版
    return G.照らす(x, 置き場=dict(名と版.出す物の置き場), 証明の口=証明, 名の口=名と版)


def test_出口が作った正しい表は殻の支給月のまま出す前の照らしを通る(tmp_path, monkeypatch):
    x = _出荷の入力(tmp_path, monkeypatch)
    assert x["支給月"] == "2027.02支給" and all("_2027-02_v" in d["名"]["名"] for d in x["出す物"])
    assert _出す前の照らし(x) == []


@pytest.mark.parametrize("ずらす", ["名", "証明"])
def test_名か証明の支給月を1字ずらすと出す前の照らしが止める(tmp_path, monkeypatch, ずらす):
    x = _出荷の入力(tmp_path, monkeypatch)
    d = x["出す物"][0]
    if ずらす == "名":
        d["名"]["名"] = d["名"]["名"].replace("_2027-02_", "_2027-03_")
    else:
        x["証明"][d["物"]]["支給月"] = "2027-03"
    reds = _出す前の照らし(x)
    assert reds and any(d["物"] in r and ("の形でない" if ずらす == "名" else "証明の 支給月") in r for r in reds), reds
