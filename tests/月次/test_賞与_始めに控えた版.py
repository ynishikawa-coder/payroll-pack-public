"""給与の決まり「回の途中で版を変えない」を賞与の回にも当てる機械の照らし（型の版 34）。作り物の会社 C1 の値だけ。

賞与を回す は、その会社の賞与の支給一覧の行の パックの版（賞与の回の始めに控えた版）が今のパックの版と同じ時だけ回す。
違う・空（版を控えていない回）・行で割れる時は止める（どちらの版で出すかはオーナーが毎回決める・2026-11-19 オーナー＝毎月と同じ）。
照らすのは月の締めの記録と同じ 1 つの部品（月次._控えた版を照らす）。注入の試験。
"""
import importlib.util
from pathlib import Path

import pytest

ここ = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("賞与_始めに控えた版_試験_関所", ここ / "test_賞与の関所.py")
関 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(関)
_spec = importlib.util.spec_from_file_location("賞与_始めに控えた版_試験_元", ここ / "test_賞与の元.py")
元 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(元)

import 月次  # noqa: E402

C, 人たち, 支給月 = 関.C, sorted(関.人たち), 関.支給月
_版 = 関._版   # 証明のパックの版を試験の版（関.版）に（autouse の fixture を借りる）


def _一覧(版たち: dict[str, str]):
    return [{**r, "パックの版": 版たち[r["NO"]]} for r in 関._一覧()]


def test_始めに控えた版と今の版が同じなら回る(tmp_path):
    o = 関._回す(tmp_path)
    assert o["証明"] and {r.NO for r in o["関所を通った"].行たち} == set(人たち)


@pytest.mark.parametrize("版たち, 訳", [
    (lambda 人: {NO: "v0.0.1" for NO in 人}, "賞与の始めに控えた版 v0.0.1 と今のパックの版"),      # 前の版で始めた回を新しい版で回す
    (lambda 人: {NO: "" for NO in 人}, "賞与の支給一覧に賞与の始めに控えた版が無い行"),            # 版を控えていない回（直し 34 の前）
    (lambda 人: {NO: (関.版 if i else "v0.0.1") for i, NO in enumerate(人)}, "行で割れている"),   # 回の途中で版を上げて書き足した人が混ざる
])
def test_始めに控えた版が今と違えば賞与を回さない(tmp_path, monkeypatch, 版たち, 訳):
    一覧 = _一覧(版たち(人たち))
    monkeypatch.setattr(関, "_一覧", lambda: 一覧)
    with pytest.raises(ValueError, match=訳) as e:
        関._回す(tmp_path)
    assert "オーナーに選択肢の画面で聞く" in str(e.value)


def test_版の鍵の無い手で組んだ支給一覧は止める(tmp_path, monkeypatch):
    一覧 = [{k: v for k, v in r.items() if k != "パックの版"} for r in 関._一覧()]
    monkeypatch.setattr(関, "_一覧", lambda: 一覧)
    with pytest.raises(ValueError, match="版が無い行"):
        関._回す(tmp_path)


def test_ほかの会社の行の版は見ない(tmp_path, monkeypatch):
    一覧 = [*関._一覧(), {"会社": "作り物の別の会社", "NO": "0001", "額": 1, "原本の名前": "x", "パックの版": "v0.0.1"}]
    monkeypatch.setattr(関, "_一覧", lambda: 一覧)
    assert 関._回す(tmp_path)["証明"]


@pytest.mark.parametrize("版, 訳", [("v0.0.1", "と今のパックの版"), ("", "版が無い行")])
def test_台帳から読んだ元も控えた版で止まる(tmp_path, 版, 訳):
    o = 月次.賞与の元を読む(元._表(**{NO: {"パックの版": 版} for NO in 人たち}), C, 支給月)
    assert {r["パックの版"] for r in o["支給一覧"]} == {版}
    共 = dict(置き場=関.作る_計算.置き場(tmp_path), 法の線=関.作る_集計.法の線, 出口=関._出口(),
             給与のルール=関.例をMDに(関.作._例()))
    with pytest.raises(ValueError, match=訳):
        月次.賞与を回す(支給月, C, 関.作._タブ(), o["支給一覧"], 支給日=o["支給日"], **o["賞与の引数"], **共)


def test_月と賞与は同じ部品で版を照らす():
    import inspect
    for f in (月次._締めた時の版を照らす, 月次._賞与の始めの版を照らす):
        assert "_控えた版を照らす(" in inspect.getsource(f), f.__name__
