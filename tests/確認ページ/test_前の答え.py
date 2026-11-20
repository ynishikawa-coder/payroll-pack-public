"""前の答えを照らす口（確認ページ/前の答え.py・qa-prior/1）の試験。表は作り物だけ。

防ぐ故障: 質問と回答で答え済みの問いを、同じ番号・新しい番号・言い回しを変えた字で先方へ出す。「分からない」や出し直しの行を
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

HEAD = ["問いの番号", "会社", "対象", "質問", "回答", "反映先", "答えで変わる項目と人", "理由"]
ROWS = [
    ["Q209901-01", "作り物の会社", "会社", "休憩は退勤の時刻の境で引きますか", "はい 境で引く",
     "2_マスタ/会社/時間.休憩の引き方", "", ""],
    ["Q209901-02", "作り物の会社", "人 作り物 一郎", "作り物 一郎さんの通勤手当はいくらですか", "分からない", "", "", ""],
    ["Q209901-03", "作り物の会社", "会社", "端数は切り捨てますか", "出し直し→ Q209901-04", "", "", ""],
    ["Q209901-05", "別の作り物の会社", "会社", "賞与の支給日はいつですか", "7 月 10 日", "", "", ""],
]


def rows(extra=()):
    return P.行にする([HEAD, *ROWS, *extra])


def test_同じ番号の答え済みは止める():
    res = P.照らす([{"key": P.鍵("Q209901-01"), "question": "何か"}], rows())
    assert P.鍵("Q209901-01") in res["answered"]


def test_番号を替えても同じ設定の項目なら止める():
    new = ["Q209902-01", "作り物の会社", "会社", "お昼の休み時間の扱いを教えてください", "",
           "2_マスタ/会社/時間.休憩の引き方", "", ""]
    res = P.照らす([{"key": P.鍵("Q209902-01"), "question": "お昼の休み時間の扱いを教えてください"}], rows([new]))
    assert P.鍵("Q209902-01") in res["answered"]


def test_言い回しだけ変えた問いは止める():
    res = P.照らす([{"key": "L1", "question": "休憩は退勤の時刻の境で引きますか？"}], rows())
    assert "L1" in res["answered"]


def test_分からないと出し直しは答え済みに数えない():
    qs = [{"key": P.鍵("Q209901-02"), "question": "作り物 一郎さんの通勤手当はいくらですか"},
          {"key": P.鍵("Q209901-03"), "question": "端数は切り捨てますか"}]
    res = P.照らす(qs, rows())
    assert res["answered"] == {} and set(res["checked"]) == {q["key"] for q in qs}


def test_理由に聞き直しを書いた問いは通す():
    new = ["Q209902-02", "作り物の会社", "会社", "休憩は退勤の時刻の境で引きますか", "",
           "2_マスタ/会社/時間.休憩の引き方", "", "聞き直し: Q209901-01・規則が変わった"]
    res = P.照らす([{"key": P.鍵("Q209902-02"), "question": "休憩は退勤の時刻の境で引きますか"}], rows([new]))
    assert res["answered"] == {}


def test_会社を渡せばほかの会社の答えでは止めない():
    q = [{"key": "L1", "question": "賞与の支給日はいつですか"}]
    assert "L1" in P.照らす(q, rows())["answered"]
    assert P.照らす(q, rows(), "作り物の会社")["answered"] == {}


def _表(tmp_path, values):
    t = tmp_path / "rows.json"
    t.write_text(json.dumps({"values": values}, ensure_ascii=False), encoding="utf-8")
    return str(t)


def test_文面の問いは答え済みがあれば_exit_2(tmp_path):
    t = _表(tmp_path, [HEAD, *ROWS])
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
    t = _表(tmp_path, [["番号", "問い", "答え"], ["Q209901-01", "休憩は", "はい"]])
    assert P.main(["--rows", t], stdin=io.StringIO(入)) == 2                          # 見出しが無い
    t = _表(tmp_path, [HEAD, *ROWS])
    for 悪い in ("{", json.dumps({"format": "qa-prior/0", "questions": []}), json.dumps({"format": "qa-prior/1"}),
               json.dumps({"format": "qa-prior/1", "questions": [{"question": "鍵が無い"}]})):
        assert P.main(["--rows", t], stdin=io.StringIO(悪い)) == 2, 悪い
    assert capsys.readouterr().out == ""


def test_表に無い会社を渡したら照らせないで_exit_2(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("PAYROLL_QA_COMPANY", raising=False)
    入 = json.dumps({"format": "qa-prior/1", "questions": [{"key": "Q209901_01", "question": "休憩は退勤の時刻の境で引きますか"}]})
    t = _表(tmp_path, [HEAD, *ROWS])
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
    空 = _表(tmp_path, [HEAD, *[[r[0], "", *r[2:]] for r in ROWS]])
    assert P.main(["--rows", 空, "--company", "新しい会社"], stdin=io.StringIO(入)) == 0


def test_値の表の命令が_qa_prior_1_を受けて_answered_と_checked_を返す(tmp_path):
    cmd = json.loads((根 / "config" / "skill-values.json").read_text(encoding="utf-8"))["docs-kit"]["qa-html"]["prior_check_cmd"]
    入 = {"format": "qa-prior/1", "questions": [
        {"key": P.鍵("Q209901-01"), "label": "", "question": "休憩の境", "about": [], "known": [], "group": "", "kind": ""},
        {"key": "q2", "label": "", "question": "残業の上限はありますか", "about": [], "known": [], "group": "", "kind": ""}]}
    env = {**os.environ, "PAYROLL_QA_ROWS": _表(tmp_path, [HEAD, *ROWS]), "PAYROLL_QA_COMPANY": "作り物の会社",
           "PAYROLL_PACK_DIR": str(根)}
    # 窓の repo（パックの外）の根で走っても PAYROLL_PACK_DIR でパックの口を引く（check.mjs は窓の今の dir で命令を走らせる）
    r = subprocess.run(cmd, shell=True, cwd=tmp_path, input=json.dumps(入, ensure_ascii=False), text=True,
                       capture_output=True, env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert set(out["answered"]) == {P.鍵("Q209901-01")} and set(out["checked"]) == {"q2"}
    # 表が渡されなければ 0 で終わらない（check.mjs が「命令が落ちた」で赤にする）
    env.pop("PAYROLL_QA_ROWS")
    r = subprocess.run(cmd, shell=True, cwd=tmp_path, input=json.dumps(入), text=True, capture_output=True, env=env, timeout=60)
    assert r.returncode == 2 and r.stdout == ""


def test_値の表に給与の印():
    assert json.loads((根 / "config" / "skill-values.json").read_text(encoding="utf-8"))["印"] == "給与のパック"


# ── 決まり切らない答え・前の形の表（2026-11-18） ──
# 防ぐ故障: 「不明」「確かめる」の答えを答え済みに数えて聞くべき問いを落とす／逆に何度目かを数えず同じ人の同じ日を 3 回聞く・
# 同じ詰め直しを 2 つの問いで出す。1 行目が見出しでない表・前の見出し（ID）・前の番号の形（Q2026.11-05）を黙って空回りして全部 checked にする。

未決の行 = [
    ["Q209901-06", "作り物の会社", "人 作り物 二郎", "作り物 二郎さんの 1 月 5 日の退勤の時刻は何時ですか", "不明", "", "", ""],
    ["Q209902-03", "作り物の会社", "人 作り物 二郎", "作り物 二郎さんの 1 月 5 日の退勤の時刻は何時ですか？", "確かめます", "", "", ""],
]


def test_不明と確かめるは答え済みに数えず詰め直しの回目を数える():
    q = [{"key": "L1", "question": "作り物 二郎さんの 1 月 5 日の退勤の時刻は何時ですか"}]
    res = P.照らす(q, rows(未決の行))
    assert res["answered"] == {}
    詰 = res["詰め直し"]["L1"]
    assert 詰["回目"] == 3 and set(詰["前の問い"]) == {"Q209901-06", "Q209902-03"}
    assert 詰["前の答え"] == ["不明", "確かめます"] and "詰め直し 3 回目" in res["checked"]["L1"]
    # 注入: 「不明」を答えと数える前の読み方なら答え済みになり、詰め直しにならない
    assert P.決まり切らない("不明") and P.決まり切らない("確かめます") and not P.決まり切らない("はい 境で引く")


def test_同じ前の問いの詰め直しは1つにまとめる():
    q = [{"key": "L1", "question": "作り物 二郎さんの 1 月 5 日の退勤の時刻は何時ですか"},
         {"key": "L2", "question": "作り物 二郎さんの 1 月 5 日の退勤の時刻は何時でしたか"}]
    res = P.照らす(q, rows(未決の行))
    assert set(res["詰め直し"]) == {"L1"} and "L1 に 1 つにまとめる" in res["answered"]["L2"]


def _走らせる(tmp_path, values):
    入 = json.dumps({"format": "qa-prior/1", "questions": [{"key": "a", "question": "残業の上限はありますか"}]})
    return P.main(["--rows", _表(tmp_path, values)], stdin=io.StringIO(入))


def test_前の形の表は訳を名指しして止める(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("PAYROLL_QA_COMPANY", raising=False)
    URLの行 = ["https://example.invalid/login", "", ""]
    for values, 訳 in (
            ([URLの行, HEAD, *ROWS], "見出しは 2 行目に在り 1 行目が見出しでない"),
            ([["ID", *HEAD[1:]], *ROWS], "前の見出し ID（今の名 問いの番号）"),
            ([HEAD, *ROWS, ["Q2099.01-07", "作り物の会社", "会社", "端数は", "切り捨て", "", "", ""]], "'Q2099.01-07'（問いの番号）"),
            ([HEAD, *ROWS, ["Q209903-01", "作り物の会社", "会社", "端数は", "", "", "", "聞き直し: Q2099.01-03・規則が変わった"]],
             "'Q2099.01-03'（Q209903-01 の 理由 の 聞き直し）")):
        assert _走らせる(tmp_path, values) == 2, 訳
        out = capsys.readouterr()
        assert out.out == "" and 訳 in out.err, out.err
    # 今の形の表は照らす（止める形が今の表を止めない）
    assert _走らせる(tmp_path, [HEAD, *ROWS, *未決の行]) == 0


# ── 字の揺れと別の人（台帳 束 K3） ──
# 防ぐ故障: 決まり切らない答えを頭の字の startswith で見ていたので「まだ分からない」が答え済みに数えられ聞き直しが止まった。
# 字の 2 字組の重なりだけで同じ問いと決めたので、別の人の同じ言い回しの問いを答え済みとして止めた。

def test_頭でない所の決まり切らない答えも答え済みに数えない():
    for a in ("まだ分からない", "今は不明です", "社内で確認中", "ＮＧ：分からない"):
        assert P.決まり切らない(a), a
    assert not P.決まり切らない("18:00 で数える")
    行 = [["Q209901-07", "作り物の会社", "人 作り物 三郎", "作り物 三郎さんの 1 月 6 日の退勤の時刻は何時ですか", "まだ分からない", "", "", ""]]
    res = P.照らす([{"key": "L1", "question": "作り物 三郎さんの 1 月 6 日の退勤の時刻は何時ですか"}], rows(行))
    assert res["answered"] == {} and "L1" in res["詰め直し"]


def test_別の人の同じ言い回しの問いは答え済みにしない():
    行 = [["Q209901-08", "作り物の会社", "人 作り物 四郎", "作り物 四郎さんの 1 月 7 日の退勤の時刻は何時ですか", "18:00", "", "", ""]]
    res = P.照らす([{"key": "L1", "question": "作り物 五郎さんの 1 月 7 日の退勤の時刻は何時ですか"}], rows(行))
    assert res["answered"] == {}
    res = P.照らす([{"key": "L1", "question": "作り物 四郎さんの 1 月 7 日の退勤の時刻は何時でしたか"}], rows(行))
    assert "L1" in res["answered"]
