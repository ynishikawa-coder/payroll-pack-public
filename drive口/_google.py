"""実の Google Drive の口（Drive v3・Sheets v4）。google の module はこの file の 開く の中でだけ import する。

呼び方は pixel-office の shell_common.google / core/lib/drive_upload から写した（サービスアカウントの鍵・代理の人・
共有ドライブ込み・表は UNFORMATTED_VALUE で読み字へ直す・書くは RAW）。鍵の値は訳・ログのどこにも出さない。
"""
from __future__ import annotations

import json
import os

from drive口 import 上限, 上限で書けない, 同じ行, 字にする, 範囲, 版が違う, 開けない

範囲の許し = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
読む形 = {"valueRenderOption": "UNFORMATTED_VALUE", "dateTimeRenderOption": "FORMATTED_STRING"}
フォルダのmime = "application/vnd.google-apps.folder"
シートのmime = "application/vnd.google-apps.spreadsheet"
_書き出し = {  # Google の物は中身を持たない＝書き出して読む
    "application/vnd.google-apps.document": "text/plain",
    シートのmime: "text/csv",
}
_全部のドライブ = {"supportsAllDrives": True}
_待って打ち直す状態 = (429, 500, 502, 503, 504)   # 打ちすぎ（429）と Google 側の一時の落ち（5xx）
_打つ回数 = 6
_待つ上限 = 32   # 秒。1・2・4・8・16 と倍に延ばし、上限で頭打ち


def _実行(req, *, 眠る=None, 二つできる=False, 書く=False):
    """Google の頼み 1 つを打つ（打ち直しはここ 1 か所だけ＝読む道も書く道もこの関数を通る）。
    429・5xx は待って打ち直す（1, 2, 4, 8, 16 秒・上限 32 秒・6 回まで）。
    二つできる（2 回届けば 2 つできる・2 行消える頼み＝values.append・files.create・行を消す）は 429 だけ打ち直す（429 は
    当たっていない）。5xx は Google 側で当たったか分からないので打ち直さず上げる（行やファイルが 2 つできる道を作らない）。
    429 の打ち直しが尽きたら、読む頼みは 上限、書く頼み（書く=True）は 上限で書けない（上限の子）で止める。どちらも
    ふつうの Exception＝書く流れの中の読み（リンク・読み直し）で尽きても、使う側の `except Exception` が書く途中の知らせを残せる。ほかの赤（403・404 など）と 5xx の尽きた赤はそのまま上げる（黙って空にしない）。"""
    import time
    眠る = 眠る or time.sleep
    打ち直す = (429,) if 二つできる else _待って打ち直す状態
    for i in range(_打つ回数):
        try:
            return req.execute()
        except Exception as e:  # noqa: BLE001  googleapiclient の HttpError（resp.status を持つ）
            try:
                状態 = int(getattr(getattr(e, "resp", None), "status", None))
            except (TypeError, ValueError):
                状態 = 0   # 状態の無い赤（つながらない等）は打ち直さず上げる
            if 状態 not in 打ち直す:
                raise
            if i == _打つ回数 - 1:
                if 状態 == 429:
                    何 = f"{_打つ回数} 回打った"
                    raise (上限で書けない(何) if 書く else 上限(何)) from None
                raise
            眠る(min(2 ** i, _待つ上限))


def セルの字(v) -> str:
    """表の値 → 字（12.0→"12"・真偽→TRUE/FALSE・空→""）。"""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _引用(x: str) -> str:
    return x.replace("\\", "\\\\").replace("'", "\\'")


def 鍵を読む(*, 鍵の変数名: str, 鍵のファイル: str | None) -> dict:
    """鍵の JSON を file か環境の変数から読む。無い・読めない時は 開けない（訳に値を入れない）。"""
    if 鍵のファイル:
        try:
            with open(鍵のファイル, encoding="utf-8") as f:
                字 = f.read()
        except OSError as e:
            raise 開けない(f"鍵の file が読めない（{type(e).__name__}）") from None
        出所 = "鍵の file"
    else:
        字 = os.environ.get(鍵の変数名, "")
        if not 字.strip():
            raise 開けない(f"鍵が無い（環境の変数 {鍵の変数名} が空か無い。--鍵のファイル か変数で渡す）")
        出所 = f"環境の変数 {鍵の変数名}"
    try:
        鍵 = json.loads(字)
    except ValueError:
        raise 開けない(f"{出所} の中身が JSON でない（値は出さない）") from None
    if not isinstance(鍵, dict) or 鍵.get("type") != "service_account":
        raise 開けない(f"{出所} の中身がサービスアカウントの鍵の形でない（値は出さない）")
    return 鍵


def 開く(*, 鍵の変数名: str, 鍵のファイル: str | None, 代理の人の変数名: str | None):
    鍵 = 鍵を読む(鍵の変数名=鍵の変数名, 鍵のファイル=鍵のファイル)
    代理 = ""
    if 代理の人の変数名:
        代理 = os.environ.get(代理の人の変数名, "").strip()
        if not 代理:
            raise 開けない(f"代理の人が無い（環境の変数 {代理の人の変数名} が空か無い）")
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        raise 開けない("google の module が無い（google-api-python-client と google-auth を入れる）") from None
    try:
        資格 = service_account.Credentials.from_service_account_info(鍵, scopes=範囲の許し)
    except Exception as e:  # noqa: BLE001 — 鍵の形の誤りの訳に値が混じらないよう型の名だけ出す
        raise 開けない(f"鍵からの資格が作れない（{type(e).__name__}）") from None
    if 代理:
        資格 = 資格.with_subject(代理)
    return Googleの口(build("drive", "v3", credentials=資格, cache_discovery=False),
                     build("sheets", "v4", credentials=資格, cache_discovery=False))


class Googleの口:
    def __init__(self, drive, sheets) -> None:
        self._d = drive
        self._s = sheets

    def 子を並べる(self, フォルダid: str) -> list[dict]:
        out, token = [], None
        while True:
            r = _実行(self._d.files().list(
                q=f"'{_引用(フォルダid)}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType)", pageSize=1000, pageToken=token,
                includeItemsFromAllDrives=True, **_全部のドライブ))
            out += [{"id": f["id"], "name": f["name"], "mimeType": f["mimeType"]} for f in r.get("files", [])]
            token = r.get("nextPageToken")
            if not token:
                return out

    def 名で引く(self, 親id: str, 名: str) -> dict | None:
        r = _実行(self._d.files().list(
            q=f"name = '{_引用(名)}' and '{_引用(親id)}' in parents and trashed = false",
            fields="files(id, name, mimeType)", pageSize=10,
            includeItemsFromAllDrives=True, **_全部のドライブ))
        fs = r.get("files", [])
        if len(fs) > 1:
            raise LookupError(f"同じ親の下に同じ名の物が {len(fs)} つ在る（どれかを選ばずに止める・訳に名は出さない＝名が組・会社を持つ）")
        return {"id": fs[0]["id"], "name": fs[0]["name"], "mimeType": fs[0]["mimeType"]} if fs else None

    def 表を読む(self, シートid: str, 範囲: str, *, _書く: bool = False) -> list[list[str]]:
        r = _実行(self._s.spreadsheets().values().get(spreadsheetId=シートid, range=範囲, **読む形), 書く=_書く)
        return [[セルの字(v) for v in row] for row in r.get("values", [])]

    def 表へ書く(self, シートid: str, 範囲: str, 値: list[list], *, 読んだ版: str | None = None) -> None:
        self._版を照らす(シートid, 読んだ版)
        _実行(self._s.spreadsheets().values().update(
            spreadsheetId=シートid, range=範囲, valueInputOption="RAW", body={"values": 値}), 書く=True)

    def 表へ足す(self, シートid: str, 範囲: str, 値: list[list]) -> None:
        _実行(self._s.spreadsheets().values().append(
            spreadsheetId=シートid, range=範囲, valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": 値}), 二つできる=True, 書く=True)

    def タブを並べる(self, シートid: str) -> list[str]:
        r = _実行(self._s.spreadsheets().get(spreadsheetId=シートid, fields="sheets.properties.title"))
        return [s["properties"]["title"] for s in r.get("sheets", [])]

    def ファイルを読む(self, file_id: str) -> bytes:
        m = _実行(self._d.files().get(fileId=file_id, fields="mimeType", **_全部のドライブ))["mimeType"]
        if m in _書き出し:
            return _実行(self._d.files().export(fileId=file_id, mimeType=_書き出し[m]))
        return _実行(self._d.files().get_media(fileId=file_id, **_全部のドライブ))

    def ファイルを置く(self, 親id: str, 名: str, 中身: bytes, mime: str) -> str:
        from googleapiclient.http import MediaInMemoryUpload
        f = _実行(self._d.files().create(body={"name": 名, "parents": [親id]},
                                   media_body=MediaInMemoryUpload(中身, mimetype=mime, resumable=False),
                                   fields="id", **_全部のドライブ), 二つできる=True, 書く=True)
        return f["id"]

    def ファイルを書き換える(self, file_id: str, 中身: bytes, *, 読んだ版: str | None = None) -> None:
        """在る file の中身だけを置き換える（files.update に media だけ＝body を渡さず名・親を変えない・新しい file を作らない）。
        mime は今の file の物のまま。Google の物（書き出して読む物）は中身を持たないので拒む（ValueError）。
        同じ中身を 2 回届けても 1 つ＝二つできる頼みでない（429・5xx を打ち直してよい）。
        読んだ版 を渡すと、今の版が違えば（読んだ後にほかが書いた）版が違う で書かずに止める。"""
        self._版を照らす(file_id, 読んだ版)
        m = _実行(self._d.files().get(fileId=file_id, fields="mimeType", **_全部のドライブ), 書く=True)["mimeType"]
        if m in _書き出し or m.startswith("application/vnd.google-apps."):
            raise ValueError(f"中身を書き換えられない種類の file（{m}）")
        from googleapiclient.http import MediaInMemoryUpload
        _実行(self._d.files().update(fileId=file_id,
                                    media_body=MediaInMemoryUpload(bytes(中身), mimetype=m, resumable=False),
                                    fields="id", **_全部のドライブ), 書く=True)

    def _作る(self, 親id: str, 名: str, mime: str) -> str:
        return _実行(self._d.files().create(body={"name": 名, "parents": [親id], "mimeType": mime},
                                      fields="id", **_全部のドライブ), 二つできる=True, 書く=True)["id"]

    def シートを作る(self, 親id: str, 名: str, タブたち: list[str] | None = None) -> str:
        """シートを作り、タブたちを渡せばその名のタブを並びどおりに持たせる（最初のタブは改名・残りは足す）。"""
        i = self._作る(親id, 名, シートのmime)
        if タブたち:
            r = _実行(self._s.spreadsheets().get(spreadsheetId=i, fields="sheets.properties.sheetId"), 書く=True)
            頭 = r["sheets"][0]["properties"]["sheetId"]
            頼み = [{"updateSheetProperties": {"properties": {"sheetId": 頭, "title": タブたち[0]}, "fields": "title"}}]
            頼み += [{"addSheet": {"properties": {"title": t}}} for t in タブたち[1:]]
            _実行(self._s.spreadsheets().batchUpdate(spreadsheetId=i, body={"requests": 頼み}), 書く=True)
        return i

    def 移す(self, file_id: str, 新しい親id: str) -> None:
        """file を別のフォルダへ移す（今の親を全部外して新しい親だけにする・共有ドライブ込み）。"""
        親 = _実行(self._d.files().get(fileId=file_id, fields="parents", **_全部のドライブ), 書く=True).get("parents", [])
        _実行(self._d.files().update(fileId=file_id, addParents=新しい親id, removeParents=",".join(親),
                               fields="id, parents", **_全部のドライブ), 書く=True)

    def リンク(self, file_id: str) -> str:
        """file を開く URL（表へは id でなくこの URL を書く）。"""
        return _実行(self._d.files().get(fileId=file_id, fields="webViewLink", **_全部のドライブ))["webViewLink"]

    def フォルダを作る(self, 親id: str, 名: str) -> str:
        return self._作る(親id, 名, フォルダのmime)

    def 版を読む(self, file_id: str, *, _書く: bool = False) -> str:
        """今の版（Drive の version＝中身・表が変わるたびに増える）。書く前に照らすために読んで持つ。"""
        return str(_実行(self._d.files().get(fileId=file_id, fields="version", **_全部のドライブ), 書く=_書く)["version"])

    def _版を照らす(self, file_id: str, 読んだ版: str | None) -> None:
        if 読んだ版 is None:
            return
        今 = self.版を読む(file_id, _書く=True)   # 書く途中の読み＝尽きたら 上限で書けない（書く側の知らせを残す）
        if 今 != str(読んだ版):
            raise 版が違う(f"読んだ後に書かれている（読んだ版 {読んだ版}・今の版 {今}）＝上書きしない。読み直して組み直す")

    def 字を読む(self, file_id: str) -> str:
        return 字にする(self.ファイルを読む(file_id))

    def 行を消す(self, シートid: str, タブ: str, 行番号: int, 読んだ行: list) -> None:
        """タブの 行番号（1 起点）の行を消す。消す前に今の行を読み、読んだ行と違えば（ほかが書いた・行がずれた）
        版が違う で消さない。2 回届けば 2 行消える＝二つできる頼み（5xx は打ち直さない）。"""
        if not isinstance(行番号, int) or 行番号 < 1:
            raise ValueError(f"行番号は 1 起点の数（{行番号!r}）")
        今 = self.表を読む(シートid, 範囲(タブ, f"{行番号}:{行番号}"), _書く=True)
        if not 同じ行(今[0] if 今 else [], 読んだ行):
            raise 版が違う(f"「{タブ}」の {行番号} 行目が読んだ時と違う＝消さない。読み直して組み直す")
        r = _実行(self._s.spreadsheets().get(spreadsheetId=シートid, fields="sheets.properties(sheetId,title)"), 書く=True)
        ids = [s["properties"]["sheetId"] for s in r.get("sheets", []) if s["properties"]["title"] == タブ]
        if len(ids) != 1:
            raise KeyError(f"タブが無い: {タブ}")
        _実行(self._s.spreadsheets().batchUpdate(spreadsheetId=シートid, body={"requests": [{"deleteDimension": {
            "range": {"sheetId": ids[0], "dimension": "ROWS", "startIndex": 行番号 - 1, "endIndex": 行番号}}}]}),
            二つできる=True, 書く=True)

    def 格子を読む(self, シートid: str) -> dict[str, tuple[int, int]]:
        """タブ → (行の数, 列の数)。格子の外のセルへの 表へ書く は Google が 400（exceeds grid limits）で拒む。"""
        r = _実行(self._s.spreadsheets().get(
            spreadsheetId=シートid, fields="sheets.properties(title,gridProperties(rowCount,columnCount))"))
        return {s["properties"]["title"]: (int(s["properties"].get("gridProperties", {}).get("rowCount", 0)),
                                           int(s["properties"].get("gridProperties", {}).get("columnCount", 0)))
                for s in r.get("sheets", [])}

    def 格子を広げる(self, シートid: str, タブ: str, 行の数: int, 列の数: int) -> None:
        """タブの格子を少なくとも 行の数 × 列の数 にする（今より狭めない）。大きさを決めて渡す頼み（足す頼みでない）＝
        2 度届けても同じ大きさ・打ち直してよい。今で足りれば何も書かない。"""
        r = _実行(self._s.spreadsheets().get(
            spreadsheetId=シートid, fields="sheets.properties(sheetId,title,gridProperties(rowCount,columnCount))"), 書く=True)
        ps = [s["properties"] for s in r.get("sheets", []) if s["properties"]["title"] == タブ]
        if len(ps) != 1:
            raise KeyError(f"タブが無い: {タブ}")
        今 = ps[0].get("gridProperties", {})
        行, 列 = max(int(今.get("rowCount", 0)), 行の数), max(int(今.get("columnCount", 0)), 列の数)
        if (行, 列) == (int(今.get("rowCount", 0)), int(今.get("columnCount", 0))):
            return
        _実行(self._s.spreadsheets().batchUpdate(spreadsheetId=シートid, body={"requests": [{"updateSheetProperties": {
            "properties": {"sheetId": ps[0]["sheetId"], "gridProperties": {"rowCount": 行, "columnCount": 列}},
            "fields": "gridProperties.rowCount,gridProperties.columnCount"}}]}), 書く=True)
