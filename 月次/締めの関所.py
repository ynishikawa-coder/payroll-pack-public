"""締めの記録の判断の口（〔口: 締める〕が呼ぶ）。置き場を開かない。

殻（事務所の側の口）が台帳を読み・書く。何を書くか・止めるかはこの口だけが決める（殻に同じ判断を写さない）。
今のパックの版は `出口/証明.パックの版()`・型に版の列が在るかは `初期設定/型の口.型()`＝この口を置いたパックの物だけを見る。
締めた行には締めた時のパックの版を押すだけ＝記録（確定した勤怠は台帳に在り、版が上がっても壊れない）。同じ月を前の版で
締めた行が在っても止めない（月を版で割らない止めは 2026-11-25 に畳んだ。どの版で締めてどの版で計算したかは 月を回す の証明に残る）。

  python3 月次/締めの関所.py 締める行の形   < 入力.json   # {"行"} → {"会社","支給月"}（台帳を読む前の形の照らし）
  python3 月次/締めの関所.py 締める         < 入力.json   # {"行","締めの記録"(get_values の 2 次元)} → {"赤"} か {"赤":[],"書く行","パックの版"}

形の崩れた入力は {"拒む": 訳}・終わりの値 2。判断の赤は {"赤": [...]}・終わりの値 0（殻が赤のまま返す）。
"""
import json
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent
if str(ここ.parent) not in sys.path:
    sys.path.insert(0, str(ここ.parent))

from 月次.口の入口 import 拒む, 回す  # noqa: E402  拒むの約束（どの崩れも {"拒む"}・終わりの値 2）は入口の 1 つだけ

締めのタブ = "締めの記録"
鍵 = ("会社", "支給月", "NO")   # 出荷の口と同じ書く鍵
版の列 = "パックの版"


def 今の版() -> str:
    """この口を置いたパックの版（出す前の照らしと同じ正本）。読めなければ拒む。"""
    from 出口 import 証明
    v = 証明.パックの版()
    if not v:
        raise 拒む("置いたパックの版が読めない")
    return v


def 型に版の列が在るか() -> bool:
    """この口を置いたパックの型の 締めの記録 に パックの版 の列が在るか。タブが無ければ拒む。"""
    import importlib.util
    p = ここ.parent / "初期設定" / "型の口.py"
    spec = importlib.util.spec_from_file_location("締めの関所_型の口", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for sh in m.型()["シート"]:
        for t in sh["タブ"]:
            if t["タブ"] == 締めのタブ:
                return any(c.get("名") == 版の列 for c in t.get("列") or [])
    raise 拒む(f"パックの型に {締めのタブ} のタブが無い")


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
    if any(版の列 in r for r in 行):
        return [f"形: 行に {版の列} を書かない（締めた時の版はこの口が置いたパックから押す）"]
    組 = {(str(r["会社"]).strip(), str(r["支給月"]).strip()) for r in 行}
    if len(組) != 1:
        return ["形: 締めるのは一度に1社・1支給月"]
    return next(iter(組))


def 締める(行, 締めの記録, 版: str | None = None, 型に列: bool | None = None) -> dict:
    """締めの行に今の版を押す（締めた時の版の記録）。型に版の列が在るのに台帳に無い（型が古い台帳）時だけ赤。
    同じ月を前の版で締めた行が在っても止めない（その行の版は書き替えない＝どの版で締めたかが残る）。"""
    形 = 締める行の形(行)
    if isinstance(形, list):
        return {"赤": 形}
    h, _ = _行たち(締めの記録)
    今 = 版 if 版 is not None else 今の版()
    型 = 型に列 if 型に列 is not None else 型に版の列が在るか()
    押す = 版の列 in h
    if 型 and not 押す:
        return {"赤": [f"パックの型（版 {今}）の {締めのタブ} には {版の列} の列が在るのに台帳に無い"
                      "＝型が古い台帳。〔口: 寄せる〕で寄せてから締める（版を書かずに締めない）"]}
    return {"赤": [], "書く行": [{**r, 版の列: 今} if 押す else dict(r) for r in 行], "パックの版": 今 if 押す else None}


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
