"""実の Google Drive の口（Drive v3・Sheets v4）。google の module はこの file の 開く の中でだけ import する。

呼び方は pixel-office の shell_common.google / core/lib/drive_upload から写した（サービスアカウントの鍵・代理の人・
共有ドライブ込み・表は UNFORMATTED_VALUE で読み字へ直す・書くは RAW）。鍵の値は訳・ログのどこにも出さない。
"""
from __future__ import annotations

import json
import os

from drive口 import 開けない

範囲の許し = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
読む形 = {"valueRenderOption": "UNFORMATTED_VALUE", "dateTimeRenderOption": "FORMATTED_STRING"}
フォルダのmime = "application/vnd.google-apps.folder"
シートのmime = "application/vnd.google-apps.spreadsheet"
_書き出し = {  # Google の物は中身を持たない＝書き出して読む
    "application/vnd.google-apps.document": "text/plain",
    シートのmime: "text/csv",
}
_全部のドライブ = {"supportsAllDrives": True}


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
            r = self._d.files().list(
                q=f"'{_引用(フォルダid)}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType)", pageSize=1000, pageToken=token,
                includeItemsFromAllDrives=True, **_全部のドライブ).execute()
            out += [{"id": f["id"], "name": f["name"], "mimeType": f["mimeType"]} for f in r.get("files", [])]
            token = r.get("nextPageToken")
            if not token:
                return out

    def 名で引く(self, 親id: str, 名: str) -> dict | None:
        r = self._d.files().list(
            q=f"name = '{_引用(名)}' and '{_引用(親id)}' in parents and trashed = false",
            fields="files(id, name, mimeType)", pageSize=10,
            includeItemsFromAllDrives=True, **_全部のドライブ).execute()
        fs = r.get("files", [])
        if len(fs) > 1:
            raise LookupError(f"同じ親の下に「{名}」が {len(fs)} つ在る（どれかを選ばずに止める）")
        return {"id": fs[0]["id"], "name": fs[0]["name"], "mimeType": fs[0]["mimeType"]} if fs else None

    def 表を読む(self, シートid: str, 範囲: str) -> list[list[str]]:
        r = self._s.spreadsheets().values().get(spreadsheetId=シートid, range=範囲, **読む形).execute()
        return [[セルの字(v) for v in row] for row in r.get("values", [])]

    def 表へ書く(self, シートid: str, 範囲: str, 値: list[list]) -> None:
        self._s.spreadsheets().values().update(
            spreadsheetId=シートid, range=範囲, valueInputOption="RAW", body={"values": 値}).execute()

    def 表へ足す(self, シートid: str, 範囲: str, 値: list[list]) -> None:
        self._s.spreadsheets().values().append(
            spreadsheetId=シートid, range=範囲, valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": 値}).execute()

    def タブを並べる(self, シートid: str) -> list[str]:
        r = self._s.spreadsheets().get(spreadsheetId=シートid, fields="sheets.properties.title").execute()
        return [s["properties"]["title"] for s in r.get("sheets", [])]

    def ファイルを読む(self, file_id: str) -> bytes:
        m = self._d.files().get(fileId=file_id, fields="mimeType", **_全部のドライブ).execute()["mimeType"]
        if m in _書き出し:
            return self._d.files().export(fileId=file_id, mimeType=_書き出し[m]).execute()
        return self._d.files().get_media(fileId=file_id, **_全部のドライブ).execute()

    def ファイルを置く(self, 親id: str, 名: str, 中身: bytes, mime: str) -> str:
        from googleapiclient.http import MediaInMemoryUpload
        f = self._d.files().create(body={"name": 名, "parents": [親id]},
                                   media_body=MediaInMemoryUpload(中身, mimetype=mime, resumable=False),
                                   fields="id", **_全部のドライブ).execute()
        return f["id"]

    def _作る(self, 親id: str, 名: str, mime: str) -> str:
        return self._d.files().create(body={"name": 名, "parents": [親id], "mimeType": mime},
                                      fields="id", **_全部のドライブ).execute()["id"]

    def シートを作る(self, 親id: str, 名: str) -> str:
        return self._作る(親id, 名, シートのmime)

    def フォルダを作る(self, 親id: str, 名: str) -> str:
        return self._作る(親id, 名, フォルダのmime)
