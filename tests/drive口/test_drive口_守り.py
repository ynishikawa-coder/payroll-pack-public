"""Drive の口の守り（受入の 5 つ）: 上限は口の 1 か所で分かる赤／版が違えば書かない／改行・BOM の違いは同じ／
読んだ行と違えば消さない／誤りの文に会社の名が出ない。作り物のDrive と、作り物の頼みで組んだ Googleの口 で照らす
（本物の Google には触らない・値は作り物だけ）。"""
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import drive口  # noqa: E402
from drive口 import _google, 置き場  # noqa: E402
from drive口.作り物 import 作り物のDrive  # noqa: E402


# ── 作り物の頼み（Googleの口 が打つ形だけを持つ） ───────────────────────────────

class _赤(Exception):
    def __init__(self, 状態):
        super().__init__(f"作り物の赤 {状態}")
        self.resp = SimpleNamespace(status=状態)


class _頼み:
    def __init__(self, 帳, 名, 値, 赤たち=()):
        self.帳, self.名, self.値, self.赤たち = 帳, 名, 値, list(赤たち)

    def execute(self):
        self.帳.append(self.名)
        if self.赤たち:
            raise self.赤たち.pop(0)
        return self.値() if callable(self.値) else self.値


class _作り物の頼み先:
    """files()・spreadsheets() の鎖を 1 つの物で受ける。赤たち＝頼みの名 → 先に上げる赤の並び。"""

    def __init__(self, *, 版="7", 行=None, 赤たち=None):
        self.帳: list[str] = []
        self.版, self.行 = 版, 行 if 行 is not None else [["A-1", "作り物", "1"]]
        self.赤たち = 赤たち or {}
        self.消した = None

    def _r(self, 名, 値):
        return _頼み(self.帳, 名, 値, self.赤たち.pop(名, ()))

    # Drive v3
    def files(self):
        return self

    def get(self, *, fileId=None, spreadsheetId=None, fields="", range=None, **_):
        if range is not None:
            self.読んだ範囲 = range
            return self._r("values.get", lambda: {"values": self.行})
        if spreadsheetId is not None:
            return self._r("sheets.get", {"sheets": [{"properties": {"sheetId": 9, "title": "タブ"}}]})
        if fields == "version":
            return self._r("files.version", {"version": self.版})
        return self._r("files.mime", {"mimeType": "text/markdown"})

    def get_media(self, **_):
        return self._r("files.media", "﻿# 決まり\r\n- 作り物\r\n".encode())

    def update(self, **kw):
        if "valueInputOption" in kw:
            return self._r("values.update", {})
        return self._r("files.update", {"id": kw.get("fileId")})

    # Sheets v4
    def spreadsheets(self):
        return self

    def values(self):
        return self

    def batchUpdate(self, *, body, **_):
        self.消した = body["requests"][0]["deleteDimension"]["range"]
        return self._r("sheets.batchUpdate", {})


@pytest.fixture(autouse=True)
def _眠らない(monkeypatch):
    import time
    monkeypatch.setattr(time, "sleep", lambda s: None)


@pytest.fixture(autouse=True)
def _作り物のgoogleapiclient(monkeypatch):
    """書く道が引く MediaInMemoryUpload を作り物に差す＝手元に googleapiclient が在っても無くても（CI）同じに回る。"""
    http = ModuleType("googleapiclient.http")
    http.MediaInMemoryUpload = lambda 中身, mimetype, resumable: SimpleNamespace(中身=中身, mime=mimetype)
    monkeypatch.setitem(sys.modules, "googleapiclient", ModuleType("googleapiclient"))
    monkeypatch.setitem(sys.modules, "googleapiclient.http", http)


def _実の口(**kw):
    先 = _作り物の頼み先(**kw)
    return _google.Googleの口(先, 先), 先


# ── 1. 429: 打ち直しで通る／尽きたら上限と分かる赤（口の 1 か所） ──────────────────

def test_429は打ち直しで通る_実の口の読む道():
    口, 先 = _実の口(赤たち={"files.version": [_赤(429), _赤(429)]})
    assert 口.版を読む("作り物-1") == "7"
    assert 先.帳.count("files.version") == 3


def test_読む時に429が尽きたら上限_元の赤でなく上限と分かる訳():
    """段を見る などの `except Exception` が拾っても、訳は「上限…時を置いて打ち直す」（元の Google の赤や段 0/1 の訳でない）。"""
    口, _ = _実の口(赤たち={"files.version": [_赤(429)] * 10})
    try:
        口.版を読む("作り物-1")
    except Exception as e:  # noqa: BLE001  使う側の形をそのまま
        拾った = e
    assert isinstance(拾った, drive口.上限) and not isinstance(拾った, _赤)
    assert "上限" in str(拾った) and "打ち直す" in str(拾った) and "作り物の赤" not in str(拾った)


def test_書く流れの中の読みで429が尽きても_使う側のexcept_Exceptionが書いた物の知らせを残せる():
    """出口/出す.py の _置く（書いた後に リンク を読む）・月次/決まりのmdを書き換える.py（書いた後に読み直す）の形。
    読む頼みの 上限 も Exception＝使う側が書いた物を返せる（BaseException だと素通りし、書いた物の知らせが消えた）。"""
    口, _ = _実の口(赤たち={"files.media": [_赤(429)] * 10})

    def 書く流れ():
        書いた = []
        try:
            口.ファイルを書き換える("作り物-1", b"x", 読んだ版=口.版を読む("作り物-1"))
            書いた.append("作り物-1")
            口.ファイルを読む("作り物-1")   # 書いた後の読み直し
            return {"書いた": 書いた}
        except Exception as e:  # noqa: BLE001
            return {"書いた": 書いた, "止まった訳": str(e), "上限": isinstance(e, drive口.上限)}

    r = 書く流れ()
    assert r["書いた"] == ["作り物-1"] and r["上限"] and "上限" in r["止まった訳"]


def test_上限で書けないは上限の子_名指しで両方拾える():
    assert issubclass(drive口.上限で書けない, drive口.上限) and issubclass(drive口.上限, Exception)
    assert "書けていない" in str(drive口.上限で書けない("x")) and "書けていない" not in str(drive口.上限("x"))


def test_書く時に429が尽きたら上限で書けない_書く前の版の読みも書く側():
    口, _ = _実の口(赤たち={"files.version": [_赤(429)] * 10})
    with pytest.raises(drive口.上限で書けない, match="上限"):
        口.ファイルを書き換える("作り物-1", b"x", 読んだ版="7")
    口, _ = _実の口(赤たち={"files.update": [_赤(429)] * 10})
    with pytest.raises(drive口.上限で書けない, match="書けていない"):
        口.ファイルを書き換える("作り物-1", b"x")


# ── 2. 版: 読んだ後にほかが書いていれば書かない ─────────────────────────────────

def test_作り物_版が変わっていればファイルも表も書かずに止まる():
    d = 作り物のDrive()
    根 = d.根を作る()
    f = d.ファイルを置く(根, "作り物.md", b"a", "text/markdown")
    s = d.シートを作る(根, "作り物の表", ["タブ"])
    vf, vs = d.版を読む(f), d.版を読む(s)
    d.ファイルを書き換える(f, b"b")          # ほかの窓が先に書いた
    d.表へ足す(s, "'タブ'!A1", [["x"]])
    with pytest.raises(drive口.版が違う):
        d.ファイルを書き換える(f, b"c", 読んだ版=vf)
    with pytest.raises(drive口.版が違う):
        d.表へ書く(s, "'タブ'!A1", [["y"]], 読んだ版=vs)
    assert d.ファイルを読む(f) == b"b" and d.表を読む(s, "'タブ'!A1:Z") == [["x"]]
    d.ファイルを書き換える(f, b"c", 読んだ版=d.版を読む(f))   # 読み直せば書ける
    assert d.ファイルを読む(f) == b"c"


def test_実の口_版が違えば書く頼みを打たない():
    口, 先 = _実の口(版="8")
    with pytest.raises(drive口.版が違う):
        口.ファイルを書き換える("作り物-1", b"x", 読んだ版="7")
    with pytest.raises(drive口.版が違う):
        口.表へ書く("作り物-1", "'タブ'!A1", [["x"]], 読んだ版="7")
    assert "files.update" not in 先.帳 and "values.update" not in 先.帳
    口.ファイルを書き換える("作り物-1", b"x", 読んだ版="8")
    assert "files.update" in 先.帳


# ── 3. 改行・BOM の違いは同じ ───────────────────────────────────────────────

def test_改行とBOMの違いは同じと見る():
    assert drive口.同じ字("﻿# a\r\nb\r\n".encode(), "# a\nb\n")
    assert drive口.同じ字(b"# a\rb", "# a\nb")
    assert not drive口.同じ字("# a\nb", "# a\nc")
    assert drive口.同じ行(["a\r\nb", None, ""], ["a\nb"])
    assert not drive口.同じ行(["a"], ["a", "b"])


def test_字を読むは作り物も実の口もBOMを落としLFにそろえる():
    d = 作り物のDrive()
    f = d.ファイルを置く(d.根を作る(), "作り物.md", "﻿# 決まり\r\n- 作り物\r\n".encode(), "text/markdown")
    口, _ = _実の口()
    assert d.字を読む(f) == 口.字を読む("作り物-1") == "# 決まり\n- 作り物\n"


# ── 4. 消す口: 読んだ行と違えば消さない ───────────────────────────────────────

def test_作り物_読んだ行と違えば消さず_同じなら消して詰める():
    d = 作り物のDrive()
    s = d.シートを作る(d.根を作る(), "作り物の表", ["タブ"])
    d.表へ書く(s, "'タブ'!A1", [["見出し"], ["A-1", "1"], ["A-2", "2"]])
    with pytest.raises(drive口.版が違う):
        d.行を消す(s, "タブ", 2, ["A-2", "2"])      # 行がずれている
    assert len(d.表を読む(s, "'タブ'!A1:Z")) == 3
    d.行を消す(s, "タブ", 2, ["A-1", 1])            # 数と字の違いは同じ
    assert d.表を読む(s, "'タブ'!A1:Z") == [["見出し"], ["A-2", "2"]]
    with pytest.raises(ValueError):
        d.行を消す(s, "タブ", 0, [])


def test_実の口_読んだ行と違えば消す頼みを打たない():
    口, 先 = _実の口(行=[["A-1", "書き換わった", "1"]])
    with pytest.raises(drive口.版が違う):
        口.行を消す("作り物-1", "タブ", 3, ["A-1", "作り物", "1"])
    assert "sheets.batchUpdate" not in 先.帳
    口, 先 = _実の口()
    口.行を消す("作り物-1", "タブ", 3, ["A-1", "作り物", "1"])
    assert 先.消した == {"sheetId": 9, "dimension": "ROWS", "startIndex": 2, "endIndex": 3}


def test_実の口_消す頼みは5xxで打ち直さない():
    """2 回届けば 2 行消える＝二つできる頼み。5xx は届いたか分からないので打ち直さず上げる。"""
    口, 先 = _実の口(赤たち={"sheets.batchUpdate": [_赤(503)]})
    with pytest.raises(_赤):
        口.行を消す("作り物-1", "タブ", 3, ["A-1", "作り物", "1"])
    assert 先.帳.count("sheets.batchUpdate") == 1


def test_タブの名のクォートは範囲で二重にし_作り物も実の口も読める():
    assert drive口.範囲("作り物's", "2:2") == "'作り物''s'!2:2"
    d = 作り物のDrive()
    s = d.シートを作る(d.根を作る(), "作り物の表", ["作り物's"])
    d.表へ書く(s, drive口.範囲("作り物's", "A1"), [["見出し"], ["A-1"]])
    d.行を消す(s, "作り物's", 2, ["A-1"])
    assert d.表を読む(s, drive口.範囲("作り物's")) == [["見出し"]]
    口, 先 = _実の口()
    with pytest.raises(KeyError):   # 作り物の頼み先のタブは「タブ」だけ＝読んだ後にタブが無いで止まる
        口.行を消す("作り物-1", "作り物's", 3, ["A-1", "作り物", "1"])
    assert 先.読んだ範囲 == "'作り物''s'!3:3"


# ── 5. 誤りの文に会社の名が出ない（顧客ID だけ） ─────────────────────────────────

_作り物の会社 = "作り物商事"


def _一覧():
    鍵 = 置き場.型の口.顧客IDの列()
    return [{鍵: "C-901", "会社": _作り物の会社, "組": "作り物組"},
            {鍵: "C-902", "会社": _作り物の会社, "組": "作り物組2"},
            {鍵: "C-903", "会社": "作り物工業", "組": "作り物組3"}]


def test_会社が一覧に無い時の赤に渡した名が出ない():
    with pytest.raises(置き場.引けない) as e:
        置き場._顧客IDを決める(_一覧(), "無い作り物社")
    assert "無い作り物社" not in str(e.value)


def test_呼び名が重なる時の赤は顧客IDだけ_会社の名が出ない():
    with pytest.raises(置き場.引けない) as e:
        置き場._顧客IDを決める(_一覧(), _作り物の会社)
    assert _作り物の会社 not in str(e.value)
    assert "C-901" in str(e.value) and "C-902" in str(e.value)


def test_同じ名が2つの時の赤に名が出ない():
    d = 作り物のDrive()
    根 = d.根を作る()
    d.フォルダを作る(根, "作り物組の物")
    d.フォルダを作る(根, "作り物組の物")
    with pytest.raises(LookupError) as e:
        d.名で引く(根, "作り物組の物")
    assert "作り物組" not in str(e.value)
