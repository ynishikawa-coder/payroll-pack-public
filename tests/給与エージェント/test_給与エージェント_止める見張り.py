"""止める見張り（plugins/payroll-agent/bin/止める見張り.py）と hook の入口（hooks/見張り.py）の試験。名を引く口は差し替える。

防ぐ故障: 窓がシート・Drive の道具で、出す物の本（取り込みだけでなく賞与の取り込み・支給控除一覧・有給休暇管理表）を出荷の口の
  外から書く・写す・作る。管理表の出荷の欄（取り込み・納品）と今の版を直に書く。名の引けない本を通す。確認ページを名の形の外の名・
  置き場の外へ置く。hook の入力が読めない・パックの場所が分からない時に黙って通す。
"""
import io
import json
import os
import subprocess
import sys

from 手伝い import PLUGIN, 根, 場所

import 止める見張り as W  # noqa: E402

本 = {"s1": {"name": "取り込み_作り物の会社_2099.01支給_v1"},
      "s2": {"name": "賞与の取り込み_作り物の会社_2099-01-賞与_v1"},
      "s3": {"name": "支給控除一覧_雇用_作り物の会社_2099.01支給_v1"},
      "s4": {"name": "有給休暇管理表_作り物の会社_2099.01支給_v1"},
      "m1": {"name": "作り物の会社_2_マスタ"},
      "L1": {"name": "00_事務所_管理表"},
      "x1": {"name": "名を変えた本", "appProperties": {"作り物の印": "1"}},
      "f8": {"name": "8_確認事項"}, "f9": {"name": "9_ほか"}, "f0": {"name": "00_事務所"},
      "T1": {"name": "台帳_2099"}, "T2": {"name": " 台帳＿２０９９"}, "T3": {"name": "台帳_2099_写し"}}
見出し = ["会社", "組", "支給月", "原本", "集計", "取り込み", "計算", "確認ページ", "納品", "外した人", "突き合わせ", "止まりの理由"]


def 名を引く(fid):
    if fid not in 本:
        raise RuntimeError("引けない")
    return 本[fid]


def 口(**kw):
    base = dict(名の頭たち=場所.名の頭たち(根), 名を引く=名を引く, 見出しを引く=lambda sid, tab: 見出し, 印="作り物の印",
                置き換える命令=("作り物_upload.py",), 確認ページの形=場所.確認ページの名の形(根),
                守るタブ=場所.守るタブたち(根), 字=場所.字の口(根), 管理表の名=場所.管理表の名(根),
                確認ページの頭たち=場所.確認ページの頭たち(根), 台帳の名か=場所.台帳の名か(根))
    base.update(kw)
    return W.口(**base)


def j(tool, **args):
    return W.判定(tool, args, 口())


def test_出す物の本へシートの道具で書くのは物を問わず止める():
    for sid in ("s1", "s2", "s3", "s4", "x1"):
        assert j("mcp__abc__update_values", spreadsheetId=sid, range="'表'!A1", values=[["1"]]), sid
    assert j("mcp__abc__copy_sheet_to_another_spreadsheet", spreadsheetId="m1", destinationSpreadsheetId="s3")


def test_賞与の取り込みと支給控除一覧をDriveの道具で作る写す置き換えるのは止める():
    assert j("mcp__d__create_file", name="賞与の取り込み_作り物の会社_2099-01-賞与_v2")
    assert j("mcp__d__create_file", name="支給控除一覧_業務委託_作り物の会社_2099.01支給_v2")
    assert j("mcp__d__copy_file", fileId="s4", name="写し")
    assert j("mcp__d__update_file", fileId="s2")
    assert j("Bash", command="python3 x/作り物_upload.py replace s3 a.csv")
    assert j("Bash", command="python3 x/作り物_upload.py replace m1 a.csv") is None


def test_管理表の出荷の欄と今の版と形の変更は止める():
    assert j("x__update_values", spreadsheetId="L1", range="'月の状況'!F2", values=[["済"]])
    assert j("x__update_values", spreadsheetId="L1", range="'月の状況'!I2", values=[["済"]])   # 納品
    assert j("x__update_values", spreadsheetId="L1", range="'月の状況'!L2", values=[["今の版: 手で書いた"]])
    assert j("x__append_values", spreadsheetId="L1", range="'月の状況'!A1", values=[["作り物"]])
    assert j("x__batch_clear_values", spreadsheetId="L1", ranges=["'月の状況'!A2:Z"])
    assert j("x__update_values", spreadsheetId="L1", range="A1", values=[["x"]])


def test_出した物のタブの今の版とリンクは窓が手で書けない():
    # 壊す: 出した物 を守るタブから落とす・出荷の欄に 今の版・リンク を入れ忘れる＝窓が一部の物だけ手でリンクを書ける
    出した物の見出し = ["会社", "組", "支給月", "回", "物", "今の版", "リンク", "更新日"]
    k = 口(見出しを引く=lambda sid, tab: 出した物の見出し if tab == "出した物" else 見出し)
    for rng in ("'出した物'!F2", "'出した物'!G2", "'出した物'!A2:H2"):
        assert W.判定("x__update_values", {"spreadsheetId": "L1", "range": rng, "values": [["手で書いた"]]}, k), rng
    assert W.判定("x__append_values", {"spreadsheetId": "L1", "range": "'出した物'!A1", "values": [["作り物"]]}, k)


def test_名と見出しの引けない本は止める():
    assert j("x__update_values", spreadsheetId="不明", range="A1", values=[["1"]])
    assert j("x__update_values", spreadsheetId=None, range="A1")
    k = 口(見出しを引く=lambda sid, tab: (_ for _ in ()).throw(RuntimeError("x")))
    assert W.判定("x__update_values", {"spreadsheetId": "L1", "range": "'月の状況'!B2", "values": [["a"]]}, k)


def test_窓の仕事の書き込みは通す():
    assert j("x__update_values", spreadsheetId="m1", range="'社員'!A2", values=[["1"]]) is None
    assert j("x__update_values", spreadsheetId="L1", range="'月の状況'!L2", values=[["例の確かめ待ち"]]) is None
    assert j("x__update_values", spreadsheetId="L1", range="'確認ページ'!A2", values=[["2099-01-01"]]) is None
    assert j("x__get_values", spreadsheetId="s1", range="A1") is None
    assert j("Read", file_path="/x") is None


def test_確認ページは名の形と置き場をパックの1か所から読んで照らす():
    assert 場所.確認ページの名の形(根)[1] == {"会社": "8_確認事項", "事務所": "00_事務所"}
    良い = "確認事項_作り物の会社_2099.01支給（1月分）_v1.html"
    assert j("d__create_file", name=良い, parents=["f8"]) is None
    assert j("d__create_file", name="確認事項_作り物の会社_2099.01支給（1月分）.html", parents=["f8"])   # 版が無い
    assert j("d__create_file", name="確認ページ_作り物の会社_2099.01支給.html", parents=["f8"])          # 前の形
    assert j("d__create_file", name=良い, parents=["f9"])                                              # 置き場違い
    assert j("d__create_file", name=良い)                                                              # 置き場が無い
    # パックの名の形が無い・読めない時は見分けられない＝止める（形を写さない）
    assert W.判定("d__create_file", {"name": "確認事項_x.html"}, 口(確認ページの形=None))
    assert W.判定("d__create_file", {"name": "確認ページ_x.html"}, 口(確認ページの形=None))
    assert W.判定("d__create_file", {"name": "作り物のメモ"}, 口(確認ページの形=None)) is None
    assert 場所.確認ページの名の形(根 / "無い所") is None


def test_事務所全体の確認ページは事務所のフォルダにだけ_会社の確認ページは会社のフォルダにだけ置ける():
    """置き場はパックの 置き場の名たち（正本は docs/設計/Drive の型.md §3 の表）から読む。"""
    事務所の = "確認事項_事務所_2099.01支給（12月分）_v1.html"
    会社の = "確認事項_作り物の会社_2099.01支給（1月分）_v1.html"
    assert j("d__create_file", name=事務所の, parents=["f0"]) is None
    assert j("d__create_file", name="下書き_" + 事務所の, parents=["f0"]) is None
    assert j("d__create_file", name=事務所の, parents=["f8"])     # 前の置き場（00_事務所/8_確認事項）は止める
    assert j("d__create_file", name=会社の, parents=["f0"])       # 会社の確認ページを 00_事務所 に置くと止める
    assert j("d__create_file", name=事務所の, parents=["f9"])     # 表に無い名のフォルダは止める
    assert j("d__create_file", name=会社の, parents=["f9"])
    # 置き場の名たち の形が分からない時は見分けられない＝止める
    形 = 場所.確認ページの名の形(根)[0]
    assert W.判定("d__create_file", {"name": 事務所の, "parents": ["f0"]}, 口(確認ページの形=(形, {"会社": "8_確認事項"})))
    assert W.判定("d__create_file", {"name": 事務所の, "parents": ["f0"]}, 口(確認ページの形=(形.replace("?P<組>", ""), {"会社": "8_確認事項", "事務所": "00_事務所"})))


def test_置き場の名たちの無い前の版のパックは置き場の名を両方に使う_形の違う物は読まない(tmp_path):
    pack = tmp_path / "pack"
    (pack / "確認ページ").mkdir(parents=True)
    f = pack / "確認ページ" / "確認ページ.py"
    f.write_text("import re\n名の形 = re.compile(r'確認事項_(?P<組>[^_]+)_x\\.html')\n置き場の名 = '8_確認事項'\n", encoding="utf-8")
    assert 場所.確認ページの名の形(pack)[1] == {"会社": "8_確認事項", "事務所": "8_確認事項"}
    f.write_text(f.read_text(encoding="utf-8") + "置き場の名たち = ('8_確認事項', '00_事務所')\n", encoding="utf-8")
    assert 場所.確認ページの名の形(pack) is None
    # 置き場の名たち の鍵とパックの会社の根の印が食い違う版も読まない（印の字は道具に写さずパックから読む）
    f.write_text(f.read_text(encoding="utf-8") + "置き場の名たち = {'<甲>': '8_確認事項', '事務所': '00_事務所'}\n会社の印 = '<乙>'\n", encoding="utf-8")
    assert 場所.確認ページの名の形(pack) is None
    f.write_text(f.read_text(encoding="utf-8") + "会社の印 = '<甲>'\n", encoding="utf-8")
    assert 場所.確認ページの名の形(pack)[1] == {"会社": "8_確認事項", "事務所": "00_事務所"}


def test_名の頭はパックの出口の出す物の置き場から読み_全部の物を含む():
    import 出口.名と版 as N
    assert set(場所.名の頭たち(根)) == {f"{k}_" for k in N.出す物の置き場}
    for 物 in ("取り込み", "賞与の取り込み", "支給控除一覧_雇用", "支給控除一覧_業務委託", "有給休暇管理表"):
        assert f"{物}_" in 場所.名の頭たち(根)


def _hook(ev, **env):
    e = {k: v for k, v in os.environ.items() if not k.startswith("PAYROLL_")}
    e.update(env)
    return subprocess.run([sys.executable, str(PLUGIN / "hooks" / "見張り.py")], input=ev, capture_output=True, text=True, env=e)


def test_hookは名を引く命令で引いて止め_読めない入力と引けない時は止める(tmp_path):
    look = tmp_path / "look.py"
    look.write_text("import json,sys\n"
                    "print(json.dumps({'name':'支給控除一覧_雇用_作り物_2099.01支給_v1'} if sys.argv[2]=='s3' else {'name':'','見えない':True}))\n",
                    encoding="utf-8")
    cmd = f"{sys.executable} {look}"
    ev = json.dumps({"tool_name": "mcp__x__update_values", "tool_input": {"spreadsheetId": "s3", "range": "'a'!A1"}})
    out = _hook(ev, PAYROLL_GUARD_LOOKUP_CMD=cmd, PAYROLL_PACK_DIR=str(根)).stdout
    assert '"deny"' in out and "支給控除一覧_雇用" in out
    ev2 = json.dumps({"tool_name": "mcp__x__update_values", "tool_input": {"spreadsheetId": "zz", "range": "'a'!A1"}})
    assert _hook(ev2, PAYROLL_GUARD_LOOKUP_CMD=cmd, PAYROLL_PACK_DIR=str(根)).stdout == ""
    assert '"deny"' in _hook(ev, PAYROLL_PACK_DIR=str(根)).stdout           # 名を引く命令が無い＝引けない＝止める
    assert '"deny"' in _hook("壊れた", PAYROLL_PACK_DIR=str(根)).stdout      # 入力が読めない
    assert '"deny"' in _hook(ev, PAYROLL_GUARD_LOOKUP_CMD=cmd, PAYROLL_PACK_DIR=str(tmp_path)).stdout   # パックの場所が違う
    assert _hook(json.dumps({"tool_name": "Read", "tool_input": {}}), PAYROLL_PACK_DIR=str(tmp_path)).stdout == ""


置き換えの通す文 = [
    "python3 - <<EOF\ns = 'xa'\nprint(s.replace('a','b'))\nEOF",
    "echo replace",
    "echo replace s3",
    "python3 x/作り物_upload.py list && echo replace s3",       # 命令の名の直後でない replace は見ない
    "grep -n replace x/作り物_upload.py",
    "python3 - <<EOF\nprint(\"it's\".replace('a','b'))\nEOF",          # 分けられても命令の名が無い
]
置き換えの止める文 = [
    "作り物_upload.py replace s3 a.csv",
    "python3 /x/作り物_upload.py replace s3 a.csv",
    "a && 作り物_upload.py replace s3 a.csv",
    "a;作り物_upload.py replace s3",
    "python3 x/作り物_upload.py --yes replace s3 a.csv",          # 旗を挟んでも見る
    "python3 x/作り物_upload.py replace",                          # 置き換える先が無い＝見分けられない
    "python3 x/作り物_upload.py --profile p replace s3",           # 値を取る旗を挟む
    "bash -c 'python3 x/作り物_upload.py replace s3'",             # 引用の中の命令
    "sh -c \"cd x && 作り物_upload.py replace s3\"",
    "作り物_upload.py re\\place s3",                               # \\ で字を割る
    "作り物_upload.py 're'place s3",                               # 引用で字を割る
    "python3 - <<EOF\nimport os\nos.system('作り物_upload.py replace s3')\nEOF",
    "python3 -c \"run(['作り物_upload.py','replace','s3'])\"",    # 分け直しても見分けられない字
    "bash -c '作り物_upload.py re\\place s3'",                       # 引用の中で \\ や引用で字を割る
    "bash -c \"作り物_upload.py 're'place s3\"",
    "bash -c '作り物_up\"load\".py replace s3'",
]


def test_Bashはreplaceの字でなく置き換える命令の名の直後のreplaceだけで止め_分けられない文は止める():
    """注入: python の str.replace を含む heredoc・echo replace（通す）と、命令の名の直後の replace を色々な打ち方で（止める）。"""
    for c in 置き換えの通す文:
        assert j("Bash", command=c) is None, c
    for c in 置き換えの止める文:
        assert j("Bash", command=c), c
    assert j("Bash", command="python3 x/作り物_upload.py replace m1 a.csv") is None    # 出す物でない本は通す
    assert j("Bash", command="echo 'replace 作り物_upload.py") and "分けられない" in j("Bash", command="echo 'replace 作り物_upload.py")
    assert W.判定("Bash", {"command": "作り物_upload.py replace s3"}, 口(置き換える命令=())) is None   # 殻が命令を渡さない


リダイレクトを挟む止める文 = [
    "python3 x/作り物_upload.py 2>&1 replace s3 a.csv",        # 壊す: 前は 2>&1・> ・&> ・< を区切りと読み、後ろの replace を捨てた
    "python3 x/作り物_upload.py >/dev/null replace s3 a.csv",
    "python3 x/作り物_upload.py &>log replace s3 a.csv",
    "python3 x/作り物_upload.py <in replace s3 a.csv",
    "作り物_upload.py 2>/dev/null replace s3",
    "作り物_upload.py >> log replace s3",
    "作り物_upload.py >| log replace s3",
    "作り物_upload.py 1> log replace s3",
    "作り物_upload.py >&2 replace s3",
    "作り物_upload.py &>>log replace s3",
    "作り物_upload.py 3<>f replace s3",
    "作り物_upload.py <<<x replace s3",
    "作り物_upload.py replace 2>&1 s3",                         # replace と id の間のリダイレクトも外して読む
    "作り物_upload.py '>' replace s3",                         # 引用の中の > はリダイレクトでなくただの字（引数）
    "作り物_upload.py \">\" replace s3",
    "作り物_upload.py \\> replace s3",
    "a 2>&1; 作り物_upload.py 2>&1 replace s3",
]
リダイレクトを挟む通す文 = [
    "python3 x/作り物_upload.py list > x; echo replace s3",     # 本当の区切りの後の replace は別の命令の引数
    "python3 x/作り物_upload.py list 2>&1 | grep replace s3",
    "python3 x/作り物_upload.py list & echo replace s3",
    "python3 x/作り物_upload.py list || echo replace s3",
    "python3 x/作り物_upload.py list 2>&1 && echo replace s3",
    "python3 x/作り物_upload.py list >/dev/null 2>&1",          # 置き換えでない命令は今どおり通す
    "python3 x/作り物_upload.py 2>&1 replace m1 a.csv",         # 出す物でない本の置き換えは今どおり通す
    "python3 x/作り物_upload.py list # it's > x",
]


def test_Bashはリダイレクトを区切りでなく引数から外して読み_本当の区切りでは区切る():
    """注入: 置き換える命令の名と replace の間・replace と id の間に色々な書き方のリダイレクトを挟む（止める）。
    本当の区切り（; | & || &&）の後の別の命令の replace と、置き換えでない命令（通す）。"""
    for c in リダイレクトを挟む止める文:
        assert j("Bash", command=c), c
        assert "s3" in W.置き換える先たち(c, ("作り物_upload.py",)), c
    for c in リダイレクトを挟む通す文:
        assert j("Bash", command=c) is None, c
    assert W.置き換える先たち("作り物_upload.py replace '>' s3", ("作り物_upload.py",)) == [">"]   # 引用の > は id の字
    assert j("Bash", command="作り物_upload.py replace >log")                                   # 的の外に id が無い＝止める


def test_hookはパックの場所が無い時も同じ見分けでBashを止める(tmp_path):
    env = dict(PAYROLL_PACK_DIR=str(tmp_path), PAYROLL_GUARD_REPLACE_CMDS="作り物_upload.py、ほか.py")
    def bash(c):
        return _hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": c}}), **env).stdout
    for c in 置き換えの通す文:
        assert bash(c) == "", c
    for c in 置き換えの止める文 + リダイレクトを挟む止める文[:4] + ["x/ほか.py replace s1", "echo 'replace 作り物_upload.py"]:
        assert '"deny"' in bash(c), c
    assert '"deny"' in _hook(json.dumps({"tool_name": "mcp__x__update_values", "tool_input": {}}), **env).stdout   # 書く道具は今どおり止める


def test_hooksの登録の形は土台のpluginと同じ形で入口を指す():
    h = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    cmds = [x["command"] for e in h["hooks"]["PreToolUse"] for x in e["hooks"]]
    assert cmds == ['python3 "${CLAUDE_PLUGIN_ROOT}/hooks/見張り.py"']
    assert (PLUGIN / "hooks" / "見張り.py").is_file()
    # 決まりの差し込み（器の窓の scripts/差し込む.py）も同じ hooks.json に登録する。scripts/ が在る版では在る事も見る
    start = [x["command"] for e in h["hooks"]["SessionStart"] for x in e["hooks"]]
    assert start == ['python3 "${CLAUDE_PLUGIN_ROOT}/scripts/差し込む.py" inject']
    if (PLUGIN / "scripts").is_dir():
        assert (PLUGIN / "scripts" / "差し込む.py").is_file()


def test_hookは確認ページの名の形が読めないパックでは確認ページを作る道具を止める(tmp_path):
    """注入: パックの写しの 確認ページ/確認ページ.py を読めない物にし、PAYROLL_PACK_DIR をそこへ向ける。"""
    import shutil
    pack = tmp_path / "pack"
    for d in ("出口", "芯", "初期設定"):   # 名と版は Drive の木と名の正本（初期設定/型.json）を読む
        shutil.copytree(根 / d, pack / d, ignore=shutil.ignore_patterns("__pycache__"))
    (pack / "確認ページ").mkdir()
    (pack / "確認ページ" / "確認ページ.py").write_text("raise RuntimeError('壊れた版')\n", encoding="utf-8")
    ev = json.dumps({"tool_name": "mcp__d__create_file", "tool_input": {"name": "確認事項_でたらめ.html"}})
    out = _hook(ev, PAYROLL_PACK_DIR=str(pack)).stdout
    assert '"deny"' in out and "名の形" in out
    assert '"deny"' in _hook(ev, PAYROLL_PACK_DIR=str(根)).stdout   # 正しいパックでも外れた名は止める


def test_名とタブと見出しは字の揺れをそろえて見る():
    # 壊す: 字のそのままの一致・startswith だと、頭に空白や全角の字のある本の名・賞与の状況のタブ・揺れた見出しへの
    # 書き込みが止まらなかった（台帳 束 K3）
    本["s5"] = {"name": " 取り込み＿作り物の会社_2099.01支給_v1"}
    本["s6"] = {"name": "00_事務所_管\u200b理表"}
    try:
        assert j("g__update_values", spreadsheetId="s5", range="A1")
        assert j("g__update_values", spreadsheetId="L1", range="'賞与の状況'!F2:F2", values=[["x"]])
        assert j("g__update_values", spreadsheetId="s6", range="'月の状況'!F2:F2", values=[["x"]])
        assert j("d__create_file", name="　支給控除一覧_雇用_x")
        揺れ = [x if x != "納品" else "納　品" for x in 見出し]
        k = 口(見出しを引く=lambda sid, tab: 揺れ)
        assert W.判定("g__update_values", {"spreadsheetId": "L1", "range": "'月の状況'!I2:I2", "values": [["x"]]}, k)
        assert W.判定("g__update_values", {"spreadsheetId": "L1", "range": "'月の状況'!L2:L2", "values": [["今の版：v2"]]}, k)
        assert not j("g__update_values", spreadsheetId="L1", range="'月の状況'!A2:A2", values=[["x"]])
    finally:
        del 本["s5"], 本["s6"]


def 前の入口の口(**kw):
    """字・守るタブ を渡さない入口（字のそろえ方の前の版の plugin の hook・殻の入口）が組む口。"""
    base = dict(名の頭たち=場所.名の頭たち(根), 名を引く=名を引く, 見出しを引く=lambda sid, tab: 見出し, 印="作り物の印",
                置き換える命令=("作り物_upload.py",), 確認ページの形=場所.確認ページの名の形(根))
    base.update(kw)
    return W.口(**base)


def test_版がずれた入口でも判定は同じ版から字と守るタブを読み_守る物に掛からない命令は通す():
    # 壊す: 判定が口の 字 だけを見る形だと、字を渡さない前の版の入口と組んだ時に echo まで全部止めた（台帳 束 K-guardver）
    k = 前の入口の口()
    for c in ("echo hi", "ls -la", "git status", "python3 -c 'print(\"x\".replace(\"a\",\"b\"))'"):
        assert W.判定("Bash", {"command": c}, k) is None, c
    assert "出す物の本" in j_口(k, "Bash", command="python3 x/作り物_upload.py replace s3 a.csv")
    assert W.判定("Bash", {"command": "python3 x/作り物_upload.py replace m1 a.csv"}, k) is None
    assert j_口(k, "g__update_values", spreadsheetId="s1", range="A1")
    本["s5"] = {"name": " 取り込み＿作り物の会社_2099.01支給_v1"}   # 字の揺れも同じ版のそろえ方で照らす
    try:
        assert j_口(k, "g__update_values", spreadsheetId="s5", range="A1")
    finally:
        del 本["s5"]
    assert "出荷の欄" in j_口(k, "g__update_values", spreadsheetId="L1", range="'賞与の状況'!F2:F2", values=[["x"]])
    assert W.判定("g__update_values", {"spreadsheetId": "m1", "range": "A1"}, k) is None


def test_判定と同じ版のパックは環境の指すパックでなくこのfileの上から探す(tmp_path, monkeypatch):
    monkeypatch.setenv("PAYROLL_PACK_DIR", str(tmp_path))   # 別の版（字のそろえ方の無い前の版）を指す環境
    assert W.自分の版のパック() == 根
    部品 = W.自分の版の部品()
    assert 部品["字"].同じ("納　品", "納品") and "月の状況" in 部品["守るタブ"]
    assert 部品["台帳の名か"]("台帳_2099") and not 部品["台帳の名か"]("台帳_2099_写し")


def test_同じ版からも字が読めない時は守る物に掛かる命令だけを止める(monkeypatch):
    # 壊す: 字が読めない時に何でも止める形だと echo まで止まり窓が動けない／何も止めない形だと置き換えが素通りする
    monkeypatch.setattr(W, "自分の版の部品", lambda: {})
    k = 前の入口の口()
    assert W.判定("Bash", {"command": "echo hi"}, k) is None
    assert W.判定("Bash", {"command": "echo replace && ls"}, k) is None
    assert "そろえ方" in j_口(k, "Bash", command="python3 x/作り物_upload.py replace m1 a.csv")
    assert "そろえ方" in j_口(k, "Bash", command="bash -c '作り物_upload.py re\\place s3'")
    assert "そろえ方" in j_口(k, "g__update_values", spreadsheetId="m1", range="A1")
    assert "そろえ方" in j_口(k, "d__create_file", name="ふつうの本")
    assert W.判定("Read", {"file_path": "x"}, k) is None
    k2 = 前の入口の口(字=場所.字の口(根), 管理表の名=場所.管理表の名(根), 台帳の名か=場所.台帳の名か(根))   # 守るタブだけ読めない＝管理表への書き込みは止める
    assert "守るタブ" in j_口(k2, "g__update_values", spreadsheetId="L1", range="'月の状況'!A2:A2")


def test_hookは字のそろえ方の無い前の版のパックを指されてもechoを通し置き換えは止める(tmp_path):
    # 版がずれた入口とパックの組の注入: 環境の指すパックから 芯/字.py を消した複製でも、判定は同じ版から読む
    import shutil
    pack = tmp_path / "前の版"
    shutil.copytree(根, pack, ignore=shutil.ignore_patterns(".git", "__pycache__", "tests"))
    (pack / "芯" / "字.py").unlink()
    look = tmp_path / "look.py"
    look.write_text("import json,sys\nprint(json.dumps({'name':'取り込み_作り物_2099.01支給_v1'}))\n", encoding="utf-8")
    env = dict(PAYROLL_PACK_DIR=str(pack), PAYROLL_GUARD_LOOKUP_CMD=f"{sys.executable} {look}",
               PAYROLL_GUARD_REPLACE_CMDS="作り物_upload.py")
    ok = _hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": "echo hi"}}), **env)
    assert ok.returncode == 0 and '"deny"' not in ok.stdout, ok.stdout + ok.stderr
    ng = _hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": "python3 作り物_upload.py replace s1 a.csv"}}), **env)
    assert '"deny"' in ng.stdout and "出す物の本" in ng.stdout


def j_口(k, tool, **args):
    return W.判定(tool, args, k) or ""


def test_穴の照らしも環境の指す前の版のパックでなく同じ版から字を読む(tmp_path):
    # 同じ原因（台帳 束 K-guardver）: 穴の照らしが環境 PAYROLL_PACK_DIR の指す別の版のパックから 芯/字.py を読み、
    # 字のそろえ方の無い版を指されると照らせず止まった。同じ版（この plugin を含む repo）から読む
    import shutil
    pack = tmp_path / "前の版"
    shutil.copytree(根, pack, ignore=shutil.ignore_patterns(".git", "__pycache__", "tests"))
    (pack / "芯" / "字.py").unlink()
    e = {k: v for k, v in os.environ.items() if not k.startswith("PAYROLL_")}
    e["PAYROLL_PACK_DIR"] = str(pack)
    r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import 穴の照らし as H; "
                        "print(H._パックの('芯.字').__file__)", str(PLUGIN / "bin")],
                       capture_output=True, text=True, env=e, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == str(根 / "芯" / "字.py")


def test_Bashのリダイレクトの的は語だけ_改行とheredocとプロセス置換の中は前の命令の引数でない():
    # 壊す: リダイレクトの次の字句を種を問わず的として飛ばす・改行を空白と読む・heredoc の本文を引数と読む形だと止めすぎる
    for c in ("python3 x/作り物_upload.py > log\necho replace s3",
              "python3 x/作り物_upload.py >\necho replace s3",
              "python3 x/作り物_upload.py <<EOF\nreplace s3\nEOF\necho ok",
              "python3 x/作り物_upload.py <<-'E'\n\treplace s3\n\tE",
              "python3 x/作り物_upload.py > >(grep replace s3)",
              "python3 x/作り物_upload.py <(echo replace s3)"):
        assert j("Bash", command=c) is None, c
    # heredoc の本文に命令と replace が両方在れば中を読む・行の継ぎは同じ命令・プロセス置換の後の引数は読む
    for c in ("bash <<EOF\npython3 x/作り物_upload.py replace s3\nEOF",
              "python3 x/作り物_upload.py \\\nreplace s3",
              "python3 x/作り物_upload.py >(cat) replace s3"):
        assert "出す物の本" in (j("Bash", command=c) or ""), c


def test_Bashで写す先の数字の後に続くリダイレクトでも置き換えを止める():
    # 壊す: `>&` の直後の数字を語の頭のリダイレクトの頭と読むと `2>&1>log` が 1 字句の区切りになり後ろを読み落とす
    for c in ("python3 x/作り物_upload.py 2>&1>log replace s3",
              "python3 x/作り物_upload.py 2>&1>>log replace s3",
              "python3 x/作り物_upload.py >&2>log replace s3",
              "python3 x/作り物_upload.py 2>&1;>log replace s3 ; python3 x/作り物_upload.py replace s3"):
        assert "出す物の本" in (j("Bash", command=c) or ""), c


def test_年の台帳へ道具で直に書くのは止め_関所をBashで呼ぶ道は止めない():
    # 壊す: 台帳の名を照らさない形だと、窓がシートの道具で年の台帳の値・行・タブを直に書き換えられる
    for sid in ("T1", "T2"):
        for tool, a in (("update_values", {"range": "'2099-01'!A2", "values": [["1"]]}),
                        ("append_values", {"range": "'2099-01'!A1", "values": [["1"]]}),
                        ("update_formulas", {"range": "'2099-01'!A2", "formulas": [["=1"]]}),
                        ("batch_clear_values", {"ranges": ["'2099-01'!A2:Z"]}),
                        ("insert_dimension", {"sheetId": 0}),
                        ("update_spreadsheet", {"requests": [{"addSheet": {}}]})):
            assert "年の台帳" in (W.判定("g__" + tool, {"spreadsheetId": sid, **a}, 口()) or ""), (sid, tool)
    assert "年の台帳" in (j("g__copy_sheet_to_another_spreadsheet", spreadsheetId="m1", destinationSpreadsheetId="T1") or "")
    assert "年の台帳" in (j("d__create_file", name="台帳_2099", mimeType="application/vnd.google-apps.spreadsheet") or "")
    assert "年の台帳" in (j("d__copy_file", fileId="m1", name="台帳_2099") or "")
    assert "年の台帳" in (j("d__copy_file", fileId="T1", name="写し") or "")
    assert "年の台帳" in (j("d__update_file", fileId="T1", addParents="f9", removeParents="f0") or "")   # 9_履歴へ移す
    # 置き換える命令（作り物の口）の置き換える先が年の台帳でも止める（出す物の本だけ照らすと通る）
    for c in ("作り物_upload.py replace T1 a.xlsx", "python3 x/作り物_upload.py replace T2 a.csv"):
        assert "年の台帳" in (j("Bash", command=c) or ""), c
    # 台帳の名の形の外（写し・頭付き）は台帳でない＝通す（書く先がほかの守る物でない時）
    assert j("g__update_values", spreadsheetId="T3", range="'x'!A1", values=[["1"]]) is None
    assert j("d__create_file", name="頭_台帳_2099") is None
    # 決まった口（殻の *_gate.py）は Bash の python で書く手順を当てる＝止めない
    for c in ("python3 agents/kyuyo/bin/daicho_gate.py --year 2099 --apply",
              "python3 agents/kyuyo/bin/ship_gate.py replace s9 a.csv"):
        assert j("Bash", command=c) is None, c


def test_台帳の名の形を渡さない前の入口でも同じ版から読んで台帳を止める():
    k = 前の入口の口()
    assert "年の台帳" in j_口(k, "g__update_values", spreadsheetId="T1", range="'2099-01'!A2", values=[["1"]])
    assert W.判定("g__update_values", {"spreadsheetId": "m1", "range": "'x'!A1", "values": [["1"]]}, k) is None
