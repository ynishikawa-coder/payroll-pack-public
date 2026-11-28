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

from 月次_試験の例 import 例をMDに, 例の問いの表  # noqa: E402

手, 出す = 置.手, 置.出す


def _締めの記録(C, 状態: dict | None = None):
    """締めの記録の格子（型の見出し）。状態: {NO: 締めの状態}（無い NO は 締まった・値が None の NO は行なし）。"""
    import 月次
    頭 = list(月次.勤怠の照らし.締めの列)
    状 = {NO: "締まった" for NO in 作.人たち} | (状態 or {})
    return [頭, *[[{"会社": C, "支給月": 作.支給月, "NO": NO, "締めの状態": v}.get(c, "") for c in 頭]
                 for NO, v in 状.items() if v is not None]]


def _会社の値(締めの状態: dict | None = None, 質問=None):
    """作り物の会社 1 社分（マスタ・確定した勤怠・締めの記録・決まり・質問と回答）。呼び名は 手.会社。
    締めの状態: _締めの記録 へ渡す（既定は全員 締まった）。質問: 質問と回答の格子（既定は例の問いの表）。"""
    import 月次
    作.C = 手.会社
    C = 作.C
    タブ = 作._タブ(人={NO: {"入社日": "2020-04-01"} for NO in 作.人たち})
    読 = 月次.読んだままの勤怠を作る(作.支給月, C, タブ, [{"部品": "Excel出勤簿", "値": 作._出勤簿()}], 置き場=None)
    台帳 = 月次.台帳の形.勤怠の表たち(確定=True, 勤怠=読["表A"], 勤怠の区間=読["表B"])
    return {"マスタ": タブ,
            "台帳": {**台帳, "読んだままの勤怠": 読["読んだままの勤怠"], "読んだままの勤怠の区間": 読["読んだままの勤怠の区間"],
                     "締めの記録": _締めの記録(C, 締めの状態)},
            "給与のルール": 例をMDに(作._例(C)), "作業のルール": "# 作業のルール（作り物）\n",
            "質問": 例の問いの表(C) if 質問 is None else 質問}


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
    assert set(置いた) == {"取り込み", "支給控除一覧"}, out
    for 名 in 置いた.values():
        assert d.名で引く(出す物, 名) is not None, 名   # 月の 2_出す物 へ書いた


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


def test_持ち主の無い答えの無い問いがあると会社が止まり_番号と通し方を名指す(monkeypatch, capsys):
    """答えの無い問い（設問.答えの無い問いか）がどの人の 残る問いの番号 にも無い＝誰を待たせるか決まらない＝会社を止める。
    通し方 3 つ（残る問いの番号に書く・答える・取り下げる）を言う。値は全部作り物。"""
    C = 手.会社
    問 = {"会社": C, "問いの番号": "Q-作り物-099", "支給月": 作.支給月, "質問": "作り物の問い", "回答": "分からない",
         "反映する支給月": 作.支給月}
    code, out = _出す(monkeypatch, capsys, _会社の値(質問=例の問いの表(C, [問])))
    assert code != 0 and out["出した"] is False, out
    赤 = " ".join(out["赤"])
    for 語 in ("Q-作り物-099", "残る問いの番号", "答える", "取り下げ"):
        assert 語 in 赤, (語, out)


def test_問いで止まる訳は全部集めて1回で止まる(monkeypatch, capsys):
    """持ち主の無い答えの無い問い と まだ反映されていない答え（前の月の物も）が同時にあれば、1 回の空回しで両方の番号が赤に出る。値は全部作り物。"""
    C = 手.会社
    無主 = {"会社": C, "問いの番号": "Q-作り物-096", "支給月": 作.支給月, "質問": "作り物の問い", "回答": "", "反映する支給月": 作.支給月}
    未反映 = {"会社": C, "問いの番号": "Q-作り物-095", "支給月": 作.支給月, "質問": "作り物の問い", "回答": "作り物の答え",
            "反映先": "2_マスタ/会社/作り物.項目", "反映する支給月": "2000.01支給"}
    code, out = _出す(monkeypatch, capsys, _会社の値(質問=例の問いの表(C, [無主, 未反映])))
    assert code != 0 and out["出した"] is False, out
    赤 = " ".join(out["赤"])
    for 語 in ("持ち主の無い答えの無い問い Q-作り物-096", "答えがまだ反映されていない問い Q-作り物-095", "後の月"):
        assert 語 in 赤, (語, out)


@pytest.mark.parametrize("反映する支給月", ["", "読めない字"])
def test_持ち主の無い問いの反映する支給月が空か読めないと会社が止まる(monkeypatch, capsys, 反映する支給月):
    """反映する支給月 が空か月と読めない持ち主の無い答えの無い問い＝どの月の問いか決まらない＝会社を止め、反映する支給月 を書く通し方も言う。値は全部作り物。"""
    C = 手.会社
    問 = {"会社": C, "問いの番号": "Q-作り物-098", "支給月": 作.支給月, "質問": "作り物の問い", "回答": "",
         "反映する支給月": 反映する支給月}
    code, out = _出す(monkeypatch, capsys, _会社の値(質問=例の問いの表(C, [問])))
    assert code != 0 and out["出した"] is False, out
    赤 = " ".join(out["赤"])
    for 語 in ("Q-作り物-098", "反映する支給月", "残る問いの番号", "取り下げ"):
        assert 語 in 赤, (語, out)


def test_持ち主の無い問いもほかの支給月の物なら会社は止まらない(monkeypatch, capsys):
    """反映する支給月 がほかの支給月の持ち主の無い答えの無い問いは、この支給月を止めない（全員出る）。値は全部作り物。"""
    C = 手.会社
    問 = {"会社": C, "問いの番号": "Q-作り物-097", "支給月": 作.支給月, "質問": "作り物の問い", "回答": "",
         "反映する支給月": "2027.05支給"}
    code, out = _出す(monkeypatch, capsys, _会社の値(質問=例の問いの表(C, [問])))
    assert code == 0 and out["出した"] is True, out
    assert _除いた(out) == {}, out


def test_持ち主の無い問いも残る問いの番号に書けば通り_その人だけ除かれる(monkeypatch, capsys):
    """同じ問いを 0003 の 残る問いの番号 に書けば会社は止まらず、0003 は仮で除かれ、ほかの人は出る。値は全部作り物。"""
    C = 手.会社
    問 = {"会社": C, "問いの番号": "Q-作り物-099", "支給月": 作.支給月, "質問": "作り物の問い", "回答": "",
         "反映する支給月": 作.支給月}
    値 = _会社の値(締めの状態={"0003": "まだ"}, 質問=例の問いの表(C, [問]))
    頭, *行 = 値["台帳"]["締めの記録"]
    for r in 行:
        if r[頭.index("NO")] == "0003":
            r[頭.index("残る問いの番号")] = "Q-作り物-099"
    code, out = _出す(monkeypatch, capsys, 値)
    assert code == 0 and out["出した"] is True, out
    assert set(_除いた(out)) == {"0003"}, out


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
