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
      "f8": {"name": "8_確認事項"}, "f9": {"name": "9_ほか"}, "f0": {"name": "00_事務所"}}
見出し = ["会社", "組", "支給月", "原本", "集計", "取り込み", "計算", "確認ページ", "納品", "外した人", "突き合わせ", "止まりの理由"]


def 名を引く(fid):
    if fid not in 本:
        raise RuntimeError("引けない")
    return 本[fid]


def 口(**kw):
    base = dict(名の頭たち=場所.名の頭たち(根), 名を引く=名を引く, 見出しを引く=lambda sid, tab: 見出し, 印="作り物の印",
                置き換える命令=("作り物_upload.py",), 確認ページの形=場所.確認ページの名の形(根))
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
    assert 場所.確認ページの名の形(根)[1] == {"<会社>": "8_確認事項", "事務所": "00_事務所"}
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
    assert W.判定("d__create_file", {"name": 事務所の, "parents": ["f0"]}, 口(確認ページの形=(形, {"<会社>": "8_確認事項"})))
    assert W.判定("d__create_file", {"name": 事務所の, "parents": ["f0"]}, 口(確認ページの形=(形.replace("?P<組>", ""), {"<会社>": "8_確認事項", "事務所": "00_事務所"})))


def test_置き場の名たちの無い前の版のパックは置き場の名を両方に使う_形の違う物は読まない(tmp_path):
    pack = tmp_path / "pack"
    (pack / "確認ページ").mkdir(parents=True)
    f = pack / "確認ページ" / "確認ページ.py"
    f.write_text("import re\n名の形 = re.compile(r'確認事項_(?P<組>[^_]+)_x\\.html')\n置き場の名 = '8_確認事項'\n", encoding="utf-8")
    assert 場所.確認ページの名の形(pack)[1] == {"<会社>": "8_確認事項", "事務所": "8_確認事項"}
    f.write_text(f.read_text(encoding="utf-8") + "置き場の名たち = ('8_確認事項', '00_事務所')\n", encoding="utf-8")
    assert 場所.確認ページの名の形(pack) is None


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
    shutil.copytree(根 / "出口", pack / "出口", ignore=shutil.ignore_patterns("__pycache__"))
    (pack / "確認ページ").mkdir()
    (pack / "確認ページ" / "確認ページ.py").write_text("raise RuntimeError('壊れた版')\n", encoding="utf-8")
    ev = json.dumps({"tool_name": "mcp__d__create_file", "tool_input": {"name": "確認事項_でたらめ.html"}})
    out = _hook(ev, PAYROLL_PACK_DIR=str(pack)).stdout
    assert '"deny"' in out and "名の形" in out
    assert '"deny"' in _hook(ev, PAYROLL_PACK_DIR=str(根)).stdout   # 正しいパックでも外れた名は止める
