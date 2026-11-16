"""給与ソフトごとの書き口と支給控除一覧（Drive の型.md §6・§7）。

- 受けるのは `関所を通った` だけ（仮の人は来ない・印も書かない）。
- 取り込み: 給与ソフトの形 × 欄の対応（渡す欄）で 1 人 1 行の表を作る。支給月が `-賞与` なら賞与の取り込み。
- 支給控除一覧: 雇用（縦）・業務委託（縦）を 1 本ずつ。業務委託の縦の表はここの 1 本だけ。
  事務所の給与ソフトが委託分も取り込む時だけ、同じ行から取り込みにも委託の人を載せる（手で写す 2 本目は無い）。
- 名は出口が付ける（名と版.py）。中身は表（行の並び）で返す。取り込みは給与ソフトの形の 渡し方 で、CSV なら bytes にでき、
  表なら 03_出力 のスプレッドシートへ書く手順（`書く手順`）を返す（支給控除一覧はいつも表）。出口は Drive を開かない＝殻が当てる。
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal

from .名と版 import 出す名, 名を付ける, 旧版
from .形 import 給与ソフトの形, 字にする, 欄の組たち, 形を組む, _数の字
from .行 import 行, 賞与か, 支給月を確かめる
from .関所 import 関所を通った, 通ったかを確かめる


@dataclass(frozen=True)
class 出す物:
    物: str
    名: 出す名
    表: tuple[tuple[str, ...], ...]
    文字コード: str | None = None
    区切り: str = ","
    空の欄: tuple[str, ...] = ()          # 「NO 欄」の値が芯に無かった所（推して埋めない・空で書いた）
    載せなかった項目: tuple[str, ...] = ()  # 芯の行にあるが対応に渡す欄が無い項目
    渡し方: str = "表"                     # 表＝スプレッドシートに書く（書く手順）・CSV＝file（csvの中身）

    def csvの中身(self) -> bytes:
        if self.渡し方 != "CSV":
            raise ValueError(f"{self.物}: 渡し方が {self.渡し方}（CSV を作らない＝書く手順 で表に書く）")
        if not self.文字コード:
            raise ValueError(f"{self.物}: 文字コードが無い")
        buf = io.StringIO(newline="")
        w = csv.writer(buf, delimiter=self.区切り, lineterminator="\r\n")
        w.writerows(self.表)
        return buf.getvalue().encode(self.文字コード)

    def 書く手順(self, 書き方: str = "RAW") -> list[dict]:
        """渡し方＝表 の物を、その月の `03_出力/` の下のスプレッドシートへ書く手順（殻が順に当てるだけ・判断しない）。
        パス は その月の `03_出力/` からの相対。前の版は同じフォルダの `旧版/` へ移し（名と版）、新しい版を作って値を書く。
        `書き方`＝`RAW`（値を字のまま書く＝NO `0001` の頭の 0・時間の字 `127.30` を数や日付に読ませない。管理表・寄せ と同じ）。
        殻の書く口が RAW を選べない（入力扱いだけ）なら `書き方="USER_ENTERED"`＝値の字の頭に '（`初期設定/型の口.入力扱いの手順`）。"""
        if self.渡し方 != "表":
            raise ValueError(f"{self.物}: 渡し方が {self.渡し方}（表に書かない＝csvの中身 で file を作る）")
        d = self.名.フォルダ
        手順 = [{"する": "file を移す", "前": f"{d}/{n}", "後": f"{d}/{旧版}/{n}"} for n in self.名.旧版へ移す]
        幅 = max((len(r) for r in self.表), default=0)
        手順.append({"する": "スプレッドシートを作る", "フォルダ": d, "名": self.名.名, "タブ": self.物})
        手順.append({"する": "値を書く", "ファイル": f"{d}/{self.名.名}", "タブ": self.物,
                   "範囲": f"A1:{_列の字(幅)}{len(self.表)}", "値": [list(r) for r in self.表], "書き方": "RAW"})
        if 書き方 == "RAW":
            return 手順
        if 書き方 != "USER_ENTERED":
            raise ValueError(f"{self.物}: 書き方「{書き方}」は RAW・USER_ENTERED の外")
        return _型の口().入力扱いの手順(手順)


def _型の口():
    """書き方の 1 か所（初期設定/型の口.py）。"""
    import importlib.util
    import sys
    from pathlib import Path
    名 = "出口_型の口"
    if 名 not in sys.modules:
        spec = importlib.util.spec_from_file_location(名, Path(__file__).resolve().parent.parent / "初期設定" / "型の口.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules[名] = m
        spec.loader.exec_module(m)
    return sys.modules[名]


def _列の字(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s or "A"


def _NOの並び(no: str):
    return (0, int(no), no) if no.isdigit() else (1, 0, no)


def _その月の人(通った: 関所を通った, 会社: str, 支給月: str) -> dict[str, dict[str, 行]]:
    支給月を確かめる(支給月)
    人: dict[str, dict[str, 行]] = {}
    for r in 通ったかを確かめる(通った).行たち:
        if r.支給月 == 支給月 and r.会社 == str(会社):
            人.setdefault(r.NO, {})[r.項目] = r
    return 人


def 取り込み(通った: 関所を通った, 会社: str, 支給月: str, 欄の対応, 形: 給与ソフトの形,
          時間の書き方: str | None = None, 氏名: dict | None = None,
          委託の人=(), 委託も取り込む: bool = False,
          今ある名=(), 旧版にある名=()) -> 出す物:
    """給与ソフトへ渡す取り込みの表。1 人 1 行・欄は 対応の渡す欄 の並び（1 つの欄に幾つかの項目を当てた欄は、その人に在る項目を足す）。

    氏名: 殻が渡す NO→氏名（形に氏名の欄がある時だけ使う。repo には置かない）。
    委託の人: 業務委託の人の NO（マスタの人.区分から殻が渡す）。委託も取り込む が False なら載せない。
    """
    形 = 形を組む(形)  # 殻が渡した形（dict でもよい）。名・鍵の欄・文字コードが無ければ止まる
    対応 = [g for g in 欄の組たち(欄の対応) if g.渡す]
    人 = _その月の人(通った, 会社, 支給月)
    委託 = {str(x) for x in 委託の人}
    頭 = [形.鍵の欄]
    if 形.氏名の欄:
        頭.append(形.氏名の欄)
    頭 += [g.欄 for g in 対応] + list(形.後ろの欄)
    表 = [tuple(頭)]
    空 = []
    渡す項目 = {k for g in 対応 for k in g.項目たち}
    載せない = []
    for no in sorted(人, key=_NOの並び):
        if no in 委託 and not 委託も取り込む:
            continue
        vals = 人[no]
        row = [no]
        if 形.氏名の欄:
            row.append(str((氏名 or {}).get(no, "")))
        for g in 対応:
            ある = [vals[k].値 for k in g.項目たち if k in vals]
            if not ある:   # 足す欄はその人に在る項目だけを足す（時給の人は時給・月給の人は基本給）。どれも無ければ空
                row.append("")
                空.append(f"{no} {g.欄}")
            else:
                row.append(字にする(sum(ある, Decimal(0)), g.形, 時間の書き方))
        row += [""] * len(形.後ろの欄)
        表.append(tuple(row))
        for k in vals:
            if k not in 渡す項目 and k not in 載せない:
                載せない.append(k)
    物 = "賞与の取り込み" if 賞与か(支給月) else "取り込み"
    return 出す物(物=物, 名=名を付ける(物, 会社, 支給月, 今ある名, 旧版にある名), 表=tuple(表),
               文字コード=形.文字コード, 区切り=形.区切り, 空の欄=tuple(空), 載せなかった項目=tuple(載せない),
               渡し方=形.渡し方)


def 支給控除一覧(通った: 関所を通った, 会社: str, 支給月: str, 項目の並び=(), 項目の形: dict | None = None,
            時間の書き方: str | None = None, 氏名: dict | None = None, 委託の人=(),
            今ある名: dict | None = None, 旧版にある名: dict | None = None) -> list[出す物]:
    """雇用（縦）と業務委託（縦）。A 列が項目・列が人・最後が合計。委託の人が居なければ業務委託は出さない。

    項目の並び: マスタの支給控除の項目の並び。並びに無い項目は後ろに出た順で足す（黙って落とさない）。
    項目の形: 項目→形（円・日・分・回）。分は 時間の書き方 で書く。無い項目は数のまま。
    今ある名・旧版にある名: 物（支給控除一覧_雇用・支給控除一覧_業務委託）→ 名の並び。
    """
    人 = _その月の人(通った, 会社, 支給月)
    委託 = {str(x) for x in 委託の人}
    out = []
    for 物, 誰 in (("支給控除一覧_雇用", [n for n in 人 if n not in 委託]),
                  ("支給控除一覧_業務委託", [n for n in 人 if n in 委託])):
        if 物.endswith("業務委託") and not 誰:
            continue
        誰 = sorted(誰, key=_NOの並び)
        並び = list(dict.fromkeys(項目の並び))
        for no in 誰:
            for k in 人[no]:
                if k not in 並び:
                    並び.append(k)
        表 = [tuple(["項目"] + 誰 + ["合計"])]
        if 氏名:
            表.append(tuple(["氏名"] + [str(氏名.get(no, "")) for no in 誰] + [""]))
        for k in 並び:
            形 = (項目の形 or {}).get(k)
            vals = [人[no][k].値 if k in 人[no] else None for no in 誰]
            if all(v is None for v in vals):
                continue
            書く = (lambda v: 字にする(v, 形, 時間の書き方)) if 形 else _数の字
            計 = sum((v for v in vals if v is not None), Decimal(0))
            表.append(tuple([k] + ["" if v is None else 書く(v) for v in vals] + [書く(計)]))
        out.append(出す物(物=物, 名=名を付ける(物, 会社, 支給月, (今ある名 or {}).get(物, ()),
                                         (旧版にある名 or {}).get(物, ())), 表=tuple(表)))
    return out
