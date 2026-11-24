"""寄せの回の続きの判断の口（〔口: 寄せる〕が呼ぶ・寄せる道具.md §1.5・§1.6）。置き場を開かない。

殻（事務所の側の口）が管理表・9_履歴 の名・寄せの記録の字を読んで渡し、何を書くか・止めるか・どこから続けるかは
この口だけが決める（殻に同じ判断を写さない）。殻は返った 赤・止める の字のまま止める。

  python3 道具/寄せ/続き.py 渡し方 < 入力.json
    # {"会社","突き合わせ": 出荷の入力|null,"突き合わせなし": 訳} → {"赤","渡した"}（何も読む前）
  python3 道具/寄せ/続き.py 前の記録の名 < 入力.json
    # {"名たち": [9_履歴 の file の名]} → {"記録": 一番新しい寄せの記録の名|null}
  python3 道具/寄せ/続き.py 前の回 < 入力.json
    # {"会社","記録": 名|null,"中身": 記録の JSON の字|null} → {"赤"} か {"赤":[],"前の回": {"記録","写した物"}}
  python3 道具/寄せ/続き.py 見通しの後 < 入力.json
    # {"見通し"} → {"終わる": 返す物}（寄せられない物が在る＝書かない）| {"続ける": true}（突き合わせる月を読む前）
  python3 道具/寄せ/続き.py 突き合わせる月の後 < 入力.json
    # {"渡した","前の回","見通し","突き合わせる月": 返り|null,"パックの訳": 字|null}
    # → {"終わる": 返す物} | {"止める": 訳} | {"続ける": true}
  python3 道具/寄せ/続き.py 続き < 入力.json
    # {"写した物","履歴","在る写し","前の回","書く手順"} → {"赤"} か {"赤":[],"続きの写し","書く手順"}

形の崩れた入力は {"拒む": 訳}・終わりの値 2。
"""
import json
import sys
from pathlib import Path

_根 = Path(__file__).resolve().parent.parent.parent
if str(_根) not in sys.path:
    sys.path.insert(0, str(_根))

from 月次.口の入口 import 拒む, 回す  # noqa: E402  拒むの約束（どの崩れも {"拒む"}・終わりの値 2）は入口の 1 つだけ

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import 見回り  # noqa: E402  寄せの記録の名の形（口の記録の名）・9_履歴/消す_<日>_<名> の形（当てる.写しを読む）の正本＝ここに写さない
渡す物 = "寄せる は 突き合わせる月（--突き合わせ 出荷の入力）か、まだ出していない訳（--突き合わせなし）のどちらか 1 つを渡す"




def 渡し方(会社: str, 突き合わせ, 突き合わせなし: str) -> dict:
    """突き合わせる月の入力と無い訳のどちらを渡したか。両方・別の会社の入力は何も読む前に赤。"""
    なし = str(突き合わせなし or "").strip()
    if 突き合わせ is not None and なし:
        return {"赤": [渡す物], "渡した": True}
    if 突き合わせ is not None and (not isinstance(突き合わせ, dict) or str(突き合わせ.get("会社") or "").strip() != 会社):
        got = 突き合わせ.get("会社") if isinstance(突き合わせ, dict) else repr(突き合わせ)
        return {"赤": [f"突き合わせの入力の会社「{got}」が寄せる会社「{会社}」でない＝別の会社の出す物で突き合わせない。"
                      "何も読まず書かずに止める"], "渡した": True}
    return {"赤": [], "渡した": 突き合わせ is not None or bool(なし)}


def 前の記録の名(名たち) -> str | None:
    """9_履歴 の名から一番新しい寄せの記録の名（無ければ None）。"""
    got = sorted(n for n in (名たち or []) if isinstance(n, str) and (m := 見回り.口の記録の名.fullmatch(n)) and m.group(1) == "寄せの記録")
    return got[-1] if got else None


def 前の回(会社: str, 記録: str | None, 中身) -> dict:
    """前の回が寄せ中のまま止まった時の、その回の寄せの記録の名・写した物。記録が無ければ写しも無い。
    記録が読めない・別の会社の物は赤（前の回の写しを申告で受けない）。"""
    if 記録 is None:
        return {"赤": [], "前の回": {"記録": None, "写した物": []}}
    try:
        rec = json.loads(中身) if isinstance(中身, str) else 中身
    except ValueError:
        rec = None
    if not isinstance(rec, dict) or rec.get("会社") != 会社 or not isinstance(rec.get("写した物", []), list):
        return {"赤": [f"9_履歴 の {記録} が会社 {会社} の寄せの記録でない＝前の回の写しを照らせない"]}
    return {"赤": [], "前の回": {"記録": 記録, "写した物": [p for p in rec.get("写した物") or [] if isinstance(p, str)]}}


def 見通しの後(見通し: dict) -> dict | None:
    """寄せられない物が在れば書かずに終わる（返す物）。無ければ None。"""
    n = len((見通し or {}).get("寄せられない物") or [])
    return {"通す": False, "書いた": 0, "寄せられない物": n, "赤": []} if n else None


def 突き合わせる月の後(渡した: bool, 前: dict | None, 見通し: dict, 月: dict | None, 訳: str | None) -> dict:
    """見通しの後 で続けた回だけ呼ぶ。パックの 突き合わせる月 の返り（拒まれたら その訳）から、終わる・止める・続ける を決める（§1.6）。"""
    見通し = 見通し or {}
    if 月 is None:
        if 渡した:
            if not str(訳 or "").strip():   # 訳の無い止まりを返さない（殻が何で止まったか言えない）
                raise 拒む("突き合わせる月 が無いのに パックの訳 が無い")
            return {"止める": str(訳)}
        if 前 is None and 見通し.get("足りない値") and not any(見通し.get(k) for k in ("書く手順", "管理表へ書く", "写した物")):
            # 残りが足りない値だけ＝突き合わせる物は無いが、寄せ終わりとは言わない（値を埋めてから見通す）
            n = len(見通し["足りない値"])
            return {"終わる": {"通す": False, "書いた": 0, "寄せられない物": 0, "足りない値": n,
                              "赤": [f"書く手順 0 だが足りない値が {n} つ＝寄せ終わりと言わない（値を埋めてから見通す）"]}}
        return {"止める": 渡す物 + ("（前の回が寄せ中のまま止まっている＝突き合わせてから外す）" if 前 is not None else
                                  "（書く手順か管理表へ書く物が在る）") + f"。パック: {訳}"}
    if not isinstance(月, dict) or not isinstance(月.get("変わらない"), bool):
        raise 拒む("突き合わせる月 の返りに 変わらない が無い")
    if 月["変わらない"]:
        return {"終わる": {"通す": True, "書いた": 0, "寄せられない物": 0, "赤": [],
                          "知らせ": ["書く手順 0・管理表も今の版＝寄せる物は無い"]}}
    if not 渡した:   # 変わる会社は申告を記録で照らしてから書く（パックが拒まなくても入力なしでは書かない）
        return {"止める": 渡す物 + f"（パックの残り: {'・'.join(map(str, 月.get('残り') or []))}）"}
    return {"続ける": True}


def 続き(写した物, 履歴: str, 在る写し: list, 前: dict | None, 書く手順: list) -> dict:
    """この回が作る写しと履歴に在る写しを照らし、前の回の写しから続ける。前の回の記録に無い写しが在れば重ねて書かない。"""
    if (not isinstance(写した物, list)
            or not all(isinstance(p, str) and p.startswith(str(履歴) + "/") and 見回り.当てる.写しを読む(p) for p in 写した物)
            or len(set(写した物)) != len(写した物)):
        return {"赤": ["パックの写した物が履歴の写しの名の並びでない＝何も書かない"]}
    在る = [p for p in (在る写し or []) if isinstance(p, str)]
    clash = set(写した物).intersection(在る)
    # 前の回が止まり、その回の寄せの記録の 写した物 に在る写し＝この回の写し（前の正の版）。作り直さず続きから当てる
    resumed = clash.intersection((前 or {}).get("写した物") or []) if 前 else set()
    if clash - resumed:
        return {"赤": ["この回が作る名前の写しが履歴に既に在る＝重ねて書かない（前の回の寄せの記録に無い写し）"]}
    if any(在る.count(x) != 1 for x in resumed):
        return {"赤": ["前の回の写しが履歴に 1 つずつ揃わない＝続きから当てない"]}
    return {"赤": [], "続きの写し": sorted(resumed),
            "書く手順": [x for x in 書く手順 or [] if not (x.get("する") == "file を写す" and x.get("先") in resumed)]}


def _口(何: str, x) -> dict:
    if not isinstance(x, dict):
        raise 拒む("入力は JSON の表で渡す")
    会社 = str(x.get("会社") or "").strip()
    if 何 == "渡し方":
        return 渡し方(会社, x.get("突き合わせ"), x.get("突き合わせなし") or "")
    if 何 == "見通しの後":
        end = 見通しの後(x.get("見通し") or {})
        return {"終わる": end} if end else {"続ける": True}
    if 何 == "前の記録の名":
        return {"記録": 前の記録の名(x.get("名たち"))}
    if 何 == "前の回":
        return 前の回(会社, x.get("記録"), x.get("中身"))
    if 何 == "突き合わせる月の後":
        return 突き合わせる月の後(bool(x.get("渡した")), x.get("前の回"), x.get("見通し") or {},
                            x.get("突き合わせる月"), x.get("パックの訳"))
    if 何 == "続き":
        if "写した物" not in x:   # 欠けたのを「写す物は無い」とみなさない
            raise 拒む("続き は 写した物（この回が作る写しの名の並び）を渡す")
        return 続き(x.get("写した物"), str(x.get("履歴") or ""), x.get("在る写し") or [], x.get("前の回"),
                  x.get("書く手順") or [])
    raise 拒む(f"知らない口: {何}")


if __name__ == "__main__":
    回す(_口)
