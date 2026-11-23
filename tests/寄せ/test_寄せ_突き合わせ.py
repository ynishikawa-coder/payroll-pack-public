"""寄せの人×項目の突き合わせの口（道具/寄せ/突き合わせ.py）。比べる字・違い・比較の写しの締めの行を殻でなくパックが決める。

根（2026-11-24）: 寄せの前と後を 1 字ずつ比べる判断が殻（事務所の側の口）に在った＝パックの出す物の形が変わっても殻の比べ方は
古いまま。判断をパックの口 1 つに寄せた。作り物の値だけ。
"""
import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

ここ = Path(__file__).resolve().parent
根 = ここ.parent.parent
sys.path.insert(0, str(根 / "道具" / "寄せ"))

import 突き合わせ as 突  # noqa: E402


def _csv(text, code="utf-8"):
    return {"CSV": base64.b64encode(text.encode(code)).decode(), "文字コード": code, "区切り": ","}


@pytest.mark.parametrize("v, 字", [(None, ""), (True, "TRUE"), (False, "FALSE"), (1.0, "1"), (1.5, "1.5"), ("a", "a"), (3, "3")])
def test_セルの字(v, 字):
    assert 突.セルの字(v) == 字


def test_同じなら違いは無い():
    t = {"明細": [["NO", "支給"], ["0001", "100"]]}
    assert 突.突き合わせる(t, t) == []


def test_人と項目で違いを言う():
    a = {"明細": [["NO", "支給"], ["0001", "100"]]}
    b = {"明細": [["NO", "支給"], ["0001", "101"]]}
    assert 突.突き合わせる(a, b) == ["明細 0001×支給: 前 '100' 後 '101'"]


def test_人が列の向きの表():
    a = {"一覧": [["項目", "0001"], ["支給", "100"]]}
    b = {"一覧": [["項目", "0001"], ["支給", "101"]]}
    assert 突.違い(a, b)[0] | {} == {"物": "一覧", "人": "0001", "項目": "支給", "前": "100", "後": "101"}


def test_物と行の欠け():
    assert 突.突き合わせる({"明細": [["a"]]}, {}) == ["明細: 寄せた後に無い"]
    assert 突.突き合わせる({"明細": [["a"]]}, {"明細": [["a"], ["b"]]}) == ["明細 2 行目: 寄せの前に無い"]
    assert 突.突き合わせる({"x": _csv("a")}, {"x": [["a"]]}) == ["x: 寄せの前は CSV・寄せた後は 表"]


def test_CSVは寄せた後の文字コードで読む():
    assert 突.突き合わせる({"x": _csv("NO,支給\n1,100\n", "cp932")}, {"x": _csv("NO,支給\n1,100\n", "cp932")}) == []
    a, b = _csv("NO,支給\n1,100\n"), _csv("NO,支給\n1,101\n")
    assert 突.突き合わせる({"x": a}, {"x": b}) == ["x 1×支給: 前 '100' 後 '101'"]
    with pytest.raises(突.拒む, match="文字コード"):
        突.突き合わせる({"x": a}, {"x": {"CSV": b["CSV"]}})


def test_合わない訳():
    assert 突.合わない訳([], "元") == ""
    assert 突.合わない訳(["a", "b", "c", "d"], "元") == "人×項目の突き合わせが合わない（4 所: a／b／c・突き合わせの元: 元）"


def test_版の違いは値と人を書かない():
    a = {"明細": [["NO", "支給", "控除"], ["0001", "100", "1"], ["0002", "200", "2"]]}
    b = {"明細": [["NO", "支給", "控除"], ["0001", "101", "1"], ["0002", "201", "3"]]}
    assert 突.版の違い(a, b) == [{"物": "明細", "所": 3, "項目": ["支給", "控除"], "訳": []}]


C, M = "作り物の会社", "2000.01支給"


def test_比較の写しにだけ版を足す():
    t = [["会社", "支給月", "NO", "状態"], [C, M, "1", "締まった"], [C, "2000.02支給", "1", "締まった"]]
    got = 突.比較の締めの行(t, C, M, "v9.9.9")
    assert got[0][-1] == "パックの版" and got[1][-1] == "v9.9.9" and got[2][4:] == []
    assert t[0] == ["会社", "支給月", "NO", "状態"], "渡した表を書き替えない"


@pytest.mark.parametrize("t, 訳", [
    ([], "揃わない＝比較を止める"),
    ([["会社", "支給月", "状態", "状態"]], "見出しが揃わない"),
    ([["会社", "支給月", "状態"], [C, M, "締め中"]], "未完了"),
    ([["会社", "支給月", "状態"], [C, "2000.02支給", "締まった"]], "締めの行が無い"),
])
def test_比較の締めの行を止める(t, 訳):
    with pytest.raises(突.拒む, match=訳):
        突.比較の締めの行(t, C, M, "v9.9.9")


def test_口から呼ぶ():
    p = 根 / "道具" / "寄せ" / "突き合わせ.py"
    r = subprocess.run([sys.executable, "-I", str(p), "字にする"], input=json.dumps({"出す物": {"x": [[1.0, None, True]]}}),
                       capture_output=True, text=True, cwd=根)
    assert r.returncode == 0 and json.loads(r.stdout) == {"出す物": {"x": [["1", "", "TRUE"]]}}
    r = subprocess.run([sys.executable, "-I", str(p), "比較の締めの行"], input=json.dumps({"締めの記録": []}),
                       capture_output=True, text=True, cwd=根)
    assert r.returncode == 2 and "比較を止める" in json.loads(r.stdout)["拒む"]


@pytest.mark.parametrize("何, 入力, 訳", [
    ("突き合わせる", '{"前": {"x": 5}, "後": {"x": [[1]]}}', "読めない"),   # 物が表でない
    ("字にする", '{"出す物": 5}', "出す物は"),
    ("字にする", "{ 崩れた", "JSON でない"),
])
def test_形の崩れた入力は拒む(何, 入力, 訳):
    # 口の約束: 形の崩れた入力はどの崩れでも 拒む と終わりの値 2（traceback と終わりの値 1 で抜けない）
    r = subprocess.run([sys.executable, "-I", str(根 / "道具" / "寄せ" / "突き合わせ.py"), 何], input=入力,
                       capture_output=True, text=True, cwd=根)
    assert r.returncode == 2 and 訳 in json.loads(r.stdout)["拒む"]
