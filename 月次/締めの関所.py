"""締めの記録の判断の口（〔口: 締める〕が呼ぶ）。置き場を開かない。

殻（事務所の側の口）が台帳を読み・書く。何を書くか・止めるかはこの口だけが決める（殻に同じ判断を写さない）。
締めの記録の置き場は年の台帳の 6_計算の結果（人ごと）（タブの名は型から 月次/台帳の名.py が結ぶ）。
締めた行に版は刻まない（版の刻み・版が読めない時とタブが無い時の拒みは 2026-11-27 に畳んだ）。

  python3 月次/締めの関所.py 締める行の形   < 入力.json   # {"行"} → {"会社","支給月"}（台帳を読む前の形の照らし）
  python3 月次/締めの関所.py 締める         < 入力.json   # {"行","締めの記録"(get_values の 2 次元)} → {"赤":[],"書く行"}

形の崩れた入力は {"拒む": 訳}・終わりの値 2。判断の赤は {"赤": [...]}・終わりの値 0（殻が赤のまま返す）。
"""
import json
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent
if str(ここ.parent) not in sys.path:
    sys.path.insert(0, str(ここ.parent))

from 月次.口の入口 import 拒む, 回す  # noqa: E402  拒むの約束（どの崩れも {"拒む"}・終わりの値 2）は入口の 1 つだけ

締めのタブ = "締めの記録"   # 物の名。型のタブの名（6_計算の結果（人ごと））へは 月次/台帳の名.py が結ぶ
鍵 = ("会社", "支給月", "NO")   # 出荷の口と同じ書く鍵


def _行たち(表) -> tuple[list[str], list[dict]]:
    if not isinstance(表, list) or not 表:
        raise 拒む(f"{締めのタブ} の見出しが無い")
    h = [str(x) for x in 表[0]]
    return h, [{c: (r[i] if i < len(r) else "") for i, c in enumerate(h)} for r in 表[1:]]


def 締める行の形(行) -> tuple[str, str] | list[str]:
    """締める行の形を照らす。通れば (会社, 支給月)、崩れていれば赤。"""
    if not isinstance(行, list) or not 行:
        return ["形: 台帳 と 行（1 行以上）が要る"]
    bad = [i for i, r in enumerate(行) if not isinstance(r, dict) or any(not str(r.get(k, "")).strip() for k in 鍵)]
    if bad:
        return [f"形: 行 {bad} に鍵（{'・'.join(鍵)}）の空がある"]
    組 = {(str(r["会社"]).strip(), str(r["支給月"]).strip()) for r in 行}
    if len(組) != 1:
        return ["形: 締めるのは一度に1社・1支給月"]
    return next(iter(組))


def 締める(行, 締めの記録) -> dict:
    """締めの行の形を照らし、書く行を返す（版は刻まない）。"""
    形 = 締める行の形(行)
    if isinstance(形, list):
        return {"赤": 形}
    _行たち(締めの記録)
    return {"赤": [], "書く行": [dict(r) for r in 行]}


def _口(何: str, x: dict) -> dict:
    if not isinstance(x, dict):
        raise 拒む("入力は JSON の表で渡す")
    if 何 == "締める行の形":
        形 = 締める行の形(x.get("行"))
        return {"赤": 形} if isinstance(形, list) else {"赤": [], "会社": 形[0], "支給月": 形[1]}
    if 何 == "締める":
        return 締める(x.get("行"), x.get("締めの記録"))
    raise 拒む(f"知らない口: {何}")


if __name__ == "__main__":
    回す(_口)
