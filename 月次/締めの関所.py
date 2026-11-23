"""締めの記録の判断の口（〔口: 締める〕と〔口: 出荷〕の「締めた時の版で回す」が呼ぶ）。置き場を開かない。

殻（事務所の側の口）が台帳を読み・決定DB の行を読み・書く。何を書くか・止めるかはこの口だけが決める（殻に同じ判断を写さない）。
今のパックの版は `出口/証明.パックの版()`・型に版の列が在るかは `初期設定/型の口.型()`＝この口を置いたパックの物だけを見る。

  python3 月次/締めの関所.py 締める行の形   < 入力.json   # {"行"} → {"会社","支給月"}（台帳を読む前の形の照らし）
  python3 月次/締めの関所.py 締める         < 入力.json   # {"行","締めの記録"(get_values の 2 次元)} → {"赤"} か {"赤":[],"書く行","パックの版"}
  python3 月次/締めの関所.py 答えの行       < 入力.json   # {"答え"} → {"赤"} か {"赤":[],"行"(決定DB の行の id)}
  python3 月次/締めの関所.py 締め直す       < 入力.json   # {"会社","支給月","答えの文","締めの記録"} → {"赤"} か {"赤":[],"書く行","パックの版"}
  python3 月次/締めの関所.py 締めた時の版で回すか < 入力.json   # {"答え","回"} → {"赤"}（台帳を読む前）
  python3 月次/締めの関所.py 締めた時の版   < 入力.json   # {"会社","支給月","締めの記録"} → {"赤"} か {"赤":[],"版"}

形の崩れた入力は {"拒む": 訳}・終わりの値 2。判断の赤は {"赤": [...]}・終わりの値 0（殻が赤のまま返す）。
"""
import json
import re
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent
if str(ここ.parent) not in sys.path:
    sys.path.insert(0, str(ここ.parent))

from 月次.口の入口 import 拒む, 回す  # noqa: E402  拒むの約束（どの崩れも {"拒む"}・終わりの値 2）は入口の 1 つだけ

締めのタブ = "締めの記録"
鍵 = ("会社", "支給月", "NO")   # 出荷の口と同じ書く鍵
版の列 = "パックの版"
締め直す範囲 = "今の版で出す"
_決定 = re.compile(r"^決定DB\s+(\d{4}-\d{2}-\d{2})\s+(https://(?:www\.)?notion\.so/\S*?([0-9a-f]{32})\S*)$")
_区切り = r"\s:：「」『』（）()、,。/｜|・"




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


def 締めた時の版(行たち: list[dict], 会社: str, 支給月: str) -> tuple[str | None, str | None]:
    """締めの記録の行から、その会社・支給月の締めた時の版。(版, 訳)。行が無い＝(None, None)・
    版が空の行がある・行で割れる＝(None, 訳)。"""
    got = sorted({str(r.get(版の列, "") or "").strip() for r in 行たち
                  if str(r.get("会社", "")).strip() == 会社 and str(r.get("支給月", "")).strip() == 支給月})
    if not got:
        return None, None
    if "" in got:
        return None, f"締めの記録に締めた時の版が無い行がある（{会社} {支給月}）"
    if len(got) > 1:
        return None, f"締めの記録の締めた時の版が行で割れている（{会社} {支給月}: {'・'.join(got)}）"
    return got[0], None


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
    """締めの行に今の版を押す。型に版の列が在るのに台帳に無い（型が古い台帳）・同じ月を別の版で締めた行が在る時は赤。"""
    形 = 締める行の形(行)
    if isinstance(形, list):
        return {"赤": 形}
    会社, 支給月 = 形
    h, 在る = _行たち(締めの記録)
    今 = 版 if 版 is not None else 今の版()
    型 = 型に列 if 型に列 is not None else 型に版の列が在るか()
    押す = 版の列 in h
    if 型 and not 押す:
        return {"赤": [f"パックの型（版 {今}）の {締めのタブ} には {版の列} の列が在るのに台帳に無い"
                      "＝型が古い台帳。〔口: 寄せる〕で寄せてから締める（版を書かずに締めない）"]}
    if 押す:
        was, why = 締めた時の版([r for r in 在る if str(r.get(版の列, "")).strip()], 会社, 支給月)
        if was and was != 今:
            why = f"{会社} {支給月} は版 {was} で締めた行が在り、今のパックの版 {今} と違う"
        if why:
            return {"赤": [why + "＝月を版で割らない。その月をどちらの版で出すかをオーナーに選択肢の画面で聞く"
                          "（今の版で出す＝〔口: 締める〕の 締め直す（月次/締めの関所.py 締め直す）／"
                          "締めた時の版で出す＝〔口: 出荷〕の 締めた時の版で回す（月次/締めの関所.py 締めた時の版）"]}
    return {"赤": [], "書く行": [{**r, 版の列: 今} if 押す else dict(r) for r in 行], "パックの版": 今 if 押す else None}


def 答えの行(答え) -> dict:
    """締め直すのオーナーの答えが出所の形（決定DB の行）か。通れば読む行の id。"""
    m = _決定.match(str(答え or "").strip())
    if not m:
        return {"赤": ["締め直す（今の版で出す）はオーナーが選んだ時だけ＝オーナーの答えを出所の形 `決定DB <YYYY-MM-DD> <行の URL>` で渡す"
                      "（会話で答えた事は決定DB の行にしてから）。AI が決めて締めた時の版を書き替えない"]}
    return {"赤": [], "行": m.group(3)}


def _言う(文: str, 語: str) -> bool:
    """文に語が区切りに挟まれて在るか（「別の作り物の会社」に「作り物の会社」は在ると見ない）。"""
    return bool(語) and re.search(rf"(?:^|(?<=[{_区切り}])){re.escape(語)}(?=$|[{_区切り}])", 文, re.M) is not None


def 答えの赤(文: str, 会社: str, 支給月: str) -> list[str]:
    """決定DB の行の字に、同じ会社・同じ支給月・範囲「今の版で出す」が在るか。"""
    miss = [f"{n}「{v}」" for n, v in (("会社", 会社), ("支給月", 支給月), ("範囲", 締め直す範囲)) if not _言う(str(文 or ""), v)]
    if miss:
        return [f"オーナーの答えの決定DB の行に {'・'.join(miss)} が無い＝別の会社・別の回・別の範囲の答えで締め直さない"]
    return []


def 締め直す(会社: str, 支給月: str, 答え, 答えの文: str, 締めの記録, 版: str | None = None) -> dict:
    """オーナーが「今の版で出す」を選んだ月の行の版を全部今の版へ。答えが決定DB の行の形か・その行の字と台帳で照らす。"""
    会社, 支給月 = str(会社 or "").strip(), str(支給月 or "").strip()
    if not (会社 and 支給月):
        return {"赤": ["形: 台帳・会社・支給月 が要る"]}
    行 = 答えの行(答え)
    if 行["赤"]:   # 決定DB の行を通らない答え（会話の字・AI の判断）では締め直さない
        return {"赤": 行["赤"]}
    赤 = 答えの赤(答えの文, 会社, 支給月)
    if 赤:
        return {"赤": 赤}
    h, 在る = _行たち(締めの記録)
    今 = 版 if 版 is not None else 今の版()
    if 版の列 not in h:
        return {"赤": [f"{締めのタブ} に {版の列} の列が無い＝型が古い台帳。〔口: 寄せる〕で寄せてから"]}
    mine = [r for r in 在る if str(r.get("会社", "")).strip() == 会社 and str(r.get("支給月", "")).strip() == 支給月]
    if not mine:
        return {"赤": [f"{締めのタブ} に {会社} {支給月} の行が無い"]}
    return {"赤": [], "書く行": [{**r, 版の列: 今} for r in mine], "パックの版": 今}


def 締めた時の版で回すか(答え, 回) -> list[str]:
    """出荷の口の「締めた時の版で回す」: オーナーの答えの在り処が在り、月の給与の時だけ（台帳を読む前）。"""
    if not str(答え or "").strip():
        return ["締めた時の版で回す はオーナーが選んだ答えの在り処（URL か受付番号）を渡す時だけ（AI が決めて版を選ばない）"]
    if 回 != "月":
        return ["締めた時の版で回す は月の給与だけ（賞与は締めの記録を読まない）"]
    return []


def 締めた時の版の印(会社: str, 支給月: str, 締めの記録) -> dict:
    """締めの記録からその月の締めた時の版。決まらなければ赤（殻はその版のパックを置かない）。"""
    if not isinstance(締めの記録, list):
        raise 拒む(f"{締めのタブ} は get_values の 2 次元（list）で渡す")
    t = 締めの記録
    h = [str(x) for x in (t or [[]])[0]]
    rows = [{c: (r[i] if i < len(r) else "") for i, c in enumerate(h)} for r in t[1:]]
    会社, 支給月 = str(会社).strip(), str(支給月).strip()
    tag, why = 締めた時の版(rows, 会社, 支給月)
    if why or not tag:
        return {"赤": [(why or f"締めの記録に {会社} {支給月} の行が無い") + "＝締めた時の版で回せない"]}
    return {"赤": [], "版": tag}


def _口(何: str, x: dict) -> dict:
    if not isinstance(x, dict):
        raise 拒む("入力は JSON の表で渡す")
    if 何 == "締める行の形":
        形 = 締める行の形(x.get("行"))
        return {"赤": 形} if isinstance(形, list) else {"赤": [], "会社": 形[0], "支給月": 形[1]}
    if 何 == "締める":
        return 締める(x.get("行"), x.get("締めの記録"))
    if 何 == "答えの行":
        return 答えの行(x.get("答え"))
    if 何 == "締め直す":
        return 締め直す(x.get("会社"), x.get("支給月"), x.get("答え"), x.get("答えの文"), x.get("締めの記録"))
    if 何 == "締めた時の版で回すか":
        return {"赤": 締めた時の版で回すか(x.get("答え"), x.get("回"))}
    if 何 == "締めた時の版":
        return 締めた時の版の印(x.get("会社"), x.get("支給月"), x.get("締めの記録"))
    raise 拒む(f"知らない口: {何}")


if __name__ == "__main__":
    回す(_口)
