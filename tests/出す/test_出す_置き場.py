"""出口/出す.py の main を、作り物の Drive（drive口 の 00_事務所/事務所の設定 の 置き場 の表と、会社の 1_決まり・2_マスタ・
台帳_<年>・3_月ごと/<月>/2_出す物・9_履歴）の上で 1 命令で通す試験。値は全部作り物（実の id・会社の名を持たない）。

防ぐ故障: drive口.置き場.会社の置き場 が返す物の名（2_マスタ・台帳_<年>・事務所の設定・1_決まり・3_月ごと）と
  出す.py が読む鍵（マスタ・台帳・事務所・給与のルール・作業のルール・質問と回答・2_出す物）が食い違い、本物の置き場の表から
  1 命令で読む→回す→書く が「置き場: … が無い」で必ず止まる。月のフォルダが 1 つに決まらないのに選んで書く。
回すは作り物（tests/出す/test_出す.py の 回す口）。照らしは本物。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_出す as 元  # noqa: E402

from drive口.作り物 import 作り物のDrive  # noqa: E402
from 初期設定 import 型の口  # noqa: E402

手, 出す = 元.手, 元.出す
一覧の頭 = 型の口.見出し("事務所の設定", "会社の一覧")
置き場の頭 = 型の口.見出し("事務所の設定", "置き場")
_版 = 元._版   # 版を作り物に（autouse）


def _行(頭, **値):
    return [値.get(c, "") for c in 頭]


def _事務所(月のフォルダ=("2099.01支給（12月分）",)):
    d = 作り物のDrive()
    根 = d.根を作る()
    事 = d.フォルダを作る(根, 型の口.名("事務所"))
    設定 = d.シートを作る(事, 型の口.名("事務所の設定"))
    管理 = d.シートを作る(事, 型の口.名("管理表"))
    d.表へ書く(管理, "'月の状況'!A1", [元.月の見出し, [手.会社, 手.月, "", "", "", ""]])
    d.表へ書く(管理, "'出した物'!A1", [元.出した物の見出し])
    組 = d.フォルダを作る(d.フォルダを作る(根, 型の口.名("会社たち")), "作り物の組")
    ids = {x: d.フォルダを作る(組, 型の口.名(x)) for x in ("決まり", "月ごと", "履歴")}
    ids["マスタ"] = d.シートを作る(組, 型の口.名("マスタ"))
    ids["台帳"] = d.シートを作る(組, 型の口.台帳の名(2099))
    for k in ("給与のルール", "作業のルール"):
        ids[k] = d.ファイルを置く(ids["決まり"], 型の口.名(k), "作り物".encode(), "text/markdown")
    ids["質問と回答"] = d.シートを作る(ids["決まり"], 型の口.名("質問と回答"))
    for 月 in 月のフォルダ:
        m = d.フォルダを作る(ids["月ごと"], 月)
        for 名 in 型の口.物たち("月の物"):
            ids[f"{月}/{名}"] = d.フォルダを作る(m, 名)
    行 = [("会社の根", 組), *[(型の口.名(x), ids[x]) for x in ("決まり", "月ごと", "履歴", "マスタ")],
          (型の口.台帳の名(2099), ids["台帳"])]
    d.物[設定]["タブ"] = {
        "既定": [], "会社の一覧": [一覧の頭, _行(一覧の頭, 顧客ID="C9001", 会社=手.会社, 組="作り物の組")],
        "置き場": [置き場の頭, *[_行(置き場の頭, 顧客ID="C9001", 会社=手.会社, 組="作り物の組", 物=物, ID=i)
                               for 物, i in 行]]}
    return d, 根, {**ids, "設定": 設定, "管理表": 管理}


def _main(monkeypatch, tmp_path, d, 根, 受け):
    import drive口
    monkeypatch.setattr(drive口, "開く", lambda **_: d)
    回す = 元.回す口()

    def 読んで回す(口, 置き場, 会社, 支給月, 回):
        受け.update(置き場)
        return 回す(口, 置き場, 会社, 支給月, 回)
    monkeypatch.setattr(出す, "読んで回す", 読んで回す)
    材料 = tmp_path / "課題の材料.json"
    材料.write_text(json.dumps(元.課題, ensure_ascii=False), encoding="utf-8")
    return 出す.main(["--会社", 手.会社, "--支給月", "2099-01", "--回", "給与", "--根", 根, "--課題の材料", str(材料)])


def test_置き場の表から1命令で読む_回す_書く(monkeypatch, tmp_path, capsys):
    d, 根, ids = _事務所()
    受け = {}
    code = _main(monkeypatch, tmp_path, d, 根, 受け)
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["出した"] is True, out
    名と版 = 元.名と版
    出す物 = ids[f"2099.01支給（12月分）/{名と版.出す置き場}"]
    assert {k: 受け.get(k) for k in ("マスタ", "台帳", "事務所", "給与のルール", "作業のルール", "質問と回答",
                                    名と版.出す置き場, 名と版.履歴の置き場, "管理表")} == {
        "マスタ": ids["マスタ"], "台帳": ids["台帳"], "事務所": ids["設定"], "給与のルール": ids["給与のルール"],
        "作業のルール": ids["作業のルール"], "質問と回答": ids["質問と回答"], 名と版.出す置き場: 出す物,
        名と版.履歴の置き場: ids["履歴"], "管理表": ids["管理表"]}
    assert d.名で引く(出す物, out["置いた"][0]["名"]) is not None   # 月の 2_出す物 へ書いた


@pytest.mark.parametrize("月のフォルダ", [(), ("2099.01支給（12月分）", "2099.01支給（1月分）")])
def test_月のフォルダが1つに決まらなければ何も作らず止める(monkeypatch, tmp_path, capsys, 月のフォルダ):
    d, 根, _ = _事務所(月のフォルダ)
    前 = {k: (v["name"], v["親"]) for k, v in d.物.items()}
    code = _main(monkeypatch, tmp_path, d, 根, {})
    out = json.loads(capsys.readouterr().out)
    assert code == 2 and out["出した"] is False
    assert any(f"{len(月のフォルダ)} つ" in r for r in out["赤"]), out
    assert {k: (v["name"], v["親"]) for k, v in d.物.items()} == 前
