"""出す前の照らしの 管理表の行 は、出す物の証明の回（月・賞与）で管理表のタブを分けて返す。値は作り物だけ。

防ぐ故障: 賞与の出荷の後に殻が管理表 月の状況 へ書き、同じ支給月の月の給与の行（取り込み・止まりの理由）を上書きする。
回が 1 つにそろわない出荷・回の読めない証明で、どのタブの行か分からないまま書く。
"""
import json

import pytest

from 手伝い import 根, 出す物, 入力, 場所  # noqa: F401

import 出す前の照らし as G  # noqa: E402

回のタブ = 場所.読む(根, "管理表.管理表").回のタブ


def test_月の出荷は月の状況_賞与の出荷は賞与の状況():
    assert G.回と管理表のタブ(入力(出す物("取り込み"), 出す物("支給控除一覧_雇用")), 回のタブ) == ("月", "月の状況", [])
    assert G.回と管理表のタブ(入力(出す物("賞与の取り込み")), 回のタブ) == ("賞与", "賞与の状況", [])


def test_回が1つにそろわない_読めない時は行を出さない():
    x = 入力(出す物("取り込み"), 出す物("賞与の取り込み"))
    回, タブ, 赤 = G.回と管理表のタブ(x, 回のタブ)
    assert (回, タブ) == (None, None) and "そろわない" in 赤[0]
    x = 入力(出す物("賞与の取り込み"))
    x["証明"]["賞与の取り込み"]["回"] = "賞与の 2 回目"
    回, タブ, 赤 = G.回と管理表のタブ(x, 回のタブ)
    assert タブ is None and 赤
    assert G.回と管理表のタブ(入力(出す物()), None)[2]   # 回のタブ の無い版のパック


@pytest.mark.parametrize("物, タブ", [("取り込み", "月の状況"), ("賞与の取り込み", "賞与の状況")])
def test_命令の管理表の行は回のタブと行を出す(monkeypatch, capsys, tmp_path, 物, タブ):
    monkeypatch.setattr(G, "照らす", lambda *a, **k: [])   # 照らしそのものは test_給与エージェント_出す前の照らし が見る
    f = tmp_path / "in.json"
    x = 入力(出す物(物))
    f.write_text(json.dumps(x, ensure_ascii=False), encoding="utf-8")
    置いた = [{"物": 物, "名": x["出す物"][0]["名"]["名"], "url": "https://example.invalid/1"}]
    assert G.main(["管理表の行", str(f), "--パック", str(根), "--置いた", json.dumps(置いた, ensure_ascii=False),
                   "--今の止まりの理由", ""]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["管理表のタブ"] == タブ and out["回"] == ("賞与" if タブ == "賞与の状況" else "月")
    # 月の出荷で有給休暇管理表を出さない時は、その訳が止まりの理由の頭に残る（賞与は有給を出さない回＝付けない）
    頭 = "有給休暇管理表は出していない: 有給の値を渡さずに回した" if タブ == "月の状況" else ""
    assert out["管理表の行"]["取り込み"] == "済" and out["管理表の行"]["止まりの理由"] == 頭
    # 物ごとの今の版とリンクはタブ 出した物 の行（回の状況のタブの止まりの理由には書かない）
    assert out["出した物のタブ"] == "出した物"
    assert out["出した物の行"] == [{"会社": x["会社"], "支給月": x["支給月"], "回": out["回"], "物": 物,
                                    "今の版": 置いた[0]["名"], "リンク": 置いた[0]["url"]}]


def test_命令の管理表の行は置いた物が出す物より少なければ行を出さない(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(G, "照らす", lambda *a, **k: [])
    x = 入力(出す物("取り込み"), 出す物("支給控除一覧_雇用"), 出す物("有給休暇管理表"))
    f = tmp_path / "in.json"
    f.write_text(json.dumps(x, ensure_ascii=False), encoding="utf-8")
    置いた = [{"物": d["物"], "名": d["名"]["名"], "url": "https://example.invalid/1"} for d in x["出す物"][:2]]
    for 渡す in (["--置いた", json.dumps(置いた, ensure_ascii=False)], ["--置いた", "{壊れた"], []):
        assert G.main(["管理表の行", str(f), "--パック", str(根), *渡す, "--今の止まりの理由", ""]) == 2
        out = json.loads(capsys.readouterr().out)
        assert not out["通す"] and "管理表の行" not in out and "出した物の行" not in out
