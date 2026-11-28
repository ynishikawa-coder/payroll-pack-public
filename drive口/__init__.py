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
    def 表へ書く(self, シートid: str, 範囲: str, 値: list[list], *, 読んだ版: str | None = None) -> None: ...  # 読んだ版＝版を読む の返り（違えば 版が違う で書かずに止める）
    def 表へ足す(self, シートid: str, 範囲: str, 値: list[list]) -> None: ...
    def タブを並べる(self, シートid: str) -> list[str]: ...
    def ファイルを読む(self, file_id: str) -> bytes: ...
    def ファイルを置く(self, 親id: str, 名: str, 中身: bytes, mime: str) -> str: ...  # 新しい file id
    def ファイルを書き換える(self, file_id: str, 中身: bytes, *, 読んだ版: str | None = None) -> None: ...  # 在る file の中身だけを置き換える（作らない・名と親と mime はそのまま・Google の物は拒む・無ければ KeyError）
    def シートを作る(self, 親id: str, 名: str, タブたち: list[str] | None = None) -> str: ...  # タブたち＝その名のタブを並びどおりに
    def 移す(self, file_id: str, 新しい親id: str) -> None: ...  # 今の親を外して新しい親へ
    def リンク(self, file_id: str) -> str: ...  # 開く URL（表へ書く時は id でなく URL）
    def フォルダを作る(self, 親id: str, 名: str) -> str: ...
    def 版を読む(self, file_id: str) -> str: ...  # 今の版（file かシートが変わるたびに増える・Drive の version）
    def 字を読む(self, file_id: str) -> str: ...  # 中身を字で（BOM を落とし改行を LF にそろえる＝字にする）
    def 行を消す(self, シートid: str, タブ: str, 行番号: int, 読んだ行: list) -> None: ...  # 1 起点。今の行が読んだ行と違えば 版が違う で消さない
    def 格子を読む(self, シートid: str) -> dict[str, tuple[int, int]]: ...  # タブ → (行の数, 列の数)＝タブの格子（その外のセルへは書けない）
    def 格子を広げる(self, シートid: str, タブ: str, 行の数: int, 列の数: int) -> None: ...  # 格子を少なくともこの大きさへ（狭めない・同じ頼みを 2 度届けても同じ）


class 開けない(RuntimeError):
    """鍵が無い・読めない・google の module が無い時に、理由つきで止める（鍵の値は訳に入れない）。"""


_上限の訳 = "Google の打てる数の上限（429・Sheets は 1 分に 60 回）に当たり、待って打ち直しても尽きた"


class 上限(RuntimeError):
    """打てる数の上限に当たり、打ち直しが尽きた（口の 1 か所＝_google._実行 だけが上げる）。訳は「上限…時を置いて打ち直す」で
    元の Google の赤を出さない。ふつうの Exception＝使う側の `except Exception` は拾え、書く途中で止まった物の知らせ
    （残った物・書いた物）を出せる。訳を分けたい使う側は `except drive口.上限` を先に置く（段を見る の「段 0/1 の訳」に化けない）。"""

    def __init__(self, 何: str = "") -> None:
        super().__init__(f"{_上限の訳}（{何}）＝時を置いて打ち直す" if 何 else f"{_上限の訳}＝時を置いて打ち直す")


class 上限で書けない(上限):
    """書く頼みで上限に当たり、打ち直しが尽きた＝書けていない（訳に「書けていない」。`except drive口.上限` で一緒に拾える）。"""

    def __init__(self, 何: str = "") -> None:
        RuntimeError.__init__(self, f"{_上限の訳}（{何}）＝書けていない・時を置いて打ち直す" if 何 else f"{_上限の訳}＝書けていない・時を置いて打ち直す")


class 版が違う(RuntimeError):
    """読んだ後にほかの人・ほかの窓が書いた（版か行が読んだ時と違う）。上書き・消しをせず止める。"""


def 字にする(中身: bytes | str) -> str:
    """中身 → 字。BOM を落とし、改行（CRLF・CR）を LF にそろえる。中身を比べる時はこの字で比べる（byte で比べない）。"""
    字 = 中身.decode("utf-8-sig") if isinstance(中身, (bytes, bytearray)) else str(中身)
    return 字.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")


def 同じ字(a: bytes | str, b: bytes | str) -> bool:
    """改行・BOM の違いだけなら同じと見る。"""
    return 字にする(a) == 字にする(b)


def 同じ行(a: list, b: list) -> bool:
    """表の 1 行どうし: セルを字にし（None は空）、末の空のセルを落として比べる。"""
    def 揃える(r):
        x = [字にする("" if c is None else str(c)) for c in (r or [])]
        while x and x[-1] == "":
            x.pop()
        return x
    return 揃える(a) == 揃える(b)


def 範囲(タブ: str, セル: str = "A1:ZZ") -> str:
    """タブの名とセル → Sheets の範囲の字（'タブ'!セル）。タブの名の ' は '' にする（そのままだと範囲が読めない・別のタブを指す）。
    範囲は使う側で f"'{タブ}'!…" と組まず、ここ 1 か所で組む。"""
    return "'" + タブ.replace("'", "''") + "'!" + セル


新しいタブの格子 = (1000, 26)   # Google が新しいタブに付ける格子（行の数, 列の数）＝これを超えて書く時は先に 格子を広げる


def セルの番地(セル: str) -> tuple[int, int]:
    """A1 のセルの字（"I1"・"AB12"）→ (行, 列)（どちらも 1 起点）。範囲（"A1:B2"）は頭のセルを読む。"""
    頭 = セル.split(":")[0].strip()
    字 = "".join(c for c in 頭 if c.isalpha()).upper()
    数 = "".join(c for c in 頭 if c.isdigit())
    if not 字 or not 数 or 頭.upper() != 字 + 数:
        raise ValueError(f"セルの字が読めない: {セル!r}")
    列 = 0
    for c in 字:
        列 = 列 * 26 + (ord(c) - 64)
    return int(数), 列


def 要る格子(セル: str, 値: list[list]) -> tuple[int, int]:
    """セル を左上に 値 を書くのに要る格子の大きさ (行の数, 列の数)。"""
    行, 列 = セルの番地(セル)
    return 行 + max(len(値), 1) - 1, 列 + max((len(r) for r in 値), default=1) - 1


def 開く(*, 鍵の変数名: str = 鍵の変数名の既定, 鍵のファイル: str | None = None,
        代理の人の変数名: str | None = None) -> Drive口:
    """実の Google Drive を開く。鍵は 鍵のファイル（path）か、環境の変数 鍵の変数名 の中身（サービスアカウントの JSON）。
    代理の人の変数名 を渡すと、その変数の中身（メールの宛名）を代理の人にする。鍵が無い・読めない・google の module が無い時は
    開けない で止める（訳に鍵の値を入れない）。"""
    from drive口 import _google
    return _google.開く(鍵の変数名=鍵の変数名, 鍵のファイル=鍵のファイル, 代理の人の変数名=代理の人の変数名)
