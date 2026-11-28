"""作り物のDrive — 記憶の中だけで Drive口 を満たす（試験用。実の id・鍵を持たない）。"""
from __future__ import annotations

import itertools

フォルダのmime = "application/vnd.google-apps.folder"
シートのmime = "application/vnd.google-apps.spreadsheet"


class 作り物のDrive:
    def __init__(self) -> None:
        self._番号 = itertools.count(1)
        self.物: dict[str, dict] = {}  # id → {"id","name","mimeType","親","中身" or "タブ"}

    # 試験で組む時の手伝い
    def _新しいid(self) -> str:
        return f"作り物-{next(self._番号)}"

    def 根を作る(self, 名: str = "根") -> str:
        i = self._新しいid()
        self.物[i] = {"id": i, "name": 名, "mimeType": フォルダのmime, "親": None}
        return i

    def _作る(self, 親id: str, 名: str, mime: str, **他) -> str:
        if 親id not in self.物:
            raise KeyError(f"親が無い: {親id}")
        i = self._新しいid()
        self.物[i] = {"id": i, "name": 名, "mimeType": mime, "親": 親id, **他}
        return i

    def _シート(self, シートid: str) -> dict[str, list[list[str]]]:
        x = self.物.get(シートid)
        if x is None or x["mimeType"] != シートのmime:
            raise KeyError(f"シートが無い: {シートid}")
        return x["タブ"]

    @staticmethod
    def _範囲を割る(範囲: str) -> tuple[str, int, int]:
        """'タブ!A1:Z' → (タブ, 始まりの行 0 起点, 始まりの列 0 起点)。"""
        タブ, _, セル = 範囲.rpartition("!")
        if not タブ:
            タブ, セル = セル, "A1"
        タブ = タブ.strip("'")
        頭 = セル.split(":")[0]
        字 = "".join(c for c in 頭 if c.isalpha()) or "A"
        数 = "".join(c for c in 頭 if c.isdigit()) or "1"
        列 = 0
        for c in 字.upper():
            列 = 列 * 26 + (ord(c) - 64)
        return タブ, int(数) - 1, 列 - 1

    # Drive口
    def 子を並べる(self, フォルダid: str) -> list[dict]:
        return [{"id": x["id"], "name": x["name"], "mimeType": x["mimeType"]}
                for x in self.物.values() if x["親"] == フォルダid]

    def 名で引く(self, 親id: str, 名: str) -> dict | None:
        hits = [x for x in self.子を並べる(親id) if x["name"] == 名]
        if len(hits) > 1:  # 実の口と同じく、同じ名が 2 つ以上なら選ばずに止める
            raise LookupError(f"同じ親の下に「{名}」が {len(hits)} つ在る（どれかを選ばずに止める）")
        return hits[0] if hits else None

    def 表を読む(self, シートid: str, 範囲: str) -> list[list[str]]:
        タブ, 行, 列 = self._範囲を割る(範囲)
        表 = self._シート(シートid)
        if タブ not in 表:
            raise KeyError(f"タブが無い: {タブ}")
        out = [[str(c) for c in r[列:]] for r in 表[タブ][行:]]
        while out and not any(out[-1]):
            out.pop()
        return out

    def _在るタブ(self, シートid: str, タブ: str) -> list[list[str]]:
        """書く先のタブ。本物の Drive は無いタブへの書きを範囲の読めない赤で止める＝作り物も黙って作らず止める
        （作り物がタブを作ると、タブの名を渡さずにシートを作る呼び方が試験で緑・本番だけ赤になる）。"""
        表 = self._シート(シートid)
        if タブ not in 表:
            raise KeyError(f"タブが無い: {タブ}（在るのは {list(表)}）")
        return 表[タブ]

    def 表へ書く(self, シートid: str, 範囲: str, 値: list[list]) -> None:
        タブ, 行, 列 = self._範囲を割る(範囲)
        表 = self._在るタブ(シートid, タブ)
        for k, r in enumerate(値):
            while len(表) <= 行 + k:
                表.append([])
            row = 表[行 + k]
            while len(row) < 列 + len(r):
                row.append("")
            for j, c in enumerate(r):
                row[列 + j] = "" if c is None else str(c)

    def 表へ足す(self, シートid: str, 範囲: str, 値: list[list]) -> None:
        タブ, _, 列 = self._範囲を割る(範囲)
        表 = self._在るタブ(シートid, タブ)
        末 = len(表)
        while 末 and not any(表[末 - 1]):
            末 -= 1
        del 表[末:]
        for r in 値:
            表.append([""] * 列 + ["" if c is None else str(c) for c in r])

    def タブを並べる(self, シートid: str) -> list[str]:
        return list(self._シート(シートid))

    def ファイルを読む(self, file_id: str) -> bytes:
        x = self.物.get(file_id)
        if x is None or "中身" not in x:
            raise KeyError(f"file が無い: {file_id}")
        return x["中身"]

    def ファイルを置く(self, 親id: str, 名: str, 中身: bytes, mime: str) -> str:
        return self._作る(親id, 名, mime, 中身=bytes(中身))

    def シートを作る(self, 親id: str, 名: str, タブたち: list[str] | None = None) -> str:
        return self._作る(親id, 名, シートのmime, タブ={t: [] for t in (タブたち or ["シート1"])})

    def 移す(self, file_id: str, 新しい親id: str) -> None:
        if file_id not in self.物 or 新しい親id not in self.物:
            raise KeyError(f"無い: {file_id} か {新しい親id}")
        self.物[file_id]["親"] = 新しい親id

    def リンク(self, file_id: str) -> str:
        if file_id not in self.物:
            raise KeyError(f"無い: {file_id}")
        return f"https://作り物.invalid/{file_id}"

    def フォルダを作る(self, 親id: str, 名: str) -> str:
        return self._作る(親id, 名, フォルダのmime)
