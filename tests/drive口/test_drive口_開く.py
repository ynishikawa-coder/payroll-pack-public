"""開く: 鍵は file か環境の変数の名から読み、無い・形が違う時は理由つきで止め、訳に鍵の値を出さない。
google の module が無くても drive口 は import でき、開く だけが理由つきで止まる。値は全部作り物。"""
import builtins
import json
import subprocess
import sys

import pytest

import drive口
from drive口 import _google, 開けない, 開く

秘密の印 = "作り物の秘密-ZZZ"
作り物の鍵 = {"type": "service_account", "private_key": 秘密の印, "client_email": "作り物@example.invalid"}


def test_googleが無くてもimportできる():
    code = ("import sys; sys.modules['google']=None; sys.modules['googleapiclient']=None; "
            "import drive口, drive口.置き場, drive口.作り物; print('ok')")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(_根()))
    assert r.stdout.strip() == "ok", r.stderr


def _根():
    from pathlib import Path
    return Path(drive口.__file__).resolve().parent.parent


def test_変数に鍵が無ければ変数の名を言って止める(monkeypatch):
    monkeypatch.delenv("GOOGLE_DRIVE_SA_JSON", raising=False)
    with pytest.raises(開けない, match="GOOGLE_DRIVE_SA_JSON"):
        開く()


def test_形の違う鍵は値を出さずに止める(monkeypatch):
    monkeypatch.setenv("作り物の鍵の変数", json.dumps({"type": "user", "x": 秘密の印}))
    with pytest.raises(開けない) as e:
        開く(鍵の変数名="作り物の鍵の変数")
    assert 秘密の印 not in str(e.value)
    monkeypatch.setenv("作り物の鍵の変数", "{" + 秘密の印)
    with pytest.raises(開けない, match="JSON でない") as e:
        開く(鍵の変数名="作り物の鍵の変数")
    assert 秘密の印 not in str(e.value)


def test_鍵のfileから読み_無いfileは止める(tmp_path):
    p = tmp_path / "鍵.json"
    p.write_text(json.dumps(作り物の鍵), encoding="utf-8")
    assert _google.鍵を読む(鍵の変数名="使わない", 鍵のファイル=str(p))["private_key"] == 秘密の印
    with pytest.raises(開けない, match="鍵の file が読めない"):
        開く(鍵のファイル=str(tmp_path / "無い.json"))


def test_代理の人の変数が空なら止める(monkeypatch):
    monkeypatch.setenv("作り物の鍵の変数", json.dumps(作り物の鍵))
    monkeypatch.delenv("作り物の代理", raising=False)
    with pytest.raises(開けない, match="作り物の代理"):
        開く(鍵の変数名="作り物の鍵の変数", 代理の人の変数名="作り物の代理")


def test_googleのmoduleが無ければ理由つきで止める(monkeypatch):
    monkeypatch.setenv("作り物の鍵の変数", json.dumps(作り物の鍵))
    元 = builtins.__import__

    def 無い(name, *a, **k):
        if name.startswith(("google", "googleapiclient")):
            raise ImportError(name)
        return 元(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", 無い)
    with pytest.raises(開けない, match="google の module が無い") as e:
        開く(鍵の変数名="作り物の鍵の変数")
    assert 秘密の印 not in str(e.value)


def test_表の値は字に直す():
    assert [_google.セルの字(v) for v in (12.0, 1.5, True, None, "あ")] == ["12", "1.5", "TRUE", "", "あ"]


class _呼び:
    """Google の API の呼び方（files().list(...).execute()）を真似る作り物。受けた引数を記録する。"""
    def __init__(self, 返し, 記録):
        self._返し, self._記録 = 返し, 記録

    def __getattr__(self, 名):
        def f(*a, **k):
            self._記録.append((名, k))
            return _呼び(self._返し, self._記録)
        return f

    def execute(self):
        return self._返し.pop(0)


def test_Googleの口は共有ドライブ込みで引き_名の引用を外さない():
    記録 = []
    d = _呼び([{"files": [{"id": "作り物-1", "name": "a'b", "mimeType": "x"}]}], 記録)
    口 = _google.Googleの口(d, None)
    assert 口.名で引く("作り物-親", "a'b")["id"] == "作り物-1"
    _, k = 記録[-1]
    assert "name = 'a\\'b'" in k["q"] and k["supportsAllDrives"] and k["includeItemsFromAllDrives"]
    d = _呼び([{"files": [{"id": "1", "name": "n", "mimeType": "x"}, {"id": "2", "name": "n", "mimeType": "x"}]}], [])
    with pytest.raises(LookupError, match="2 つ在る"):
        _google.Googleの口(d, None).名で引く("作り物-親", "n")


def test_Googleの口は表をRAWで書き読む時は字に直す():
    記録 = []
    s = _呼び([None, {"values": [[1.0, True]]}], 記録)
    口 = _google.Googleの口(None, s)
    口.表へ書く("作り物-表", "'タブ'!A1", [["1"]])
    assert ("update", {"spreadsheetId": "作り物-表", "range": "'タブ'!A1", "valueInputOption": "RAW", "body": {"values": [["1"]]}}) in 記録
    assert 口.表を読む("作り物-表", "'タブ'!A1:Z") == [["1", "TRUE"]]
    assert ("get", {"spreadsheetId": "作り物-表", "range": "'タブ'!A1:Z", **_google.読む形}) in 記録
