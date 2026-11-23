"""口の約束（bin/口の約束.py）の試験。作り物の口と作り物の殻の表だけ。

防ぐ故障: 口の一覧の守る事を変えた・消したのに、殻の試験を見直さずに通る。殻が確かめていない条を黙って残す。
  試験の名だけ書いて試験が無い。口の一覧が指すパックの部品の名が消えたのに文が残る。表の形が崩れた行を黙って捨てる。
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
    return {"覆い": [{"口": c["口"], "指紋": c["指紋"], "試験": ["tests/test_作り物.py::test_作り物"]}
                     for c in 条 if c["指紋"] not in 穴],
            "穴": [{"口": c["口"], "指紋": c["指紋"], "訳": "作り物の訳"} for c in 条 if c["指紋"] in 穴]}


def test_条に分ける_括弧の中の句点では切らない_末の句点で指紋は変わらない():
    条 = K.条たち(作り物の一覧)
    assert [(c["欄"], c["文"]) for c in 条] == [("渡す物", "在り処"), ("返す物", "行"), ("守る事", "書いた値を返す"),
                                              ("守る事", "読み直す（作り物。括弧の中の文）")]
    末なし = K.条たち(作り物の一覧.replace("の文）。 |", "の文） |"))
    assert [c["指紋"] for c in 末なし] == [c["指紋"] for c in 条]


def test_全部の条を覆えば緑_穴は訳つきで緑():
    条 = K.条たち(作り物の一覧)
    assert K.照らす(条, _殻の表(条)) == []
    assert K.照らす(条, _殻の表(条, 穴={条[-1]["指紋"]})) == []


def test_注入_守る事の文を変えると古い指紋と確かめていない条で赤():
    条 = K.条たち(作り物の一覧)
    表 = _殻の表(条)
    新 = K.条たち(作り物の一覧.replace("書いた値を返す", "書式の値を返す"))
    外れ = K.照らす(新, 表)
    assert any("今の口の一覧に無い指紋" in x for x in 外れ) and any("殻が確かめていない条" in x for x in 外れ), 外れ


def test_注入_条を消すと古い指紋で赤_条を足すと確かめていない条で赤():
    条 = K.条たち(作り物の一覧)
    表 = _殻の表(条)
    消した = K.条たち(作り物の一覧.replace("書いた値を返す。", ""))
    assert [x for x in K.照らす(消した, 表) if "今の口の一覧に無い指紋" in x]
    足した = K.条たち(作り物の一覧.replace("読み直す", "1 件ずつ置く。読み直す"))
    assert [x for x in K.照らす(足した, 表) if "1 件ずつ置く" in x]


def test_注入_試験の無い覆い_訳の無い穴_同じ指紋の2度_違う口で赤():
    条 = K.条たち(作り物の一覧)
    表 = _殻の表(条, 穴={条[0]["指紋"]})
    表["覆い"][0]["試験"] = []
    表["穴"][0]["訳"] = " "
    表["覆い"].append(dict(表["覆い"][1]))
    表["覆い"][2]["口"] = "作り物の別の口"
    外れ = K.照らす(条, 表)
    assert any("試験が無い" in x for x in 外れ) and any("訳が無い" in x for x in 外れ)
    assert any("2 度" in x for x in 外れ) and any("口「作り物を読む」の条" in x for x in 外れ), 外れ


def test_注入_殻の根を渡すと試験の在り処を照らす(tmp_path):
    条 = K.条たち(作り物の一覧)
    表 = _殻の表(条)
    assert any("試験の file が無い" in x for x in K.照らす(条, 表, tmp_path))
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_作り物.py").write_text("def test_別():\n    pass\n", encoding="utf-8")
    assert any("試験が無い: tests/test_作り物.py::test_作り物" in x for x in K.照らす(条, 表, tmp_path))
    (tmp_path / "tests" / "test_作り物.py").write_text("def test_作り物():\n    pass\n", encoding="utf-8")
    assert K.照らす(条, 表, tmp_path) == []


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
    表 = tmp_path / "表.json"
    表.write_text(json.dumps(_殻の表(条), ensure_ascii=False), encoding="utf-8")
    r = _回す("照らす", str(表), "--パック", str(根))
    assert r.returncode == 0 and r.stdout.startswith("緑: 条"), (r.stdout, r.stderr)
    表.write_text(json.dumps(_殻の表(条[1:]), ensure_ascii=False), encoding="utf-8")
    r = _回す("照らす", str(表), "--パック", str(根))
    assert r.returncode == 1 and "殻が確かめていない条" in r.stdout
    表.write_text("{壊れた", encoding="utf-8")
    assert _回す("照らす", str(表), "--パック", str(根)).returncode == 2
    assert _回す("照らす", str(表), "--パック", str(tmp_path)).returncode == 2   # パックが無い
    assert _回す("作り物").returncode == 2
