"""見張り: 社員の 社保.厚年の標準報酬 の列（型の版 2・直し 2）を寄せる。作り物の値だけ。

- 版 0 の会社: 健保と厚年の等級が違う人（厚年は下限）でも「ぶつかり」で止まらず、厚年の値は 社保.厚年の標準報酬 へ移る
- 版 1 の会社: 直し 2 が列を足し、型の並びにそろえる（自己検査を版 1 の型から回して緑）
"""
import copy
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent
sys.path.insert(0, str(ここ.parent.parent / "道具" / "寄せ"))

sys.path.insert(0, str(ここ))
import 当てる  # noqa: E402
import 作り物の殻  # noqa: E402
import 直し as 直しの形  # noqa: E402
import 自己検査  # noqa: E402

今日 = dt.date(2026, 11, 11)
型の置き場 = ここ.parent.parent / "初期設定" / "型.json"


def 列(シート, 名):
    return [r[シート[0].index(名)] for r in シート[1:]]


def test_版0の健保と厚年の等級が違う人はぶつからず厚年の列へ移る():
    会社 = json.loads((ここ / "作り物の前の形.json").read_text(encoding="utf-8"))
    社員 = 会社["シート"]["03_マスタ"]["社員"]
    社員[1][社員[0].index("健保の標準報酬")] = "58000"
    社員[1][社員[0].index("厚年の標準報酬")] = "88000"
    r = 当てる.見通す(作り物の殻.前の形を渡す(会社), 当てる.型を開く(型の置き場), 直しの形.読む(), 今日)
    assert r["寄せられない物"] == [], r["寄せられない物"]
    後 = r["寄せた後の値"]["シート"]["03_マスタ"]["社員"]
    assert 列(後, "社保.標準報酬")[0] == "58000"
    assert 列(後, "社保.厚年の標準報酬")[0] == "88000"
    型の列 = [c["名"] for c in 当てる.型を読む(当てる.型を開く(型の置き場))["ファイル"]["03_マスタ"]["社員"]]
    assert 後[0][:len(型の列)] == 型の列  # 型の並び（型に無い前の列は後ろで人の答えを待つ）
    assert 後[0].index("社保.厚年の標準報酬") == 後[0].index("社保.標準報酬") + 1
    assert r["値の保ち"]["合う"]


def 版1の型(tmp: Path) -> Path:
    """今の型から 社保.厚年の標準報酬 を除き版を 1 にした、版 1 の型の写し（試験の中だけ）。"""
    d = tmp / "版1"
    shutil.copytree(型の置き場.parent, d, ignore=shutil.ignore_patterns("*.py", "__pycache__"))
    型 = json.loads((d / "型.json").read_text(encoding="utf-8"))
    型["版"] = 1
    (d / "型.json").write_text(json.dumps(型, ensure_ascii=False), encoding="utf-8")
    項 = json.loads((d / "項目.json").read_text(encoding="utf-8"))
    項["項目"] = [it for it in 項["項目"] if it["項目"] != "社保.厚年の標準報酬"]
    (d / "項目.json").write_text(json.dumps(項, ensure_ascii=False), encoding="utf-8")
    return d / "型.json"


def test_直し2は版1の型から今の型へ緑(tmp_path):
    前 = 当てる.型を開く(版1の型(tmp_path))
    r = 自己検査.全部(当てる.型を開く(型の置き場), 直しの形.読む(), 前)
    assert all(v == [] for v in r.values()), r


def test_版1の会社は直し2で列が足され値はそのまま(tmp_path):
    前 = 当てる.型を開く(版1の型(tmp_path))
    会社 = 自己検査.雛形(前)
    会社["会社"] = "作り物の会社"
    社員 = 会社["シート"]["03_マスタ"]["社員"]
    社員.append([""] * len(社員[0]))
    社員[1][0], 社員[1][1] = "作り物の会社", "0001"
    社員[1][社員[0].index("社保.標準報酬")] = "300000"
    before = copy.deepcopy(社員)
    r = 当てる.見通す(作り物の殻.前の形を渡す(会社), 当てる.型を開く(型の置き場), 直しの形.読む(), 今日)
    assert r["寄せられない物"] == []
    後 = r["寄せた後の値"]["シート"]["03_マスタ"]["社員"]
    assert r["寄せた後の値"]["型の版"] == 当てる.型を読む(当てる.型を開く(型の置き場))["版"]
    assert 列(後, "社保.標準報酬") == ["300000"] and 列(後, "社保.厚年の標準報酬") == [""]
    assert [c for c in 後[0] if c != "社保.厚年の標準報酬"] == before[0]
