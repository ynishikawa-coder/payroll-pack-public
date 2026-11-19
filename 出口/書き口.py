"""給与ソフトごとの書き口と支給控除一覧（Drive の型.md §6・§7）。

- 受けるのは `関所を通った` だけ（仮の人は来ない・印も書かない）。
- 取り込み: 給与ソフトの形 × 欄の対応（渡す欄）で 1 人 1 行の表を作る。支給月が `-賞与` なら賞与の取り込み。
- 芯の行のうち残高（`出さない項目`＝社保の立て替えの残り）は取り込みにも支給控除一覧にも載せない（月次が台帳へ回す）。
- 支給控除一覧: 雇用（縦）・業務委託（縦）を 1 本ずつ。業務委託の縦の表はここの 1 本だけ。
  事務所の給与ソフトが委託分も取り込む時だけ、同じ行から取り込みにも委託の人を載せる（手で写す 2 本目は無い）。
- 名は出口が付ける（名と版.py）。中身は表（行の並び）で返す。取り込みは給与ソフトの形の 渡し方 で、CSV なら bytes にでき、
  表なら 2_出す物 のスプレッドシートへ書く手順（`書く手順`）を返す（支給控除一覧はいつも表）。出口は Drive を開かない＝殻が当てる。
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal

from .名と版 import 出す名, 名を付ける, 履歴の置き場
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
    渡さなかった人: tuple[str, ...] = ()    # 取り込みに載せなかった人（委託・給与ソフトへ入れない人）＝突き合わせの 渡さなかった人 へそのまま渡す
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
        """渡し方＝表 の物を、その月の `2_出す物/` の下のスプレッドシートへ書く手順（殻が順に当てるだけ・判断しない）。
        パス は その月の置き場（`3_月ごと/<月>/`）からの相対。前の版は会社の根の `9_履歴/` へ移し（`file を移す` の 後 だけは
        会社の根からの名＝`後の根`: 会社の根）、新しい版を `2_出す物/` に作って値を書く（名と版）。
        `書き方`＝`RAW`（値を字のまま書く＝NO `0001` の頭の 0・時間の字 `127.30` を数や日付に読ませない。管理表・寄せ と同じ）。
        殻の書く口が RAW を選べない（入力扱いだけ）なら `書き方="USER_ENTERED"`＝値の字の頭に '（`初期設定/型の口.入力扱いの手順`）。"""
        if self.渡し方 != "表":
            raise ValueError(f"{self.物}: 渡し方が {self.渡し方}（表に書かない＝csvの中身 で file を作る）")
        d = self.名.フォルダ
        手順 = [{"する": "file を移す", "前": f"{d}/{n}", "後": f"{履歴の置き場}/{n}", "後の根": "会社の根"} for n in self.名.履歴へ移す]
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


def 出さない項目() -> frozenset[str]:
    """芯の行のうち出す物（取り込み・支給控除一覧・突き合わせ）に載せない項目＝残高（芯/計算 の `支給控除.出さない項目` が正本）。
    `社保の立て替えの残り` は支給でも控除でもない立て替えの残高＝月次が台帳（次の月の その月だけの指示）へ回す。"""
    from 芯.計算.支給控除 import 出さない項目 as 名たち
    return frozenset(名たち)


def 出さない項目の欄を止める(欄の対応, 向き: str) -> None:
    """欄の対応で 出さない項目 に欄を当てていたら止める（残高を給与ソフトの欄へ渡さない・受けて照らさない）。"""
    出さない = 出さない項目()
    for g in 欄の組たち(欄の対応):
        if getattr(g, 向き) and (当てた := [k for k in g.項目たち if k in 出さない]):
            raise ValueError(f"欄の対応: 「{'・'.join(当てた)}」は立て替えの残高（支給でも控除でもない）＝給与ソフトの欄「{g.欄}」へ当てない"
                             "（月次が台帳「その月だけの指示」の次の月の行へ回す。返しの額は 社保の立て替えの返し の欄へ当てる）")


def _その月の人(通った: 関所を通った, 会社: str, 支給月: str) -> dict[str, dict[str, 行]]:
    支給月を確かめる(支給月)
    出さない = 出さない項目()
    人: dict[str, dict[str, 行]] = {}
    for r in 通ったかを確かめる(通った).行たち:
        if r.支給月 == 支給月 and r.会社 == str(会社) and r.項目 not in 出さない:
            人.setdefault(r.NO, {})[r.項目] = r
    return 人


def 取り込み(通った: 関所を通った, 会社: str, 支給月: str, 欄の対応, 形: 給与ソフトの形,
          時間の書き方: str | None = None, 氏名: dict | None = None,
          委託の人=(), 委託も取り込む: bool = False,
          *, 今ある名, 履歴にある名, 渡さない人=()) -> 出す物:
    """給与ソフトへ渡す取り込みの表。1 人 1 行・欄は 対応の渡す欄 の並び（1 つの欄に幾つかの項目を当てた欄は、その人に在る項目を足す）。

    氏名: 殻が渡す NO→氏名（形に氏名の欄がある時だけ使う。repo には置かない）。
    委託の人: 業務委託の人の NO（マスタの人.区分から殻が渡す）。委託も取り込む が False なら載せない。
    渡さない人: その給与ソフトへ入れない人の NO（`形.渡さない人を組む`＝⑥つなぎ の人の行 `渡さない`。`月次.月を回す` は口が組む）。
    載せなかった人（委託・渡さない人）は行も `空の欄` も出さず、`渡さなかった人` に返す（突き合わせへそのまま渡す）。
    """
    形 = 形を組む(形)  # 殻が渡した形（dict でもよい）。名・鍵の欄・文字コードが無ければ止まる
    出さない項目の欄を止める(欄の対応, "渡す")
    対応 = [g for g in 欄の組たち(欄の対応) if g.渡す]
    人 = _その月の人(通った, 会社, 支給月)
    外す = {str(x) for x in 渡さない人}
    if not 委託も取り込む:
        外す |= {str(x) for x in 委託の人}
    頭 = [形.鍵の欄]
    if 形.氏名の欄:
        頭.append(形.氏名の欄)
    頭 += [g.欄 for g in 対応] + list(形.後ろの欄)
    表 = [tuple(頭)]
    空 = []
    渡す項目 = {k for g in 対応 for k in g.項目たち}
    載せない = []
    渡さなかった = []
    for no in sorted(人, key=_NOの並び):
        if no in 外す:
            渡さなかった.append(no)
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
    return 出す物(物=物, 名=名を付ける(物, 会社, 支給月, 今ある名, 履歴にある名), 表=tuple(表),
               文字コード=形.文字コード, 区切り=形.区切り, 空の欄=tuple(空), 載せなかった項目=tuple(載せない),
               渡し方=形.渡し方, 渡さなかった人=tuple(渡さなかった))


def _物の名(名たち, 物: str):
    """置き場の名の並び（そのまま）か、物 → 名の並び の dict（その物の並び・無ければ None＝名と版が止める）。"""
    return 名たち.get(物) if isinstance(名たち, dict) else 名たち


def 支給控除一覧(通った: 関所を通った, 会社: str, 支給月: str, 項目の並び=(), 項目の形: dict | None = None,
            時間の書き方: str | None = None, 氏名: dict | None = None, 委託の人=(),
            *, 今ある名: dict | list, 履歴にある名: dict | list) -> list[出す物]:
    """雇用（縦）と業務委託（縦）。A 列が項目・列が人・最後が合計。委託の人が居なければ業務委託は出さない。

    項目の並び: マスタの支給控除の項目の並び。並びに無い項目は後ろに出た順で足す（黙って落とさない）。
    項目の形: 項目→形（円・日・分・回）。分は 時間の書き方 で書く。無い項目は数のまま。
    今ある名・履歴にある名: 置き場（2_出す物/・9_履歴/）の名の並び（どの物の名も混ざってよい＝名と版が物ごとに選ぶ）か、
    物 → 名の並び。必ず渡す（前の版が無ければ []）。渡さない物は止める＝名と版.名を付ける。
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
        out.append(出す物(物=物, 名=名を付ける(物, 会社, 支給月, _物の名(今ある名, 物), _物の名(履歴にある名, 物)),
                       表=tuple(表)))
    return out
