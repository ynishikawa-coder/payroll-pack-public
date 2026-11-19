"""型の正本（型.json・項目.json・雛形/）を読む口。寄せる道具・始める道具・殻はここから今の型を引く。

  python3 初期設定/型の口.py 見出し      # 全部のシート×タブの見出しの並び（JSON）
  python3 初期設定/型の口.py md          # md の雛形 4 枚の見出しの並び（JSON）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent
if str(ここ.parent) not in sys.path:   # 支給月の字の正本（芯/支給月の字.py）を読む
    sys.path.insert(0, str(ここ.parent))
from 芯 import 支給月の字  # noqa: E402


def 型() -> dict:
    return json.loads((ここ / "型.json").read_text(encoding="utf-8"))


def 版() -> int:
    return 型()["版"]


def 項目たち() -> list[dict]:
    return json.loads((ここ / "項目.json").read_text(encoding="utf-8"))["項目"]


def 項目(名: str) -> dict:
    for it in 項目たち():
        if it["項目"] == 名:
            return it
    raise KeyError(名)


def 列になる項目(段: str, 辞書: list[dict] | None = None) -> list[dict]:
    """その段に置ける 1 つの値の項目（仕組みだけの項目・行の束・優先 B を除く）を辞書の順に。
    辞書を渡せばその辞書から（寄せる道具が型の file を指して読む時）、無ければ 初期設定/項目.json から。"""
    return [it for it in (項目たち() if 辞書 is None else 辞書)
            if 段 in it["段"] and "置く所" not in it and not it.get("優先B")]


def タブの列(t: dict, 辞書: list[dict] | None = None) -> list[dict]:
    """型.json のタブ 1 つ → 列の名と意味の並び（「列」の後ろに「項目の列」を広げる）。列を広げる決まりはここ 1 か所。"""
    out = [dict(c) for c in t.get("列", [])]
    if t.get("項目の列"):
        out += [{"名": it["項目"], "意味": it.get("意味", "")} for it in 列になる項目(t["項目の列"], 辞書)]
    return out


def タブ(シート: str, タブ名: str) -> dict:
    for s in 型()["シート"]:
        if s["シート"] == シート:
            for t in s["タブ"]:
                if t["タブ"] == タブ名:
                    return t
    raise KeyError(f"{シート}/{タブ名}")


def 列(シート: str, タブ名: str) -> list[dict]:
    """列の名と意味の並び（項目の列を広げた後）。"""
    return タブの列(タブ(シート, タブ名))


def 見出し(シート: str, タブ名: str) -> list[str]:
    return [c["名"] for c in 列(シート, タブ名)]


def 全部の見出し() -> dict[str, list[str]]:
    return {f'{s["シート"]}/{t["タブ"]}': 見出し(s["シート"], t["タブ"]) for s in 型()["シート"] for t in s["タブ"]}


def 雛形(名: str) -> str:
    for m in 型()["md の雛形"]:
        if m["名"] == 名:
            return (ここ / m["雛形"]).read_text(encoding="utf-8")
    raise KeyError(名)


def md_の見出し(名: str) -> list[str]:
    return [l for l in 雛形(名).splitlines() if l.startswith("#")]


def 全部の_md_の見出し() -> dict[str, list[str]]:
    return {m["名"]: md_の見出し(m["名"]) for m in 型()["md の雛形"]}


def 見出しの違い(シート: str, タブ名: str, 今の見出し: list[str]) -> list[str]:
    """Drive のシートの 1 行目と型の見出しを照らし、違いを 1 行ずつ返す（無ければ []）。"""
    型の = 見出し(シート, タブ名)
    if 今の見出し == 型の:
        return []
    out = [f"無い列: {c}" for c in 型の if c not in 今の見出し]
    out += [f"型に無い列: {c}" for c in 今の見出し if c not in 型の]
    if not out:
        out.append("列の並びが型と違う")
    return out


def 事務所の質問と回答() -> dict:
    """事務所全体の問いの 質問と回答 の型（型.json の 質問と回答 の「事務所」）→ {ファイル, タブ, 会社, 見出し}。
    列・並びは会社の 質問と回答 と同じ 1 つの型（写さない）。ファイルは事務所の根からの名（00_事務所/質問と回答）。"""
    for s in 型()["シート"]:
        if s["シート"] == "質問と回答":
            事 = s.get("事務所")
            if not isinstance(事, dict) or not 事.get("置き場") or not 事.get("会社") or len(s["タブ"]) != 1:
                raise ValueError("型.json の 質問と回答 に 事務所（置き場・会社）が無い・タブが 1 つでない")
            t = s["タブ"][0]
            return {"ファイル": f'{事["置き場"]}/{s["シート"]}', "タブ": t["タブ"], "会社": 事["会社"],
                    "見出し": [c["名"] for c in タブの列(t)]}
    raise KeyError("質問と回答")


# ── 質問と回答の 問いの番号（作る所・読む所の 1 か所） ─────────────────
# 正本は 型.json の 質問と回答「問いの番号」の意味＝`Q<支給年月>-<2 桁の順>`（例 Q202612-01）。
# 前の形の番号（ある事務所の前の道具の形）は読まない＝今の形へ書き直すのは事務所の前の形の読み替え（寄せる道具.md・入れてよい物.md §1）。
_問いの番号の形 = re.compile(r"Q(\d{4})(\d{2})-(\d+)")


def _比べる月(支給月: str) -> str:
    """支給月の字 → 比べる字 `YYYY.MM`（正本 芯/支給月の字.py）。読めなければ止める。"""
    x = 支給月の字.そろえる(支給月, "比べる")
    if x is None:
        raise ValueError(f"支給月 {支給月!r} から年月が読めない（YYYY.MM支給）")
    return x


def 問いの番号(支給月: str, 順: int) -> str:
    """支給月（`YYYY.MM支給`・`YYYY.MM`・`YYYY-MM`）と順 → 問いの番号 `QYYYYMM-NN`（型の形）。"""
    return f"Q{_比べる月(支給月).replace('.', '')}-{int(順):02d}"


def 問いの番号を読む(字) -> tuple[str, int] | None:
    """問いの番号の字 → (`YYYY.MM`, 順)。型の形 `Q202612-01` だけを読む。読めなければ None。"""
    m = _問いの番号の形.fullmatch(str(字 or "").strip())
    月 = 支給月の字.そろえる(f"{m.group(1)}.{m.group(2)}", "比べる") if m else None
    return (月, int(m.group(3))) if 月 else None


def 次の問いの番号(行たち, 支給月: str) -> int:
    """質問と回答の行（既にある行）のうち同じ支給年月の問いの番号の一番大きい順＋1（無ければ 1）。"""
    月 = _比べる月(支給月)
    順たち = [x[1] for r in 行たち or () if (x := 問いの番号を読む((r or {}).get("問いの番号"))) and x[0] == 月]
    return max(順たち, default=0) + 1


# ── 書き方（台帳・マスタ・出力・管理表へ値を書く時の 1 か所） ─────────────
# 書く手順の 書き方: 字のまま＝Sheets の valueInputOption=RAW（字を数・日付・時刻・式に読ませない）。
# 殻の書く口に RAW を選ぶ所が無く、いつも入力扱い（USER_ENTERED）になる時は、`入力扱いでも字のまま` で字の頭に ' を付けて渡す
# （入力扱いの ' は「字として入れる」の印で、セルの値に残らない＝RAW で書いた時と同じ値になる）。書いた後は `書いた値を照らす` で読み直して照らす。
字のまま = "RAW"
入力扱い = "USER_ENTERED"


def 入力扱いでも字のまま(格子) -> list[list]:
    """値の格子（行の並び）→ 入力扱いの書く口で書いても RAW と同じ値になる格子。空でない字の頭に ' を付ける（数〔int・Decimal〕は数のまま）。"""
    return [[("'" + v) if isinstance(v, str) and v != "" else v for v in 行] for 行 in 格子 or ()]


def 入力扱いの手順(手順たち) -> list[dict]:
    """書く手順（`値を書く`・`行を足す` の 書き方＝RAW）→ 入力扱いの書く口へ当てる手順（値の字の頭に '・書き方＝USER_ENTERED）。
    ほかの手順（file を移す・タブを足す など）はそのまま。"""
    out = []
    for x in 手順たち or ():
        if isinstance(x, dict) and x.get("書き方") == 字のまま and isinstance(x.get("値"), list):
            x = {**x, "値": 入力扱いでも字のまま(x["値"]), "書き方": 入力扱い}
        out.append(x)
    return out


def _同じ数(v, w) -> bool:
    from decimal import Decimal, InvalidOperation
    try:
        return Decimal(str(v)) == Decimal(str(w).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return False


def 書いた値を照らす(書いた格子, 読み直した格子) -> list[str]:
    """書いた値（字のままの格子）と、書いた後に読み直した値（表示の字）の違う所 → ["<行>行<列>列: 書いた「…」・読んだ「…」"]。
    空でない時は止める（数・日付・時刻に読まれた＝頭の 0 が落ちた・2027/2/3 が日付の数になった など）。字で書いた値は字で、
    数（int・Decimal）で書いた値は数で比べる（12.50 と 12.5 は同じ・字の "0001" と "1" は違う）。"""
    def 字(v):
        if v is None:
            return ""
        s = str(v)
        return s[1:] if s.startswith("'") else s
    違う = []
    読 = [list(r) for r in 読み直した格子 or ()]
    for i, 行 in enumerate(書いた格子 or ()):
        for j, v in enumerate(行):
            w = 読[i][j] if i < len(読) and j < len(読[i]) else ""
            if not isinstance(v, str) and v is not None and _同じ数(v, w):   # 数で書いた値は数で比べる（12.50 と 12.5）
                continue
            if 字(v).strip() != 字(w).strip():
                違う.append(f"{i + 1}行{j + 1}列: 書いた「{字(v)}」・読んだ「{字(w)}」")
    return 違う


# ── 質問と回答の 回答（読む所の 1 か所。設問の照らしと入口の文脈が使う） ─────────────
def 答えの芯(回答) -> str:
    """回答 の字（確認ページの 貼り戻し の形「答え ／ 補足: … ／ 受付: …（版 …）」）→ 答えの語だけ。"""
    芯 = re.split(r" ／ (?:補足|受付):", str(回答 or ""))[0].strip()
    return "" if 芯.startswith(("補足:", "受付:")) else 芯   # ひとことだけの答え＝まだ答えの無い問いと同じ


def 今の問いの行たち(行たち) -> list[dict]:
    """問いの番号ごとに一番下の行だけ（確認ページを送り直した答えは新しい行で足す＝下の行が正）。行たち は dict の並び。"""
    今: dict = {}
    for q in 行たち or ():
        今[(str(q.get("会社", "")).strip(), str(q.get("問いの番号", "")).strip())] = q
    return list(今.values())


if __name__ == "__main__":
    何 = sys.argv[1] if len(sys.argv) > 1 else "見出し"
    out = 全部の見出し() if 何 == "見出し" else 全部の_md_の見出し()
    json.dump({"版": 版(), 何: out}, sys.stdout, ensure_ascii=False, indent=1)
    print()
