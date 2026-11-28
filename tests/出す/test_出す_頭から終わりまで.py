"""出口/出す.py の main を、作り物の Drive の上で 回=給与・回=月 の頭から終わりまで通す試験。値は全部作り物。

防ぐ故障: 出す.py が 出口 を名だけ（{"取り込み": 名, ...}）で 月を回す へ渡し、月次の奥が 出口["取り込み"]["形"] を
  求めて止まる＝本物の置き場から 1 命令で回すと取り込みも支給控除一覧も出ない。月を回す も 計算の元 も作り物に
  替えない（替えるのは drive口.開く だけ）ので、呼ぶ側と受ける側の形の食い違いはここで赤になる。
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ここ = Path(__file__).resolve().parent
根 = ここ.parents[1]
sys.path.insert(0, str(ここ))
sys.path.insert(0, str(根 / "tests" / "計算"))
sys.path.insert(0, str(根 / "tests" / "集計"))
sys.path.insert(0, str(根 / "tests" / "月次"))
import test_出す_置き場 as 置  # noqa: E402

_spec = importlib.util.spec_from_file_location("頭から終わりまで_作り物", 根 / "tests" / "初期設定" / "test_初期設定_給与の関所.py")
作 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(作)

from 月次_試験の例 import 例をMDに, 例の問い, 例の振り分け, 例の表  # noqa: E402

手, 出す = 置.手, 置.出す


def _締めの記録(C, 状態: dict | None = None):
    """締めの記録の格子（型の見出し）。状態: {NO: 締めの状態}（無い NO は 締まった・値が None の NO は行なし）。"""
    import 月次
    頭 = list(月次.勤怠の照らし.締めの列)
    状 = {NO: "締まった" for NO in 作.人たち} | (状態 or {})
    return [頭, *[[{"会社": C, "支給月": 作.支給月, "NO": NO, "締めの状態": v}.get(c, "") for c in 頭]
                 for NO, v in 状.items() if v is not None]]


_始めの日が空の人 = "0003"


def _会社の値(締めの状態: dict | None = None, 質問と回答=None):
    """作り物の会社 1 社分（マスタ・確定した勤怠・締めの記録・決まり・質問と回答）。呼び名は 手.会社。
    締めの状態: _締めの記録 へ渡す（既定は全員 締まった）。質問と回答: 3 タブを読んだ表（既定は例の表＝止まり無し）。"""
    import 月次
    作.C = 手.会社
    C = 作.C
    # 有給の始めの日: 0001・0002 は在る（有給休暇管理表に行が出る）・0003 は空（給与は出し、有給休暇管理表の行だけ出さず始めの日を聞く）
    始め = {"有給の始めの日": "2027-01-31", "有給の始めの残り": "10", "有給の始めの繰越": "0"}
    タブ = 作._タブ(型={"日勤": {"時間.週の所定日数": "5"}}, 人={NO: {"入社日": "2020-04-01", **(始め if NO != _始めの日が空の人 else {})} for NO in 作.人たち})
    読 = 月次.読んだままの勤怠を作る(作.支給月, C, タブ, [{"部品": "Excel出勤簿", "値": 作._出勤簿()}], 置き場=None)
    台帳 = 月次.台帳の形.勤怠の表たち(確定=True, 勤怠=読["表A"], 勤怠の区間=読["表B"])
    return {"マスタ": タブ,
            "台帳": {**台帳, "読んだままの勤怠": 読["読んだままの勤怠"], "読んだままの勤怠の区間": 読["読んだままの勤怠の区間"],
                     "締めの記録": _締めの記録(C, 締めの状態)},
            "給与のルール": 例をMDに(作._例(C)), "作業のルール": "# 作業のルール（作り物）\n",
            "質問と回答": 例の表("C9001") if 質問と回答 is None else 質問と回答}


@pytest.mark.parametrize("回", ["給与", "月"])
def test_置き場から1命令で回すと取り込みと支給控除一覧が両方できる(monkeypatch, capsys, 回):
    import drive口
    d, 根id, ids = 置._事務所(("2027.02支給（1月分）",), 年=2027, 会社の値=_会社の値())
    monkeypatch.setattr(drive口, "開く", lambda **_: d)
    code = 出す.main(["--会社", 手.会社, "--支給月", "2027-02", "--回", 回, "--根", 根id])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["出した"] is True, out
    assert out["除いた人"] == [], out
    出す物 = ids[f"2027.02支給（1月分）/{置.元.名と版.出す置き場}"]
    置いた = {x["物"].split("_")[0]: x["名"] for x in out["置いた"]}
    assert set(置いた) == {"取り込み", "支給控除一覧", "有給休暇管理表"}, out   # 有給休暇管理表も毎月出す
    for 名 in 置いた.values():
        assert d.名で引く(出す物, 名) is not None, 名   # 月の 2_出す物 へ書いた


def test_有給の始めの日が空の人は給与を出し_有給休暇管理表の行だけ出さず始めの日を聞く(monkeypatch):
    """2026-11-28 オーナーの決め: 有給の始めの日が空＝値が壊れたのでなく情報が無いだけ。仮が残る人は出さない を当てない。"""
    import drive口
    d, 根id, ids = 置._事務所(("2027.02支給（1月分）",), 年=2027, 会社の値=_会社の値())
    monkeypatch.setattr(drive口, "開く", lambda **_: d)
    取った = {}
    code, out = _回す(monkeypatch, d, 根id, "給与", 取った)
    assert code == 0 and out["出した"] is True and out["除いた人"] == [], out
    空 = _始めの日が空の人
    人 = {x.物: set(x.人) for x in 出す.出す物たち(取った["o"])}
    assert 空 in 人["取り込み"]                                            # 給与は出す
    assert 人["有給休暇管理表"] == set(作.人たち) - {空}                     # 有給休暇管理表の行だけ出さない
    assert [a["NO"] for a in out["有給の止めた人"]] == [空] and out["有給の止めた人"][0]["理由"], out   # NO と理由を返す
    [問] = [q for q in 取った["o"]["問い"]["有給"] if q.get("NO") == 空]
    assert 問["何が無いか"] == "有給の始めの日" and 問["反映先"] == 置.型の口.マスタの反映先("社員", "有給の始めの日")
    from 初期設定 import 設問
    [種] = [x for x in 設問.種を集める(取った["o"]) if x["何が無いか"] == "有給の始めの日"]   # 今の問いの道（設問）に載る
    assert 種["人"] == [空] and 種["反映先"] == 問["反映先"], 種
    管理 = d.名で引く(根id, 置.型の口.Driveの名("管理表"))["id"]
    月 = d.表を読む(管理, f"'{置.表.Driveのタブ('月の状況')}'!A1:Z")
    h = 月[0]
    [行] = [r for r in 月[1:] if r[h.index("会社")] == 手.会社 and r[h.index("取り込み")] == "済"]   # 除いた人ではない＝取り込みは済
    assert 行[h.index("止まりの理由")].startswith(f"{出す.有給に載せない頭}: NO {空}"), 月


def test_有給の始めの日の問いは設問と確認ページを通っても振り分けを持ち_答えの無い間は会社を止めずその人の有給だけ止める(monkeypatch):
    """防ぐ故障: 有給の始めの日の問いが振り分けを持たずに出た＝確認ページを起こす側が振り分けを書き忘れると、答えの無い問いは
    誰に効くか決まらず会社の全員を止めた。また反映先が型の口の形（2_マスタ/社員/…）のままだと書き戻しが知らない先として拒む。
    パックが問いに振り分け（反映先は書き戻しの形）を付け、設問 → 確認ページ → 読む口 → 止まりを集める まで落とさない。値は全部作り物。"""
    import drive口
    import 月次
    from 初期設定 import 設問
    from 初期設定 import 質問と回答 as 問答
    d, 根id, ids = 置._事務所(("2027.02支給（1月分）",), 年=2027, 会社の値=_会社の値())
    monkeypatch.setattr(drive口, "開く", lambda **_: d)
    取った = {}
    code, out = _回す(monkeypatch, d, 根id, "給与", 取った)
    assert code == 0, out
    空 = _始めの日が空の人
    資料 = {"名": "作り物の有給休暇管理表", "url": "https://drive.example.invalid/d/1", "置き場": "10_会社/作り物の組/3_月ごと/2027.02支給（1月分）/1_届いた物"}
    月の物 = {**設問.その月だけの物の問い("2027-02", 手.会社), "根拠": [{"資料": 資料["名"], "場所": "全体", "原文": "今月の物 無し"}],
             "読み": "今月だけの物の決まりが無いと読みました。"}
    m = 設問.まとめる([*設問.種を集める(取った["o"]), 月の物], 会社=手.会社, 支給月="2027-02", 今日="2027-02-01", 既にある=[],
                    読んだ資料=[資料], 根拠={"有給の始めの日": {"根拠": [{"資料": "作り物の有給休暇管理表", "場所": "社員 タブ 0003 の行",
                                                     "原文": "始めの日 空"}], "読み": "始めの日の欄が空と読みました。"}})
    [行] = [r for r in m["問い"] if r["何が無いか"] == "有給の始めの日"]
    _s = importlib.util.spec_from_file_location("頭から終わりまで_確認ページ", 根 / "確認ページ" / "確認ページ.py")
    頁 = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(頁)
    r = 頁.作る({"履歴にある名": [], "組": "作り物の組", "支給月": "2027.02支給", "用": "毎月", "問い": m["問い"], "読んだ資料": [資料],
               "今ある名": [], "宛先": "copy"})
    assert r["赤"] == [], r["赤"]
    # 問いを出す時に振り分けを 3_振り分け の候補の行へ書く → 原本を読み直すと問いに戻る（確認ページは振り分けを持たない）
    q, 足す手 = 問答.問いを足す(問答.表(), 顧, "2027-02", "2027-02-01", 行["質問"], "", 選択肢の振り分け=頁.選択肢の振り分け(行, 顧))
    格子 = {}
    for x in 足す手:
        if x["する"] == "行を足す":
            格子.setdefault(x["タブ"], [問答.見出し(問答._タブの役(x["タブ"]))]).extend(x["値"])
    表 = 問答.読む(格子)
    鍵 = q.鍵
    [振] = [f for v in 表.問いたち[0].選択肢の振り分け.values() for f in v]
    assert (振.対象, 振.反映先, 振.何を) == (空, "マスタ/社員", "有給の始めの日"), 振   # 書き戻しの知る形
    止 = 月次.止まりを集める(表, 顧, "2027-02", 人たち=作.人たち)
    assert 止["止まり"] == [] and [(s["対象"], s["問いの鍵"]) for s in 止["有給の止まり"]] == [(空, 鍵)], 止
    # 値（始めの日）は補足から決まる＝選んだだけでは振り分けを書かず、問いを 聞いている のまま残す（値の空の行を作らない）
    [見] = 表.問いたち[0].選択肢の振り分け
    手順 = 問答.答えを原本へ入れる(表.問いたち[0], 見, "分かる 2027-01-31", "2027-02-02")
    assert not [x for x in 手順 if 問答.Driveのタブ("振り分け") in str(x.get("範囲", x.get("先", "")))] and len(手順) == 2, 手順


def test_取り込みがあるのに有給休暇管理表が無ければ何も書かず止める(monkeypatch):
    import drive口
    d, 根id, ids = 置._事務所(("2027.02支給（1月分）",), 年=2027, 会社の値=_会社の値())
    monkeypatch.setattr(drive口, "開く", lambda **_: d)
    元の = 出す.読んで回す
    def 欠く(*a, **k):
        o, 赤 = 元の(*a, **k)
        return {k2: v for k2, v in o.items() if k2 != "有給休暇管理表"}, 赤
    monkeypatch.setattr(出す, "読んで回す", 欠く)
    出す物 = ids[f"2027.02支給（1月分）/{置.元.名と版.出す置き場}"]
    前 = [x["name"] for x in d.子を並べる(出す物)]
    code, out = _回す(monkeypatch, d, 根id, "給与")
    assert code == 2 and out["出した"] is False and "有給休暇管理表が組めていない" in out["赤"][0], out
    assert [x["name"] for x in d.子を並べる(出す物)] == 前                     # 何も書いていない


# ── 書く道（作り物の Drive の口へ実際に書かせて、出す物のタブ・中身・名と版・管理表まで照らす） ──
防ぐ故障_書く道 = """出す.py が新しいスプレッドシートをタブの名を渡さずに作り（タブは「シート1」だけ）、'<物>'!A1 へ書いて
本物の Drive が範囲の読めない赤で止まった＝中身の無いスプレッドシートが 2_出す物 に残った。作り物の Drive が無いタブへの
書きを黙って作っていたので試験は緑だった。今は作り物も無いタブへの書きで止まる。"""


def _回す(monkeypatch, d, 根id, 回, 取る=None):
    """出す.main を 1 回。取る に dict を渡すと 月次が組んだ出す物（読んで回す の返り）をそこへ写す（中身の照らし用）。"""
    元の = 出す.読んで回す
    def 写す(*a, **k):
        o, 赤 = 元の(*a, **k)
        if 取る is not None:
            取る["o"] = o
        return o, 赤
    monkeypatch.setattr(出す, "読んで回す", 写す)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = 出す.main(["--会社", 手.会社, "--支給月", "2027-02", "--回", 回, "--根", 根id])
    return code, json.loads(buf.getvalue())


def _id(x):
    return x["url"].rsplit("/", 1)[1]


@pytest.mark.parametrize("回", ["給与", "月"])
def test_書く道_出す物は物の名のタブ1つに月次が組んだ表そのままが入り_名は版1(monkeypatch, 回):
    import drive口
    d, 根id, ids = 置._事務所(("2027.02支給（1月分）",), 年=2027, 会社の値=_会社の値())
    monkeypatch.setattr(drive口, "開く", lambda **_: d)
    取った = {}
    code, out = _回す(monkeypatch, d, 根id, 回, 取った)
    assert code == 0 and out["出した"] is True, out
    出す物 = ids[f"2027.02支給（1月分）/{置.元.名と版.出す置き場}"]
    組んだ = {x.物: x for x in 出す.出す物たち(取った["o"])}
    assert {x["物"] for x in out["置いた"]} == set(組んだ)
    for x in out["置いた"]:
        f = d.物[_id(x)]
        assert f["親"] == 出す物 and f["name"] == x["名"] == f"{x['物']}_{手.会社}_2027-02_v1"
        assert list(f["タブ"]) == [x["物"]], f["タブ"]            # シート1 だけの空の本にしない
        want = [[("" if c is None else str(c)) for c in r] for r in 組んだ[x["物"]].表]
        assert d.表を読む(_id(x), f"'{x['物']}'!A1:ZZ") == [r for r in want], x["物"]
        assert len(want) > 1                                       # 見出しだけでなく人の行が入る
    管 = 置.型の口.Driveの名("管理表")
    管理 = d.名で引く(根id, 管)["id"]
    出た = d.表を読む(管理, f"'{置.表.Driveのタブ('出した物')}'!A1:Z")
    h = 出た[0]
    assert sorted(r[h.index("今の版")] for r in 出た[1:]) == sorted(x["名"] for x in out["置いた"])
    assert {r[h.index("リンク")] for r in 出た[1:]} == {x["url"] for x in out["置いた"]}


def test_書く道_出し直すと版2が2_出す物に1つだけ残り_版1は9_履歴へ移る(monkeypatch):
    import drive口
    d, 根id, ids = 置._事務所(("2027.02支給（1月分）",), 年=2027, 会社の値=_会社の値())
    monkeypatch.setattr(drive口, "開く", lambda **_: d)
    assert _回す(monkeypatch, d, 根id, "給与")[0] == 0
    code, out = _回す(monkeypatch, d, 根id, "給与")
    assert code == 0, out
    出す物 = ids[f"2027.02支給（1月分）/{置.元.名と版.出す置き場}"]
    assert sorted(x["name"] for x in d.子を並べる(出す物)) == sorted(x["名"] for x in out["置いた"])
    assert all(x["名"].endswith("_v2") for x in out["置いた"])
    履歴 = [x["name"] for x in d.子を並べる(ids["履歴"])]
    assert sorted(履歴) == sorted(x["名"][:-1] + "1" for x in out["置いた"])


def test_書く道_書く途中で落ちたら_作った物と移した物のidを返し黙って残さない(monkeypatch):
    import drive口
    d, 根id, ids = 置._事務所(("2027.02支給（1月分）",), 年=2027, 会社の値=_会社の値())
    monkeypatch.setattr(drive口, "開く", lambda **_: d)
    元の書く, 回数 = d.表へ書く, []
    def 二本目で落ちる(sid, 範囲, 値):
        if d.物.get(sid, {}).get("親") == 出す物:
            回数.append(sid)
            if len(回数) == 2:
                raise OSError("作り物の Drive が落ちた")
        return 元の書く(sid, 範囲, 値)
    出す物 = ids[f"2027.02支給（1月分）/{置.元.名と版.出す置き場}"]
    管理 = d.名で引く(根id, 置.型の口.Driveの名("管理表"))["id"]
    import copy
    前の管理表 = copy.deepcopy(d.物[管理]["タブ"])
    d.表へ書く = 二本目で落ちる
    code, out = _回す(monkeypatch, d, 根id, "給与")
    assert code == 2 and out["出した"] is False, out
    assert out["赤"] == ["書く途中で止まった: OSError: 作り物の Drive が落ちた"]
    残 = out["残った物"]
    assert [x["中身"] for x in 残] == ["書けた", "まだ（空のシート）"], 残
    assert {x["id"] for x in 残} == {x["id"] for x in d.子を並べる(出す物)}   # 2_出す物 に在る物は全部 id で返る
    assert out["書いた"] == [f"2_出す物: {残[0]['名']}"] and out["移した物"] == []
    assert d.物[管理]["タブ"] == 前の管理表                                 # 管理表へは何も書かない


def test_作り物のDriveは無いタブへの書きで止まる():
    from drive口.作り物 import 作り物のDrive
    d = 作り物のDrive()
    sid = d.シートを作る(d.根を作る(), "作り物の本")
    with pytest.raises(KeyError, match="タブが無い"):
        d.表へ書く(sid, "'取り込み'!A1", [["a"]])
    with pytest.raises(KeyError, match="タブが無い"):
        d.表へ足す(sid, "'取り込み'!A1", [["a"]])
    assert d.タブを並べる(sid) == ["シート1"]


# ── 締めの記録の照らし（作り物の Drive から 1 命令で。締めの記録は 6_計算の結果（人ごと）に同居する） ──
def _出す(monkeypatch, capsys, 会社の値, 壊す=None):
    import drive口
    d, 根id, ids = 置._事務所(("2027.02支給（1月分）",), 年=2027, 会社の値=会社の値)
    if 壊す:
        壊す(d, ids)
    monkeypatch.setattr(drive口, "開く", lambda **_: d)
    code = 出す.main(["--会社", 手.会社, "--支給月", "2027-02", "--回", "給与", "--根", 根id])
    return code, json.loads(capsys.readouterr().out)


def _除いた(out):
    return {str(x["NO"]): str(x["理由"]) for x in out["除いた人"]}


@pytest.mark.parametrize("状態, 訳", [("まだ", "締めの記録が「まだ」"), (None, "締めの記録に行が無い")])
def test_締まっていない人と締めの行の無い人だけ除かれほかの人は出る(monkeypatch, capsys, 状態, 訳):
    """締めの記録が まだ の人・その支給月の締めの行が無い人は仮で出口へ出さない。ほかの人は待たせず出す。値は全部作り物。"""
    code, out = _出す(monkeypatch, capsys, _会社の値(締めの状態={"0002": 状態}))
    assert code == 0 and out["出した"] is True, out
    除 = _除いた(out)
    assert set(除) == {"0002"} and 訳 in 除["0002"], out


# ── 質問と回答の止まり（振り分け・答えの無い問い）。人の物はその人だけ・会社の物は会社の全員を仮で除く＝止めない ──
顧 = "C9001"   # 作り物の事務所の自社の顧客ID（test_出す_置き場._事務所）


def _問いの値(振り分けたち=(), 問いたち=(), **kw):
    return _会社の値(質問と回答=例の表(顧, 問いたち=問いたち, 振り分けたち=振り分けたち), **kw)


def test_人の振り分けがまだ反映されていなければその人だけ除かれほかの人は出る(monkeypatch, capsys):
    """対象＝社員ID の振り分けが反映済みでない＝その人だけ仮（出口へ出ない）。ほかの人は待たせず出す。値は全部作り物。"""
    振 = 例の振り分け("Q-作り物-091", 顧, 対象="0002", 反映先="マスタ/社員", 何を="基本給", 値="1")
    code, out = _出す(monkeypatch, capsys, _問いの値([振]))
    assert code == 0 and out["出した"] is True, out
    除 = _除いた(out)
    assert set(除) == {"0002"} and "Q-作り物-091" in 除["0002"], out
    assert any(s["問いの鍵"] == "Q-作り物-091" and s["対象"] == "0002" for s in out["止まり"]), out


def test_会社の振り分けがまだ反映されていなければその会社の全員が除かれ何も出ない(monkeypatch, capsys):
    """対象＝会社（決まりの md の反映先も会社）＝その会社の全員を仮。何も出さず、止まりに問いの鍵と通し方を返す。値は全部作り物。"""
    振 = 例の振り分け("Q-作り物-092", 顧, 対象="0001", 反映先="給与のルール.md", 何を="作り物の決まり")   # md は会社の物
    code, out = _出す(monkeypatch, capsys, _問いの値([振]))
    assert out["出した"] is False, out
    assert set(_除いた(out)) == set(作.人たち), out
    s, = out["止まり"]
    assert s["対象"] == "会社" and s["問いの鍵"] == "Q-作り物-092" and "反映済み" in s["何をすれば通るか"], out


def test_反映しないと後の月の振り分けは止めない(monkeypatch, capsys):
    """反映先＝反映しない・効く月が後の月の振り分けは、この月を止めない（全員出る）。値は全部作り物。"""
    振たち = [例の振り分け("Q-作り物-093", 顧, 反映先="反映しない"),
            例の振り分け("Q-作り物-094", 顧, 対象="0001", 効く月="2027-05")]
    code, out = _出す(monkeypatch, capsys, _問いの値(振たち))
    assert code == 0 and out["出した"] is True and _除いた(out) == {}, out
    assert not out.get("止まり"), out


def test_出し済みの前の月に効く振り分けは出し直しの候補に出て今月は止めない(monkeypatch, capsys):
    """管理表で出し済みの 2027.01 に効く振り分け＝今月を止めず 出し直しの候補 に返す。値は全部作り物。"""
    from 管理表 import 管理表 as 表
    def 出し済みにする(d, ids):
        d.表へ足す(ids["管理表"], f"'{表.Driveのタブ('月の状況')}'!A1", [[手.会社, "2027.01支給", "済", "", "", ""]])
    振 = 例の振り分け("Q-作り物-095", 顧, 対象="0003", 効く月="2027-01")
    code, out = _出す(monkeypatch, capsys, _問いの値([振]), 出し済みにする)
    assert code == 0 and out["出した"] is True and _除いた(out) == {}, out
    c, = out["出し直しの候補"]
    assert c["問いの鍵"] == "Q-作り物-095" and c["効く月"] == "2027-01" and c["対象"] == "0003", out


def test_止まりは全部1回で見え_形の崩れも止める(monkeypatch, capsys):
    """人の振り分け 2 人分・反映先が 5 種でない振り分け・答えの無い問いが同時にあれば、1 回の空回しで全部の止まりが見える。
    反映先が 5 種でない振り分け（形の崩れ）は「反映しない」と言えない＝その人を止め、形の崩れ にも直し方つきで返す。値は全部作り物。
    出す.py は Drive の 3 タブだけを読む＝問いの選択肢の振り分け（確認ページの問いの JSON が持つ・表の列に無い）は渡らず、
    答えの無い問いは候補の人が決まらないので会社を止める（安全な側）。"""
    振たち = [例の振り分け("Q-作り物-081", 顧, 対象="0001"), 例の振り分け("Q-作り物-082", 顧, 対象="0002"),
            例の振り分け("Q-作り物-083", 顧, 対象="0003", 反映先="作り物の知らない先")]
    問 = 例の問い("Q-作り物-084", 顧, 選択肢の振り分け={"はい": [{"対象": "0003", "効く月": ""}]})
    code, out = _出す(monkeypatch, capsys, _問いの値(振たち, [問]))
    assert {(s["対象"], s["問いの鍵"]) for s in out["止まり"]} == {
        ("0001", "Q-作り物-081"), ("0002", "Q-作り物-082"), ("0003", "Q-作り物-083"), ("会社", "Q-作り物-084")}, out
    assert out["出した"] is False and {"0001", "0002"} <= set(_除いた(out)), out
    assert any("Q-作り物-083" in x and "通すには" in x for x in out["形の崩れ"]), out


def test_締めの記録が読めないと空と読まず止まる(monkeypatch, capsys):
    """6_計算の結果（人ごと）に締めの状態の列が無い＝締めの記録が読めない。誰も締まっていないと読まず、何も出さず止まる。値は全部作り物。"""
    from 初期設定 import 型の口
    def 壊す(d, ids):
        台帳 = 型の口.名("台帳")
        g = d.物[ids[2027]]["タブ"][型の口.タブの名(台帳, "人ごとの月の数字")]
        g[0] = ["壊した列" if c == "締めの状態" else c for c in g[0]]
    code, out = _出す(monkeypatch, capsys, _会社の値(), 壊す)
    assert code != 0 and out["出した"] is False, out
    assert any("締めの状態" in x and "空と読まない" in x for x in out["赤"]), out


def test_有給の始めの列へ反映する振り分けが残っても給与は出し_有給の止めた人に訳を返す(monkeypatch, capsys):
    """2026-11-28 オーナーの決め: 有給の始めの日を聞いている間（答えの振り分けがまだ反映されていない＝次の月から）も給与は出す。
    有給の始めの列（マスタ/社員/有給の始めの日 など）だけに効く止まりは仮にせず、有給休暇管理表の行だけ外す。値は全部作り物。"""
    振 = 例の振り分け("Q-作り物-096", 顧, 対象="0002", 反映先="マスタ/社員", 何を="有給の始めの日", 値="2027-01-31")
    code, out = _出す(monkeypatch, capsys, _問いの値([振]))
    assert code == 0 and out["出した"] is True and out["除いた人"] == [], out
    assert not out.get("止まり"), out
    止めた = {str(a["NO"]): a["理由"] for a in out["有給の止めた人"]}
    assert "Q-作り物-096" in 止めた["0002"], out   # 始めの日が在る人も、反映を待つ間は有給休暇管理表の行だけ外す
