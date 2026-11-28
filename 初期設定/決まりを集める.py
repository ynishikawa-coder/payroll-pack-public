"""決まりを集める段: 新しい会社を始める時に、計算が要る決まりが揃っているかを 1 か所で照らし、欠けを
事務所の既定（事務所の設定「既定」に 1 行）か会社への問いへ回す。Drive を開かない・値を埋めない（既定は候補として見せるだけ）。

なぜ在るか（2026-11-28）: 決まりの欠けは計算の時に初めて「事務所の設定「既定」のタブにも会社のマスタにも無い」の仮として
全部の会社に出ていた（集める段が無く、項目ごとにどこで決めるかの印も無かった）。項目.json の `集め方` がその印で、ここが読む 1 か所。

  集める(入力) → {揃った, 事務所の既定へ, 会社に聞く, 条件待ち, 止める, 止めた訳}
    入力（始める と同じ dict。どれも無くてよい）:
      最初の支給月      事務所の行の適用開始を比べる月（YYYY.MM支給）
      会社の値          {名: 値 か {値, 書類の名}}（書類から入れた会社の値）
      事務所            事務所の設定「既定」の行 [{項目, 今の値, 適用開始}]
      勤務の型・人      その会社の勤務の型・社員の行（列＝`分野.名`）
      会社              会社の呼び名
      支給控除の項目    2_マスタ ④ の行・つなぎ: ⑥ の行（会社・側・道具・その道具での名・その道具での番号）
      事務所のルール    事務所のルール.md の本文
    揃った: 事務所・会社・（全部の）勤務の型か人のどこかに値がある名。
    事務所の既定へ: [{鍵, 既定の候補, 法の根拠}]（集め方＝事務所の既定 の欠け。事務所が 1 行書けば全部の会社に効く）。
    会社に聞く: [名]（集め方＝会社に聞く の欠け。問いは 始める.問いを起こす が立てる）。
    条件待ち: [{鍵, 条件の項目}]（要る時 の条件の値がまだ無い＝条件が決まってから要るかが決まる）。
    法の既定 の名は法の表/法の線.json の線で決まる＝照らさない。
  止める（黙って既定へ落とさない・黙って読み飛ばさない）:
    事務所の行・会社の値の 項目 が項目の辞書に無い名（打ち間違い・型の版で消えた名 例 有給.1日の賃金）。
    値が選べる値に当たらない（例 有給.1日の賃金 の「通常の賃金」のような辞書の外の字）。
    事務所のルール.md「給与ソフトと取り込みの形」の `- X: Y` の X が形の鍵でない（打ち間違いが黙って説明になっていた）。
    ⑥つなぎ の項目の形が引けない（固定残業手当・通勤 などは ④ の行が置き場。下の 固定残業と通勤の置き場）。
    割増.固定残業＝額で なのに ④ に訳 固定残業手当 の行が無い・行があるのに 額で でない。
固定残業と通勤の置き場（論点 5・型の版 42 の線を初期設定で照らす）: 固定残業手当の額は ④ の訳（割増の基礎から除く訳）
固定残業手当 の行＋② の人の額の 1 か所。通勤は ④ の行の 課税（通勤の非課税・課税）。⑥つなぎ の項目の名はその ④ の行の 項目 と
同じ字で引く（出口/形.py の 欄の対応を組む が ④ の 項目 を円の名に入れる）。
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent
if str(ここ.parent) not in sys.path:
    sys.path.insert(0, str(ここ.parent))
from 芯 import 設定  # noqa: E402


def _読む(名: str, 場所: Path):
    if 名 not in sys.modules:
        spec = importlib.util.spec_from_file_location(名, 場所)
        m = importlib.util.module_from_spec(spec)
        sys.modules[名] = m
        spec.loader.exec_module(m)
    return sys.modules[名]


口 = _読む("初期設定_型の口_集める", ここ / "型の口.py")
段 = _読む("初期設定_段の解決_集める", ここ / "段の解決.py")

集め方たち = ("事務所の既定", "会社に聞く", "法の既定")
固定残業の訳 = "固定残業手当"
つなぎの欠けの直し方 = ("④支給控除の項目にその名の行を足す（固定残業手当＝割増の基礎から除く訳 固定残業手当 の行、"
                  "通勤＝課税 通勤の非課税／課税 の行。項目 の字を ⑥つなぎ と同じに）")


def _辞書() -> dict:
    return {it["項目"]: it for it in 口.項目たち()}


def 読み(v):
    """選べる値の語を空白と後ろの括弧を除いて読む（`4 週 4 休（起算日つき）` と `4週4休` を同じに。芯/集計 の読みと同じ）。"""
    if v is None:
        return None
    s = "".join(str(v).split())
    return s.split("（", 1)[0] if s.endswith("）") and not s.startswith("（") else s


def _事務所の値(入力: dict) -> dict:
    rows = 段.行たち(入力.get("事務所") or ())
    if not rows:
        return {}
    月 = 入力.get("最初の支給月")
    if not 月:
        return {str(r.get("項目", "")).strip(): r.get("今の値") for r in rows
                if str(r.get("項目", "")).strip() and not 段.空(r.get("今の値"))}
    return 段.一番新しい(rows, lambda r: str(r.get("項目", "")).strip() or None, "今の値", 月, [])


def 効く値(名: str, 入力: dict):
    """会社の値 → 事務所の既定の行 → None（項目の既定へは落とさない＝既定は問いに見せる見当）。"""
    会社 = 入力.get("会社の値") or {}
    if 名 in 会社:
        return 会社[名]["値"] if isinstance(会社[名], dict) else 会社[名]
    return _事務所の値(入力).get(名)


def 要るか(it: dict, 入力: dict):
    """要る時 の条件 → True（要る）／False（要らない）／None（条件の値がまだどこにも無い＝決まってから要るかが決まる）。"""
    要る = it.get("要る時")
    if not 要る:
        return True
    値たち = {読み(効く値(要る["項目"], 入力))}
    for 段名 in ("勤務の型", "人"):
        for r in 入力.get(段名) or ():
            値たち.add(読み(r.get(要る["項目"])))
    値たち -= {None, ""}
    if not 値たち:
        return None
    return bool(値たち & {読み(v) for v in 要る["値"]})


def _下の段で揃う(it: dict, 入力: dict) -> bool:
    """勤務の型か人の段に置ける名で、その段の行が在り全部に値がある。"""
    名 = it["項目"]
    for 段名 in ("勤務の型", "人"):
        rows = 入力.get(段名) or ()
        if 段名 in it.get("段", ()) and rows and all(not 段.空(r.get(名)) for r in rows):
            return True
    return False


def 足りない値(入力: dict) -> list[dict]:
    """聞く項目のうち、事務所にも会社にも全部の勤務の型にも全部の人にも値が無い物 → [{項目, 段, 誰}]。
    要る時 の条件がまだ決まらない名は聞かない（条件待ち＝集める の 条件待ち に出る）。"""
    会社の値 = 入力.get("会社の値") or {}
    事務所の値 = _事務所の値(入力)
    out = []
    for it in 口.項目たち():
        if not it.get("聞く") or 要るか(it, 入力) is not True:
            continue
        名 = it["項目"]
        if 名 in 事務所の値 or ("会社" in it["段"] and 名 in 会社の値):
            continue
        欠け = {}
        for 段名, 鍵 in (("勤務の型", "型の名"), ("人", "NO")):
            if 段名 in it["段"]:
                rows = 入力.get(段名) or []
                欠け[段名] = [str(r.get(鍵)) for r in rows if r.get(名) in (None, "")] if rows else ["（無い）"]
        if "会社" in it["段"]:
            if any(not v for v in 欠け.values()):
                continue  # 下の段の全部に値がある
            out.append({"項目": 名, "段": "会社", "誰": []})
        else:
            段名 = next(iter(欠け))
            if 欠け[段名]:
                out.append({"項目": 名, "段": 段名, "誰": 欠け[段名]})
    return out


def 集める名() -> list[str]:
    """計算が要る決まりの名: 芯が見当で埋める名（要る人だけの名を除く）・聞く名・必ず埋める名（会社か事務所の段の物）。名の順。"""
    辞書 = _辞書()
    名たち = {n for n, e in 設定.表().items() if e.get("見当") is not None and n not in 設定.要る人だけの見当}
    名たち |= {n for n, it in 辞書.items() if it.get("聞く")}
    名たち |= {n for n in 設定.必ず埋める() if n in 辞書 and {"会社", "事務所"} & set(辞書[n]["段"])}
    return sorted(名たち)


def _値の誤り(名: str, v) -> str | None:
    if 段.空(v):
        return None
    if 名 in 段.字をそろえる項目:
        return None if 段.字をそろえる(名, v) is not None else f"の値「{v}」が読めない（{段.字をそろえる項目[名]}）"
    if not 段.設定の字か(名, v):
        return f"の値「{v}」が選べる値に無い（選べる値: {_辞書()[名]['選べる値']}）"
    return None


def _名と値を照らす(所: str, 名: str, v, 辞書: dict) -> str | None:
    if 名 not in 辞書:
        return f"{所}「{名}」が今の項目の辞書に無い名（打ち間違いか型の版で消えた名。今の名へ直す）"
    誤り = _値の誤り(名, v)
    return f"{所}「{名}」{誤り}" if 誤り else None


def _mdの知らない鍵(md: str) -> list[str]:
    """事務所のルール.md「給与ソフトと取り込みの形」の `- X: Y` のうち X が形の鍵でない行（出口/形.py の 形をmdから読む と同じ読み）。"""
    from 出口 import 形
    行たち = str(md or "").splitlines()
    始め = next((i for i, x in enumerate(行たち) if re.match(rf"^##\s+(\d+\s+)?{形.形の見出し}\s*$", x.strip())), None)
    if 始め is None:
        return []
    out = []
    for x in 行たち[始め + 1:]:
        if re.match(r"^##\s", x.strip()):
            break
        m = re.match(r"^\s*[-*]\s*([^:：]+?)\s*[:：]\s*(.*?)\s*$", x)
        if m and m.group(1) not in 形.形の鍵たち:
            out.append(f"事務所のルール.md「{形.形の見出し}」の「{m.group(1)}」が形の鍵でない"
                       f"（鍵は {'・'.join(形.形の鍵たち)}。説明は箇条書きの `鍵: 値` の形で書かない）")
    return out


def _つなぎの誤り(入力: dict) -> list[str]:
    会社, つなぎ = str(入力.get("会社", "")).strip(), 入力.get("つなぎ") or ()
    if not つなぎ:
        return []
    from 出口 import 形
    道具たち = sorted({str(t.get("道具", "")).strip() for t in つなぎ
                    if str(t.get("会社", "")).strip() == 会社 and t.get("側") == "出口" and str(t.get("道具", "")).strip()})
    out = []
    for 道具 in 道具たち:
        try:
            形.欄の対応を組む(会社, 道具, 入力.get("支給控除の項目") or (), つなぎ, 入力.get("最初の支給月"))
        except ValueError as e:
            if "形が引けない" not in str(e):
                raise
            out.append(f"{e}。直し方: {つなぎの欠けの直し方}")
    return out


def _固定残業の誤り(入力: dict) -> list[str]:
    会社 = str(入力.get("会社", "")).strip()
    行 = [r for r in 入力.get("支給控除の項目") or ()
         if str(r.get("会社", "")).strip() == 会社 and str(r.get("割増の基礎から除く訳") or "").strip() == 固定残業の訳]
    値たち = [効く値("割増.固定残業", 入力), *[r.get("割増.固定残業") for r in 入力.get("人") or ()]]
    額で = any(str(読み(v) or "").startswith("額で") for v in 値たち)
    if 額で and not 行:
        return [f"割増.固定残業＝額で なのに ④支給控除の項目 に 割増の基礎から除く訳＝{固定残業の訳} の行が無い"
                "（額は ④ の行と ② の人の額の 1 か所）"]
    if 行 and not 額で:
        return [f"④支給控除の項目 に 割増の基礎から除く訳＝{固定残業の訳} の行（{'・'.join(str(r.get('項目', '')) for r in 行)}）が"
                "あるのに 割増.固定残業 が 額で でない（形を 額で にするか行を消す）"]
    return []


def 止める訳(入力: dict) -> list[str]:
    辞書 = _辞書()
    out = []
    for r in 段.行たち(入力.get("事務所") or ()):
        名 = str(r.get("項目", "")).strip()
        if 名:
            x = _名と値を照らす("事務所の設定「既定」の", 名, r.get("今の値"), 辞書)
            if x:
                out.append(x)
    for 名, v in (入力.get("会社の値") or {}).items():
        x = _名と値を照らす("会社の値の", str(名).strip(), v["値"] if isinstance(v, dict) else v, 辞書)
        if x:
            out.append(x)
    out += _mdの知らない鍵(入力.get("事務所のルール") or "")
    out += _つなぎの誤り(入力)
    out += _固定残業の誤り(入力)
    return out


def 集める(入力: dict) -> dict:
    辞書 = _辞書()
    表 = 設定.表()
    会社の値 = 入力.get("会社の値") or {}
    事務所の値 = _事務所の値(入力)
    揃った, 事務所へ, 会社へ, 待ち = [], [], [], []
    for 名 in 集める名():
        it = 辞書.get(名)
        if it is None:   # 芯の表に在り項目の辞書に無い名（型の版で辞書へ入れる）: 事務所の既定の候補として回す
            if 名 in 事務所の値 or 名 in 会社の値:
                揃った.append(名)
            else:
                事務所へ.append({"鍵": 名, "既定の候補": 表[名].get("見当"), "法の根拠": "",
                              "辞書に無い": True})
            continue
        if it.get("集め方") == "法の既定":
            continue
        if 名 in 事務所の値 or 名 in 会社の値 or _下の段で揃う(it, 入力):
            揃った.append(名)
            continue
        要る = 要るか(it, 入力)
        if 要る is None:
            待ち.append({"鍵": 名, "条件の項目": it["要る時"]["項目"]})
            continue
        if not 要る:
            continue
        if it["集め方"] == "会社に聞く":
            会社へ.append(名)
        else:
            候補 = it.get("既定", 表.get(名, {}).get("見当"))
            事務所へ.append({"鍵": 名, "既定の候補": 候補, "法の根拠": "" if it.get("法の線") in (None, "—") else it["法の線"]})
    訳 = 止める訳(入力)
    return {"揃った": 揃った, "事務所の既定へ": 事務所へ, "会社に聞く": 会社へ, "条件待ち": 待ち,
            "止める": bool(訳), "止めた訳": 訳}
