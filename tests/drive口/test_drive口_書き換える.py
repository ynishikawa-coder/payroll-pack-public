"""drive口 の ファイルを書き換える: 在る file の中身だけを置き換える（作らない・名と親と mime はそのまま・中身を持たない物は拒む）。
作り物のDrive と、実の口（Googleの口）が打つ頼みの形（files.update に media だけ・body なし）を照らす。本物の Google には触らない。"""
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from drive口 import _google  # noqa: E402
from drive口.作り物 import 作り物のDrive  # noqa: E402


def _口():
    d = 作り物のDrive()
    根 = d.根を作る("給与計算")
    f = d.フォルダを作る(根, "1_決まり")
    md = d.ファイルを置く(f, "給与のルール.md", "## 欠勤\n- 引く\n".encode(), "text/markdown")
    return d, f, md


def test_作り物は中身だけを置き換え_名と親とmimeは変えず_数も増えない():
    d, f, md = _口()
    前 = {k: dict(v) for k, v in d.物.items()}
    d.ファイルを書き換える(md, "## 欠勤\n- 半日は引かない\n".encode())
    assert d.ファイルを読む(md).decode() == "## 欠勤\n- 半日は引かない\n"
    assert set(d.物) == set(前)
    for k in ("id", "name", "mimeType", "親"):
        assert d.物[md][k] == 前[md][k]
    assert d.名で引く(f, "給与のルール.md")["id"] == md


def test_作り物は無いfileを作らずKeyError_フォルダとシートはValueError():
    d, f, md = _口()
    n = len(d.物)
    with pytest.raises(KeyError):
        d.ファイルを書き換える("無いid", b"x")
    with pytest.raises(ValueError):
        d.ファイルを書き換える(f, b"x")
    シート = d.シートを作る(f, "作り物の表")
    with pytest.raises(ValueError):
        d.ファイルを書き換える(シート, b"x")
    assert len(d.物) == n + 1   # シートを作った 1 つだけ


class _頼み:
    def __init__(self, 値):
        self.値 = 値

    def execute(self):
        return self.値


class _files:
    def __init__(self, mime):
        self.mime, self.打った = mime, []

    def get(self, **kw):
        self.打った.append(("get", kw))
        return _頼み({"mimeType": self.mime})

    def update(self, **kw):
        self.打った.append(("update", kw))
        return _頼み({"id": kw["fileId"]})

    def create(self, **kw):  # 呼ばれたら落とす（作らない）
        raise AssertionError("files.create を打った")


class _drive:
    def __init__(self, mime):
        self.f = _files(mime)

    def files(self):
        return self.f


class _作り物のMedia:  # googleapiclient.http.MediaInMemoryUpload の作り物（CI に googleapiclient が無くても回す）
    def __init__(self, 中身, mimetype, resumable):
        self.中身, self.mime, self.resumable = 中身, mimetype, resumable


def test_実の口はfiles_updateにmediaだけを渡し_bodyで名や親を変えない(monkeypatch):
    作り物のhttp = types.ModuleType("googleapiclient.http")
    作り物のhttp.MediaInMemoryUpload = _作り物のMedia
    monkeypatch.setitem(sys.modules, "googleapiclient", types.ModuleType("googleapiclient"))
    monkeypatch.setitem(sys.modules, "googleapiclient.http", 作り物のhttp)
    d = _drive("text/markdown")
    _google.Googleの口(d, None).ファイルを書き換える("作り物のid", "本文".encode())
    (g, gk), (u, uk) = d.f.打った
    assert g == "get" and u == "update"
    assert uk["fileId"] == "作り物のid" and uk["supportsAllDrives"] is True
    assert not ({"body", "addParents", "removeParents"} & set(uk))
    m = uk["media_body"]
    assert isinstance(m, _作り物のMedia) and m.mime == "text/markdown" and m.中身 == "本文".encode()
    assert m.resumable is False


@pytest.mark.parametrize("mime", ["application/vnd.google-apps.folder", "application/vnd.google-apps.spreadsheet",
                                  "application/vnd.google-apps.document", "application/vnd.google-apps.form"])
def test_実の口はGoogleの物とフォルダを拒みupdateを打たない(mime, monkeypatch):
    monkeypatch.setitem(sys.modules, "googleapiclient", None)  # 拒む道は googleapiclient に頼らない
    d = _drive(mime)
    with pytest.raises(ValueError):
        _google.Googleの口(d, None).ファイルを書き換える("作り物のid", b"x")
    assert [k for k, _ in d.f.打った] == ["get"]
