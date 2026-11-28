"""作り物の Drive の上で、道具/移しを当てる.py が点検の案だけを当て、点検の後に変わった物・中身の違う行には触らないこと。
値は全部作り物（実の会社・人・額・id を持たない）。事務所の組み方は 移しの点検 の試験の物を、書ける作り物で借りる。"""
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

import drive口
from drive口.作り物 import 作り物のDrive
from 初期設定 import 型の口

根 = Path(__file__).resolve().parents[2]


def _読む(名, path):
    s = importlib.util.spec_from_file_location(名, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


当 = _読む("移しを当てる", 根 / "道具" / "移しを当てる.py")
組 = _読む("移しの点検の試験_借り", Path(__file__).with_name("test_作り物_移しの点検.py"))
組.書けない作り物 = 作り物のDrive   # 当てる試験は書ける作り物で組む
点 = 当.点
今 = datetime(2099, 3, 10, 9, 30, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
月 = "2099.03支給（2月分）"
D = 型の口.Driveの名


def _計画(d, r, 会社=None):
    return 当.計画を組む(d, 点.点検(d, r, 当てる用=True), 会社)


def _シート(d, 名):
    return next(i for i, x in d.物.items() if x["name"] == 名 and "タブ" in x)


def _写し(d):
    return json.dumps({i: {k: v for k, v in x.items() if k != "版"} for i, x in d.物.items()},
                      ensure_ascii=False, sort_keys=True, default=repr)


def _記録(d):
    return [x for x in d.物.values() if x["name"].startswith(当.記録の頭)]


def _回す(d, r, *a):
    return 当.main(["--根", r, "--間", "0", *a], 口=d, 眠る=lambda s: None, 今=今)


def _重なる記録():
    x = dict(顧客ID="C9001", 記録日="2099-01-01", 社員ID="1", 項目="作り物の前の名", 新しい値="1")
    return [x, x, dict(x, 新しい値="2"), dict(x, 新しい値="2")]


def test_乾いた回しは何も書かない(capsys):
    d, r = 組._事務所(状態="")
    前 = _写し(d)
    assert _回す(d, r) == 0
    assert _写し(d) == 前
    out = json.loads(capsys.readouterr().out)
    assert out["乾いた回し"] and out["会社"]["C9001"]["数"]["書く"] >= 1
    assert "作り物-" not in json.dumps(out, ensure_ascii=False)   # id を出さない


def test_当てると書き_2度目は何もしない():
    d, r = 組._事務所(状態="")
    計画 = _計画(d, r)
    assert 計画["C9001"]["書く"] and 計画["C9001"]["足す"]
    返り = 当.当てる(d, r, 計画, 今=今)
    assert 返り["数"]["C9001"]["書いた"] == len(計画["C9001"]["書く"])
    一覧 = d.物[_シート(d, D("事務所の設定"))]["タブ"][型の口.タブの名("事務所の設定", "会社の一覧")]
    assert 一覧[1][組.一覧の頭.index("状態")] == "立ち上げ"
    月の状況 = d.物[_シート(d, D("管理表"))]["タブ"][点.管理表.Driveのタブ("月の状況")]
    assert any(月 in r_ for r_ in 月の状況[1:])
    二度目 = _計画(d, r)
    assert 当.当てる数(二度目) == 0
    前 = _写し(d)
    assert 当.当てる(d, r, 二度目, 今=今) == {"記録": None, "数": {}}
    assert _写し(d) == 前


def test_点検の後に行が変われば何も当てずに止める():
    d, r = 組._事務所(状態="", 変更=_重なる記録())
    計画 = _計画(d, r)
    k = _シート(d, 型の口.タブの本(組.マ, "変更の記録"))
    タ = 型の口.タブの名(組.マ, "変更の記録")
    d.物[k]["タブ"][タ][1][組._頭(組.マ, "変更の記録").index("新しい値")] = "ほかの人が書いた"
    前 = _写し(d)
    with pytest.raises(当.止める, match="点検の時と違う"):
        当.当てる(d, r, 計画, 今=今)
    assert _写し(d) == 前 and not _記録(d)


def test_月の状況に行が足された後は足さない():
    d, r = 組._事務所(状態="")
    計画 = _計画(d, r)
    管 = _シート(d, D("管理表"))
    d.物[管]["タブ"][点.管理表.Driveのタブ("月の状況")].append(["ほかの窓の行"])
    with pytest.raises(当.止める, match="行を足さない"):
        当.当てる(d, r, 計画, 今=今)


def test_中身の違う行は消す口も消さない():
    d, r = 組._事務所(月の状況=(月,), 変更=_重なる記録())
    計画 = _計画(d, r)
    x = 計画["C9001"]["消す"][0]["_当て"]
    with pytest.raises(drive口.版が違う):
        d.行を消す(x["シート"], x["タブ"], x["行"], [*x["読んだ行"][:-1], "違う"])


def test_消すのはタブごとに下の行から():
    d, r = 組._事務所(月の状況=(月,), 変更=_重なる記録())
    計画 = _計画(d, r)
    消す = sorted(x["_当て"]["行"] for x in 計画["C9001"]["消す"])
    assert 消す == [3, 5]
    呼んだ = []
    元 = d.行を消す
    d.行を消す = lambda s, t, n, 行: (呼んだ.append(n), 元(s, t, n, 行))
    当.当てる(d, r, 計画, 今=今)
    assert 呼んだ == [5, 3]
    k = _シート(d, 型の口.タブの本(組.マ, "変更の記録"))
    assert len(d.物[k]["タブ"][型の口.タブの名(組.マ, "変更の記録")]) == 3   # 頭 + 残した 2 行
    assert 当.当てる数(_計画(d, r)) == 0


def test_月のフォルダを作り_名が先に在れば止める():
    d, r = 組._事務所(月のフォルダ=(月, "2099.05支給（4月分）"), 月の状況=(月, "2099.04支給（3月分）", "2099.05支給（4月分）"))
    計画 = _計画(d, r)
    assert [x["フォルダ"] for x in 計画["C9001"]["作る"]] == ["2099.04支給（3月分）"]
    当.当てる(d, r, 計画, 今=今)
    f = [x for x in d.物.values() if x["name"] == "2099.04支給（3月分）"]
    assert len(f) == 1 and {x["name"] for x in d.物.values() if x["親"] == f[0]["id"]} == set(型の口.物たち("月の物"))
    d2, r2 = 組._事務所(月のフォルダ=(月, "2099.05支給（4月分）"), 月の状況=(月, "2099.04支給（3月分）", "2099.05支給（4月分）"))
    計画 = _計画(d2, r2)
    d2.フォルダを作る(計画["C9001"]["作る"][0]["_当て"]["親"], "2099.04支給（3月分）")
    with pytest.raises(当.止める, match="点検の後に在る"):
        当.当てる(d2, r2, 計画, 今=今)


def test_問う物と道だけの物は当てずに並べる():
    台帳 = 組._台帳の格子(勤怠=[("作り物A", "2099.03支給")], 締め=[("作り物A", "2099.03支給", "")])
    d, r = 組._事務所(月の状況=(月,), 台帳=台帳,
                    変更=[dict(顧客ID="C9001", 適用支給月="2099.03支給", 社員ID="1", 項目="社保.標準報酬", 確かめ="確認済")])
    計画 = _計画(d, r)
    assert 計画["C9001"]["問う物"] and any("道" in x for x in 計画["C9001"]["当てない"])
    assert 当.当てる数(計画) == 0
    前 = _写し(d)
    当.当てる(d, r, 計画, 今=今)
    assert _写し(d) == 前


def test_当てた回の記録を9_履歴に置く():
    d, r = 組._事務所(状態="", 変更=_重なる記録())
    当.当てる(d, r, _計画(d, r), 今=今)
    [x] = _記録(d)
    assert x["name"] == f"{当.記録の頭}2099-03-10_093000.json"
    assert d.物[x["親"]]["name"] == 型の口.名("履歴") and d.物[x["親"]]["親"] == r
    記録 = json.loads(x["中身"])
    assert 記録["いつ"] == "2099-03-10T09:30:00+09:00"
    assert 記録["会社"]["C9001"]["書いた"] >= 1 and 記録["会社"]["C9001"]["消した"] == 2
    assert "作り物-" not in x["中身"].decode() and "作り物A" not in x["中身"].decode()


def test_途中で落ちても当てた所までを記録して止める():
    d, r = 組._事務所(状態="", 変更=_重なる記録())
    計画 = _計画(d, r)
    d.行を消す = lambda *a: (_ for _ in ()).throw(drive口.上限("作り物"))
    with pytest.raises(当.止める, match="途中で止まった"):
        当.当てる(d, r, 計画, 今=今)
    記録 = json.loads(_記録(d)[0]["中身"])
    assert 記録["止まった"].startswith("上限") and 記録["会社"]["C9001"]["消した"] == 0


def test_会社で絞る_無い顧客IDは止める():
    d, r = 組._事務所(状態="")
    結果 = 点.点検(d, r, 当てる用=True)
    assert list(当.計画を組む(d, 結果, "C9001")) == ["C9001"]
    with pytest.raises(当.止める):
        当.計画を組む(d, 結果, "C0000")


def test_乾いた回しの印と違えば当てない(capsys):
    d, r = 組._事務所(状態="")
    assert _回す(d, r) == 0
    印 = json.loads(capsys.readouterr().out)["印"]
    前 = _写し(d)
    assert _回す(d, r, "--当てる", "--印", "0000") == 3
    assert _写し(d) == 前
    assert _回す(d, r, "--当てる", "--印", 印) == 0
    assert _写し(d) != 前


class _呼びを数える:
    def __init__(self, d, 呼び):
        self._d, self._呼び = d, 呼び

    def __getattr__(self, 名):
        f = getattr(self._d, 名)
        if not callable(f):
            return f

        def 打つ(*a, **k):
            self._呼び.append(名)
            return f(*a, **k)
        return 打つ


def test_当てる回しは打つ頼みの数で間をあけ_1分60頼みを超えない(capsys):
    d, r = 組._事務所(状態="", 変更=_重なる記録())   # 行を消す（3 頼み）が続く形
    眠った, 呼び = [], []
    assert 当.main(["--根", r, "--当てる"], 口=_呼びを数える(d, 呼び), 眠る=眠った.append, 今=今) == 0
    out = json.loads(capsys.readouterr().out)
    重さ = [当.頼みの数.get(n, 1) for n in 呼び]
    assert out["Google へ打った頼みの数"] == sum(重さ)
    assert 眠った == pytest.approx([1.1 * w for w in 重さ[1:]])
    assert 呼び.count("行を消す") == 2 and pytest.approx(3.3) in 眠った
    時, 打った = 0.0, []   # 眠った秒を時に積み、どの 60 秒にも 60 頼みを超えない
    for k, w in enumerate(重さ):
        時 += 眠った[k - 1] if k else 0.0
        打った += [時] * w
    assert max(sum(1 for t in 打った if s <= t < s + 60) for s in 打った) <= 60
    assert out["当てた"]["数"]["C9001"]["書いた"] >= 1


def test_頼みの数は実の口の打つ数と同じ():
    """drive口/_google.py の各口が _実行 を打つ数（self の口を呼ぶ物は足す）と 当.頼みの数 を照らす。"""
    import ast
    t = ast.parse((根 / "drive口" / "_google.py").read_text(encoding="utf-8"))
    口 = next(n for n in t.body if isinstance(n, ast.ClassDef) and n.name == "Googleの口")
    f = {n.name: n for n in 口.body if isinstance(n, ast.FunctionDef)}

    def 数(名):
        c = 0
        for n in ast.walk(f[名]):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_実行":
                c += 1
            elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                  and n.func.value.id == "self" and n.func.attr in f and n.func.attr != "_版を照らす"):
                c += 数(n.func.attr)
        return c
    実 = {名: 数(名) for 名 in f if not 名.startswith("_")}
    assert {名: n for 名, n in 実.items() if n > 1} == 当.頼みの数


def test_読めない訳と止めた訳に_Google_の赤の字を出さない(capsys):
    class 赤(Exception):
        resp = type("r", (), {"status": 403})()

        def __str__(self):
            return "https://sheets.googleapis.com/v4/spreadsheets/作り物の秘密のid"
    d, r = 組._事務所(状態="")
    d.タブを並べる = lambda *a: (_ for _ in ()).throw(赤())
    assert _回す(d, r) == 2
    e = capsys.readouterr().err
    assert "秘密" not in e and "赤（状態 403）" in e
    d, r = 組._事務所(状態="")
    d.ファイルを置く = lambda *a: (_ for _ in ()).throw(赤())   # 記録を置く で落ちる
    assert _回す(d, r, "--当てる") == 3
    e = capsys.readouterr().err
    assert "秘密" not in e and "Traceback" not in e and "赤（状態 403）" in e


def _狭い指示のタブ():
    """その月だけの指示 の見出しが 確認・原本の名前 を欠き、タブの格子も今の見出しの幅だけ（列を足す余地が無い）事務所。"""
    台 = 型の口.名("台帳")
    頭 = 組._頭(台, "その月だけの指示")
    短い = [c for c in 頭 if c not in ("確認", "原本の名前")]
    台帳 = 組._台帳の格子(指示=[組._行(短い, 会社="作り物A", 支給月="2099.03支給", NO="1", 項目="平均賃金", 値="1")],
                        指示の頭=短い)
    d, r = 組._事務所(状態="", 月の状況=(月,), 台帳=台帳)
    台帳id = _シート(d, "台帳_2099")
    タブ = 型の口.タブの名(台, "その月だけの指示")
    d.格子を決める(台帳id, タブ, 500, len(短い))
    return d, r, 台帳id, タブ, 頭, len(短い)


def test_格子の外のセルは乾いた回しで列を広げるを数え_当てると広げてから書く(capsys):
    d, r, 台帳id, タブ, 頭, 幅 = _狭い指示のタブ()
    with pytest.raises(drive口.作り物.格子の外):   # 作り物も実の Sheets と同じく格子の外へは書かない
        d.表へ書く(台帳id, drive口.範囲(タブ, f"{点.管理表.列の字(幅)}1"), [["確認"]])
    前 = _写し(d)
    assert _回す(d, r) == 0
    assert _写し(d) == 前   # 乾いた回しは広げない
    out = json.loads(capsys.readouterr().out)
    c = out["会社"]["C9001"]
    assert c["数"]["列を広げる"] == 1 and c["数"]["行を広げる"] == 0
    assert c["広げる"] == [{"タブ": タブ, "今": f"500 行 × {幅} 列", "広げて": f"500 行 × {幅 + 2} 列"}]
    assert "作り物-" not in json.dumps(out, ensure_ascii=False)   # id を出さない
    assert _回す(d, r, "--当てる", "--印", out["印"]) == 0
    当てた = json.loads(capsys.readouterr().out)["当てた"]["数"]["C9001"]
    assert 当てた["広げたタブ"] == 1
    assert d.格子を読む(台帳id)[タブ] == (500, 幅 + 2)
    assert d.表を読む(台帳id, drive口.範囲(タブ))[0][幅:幅 + 2] == ["確認", "原本の名前"]
    assert _計画(d, r)["C9001"]["広げる"] == []   # 2 度目は広げる物が無い


def test_格子で足りる案は広げず_印に広げるを入れない():
    d, r = 組._事務所(状態="")
    計画 = _計画(d, r)
    assert all(p["広げる"] == [] for p in 計画.values())
    旧 = json.dumps({c: {k: p[k] for k in ("書く", "足す", "作る", "消す")} for c, p in 計画.items()},
                   ensure_ascii=False, sort_keys=True, default=str)
    import hashlib
    assert 当.印(計画) == hashlib.sha256(旧.encode("utf-8")).hexdigest()[:16]   # 広げる物の無い案の印は前と同じ


def test_当てる途中で落ちた訳は型の名と状態の番号を持ち_id_を持たない(capsys):
    class 赤(Exception):
        resp = type("r", (), {"status": 400})()

        def __str__(self):
            return "https://sheets.googleapis.com/v4/spreadsheets/作り物の秘密のid exceeds grid limits"
    d, r = 組._事務所(状態="")
    d.表へ書く = lambda *a, **k: (_ for _ in ()).throw(赤())
    assert _回す(d, r, "--当てる") == 3
    e = capsys.readouterr().err
    assert "赤（状態 400）" in e and "秘密" not in e
    記録 = json.loads(_記録(d)[0]["中身"])
    assert 記録["止まった"] == "赤（状態 400）"
