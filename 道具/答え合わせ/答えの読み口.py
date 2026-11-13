"""答えの読み口（確かめと仮.md §1）。過去の答え（給与ソフトの一覧表・明細）を人×項目の縦の行へ直すだけで、比べない。

- 読み口は **形ごとに 1 つ**: `一覧表を読む`（人が行か列に並ぶ表・向きは問わない）と `明細を読む`（1 人 1 枚）。会社ごとに作らない。
- 欄（見出し）と芯の項目の対応は引数 `つなぎ`（開発の窓が Drive のマスタ「つなぎ」から渡す。形は 出口/ の `欄の対応` と同じ
  `{項目, 欄, 形}`）。repo に会社の欄の名を持たない。読み用の別名・読み替えを持たない。
- 出す行は `出口.行.行`（出所＝読んだ file と タブの名・状態＝確定）。返す物は `出口.読み口.読んだ物`（出口の読み口と同じ形）。
- 人の行（列）があり欄もある空のセルは 0 と読む（給与ソフトは 0 を空で出す）。
- 読めない物（対応に無い見出し・鍵の無い行・数でない値・同じ人×項目の違う値）は推して埋めず、黙って捨てず `要確認` に返す。
- 答えから値を起こさない（ここは読むだけ。差は 照合の段 が問いにして返す）。
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from 出口.形 import 字を分に, 字を数に, 対応にする
from 出口.行 import 確定, 行, 支給月を確かめる
from 出口.読み口 import 読んだ物

from .表 import 表

合計の名 = ("合計", "総合計", "小計", "計")


def _掃く(v) -> str:
    """見出しの字: 前後と中の空白（全角も）を除き、全角の英数を半角にする。"""
    return unicodedata.normalize("NFKC", re.sub(r"[\s　]+", "", str(v or "")))


def _NOの字(v) -> str | None:
    s = _掃く(v)
    return s if re.fullmatch(r"\d{1,10}", s) else None


def _値の字か(v: str) -> bool:
    s = _掃く(v).replace(",", "").replace("¥", "").replace("円", "")
    return bool(re.fullmatch(r"-?\d+(\.\d+)?|-?\d+:\d{2}", s))


class _読み:
    """2 つの読み口が同じに使う物（つなぎ・値の読み・同じ人×項目の重なりの見張り）。"""

    def __init__(self, 会社, 支給月, つなぎ, 時間の書き方, 鍵の見出し, 氏名の見出し, 氏名からNO, 読まない見出し):
        self.会社 = str(会社)
        self.支給月 = 支給月を確かめる(支給月)
        self.欄 = {_掃く(x.欄): x for x in 対応にする(つなぎ)}
        self.時間の書き方 = 時間の書き方
        self.鍵 = {_掃く(x).upper() for x in 鍵の見出し}
        self.氏名 = {_掃く(x) for x in 氏名の見出し}
        self.氏名からNO: dict[str, list[str]] = {}
        for 名, no in (氏名からNO or {}).items():
            self.氏名からNO.setdefault(_掃く(名), []).append(str(no))
        self.読まない = {_掃く(x) for x in 読まない見出し} | {_掃く(x) for x in 合計の名}
        self.行たち: dict[tuple[str, str], 行] = {}
        self.要確認: list[str] = []

    def 鍵か(self, v) -> bool:
        return _掃く(v).upper() in self.鍵

    def 氏名か(self, v) -> bool:
        return bool(self.氏名からNO) and _掃く(v) in self.氏名

    def 知る見出しか(self, v) -> bool:
        s = _掃く(v)
        return s in self.欄 or s in self.読まない or self.鍵か(s) or s in self.氏名

    def 氏名でNO(self, 出所, 名) -> str | None:
        nos = self.氏名からNO.get(_掃く(名), [])
        if len(nos) != 1:
            why = "引けない" if not nos else f"決まらない（同じ氏名が {len(nos)} 人）"
            self.要確認.append(f"{出所}「{名}」: 氏名で NO が{why}（この人の値は読んでいない）")
            return None
        return nos[0]

    def 足す(self, 出所, no, 見出し, 字):
        x = self.欄[_掃く(見出し)]
        s = str(字).strip()
        try:
            if x.形 == "分" and ":" in s:
                v = 字を分に(s.replace(",", ""), "時:分")   # xlsx の時刻のセルは 時:分 の字で来る
            else:
                v = 字を数に(s, x.形, self.時間の書き方)
        except ValueError as e:
            self.要確認.append(f"{出所} {no} {見出し}: {e}（読んでいない）")
            return
        if v is None:   # 人も欄もある空のセル＝給与ソフトが 0 を空で出した
            v = 字を数に("0", "円", None)
        k = (no, x.項目)
        前 = self.行たち.get(k)
        if 前 is not None:
            if 前.値 != v:
                self.要確認.append(f"{出所} {no} {x.項目}: {前.出所} の値 {前.値} と違う値 {v}（前の値のまま）")
            return
        self.行たち[k] = 行(支給月=self.支給月, 会社=self.会社, NO=no, 項目=x.項目, 値=v, 出所=出所, 状態=確定)

    def 返す(self) -> 読んだ物:
        並び = list(self.欄.values())
        順 = {x.項目: i for i, x in enumerate(並び)}
        rows = sorted(self.行たち.values(), key=lambda r: (r.NO, 順[r.項目]))
        return 読んだ物(tuple(rows), tuple(self.要確認))


def 一覧表を読む(表たち: Iterable[表], 会社: str, 支給月: str, つなぎ, 時間の書き方: str | None = None,
              鍵の見出し=("NO",), 氏名の見出し=("氏名",), 氏名からNO: dict | None = None,
              読まない見出し=()) -> 読んだ物:
    """人が行（横）か列（縦）に並ぶ一覧表（支給控除一覧表・勤怠一覧表など）→ 人×項目の行。

    鍵の見出し（既定 `NO`）のセルを探し、その行と列のどちらに つなぎ の欄が多いかで向きを決める。
    鍵の見出しの無い表は、氏名からNO（開発の窓が Drive の社員マスタから渡す {氏名: NO}）があれば氏名の見出しで人を引く。
    合計の行・列（`合計の名`）と 読まない見出し は読まない。1 支給月 1 会社の file を渡す（タブは全部読む）。
    """
    読 = _読み(会社, 支給月, つなぎ, 時間の書き方, 鍵の見出し, 氏名の見出し, 氏名からNO, 読まない見出し)
    for t in 表たち:
        _一覧表(読, t)
    return 読.返す()


def _一覧表(読: _読み, t: 表):
    升 = [list(r) for r in t.升]
    if not any(any(c for c in r) for r in 升):
        return
    w = max(len(r) for r in 升)
    升 = [r + [""] * (w - len(r)) for r in 升]
    場所 = None
    for i, r in enumerate(升):
        for j, c in enumerate(r):
            if 読.鍵か(c) or 読.氏名か(c):
                場所 = (i, j, 読.鍵か(c))
                break
        if 場所:
            break
    if 場所 is None:
        読.要確認.append(f"{t.名}: 鍵の見出し（{'・'.join(sorted(読.鍵))}）が無い（この表は読んでいない）")
        return
    i, j, 鍵で引く = 場所
    横の数 = sum(1 for c in 升[i] if _掃く(c) in 読.欄)
    縦の数 = sum(1 for r in 升 if _掃く(r[j]) in 読.欄)
    if 横の数 == 0 and 縦の数 == 0:
        読.要確認.append(f"{t.名}: つなぎ の欄が 1 つも無い（この表は読んでいない）")
        return
    if 縦の数 > 横の数:   # 人が列・欄が行 → 人が行へ直す
        升 = [list(c) for c in zip(*升)]
        i, j = j, i
    頭 = 升[i]
    読む列 = []
    for c, h in enumerate(頭):
        if c == j:
            continue
        s = _掃く(h)
        値のある列 = any(r[c] for r in 升[i + 1:])
        if not s:
            if 値のある列:
                読.要確認.append(f"{t.名}: 見出しの無い列（行）に値がある（読んでいない）")
            continue
        if s in 読.欄:
            読む列.append(c)
        elif not 読.知る見出しか(s) and 値のある列:
            読.要確認.append(f"{t.名}: つなぎ に無い見出し「{h}」（読んでいない）")
    for r in 升[i + 1:]:
        鍵 = r[j]
        if not _掃く(鍵):
            if any(r[c] for c in 読む列):
                読.要確認.append(f"{t.名}: 鍵の無い行（列）に値がある（読んでいない）")
            continue
        if _掃く(鍵) in 読.読まない:
            continue
        if 鍵で引く:
            no = _NOの字(鍵)
            if no is None:
                読.要確認.append(f"{t.名}: NO でない鍵「{鍵}」（この行は読んでいない）")
                continue
        else:
            no = 読.氏名でNO(t.名, 鍵)
            if no is None:
                continue
        for c in 読む列:
            読.足す(t.名, no, 頭[c], r[c])


def 明細を読む(表たち: Iterable[表], 会社: str, 支給月: str, つなぎ, 時間の書き方: str | None = None,
            鍵の見出し=("NO",), 氏名の見出し=("氏名",), 氏名からNO: dict | None = None,
            読まない見出し=()) -> 読んだ物:
    """1 人 1 枚（タブ）の明細 → 人×項目の行。

    見出し（鍵・氏名・つなぎ の欄）の値は、すぐ右のセルが値ならそれ、でなければすぐ下のセルが値ならそれ。
    右も下も空（か別の見出し）なら 0。人は鍵の見出しの値（NO）で、無ければ氏名からNO で引く。1 枚に人が 2 人以上・引けない枚は読まない。
    値に使わなかった字のセルで、つなぎ にも 読まない見出し にも無い物は要確認に出す（表題・会社の名は 読まない見出し で渡す）。
    """
    読 = _読み(会社, 支給月, つなぎ, 時間の書き方, 鍵の見出し, 氏名の見出し, 氏名からNO, 読まない見出し)
    for t in 表たち:
        _明細(読, t)
    return 読.返す()


def _明細(読: _読み, t: 表):
    升 = [list(r) for r in t.升]
    if not any(any(c for c in r) for r in 升):
        return
    w = max(len(r) for r in 升)
    升 = [r + [""] * (w - len(r)) for r in 升]

    def 升の字(i, j):
        return 升[i][j] if 0 <= i < len(升) and 0 <= j < w else ""

    使った: set[tuple[int, int]] = set()

    def 値の場所(i, j, 字も=False):
        for (a, b) in ((i, j + 1), (i + 1, j)):
            s = 升の字(a, b)
            if s and (字も and not 読.知る見出しか(s) or _値の字か(s)):
                return (a, b)
        return None

    人たち, 見出したち = [], []
    for i, r in enumerate(升):
        for j, c in enumerate(r):
            if not c:
                continue
            if 読.鍵か(c):
                p = 値の場所(i, j)
                if p:
                    人たち.append(_NOの字(升の字(*p)) or "")
                    使った |= {(i, j), p}
            elif _掃く(c) in 読.氏名:
                p = 値の場所(i, j, 字も=True)
                使った.add((i, j))
                if p:
                    使った.add(p)
                    if not any(読.鍵か(x) for row in 升 for x in row):
                        人たち.append(("氏名", 升の字(*p)))
            elif _掃く(c) in 読.欄:
                見出したち.append((i, j))
    if len(人たち) != 1:
        why = "人が引けない（鍵の見出しも氏名も無い）" if not 人たち else f"1 枚に人が {len(人たち)} 人"
        読.要確認.append(f"{t.名}: {why}（この枚は読んでいない）")
        return
    人 = 人たち[0]
    if isinstance(人, tuple):
        no = 読.氏名でNO(t.名, 人[1])
    else:
        no = 人 or None
        if no is None:
            読.要確認.append(f"{t.名}: NO の値が NO の形でない（この枚は読んでいない）")
    if no is None:
        return
    for (i, j) in 見出したち:
        使った.add((i, j))
        p = 値の場所(i, j)
        if p:
            使った.add(p)
            読.足す(t.名, no, 升[i][j], 升の字(*p))
        elif all(not s or 読.知る見出しか(s) for s in (升の字(i, j + 1), 升の字(i + 1, j))):
            読.足す(t.名, no, 升[i][j], "")
        else:
            読.要確認.append(f"{t.名} {no} {升[i][j]}: 右にも下にも値が無い（読んでいない）")
    for i, r in enumerate(升):
        for j, c in enumerate(r):
            if c and (i, j) not in 使った and not _値の字か(c) and _掃く(c) not in 読.読まない:
                読.要確認.append(f"{t.名}: つなぎ に無い見出し「{c}」（読んでいない）")
