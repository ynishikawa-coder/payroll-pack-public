"""移しを当てる — 道具/移しの点検.py の案（書く物・消す物）を、そのまま事務所の Drive へ当てる 1 命令。

既定は乾いた回し: 何を広げる・書く・足す・作る・消すかを会社（顧客ID）ごとに並べるだけで、Drive へは書かない。
広げる＝書く・足すセルがタブの格子（行の数 × 列の数）の外に在る時、そのタブの格子を要る大きさまで広げる（drive口 格子を広げる。
実の Sheets は格子の外のセルへの書きを 400 で拒む）。広げる物の無い案の印は前と同じ。
`--当てる` の時だけ書く。書く字を組むのは点検の 1 か所（管理表.py 月の段 の手順も点検が渡す）で、ここは組み直さない。

当てる順と守り:
  1. 点検を回し直し、案の `_当て`（点検の時に読んだ行の生の字）を受ける。
  2. 書く前に、当てる行を全部読み直して点検の時の行と照らす（書く物・消す物は行の全部の列・月の状況に足す物はタブの全部の行・
     作るフォルダは同じ名がまだ無い事）。1 つでも違えば何も書かずに止める（ほかの人・ほかの窓が書いた物を上書きしない）。
     同じ行を書いて消す案・同じセルへ違う字を書く案も、当てずに止める。
  3. 格子を広げる → セルを書く → 月の状況へ行を足す → 月のフォルダを作る（drive口/置き場.py 月の置き場 作る=True）→ 行を消す。
     消すのはシートのタブごとに下の行から（上の行を先に消すと下の行の番号がずれる）。消す口（drive口 行を消す）も、
     今の行が読んだ行と全部の列で同じ時だけ消す。
  4. 当てた回ごとに 1 つ、事務所の根/9_履歴/ へ記録（いつ・顧客ID・書いた数・消した数）を置く（名の形は Drive の型.md §2 口の記録）。
     途中で止まった時も、それまでに当てた数と止まった訳（赤の型の名と状態の番号だけ・id や URL を出さない）を記録に置いてから止まる。
  問う物（値が決まらず人に聞く物）と、点検が道だけを示す物（締めの記録＝③ 勤怠の締め を当てる）は並べるだけで当てない。

Drive を呼ぶたびに、その呼び出しが Google へ打つ頼みの数 × 間 秒あける（既定 1.1 秒＝1 分 60 頼みの上限の内。点検の読みも含む）。
出す字に Drive の id・鍵・読んだ行の中身を入れない（タブ・行・列・支給月・項目の名・数だけ）。

使い方: python 道具/移しを当てる.py [--根 <事務所の根の id>] [--会社 <顧客ID>] [--当てる] [--印 <乾いた回しの印>] [--間 1.1]
  根は --根 か環境の変数 PAYROLL_OFFICE_ROOT_ID。鍵は drive口.開く が環境から読む（値は出さない）。
  --印 を渡すと、乾いた回しで見た案と今の案が同じ時だけ当てる（違えば止める）。
  終わりの値: 0＝済んだ（当てる物が無い時も）・2＝読めない・3＝照らして違う／当てる途中で止まった。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

根 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(根))

import drive口  # noqa: E402
from drive口 import 置き場 as 置き場の口  # noqa: E402
from 初期設定 import 型の口  # noqa: E402

_spec = importlib.util.spec_from_file_location("移しの点検_当てる", 根 / "道具" / "移しの点検.py")
点 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(点)

記録の頭 = "移しを当てた記録_"   # 名の形の正本は docs/設計/Drive の型.md §2「口の記録」の行
日本 = ZoneInfo("Asia/Tokyo")


class 止める(RuntimeError):
    """照らして違う・案が食い違う・当てる途中で落ちた。訳に id と行の中身を入れない。"""


# 口の 1 呼び出しが Google へ打つ頼みの数（drive口/_google.py の正本と同じ・試験が照らす）。無い物は 1。
# 読んだ版 を渡すと版の読みが 1 つ増えるが、この道具は 読んだ版 を渡さない。
頼みの数 = {"行を消す": 3, "ファイルを読む": 3, "字を読む": 3, "シートを作る": 3, "ファイルを書き換える": 2, "移す": 2,
         "格子を広げる": 2}


class 間の口:
    """Drive口 の呼び出しの前に、その呼び出しが打つ頼みの数 × 間 秒あける（行を消す は 3 頼み＝3 間）。
    既定の 1.1 秒なら 1 分に打つ頼みは 60 回の上限の内。`回数` は打った頼みの数。"""

    def __init__(self, 口, 間: float = 1.1, 眠る=time.sleep) -> None:
        self._口, self._間, self._眠る, self.回数 = 口, 間, 眠る, 0

    def __getattr__(self, 名):
        f = getattr(self._口, 名)
        if not callable(f):
            return f
        重さ = 頼みの数.get(名, 1)

        def 打つ(*a, **k):
            if self.回数 and self._間:
                self._眠る(self._間 * 重さ)
            self.回数 += 重さ
            return f(*a, **k)
        return 打つ


def _表(x: dict) -> dict:
    """案の出す字（`_` で始まる鍵を落とす＝id・読んだ行を出さない）。"""
    return {k: v for k, v in x.items() if not k.startswith("_")}


def 計画を組む(口, 結果: dict, 会社: str | None = None) -> dict:
    """点検の結果（当てる用）→ {顧客ID: {広げる, 書く, 足す, 作る, 消す, 当てない, 問う物}}。会社 を渡せばその顧客ID だけ。
    広げる＝書く・足す先のセルがタブの格子（行の数 × 列の数）の外になるタブ。口 で今の格子を読む（シートごとに 1 度）。
    格子の外へは Google が 400（exceeds grid limits）で書かない＝当てる時に先に広げてから書く。"""
    if 会社 is not None and 会社 not in 結果:
        raise 止める(f"顧客ID「{会社}」が点検の結果に無い（事務所の設定「会社の一覧」の顧客ID で渡す）")
    out = {}
    for c, v in 結果.items():
        if 会社 is not None and c != 会社:
            continue
        p = {"書く": [], "足す": [], "作る": [], "消す": [], "当てない": [], "問う物": list(v["問う物"])}
        for x in v["書く物"]:
            t = x.get("_当て")
            if t is None:
                p["当てない"].append(x)
            elif "セル" in t:
                p["書く"].append(x)
            elif "足す行" in t:
                p["足す"].append(x)
            elif "親" in t:
                p["作る"].append(x)
            else:
                p["当てない"].append(x)
        for x in v["消す物"]:
            (p["消す"] if x.get("_当て") is not None else p["当てない"]).append(x)
        out[c] = p
    _広げる物を足す(口, out)
    return out


def _広げる物を足す(口, 計画: dict) -> None:
    """書く・足す先に要る格子を (シート, タブ) ごとに集め、今の格子より大きいタブを 広げる に置く
    （同じタブを 2 社が書く時は先の会社に 1 つ）。"""
    要る: dict[tuple, list] = {}
    for c, p in 計画.items():
        p["広げる"] = []
        for x in p["書く"]:
            t = x["_当て"]
            行, 列 = drive口.要る格子(t["セル"], [[x["値"]]])
            k = (t["シート"], t["タブ"])
            v = 要る.setdefault(k, [c, 0, 0])
            v[1], v[2] = max(v[1], 行), max(v[2], 列)
        for x in p["足す"]:
            t = x["_当て"]
            k = (t["シート"], t["タブ"])
            v = 要る.setdefault(k, [c, 0, 0])   # 足す（行を差し込む）は行が格子を超えてよい＝列だけ要る
            v[2] = max(v[2], len(t["足す行"]))
    格子: dict[str, dict] = {}
    for (シート, タブ), (c, 行, 列) in 要る.items():
        if シート not in 格子:
            格子[シート] = 口.格子を読む(シート)
        今行, 今列 = 格子[シート].get(タブ, (0, 0))
        if 行 > 今行 or 列 > 今列:
            広げた行, 広げた列 = max(今行, 行), max(今列, 列)
            計画[c]["広げる"].append({
                "タブ": タブ, "今": f"{今行} 行 × {今列} 列", "広げて": f"{広げた行} 行 × {広げた列} 列",
                "_当て": {"シート": シート, "タブ": タブ, "行の数": 広げた行, "列の数": 広げた列,
                          "列を広げる": 広げた列 > 今列, "行を広げる": 広げた行 > 今行}})


def 当てる数(計画: dict) -> int:
    return sum(len(p[k]) for p in 計画.values() for k in ("広げる", "書く", "足す", "作る", "消す"))


def 印(計画: dict) -> str:
    """案の全部（読んだ行の字を含む）の印。乾いた回しで見た案と当てる案が同じかを照らす。
    広げる は在る時だけ入れる（広げる物の無い案の印は、広げる を足す前と同じ）。"""
    字 = json.dumps({c: {k: p[k] for k in ("広げる", "書く", "足す", "作る", "消す") if k != "広げる" or p.get(k)}
                    for c, p in 計画.items()},
                   ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(字.encode("utf-8")).hexdigest()[:16]


def 見せる(計画: dict) -> dict:
    """乾いた回しで出す字（id・読んだ行の中身を落とす）。"""
    return {c: {"数": {"列を広げる": sum(1 for x in p["広げる"] if x["_当て"]["列を広げる"]),
                       "行を広げる": sum(1 for x in p["広げる"] if x["_当て"]["行を広げる"]),
                       **{k: len(p[k]) for k in ("書く", "足す", "作る", "消す", "当てない", "問う物")}},
                **{k: [_表(x) for x in p[k]] for k in ("広げる", "書く", "足す", "作る", "消す", "当てない", "問う物")}}
            for c, p in 計画.items()}


def _末を落とす(格子) -> list[list]:
    g = [list(r) for r in (格子 or [])]
    while g and not any(str(c if c is not None else "").strip() for c in g[-1]):
        g.pop()
    return g


def _食い違い(計画: dict) -> list[str]:
    """同じ行を書いて消す・同じセルへ違う字を書く・同じ行を 2 度消す案。"""
    out = []
    セル, 消す = {}, set()
    for c, p in 計画.items():
        for x in p["消す"]:
            t = x["_当て"]
            k = (t["シート"], t["タブ"], t["行"])
            if k in 消す:
                out.append(f"{c}: 「{t['タブ']}」の {t['行']} 行目を 2 度消す案")
            消す.add(k)
    for c, p in 計画.items():
        for x in p["書く"]:
            t = x["_当て"]
            if (t["シート"], t["タブ"], t["行"]) in 消す:
                out.append(f"{c}: 「{t['タブ']}」の {t['行']} 行目を書いて消す案")
            k = (t["シート"], t["タブ"], t["セル"])
            if k in セル and セル[k] != x["値"]:
                out.append(f"{c}: 「{t['タブ']}」の {t['セル']} へ違う字を 2 つ書く案")
            セル[k] = x["値"]
    return out


def 照らす(口, 計画: dict) -> list[str]:
    """当てる前に今の Drive を読み直し、点検の時と違う所を返す（空なら当ててよい）。タブは 1 度ずつ読む。"""
    違い = _食い違い(計画)
    読んだ: dict[tuple, list] = {}

    def 今の表(シート, タブ):
        k = (シート, タブ)
        if k not in 読んだ:
            読んだ[k] = 口.表を読む(シート, drive口.範囲(タブ))
        return 読んだ[k]

    for c, p in 計画.items():
        for 何 in ("書く", "消す"):
            for x in p[何]:
                t = x["_当て"]
                g = 今の表(t["シート"], t["タブ"])
                今 = g[t["行"] - 1] if t["行"] <= len(g) else []
                if not drive口.同じ行(今, t["読んだ行"]):
                    違い.append(f"{c}: 「{t['タブ']}」の {t['行']} 行目が点検の時と違う")
        for x in p["足す"]:
            t = x["_当て"]
            今, 前 = _末を落とす(今の表(t["シート"], t["タブ"])), _末を落とす(t["読んだ表"])
            if len(今) != len(前) or not all(drive口.同じ行(a, b) for a, b in zip(今, 前)):
                違い.append(f"{c}: 「{t['タブ']}」の行が点検の時と違う（行を足さない）")
        for x in p["作る"]:
            t = x["_当て"]
            try:
                在る = 口.名で引く(t["親"], t["名"])
            except LookupError:
                在る = True
            if 在る:
                違い.append(f"{c}: 月のフォルダ「{t['名']}」が点検の後に在る")
    return list(dict.fromkeys(違い))


def _記録を置く(口, 根id: str, 記録: dict, 今: datetime) -> str:
    名 = 型の口.名("履歴")
    在る = 口.名で引く(根id, 名)
    親 = 在る["id"] if 在る else 口.フォルダを作る(根id, 名)
    file名 = f"{記録の頭}{今:%Y-%m-%d_%H%M%S}.json"
    口.ファイルを置く(親, file名, json.dumps(記録, ensure_ascii=False, indent=1).encode("utf-8"), "application/json")
    return file名


def 当てる(口, 根id: str, 計画: dict, *, 今: datetime | None = None) -> dict:
    """照らして同じなら当てる → 記録。違えば何も書かずに 止める。途中で落ちたら、そこまでを記録に置いて 止める。"""
    今 = 今 or datetime.now(日本)
    違い = 照らす(口, 計画)
    if 違い:
        raise 止める("点検の後に変わった所が在る＝何も当てずに止める（点検から回し直す）: " + "／".join(違い))
    数 = {c: {"広げたタブ": 0, "書いた": 0, "足した行": 0, "作ったフォルダ": 0, "消した": 0} for c, p in 計画.items()
          if any(p[k] for k in ("広げる", "書く", "足す", "作る", "消す"))}
    if not 数:
        return {"記録": None, "数": {}}
    訳 = None
    try:
        for c, p in 計画.items():   # 格子の外へは書けない＝書く・足す より先に広げる（大きさを決める頼み＝打ち直してよい）
            for x in p["広げる"]:
                t = x["_当て"]
                口.格子を広げる(t["シート"], t["タブ"], t["行の数"], t["列の数"])
                数[c]["広げたタブ"] += 1
        for c, p in 計画.items():
            for x in p["書く"]:
                t = x["_当て"]
                口.表へ書く(t["シート"], drive口.範囲(t["タブ"], t["セル"]), [[x["値"]]])
                数[c]["書いた"] += 1
        for c, p in 計画.items():
            for x in p["足す"]:
                t = x["_当て"]
                口.表へ足す(t["シート"], drive口.範囲(t["タブ"]), [list(t["足す行"])])
                数[c]["足した行"] += 1
        for c, p in 計画.items():
            for x in p["作る"]:
                t = x["_当て"]
                置き場の口.月の置き場(口, t["親"], t["名"], 作る=True)
                数[c]["作ったフォルダ"] += 1
        消す = sorted(((c, x["_当て"]) for c, p in 計画.items() for x in p["消す"]),
                    key=lambda ct: (ct[1]["シート"], ct[1]["タブ"], -ct[1]["行"]))
        for c, t in 消す:   # タブごとに下の行から（上を先に消すと下の行の番号がずれる）
            口.行を消す(t["シート"], t["タブ"], t["行"], list(t["読んだ行"]))
            数[c]["消した"] += 1
    except Exception as e:  # noqa: BLE001 — 当てた所までを記録に残してから止める（訳は型の名と状態の番号・id と URL を出さない）
        訳 = _訳(e)
    記録 = {"いつ": 今.isoformat(timespec="seconds"), "道具": "道具/移しを当てる.py", "印": 印(計画), "会社": 数}
    if 訳:
        記録["止まった"] = 訳
    名 = _記録を置く(口, 根id, 記録, 今)
    if 訳:
        raise 止める(f"当てる途中で止まった（{訳}）。当てた所までを 9_履歴/{名} に置いた。点検から回し直す")
    return {"記録": 名, "数": 数}


def _訳(e: Exception) -> str:
    """出す訳。この道具と drive口 が組む訳（id を入れない決まり）はそのまま、ほかの物（Google の HttpError は URL に
    シート・ファイルの id を持つ）は型の名と状態の番号だけにする。"""
    if isinstance(e, (止める, drive口.版が違う, drive口.上限, drive口.開けない, 置き場の口.引けない)):
        return f"{type(e).__name__}: {e}"
    状態 = getattr(getattr(e, "resp", None), "status", None)
    return type(e).__name__ + (f"（状態 {状態}）" if 状態 else "")


def main(argv=None, *, 口=None, 眠る=time.sleep, 今: datetime | None = None) -> int:
    p = argparse.ArgumentParser(description="移しの点検の案を Drive へ当てる（既定は乾いた回し）")
    p.add_argument("--根", default=None, help="事務所の根の id（無ければ環境の変数 PAYROLL_OFFICE_ROOT_ID）")
    p.add_argument("--会社", default=None, help="この顧客ID だけ当てる")
    p.add_argument("--当てる", action="store_true", help="書く（無ければ並べるだけ）")
    p.add_argument("--印", default=None, help="乾いた回しで出た印（当てる時に案が同じかを照らす）")
    p.add_argument("--間", type=float, default=1.1, help="Google へ打つ頼み 1 つあたりにあける秒（既定 1.1＝1 分 60 頼みの上限の内）")
    a = p.parse_args(argv)
    try:
        根id = 置き場の口.根を受け取る(a.根)
        間 = 間の口(口 if 口 is not None else drive口.開く(), a.間, 眠る)
        結果 = 点.点検(点.読む口(間, 0), 根id, 当てる用=True)
        計画 = 計画を組む(間, 結果, a.会社)
    except Exception as e:  # noqa: BLE001 — 訳に id・鍵を入れない（型の名と訳だけ）
        print(f"読めない: {_訳(e)}", file=sys.stderr)
        return 2
    今の印 = 印(計画)
    out = {"乾いた回し": not a.当てる, "印": 今の印, "会社": 見せる(計画)}
    if a.当てる:
        if a.印 is not None and a.印 != 今の印:
            print(f"止めた: 印が違う（乾いた回しの後に案が変わった）。乾いた回しから回し直す", file=sys.stderr)
            return 3
        try:
            out["当てた"] = 当てる(間, 根id, 計画, 今=今)
        except 止める as e:
            print(json.dumps(out, ensure_ascii=False, indent=1))
            print(f"止めた: {e}", file=sys.stderr)
            return 3
        except Exception as e:  # noqa: BLE001 — 照らす・記録を置く で落ちた（訳に id を入れない）
            print(json.dumps(out, ensure_ascii=False, indent=1))
            print(f"止めた: 照らす・記録を置く途中で読めない・書けない（{_訳(e)}）。点検から回し直す", file=sys.stderr)
            return 3
    out["Google へ打った頼みの数"] = 間.回数
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("、".join(f"{c}: 列を広げる {v['数']['列を広げる']}・行を広げる {v['数']['行を広げる']}・書く {v['数']['書く'] + v['数']['足す'] + v['数']['作る']}・消す {v['数']['消す']}"
                   f"・当てない {v['数']['当てない']}・問う {v['数']['問う物']}" for c, v in out["会社"].items())
          or "当てる物は無い", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
