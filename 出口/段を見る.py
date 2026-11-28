#!/usr/bin/env python3
"""段を見る — 1 会社・1 支給月・1 回が今どの段に居て、何が足りず、次に何をするかを 1 つの命令で見る（何も止めない・出さない）。

使い方:
  python3 出口/段を見る.py --会社 <会社> --支給月 <YYYY-MM> --回 <給与|賞与> [--根 <id>]
                        [--鍵の変数名 GOOGLE_DRIVE_SA_JSON] [--書く]

- 出す.py の試し（書かない）を回し、その返り（赤・除いた人・止まり）と 会社の一覧の状態・管理表の回のタブの行を
  管理表/段.py の 段を見る に渡す。段の分けと次にやることの正本は 管理表/段.py（ここで分けない）。
- 勤怠が来ていない月も、決まり・マスタ・つなぎの形は先に読む（初期設定の欠けを勤怠の後に 1 つずつ知らない）。
- 何も書かない。--書く の時だけ 管理表「段」（7_段）へ 1 行を書く（管理表.書く の手順で・同じ会社×支給月×回の行は上書き）。
exit: 0＝見た（段は stdout の JSON）／1＝見たが --書く で書けない（訳は 書けない）／2＝見られない（根が無い・Drive が開けない・会社が引けない）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

根の場所 = Path(__file__).resolve().parents[1]
if str(根の場所) not in sys.path:
    sys.path.insert(0, str(根の場所))

import drive口  # noqa: E402
from 出口 import 出す as 出  # noqa: E402
from 管理表 import 段 as 段の口  # noqa: E402
from 管理表 import 管理表 as 表  # noqa: E402
from 芯 import 支給月の字  # noqa: E402

_来ていない = "この月の勤怠が来ていない"
_出す物が無い = f"置き場: {出.出す置き} が無い＝前の版の番号が分からない"   # 出す.前の版の名 の字


def 事実を集める(口, 会社の置き場: dict, 支給月: str, 回: str, *, 状態: str = "", 回す=None) -> dict:
    """出す の試しの返り＋状態＋管理表の行 → 段を見る の 事実。何も書かない。"""
    置き場, 赤 = 出.出す置き場へ(口, 会社の置き場, 支給月)
    会社 = 会社の置き場.get("会社", "")
    try:
        字 = 出.月次の支給月(支給月)
    except ValueError:
        字 = 支給月   # 形の崩れは 出す の赤が持つ
    事実: dict = {"会社": 会社, "支給月": 字, "回": 出.回の名.get(回, 回), "状態": 状態}
    if 赤:
        # 置き場が全部は決まらない時も、引けた物で決まり・マスタ・つなぎ・9_履歴 を先に読む（読んで回す の赤を足す）。
        # 落とすのは「月のフォルダが無いので 2_出す物 も無い」の 1 つだけ（勤怠が来ていない訳と同じ・二重に見せない）
        if 置き場:
            try:
                _, 赤2 = (回す or 出.読んで回す)(口, 置き場, 会社, 字, 事実["回"])
            except drive口.上限:   # 上限を段の訳（初期設定の欠け等）に化けさせない＝main で止める
                raise
            except Exception as e:  # noqa: BLE001  読めない訳も段に置く
                赤2 = [f"回す: {type(e).__name__}: {e}"]
            月が無い = any(_来ていない in r for r in 赤)
            赤 = [*赤, *(r for r in 赤2 if r not in 赤 and not (月が無い and r == _出す物が無い))]
        事実["赤"] = 出.伏せる(赤)
    else:
        _, out = 出.出す(口, 置き場, 支給月, 回, 書かない=True, 回す=回す)
        事実.update({k: out[k] for k in ("赤", "除いた人", "止まり", "形の崩れ", "出し直しの候補", "知らせ") if out.get(k)})
        事実["支給月"] = out.get("支給月") or 字
    事実["行"] = 管理表の行を読む(口, 会社の置き場, 会社, 支給月, 事実["回"], 事実)
    return 事実


def 管理表の行を読む(口, 会社の置き場: dict, 会社: str, 支給月: str, 回: str, 事実: dict) -> dict | None:
    """管理表の回のタブ（月の状況・賞与の状況）のその会社×支給月の行。読めない時は赤に足し None。"""
    if 回 not in ("月", "賞与") or not 会社の置き場.get(出._管理表の鍵()):
        return None
    名 = 表.回のタブ(回)
    try:
        行たち = 表.行の辞書(名, 出._管理表を読む(口, 会社の置き場, 名))
    except drive口.上限:   # 上限を段の訳（初期設定の欠け等）に化けさせない＝main で止める
        raise
    except Exception as e:  # noqa: BLE001
        事実["赤"] = [*(事実.get("赤") or ()), 出.伏せる(f"管理表: 「{名}」が読めない（{type(e).__name__}: {e}）")]
        return None
    年月 = (int(支給月[:4]), int(支給月[5:7])) if len(支給月) >= 7 and 支給月[:4].isdigit() and 支給月[5:7].isdigit() else None
    return next((r for r in 行たち if r.get("会社") == 会社 and 支給月の字.鍵の年月(r.get("支給月")) == 年月), None)


def 書く(口, 会社の置き場: dict, 見た: dict, 今日: str) -> list[dict]:
    """管理表「段」へ 1 行（管理表.書く の手順を drive口 で当てる）。返り: 当てた手順。"""
    名 = "段"
    本 = 会社の置き場[出._管理表の鍵()]
    今 = 出._管理表を読む(口, 会社の置き場, 名)
    行 = 段の口.管理表の行(見た, 今日)
    手順 = 表.書く({"タブ": 名, "今の値": 今, "会社の一覧": {見た["会社"]: 会社の置き場.get("組", "")},
                 "受け持つ組": 会社の置き場.get("組", ""), "行たち": [行], "今日": 今日})
    for s in 手順:
        if s["する"] == "行を足す":
            口.表へ足す(本, drive口.範囲(s["タブ"], "A1"), [s["値"]])
        else:
            口.表へ書く(本, drive口.範囲(s["タブ"], s["セル"]), [[s["値"]]])
    return 手順


def 状態を読む(口, 根: str, 顧客ID: str) -> str:
    from drive口 import 置き場 as 置
    from 初期設定 import 型の口
    _, _, 一覧 = 置._登録を読む(口, 根)
    鍵 = 型の口.顧客IDの列()
    return next((str(r.get("状態") or "") for r in 一覧 if r.get(鍵) == 顧客ID), "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="1 会社・1 支給月・1 回の段を見る")
    ap.add_argument("--会社", required=True)
    ap.add_argument("--支給月", required=True)
    ap.add_argument("--回", required=True)
    ap.add_argument("--根")
    ap.add_argument("--鍵の変数名", default=drive口.鍵の変数名の既定)
    ap.add_argument("--書く", action="store_true")
    a = ap.parse_args(argv)
    根 = a.根 or os.environ.get(drive口.根の変数名の既定)
    if not 根:
        print(json.dumps({"赤": [f"根: --根 か 環境の変数 {drive口.根の変数名の既定} が要る"]}, ensure_ascii=False))
        return 2
    try:
        口 = drive口.開く(鍵の変数名=a.鍵の変数名)
        from drive口 import 置き場 as 置
        会社の置き場 = 置.会社の置き場(口, 根, a.会社)
        状態 = 状態を読む(口, 根, 会社の置き場["顧客ID"])
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"赤": 出.伏せる([f"Drive: {type(e).__name__}: {e}"])}, ensure_ascii=False))
        return 2
    try:
        見た = 段の口.段を見る(事実を集める(口, 会社の置き場, a.支給月, a.回, 状態=状態))
    except drive口.上限 as e:   # 上限は段でない＝見られない（時を置いて打ち直す）
        print(json.dumps({"赤": [str(e)]}, ensure_ascii=False))
        return 2
    if a.書く:
        try:
            見た["書いた"] = len(書く(口, 会社の置き場, 見た, date.today().isoformat()))
        except Exception as e:  # noqa: BLE001  見た段は返す（書けない訳を添える）
            見た["書けない"] = 出.伏せる(f"{type(e).__name__}: {e}")
    print(json.dumps(見た, ensure_ascii=False, indent=1))
    return 1 if "書けない" in 見た else 0


if __name__ == "__main__":
    sys.exit(main())
