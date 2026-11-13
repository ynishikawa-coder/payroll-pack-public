"""② 見張り: 作り物の小さな原本 → 表 A・B（か月の数字の口・月の変動）が黙って変わらない。

期待は 見張り_期待.json。読み口を直して結果が変わるのが正しい時だけ、
`PAYROLL_IRIGUCHI_MIHARI_KAKINAOSU=1 python3 -m pytest tests/入口` で書き直し、差分を PR で見せる。
"""
import json
import os
from pathlib import Path

import pytest

import 入口_作り物 as 作
from 入口 import 口, PDFタイムカード, Excel出勤簿, 勤怠システムの月報, 集計済み勤怠表, メールとメモ, 手当控除の一覧, 日次の勤怠CSV

期待のファイル = Path(__file__).with_name("見張り_期待.json")


def 結果たち():
    c = 作.文脈()
    出勤簿 = Excel出勤簿.読む(作.出勤簿, c)
    メモ = メールとメモ.読む(作.連絡, c, 作.手当の辞書, 作.手当の単価)
    return {
        "PDFタイムカード": PDFタイムカード.読む([作.カード], c),
        "Excel出勤簿": 出勤簿,
        "勤怠システムの月報": 勤怠システムの月報.読む([作.月報], c),
        "日次の勤怠CSV": 日次の勤怠CSV.読む(作.日次のCSV, "勤怠_20261108_日次.csv", 作.文脈(つなぎ=作.つなぎ), 作.道具),
        "集計済み勤怠表": 集計済み勤怠表.読む(作.集計表, c, 作.集計表の対応, "60進", 見ない=("部署",)),
        "メールとメモ": メモ,
        "出勤簿にメモを重ねる": 口.重ねる(出勤簿, メモ),
        "手当控除の一覧": 手当控除の一覧.読む(作.手当, c, "変更_20261108_手当.pdf", 作.手当の辞書, 作.手当の単価),
    }


def 形(r: 口.結果) -> dict:
    return {
        "日": [[a[k] for k in 口.表Aの列] for a in r.日],
        "区間": [[b[k] for k in 口.表Bの列] for b in r.区間],
        "月の数字": [[x[k] for k in 口.月の数字の列] for x in r.月の数字],
        "月の変動": [[x[k] for k in 口.月の変動の列] for x in r.月の変動],
        "人ごとの支給控除": [[x[k] for k in 口.人ごとの支給控除の列] for x in r.人ごとの支給控除],
        "要確認": [[q["NO"], q["日付"], q["理由"]] for q in r.要確認],
        "人の状態": r.人の状態(),
    }


def test_見張り():
    今 = {k: 形(v) for k, v in 結果たち().items()}
    if os.environ.get("PAYROLL_IRIGUCHI_MIHARI_KAKINAOSU"):
        期待のファイル.write_text(json.dumps(今, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        pytest.skip("見張りの期待を書き直した")
    期待 = json.loads(期待のファイル.read_text(encoding="utf-8"))
    for k in 期待:
        assert 今[k] == 期待[k], k
    assert set(今) == set(期待)


def test_表A_B_の列は勤怠の形のまま_芯の数え方とツールの名を出さない():
    for r in 結果たち().values():
        for a in r.日:
            assert list(a) == 口.表Aの列
        for b in r.区間:
            assert list(b) == 口.表Bの列
        for row in r.日 + r.区間:
            for v in row.values():
                assert 作.道具 not in v
    for 芯の語 in ("深夜", "残業", "法定外", "法定休日の時間", "所定内"):
        assert 芯の語 not in 口.表Aの列 and 芯の語 not in 口.表Bの列


def test_全部の日に表Aの行が1つ():
    c = 作.文脈()
    for k in ("PDFタイムカード", "Excel出勤簿", "勤怠システムの月報", "日次の勤怠CSV"):
        r = 結果たち()[k]
        for no in {a["NO"] for a in r.日}:
            assert [a["日付"] for a in r.日 if a["NO"] == no] == c.日付たち(), (k, no)
