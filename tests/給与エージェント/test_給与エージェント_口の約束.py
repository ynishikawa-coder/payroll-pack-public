"""口の約束（bin/口の約束.py）の試験。作り物の口と作り物の殻の表だけ。

防ぐ故障: 口の一覧の守る事を変えた・消したのに、殻の試験を見直さずに通る。殻が確かめていない条を黙って残す。
  表に試験の名だけ書いて、名の在る試験が条と違う物を試していても通る（覆いは試験の本文の印だけで持つ）。
  印だけ在って確かめの無い試験（assert True・確かめから離れた印・docstring の印）や、skip・xfail で飛ばされる試験の印で通る。
  口の一覧が指すパックの部品の名が消えたのに文が残る。表の形が崩れた行を黙って捨てる。
"""
import json
import subprocess
import sys

import pytest

from 手伝い import BIN, PLUGIN, 根

import 口の約束 as K  # noqa: E402

作り物の一覧 = (
    "| 口 | 渡す物 | 返す物 | 守る事 |\n|---|---|---|---|\n"
    "| 〔口: 作り物を読む〕 | 在り処 | 行 | 書いた値を返す。読み直す（作り物。括弧の中の文）。 |\n"
)


def _殻の表(条, 穴=()):
    return {"穴": [{"口": c["口"], "指紋": c["指紋"], "訳": "作り物の訳"} for c in 条 if c["指紋"] in 穴]}


def _印(fp):
    return "口の約束 " + fp   # 試験の file の字に印の形をそのまま書かない（殻の根がパックを含む時に拾われない）


def _殻を作る(根の場所, 条, 外す=()):
    """作り物の殻: 条ごとに 1 つの試験が本文に印を持つ。"""
    d = 根の場所 / "tests"
    d.mkdir(parents=True, exist_ok=True)
    本文 = "".join(f"def test_作り物_{i}():\n    値 = 作り物を読む()\n    # {_印(c['指紋'])}\n    assert 値 == 1\n\n\n"
                  for i, c in enumerate(条) if c["指紋"] not in 外す)
    (d / "test_作り物.py").write_text("def 作り物を読む():\n    return 1\n\n\n" + 本文, encoding="utf-8")
    return 根の場所


def _照らす(条, 表, 殻):
    印, 外れ = K.印を集める(殻)
    return 外れ + K.照らす(条, 表, 印)


def test_条に分ける_括弧の中の句点では切らない_末の句点で指紋は変わらない():
    条 = K.条たち(作り物の一覧)
    assert [(c["欄"], c["文"]) for c in 条] == [("渡す物", "在り処"), ("返す物", "行"), ("守る事", "書いた値を返す"),
                                              ("守る事", "読み直す（作り物。括弧の中の文）")]
    末なし = K.条たち(作り物の一覧.replace("の文）。 |", "の文） |"))
    assert [c["指紋"] for c in 末なし] == [c["指紋"] for c in 条]


def test_全部の条に試験の印が在れば緑_穴は訳つきで緑(tmp_path):
    条 = K.条たち(作り物の一覧)
    assert _照らす(条, _殻の表(条), _殻を作る(tmp_path / "a", 条)) == []
    穴 = {条[-1]["指紋"]}
    assert _照らす(条, _殻の表(条, 穴), _殻を作る(tmp_path / "b", 条, 穴)) == []
    印, _ = K.印を集める(tmp_path / "a")
    assert 印[条[0]["指紋"]] == ["tests/test_作り物.py::test_作り物_0"]


def test_注入_守る事の文を変えると試験の印が古い指紋で赤(tmp_path):
    条 = K.条たち(作り物の一覧)
    殻 = _殻を作る(tmp_path, 条)
    新 = K.条たち(作り物の一覧.replace("書いた値を返す", "書式の値を返す"))
    外れ = _照らす(新, _殻の表(条), 殻)
    assert any(x.startswith("印: 今の口の一覧に無い指紋") and "test_作り物_2" in x for x in 外れ), 外れ
    assert any("殻が確かめていない条" in x and "書式の値を返す" in x for x in 外れ), 外れ


def test_注入_条を消すと古い指紋で赤_条を足すと確かめていない条で赤(tmp_path):
    条 = K.条たち(作り物の一覧)
    殻 = _殻を作る(tmp_path, 条)
    消した = K.条たち(作り物の一覧.replace("書いた値を返す。", ""))
    assert [x for x in _照らす(消した, {"穴": []}, 殻) if "今の口の一覧に無い指紋" in x]
    足した = K.条たち(作り物の一覧.replace("読み直す", "1 件ずつ置く。読み直す"))
    assert [x for x in _照らす(足した, {"穴": []}, 殻) if "1 件ずつ置く" in x]


def test_注入_印の無い試験は確かめていない条で赤(tmp_path):
    """名の在る試験を表に書くだけでは通らない＝試験の本文に印が要る（前の表の 覆い の穴）。"""
    条 = K.条たち(作り物の一覧)
    殻 = _殻を作る(tmp_path, 条, 外す={条[0]["指紋"]})
    (殻 / "tests" / "test_名だけ.py").write_text("def test_作り物の名だけ():\n    assert True\n", encoding="utf-8")
    外れ = _照らす(条, {"穴": []}, 殻)
    assert len(外れ) == 1 and 外れ[0].startswith(f"殻が確かめていない条 {条[0]['指紋']}"), 外れ


def test_注入_表に覆いを書くと赤_試験の外の印は赤(tmp_path):
    条 = K.条たち(作り物の一覧)
    殻 = _殻を作る(tmp_path, 条)
    表 = {"覆い": [{"口": 条[0]["口"], "指紋": 条[0]["指紋"], "試験": ["tests/test_作り物.py::test_作り物_0"]}], "穴": []}
    assert any("殻の表に 覆い が在る" in x for x in _照らす(条, 表, 殻))
    (殻 / "tests" / "test_外.py").write_text(f"# {_印(条[0]['指紋'])}\n\n\ndef _手伝い():\n    # {_印(条[1]['指紋'])}\n    pass\n",
                                          encoding="utf-8")
    外れ = _照らす(条, {"穴": []}, 殻)
    assert [x for x in 外れ if x.startswith("印が試験の外")] == [
        f"印が試験の外: tests/test_外.py:1 {_印(条[0]['指紋'])}（試験 def test_… の本文に置く）",
        f"印が試験の外: tests/test_外.py:5 {_印(条[1]['指紋'])}（試験 def test_… の本文に置く）"], 外れ


def test_注入_訳の無い穴_同じ指紋の2度_違う口_印と穴の両方で赤(tmp_path):
    条 = K.条たち(作り物の一覧)
    殻 = _殻を作る(tmp_path, 条, 外す={条[0]["指紋"]})
    表 = _殻の表(条, 穴={条[0]["指紋"]})
    表["穴"][0]["訳"] = " "
    表["穴"].append(dict(表["穴"][0], 口="作り物の別の口"))
    表["穴"].append({"口": 条[1]["口"], "指紋": 条[1]["指紋"], "訳": "作り物の訳"})
    外れ = _照らす(条, 表, 殻)
    assert any("訳が無い" in x for x in 外れ) and any("2 度" in x for x in 外れ)
    assert any("口「作り物を読む」の条" in x for x in 外れ), 外れ
    assert any(f"指紋 {条[1]['指紋']}" in x and "印で確かめている（穴から消す）" in x for x in 外れ), 外れ


def _一つの試験(殻, 本文, 頭=""):
    """作り物の殻の file に試験を 1 つ足す（本文の {印} を条 0 の印に置き換える）。"""
    (殻 / "tests" / "test_足す.py").write_text(頭 + 本文, encoding="utf-8")


@pytest.mark.parametrize("本文", [
    "def test_x():\n    # {印}\n    assert True\n",
    "def test_x():\n    # {印}\n    assert 1\n",
    "def test_x():\n    # {印}\n    assert 1 == 1\n",
    "def test_x():\n    # {印}\n    assert (作り物を読む() == 2, '訳')\n",
    "def test_x():\n    \"\"\"{印}\"\"\"\n    assert 作り物を読む() == 2\n",
    "def test_x():\n    # {印}\n    値 = 作り物を読む()\n    assert 値 == 2\n",
    "def test_x():\n    # {印}\n    作り物を読む()\n",
    "def test_x():\n    def 中():\n        assert 作り物を読む() == 2\n    # {印}\n    中()\n",
])
def test_注入_確かめの無い印_離れた印_docstringの印は数えず赤(tmp_path, 本文):
    条 = K.条たち(作り物の一覧)
    殻 = _殻を作る(tmp_path, 条, 外す={条[0]["指紋"]})
    _一つの試験(殻, 本文.replace("{印}", _印(条[0]["指紋"])), "from test_作り物 import 作り物を読む\n\n\n")
    外れ = _照らす(条, {"穴": []}, 殻)
    assert any(x.startswith("印が確かめに付いていない: tests/test_足す.py:") for x in 外れ), 外れ
    assert any(x.startswith(f"殻が確かめていない条 {条[0]['指紋']}") for x in 外れ), 外れ


@pytest.mark.parametrize("本文", [
    "def test_x():\n    # {印}\n    assert 作り物を読む() == 1\n",
    "def test_x():\n    assert 作り物を読む() == 1  # {印}\n",
    "def test_x():\n    # {印}\n    # 作り物の説明\n\n    assert (\n        作り物を読む() == 1\n    )\n",
    "def test_x():\n    # {印}\n    with pytest.raises(ValueError):\n        int('作り物')\n",
    "class Test作り物:\n    def test_x(self):\n        # {印}\n        self.assertEqual(作り物を読む(), 1)\n",
])
def test_確かめの真上か同じ行の印は数える(tmp_path, 本文):
    条 = K.条たち(作り物の一覧)
    殻 = _殻を作る(tmp_path, 条, 外す={条[0]["指紋"]})
    _一つの試験(殻, 本文.replace("{印}", _印(条[0]["指紋"])), "import pytest\nfrom test_作り物 import 作り物を読む\n\n\n")
    assert _照らす(条, {"穴": []}, 殻) == []


@pytest.mark.parametrize("頭, 本文, 訳", [
    ("", "@pytest.mark.skip(reason='作り物')\ndef test_x():\n    # {印}\n    assert 作り物を読む() == 1\n", "試験の飾り"),
    ("", "@pytest.mark.skipif(True, reason='作り物')\ndef test_x():\n    # {印}\n    assert 作り物を読む() == 1\n", "試験の飾り"),
    ("", "@pytest.mark.xfail\ndef test_x():\n    # {印}\n    assert 作り物を読む() == 1\n", "試験の飾り"),
    ("", "@pytest.mark.parametrize('v', [pytest.param(1, marks=pytest.mark.skip)])\n"
         "def test_x(v):\n    # {印}\n    assert 作り物を読む() == v\n", "試験の飾り"),
    ("", "@pytest.mark.xfail\nclass Test作り物:\n    def test_x(self):\n        # {印}\n        assert 作り物を読む() == 1\n",
     "class Test作り物 の飾り"),
    ("pytestmark = [pytest.mark.skip]\n", "def test_x():\n    # {印}\n    assert 作り物を読む() == 1\n", "module の pytestmark"),
    ("", "def test_x():\n    pytest.skip('作り物')\n    # {印}\n    assert 作り物を読む() == 1\n", "本文で skip を呼ぶ"),
    ("", "def test_x():\n    pytest.importorskip('作り物の無い部品')\n    # {印}\n    assert 作り物を読む() == 1\n",
     "本文で importorskip を呼ぶ"),
    ("", "def test_x():\n    if 作り物を読む():\n        pytest.xfail('作り物')\n    # {印}\n    assert 作り物を読む() == 1\n",
     "本文で xfail を呼ぶ"),
])
def test_注入_飛ばされる試験の印は数えず赤(tmp_path, 頭, 本文, 訳):
    条 = K.条たち(作り物の一覧)
    殻 = _殻を作る(tmp_path, 条, 外す={条[0]["指紋"]})
    _一つの試験(殻, 本文.replace("{印}", _印(条[0]["指紋"])), "import pytest\nfrom test_作り物 import 作り物を読む\n" + 頭 + "\n\n")
    外れ = _照らす(条, {"穴": []}, 殻)
    assert any(x.startswith("印の試験が飛ばされる: tests/test_足す.py::test_x（" + 訳) for x in 外れ), 外れ
    assert any(x.startswith(f"殻が確かめていない条 {条[0]['指紋']}") for x in 外れ), 外れ


def test_印は依存や隠しのdirの試験から拾わない(tmp_path):
    条 = K.条たち(作り物の一覧)
    殻 = _殻を作る(tmp_path, 条, 外す={条[0]["指紋"]})
    for d in ("node_modules/x", ".venv/y", ".git/z"):
        (殻 / d).mkdir(parents=True)
        (殻 / d / "test_外す.py").write_text(f"def test_外す():\n    # {_印(条[0]['指紋'])}\n    pass\n", encoding="utf-8")
    assert any("殻が確かめていない条" in x for x in _照らす(条, {"穴": []}, 殻))


def test_注入_表の形が崩れた行は黙って捨てずに止める():
    with pytest.raises(ValueError, match="列"):
        K.条たち(作り物の一覧.replace(" | 行 |", " 行 |"))
    with pytest.raises(ValueError, match="空"):
        K.条たち(作り物の一覧.replace("| 行 |", "|  |"))
    with pytest.raises(ValueError, match="1 つも無い"):
        K.条たち("| 口 | 渡す物 |\n")


def test_本物の口の一覧は分けられ_指す部品の名が全部在る():
    text = (PLUGIN / "口の一覧.md").read_text(encoding="utf-8")
    条 = K.条たち(text)
    assert len({c["指紋"] for c in 条}) == len(条)   # 同じ指紋の条が無い
    assert K.死んだ名(根, text) == []


def test_注入_指す部品の名が消えると赤(tmp_path):
    for p in ("初期設定/項目.json", "初期設定/型の口.py", "管理表/管理表.py", "月次/__init__.py"):
        (tmp_path / p).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / p).write_text((根 / p).read_text(encoding="utf-8"), encoding="utf-8")
    行 = ("| 〔口: 作り物〕 | `初期設定/型の口.py` の `書いた値を照らす` | `管理表/管理表.py 書く・寄せの印` | "
         "`月次.月を回す` と `突き合わせ.差0の月数の目安` と `結果.問い` |\n")
    assert K.死んだ名(tmp_path, 行) == []
    壊す = 行.replace("書いた値を照らす", "作り物の消えた名").replace("寄せの印", "作り物の口").replace("月を回す", "作り物を回す")
    assert K.死んだ名(tmp_path, 壊す) == ["初期設定/型の口.py に 作り物の消えた名 が無い", "管理表/管理表.py に口 作り物の口 が無い",
                                         "月次 に 作り物を回す が無い"]
    assert K.死んだ名(tmp_path, 行.replace("初期設定/型の口.py", "作り物/無い.py")) == ["指す file が無い: 作り物/無い.py"]


def _回す(*a, 入力=None):
    return subprocess.run([sys.executable, str(BIN / "口の約束.py"), *a], capture_output=True, text=True, input=入力)


def test_道具の終わりの値_緑0_赤1_壊れた2(tmp_path):
    r = _回す("一覧", "--パック", str(根))
    assert r.returncode == 0, r.stderr
    条 = json.loads(r.stdout)
    殻 = _殻を作る(tmp_path / "殻", 条)
    表 = tmp_path / "表.json"
    表.write_text(json.dumps({"穴": []}, ensure_ascii=False), encoding="utf-8")
    r = _回す("照らす", str(表), "--パック", str(根), "--殻の根", str(殻))
    assert r.returncode == 0 and r.stdout.startswith("緑: 条"), (r.stdout, r.stderr)
    _殻を作る(殻, 条, 外す={条[0]["指紋"]})
    r = _回す("照らす", str(表), "--パック", str(根), "--殻の根", str(殻))
    assert r.returncode == 1 and "殻が確かめていない条" in r.stdout
    assert _回す("照らす", str(表), "--パック", str(根)).returncode == 2   # 殻の根が無い＝印を見ずに緑にしない
    assert _回す("照らす", str(表), "--パック", str(根), "--殻の根", str(tmp_path / "無い")).returncode == 2
    表.write_text("{壊れた", encoding="utf-8")
    assert _回す("照らす", str(表), "--パック", str(根), "--殻の根", str(殻)).returncode == 2
    assert _回す("照らす", str(表), "--パック", str(tmp_path), "--殻の根", str(殻)).returncode == 2   # パックが無い
    assert _回す("作り物").returncode == 2
