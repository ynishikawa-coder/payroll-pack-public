"""オーナーへの文の照らし（plugins/payroll-agent/bin/オーナーへの文の照らし.py）と、hook の入口（hooks/見張り.py）の選択肢の画面の枝の試験。

防ぐ故障（2026-11-17〜18 の給与の窓）: オーナーへ「Q202611-67・68 に答えてください」と番号だけで頼み、どこで何に答えるかが
  分からなかった。オーナーが決めなくてよい検算を聞き、「事務所に聞く」と返された。決まりの正本は plugin の 決まり.md「聞く」。
注入の試験: わざと番号だけの頼み・検算の問いを選択肢の画面に入れると、hook が知らせる（止めない＝deny を出さない）。
防ぐ故障（cc4408cbad40）: 照らしが拾う語は検算・原本の読み方だけで、会社の決まり・人ごとの事実の問いをオーナーへ出しても知らせなかった。
  オーナーの決定（2026-11-19）: 許す種類だけ通す＝決まり.md「聞く」の 2 種類の印を頭に名乗る問いだけ通し、印の無い問いを知らせる（止めない）。
防ぐ故障（cb23eb3dd693）: パックの場所が分からない時の知らせが PAYROLL_PACK_DIR だけを言い、plugin を入れ直す道を言わなかった。
"""
import io
import json
import re

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
    args = {"questions": [{"question": "〔道具の都合〕どれにしますか", "header": "道具",
                           "options": [{"label": "全部", "description": "Q202611-67 の答えを待つ"}, {"label": "分からない"}]}]}
    assert "Q202611-67" in 照.選択肢の画面の文(args)
    assert 照.照らす(照.選択肢の画面の文(args), 形)


def test_番号の形が読めない時は黙らずに知らせる():
    assert any("番号の形を読めない" in x for x in 照.照らす("Q202611-67 に答えて", None))
    訳 = 照.照らす("Q202611-67 に答えて", None, パックが在る=False)
    assert any("番号の形を読めない" in x and "入れ直す" in x and "PAYROLL_PACK_DIR" in x for x in 訳)


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
        {"question": "〔道具の都合〕Q202611-67・68 に答えてください", "header": "答え", "options": [{"label": "答えた"}, {"label": "分からない"}]}]}}
    got = json.loads(_hook(ev))["hookSpecificOutput"]
    assert "Q202611-67" in got["additionalContext"]
    assert "permissionDecision" not in got   # 知らせるだけ


def test_注入_検算を選択肢の画面に入れると知らせる():
    ev = {"tool_name": "AskUserQuestion", "tool_input": {"questions": [
        {"question": "〔道具の都合〕この人の検算は合っていますか", "header": "検算", "options": [{"label": "合っている"}, {"label": "分からない"}]}]}}
    assert "担当者" in json.loads(_hook(ev))["hookSpecificOutput"]["additionalContext"]


def test_当たらない選択肢の画面は何も出さない():
    ev = {"tool_name": "AskUserQuestion", "tool_input": {"questions": [
        {"question": "〔消す OK〕前の置き場の写しを消してよいですか", "header": "消す", "options": [{"label": "消す"}, {"label": "分からない"}]}]}}
    assert _hook(ev) == ""


def test_決まりの正本に線が在る():
    決まり = (PLUGIN / "決まり.md").read_text(encoding="utf-8")
    assert "オーナーに聞かない" in 決まり and "番号で書かない" in 決まり


def test_決まりは出所の形の正本を指す():
    """オーナーが自分から答えた事の出所の形は、例の確かめの正本（月次/例の確かめ.py の 出所の書き方）を指す（写さない）。"""
    決まり = (PLUGIN / "決まり.md").read_text(encoding="utf-8")
    assert "`月次/例の確かめ.py` の `出所の書き方`" in 決まり
    import 月次.例の確かめ as 例
    assert "決定DB" in 例.出所の書き方   # 指す先が在り、会話の答えを残す形（決定DB の行）を持つ


# ── パックの場所が分からない窓（環境 PAYROLL_PACK_DIR が無く、plugin が目録から入った所）──
def _入れた形(tmp_path, 版_ずらす=False):
    """Claude Code が plugin を入れた形（<plugins>/cache/<目録>/<plugin>/<版>/ と <plugins>/marketplaces/<目録>/）を作り物で組む。
    目録の複製は git の repo（パックの出口・型・確認ページの dir を指す）。版の dir の名はその HEAD の commit の頭。"""
    import shutil
    import subprocess
    plugins = tmp_path / "plugins"
    複製 = plugins / "marketplaces" / "payroll-pack"
    複製.mkdir(parents=True)
    for d in ("出口", "初期設定", "確認ページ"):
        (複製 / d).symlink_to(根 / d)
    g = ["git", "-C", str(複製), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", str(複製)], check=True)
    subprocess.run(g + ["add", "-A"], check=True)
    subprocess.run(g + ["commit", "-q", "-m", "x"], check=True)
    head = subprocess.run(g + ["rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    版 = ("0" * 12) if 版_ずらす else head[:12]
    入れた = plugins / "cache" / "payroll-pack" / "payroll-agent" / 版
    入れた.mkdir(parents=True)
    for d in ("bin", "hooks"):
        shutil.copytree(PLUGIN / d, 入れた / d)
    shutil.copy(PLUGIN / "決まり.md", 入れた / "決まり.md")   # plugin は決まり.md ごと入る（種類の印はここから読む）
    return 入れた, 複製


def _入れた所の見張り(入れた, ev):
    import os
    import subprocess
    import sys
    env = {k: v for k, v in os.environ.items() if k != "PAYROLL_PACK_DIR"}
    r = subprocess.run([sys.executable, str(入れた / "hooks" / "見張り.py")], input=json.dumps(ev, ensure_ascii=False),
                       capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


関係ない画面 = {"tool_name": "AskUserQuestion", "tool_input": {"questions": [
    {"question": "〔道具の都合〕どちらの名にしますか", "header": "名", "options": [{"label": "甲"}, {"label": "分からない"}]}]}}


def test_入れた目録の同じ版の複製をパックとして読む_関係ない画面に知らせない(tmp_path):
    入れた, 複製 = _入れた形(tmp_path)
    assert 場所.入れた目録(入れた / "bin" / "パックの場所.py") == 複製
    assert _入れた所の見張り(入れた, 関係ない画面) == ""
    番号だけ = {"tool_name": "AskUserQuestion", "tool_input": {"questions": [
        {"question": "〔道具の都合〕Q202611-67 に答えてください", "header": "問い", "options": [{"label": "答えた"}, {"label": "分からない"}]}]}}
    assert "Q202611-67" in _入れた所の見張り(入れた, 番号だけ)   # 番号の形も読めている


def test_注入_版の違う目録の複製は読まない(tmp_path):
    """注入: 目録の複製が plugin と違う版（版の dir の名が HEAD の頭でない）＝その複製をパックにしない（照らしていないと知らせる）。"""
    入れた, _ = _入れた形(tmp_path, 版_ずらす=True)
    assert 場所.入れた目録(入れた / "bin" / "パックの場所.py") is None
    assert "照らしていない" in _入れた所の見張り(入れた, 関係ない画面)
    out = _入れた所の見張り(入れた, 関係ない画面)
    assert "入れ直す" in out and "PAYROLL_PACK_DIR" in out and "版" in out   # 版が違う訳と、直し方の両方を言う


# ── 種類の印（cc4408cbad40・許す種類だけ通す）──
def _画面(*問い):
    return {"questions": [{"question": q, "header": "問い", "options": [{"label": "はい"}, {"label": "分からない"}]} for q in 問い]}


印たち = 照.許す印たち()


def test_印は決まりの聞くの節から読む_2種類():
    assert 印たち == ("〔道具の都合〕", "〔消す OK〕")
    決まり = (PLUGIN / "決まり.md").read_text(encoding="utf-8")
    聞く = 決まり.split("## 聞く", 1)[1].split("\n## ", 1)[0]
    assert "- 許す印: " + "・".join(f"`{印}`" for 印 in 印たち) in 聞く   # 印の並びは「聞く」の決まった 1 行（照らしはそこだけを読む）
    assert "〔道具の都合〕" not in (PLUGIN / "bin" / "オーナーへの文の照らし.py").read_text(encoding="utf-8")   # 照らしに写さない


def test_印の正しい2種類は通る():
    for q in ("〔道具の都合〕確認ページの置き場のフォルダの名はどちらにしますか", "〔消す OK〕前の置き場の写し 3 つを消してよいですか",
              "  〔道具の都合〕頭の空白は見ない"):
        assert 照.印を照らす(_画面(q), 印たち) == [], q


def test_注入_印の無い問いと印を偽った形を知らせる():
    悪い問い = [
        "作り物の会社の通勤の手当の上限は月いくらですか",          # 会社の決まりの問い（印が無い）
        "作り物 一郎さんは 2099-01 から扶養が 1 人増えましたか",    # 人ごとの事実の問い（印が無い）
        "〔会社の決まり〕作り物の会社の締め日は末ですか",            # 許していない種類の印を名乗る
        "[道具の都合] 通勤の手当の上限はいくらですか",              # 印の括弧を偽る
        "作り物の会社の締め日は末ですか〔道具の都合〕",              # 印が頭に無い
        "〔道具の都合 〕作り物の会社の締め日は末ですか",            # 印の字を崩す
    ]
    for q in 悪い問い:
        訳 = 照.印を照らす(_画面(q), 印たち)
        assert len(訳) == 1 and "印が無い" in 訳[0], q
    # 1 つの画面に正しい問いと印の無い問いが混ざれば、印の無い方だけ知らせる
    assert len(照.印を照らす(_画面("〔消す OK〕消してよいですか", 悪い問い[0]), 印たち)) == 1
    # 見出し・選択肢にだけ印を置いても通らない（問いの頭で見る）
    偽 = {"questions": [{"question": 悪い問い[0], "header": "〔道具の都合〕", "options": [{"label": "〔道具の都合〕はい"}]}]}
    assert 照.印を照らす(偽, 印たち)


def test_注入_印の無い会社の決まりと人ごとの事実の問いを選択肢の画面に入れると見張りが知らせる_止めない():
    for q in ("作り物の会社の通勤の手当の上限は月いくらですか", "作り物 一郎さんは 2099-01 から扶養が 1 人増えましたか"):
        got = json.loads(_hook({"tool_name": "AskUserQuestion", "tool_input": _画面(q)}))["hookSpecificOutput"]
        assert "印が無い" in got["additionalContext"] and "permissionDecision" not in got, q


def test_注入_決まりから印を読めない時は黙らずに知らせる(tmp_path):
    無い = tmp_path / "決まり.md"
    無い.write_text("# 作り物\n\n## 聞く\n- 印の無い節\n", encoding="utf-8")
    assert 照.許す印たち(無い) == ()
    assert 照.許す印たち(tmp_path / "無い.md") == ()
    assert any("印" in x and "読めない" in x for x in 照.印を照らす(_画面("〔道具の都合〕どちら"), 照.許す印たち(無い)))


def test_注入_聞くの節にほかの印を書いても許す印にならない_決まった1行だけを読む(tmp_path):
    """ef310ecaea6b: 許す印は「聞く」の節の `- 許す印: ` の 1 行だけ。節のほかの所にバッククォートの〔…〕を書いても通らない。"""
    本物 = (PLUGIN / "決まり.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^- 許す印: ", 本物, re.M)) == 1   # 決まった 1 行は 1 つだけ
    足す = 本物.replace("## 聞く\n", "## 聞く\n- 作り物の注: 会社の決まりは `〔会社の決まり〕` と書く事もある\n", 1)
    assert 足す != 本物
    f = tmp_path / "決まり.md"
    f.write_text(足す, encoding="utf-8")
    assert 照.許す印たち(f) == ("〔道具の都合〕", "〔消す OK〕")
    訳 = 照.印を照らす(_画面("〔会社の決まり〕作り物の会社の締め日は末ですか"), 照.許す印たち(f))
    assert len(訳) == 1 and "印が無い" in 訳[0]


def test_注入_決まった1行が無い_2行在る_崩れた時は既定で止める(tmp_path):
    f = tmp_path / "決まり.md"
    悪い節 = [
        "- オーナーへ聞くのは `〔道具の都合〕`・`〔消す OK〕` だけ\n",                     # 印は書いてあるが決まった 1 行が無い
        "- 許す印: `〔道具の都合〕`\n- 許す印: `〔会社の決まり〕`\n",                    # 2 行在る（どちらを読むか決まらない）
        "- 許す印: `〔道具の都合〕`・〔会社の決まり〕\n",                              # バッククォートの無い物が混ざる
        "- 許す印: `〔道具の都合〕`・`〔消す OK〕` など\n",                            # 印の形でない字が混ざる
        "- 許す印: \n",                                                              # 空
    ]
    for 節 in 悪い節:
        f.write_text("# 作り物\n\n## 聞く\n" + 節 + "\n## 置かない\n- 許す印: `〔消す OK〕`\n", encoding="utf-8")
        assert 照.許す印たち(f) == (), 節
        訳 = 照.印を照らす(_画面("〔道具の都合〕どちら"), 照.許す印たち(f))
        assert any("読めない" in x for x in 訳), 節   # どの問いも黙って通さない
    # ほかの節に在る決まった形の行は読まない
    f.write_text("# 作り物\n\n## 聞く\n- 印の無い節\n\n## 置かない\n- 許す印: `〔消す OK〕`\n", encoding="utf-8")
    assert 照.許す印たち(f) == ()


# ── パックの場所が分からない時の知らせの文（cb23eb3dd693・正本は パックの場所.分からない訳）──
def test_分からない訳は直し方を両方言う():
    for 訳 in (場所.分からない訳("作り物の物を読めない"), 場所.分からない訳("作り物の物を読めない", "/無い/所")):
        assert "入れ直す" in 訳 and "PAYROLL_PACK_DIR" in 訳 and "作り物の物を読めない" in 訳
    assert "/無い/所" in 場所.分からない訳("x", "/無い/所")


def test_照らしの道具と見張りの知らせは分からない訳を使う(tmp_path, monkeypatch, capsys):
    """パックの場所が分からない時、問いの照らし・出す前の照らし・オーナーへの文の照らし・書く道具の見張りの知らせに直し方の両方が入る。"""
    import subprocess
    import sys
    monkeypatch.delenv("PAYROLL_PACK_DIR", raising=False)
    import 問いの照らし as Q
    assert Q.main(["--rows", "x", "--パック", str(tmp_path)], runner=None) == 2
    err = capsys.readouterr().err
    assert "入れ直す" in err and "PAYROLL_PACK_DIR" in err
    渡した = f"渡されたパックの dir {tmp_path}"   # 渡した dir が訳に出る（環境が無い時の訳に化けない）
    assert 渡した in err
    入力 = tmp_path / "入力.json"
    入力.write_text("{}", encoding="utf-8")
    r = subprocess.run([sys.executable, str(PLUGIN / "bin" / "出す前の照らし.py"), "照らす", str(入力), "--パック", str(tmp_path)],
                       capture_output=True, text=True, timeout=60)
    赤 = json.loads(r.stdout)["赤"]
    assert any("入れ直す" in x and "PAYROLL_PACK_DIR" in x and 渡した in x for x in 赤)
    r = subprocess.run([sys.executable, str(PLUGIN / "bin" / "オーナーへの文の照らし.py"), "--パック", str(tmp_path)],
                       input="Q202611-67 に答えて", capture_output=True, text=True, timeout=60)
    assert "入れ直す" in r.stdout and "PAYROLL_PACK_DIR" in r.stdout and 渡した in r.stdout
    import os
    env = dict(os.environ, PAYROLL_PACK_DIR=str(tmp_path))
    ev = {"tool_name": "mcp__x__update_values", "tool_input": {"spreadsheetId": "s3", "range": "'a'!A1"}}
    r = subprocess.run([sys.executable, str(PLUGIN / "hooks" / "見張り.py")], input=json.dumps(ev, ensure_ascii=False),
                       capture_output=True, text=True, env=env, timeout=60)
    deny = json.loads(r.stdout)["hookSpecificOutput"]
    assert deny["permissionDecision"] == "deny" and "入れ直す" in deny["permissionDecisionReason"]
    assert "PAYROLL_PACK_DIR" in deny["permissionDecisionReason"] and 渡した in deny["permissionDecisionReason"]


def test_知らせの文を道具に写さない():
    """「plugin payroll-agent を入れ直す」の文はパックの場所.py の 1 か所だけに在る（3 つの道具と見張りは呼ぶだけ）。"""
    文 = "plugin payroll-agent を入れ直す"
    在る = [f.name for f in [*(PLUGIN / "bin").glob("*.py"), *(PLUGIN / "hooks").glob("*.py")] if 文 in f.read_text(encoding="utf-8")]
    assert 在る == ["パックの場所.py"]
    for f in ("問いの照らし.py", "出す前の照らし.py", "オーナーへの文の照らし.py"):
        assert "分からない訳" in (PLUGIN / "bin" / f).read_text(encoding="utf-8"), f
    assert "分からない訳" in (PLUGIN / "hooks" / "見張り.py").read_text(encoding="utf-8")
