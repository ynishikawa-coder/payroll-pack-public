"""型の版 28: 2_マスタ「社員」の 育休の始め・育休の終わり・産休の始め・産休の終わり を段の解決が芯の名へ渡す（列が型に在り、芯が読む）。"""
import importlib.util
import json
from pathlib import Path

根 = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("初期設定_段の解決_産休育休", 根 / "初期設定" / "段の解決.py")
段 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(段)

C = "作り物の会社"
列 = {"育休の始め": "社保.育休の始め", "育休の終わり": "社保.育休の終わり", "産休の始め": "社保.産休の始め", "産休の終わり": "社保.産休の終わり"}


def test_社員のタブに4列が在り段の解決が芯の名へ渡す():
    型 = json.loads((根 / "初期設定" / "型.json").read_text(encoding="utf-8"))
    社員 = next(t for sh in 型["シート"] for t in sh["タブ"] if t["タブ"] == "社員")
    assert set(列) <= {c["名"] for c in 社員["列"]}
    assert all(段.社員の列の名[k] == v for k, v in 列.items())
    r = 段.解く("2027.02支給", 社員=[{"会社": C, "NO": "0001", "氏名": "作り物 一郎", "育休の始め": "2027-01-05",
                                     "育休の終わり": "2027-03-31", "産休の始め": "", "産休の終わり": ""}])
    p = r["人"][(C, "0001")]
    assert p["社保.育休の始め"] == "2027-01-05" and p["社保.育休の終わり"] == "2027-03-31"
    assert "社保.産休の始め" not in p   # 空は渡さない＝免除しない


def test_芯は渡された育休の日で免除を数える():
    from 芯.計算.支給控除 import 産休育休の免除
    assert 産休育休の免除({"社保.育休の始め": "2027-01-05", "社保.育休の終わり": "2027-03-31"}, (2027, 1), False)[0] == "育休"
