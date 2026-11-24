"""前任の未決の一覧の仕分け（`docs/設計/設問の作り方.md` §10）。前任から受けた「まだ決まっていない」の行を
決定済み／計算に効かない／給与の外／聞く の 4 つに分け、聞く だけを問いにする。分けられない行は `未仕分け` に残し、
残る間は `始める` が会社を先へ進めない（止める）。

判定の元は パックの表と決まりだけ（会社ごとの語を持たない）:
- 項目の辞書（`初期設定/項目.json`）の名・段・既定・聞く・置く所
- 芯の読む名の表（`芯/設定の表.json`）と、マスタの値を芯の入力へ直す読み手（段の解決・入口の文脈・入口/・有給/）が読む名
- 決まった値: 会社の値（書類）・閉じた問い（閉じる段の {項目, 値, 出所}）・答え合わせで一致した項目

行の形: {"番号": "…", "問い": "…", "項目": "分野.名"（無くてよい）, "仕分け": "…", "出所": "…"}。
`項目` の無い行は機械で分けない。人が分けた `仕分け`（4 つのどれか）と `出所`（誰がいつ・何で）が両方ある時だけ受け、ほかは未仕分け。
"""
from __future__ import annotations

import functools
import importlib.util
import json
from pathlib import Path

ここ = Path(__file__).resolve().parent
根 = ここ.parent
_spec = importlib.util.spec_from_file_location("初期設定_型の口_仕分け", ここ / "型の口.py")
口 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(口)

分類たち = ("決定済み", "計算に効かない", "給与の外", "聞く")
# マスタの値を芯の入力へ直す読み手（ここで名が読まれる項目は芯の名の表に無くても計算に効く）
_読み手 = (根 / "芯", 根 / "入口", 根 / "有給", ここ / "段の解決.py", ここ / "入口の文脈.py")


@functools.lru_cache(maxsize=1)
def _芯の名() -> frozenset:
    return frozenset(e["名"] for e in json.loads((根 / "芯" / "設定の表.json").read_text(encoding="utf-8"))["項目"])


@functools.lru_cache(maxsize=1)
def _読み手の字() -> str:
    字 = []
    for p in _読み手:
        for f in ([p] if p.is_file() else sorted(p.rglob("*.py"))):
            字.append(f.read_text(encoding="utf-8"))
    return "\n".join(字)


def 計算に効くか(it: dict) -> bool:
    """芯の名の表に在る・マスタの別の置き場から読む（置く所）・読み手が名を読む のどれかなら効く。"""
    名 = it["項目"]
    return 名 in _芯の名() or bool(it.get("置く所")) or 名 in _読み手の字()


def _分野たち() -> set[str]:
    return {it["項目"].split(".", 1)[0] for it in 口.項目たち()}


def 決まった値(会社の値: dict | None = None, 閉じた=(), 答え合わせの一致=()) -> dict:
    """項目 → {値, 出所}（先に在る方が勝つ: 書類 → 閉じた問い → 答え合わせ）。"""
    out: dict[str, dict] = {}
    for 名, v in (会社の値 or {}).items():
        値, 書類 = (v.get("値"), v.get("書類の名")) if isinstance(v, dict) else (v, "")
        out.setdefault(名, {"値": 値, "出所": f"書類 {書類}" if 書類 else "会社の値"})
    for x in [*閉じた, *答え合わせの一致]:
        if x.get("項目") and x.get("出所"):
            out.setdefault(x["項目"], {"値": x.get("値"), "出所": x["出所"]})
    return out


def 一つを分ける(行: dict, 決まった: dict) -> dict:
    """1 行 → {分類, 訳, 出所, 値}（分類 None＝未仕分け）。"""
    名 = str(行.get("項目") or "").strip()
    if not 名:
        手 = 行.get("仕分け")
        if 手 in 分類たち and str(行.get("出所") or "").strip():
            return {"分類": 手, "訳": "人が仕分けた", "出所": 行["出所"]}
        why = "項目 が無く、人の仕分け（4 つのどれか）と出所も無い" if not 手 else \
            (f"仕分け「{手}」は 4 つのどれでもない" if 手 not in 分類たち else "人の仕分けに 出所 が無い")
        return {"分類": None, "訳": why}
    分野 = 名.split(".", 1)[0]
    try:
        it = 口.項目(名)
    except KeyError:
        if "." in 名 and 分野 not in _分野たち():
            return {"分類": "給与の外", "訳": f"分野 {分野} は項目の辞書の分野に無い（給与の決まりの外）", "出所": "初期設定/項目.json の分野"}
        return {"分類": None, "訳": f"項目 {名} が項目の辞書に無い（辞書に足すか、項目を直す）"}
    if 名 in 決まった:
        d = 決まった[名]
        return {"分類": "決定済み", "訳": "値が決まっている", "出所": d["出所"], "値": d["値"]}
    if it.get("段") == ["仕組み"]:
        return {"分類": "決定済み", "訳": "パックの仕組みで決まる（会社ごとに選ばない）", "出所": "初期設定/項目.json の段 仕組み",
                "値": it.get("既定")}
    if not 計算に効くか(it):
        return {"分類": "計算に効かない", "訳": "芯の名の表に無く、マスタの読み手も読まない", "出所": "芯/設定の表.json"}
    if it.get("既定") is not None and not it.get("聞く"):
        return {"分類": "決定済み", "訳": "項目の既定で計算する（既定が null の項目だけを聞く）",
                "出所": "初期設定/項目.json の既定", "値": it["既定"]}
    return {"分類": "聞く", "訳": "値が無く計算に効く"}


def 仕分ける(未決たち, 会社の値: dict | None = None, 閉じた=(), 答え合わせの一致=()) -> dict:
    """前任の未決の一覧 → {決定済み, 計算に効かない, 給与の外, 聞く, 未仕分け, 止める}。各行は元の行に 分類・訳・出所（と値）を足した物。
    止める＝未仕分けが 1 行でも在る（`始める` は会社を先へ進めない）。"""
    決まった = 決まった値(会社の値, 閉じた, 答え合わせの一致)
    out: dict = {k: [] for k in (*分類たち, "未仕分け")}
    for r in 未決たち or ():
        if not isinstance(r, dict):
            raise TypeError(f"前任の未決の行は dict で渡す: {r!r}")
        d = 一つを分ける(r, 決まった)
        out[d["分類"] or "未仕分け"].append({**r, **{k: v for k, v in d.items() if k != "分類"}, "分類": d["分類"] or "未仕分け"})
    out["止める"] = bool(out["未仕分け"])
    return out
