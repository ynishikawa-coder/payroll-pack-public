"""出口の証明（出口/証明.py・形 給与の証明/1）の試験。作り物の会社 C1 の値だけ（tests/初期設定/test_初期設定_給与の関所.py の作り物）。

根: 出口の外で値を差し替えた表が殻の手で出せた。殻の出荷の口は、出口が付けた証明と表を照らして通す。
ここでは誤りの類（表の 1 字の差し替え・欠けた鍵・知らない形・例を通っていない月・別の版・例のタブの書き換え）を
わざと入れて、照らす が通さないことを見る（注入の試験）。
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(根))
sys.path.insert(0, str(根 / "tests" / "計算"))
sys.path.insert(0, str(根 / "tests" / "集計"))
_spec = importlib.util.spec_from_file_location("証明_試験_作り物", 根 / "tests" / "初期設定" / "test_初期設定_給与の関所.py")
作 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(作)

import 作る_計算  # noqa: E402
import 作る_集計  # noqa: E402
import 月次  # noqa: E402
from 出口 import 証明  # noqa: E402

C, 支給月, 人たち = 作.C, 作.支給月, 作.人たち
版 = "v9.9.9"


@pytest.fixture(autouse=True)
def _版(monkeypatch):
    monkeypatch.setattr(証明, "パックの版", lambda: 版)


def _回す(tmp_path, 例):
    return 月次.月を回す(支給月, C, 作._タブ(), [{"部品": "Excel出勤簿", "値": 作._出勤簿()}], 法の線=作る_集計.法の線,
                     置き場=作る_計算.置き場(tmp_path), 例=例, 出口={"支給控除一覧": {}})


def _殻の指紋(table):
    """殻の出荷の口（pixel-office agents/kyuyo/bin/shell_common.table_fingerprint）の式を写した物＝両側の揃いを見る。"""
    rows = [[("" if c is None else str(c)) for c in r] for r in table]
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _一つ(o):
    d = o["支給控除一覧"][0]
    return d, o["証明"][d.物]


def test_月を回すは出す物ごとに証明を付け_照らすは通す(tmp_path):
    o = _回す(tmp_path, 作._例())
    d, p = _一つ(o)
    assert p["形"] == "給与の証明/1" and p["会社"] == C and p["支給月"] == 支給月 and p["物"] == d.物
    assert p["表の指紋"] == _殻の指紋(d.表) and p["パックの版"] == 版
    assert p["関所"] == {"通った": True, "外した人": 0}
    assert p["例の照らし"] == {"通った": True, "数": o["例の確かめ"]["数"], "合わない": 0}
    assert set(o["証明"]) == {x.物 for x in o["支給控除一覧"]}
    入 = {"例": 作._例()}
    assert 証明.照らす(d, p, 入力=入) == {"通す": True, "赤": []}
    # JSON を通しても（殻は JSON で受ける）通る
    assert 証明.照らす({"物": d.物, "表": json.loads(json.dumps(d.表))}, json.loads(json.dumps(p)),
                    入力=json.loads(json.dumps(入)))["通す"]


def test_入力が無い_形が違う時は照らせないので通さない(tmp_path):
    d, p = _一つ(_回す(tmp_path, 作._例()))
    for 入 in (None, {}, {"例": None}, {"例": "行"}, []):
        r = 証明.照らす(d, p, 入力=入)
        assert not r["通す"] and any("入力" in x for x in r["赤"]), (入, r)
    # 殻の今の呼び方 verify(out, proof)＝入力を省いても黙って通さない
    r = 証明.照らす(d, p)
    assert not r["通す"] and any("入力" in x and "無い" in x for x in r["赤"])


def test_表を1字差し替えたら通さない(tmp_path):
    d, p = _一つ(_回す(tmp_path, 作._例()))
    表 = [list(r) for r in d.表]
    表[-1][1] = 表[-1][1] + "0"
    r = 証明.照らす({"物": d.物, "表": 表}, p, 入力={"例": 作._例()})
    assert not r["通す"] and any("表の指紋が合わない" in x for x in r["赤"])


def test_例を通っていない月の証明は通さない(tmp_path):
    for 例 in (作._例()[:1], None):
        o = _回す(tmp_path / str(id(例)), 例)
        d, p = _一つ(o)
        assert p["例の照らし"]["通った"] is False
        r = 証明.照らす(d, p, 入力={"例": 例 or []})
        assert not r["通す"] and any("例の照らしを通っていない" in x for x in r["赤"])


def test_手で書き換えた証明の中身の食い違いは通さない(tmp_path):
    d, p = _一つ(_回す(tmp_path, 作._例()))
    for 上書き, 訳 in (({"例の照らし": {"通った": True, "数": 0, "合わない": 0}}, "例の照らしの中身"),
                     ({"例の照らし": {"通った": True, "数": 3, "合わない": 1}}, "例の照らしの中身"),
                     ({"関所": {"通った": "はい"}}, "関所を通っていない"),
                     ({"形": "給与の証明/0"}, "証明の形"),
                     ({"物": "取り込み"}, "物が違う"),
                     ({"パックの版": "v0.0.1"}, "照らすパックの版"),
                     ({"台帳の指紋": ""}, "台帳の指紋 が無い")):
        r = 証明.照らす(d, {**p, **上書き}, 入力={"例": 作._例()})
        assert not r["通す"] and any(訳 in x for x in r["赤"]), (上書き, r)
    for k in 証明.鍵たち:
        q = dict(p)
        q.pop(k)
        assert not 証明.照らす(d, q, 入力={"例": 作._例()})["通す"], k
    assert not 証明.照らす(d)["通す"] and not 証明.照らす(d, "証明")["通す"]


def test_証明を作った後に例のタブが変わったら通さない(tmp_path):
    d, p = _一つ(_回す(tmp_path, 作._例()))
    見出し, *行 = 作._例()
    行 = [list(r) for r in 行]
    行[0][見出し.index("期待")] = str(行[0][見出し.index("期待")]) + "・"
    r = 証明.照らす(d, p, 入力={"例": [見出し, *行]})
    assert not r["通す"] and any("台帳の指紋が合わない" in x for x in r["赤"])
    # 行の並べ替え・前後の空白では変わらない
    assert 証明.照らす(d, p, 入力={"例": [見出し, *reversed(作._例()[1:])]})["通す"]
    assert not 証明.照らす(d, p, 入力={"例の行": []})["通す"]


def test_照らすパックが版の印の中身でなければ通さない(tmp_path, monkeypatch):
    d, p = _一つ(_回す(tmp_path, 作._例()))
    monkeypatch.setattr(証明, "パックの版", lambda: 版 + "+未リリース")
    r = 証明.照らす(d, p, 入力={"例": 作._例()})
    assert not r["通す"] and any("版の印の中身でない" in x for x in r["赤"])


def test_パックの版はCHANGELOGの一番上の版と未リリースの印(tmp_path, monkeypatch):
    monkeypatch.undo()
    for 中身, 期待 in (("# C\n\n## 未リリース\n\n## [v1.2.3] - 2099-01-01\n- a\n", "v1.2.3"),
                     ("# C\n\n## 未リリース\n- 足した\n\n## [v1.2.3] - 2099-01-01\n", "v1.2.3+未リリース"),
                     ("# C\n", "")):
        (tmp_path / "CHANGELOG.md").write_text(中身, encoding="utf-8")
        monkeypatch.setattr(証明, "_根", tmp_path)
        assert 証明.パックの版() == 期待


def test_例の列は例の確かめと同じ():
    assert 証明.例の列 == 月次.例の確かめ.例の列
