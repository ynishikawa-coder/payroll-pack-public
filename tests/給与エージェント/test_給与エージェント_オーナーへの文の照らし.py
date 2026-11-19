"""オーナーへの文の照らし（plugins/payroll-agent/bin/オーナーへの文の照らし.py）と、hook の入口（hooks/見張り.py）の選択肢の画面の枝の試験。

防ぐ故障（2026-11-17〜18 の給与の窓）: オーナーへ「Q202611-67・68 に答えてください」と番号だけで頼み、どこで何に答えるかが
  分からなかった。オーナーが決めなくてよい検算を聞き、「事務所に聞く」と返された。決まりの正本は plugin の 決まり.md「聞く」。
注入の試験: わざと番号だけの頼み・検算の問いを選択肢の画面に入れると、hook が知らせる（止めない＝deny を出さない）。
"""
import io
import json

from 手伝い import PLUGIN, 根, 場所

import オーナーへの文の照らし as 照  # noqa: E402

形 = 場所.番号の形たち(根)   # 番号の形はパックの正本から読む（写さない）

悪い = [
    ("Q202611-67・68 に答えてください", "Q202611-67"),
    ("Q202611-100 に答えてください", "Q202611-100"),   # 順が 3 桁（正本は桁を限らない）
    ("受付 R261118-AB12 の答えを見てください", "R261118-AB12"),
    ("この人の残業の検算は合っていますか", "検算"),
    ("この原本の読み方で合っていますか", "原本の読み"),
]
良い = [
    "作り物の会社の担当者に、通勤の手当の上限を確認ページで聞きました。答えは確認ページで見られます。",
    "消してよいですか（前の置き場の写し 3 つ）",
    "Q と R の字だけの文",
]


def test_悪い文を拾う():
    for 文, 字 in 悪い:
        訳 = 照.照らす(文, 形)
        assert 訳 and any(字 in x for x in 訳), 文


def test_良い文は通す():
    for 文 in 良い:
        assert 照.照らす(文, 形) == [], 文


def test_選択肢の画面の文は問いと選択肢の説明を全部見る():
    args = {"questions": [{"question": "どれにしますか", "header": "道具",
                           "options": [{"label": "全部", "description": "Q202611-67 の答えを待つ"}, {"label": "分からない"}]}]}
    assert "Q202611-67" in 照.選択肢の画面の文(args)
    assert 照.照らす(照.選択肢の画面の文(args), 形)


def test_番号の形が読めない時は黙らずに知らせる():
    assert any("番号の形を読めない" in x for x in 照.照らす("Q202611-67 に答えて", None))


def test_番号の形はパックの正本と同じ():
    import importlib
    assert 形[0] == importlib.import_module("初期設定.型の口")._問いの番号の形.pattern
    assert 形[1] == r"R\d{6}-[A-Z0-9]{4}" and 形[1] in (根 / "確認ページ" / "確認ページ.py").read_text(encoding="utf-8")


def _hook(ev):
    import contextlib
    import importlib.util
    import os
    spec = importlib.util.spec_from_file_location("見張りの入口", PLUGIN / "hooks" / "見張り.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    out = io.StringIO()
    # パックはこの repo を読む（窓の環境の PAYROLL_PACK_DIR が入れた plugin の在り処〔無い所もある〕を指していても結果を変えない）
    前 = os.environ.get("PAYROLL_PACK_DIR")
    os.environ["PAYROLL_PACK_DIR"] = str(根)
    try:
        with contextlib.redirect_stdout(out):
            assert m.main(io.StringIO(json.dumps(ev, ensure_ascii=False))) == 0
    finally:
        if 前 is None:
            os.environ.pop("PAYROLL_PACK_DIR", None)
        else:
            os.environ["PAYROLL_PACK_DIR"] = 前
    return out.getvalue().strip()


def test_注入_番号だけの頼みを選択肢の画面に入れると知らせる_止めない():
    ev = {"tool_name": "AskUserQuestion", "tool_input": {"questions": [
        {"question": "Q202611-67・68 に答えてください", "header": "答え", "options": [{"label": "答えた"}, {"label": "分からない"}]}]}}
    got = json.loads(_hook(ev))["hookSpecificOutput"]
    assert "Q202611-67" in got["additionalContext"]
    assert "permissionDecision" not in got   # 知らせるだけ


def test_注入_検算を選択肢の画面に入れると知らせる():
    ev = {"tool_name": "AskUserQuestion", "tool_input": {"questions": [
        {"question": "この人の検算は合っていますか", "header": "検算", "options": [{"label": "合っている"}, {"label": "分からない"}]}]}}
    assert "担当者" in json.loads(_hook(ev))["hookSpecificOutput"]["additionalContext"]


def test_当たらない選択肢の画面は何も出さない():
    ev = {"tool_name": "AskUserQuestion", "tool_input": {"questions": [
        {"question": "前の置き場の写しを消してよいですか", "header": "消す", "options": [{"label": "消す"}, {"label": "分からない"}]}]}}
    assert _hook(ev) == ""


def test_決まりの正本に線が在る():
    決まり = (PLUGIN / "決まり.md").read_text(encoding="utf-8")
    assert "オーナーに聞かない" in 決まり and "番号で書かない" in 決まり
