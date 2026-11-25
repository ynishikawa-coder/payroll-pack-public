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


# ── 勤怠の行の 原本の種別（正本は 型.json の「原本の種別」） ─────────
# 入口（入口/口.py）・台帳の形（月次/台帳の形.py の _原本の在り処）・殻の照らし（月次/台帳へ書く.py）はここから読み、種別の値を写さない。

def 原本の種別たち() -> dict[str, str]:
    """{原本の種別: 種類}。種類は ファイル（1_届いた物 の file＝原本の名前と在り処が要る）か 所定どおり（file が無い＝出所はマスタの所定）。"""
    return dict(型()["原本の種別"]["種類"])


def 原本の種類(種別: str) -> str:
    """原本の種別 → 種類（ファイル／所定どおり）。型に無い種別は KeyError（黙って通さない）。"""
    種類たち = 原本の種別たち()
    if 種別 not in 種類たち:
        raise KeyError(f"原本の種別「{種別}」は型に無い（{'・'.join(種類たち)} のどれか）")
    return 種類たち[種別]


# ── Drive の木と名の形（正本は 型.json の「木」「名の形」・シートの「役」・md の雛形の「役」） ─────────
# 道具はフォルダ・シート・md の名を直に書かず、役の名でここから引く（tests/test_名を直に書かない.py が拒む）。

def 木() -> dict:
    return 型()["木"]


def シートの型(役: str) -> dict:
    """役（マスタ・台帳・質問と回答・事務所の設定）→ 型.json のシート 1 つ。"""
    for s in 型()["シート"]:
        if s.get("役") == 役:
            return s
    raise KeyError(f"型.json に役 {役} のシートが無い")


def 名(役: str) -> str:
    """役 → Drive の名（木の名・シートの名・md の名。木の道（例 会社の根）は / でつなぐ）。無い役は KeyError。"""
    t = 型()
    if 役 in t["木"]["名"]:
        return t["木"]["名"][役]
    if isinstance(t["木"].get(役), list) and all(isinstance(x, str) for x in t["木"][役]) and 役 == "会社の根":
        return "/".join(名(x) for x in t["木"][役])
    for s in t["シート"]:
        if s.get("役") == 役:
            return s["シート"]
    for m in t["md の雛形"]:
        if m.get("役") == 役:
            return m["名"]
    raise KeyError(f"型.json の木に役 {役} が無い")


def 道(*役たち: str) -> str:
    """役の並び → / でつないだ道（例 道("会社の根", "確認事項") → 10_会社/<組>/8_確認事項）。"""
    return "/".join(名(x) for x in 役たち)


def 物たち(鍵: str) -> tuple[str, ...]:
    """木の物の並び（事務所の物・会社の根の物・決まりの物・月の物）→ 名の並び。"""
    return tuple(名(x) for x in 木()[鍵])


def 置き場の物() -> tuple[str, ...]:
    """事務所の設定「置き場」タブの列「物」に書ける字（会社の根 は字のまま・ほかは木の名）。"""
    return tuple(x if x == "会社の根" else 名(x) for x in 木()["置き場の物"])


def 組の印() -> str:
    return 名("組")


def 台帳の名(年: int | str | None = None) -> str:
    """年の台帳の名（型の名は `台帳_<支給年>`・年を渡せばその年の名）。"""
    n = 名("台帳")
    return n if 年 is None else n.replace("<支給年>", str(年))


def 台帳の名か(x: str) -> bool:
    頭, _, 尾 = 名("台帳").partition("<支給年>")
    return re.fullmatch(re.escape(頭) + r"\d{4}" + re.escape(尾), x) is not None


def 名の形(鍵: str) -> dict:
    """名の形（月・台帳・出す物・確認事項）→ {形, 支給月の字?, …}。"""
    return 型()["名の形"][鍵]


def 出す物たち() -> tuple[str, ...]:
    return tuple(名の形("出す物")["物"])


def 確認事項の置き場の表() -> dict[str, tuple[str, str]]:
    """確認事項のページの置き場と前の版の置き場 → {"<組>": (置き場/, 前の版/), "事務所": (…)}（フォルダは / で終わる）。"""
    return {k: (道(*v["置き場"]) + "/", 道(*v["前の版"]) + "/") for k, v in 木()["確認事項の置き場"].items()}


def 事務所の質問と回答() -> dict:
    """事務所全体の問いの 質問と回答 の型（型.json の 質問と回答 の「事務所」）→ {ファイル, タブ, 会社, 見出し}。
    列・並びは会社の 質問と回答 と同じ 1 つの型（写さない）。ファイルは事務所の根からの名（00_事務所/質問と回答）。"""
    for s in 型()["シート"]:
        if s.get("役") == "質問と回答":
            事 = s.get("事務所")
            if not isinstance(事, dict) or not 事.get("置き場") or not 事.get("会社") or len(s["タブ"]) != 1:
                raise ValueError("型.json の 質問と回答 に 事務所（置き場・会社）が無い・タブが 1 つでない")
            t = s["タブ"][0]
            return {"ファイル": f'{事["置き場"]}/{s["シート"]}', "タブ": t["タブ"], "会社": 事["会社"],
                    "見出し": [c["名"] for c in タブの列(t)]}
    raise KeyError("型.json に役 質問と回答 のシートが無い")


# ── 質問と回答の 問いの番号（作る所・読む所の 1 か所） ─────────────────
# 正本は 型.json の 質問と回答「問いの番号」の意味＝`Q<支給年月>-<2 桁の順>`（例 Q202612-01）。
# 前の形の番号（ある事務所の前の道具の形）は読まない＝今の形へ書き直すのは事務所の前の形の読み替え（寄せる道具.md・入れてよい物.md §1）。
問いの番号の形 = re.compile(r"Q(\d{4})(\d{2})-(\d+)")


def 問いの相手() -> str:
    """質問と回答「誰に」の字（正本は 型.json の 決まった値）。問いの相手はいつも事務所の担当者 1 人＝道具はこの字だけを書く。"""
    for c in タブ(名("質問と回答"), "質問")["列"]:
        if c["名"] == "誰に":
            return c["決まった値"]
    raise KeyError("質問と回答/質問 の 誰に")


def 問いの相手を当てる(種: dict) -> str:
    """問いの種 → 書く「誰に」の字。種が別の相手（先方 など）を名乗れば止める＝事務所の担当者のほかへ聞く問いを作らない。"""
    相手 = 問いの相手()
    名乗り = 種.get("誰に")
    if 名乗り not in (None, "", 相手):
        raise ValueError(f"問いの相手は {相手} だけ（種の 誰に={名乗り!r}）。事務所の担当者のほかへ聞く問いは作らない")
    return 相手

def 問いの列(列名: str) -> dict:
    """質問と回答「質問」の列の型（既定・選べる値・頭 などの正本は 型.json）。"""
    for c in タブ(名("質問と回答"), "質問")["列"]:
        if c["名"] == 列名:
            return c
    raise KeyError(f"質問と回答/質問 の {列名}")


def 拠り所の頭たち() -> dict[str, bool]:
    """見当の拠り所 の頭 → 見込みか（担当者へ見込みとして見せてよいか）。正本は 型.json の 頭。"""
    return {h["頭"]: bool(h["見込み"]) for h in 問いの列("見当の拠り所")["頭"]}


def 拠り所の頭(字) -> str | None:
    """見当の拠り所 の字（頭 か 頭（中身））→ 頭。空は 既定 の頭。型に無い頭は None。"""
    w = str(字 if 字 is not None else "").strip()
    if not w:
        return 問いの列("見当の拠り所")["既定"]
    頭 = w.split("（", 1)[0] if w.endswith("）") and "（" in w else w
    return 頭 if 頭 in 拠り所の頭たち() else None


def 見込みの拠り所か(字) -> bool:
    """見込みを担当者へ見せてよい拠り所か。型に無い頭は見せない（見込みと読まない）。"""
    頭 = 拠り所の頭(字)
    return 頭 is not None and 拠り所の頭たち()[頭]


def 拠り所に直す(字, 頭: str = "既定") -> str:
    """型の頭で始まらない拠り所の字（芯・入口の理由の文）→ 頭（字）。型の頭で始まる字と空はそのまま。
    頭は型の頭のどれか（既定は 既定＝見込みでない＝見せない）。"""
    if 頭 not in 拠り所の頭たち():
        raise ValueError(f"見当の拠り所 の頭 {頭!r} は型に無い（{'・'.join(拠り所の頭たち())}）")
    w = str(字 if 字 is not None else "").strip()
    return w if not w or 拠り所の頭(w) is not None else f"{頭}（{w}）"


def 反映済みを読む(v) -> bool | None:
    """反映済み の欄の字 → True（済）／False（まだ）／None（読めない）。選べる値・同じに読む字・日付は 型.json の 反映済み の列。"""
    c = 問いの列("反映済み")
    w = re.sub(r"[\s　]", "", str(v if v is not None else ""))
    w = c.get("同じに読む字", {}).get(w, w)
    if re.fullmatch(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", w):
        w = c["日付は"]
    if w not in c["選べる値"]:
        return None
    return w != c["既定"]


def 反映済みの書き方() -> str:
    """反映済み に書ける字の並び（読めない時の知らせに使う）。"""
    c = 問いの列("反映済み")
    return "・".join(dict.fromkeys(x or "空" for x in [*c["選べる値"], *c.get("同じに読む字", {})])) + "・日付"


def 問いの行(**値) -> dict:
    """質問と回答「質問」の 1 行。見出しの外の鍵は拒む。渡さない・空の列は型の 既定（無ければ空）。
    誰に は 問いの相手を当てる、見当の拠り所 は型の頭、反映済み は選べる値で照らす（外れは ValueError）。"""
    見 = 見出し(名("質問と回答"), "質問")
    外 = [k for k in 値 if k not in 見]
    if 外:
        raise ValueError(f"質問と回答/質問 に無い列: {外}")
    行 = {}
    for k in 見:
        v = 値.get(k)
        行[k] = 問いの列(k).get("既定", "") if v is None or v == "" else v
    行["誰に"] = 問いの相手を当てる(値)
    if 拠り所の頭(行["見当の拠り所"]) is None:
        raise ValueError(f"見当の拠り所 {行['見当の拠り所']!r} の頭が型に無い（{'・'.join(拠り所の頭たち())}）")
    if 反映済みを読む(行["反映済み"]) is None:
        raise ValueError(f"反映済み {行['反映済み']!r} は読めない（{反映済みの書き方()}）")
    return 行


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
    m = 問いの番号の形.fullmatch(str(字 or "").strip())
    月 = 支給月の字.そろえる(f"{m.group(1)}.{m.group(2)}", "比べる") if m else None
    return (月, int(m.group(3))) if 月 else None


def 格子を行へ(表) -> list[dict]:
    """列名の dict の並びか、get_values の形（1 行目が見出しの格子）を dict の並びに（読み方の正本・段の解決.行たち もこれを呼ぶ）。"""
    表 = list(表 or [])
    if 表 and isinstance(表[0], (list, tuple)):
        見出し = [str(c) for c in 表[0]]
        return [{c: (r[i] if i < len(r) else "") for i, c in enumerate(見出し)} for r in 表[1:]]
    return [dict(r) for r in 表]


def 既にある行を確かめる(行たち) -> list[dict]:
    """質問と回答の今の行（`既にある`）を受ける 1 か所 → dict の行の並び。行が無ければ空の並び `[]` を渡す。
    省く・None・1 つの字・dict・使い切る並び（generator）・dict でも格子の行でもない行は止める＝既にある問いを見ずに
    番号を 01 から振り直す・答え済みの問いを出し直すことをしない（`次の問いの番号`・`設問.まとめる`・`設問.型ごとの網` が読む）。"""
    if not isinstance(行たち, (list, tuple)):   # None・字・dict・使い切る並び（generator）も止める
        raise ValueError(f"既にある（質問と回答の行）を行の並びで渡す（行が無ければ []）。渡さないと既にある問いを見られない"
                         f"＝番号を振らない・問いを出さない（受けた物: {行たち!r}）")
    格子 = bool(行たち) and isinstance(行たち[0], (list, tuple))
    if any(not isinstance(r, (list, tuple) if 格子 else dict) for r in 行たち[1 if 格子 else 0:]):
        raise ValueError("既にある（質問と回答の行）の行は列名の dict か、1 行目が見出しの格子で渡す")
    return 格子を行へ(行たち)


def 次の問いの番号(行たち, 支給月: str) -> int:
    """質問と回答の行（既にある行）のうち同じ支給年月の問いの番号の一番大きい順＋1（無ければ 1）。
    行たちは必ず渡す（行が無ければ空の並び `[]`）。行は列名の dict か、1 行目が見出しの格子（`格子を行へ` で読む）。
    省く・None・1 つの字・dict・使い切る並び・dict でも格子の行でもない行は止める＝既にある番号を見ずに
    黙って 01 から振らない（同じ番号は送り直しの行と読まれる。出す物の版の番号〔出口/名と版〕と同じ根・2026-11-19）。"""
    行たち = 既にある行を確かめる(行たち)
    月 = _比べる月(支給月)
    順たち = [x[1] for r in 行たち if (x := 問いの番号を読む((r or {}).get("問いの番号"))) and x[0] == 月]
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


def 名つきの木() -> dict:
    """人が読む木（文書が写さず指す物）: 事務所の根・会社の根・月の置き場の名の並びと、名の形・確認事項の置き場。どれも 型.json から組む。"""
    月 = 名の形("月")["形"]
    return {
        "事務所の根": {名("事務所"): list(物たち("事務所の物")), 道("会社の根"): "会社の根"},
        "会社の根": {道("会社の根"): [台帳の名() if x == "台帳" else 名(x) for x in 木()["会社の根の物"]]},
        "月の置き場": {f"{道('会社の根', '月ごと')}/{月}": list(物たち("月の物"))},
        "決まりの置き場": {道("会社の根", "決まり"): list(物たち("決まりの物"))},
        "確認事項の置き場": {k: {"置き場": v[0], "前の版": v[1]} for k, v in 確認事項の置き場の表().items()},
        "名の形": {k: v.get("形") for k, v in 型()["名の形"].items() if isinstance(v, dict) and v.get("形")},
        "シートのタブ": {s["シート"]: [t["タブ"] for t in s["タブ"]] for s in 型()["シート"]},
    }


def 原本の箱の道(組: str) -> str:
    """受け取った原本の箱（先方から届いた原本・書類を置くフォルダ）の道の形 `10_会社/<組>/3_月ごと/<月>/1_届いた物`
    （名は 型.json の木）。<月> は月のフォルダの名（支給月の字の 置き場 の形）。"""
    return "/".join([道("会社の根", "月ごと").replace(組の印(), 組), "<月>", 名("届いた物")])


def 原本の箱か(置き場, 組: str) -> bool:
    """置き場（file の入ったフォルダの道）が、この組の受け取った原本の箱（どれかの月の 1_届いた物）か。
    こちらで作った物の置き場（2_出す物・台帳・マスタ・確認事項・決まり）・ほかの組・月の名の形でない物は False。"""
    頭, 尻 = 原本の箱の道(組).split("<月>")
    v = str(置き場 or "").strip().strip("/")
    if not (組 and v.startswith(頭) and v.endswith(尻)):
        return False
    return 支給月の字.置き場の字を読む(v[len(頭):len(v) - len(尻)]) is not None


if __name__ == "__main__":
    何 = sys.argv[1] if len(sys.argv) > 1 else "見出し"
    out = 全部の見出し() if 何 == "見出し" else 名つきの木() if 何 == "木" else 全部の_md_の見出し()
    json.dump({"版": 版(), 何: out}, sys.stdout, ensure_ascii=False, indent=1)
    print()
