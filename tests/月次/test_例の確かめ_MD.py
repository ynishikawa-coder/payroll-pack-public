"""例の確かめ: 給与のルール.md の例の表を読む口（月次/例の確かめ.py の MDから例を読む）の試験。作り物の会社 C1 の値だけ。

根: 例は 前のマスタ「例」のタブでなく 給与のルール.md の決まりごとの見出しの下の表に書く（人は MD を読まない・形は AI が決める）。
MD は字なので、列の欠け・見出しの外の表・升の数の違う行が黙って読み落とされると、例の照らしが黙って減る。
ここでは MD の字 → 例の行 → 確かめる の往復が通ることと、その誤りの類をわざと入れて会社が出口へ出ない（通った=False）ことを見る。
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(根))
sys.path.insert(0, str(根 / "tests" / "計算"))
sys.path.insert(0, str(根 / "tests" / "集計"))
_spec = importlib.util.spec_from_file_location("例の確かめ_MD_試験_作り物", 根 / "tests" / "初期設定" / "test_初期設定_給与の関所.py")
作 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(作)

import 作る_集計  # noqa: E402
import 月次  # noqa: E402

例の確かめ = 月次.例の確かめ
読む = 例の確かめ.MDから例を読む
C, 支給月 = 作.C, 作.支給月
列 = list(例の確かめ.MDの例の列)


def _確かめる(例, **タブの上書き):
    return 例の確かめ.確かめる(支給月, C, 作._タブ(**タブの上書き), 例, 法の線=作る_集計.法の線, 段=月次.段, 繋=月次.繋,
                          確かめてよい人=作._名簿())


def _作の行() -> list[dict]:
    見出し, *行 = 作._例()
    return [dict(zip(見出し, r)) for r in 行]


def _決まりの名(決まり: str) -> tuple[str, str]:
    """作り物の 決まり `給与のルール.md#2 始業前の打刻（時間.…）` → (見出し, 名の並び)。"""
    m = re.match(r"^給与のルール\.md#(.+?)（(.*)）$", 決まり)
    return m.group(1), m.group(2)


def _表(行たち, 列たち=None) -> str:
    列たち = 列たち or 列
    out = ["| " + " | ".join(列たち) + " |", "|" + "---|" * len(列たち)]
    out += ["| " + " | ".join(str(r.get(c, "")) for c in 列たち) + " |" for r in 行たち]
    return "\n".join(out)


def _md(行たち=None, 列たち=None) -> str:
    """作り物の例を 給与のルール.md の形（決まりごとの ### と文と表）にした字。"""
    out = ["# 給与のルール（作り物の組）", "", "## 1 支払の枠", ""]
    for r in 行たち or _作の行():
        見出し, 名 = _決まりの名(r["決まり"])
        out += [f"### {見出し}", "", "作り物の決まりの文。", "", _表([{**r, "決まり": 名}], 列たち), ""]
    return "\n".join(out)


# --- 往復: MD の字 → 例の行 → 確かめる ---

def test_MD_の例は例の行になり確かめるを通る():
    行 = 読む(_md(), 会社=C)
    assert [r["例の番号"] for r in 行] == ["E1", "E2"]
    assert all(set(r) == set(例の確かめ.例の列) and r["会社"] == C for r in 行)
    # 読んだ行は 前のマスタ「例」の行と同じ（決まり は 給与のルール.md#<見出し>（名） の形に戻る）
    assert 行 == _作の行()
    assert _確かめる(行) == {"通った": True, "数": 2, "合わない": [], "止め": []}


def test_MD_から読んだ例も取り違えたマスタを止める():
    r = _確かめる(読む(_md(), 会社=C), 型={"日勤": {"時間.始業前の打刻": "打刻のまま"}})
    assert not r["通った"] and [x["例の番号"] for x in r["合わない"]] == ["E1"]


def test_雛形の注の中の作り物の例は読まない_空の雛形は止まる():
    字 = (根 / "初期設定" / "雛形" / "給与のルール.md").read_text(encoding="utf-8")
    assert 読む(字, 会社=C) == []
    r = _確かめる(読む(字, 会社=C))
    assert not r["通った"] and "1 つも無い" in r["止め"][0]


def test_雛形の注の作り物の例は注を外せば例の行として読める():
    字 = (根 / "初期設定" / "雛形" / "給与のルール.md").read_text(encoding="utf-8")
    注 = "\n".join(l.strip() for l in re.findall(r"<!--(.*?)-->", 字, flags=re.S)[-1].splitlines())
    (r,) = 読む(注, 会社=C)
    assert r["例の番号"] == "E1" and r["種類"] == "日" and r["決まり"].startswith("給与のルール.md#始業前の打刻（")
    assert r["確かめた人"] == "作り物 確かめる人" and not r["備考"]


def test_コードの囲みの中の表は読まない():
    字 = _md() + "\n### 囲み\n\n```\n" + _表([{**_作の行()[0], "例の番号": "E9"}]) + "\n```\n"
    assert [r["例の番号"] for r in 読む(字, 会社=C)] == ["E1", "E2"]


def test_会社が空なら止める():
    with pytest.raises(例の確かめ.例の誤り):
        読む(_md(), 会社=" ")


# --- 注入: 読めない MD は既定で止める（会社を出さない） ---

def _止まる(字, 含む: str):
    行 = 読む(字, 会社=C)
    r = _確かめる(行)
    assert not r["通った"]
    読めない = [x for x in r["合わない"] if x["訳"].startswith(例の確かめ.読めない印)]
    assert 読めない and any(含む in x["訳"] for x in 読めない), r["合わない"]
    return r


def test_列の欠けた表は止まる():
    _止まる(_md(列たち=[c for c in 列 if c != "確かめた人"]), "無い列: 確かめた人")


def test_外の列のある表は止まる():
    # 確かめた日 を 確かめ日 と書き違えた＝外の列と欠けの両方
    字 = _md().replace("| 確かめた日 |", "| 確かめ日 |")
    _止まる(字, "外の列: 確かめ日")


def test_同じ列が2つある表は止まる():
    _止まる(_md(列たち=[*列, "備考"]), "2 つある列: 備考")


def test_見出しの外の表は止まる():
    字 = _md() + "\n## 3 休日と時間外\n\n" + _表([{**_作の行()[0], "例の番号": "E9", "決まり": "時間.始業前の打刻"}]) + "\n"
    r = _止まる(字, "見出しの下に無い")
    assert any(x["決まり"] == "（見出しの外）" for x in r["合わない"])


def test_見出しの前の表は止まる():
    _止まる(_表([{**_作の行()[0], "決まり": "時間.始業前の打刻"}]) + "\n\n" + _md(), "見出しの下に無い")


def test_区切りの行の無い表は止まる():
    字 = _md().replace("\n|" + "---|" * len(列) + "\n", "\n", 1)
    _止まる(字, "区切り")


def test_升の数の違う行は止まる_ほかの行は読む():
    字 = _md().replace("| E2 |", "| E2 | 余り |", 1)
    行 = 読む(字, 会社=C)
    assert [r["例の番号"] for r in 行 if r["種類"] != "書けない"] == ["E1"]
    _止まる(字, "升の数")


def test_読めない印の無い書けないの行はマスタに書けないの訳のまま():
    r = _確かめる([*_作の行(), {"会社": C, "例の番号": "E3", "決まり": "給与のルール.md#9 x", "種類": "書けない",
                              "確かめた日": "2026-11-01", "備考": ""}])
    assert any("マスタに書けない" in x["訳"] for x in r["合わない"])


# --- 見分けの照らしが読む 型で引く名: 書き方を変えても黙って減らない ---

def test_型で引く名は今の芯の集計で正規表現より減らない():
    fs = sorted((根 / "芯" / "集計").glob("*.py"))
    字 = "".join(p.read_text(encoding="utf-8") for p in fs)
    前の = set(re.findall(r'\.引く\("([^"]+)",\s*型', 字))
    assert 前の <= 例の確かめ.型で引く名(fs)


def _芯(tmp_path, 本文: str):
    p = tmp_path / "x.py"
    p.write_text("class 決まり:\n    def 引く(self, 名, 型=None):\n        return None\n\n" + 本文, encoding="utf-8")
    return [p]


def test_型で引く名は書き方を変えても拾う(tmp_path):
    本文 = ("def f(決, 型):\n"
          "    決.引く(\n        \"時間.甲\",\n        型)\n"   # 改行を挟む（前の正規表現は落とした）
          "    決.引く(\"時間.乙\", 型=型)\n"                    # 名で渡す
          "    決.引く(\"時間.丙\", 決の型)\n"                   # 型の変数の名が違う
          "    決.引く(\"時間.丁\")\n"                           # 型で引かない
          "    決.引く(\"時間.戊\", None)\n")                    # 型で引かない
    assert 例の確かめ.型で引く名(_芯(tmp_path, 本文)) == {"時間.甲", "時間.乙", "時間.丙"}


def test_名が字でない引き方は止める(tmp_path):
    with pytest.raises(例の確かめ.引き方が読めない):
        例の確かめ.型で引く名(_芯(tmp_path, "名たち = ['時間.甲']\ndef f(決, 型):\n    for n in 名たち:\n        決.引く(n, 型)\n"))


def test_引く口が無ければ止める(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("def f():\n    return 1\n", encoding="utf-8")
    with pytest.raises(例の確かめ.引き方が読めない):
        例の確かめ.型で引く名([p])


def test_名の引数の名が違う包みも口として拾う(tmp_path):
    # レビューの赤 1: `def _引(n, 型): return 決.引く(n, 型)` を `_引("名", 型)` で呼ぶと、前は口として拾わず黙って落とした
    本文 = ("def _引(決, n, 型):\n    return 決.引く(n, 型)\n\n"
          "def _引2(決, 名前, 型x=None):\n    return _引(決, 名前, 型=型x)\n\n"   # 包みの包み・名で渡す
          "def _型なし(決, n):\n    return 決.引く(n)\n\n"                       # 型で引かない包み
          "def f(決, 型):\n"
          "    _引(決, \"時間.甲\", 型)\n"
          "    _引2(決, \"時間.乙\", 型)\n"
          "    _引2(決, \"時間.丙\")\n"
          "    _型なし(決, \"時間.丁\")\n")
    assert 例の確かめ.型で引く名(_芯(tmp_path, 本文)) == {"時間.甲", "時間.乙"}


def test_口でない関数の中の名が字でない引き方は止める(tmp_path):
    # 引数を加工して渡す（そのまま渡す包みでない）＝どの名を引くか読めない
    with pytest.raises(例の確かめ.引き方が読めない):
        例の確かめ.型で引く名(_芯(tmp_path, "def f(決, n, 型):\n    決.引く(\"時間.\" + n, 型)\n"))


def test_包みが型の位置へ引数でもNoneでもない物を渡すと止める(tmp_path):
    with pytest.raises(例の確かめ.引き方が読めない):
        例の確かめ.型で引く名(_芯(tmp_path, "def _引(決, n):\n    return 決.引く(n, 決.型)\n\ndef f(決):\n    _引(決, \"時間.甲\")\n"))


def test_同じ名の別の関数の引くは口に数えない(tmp_path):
    # 芯/集計/法の線の橋.py は 芯/計算 の関数 `引く(表の名, 日, …)` を呼ぶ＝決まり.引く（メソッド）と取り違えない
    本文 = "from 外 import 引く\n\ndef f(決, 表の名, 日, 型):\n    引く(表の名, 日)\n    決.引く(\"時間.甲\", 型)\n"
    assert 例の確かめ.型で引く名(_芯(tmp_path, 本文)) == {"時間.甲"}


def _二つ(tmp_path, b: str):
    """a.py（決まり.引く と 名の引数を n で受ける包み _引）と、それを呼ぶ b.py。"""
    a = tmp_path / "a.py"
    a.write_text("class 決まり:\n    def 引く(self, 名, 型=None):\n        return None\n\n"
                 "def _引(決, n, 型):\n    return 決.引く(n, 型)\n", encoding="utf-8")
    bp = tmp_path / "b.py"
    bp.write_text(b, encoding="utf-8")
    return [a, bp]


_名 = {"時間.甲", "時間.乙", "時間.丙"}


def test_モジュールの包みを呼ぶ形も拾う(tmp_path):
    # レビューの赤 2: `a._引("名", 型)` は前は拾わず止めもしなかった
    fs = _二つ(tmp_path, "import a\n\ndef f(決, 型):\n    a._引(決, \"時間.甲\", 型)\n")
    assert 例の確かめ.型で引く名(fs, 名たち=_名) == {"時間.甲"}


def test_別名で読み込んだ包みを呼ぶ形も拾う(tmp_path):
    # レビューの赤 2: `from a import _引 as 引き` の `引き("名", 型)` は前は set() で止まらなかった
    fs = _二つ(tmp_path, "from a import _引 as 引き\n\ndef f(決, 型):\n    引き(決, \"時間.甲\", 型)\n")
    assert 例の確かめ.型で引く名(fs, 名たち=_名) == {"時間.甲"}


@pytest.mark.parametrize("b", [
    # 口を通らず決まりの値を直に読む
    "def f(決, 型):\n    return 決.値たち['勤務の型'][型]['時間.甲']\n",
    # 呼び方が分からない口（関数を値として渡して呼ぶ）
    "import a\n\ndef f(決, 型):\n    g = a._引\n    return g(決, \"時間.甲\", 型)\n",
    # 名の字を変数に置いてから渡す
    "def f(決, 型):\n    n = \"時間.甲\"\n    return 決.引く(n, 型)\n",
])
def test_見分けの元の名の字が口の名でない所にあれば止める(tmp_path, b):
    with pytest.raises(例の確かめ.引き方が読めない):
        例の確かめ.型で引く名(_二つ(tmp_path, b), 名たち=_名)


def test_承知の印を読む所の名の字は止めない(tmp_path):
    b = ("def 承知か(決, 線, 型=None):\n    return False\n\n"
         "def f(決, 承知の印):\n    承知か(決, \"時間.甲\")\n    承知の印.読む(決)[0].get(\"時間.乙\", \"\")\n")
    assert 例の確かめ.型で引く名(_二つ(tmp_path, b), 名たち=_名) == set()


def test_印の列は書いても書かなくても読める():
    # 印 は任意の列（前の MD の表は印の列が無くても読める＝上の往復の試験）。書いた表は印を例の行へ渡す
    行 = [{**r, "印": "早退" if r["例の番号"] == "E1" else ""} for r in _作の行()]
    読んだ = 読む(_md(行, 列 + ["印"]), 会社=C)
    assert [r.get("印") for r in 読んだ] == ["早退", ""]
    assert all(r["種類"] != "書けない" for r in 読んだ)
    # 任意の列のほかの外の列は今までどおり読めない
    読んだ = 読む(_md(_作の行(), 列 + ["しるし"]), 会社=C)
    assert all(r["種類"] == "書けない" and "外の列: しるし" in r["備考"] for r in 読んだ)
