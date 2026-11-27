"""Drive口 — パックが自分で Google Drive（Drive v3・Sheets v4）を開いて読み書きする口。

形の約束（窓3 と窓4・2026-11-27）の正本はこの file。名と引数を変える時は使う側（出口/出す.py）と揃える。
- 鍵と置き場の根の id はパックの外から受け取る（鍵は引数の file か環境の変数の名・根は引数か環境の変数の名）。
  鍵の値・実の id はこの repo に置かない。
- google の module はここでは import しない（開く の中でだけ import する）。入っていない環境でも import でき、
  試験は 作り物.作り物のDrive で回る。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

鍵の変数名の既定 = "GOOGLE_DRIVE_SA_JSON"
根の変数名の既定 = "PAYROLL_OFFICE_ROOT_ID"


@runtime_checkable
class Drive口(Protocol):
    def 子を並べる(self, フォルダid: str) -> list[dict]: ...  # {"id","name","mimeType"}
    def 名で引く(self, 親id: str, 名: str) -> dict | None: ...  # 子の 1 つ（無ければ None・2 つ以上なら LookupError）
    def 表を読む(self, シートid: str, 範囲: str) -> list[list[str]]: ...  # A1 記法（"タブ名!A1:Z"）
    def 表へ書く(self, シートid: str, 範囲: str, 値: list[list]) -> None: ...
    def 表へ足す(self, シートid: str, 範囲: str, 値: list[list]) -> None: ...
    def タブを並べる(self, シートid: str) -> list[str]: ...
    def ファイルを読む(self, file_id: str) -> bytes: ...
    def ファイルを置く(self, 親id: str, 名: str, 中身: bytes, mime: str) -> str: ...  # 新しい file id
    def シートを作る(self, 親id: str, 名: str) -> str: ...
    def フォルダを作る(self, 親id: str, 名: str) -> str: ...


class 開けない(RuntimeError):
    """鍵が無い・読めない・google の module が無い時に、理由つきで止める（鍵の値は訳に入れない）。"""


def 開く(*, 鍵の変数名: str = 鍵の変数名の既定, 鍵のファイル: str | None = None,
        代理の人の変数名: str | None = None) -> Drive口:
    """実の Google Drive を開く。鍵は 鍵のファイル（path）か、環境の変数 鍵の変数名 の中身（サービスアカウントの JSON）。
    代理の人の変数名 を渡すと、その変数の中身（メールの宛名）を代理の人にする。鍵が無い・読めない・google の module が無い時は
    開けない で止める（訳に鍵の値を入れない）。"""
    from drive口 import _google
    return _google.開く(鍵の変数名=鍵の変数名, 鍵のファイル=鍵のファイル, 代理の人の変数名=代理の人の変数名)
