"""出す前の照らしは前の値（管理表の今の止まりの理由・前の版の名）を必ず受ける。渡さない・形の違う時は止める（注入の試験）。値は作り物だけ。

根（2026-11-19）: v0.33.0・v0.34.0 で出す物・確認ページ・問いの番号に直したのと同じ原因＝前の値の既定が空で、渡さないと黙って
ほかの止まりの理由を消し（管理表の行）、名の照らしは版の大小を見ずに前の版より小さい・同じ番号の名を通した。
"""
import json
import sys

import pytest

from 手伝い import BIN, 根, 出す物, 入力, 回, 場所, 会社, 月  # noqa: F401

import 出す前の照らし as G  # noqa: E402
import 出口.名と版 as 名と版  # noqa: E402
import 出口.証明 as 証  # noqa: E402
from 手伝い import 版, 証明  # noqa: E402

置き場 = 場所.出す物の置き場(根)


@pytest.fixture
def 本物(monkeypatch):
    monkeypatch.setattr(証, "パックの版", lambda: 版)
    return lambda x: G.照らす(x, 置き場=置き場, 証明の口=証, 名の口=名と版)


def _名(物, n):
    return f"{名と版.名の頭(物, 会社, 名と版.出す支給月(月, 回(物)))}{n}"


# --- 管理表の行: 今の止まりの理由は必ず字で渡す ---

def test_管理表の行は今の止まりの理由を省けず_字でなければ止める():
    with pytest.raises(TypeError):
        G.管理表の行(入力())   # 既定の "" を畳んだ
    for v in (None, ["例の確かめ待ち"], 1):
        with pytest.raises(ValueError, match="止まりの理由 の欄の字で渡す"):
            G.管理表の行(入力(), v)
    # 空の欄は "" で渡せば空・ほかの理由が在れば残す（有給休暇管理表の訳が付かない 支給控除一覧 の出荷で見る）
    一覧 = 入力(出す物("支給控除一覧_雇用"))
    assert G.管理表の行(一覧, "")["止まりの理由"] == ""
    assert G.管理表の行(一覧, "例の確かめ待ち")["止まりの理由"] == "例の確かめ待ち"


def test_命令の管理表の行は今の止まりの理由を省くと止め_空の字は通す(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(証, "パックの版", lambda: 版)
    f = tmp_path / "in.json"
    f.write_text(json.dumps(入力(), ensure_ascii=False), encoding="utf-8")
    d = 入力()["出す物"][0]
    頭 = ["管理表の行", str(f), "--パック", str(根), "--置いた",
          json.dumps([{"物": d["物"], "名": d["名"]["名"], "url": "u"}], ensure_ascii=False)]
    for 足す in ([], ["--今の止まりの理由"]):   # 省く・値の無い旗
        assert G.main(頭 + 足す) == 2
        out = json.loads(capsys.readouterr().out)
        assert not out["通す"] and "--今の止まりの理由" in out["赤"][0] and "管理表の行" not in out
    assert G.main(頭 + ["--今の止まりの理由", "例の確かめ待ち ／ 今の版: 前の形 u0"]) == 0
    assert json.loads(capsys.readouterr().out)["管理表の行"]["止まりの理由"].endswith("例の確かめ待ち")


# --- 名の版: 前の版の最大の次だけ通す（材料 今ある名・履歴にある名 は必ず渡す） ---

@pytest.mark.parametrize("鍵", ["今ある名", "履歴にある名"])
@pytest.mark.parametrize("値", ["省く", None, "取り込み_x_v1", {"取り込み": []}, [{"name": "取り込み_x_v1"}], [3]])
def test_前の版の名を名の字の並びで渡さなければ止める(本物, 鍵, 値):
    x = 入力()
    if 値 == "省く":
        del x["材料"][鍵]
    else:
        x["材料"][鍵] = 値
    assert any(f"材料 の {鍵}" in r and "名の字の並びで渡す" in r for r in 本物(x))


@pytest.mark.parametrize("物", ["取り込み", "支給控除一覧_雇用", "有給休暇管理表", "賞与の取り込み"])
def test_前の版の最大の次なら通り_小さい同じ飛ばした番号は止める(本物, 物):
    x = 入力(出す物(物, 版の番号=4))   # 名は v4
    x["材料"]["今ある名"] = [_名(物, 3), "別の物.csv"]
    x["材料"]["履歴にある名"] = [_名(物, 1), _名(物, 2)]
    assert 本物(x) == []
    for 今, 履歴 in (([_名(物, 4)], []),                 # 同じ番号が置き場に在る（置いた後に照らした・出し直しの数え違い）
                     ([], [f"{_名(物, 6)}.csv"]),         # 履歴の前の版より小さい（番号を戻した）
                     ([_名(物, 2)], [])):                  # 飛ばした番号（v3 が付く所に v4）
        x["材料"]["今ある名"], x["材料"]["履歴にある名"] = 今, 履歴
        assert any("前の版の最大の次でない" in r for r in 本物(x)), (今, 履歴)


def test_名を付ける口の無い前の版のパックは止める():
    class 口:
        殻の支給月か = staticmethod(名と版.殻の支給月か)
        出す支給月 = staticmethod(名と版.出す支給月)
        出す名か = staticmethod(名と版.出す名か)
        回たち = 名と版.回たち
    x = 入力()
    r = G.照らす(x, 置き場=置き場, 証明の口=証, 名の口=口)
    assert any("名を付ける" in s and "名の版を照らせない" in s for s in r)


def test_命令の管理表の行は置いたばかりの名だけを前の版に数えない(tmp_path, capsys, monkeypatch):
    """置いた後に 2_出す物/ を読み直して 今ある名 を作っても、置いた名（拡張子つきも）で止めない。ほかの同じ番号は止める。"""
    monkeypatch.setattr(証, "パックの版", lambda: 版)
    x = 入力()
    置いた = x["出す物"][0]["名"]["名"]
    f = tmp_path / "in.json"
    頭 = ["管理表の行", str(f), "--パック", str(根), "--置いた",
          json.dumps([{"物": x["出す物"][0]["物"], "名": 置いた, "url": "u"}], ensure_ascii=False), "--今の止まりの理由", ""]
    for 今 in ([置いた], [f"{置いた}.csv"]):
        x["材料"]["今ある名"] = 今
        f.write_text(json.dumps(x, ensure_ascii=False), encoding="utf-8")
        assert G.main(頭) == 0, capsys.readouterr().out
        capsys.readouterr()
    x["材料"]["今ある名"] = [置いた]
    f.write_text(json.dumps(x, ensure_ascii=False), encoding="utf-8")
    assert G.main(["照らす", str(f), "--パック", str(根)]) == 2   # 置く前の照らしでは同じ番号を止める
    assert "前の版の最大の次でない" in capsys.readouterr().out
