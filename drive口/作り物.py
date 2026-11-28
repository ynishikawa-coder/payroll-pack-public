"""作り物のDrive — 記憶の中だけで Drive口 を満たす（試験用。実の id・鍵を持たない）。"""
from __future__ import annotations

import itertools

from drive口 import 同じ行, 字にする, 新しいタブの格子, 版が違う

フォルダのmime = "application/vnd.google-apps.folder"
シートのmime = "application/vnd.google-apps.spreadsheet"
格子の既定 = 新しいタブの格子


class 格子の外(ValueError):
    """実の Sheets が 400「exceeds grid limits」で拒む書き（格子の外のセル）を、作り物も黙って広げずに拒む。"""


class 作り物のDrive:
    def __init__(self) -> None:
        self._番号 = itertools.count(1)
        self.物: dict[str, dict] = {}  # id → {"id","name","mimeType","親","版","中身" or "タブ"}

    # 試験で組む時の手伝い
    def _新しいid(self) -> str:
        return f"作り物-{next(self._番号)}"

    def 根を作る(self, 名: str = "根") -> str:
        i = self._新しいid()
        self.物[i] = {"id": i, "name": 名, "mimeType": フォルダのmime, "親": None, "版": 1}
        return i

    def _作る(self, 親id: str, 名: str, mime: str, **他) -> str:
        if 親id not in self.物:
            raise KeyError(f"親が無い: {親id}")
        i = self._新しいid()
        self.物[i] = {"id": i, "name": 名, "mimeType": mime, "親": 親id, "版": 1, **他}
        return i

    def _変えた(self, i: str) -> None:
        """実の Drive の version と同じく、変わるたびに版を 1 つ増やす。"""
        self.物[i]["版"] = self.物[i].get("版", 1) + 1

    def _版を照らす(self, i: str, 読んだ版: str | None) -> None:
        if 読んだ版 is None:
            return
        今 = self.版を読む(i)
        if 今 != str(読んだ版):
            raise 版が違う(f"読んだ後に書かれている（読んだ版 {読んだ版}・今の版 {今}）＝上書きしない。読み直して組み直す")

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
        if len(タブ) >= 2 and タブ[0] == タブ[-1] == "'":   # 'タブ' の囲みを外し、中の '' を ' に戻す（Sheets の A1 の書き方）
            タブ = タブ[1:-1].replace("''", "'")
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
            raise LookupError(f"同じ親の下に同じ名の物が {len(hits)} つ在る（どれかを選ばずに止める・訳に名は出さない＝名が組・会社を持つ）")
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

    def _決めた格子(self, シートid: str, タブ: str) -> tuple[int, int] | None:
        """格子を持つタブ＝この口が作ったタブ（シートを作る）と 格子を決める・格子を広げる で決めたタブ。"""
        return self.物[シートid].get("格子", {}).get(タブ)

    def _格子(self, シートid: str, タブ: str) -> tuple[int, int]:
        """タブの格子。決めた物が無いタブ（試験が中身を直に置いたタブ＝前から在る物）は、既定と今の中身の大きい方と読む。"""
        表 = self._在るタブ(シートid, タブ)
        決めた = self._決めた格子(シートid, タブ)
        if 決めた:
            return 決めた
        return (max(格子の既定[0], len(表)), max(格子の既定[1], max((len(r) for r in 表), default=0)))

    def 格子を決める(self, シートid: str, タブ: str, 行の数: int, 列の数: int) -> None:
        """試験で組む時の手伝い: タブの格子を決める（中身はそのまま）。"""
        self._在るタブ(シートid, タブ)
        self.物[シートid].setdefault("格子", {})[タブ] = (行の数, 列の数)

    def 格子を読む(self, シートid: str) -> dict[str, tuple[int, int]]:
        return {t: self._格子(シートid, t) for t in self._シート(シートid)}

    def 格子を広げる(self, シートid: str, タブ: str, 行の数: int, 列の数: int) -> None:
        行, 列 = self._格子(シートid, タブ)
        if 行 >= 行の数 and 列 >= 列の数:
            return
        self.物[シートid].setdefault("格子", {})[タブ] = (max(行, 行の数), max(列, 列の数))
        self._変えた(シートid)

    def _格子に収まる(self, シートid: str, タブ: str, 行の数: int, 列の数: int) -> None:
        """格子を持つタブだけ照らす（試験が中身を直に置いたタブは大きさを知らない＝止めない）。"""
        if not self._決めた格子(シートid, タブ):
            return
        行, 列 = self._格子(シートid, タブ)
        if 行の数 > 行 or 列の数 > 列:
            raise 格子の外(f"「{タブ}」の格子（{行} 行 × {列} 列）の外へ書く（要る {行の数} 行 × {列の数} 列）")

    def 表へ書く(self, シートid: str, 範囲: str, 値: list[list], *, 読んだ版: str | None = None) -> None:
        タブ, 行, 列 = self._範囲を割る(範囲)
        表 = self._在るタブ(シートid, タブ)
        self._版を照らす(シートid, 読んだ版)
        # 要る大きさは書く所（_範囲を割る の読み）から出す＝「タブ!A:C」や ! の無い範囲も同じ読みで照らす
        self._格子に収まる(シートid, タブ, 行 + max(len(値), 1), 列 + max((len(r) for r in 値), default=1))
        self._変えた(シートid)
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
        # 足す（INSERT_ROWS）は行を差し込む＝行は格子を超えてよい。列は格子の内だけ（実の口が列を足すかに頼らない）
        行の数, 列の数 = self._格子(シートid, タブ)
        要る列 = 列 + max((len(r) for r in 値), default=0)
        if self._決めた格子(シートid, タブ) and 要る列 > 列の数:
            raise 格子の外(f"「{タブ}」の格子（{列の数} 列）の外へ足す（要る {要る列} 列）")
        self._変えた(シートid)
        末 = len(表)
        while 末 and not any(表[末 - 1]):
            末 -= 1
        del 表[末:]
        for r in 値:
            表.append([""] * 列 + ["" if c is None else str(c) for c in r])
        if self.物[シートid].get("格子", {}).get(タブ):
            self.物[シートid]["格子"][タブ] = (max(行の数, len(表)), 列の数)

    def タブを並べる(self, シートid: str) -> list[str]:
        return list(self._シート(シートid))

    def ファイルを読む(self, file_id: str) -> bytes:
        x = self.物.get(file_id)
        if x is None or "中身" not in x:
            raise KeyError(f"file が無い: {file_id}")
        return x["中身"]

    def ファイルを置く(self, 親id: str, 名: str, 中身: bytes, mime: str) -> str:
        return self._作る(親id, 名, mime, 中身=bytes(中身))

    def ファイルを書き換える(self, file_id: str, 中身: bytes, *, 読んだ版: str | None = None) -> None:
        """実の口と同じ: 在る file の中身だけを置き換える（作らない・名・親・mime は触らない）。無い file は KeyError・
        中身を持たない物（フォルダ・シート）は ValueError。読んだ版 が今の版と違えば 版が違う で書かない。"""
        x = self.物.get(file_id)
        if x is None:
            raise KeyError(f"file が無い: {file_id}")
        if "中身" not in x:
            raise ValueError(f"中身を書き換えられない種類の file（{x.get('mimeType')}）")
        self._版を照らす(file_id, 読んだ版)
        x["中身"] = bytes(中身)
        self._変えた(file_id)

    def シートを作る(self, 親id: str, 名: str, タブたち: list[str] | None = None) -> str:
        タブ = list(タブたち or ["シート1"])
        return self._作る(親id, 名, シートのmime, タブ={t: [] for t in タブ}, 格子={t: 格子の既定 for t in タブ})

    def 移す(self, file_id: str, 新しい親id: str) -> None:
        if file_id not in self.物 or 新しい親id not in self.物:
            raise KeyError(f"無い: {file_id} か {新しい親id}")
        self.物[file_id]["親"] = 新しい親id
        self._変えた(file_id)

    def リンク(self, file_id: str) -> str:
        if file_id not in self.物:
            raise KeyError(f"無い: {file_id}")
        return f"https://作り物.invalid/{file_id}"

    def フォルダを作る(self, 親id: str, 名: str) -> str:
        return self._作る(親id, 名, フォルダのmime)

    def 版を読む(self, file_id: str) -> str:
        if file_id not in self.物:
            raise KeyError(f"無い: {file_id}")
        return str(self.物[file_id].get("版", 1))

    def 字を読む(self, file_id: str) -> str:
        return 字にする(self.ファイルを読む(file_id))

    def 行を消す(self, シートid: str, タブ: str, 行番号: int, 読んだ行: list) -> None:
        """実の口と同じ: 今の行が読んだ行と違えば 版が違う で消さない。消した行より下は 1 つ上へ詰まる。"""
        if not isinstance(行番号, int) or 行番号 < 1:
            raise ValueError(f"行番号は 1 起点の数（{行番号!r}）")
        表 = self._在るタブ(シートid, タブ)
        今 = 表[行番号 - 1] if 行番号 <= len(表) else []
        if not 同じ行(今, 読んだ行):
            raise 版が違う(f"「{タブ}」の {行番号} 行目が読んだ時と違う＝消さない。読み直して組み直す")
        if 行番号 <= len(表):
            del 表[行番号 - 1]
        self._変えた(シートid)
