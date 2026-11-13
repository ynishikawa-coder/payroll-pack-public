"""法の表を引く口（docs/設計/法の表.md §1.2・§2.2）。芯に 1 つだけ。

引く(表の名, 基準の日, 鍵…) → 引いた（値・出所・仮か）。
- 鍵が合い（行の `鍵` の全部が引く側の鍵と同じ）、効く始め ≦ 基準の日 ≦ 効く終わり の行を 1 つ選ぶ。基準の日は行の粒に切って比べる。
- 2 行に当たったら表の誤り＝落ちる（`表の誤り`）。
- 当たる行が無い・`まだ`・`未起こし` は欠け。表の `欠けた時` が
  - `止める` → `欠け` を投げる（その人のその項目は計算しない）
  - `仮で計算し問う` → 基準の日より前で一番新しい `出た` 行の値を **仮** として返す（出所に「仮: …の値」）。前の `出た` 行も無ければ `欠け`。
- 表の置き場は既定で repo の `法の表/`。試験だけ別の置き場を渡せる（`置き場=`）。芯は Drive を開かない。
- 芯/計算 と 芯/集計 の両方がこれを使う（集計は `芯/集計/法の線の橋.py` から）。日は字・`date`・{基準: 日} のどれでも渡せる。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

既定の置き場 = Path(__file__).resolve().parents[2] / "法の表"
基準たち = ("月分", "支払日", "締め日", "年分", "労働した日")


class 欠け(Exception):
    """引けない（国がまだ出していない・起こしていない・前の値で代えない表）。"""

    def __init__(self, 表の名: str, 基準の日: str, 鍵: dict, 訳: str):
        self.表の名, self.基準の日, self.鍵, self.訳 = 表の名, 基準の日, dict(鍵), 訳
        鍵の字 = "・".join(f"{k}={v}" for k, v in 鍵.items())
        super().__init__(f"法の表「{表の名}」{基準の日}{' ' + 鍵の字 if 鍵の字 else ''}: {訳}")


class 表の誤り(Exception):
    """表の行の範囲が重なっている・形が違う（表を直す。引く側で避けない）。"""


@dataclass(frozen=True)
class 引いた:
    値: object
    出所: str
    仮: bool = False


@lru_cache(maxsize=None)
def _読む(置き場: str, 名: str) -> dict:
    p = Path(置き場) / f"{名}.json"
    if not p.exists():
        return None
    表 = json.loads(p.read_text(encoding="utf-8"), parse_float=Decimal)
    if 表.get("基準") not in 基準たち:
        raise 表の誤り(f"法の表「{名}」の基準「{表.get('基準')}」は {'・'.join(基準たち)} の外")
    return 表


def 表(名: str, 置き場=None) -> dict | None:
    """表の中身。表の file が無ければ None（引く は 欠け にする）。"""
    return _読む(str(置き場 or 既定の置き場), 名)


def _字(日) -> str:
    return 日.isoformat() if isinstance(日, date) else str(日)


def 基準を選ぶ(表の基準: str, 日: str | date | dict) -> str:
    """日が {基準: 日} の dict なら表の基準の日を選ぶ。字・date ならそのまま（date は YYYY-MM-DD の字に）。"""
    if isinstance(日, dict):
        if 表の基準 not in 日:
            raise 表の誤り(f"基準「{表の基準}」の日が渡っていない（渡った: {'・'.join(日)}）")
        return _字(日[表の基準])
    return _字(日)


def _当たる(行: dict, 基準の日: str, 鍵: dict) -> bool:
    if any(鍵.get(k) != v for k, v in (行.get("鍵") or {}).items()):
        return False
    始め, 終わり = 行.get("効く始め"), 行.get("効く終わり")
    if 始め is not None and 基準の日[: len(始め)] < 始め:
        return False
    if 終わり is not None and 基準の日[: len(終わり)] > 終わり:
        return False
    return True


def _出典の字(名: str, 行: dict) -> str:
    範囲 = f"{行.get('効く始め') or '…'}〜{行.get('効く終わり') or '…'}"
    return f"法の表/{名} {範囲}"


def 引く(名: str, 日: str | date | dict, *, 置き場=None, **鍵) -> 引いた:
    t = 表(名, 置き場)
    if t is None:
        raise 欠け(名, _字(日) if not isinstance(日, dict) else str(日), 鍵, "表がまだ無い（法の表/ に file が無い）")
    基準の日 = 基準を選ぶ(t["基準"], 日)
    当たり = [r for r in t["行"] if _当たる(r, 基準の日, 鍵)]
    if len(当たり) > 1:
        raise 表の誤り(f"法の表「{名}」{基準の日} {鍵}: 行が {len(当たり)} 個に当たる（範囲が重なっている）")
    if 当たり and 当たり[0].get("状態") == "出た":
        return 引いた(当たり[0]["値"], _出典の字(名, 当たり[0]))
    訳 = "当たる行が無い" if not 当たり else f"行の状態が「{当たり[0].get('状態')}」"
    if t.get("欠けた時") == "仮で計算し問う":
        前 = [r for r in t["行"] if r.get("状態") == "出た" and r.get("効く終わり") is not None
             and r["効く終わり"] < 基準の日[: len(r["効く終わり"])]
             and all(鍵.get(k) == v for k, v in (r.get("鍵") or {}).items())]
        if 前:
            r = max(前, key=lambda r: r["効く終わり"])
            return 引いた(r["値"], f"仮: {_出典の字(名, r)} の値（{基準の日} は{訳}）", 仮=True)
    raise 欠け(名, 基準の日, 鍵, 訳)
