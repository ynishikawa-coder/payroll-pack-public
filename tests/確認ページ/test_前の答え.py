"""前の答えを照らす口（確認ページ/前の答え.py・qa-prior/1）の試験。表は作り物だけ。

防ぐ故障: 質問と回答で答え済みの問いを、同じ鍵・新しい鍵・言い回しを変えた字で事務所の担当者へ出す。「分からない」や出し直しの行を
答え済みと数えて聞くべき問いを落とす。表が渡されない・読めない時に黙って全部 checked にする（check.mjs が緑にしてしまう）。
値の表の命令（prior_check_cmd）が実際にこの口を呼ぶ事も、命令の字のまま走らせて見る。
"""
import io
import json
import os
import subprocess
import sys
from pathlib import Path

根 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(根 / "確認ページ"))
import 前の答え as P  # noqa: E402
sys.path.insert(0, str(根))
from 初期設定 import 質問と回答 as qa  # noqa: E402

# 行 = (問いの鍵, 顧客ID, 対象, 問いの文, 回答, 反映先)。回答が空なら答え の行は無い。対象 か 反映先 があれば 振り分け の行を書く
ROWS = [
    ("Q1", "作り物の会社", "会社", "休憩は退勤の時刻の境で引きますか", "はい 境で引く", "2_マスタ/会社/時間.休憩の引き方"),
    ("Q2", "作り物の会社", "作り物 一郎", "作り物 一郎さんの通勤手当はいくらですか", "分からない", ""),
    ("Q3", "作り物の会社", "会社", "端数は切り捨てますか", "出し直し→ Q4", ""),
    ("Q5", "別の作り物の会社", "会社", "賞与の支給日はいつですか", "7 月 10 日", ""),
]


def 格子たち(行たち, 取り下げ=()):
    """作り物の行 → 質問と回答 の 3 タブ（Drive のタブの名 → 格子）。"""
    問, 答, 振 = [qa.見出し("問い")], [qa.見出し("答え")], [qa.見出し("振り分け")]
    for 鍵, 社, 対象, 文, 回答, 先 in 行たち:
        状態 = "取り下げ" if 鍵 in 取り下げ else ("答えた" if 回答 else "聞いている")
        問.append([鍵, 社, "2099-01", "2099-01-05", 文, "", 状態])
        if 回答:
            答.append([鍵, 回答, "2099-01-06", ""])
        if 対象 or 先:
            振.append([鍵, 社, 対象, 先, "", "", "", "", "", ""])
    return {qa.Driveのタブ("問い"): 問, qa.Driveのタブ("答え"): 答, qa.Driveのタブ("振り分け"): 振}


def rows(extra=()):
    return P.表の行たち(qa.読む(格子たち([*ROWS, *extra])))


def test_同じ鍵の答え済みは止める():
    res = P.照らす([{"key": P.鍵("Q1"), "question": "何か"}], rows())
    assert P.鍵("Q1") in res["answered"]


def test_鍵を替えても同じ設定の項目なら止める():
    new = ("Q6", "作り物の会社", "会社", "お昼の休み時間の扱いを教えてください", "", "2_マスタ/会社/時間.休憩の引き方")
    res = P.照らす([{"key": P.鍵("Q6"), "question": "お昼の休み時間の扱いを教えてください"}], rows([new]))
    assert P.鍵("Q6") in res["answered"]


def test_言い回しだけ変えた問いは止める():
    res = P.照らす([{"key": "L1", "question": "休憩は退勤の時刻の境で引きますか？"}], rows())
    assert "L1" in res["answered"]


def test_分からないと出し直しは答え済みに数えない():
    qs = [{"key": P.鍵("Q2"), "question": "作り物 一郎さんの通勤手当はいくらですか"},
          {"key": P.鍵("Q3"), "question": "端数は切り捨てますか"}]
    res = P.照らす(qs, rows())
    assert res["answered"] == {} and set(res["checked"]) == {q["key"] for q in qs}


def test_問いの文に聞き直しを書いた問いは通す():
    new = ("Q7", "作り物の会社", "会社", "休憩は退勤の時刻の境で引きますか（聞き直し: Q1・規則が変わった）", "",
           "2_マスタ/会社/時間.休憩の引き方")
    res = P.照らす([{"key": P.鍵("Q7"), "question": "休憩は退勤の時刻の境で引きますか"}], rows([new]))
    assert res["answered"] == {}
    # 聞き直しを書かなければ同じ設定の項目で止まる（注入: 書いた字を読まない読み方なら上も止まる）
    new = (*new[:3], "休憩は退勤の時刻の境で引きますか", *new[4:])
    assert P.鍵("Q7") in P.照らす([{"key": P.鍵("Q7"), "question": "休憩は退勤の時刻の境で引きますか"}], rows([new]))["answered"]


def test_取り下げた問いは照らさない():
    行 = qa.読む(格子たち(ROWS, 取り下げ={"Q1"}))
    assert "Q1" not in {r["問いの番号"] for r in P.表の行たち(行)}
    assert P.照らす([{"key": "L1", "question": "休憩は退勤の時刻の境で引きますか"}], P.表の行たち(行))["answered"] == {}


def test_会社を渡せばほかの会社の答えでは止めない():
    q = [{"key": "L1", "question": "賞与の支給日はいつですか"}]
    assert "L1" in P.照らす(q, rows())["answered"]
    assert P.照らす(q, rows(), "作り物の会社")["answered"] == {}


def _表(tmp_path, 中身):
    """中身（{タブの名: 格子}・前の形の物も渡せる）を JSON の file に置いて path を返す。"""
    t = tmp_path / "rows.json"
    t.write_text(json.dumps(中身, ensure_ascii=False), encoding="utf-8")
    return str(t)


def test_文面の問いは答え済みがあれば_exit_2(tmp_path):
    t = _表(tmp_path, 格子たち(ROWS))
    q = tmp_path / "q.txt"
    q.write_text("休憩は退勤の時刻の境で引きますか\n残業の上限はありますか\n", encoding="utf-8")
    assert P.main(["--rows", t, "--questions", str(q)]) == 2
    q.write_text("残業の上限はありますか\n", encoding="utf-8")
    assert P.main(["--rows", t, "--questions", str(q)]) == 0


def test_照らせない時は何も出さず_exit_2(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("PAYROLL_QA_ROWS", raising=False)
    入 = json.dumps({"format": "qa-prior/1", "questions": [{"key": "a", "question": "x"}]})
    assert P.main([], stdin=io.StringIO(入)) == 2                                    # 表が渡されない
    assert P.main(["--rows", str(tmp_path / "無い.json")], stdin=io.StringIO(入)) == 2   # 読めない
    t = _表(tmp_path, {qa.Driveのタブ("答え"): 格子たち(ROWS)[qa.Driveのタブ("答え")]})
    assert P.main(["--rows", t], stdin=io.StringIO(入)) == 2                          # 問いのタブが無い
    t = _表(tmp_path, 格子たち(ROWS))
    for 悪い in ("{", json.dumps({"format": "qa-prior/0", "questions": []}), json.dumps({"format": "qa-prior/1"}),
               json.dumps({"format": "qa-prior/1", "questions": [{"question": "鍵が無い"}]})):
        assert P.main(["--rows", t], stdin=io.StringIO(悪い)) == 2, 悪い
    assert capsys.readouterr().out == ""


def test_表に無い会社を渡したら照らせないで_exit_2(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("PAYROLL_QA_COMPANY", raising=False)
    入 = json.dumps({"format": "qa-prior/1", "questions": [{"key": P.鍵("Q1"), "question": "休憩は退勤の時刻の境で引きますか"}]})
    t = _表(tmp_path, 格子たち(ROWS))
    for 名 in ("作り物", "作り物の会杜"):   # 略した名・1 字違い
        assert P.main(["--rows", t, "--company", 名], stdin=io.StringIO(入)) == 2, 名
    assert capsys.readouterr().out == ""
    monkeypatch.setenv("PAYROLL_QA_COMPANY", "作り物")                                  # 環境から渡しても同じ
    assert P.main(["--rows", t], stdin=io.StringIO(入)) == 2
    monkeypatch.delenv("PAYROLL_QA_COMPANY")
    # 表に在る会社・会社を渡さない・会社の欄が全部空の表（1 社だけの表）は照らす
    assert P.main(["--rows", t, "--company", "作り物の会社"], stdin=io.StringIO(入)) == 0
    assert json.loads(capsys.readouterr().out)["answered"]
    assert P.main(["--rows", t], stdin=io.StringIO(入)) == 0
    capsys.readouterr()
    空 = _表(tmp_path, 格子たち([(r[0], "", *r[2:]) for r in ROWS]))
    assert P.main(["--rows", 空, "--company", "新しい会社"], stdin=io.StringIO(入)) == 0


def test_値の表の命令が_qa_prior_1_を受けて_answered_と_checked_を返す(tmp_path):
    cmd = json.loads((根 / "config" / "skill-values.json").read_text(encoding="utf-8"))["docs-kit"]["qa-html"]["prior_check_cmd"]
    入 = {"format": "qa-prior/1", "questions": [
        {"key": P.鍵("Q1"), "label": "", "question": "休憩の境", "about": [], "known": [], "group": "", "kind": ""},
        {"key": "q2", "label": "", "question": "残業の上限はありますか", "about": [], "known": [], "group": "", "kind": ""}]}
    # check.mjs は値の表の repo の根（パックの根）で命令を走らせる。環境の PAYROLL_PACK_DIR が無い dir を指していても
    # （窓の環境が古い marketplace の場所を持つ時・2026-11-24 に起きた）道具はパックの根から引く
    env = {**os.environ, "PAYROLL_QA_ROWS": _表(tmp_path, 格子たち(ROWS)), "PAYROLL_QA_COMPANY": "作り物の会社",
           "PAYROLL_PACK_DIR": str(tmp_path / "無いパックの場所")}
    r = subprocess.run(cmd, shell=True, cwd=根, input=json.dumps(入, ensure_ascii=False), text=True,
                       capture_output=True, env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert set(out["answered"]) == {P.鍵("Q1")} and set(out["checked"]) == {"q2"}
    # 表が渡されなければ 0 で終わらない（check.mjs が「命令が落ちた」で赤にする）
    env.pop("PAYROLL_QA_ROWS")
    r = subprocess.run(cmd, shell=True, cwd=根, input=json.dumps(入), text=True, capture_output=True, env=env, timeout=60)
    assert r.returncode == 2 and r.stdout == ""


def test_値の表に給与の印():
    assert json.loads((根 / "config" / "skill-values.json").read_text(encoding="utf-8"))["印"] == "給与のパック"


# ── 決まり切らない答え・前の形の表（2026-11-18） ──
# 防ぐ故障: 「不明」「確かめる」の答えを答え済みに数えて聞くべき問いを落とす／逆に何度目かを数えず同じ人の同じ日を 3 回聞く・
# 同じ詰め直しを 2 つの問いで出す。前の 1 枚の表（タブ 質問）を黙って空回りして全部 checked にする。

未決の行 = [
    ("Q8", "作り物の会社", "作り物 二郎", "作り物 二郎さんの 1 月 5 日の退勤の時刻は何時ですか", "不明", ""),
    ("Q9", "作り物の会社", "作り物 二郎", "作り物 二郎さんの 1 月 5 日の退勤の時刻は何時ですか？", "確かめます", ""),
]


def test_不明と確かめるは答え済みに数えず詰め直しの回目を数える():
    q = [{"key": "L1", "question": "作り物 二郎さんの 1 月 5 日の退勤の時刻は何時ですか"}]
    res = P.照らす(q, rows(未決の行))
    assert res["answered"] == {}
    詰 = res["詰め直し"]["L1"]
    assert 詰["回目"] == 3 and set(詰["前の問い"]) == {"Q8", "Q9"}
    assert 詰["前の答え"] == ["不明", "確かめます"] and "詰め直し 3 回目" in res["checked"]["L1"]
    # 注入: 「不明」を答えと数える前の読み方なら答え済みになり、詰め直しにならない
    assert P.決まり切らない("不明") and P.決まり切らない("確かめます") and not P.決まり切らない("はい 境で引く")


def test_同じ前の問いの詰め直しは1つにまとめる():
    q = [{"key": "L1", "question": "作り物 二郎さんの 1 月 5 日の退勤の時刻は何時ですか"},
         {"key": "L2", "question": "作り物 二郎さんの 1 月 5 日の退勤の時刻は何時でしたか"}]
    res = P.照らす(q, rows(未決の行))
    assert set(res["詰め直し"]) == {"L1"} and "L1 に 1 つにまとめる" in res["answered"]["L2"]


def _走らせる(tmp_path, 中身):
    入 = json.dumps({"format": "qa-prior/1", "questions": [{"key": "a", "question": "残業の上限はありますか"}]})
    return P.main(["--rows", _表(tmp_path, 中身)], stdin=io.StringIO(入))


def test_前の1枚の表は訳を名指しして止める(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("PAYROLL_QA_COMPANY", raising=False)
    前の頭 = ["問いの番号", "会社", "対象", "質問", "回答", "反映先", "答えで変わる項目と人", "理由"]
    前の行 = ["Q209901-01", "作り物の会社", "会社", "休憩は", "はい", "", "", ""]
    for 中身, 訳 in (
            ({"values": [前の頭, 前の行]}, "get_values の形"),                          # 前の 1 枚の表の get_values の形
            ({**格子たち(ROWS), "質問": [前の頭, 前の行]}, "前の形のタブ"),            # 3 タブに前のタブが残っている
            ({"質問": [前の頭, 前の行]}, "前の形のタブ"),
            ):
        assert _走らせる(tmp_path, 中身) == 2, 訳
        out = capsys.readouterr()
        assert out.out == "" and 訳 in out.err, out.err
    # 今の形の表は照らす（止める形が今の表を止めない）・前のタブが空なら止めない
    assert _走らせる(tmp_path, 格子たち([*ROWS, *未決の行])) == 0
    assert _走らせる(tmp_path, {**格子たち(ROWS), "質問": []}) == 0


# ── 字の揺れと別の人（台帳 束 K3） ──
# 防ぐ故障: 決まり切らない答えを頭の字の startswith で見ていたので「まだ分からない」が答え済みに数えられ聞き直しが止まった。
# 字の 2 字組の重なりだけで同じ問いと決めたので、別の人の同じ言い回しの問いを答え済みとして止めた。

def test_頭でない所の決まり切らない答えも答え済みに数えない():
    for a in ("まだ分からない", "今は不明です", "社内で確認中", "ＮＧ：分からない"):
        assert P.決まり切らない(a), a
    assert not P.決まり切らない("18:00 で数える")
    行 = [("Q10", "作り物の会社", "作り物 三郎", "作り物 三郎さんの 1 月 6 日の退勤の時刻は何時ですか", "まだ分からない", "")]
    res = P.照らす([{"key": "L1", "question": "作り物 三郎さんの 1 月 6 日の退勤の時刻は何時ですか"}], rows(行))
    assert res["answered"] == {} and "L1" in res["詰め直し"]


def test_別の人の同じ言い回しの問いは答え済みにしない():
    行 = [("Q11", "作り物の会社", "作り物 四郎", "作り物 四郎さんの 1 月 7 日の退勤の時刻は何時ですか", "18:00", "")]
    res = P.照らす([{"key": "L1", "question": "作り物 五郎さんの 1 月 7 日の退勤の時刻は何時ですか"}], rows(行))
    assert res["answered"] == {}
    res = P.照らす([{"key": "L1", "question": "作り物 四郎さんの 1 月 7 日の退勤の時刻は何時でしたか"}], rows(行))
    assert "L1" in res["answered"]
