"""例の確かめ: 月の計算の前に、その会社の決まりの「例」を全部、今のマスタの値で芯に通して照らす（月次/README.md「例の確かめ」）。

決まりは 給与のルール.md（AI が書き、AI が読む。人は読まない）と 2_マスタ（計算が読む）に書かれる。2 つが同じ事を言っているかは、
マスタの欄が埋まったか・字が選べる値かを見るだけでは分からない（選べる値の中で取り違えた値は、どの照らしも通る）。
そこで 給与のルール.md の決まりごと（`### <決まりの名>`）に、文の下へ「この打刻ならこう数える」の例の表を置く。
AI がその例を人の言葉にして事務所の担当者に確かめてもらい、確かめた日と、確かめた人に答えた人の名（かオーナーの決定）と
その確かめの出所（確認ページの答えの受付番号・決定DB の行・回答のある問いの番号・過去の結果の照らし）を `名（出所）` の形で書く。
`MDから例を読む` が表を例の行（1 行＝dict）にし、この口（`確かめる`）が例を今のマスタの値で芯/集計（と期間は入口の文脈）に
通し、次のどれかが 1 つでもあれば その会社の月を通さない:

  - 例が 1 つも無い
  - 例の期待と芯の数えが合わない（取り違え・書けていない決まり）
  - 事務所が確かめた日の無い例（AI の取り違えは例にも同じに入る＝人が確かめる所はここ 1 か所）
  - 確かめた人が空か、確かめの出所が付いていない例（AI が自分で確かめたと書いて、人が読んでいない数え方で給与が出るのを
    防ぐ。誰が答えてもよい＝名簿は置かない〔2026-11-19 オーナーの決定〕。出所の形は `確かめた人を読む`）
  - `書けない` の例（マスタに書けない決まり＝芯が決まりどおりに数えられない。読めない MD の表・行も `書けない` の行になる）
  - 読めない例（字の誤り）

返す物: {"通った": bool, "数": 例の数, "合わない": [{"例の番号", "訳"}], "止め": [訳]}
（`月次.月を回す`・`月次.賞与を回す` が 通った でなければ、その会社の全員を関所で外す＝出口へ出さない）。

例は決まりの文から作る（過去の給与ソフトの答えからは作らない）。答え合わせではない: 照らす相手は確かめた例。例の確かめの出所に
過去の結果の照らし（人×項目の一致）を書いてよいが、一致は月次では見ない（道具/答え合わせ の 出所を見る が照らしの結果で確かめる）。
芯・入口・初期設定の部品は呼ぶだけ（中身を変えない）。Drive を開かない（MD の字は殻が読んで渡す）。
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import unicodedata
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

例の列 = ("会社", "例の番号", "決まり", "種類", "支給月", "勤務の型", "人の値", "日付", "日の種類", "区間", "期待",
        "確かめた日", "確かめた人", "備考")
# 書いても書かなくてもよい列（前の例の表・MD の表に無くても読める）。`印` は表 A の印（入口/口.py の 印たち の語を読点で）を
# 例の日へ渡す＝原本の印で数え方の変わる決まり（定時扱い・早退＝終業前の退勤を延ばさない）を例で確かめる
任意の列 = ("印",)
種類たち = ("日", "月", "書けない")
# 種類＝日 の期待に書ける語のうち、芯/集計 の行でなく 日の要約 から引く語（その日の休憩と労働）
日の要約の語 = ("休憩", "労働")
月の語 = ("締めの始め", "締めの終わり")
_日の種類 = ("勤務", "休日勤務", "休暇", "欠勤", "休日")
_仮の人 = "例"
_根 = Path(__file__).resolve().parent.parent
if str(_根) not in sys.path:   # 支給月の字の正本（芯/支給月の字.py）を読む
    sys.path.insert(0, str(_根))
from 芯 import 支給月の字  # noqa: E402


class 例の誤り(ValueError):
    pass


def _字(v) -> str:
    return str(v if v is not None else "").strip()


def _対(字: str) -> list[tuple[str, str]]:
    """`名=値・名=値`（＝・、・改行でも）→ [(名, 値)]。区切りは次に `名=` が続く所だけ＝値の中の ・ や 、
    （休憩の表 `5:59超30分、8:00超60分`・`入れない・時間外の率で払う`）は値のまま読む。"""
    out = []
    for x in re.split(r"[・、,;\n]\s*(?=[^・、,;\n=＝]+[=＝])", 字 or ""):
        x = x.strip()
        if not x:
            continue
        m = re.match(r"^(.+?)\s*[=＝]\s*(.*)$", x)
        if not m:
            raise 例の誤り(f"「{x}」は 名=値 の形でない")
        out.append((m.group(1).strip(), m.group(2).strip()))
    return out


def _時刻(v: str) -> str:
    m = re.match(r"^(\d{1,2})[:：](\d{2})$", v.strip())
    if not m:
        raise 例の誤り(f"時刻「{v}」は h:mm でない")
    return f"{int(m.group(1))}:{m.group(2)}"


def _区間(字: str) -> list[tuple[str, str, str]]:
    """`労働 8:50-18:16、休憩 12:00-13:00`（種別を省けば労働）→ [(種別, 始め, 終わり)]。"""
    out = []
    for x in re.split(r"[、,\n]", 字 or ""):
        x = x.strip()
        if not x:
            continue
        m = re.match(r"^(?:(労働|休憩|外出)\s*)?(\S+?)\s*[-〜～~]\s*(\S+)$", x)
        if not m:
            raise 例の誤り(f"区間「{x}」は <労働|休憩|外出> h:mm-h:mm の形でない")
        out.append((m.group(1) or "労働", _時刻(m.group(2)), _時刻(m.group(3))))
    return out


def _期待の値(名: str, v: str):
    """h:mm → 分。数 → そのまま（日数など）。日付 → 字。"""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        return v
    m = re.match(r"^(\d+)[:：](\d{2})$", v)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    try:
        x = float(v)
    except ValueError:
        raise 例の誤り(f"期待「{名}={v}」の値が h:mm・数・日付のどれでもない") from None
    return int(x) if x == int(x) else x


def _見せる(名: str, v) -> str:
    if isinstance(v, int) and 名 not in ("出勤日数", "所定日数", "欠勤") and not 名.endswith("日数") and not 名.endswith("回数"):
        return f"{v // 60}:{v % 60:02d}"
    return "空" if v is None else str(v)


def 行たち(表) -> list[dict]:
    """get_values の形（1 行目が見出し）か列名の dict の並び → dict の並び。"""
    表 = list(表 or ())
    if 表 and isinstance(表[0], (list, tuple)):
        見出し = [_字(h) for h in 表[0]]
        return [{h: (r[i] if i < len(r) else "") for i, h in enumerate(見出し)} for r in 表[1:]
                if any(_字(c) for c in r)]
    return [dict(r) for r in 表]


# --- 給与のルール.md の例の表を読む（形の約束: 決まりごとに `### <決まりの名>`・文・その下に例の表） ---

MDの例の列 = tuple(c for c in 例の列 if c != "会社")   # MD の表の列（会社は MDから例を読む の引数で埋める）。任意の列 は在れば読む
読めない印 = "給与のルール.md の例の表が読めない"   # 読めない表・行は 種類＝書けない の行にし、備考の頭にこの印を置く


def _表の行か(行: str) -> bool:
    return 行.lstrip().startswith("|")


def _升(行: str) -> list[str]:
    """`| a | b |` → ["a", "b"]（`\\|` は升の中の | として読む）。"""
    s = 行.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") and not s.endswith("\\|") else s
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def _区切りの行か(升: list[str]) -> bool:
    return bool(升) and all(re.fullmatch(r":?-{3,}:?", c) for c in 升)


def MDから例を読む(字: str, 会社: str) -> list[dict]:
    """給与のルール.md の字 → 例の行の並び（前のマスタ「例」の 1 行と同じ鍵の dict・会社 は引数で埋める）。`確かめる` へそのまま渡す。

    読む形: `### <決まりの名>` の見出しの下の Markdown の表。表の列は `MDの例の列`（並びは問わない・足りない列も外の列も
    読めない）。決まり の列には照らすマスタの項目の名（芯/設定の表.json の名）を書き、読んだ行の 決まり は
    `給与のルール.md#<決まりの名>（<決まり の升>）` にする。HTML の注（<!-- -->）とコードの囲みの中は読まない。

    既定は止める側: 次の物は、その表・その行を `種類＝書けない`・`備考＝<読めない印>: <訳>` の行にして返す
    （`確かめる` が会社を出さない）。見出しの外（`###` の下でない）の表／列の欠け・外の列・同じ列が 2 つ／区切りの行の無い表／
    升の数が見出しと違う行。会社 が空なら 例の誤り。"""
    会社 = _字(会社)
    if not 会社:
        raise 例の誤り("MDから例を読む の 会社 が空")
    字 = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), 字 or "", flags=re.S)
    行たち_ = 字.splitlines()
    out: list[dict] = []
    見出し: str | None = None   # 今の `###` の決まりの名（`#`・`##` の見出しで外れる）
    囲み = False
    i = 0

    def 読めない(何行目: int, 訳: str):
        out.append({"会社": 会社, **{c: "" for c in MDの例の列}, "例の番号": f"（給与のルール.md {何行目} 行目）",
                    "決まり": f"給与のルール.md#{見出し}" if 見出し else "（見出しの外）", "種類": "書けない",
                    "備考": f"{読めない印}: {訳}"})

    while i < len(行たち_):
        行 = 行たち_[i]
        if 行.lstrip().startswith(("```", "~~~")):
            囲み = not 囲み
            i += 1
            continue
        if 囲み:
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", 行)
        if m:
            見出し = m.group(2).strip() if len(m.group(1)) == 3 else None
            i += 1
            continue
        if not _表の行か(行):
            i += 1
            continue
        始め = i
        表 = []
        while i < len(行たち_) and _表の行か(行たち_[i]):
            表.append(_升(行たち_[i]))
            i += 1
        if 見出し is None:
            読めない(始め + 1, "表が `### <決まりの名>` の見出しの下に無い（決まりごとの見出しの下に置く）")
            continue
        頭 = 表[0]
        if len(表) < 2 or not _区切りの行か(表[1]) or len(表[1]) != len(頭):
            読めない(始め + 1, "表の 2 行目が見出しと同じ数の区切り（|---|）でない")
            continue
        欠け = [c for c in MDの例の列 if c not in 頭]
        外 = [c for c in 頭 if c not in MDの例の列 + 任意の列]
        二つ = sorted({c for c in 頭 if 頭.count(c) > 1})
        if 欠け or 外 or 二つ:
            訳 = "／".join(x for x in (f"無い列: {'・'.join(欠け)}" if 欠け else "", f"外の列: {'・'.join(外)}" if 外 else "",
                                     f"2 つある列: {'・'.join(二つ)}" if 二つ else "") if x)
            読めない(始め + 1, f"表の列が例の列と違う（{訳}）")
            continue
        for k, 升 in enumerate(表[2:], 始め + 3):
            if len(升) != len(頭):
                読めない(k, f"升の数 {len(升)} が見出しの {len(頭)} と違う")
                continue
            if not any(升):
                continue
            r = dict(zip(頭, 升))
            r["決まり"] = f"給与のルール.md#{見出し}（{r['決まり']}）" if r["決まり"] else f"給与のルール.md#{見出し}"
            out.append({"会社": 会社, **{c: r[c] for c in MDの例の列}, **{c: r[c] for c in 任意の列 if c in r}})
    return out


def _月(支給月: str) -> str:
    """例の 支給月 の字 → パックの中の字 `YYYY-MM`（字は正本 芯/支給月の字.py が組む）。読めなければ 例の誤り。"""
    x = 支給月の字.そろえる(支給月, "中")
    if x is None:
        raise 例の誤り(f"支給月「{支給月}」は YYYY.MM支給 でない")
    return x


def _例の人を足す(段, 会社名: str, タブ: dict, 例: dict) -> tuple[str, dict]:
    """例の人（社員の行 1 つ・勤務の型と人の値は例の値）をタブの社員に足す → (NO, タブ)。"""
    NO = f"{_仮の人}-{_字(例.get('例の番号'))}"
    人の値 = dict(_対(_字(例.get("人の値"))))
    外 = sorted(n for n in 人の値 if n not in _人の段の名())
    if 外:
        raise 例の誤り(f"人の値の {'・'.join(外)} は人の段に置ける項目でない（初期設定/項目.json の 段 に 人 が在る名だけ）")
    行 = {"会社": 会社名, "NO": NO, "氏名": "例", "勤怠の表記": NO, "勤務の型": _字(例.get("勤務の型")),
         "入社日": "2000-01-01", "生年月日": "1980-01-01", **人の値}
    return NO, {**タブ, "社員": [*段.行たち(タブ.get("社員", ())), 行]}


_休暇の列 = ("休暇の種類", "休暇の単位", "休暇の時間")


def _日の種類と休暇(字: str) -> tuple[str, dict]:
    """例の 日の種類 `休暇（年休・全日）`・`勤務（年休・午前半休）`・`休暇（年休・時間・2:00）` → (日の種類, 表 A の休暇の列)。
    括弧の中は 休暇の種類・休暇の単位〔・休暇の時間〕（docs/設計/勤怠の形.md の表 A の字のまま）。空＝勤務。"""
    m = re.match(r"^([^（(]*)(?:[（(](.*)[）)])?$", 字 or "")
    種 = (m.group(1).strip() if m else 字) or "勤務"
    if not m or 種 not in _日の種類:
        raise 例の誤り(f"日の種類「{字}」は {'・'.join(_日の種類)} のどれでもない（休暇は 休暇（年休・全日） の形）")
    中 = [x.strip() for x in re.split(r"[・、,]", m.group(2) or "") if x.strip()]
    if len(中) > len(_休暇の列) or (m.group(2) is not None and len(中) < 2):
        raise 例の誤り(f"日の種類「{字}」の括弧は 休暇の種類・休暇の単位〔・休暇の時間〕")
    return 種, dict(zip(_休暇の列, 中))


def _印(字: str) -> str:
    """例の 印 `早退`・`定時扱い、手で直した`（表 A の印の字のまま・読点で）→ 表 A の 印 の字。知らない語は 例の誤り。"""
    from 入口.口 import 印たち
    from 月次.台帳の形 import 始業から扱い   # 問いの答えでだけ置く印（確定した勤怠の印）も例には書ける
    書ける = (*印たち, 始業から扱い)
    語 = [w.strip() for w in re.split(r"[、,]", 字 or "") if w.strip()]
    外 = [w for w in 語 if w not in 書ける]
    if 外:
        raise 例の誤り(f"印「{'・'.join(外)}」は表 A の印（{'・'.join(書ける)}）のどれでもない")
    return "、".join(語)


def _日の例を数える(段, 支給月: str, 会社名: str, タブ: dict, 例: dict, 法の線: dict) -> dict:
    """種類＝日 の例 1 つを、今のマスタの値で芯/集計に通す → {語: 値}（集計の行と、その日の 休憩・労働）。"""
    from 芯.集計 import 集計する
    NO, タブ = _例の人を足す(段, 会社名, タブ, 例)
    型 = _字(例.get("勤務の型"))
    r = 段.解く(支給月, **タブ)
    決まり = r["決まり"].get((会社名, NO))
    仮 = [_字(q.get("項目")) for q in r.get("仮の値", ()) if _字(q.get("NO")) == NO]
    if 仮:
        raise 例の誤り(f"段の解決が例の人の値を読めない（{'・'.join(仮)}）")
    if 決まり is None:
        raise 例の誤り("段の解決が例の人の決まりを出さない（勤務の型・人の値の名を見る）")
    日付 = _字(例.get("日付"))
    前 = _読める日(日付, "日付")
    種, 休 = _日の種類と休暇(_字(例.get("日の種類")))
    月 = _月(支給月)
    鍵 = {"支給月": 月, "会社": 会社名, "NO": NO, "勤怠の表記": NO}
    A = [{**鍵, "日付": 日付, "日の種類": 種, **休, "勤務の型": 型, "原本の名前": "例", "原本の種別": "Excel出勤簿",
          "読み取りの確かめ": "確認済", "印": _印(_字(例.get("印")))}]
    B = [{**鍵, "日付": 日付, "区間の番号": i, "区間の種別": 種別, "始め": 始, "終わり": 終, "時刻の出所": "打刻"}
         for i, (種別, 始, 終) in enumerate(_区間(_字(例.get("区間"))), 1)]
    # 例の日の前の 7 日は休みの日として前の表 A に置く（例の日だけで週を判定できる＝前の期間の日を受けていない仮にしない。
    # 例は 1 日の決まりを照らす物で、週の法定の例は 1 日の例では書かない）
    前A = [{**鍵, "日付": (前 - timedelta(days=i)).isoformat(), "日の種類": "休日", "勤務の型": 型, "原本の名前": "例",
           "原本の種別": "Excel出勤簿", "読み取りの確かめ": "確認済"} for i in range(7, 0, -1)]
    集 = 集計する(A, B, 決まり={(会社名, NO): 決まり}, 法の線=法の線, 前の表A=前A, 支給月=月)
    out = {}
    for x in 集["行"]:
        if str(x.get("NO")) == NO:
            out[x["項目"]] = None if x.get("状態") == "仮" else x.get("値")
    for x in 集["日の要約"]:
        if str(x.get("NO")) == NO and x.get("日付") == 日付:
            out["休憩"], out["労働"] = x.get("休憩"), x.get("労働")
    out["_仮"] = [q["何が無いか"] for q in 集["問い"]]
    return out


def _月の例を数える(段, 繋, 会社名: str, タブ: dict, 例: dict) -> dict:
    """種類＝月 の例: 例の 支給月 の期間（締めの始め・締めの終わり）を、入口の文脈と同じ式で出す。"""
    月 = _字(例.get("支給月"))
    _月(月)
    _, タブ = _例の人を足す(段, 会社名, タブ, 例)   # 締め日は会社の人の決まりから読む（人の居ない会社でも見当の 末 にしない）
    r = 段.解く(月, **タブ)
    x = 繋.入口の文脈(月, 会社名, r, **{k: v for k, v in タブ.items() if k in ("会社", "勤務の型", "社員", "事務所")})
    return {"締めの始め": x["文脈"]["期間の始め"], "締めの終わり": x["文脈"]["期間の終わり"]}


def _読める日(v: str, 何: str) -> date:
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        raise 例の誤り(f"{何}「{v}」は YYYY-MM-DD でない")
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise 例の誤り(f"{何}「{v}」は無い日") from None


@lru_cache(maxsize=1)
def _人の段の名() -> frozenset:
    d = json.loads((_根 / "初期設定" / "項目.json").read_text(encoding="utf-8"))
    return frozenset(e["項目"] for e in d["項目"] if "人" in (e.get("段") or ()))


@lru_cache(maxsize=1)
def 覆う名() -> frozenset:
    """例で覆う決まり（2026-11-18 オーナーの決定＝勤怠の数え方の決まりは全部）: 芯/設定の表.json で 読む所 に 集計 が在る名。
    人の事実（`人.` の名・`支払.賃金の形`）は決まりでないので外し、締めの例が照らす `支払.締め日` を足す。"""
    from 芯 import 設定
    return frozenset({n for n, e in 設定.表().items() if "集計" in (e.get("読む所") or ())
                      and not n.startswith("人.") and n != "支払.賃金の形"} | {"支払.締め日"})


@lru_cache(maxsize=1)
def 日で見分ける名() -> frozenset:
    """1 日の例で値の取り違えを見分けられる決まり: 芯/集計 が勤務の型ごとに引く名（`.引く("名", 型)`）のうち、
    選べる値の決まった形（選ぶ・端数の語）の物。週・月で効く決まりは 1 日の例では見分けられない（覆いの照らしだけ）。"""
    from 芯 import 設定
    型で引く = 型で引く名(sorted((_根 / "芯" / "集計").glob("*.py")))
    return frozenset(n for n in 型で引く if 設定.表().get(n, {}).get("形") in ("選ぶ", "端数の語")) - _週と期間で効く名


class 引き方が読めない(RuntimeError):
    """芯/集計 の決まりの引き方が、型で引くかを見分けられる形でない（見分けの照らしが黙って減らないよう止める）。"""


def 型で引く名(files, 名たち=None) -> set[str]:
    """芯/集計 の .py を構文で読み、勤務の型で引く決まりの名を返す（名の字の正規表現でなく構文木で読む）。

    引く口 = 芯/集計 で 名 と 型 の 2 つを引数に持つ関数（`決まり.引く`・`決まり.曜日の値` など。定義から拾う）と、
    自分の引数を引く口の名へそのまま渡す包み（`def _引(n, 型): return 決.引く(n, 型)`。引数の名は問わない・
    包みの包みも拾う）。口の呼び出しで、名が字で書かれ、型の位置（位置か名で渡す）に None でない物を渡す物を
    「型で引く」に数える。既定は止める側（書き方を変えると見分けの照らしが黙って減る穴を塞ぐ）:
      - 名が字でない呼び出しは、囲む関数が口として拾われ、その口の名の引数をそのまま渡す時だけ通す。ほかは `引き方が読めない`
      - 包みが型の位置へ自分の引数でも None でもない物を渡す（型で引くかが呼び出しで決まらない）は `引き方が読めない`
      - 引く口が 1 つも見つからない（`引く` の定義が無い）は `引き方が読めない`
    閉じた照らし（呼び方の抜けを 1 つずつ塞ぐのでなく、次の書き方の変化でも黙って減らない）: `名たち`（既定は見分けの
    元＝芯/設定の表.json の 選ぶ・端数の語 で集計が読む名）の字が 芯/集計 のどこかに出たら、その字は口の呼び出しの名として
    数えた物か、事務所の承知の印を読む所（`_承知を読む口`）でなければ `引き方が読めない`。
    口の呼び方: メソッドは `x.名(…)`、関数は `名(…)`・`モジュール.名(…)`・`from … import 名 as 別名` の別名でも照らす。"""
    import ast
    木たち = [ast.parse(Path(f).read_text(encoding="utf-8"), filename=str(f)) for f in files]
    関数 = (ast.FunctionDef, ast.AsyncFunctionDef)

    def 引数(f) -> list[str]:
        out = [a.arg for a in [*f.args.posonlyargs, *f.args.args]]
        return out[1:] if out[:1] in (["self"], ["cls"]) else out

    def 呼び出し(f):
        """f の本文の呼び出し（中の関数の定義の中は除く）。"""
        todo = list(ast.iter_child_nodes(f))
        while todo:
            n = todo.pop()
            if isinstance(n, (*関数, ast.Lambda)):
                continue
            if isinstance(n, ast.Call):
                yield n
            todo.extend(ast.iter_child_nodes(n))

    # 口の鍵 = (形, 名)。形＝メソッド（クラスの中の定義・`x.名(…)` で呼ぶ）か 関数（`名(…)` で呼ぶ）。
    # 同じ名の別物（芯/計算 から読み込んだ関数の `引く` と 決まり.引く）を取り違えない
    # 口の鍵 → (名の位置, 名の引数の名, 型の位置か None, 型の引数の名か None)
    口: dict[tuple[str, str], tuple[int, str, int | None, str | None]] = {}
    defs = [n for 木 in 木たち for n in ast.walk(木) if isinstance(n, 関数)]
    メソッド = {id(m) for 木 in 木たち for c in ast.walk(木) if isinstance(c, ast.ClassDef)
             for m in c.body if isinstance(m, 関数)}

    def 鍵(f) -> tuple[str, str]:
        return ("メソッド" if id(f) in メソッド else "関数", f.name)

    for f in defs:
        a = 引数(f)
        if a[:1] == ["名"] and "型" in a:
            口[鍵(f)] = (0, "名", a.index("型"), "型")
    if ("メソッド", "引く") not in 口:
        raise 引き方が読めない("芯/集計 に 引く(名, 型) の口が見つからない")

    def 渡した(c: ast.Call, 位置: int | None, 名: str | None):
        if 位置 is None:
            return None
        if len(c.args) > 位置:
            return c.args[位置]
        return next((k.value for k in c.keywords if k.arg == 名), None)

    別名 = {a.asname: a.name for 木 in 木たち for n in ast.walk(木) if isinstance(n, (ast.Import, ast.ImportFrom))
          for a in n.names if a.asname}

    def 口の呼び出しか(c) -> tuple[str, str] | None:
        f = c.func
        if isinstance(f, ast.Attribute):   # x.名(…)＝メソッドか、モジュール.関数
            return next((k for k in (("メソッド", f.attr), ("関数", f.attr)) if k in 口), None)
        if isinstance(f, ast.Name):
            k = ("関数", 別名.get(f.id, f.id))
            return k if k in 口 else None
        return None

    増えた = True
    while 増えた:   # 包みの包みまで拾う
        増えた = False
        for f in defs:
            if 鍵(f) in 口:
                continue
            a = 引数(f)
            for c in 呼び出し(f):
                k = 口の呼び出しか(c)
                if not k:
                    continue
                名位置, 名の名, 型位置, 型の名 = 口[k]
                名 = 渡した(c, 名位置, 名の名)
                if not (isinstance(名, ast.Name) and 名.id in a):
                    continue
                型 = 渡した(c, 型位置, 型の名)
                if 型 is None or (isinstance(型, ast.Constant) and 型.value is None):
                    口[鍵(f)] = (a.index(名.id), 名.id, None, None)
                elif isinstance(型, ast.Name) and 型.id in a:
                    口[鍵(f)] = (a.index(名.id), 名.id, a.index(型.id), 型.id)
                else:
                    raise 引き方が読めない(f"{f.name} が {k[1]} へ渡す型が引数でも None でもない（{ast.unparse(c)}）")
                増えた = True
                break

    out: set[str] = set()
    数えた: set[int] = set()   # 口の呼び出しの名として数えた字の node
    for f in [None, *defs]:
        自分 = 口.get(鍵(f)) if f is not None else None
        for c in (呼び出し(f) if f is not None else
                  (n for 木 in 木たち for n in 呼び出し(木))):
            k = 口の呼び出しか(c)
            if not k:
                continue
            名位置, 名の名, 型位置, 型の名 = 口[k]
            名 = 渡した(c, 名位置, 名の名)
            if isinstance(名, ast.Constant) and isinstance(名.value, str):
                数えた.add(id(名))
                型 = 渡した(c, 型位置, 型の名)
                if 型 is not None and not (isinstance(型, ast.Constant) and 型.value is None):
                    out.add(名.value)
            elif not (自分 and isinstance(名, ast.Name) and 名.id == 自分[1]):
                raise 引き方が読めない(f"{k[1]} の名が字でない（口の名の引数をそのまま渡す包みの外: {ast.unparse(c)}）")
    # 閉じた照らし: 見分けの元の名の字は、口の名として数えたか、承知の印を読む所でなければ止める
    if 名たち is None:
        from 芯 import 設定
        名たち = {n for n, e in 設定.表().items() if "集計" in (e.get("読む所") or ()) and e.get("形") in ("選ぶ", "端数の語")}
    承知の所: set[int] = set()
    for 木 in 木たち:
        for c in ast.walk(木):
            if isinstance(c, ast.Call) and _承知を読む口(c):
                承知の所 |= {id(x) for x in [*c.args, *(k.value for k in c.keywords)]}
    for 木 in 木たち:
        for n in ast.walk(木):
            if (isinstance(n, ast.Constant) and n.value in 名たち and id(n) not in 数えた and id(n) not in 承知の所):
                raise 引き方が読めない(f"{n.value} の字が引く口の名でない所にある（{getattr(n, 'lineno', '?')} 行目。"
                                     "型で引くかが読めない＝引く口で引くか、ここで照らす）")
    return out


def _承知を読む口(c) -> bool:
    """名の字を受けるが決まりの値を引かない呼び出し: 法の線を下回る線を事務所が承知した印を読む所（`承知か(決, 線)`・
    `承知の印.読む(…)[0].get(線)`）。決まりの値でなく承知の印の鍵として名を使う＝見分けの元に数えない。"""
    import ast
    f = c.func
    if isinstance(f, ast.Name) and f.id == "承知か" or isinstance(f, ast.Attribute) and f.attr == "承知か":
        return True
    return isinstance(f, ast.Attribute) and f.attr == "get" and "承知の印" in ast.unparse(f.value)


# 勤務の型ごとに引くが、1 日の数えで効くのは所定が日の法定を超える日だけで、ほかは週・変形の期間で効く決まり。
# 所定が 8 時間以内の会社では 1 日の例でどの値とも見分けられない（実の会社の例で分かった）＝覆いだけ（人が例を読む）
_週と期間で効く名 = frozenset({"時間.制度"})


# 社員の列の値のうち覆う物の形（数え方の決まり＝選べる値・休憩の表）。時間・時刻・数・日付の形の値（日の所定・みなし残業の時間
# など）はその人の契約の量＝事実で、決まりの文の写しでない＝覆いに数えない（PR #159 の線）
_人の決まりの形 = ("選ぶ", "端数の語", "休憩の表")


@lru_cache(maxsize=1)
def 人で覆う名() -> frozenset:
    """覆う名のうち、2_マスタ「社員」の列に置いた値も覆う物（人の段に置けて、形が数え方の決まり＝`_人の決まりの形`）。"""
    from 芯 import 設定
    return frozenset(n for n in 覆う名() & _人の段の名() if 設定.表().get(n, {}).get("形") in _人の決まりの形)


def 例の決まりの名(e: dict) -> set[str]:
    """例の 決まり の欄に書いたマスタの項目の名（芯/設定の表.json の名を字の中から拾う）。"""
    from 芯 import 設定
    字 = _字(e.get("決まり"))
    return {n for n in 設定.表() if n in 字}


def _会社の値(段, 会社名: str, タブ: dict, 名: str, 人も: bool = True) -> list:
    """マスタのその会社の 名 の値（会社の行・勤務の型の列・社員の列〔人も＝False なら外す〕。空は外す）。"""
    out = [r.get("今の値") for r in 段.行たち(タブ.get("会社", ())) if _字(r.get("会社")) == 会社名 and _字(r.get("項目")) == 名]
    for t in ("勤務の型", "社員") if 人も else ("勤務の型",):
        out += [r.get(名) for r in 段.行たち(タブ.get(t, ())) if _字(r.get("会社")) == 会社名 and 名 in r]
    return [v for v in out if _字(v)]


def _人の値たち(段, 会社名: str, タブ: dict, 名: str) -> set[str]:
    """2_マスタ「社員」のその会社の人の 名 の値（ならした字・空は外す）。"""
    return {_ならす(r.get(名)) for r in 段.行たち(タブ.get("社員", ()))
            if _字(r.get("会社")) == 会社名 and _字(r.get(名))}


def _人の値の例(e: dict, 名: str) -> str | None:
    """例の 人の値 に置いた 名 の値（ならした字）。置いていなければ None。"""
    d = dict(_対(_字(e.get("人の値"))))
    return _ならす(d[名]) if 名 in d else None


def _人の値を替えた例(e: dict, 名: str, 値: str) -> dict:
    d = dict(_対(_字(e.get("人の値"))))
    d[名] = 値
    return {**e, "人の値": "・".join(f"{k}={v}" for k, v in d.items())}


def _替えたタブ(段, 会社名: str, タブ: dict, 名: str, 値: str) -> dict:
    """その会社のマスタの 名 を全部 値 にしたタブ（会社の行が無ければ足す）。"""
    会社 = [dict(r) for r in 段.行たち(タブ.get("会社", ()))]
    在る = False
    for r in 会社:
        if _字(r.get("会社")) == 会社名 and _字(r.get("項目")) == 名:
            r["今の値"], 在る = 値, True
    if not 在る:
        会社.append({"会社": 会社名, "項目": 名, "今の値": 値, "適用開始": ""})
    out = {**タブ, "会社": 会社}
    for t in ("勤務の型", "社員"):
        out[t] = [({**r, 名: 値} if _字(r.get("会社")) == 会社名 and 名 in r else dict(r)) for r in 段.行たち(タブ.get(t, ()))]
    return out


def _ならす(v) -> str:
    from 芯 import 設定
    return re.sub(r"（.*$", "", 設定.揃える(v))


def _照らす一つ(段, 繋, 支給月: str, 会社名: str, タブ: dict, e: dict, 法の線: dict) -> str | None:
    """日・月 の例 1 つを今のマスタで数え、合わなければ訳を返す（合えば None）。読めない例は 例の誤り を投げる。"""
    期待 = [(名, _期待の値(名, v)) for 名, v in _対(_字(e.get("期待")))]
    if not 期待:
        raise 例の誤り("期待が空")
    if _字(e.get("種類")) == "月":
        外の名 = [名 for 名, _ in 期待 if 名 not in 月の語]
        if 外の名:
            raise 例の誤り(f"月の例の期待に書ける語は {'・'.join(月の語)} だけ（{'・'.join(外の名)}）")
        出た = _月の例を数える(段, 繋, 会社名, タブ, e)
    else:
        出た = _日の例を数える(段, 支給月, 会社名, タブ, e, 法の線)
    違い = []
    for 名, v in 期待:
        if 名 not in 出た:
            違い.append(f"{名}: 芯の数えに無い語")
        elif 出た[名] is None:
            違い.append(f"{名}: 芯が仮で数えた（{'・'.join(出た.get('_仮', [])) or '訳は集計の問い'}）")
        elif 出た[名] != v:
            違い.append(f"{名}: 例 {_見せる(名, v)}・芯 {_見せる(名, 出た[名])}")
    return "例と芯の数えが合わない（" + "／".join(違い) + "）" if 違い else None


# 例の確かめの出所（2026-11-19 オーナーの決定: 「確かめてよい人」の名簿を置かず、例に答えの受付番号か決定DB の行が付いている
# 事だけを照らす。誰が答えてもよい）。確かめた人 の字は `<答えた人の名かオーナー>（<出所>）`。出所は次のどれか 1 つ以上（・で並べてよい）:
#   受付番号: 確認ページの答えの受付番号（形の正本は 確認ページ/確認ページ.py の 受付番号の形）
#   決定DB の行: `決定DB <YYYY-MM-DD> <行の URL か ⟦鍵:…⟧>`（日付と URL か鍵の両方）
#   問いの番号: 回答のある質問と回答の問いの番号（形の正本は 初期設定/型の口.py の 問いの番号を読む）
#   過去の結果の照らし: `過去の結果 <支給月> <資料の名> <NO>:<項目>[・<NO>:<項目>…] 一致`（2026-11-19 オーナーの決定:
#     過去の資料で埋め切り、分からない物だけ聞く）。初期設定の照らし（道具/答え合わせ）でその資料のその人×項目が差 0 だった事を
#     指す。形の正本は `過去の結果を読む`（変更の記録の 書類の名・MD の［出所］もこの 1 つで読む）。一致したかは月次では見られない
#     （過去の結果を受けない）＝道具/答え合わせ の `出所を見る` が照らしの結果（差の表と答えの行）で 1 つずつ確かめ、
#     差のある・照らしに無い・資料の違う人×項目は止める（初期設定の照らしの終わりの関所）。
_決定の日 = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
_決定の印 = re.compile(r"https?://\S+|⟦鍵:[^⟧]+⟧")
過去の結果の印 = "過去の結果"
過去の結果の書き方 = ("`過去の結果 <支給月> <資料の名> <NO>:<項目>[・<NO>:<項目>…] 一致`（例 `過去の結果 2026.09支給 支給控除一覧表 "
              "000003:総支給・000003:残業手当 一致`。項目は芯の項目の名・照らしの差の表で差 0 の人×項目だけ）")
出所の書き方 = ("確かめた人 を `<答えた人の名>（<出所>）` の形で書く。出所は 確認ページの答えの受付番号 R<YYMMDD>-<英数 4 字>・"
           "決定DB の行（`決定DB <YYYY-MM-DD> <行の URL か ⟦鍵:…⟧>`）・回答のある問いの番号 Q<支給年月>-<順>・"
           "過去の結果の照らし " + 過去の結果の書き方 + " のどれか")
_人と項目 = r"[^\s:・、,]+:[^\s・、,]+"
_過去の結果の形 = re.compile(
    rf"過去の結果\s+(?P<月>\S+)\s+(?P<資料>.+?)\s+(?P<人>{_人と項目}(?:\s*[・、,]\s*{_人と項目})*)\s*(?:で)?一致(?=$|[\s・、,;)\]])")


def 過去の結果を読む(字) -> tuple[list[dict], str | None]:
    """出所の字の中の過去の結果の照らし → ([{支給月（中の字）, 資料の名, 人と項目: [(NO, 項目)], 字}], 止めの訳)。
    `過去の結果` の語が無ければ ([], None)。語が在るのに形に読めない所が残れば訳を返す（既定は止める側＝支給月・資料の名・
    人×項目・`一致` のどれかが欠けた字は出所に数えない）。全角半角は NFKC でそろえる（`：` と `:` は同じ）。"""
    s = unicodedata.normalize("NFKC", _字(字))
    if 過去の結果の印 not in s:
        return [], None
    out: list[dict] = []
    for m in _過去の結果の形.finditer(s):
        月 = 支給月の字.読む(m["月"])
        if 月 is None or "賞与" in m["月"]:
            return out, f"過去の結果の支給月「{m['月']}」が読めない（{過去の結果の書き方}）"
        資料 = m["資料"].strip()
        if not 資料 or 過去の結果の印 in 資料:
            return out, f"過去の結果の資料の名が無い（{過去の結果の書き方}）"
        人 = [tuple(x.split(":", 1)) for x in re.split(r"\s*[・、,]\s*", m["人"])]
        out.append({"支給月": 支給月の字.字にする(*月), "資料の名": 資料, "人と項目": 人, "字": m.group(0)})
    if s.count(過去の結果の印) != len(out):
        return out, f"過去の結果の照らしが形に読めない（{過去の結果の書き方}）"
    return out, None


def _読み込む(名: str, 置き場: Path):
    if 名 not in sys.modules:
        spec = importlib.util.spec_from_file_location(名, 置き場)
        m = importlib.util.module_from_spec(spec)
        sys.modules[名] = m
        spec.loader.exec_module(m)
    return sys.modules[名]


def _受付番号の形():
    return _読み込む("例の確かめ_確認ページ", _根 / "確認ページ" / "確認ページ.py").受付番号の形


def _問いの番号を読む(字):
    return _読み込む("例の確かめ_型の口", _根 / "初期設定" / "型の口.py").問いの番号を読む(字)


def 確かめた人を読む(字) -> tuple[str, list[str], str | None]:
    """例の 確かめた人 の字 → (答えた人の名, 読めた出所の並び, 止めの訳)。出所が 1 つも読めなければ訳を返す（既定は止める側）。
    全角半角は NFKC でそろえて読む（`（）` と `()` は同じ）。名だけ・AI の名だけの字は出所が無い＝止める。"""
    s = unicodedata.normalize("NFKC", _字(字))
    if not s:
        return "", [], "確かめた人が空（例を事務所に確かめてもらい、" + 出所の書き方 + "）"
    m = re.fullmatch(r"(.*?)\s*\((.*)\)", s, flags=re.S)
    if not m:
        return s, [], f"確かめた人「{_字(字)}」に確かめの出所が付いていない（{出所の書き方}）"
    名, 中 = m.group(1).strip(), m.group(2)
    if not 名:
        return "", [], f"確かめた人「{_字(字)}」に答えた人の名が無い（{出所の書き方}）"
    出所: list[str] = []
    過去, 過去の止め = 過去の結果を読む(中)
    if 過去の止め:
        return 名, [], f"確かめた人「{_字(字)}」の{過去の止め}"
    for x in 過去:   # 過去の結果の字は抜いてから残りを読む（資料の名の字を受付番号や問いの番号に読まない）
        中 = 中.replace(x["字"], " ")
        出所.append(" ".join((過去の結果の印, x["支給月"], x["資料の名"], "・".join(f"{n}:{k}" for n, k in x["人と項目"]), "一致")))
    受付 = _受付番号の形()
    for x in re.split(r"[\s・、,;()]+", 中):
        if 受付.fullmatch(x) or _問いの番号を読む(x):
            出所.append(x)
    if "決定DB" in 中:
        日, 印 = _決定の日.search(中), _決定の印.search(中)
        if not (日 and 印):
            return 名, 出所, (f"確かめた人「{_字(字)}」の決定DB の行に日付と URL か鍵が無い"
                           "（`決定DB <YYYY-MM-DD> <行の URL か ⟦鍵:…⟧>` の形で、その決定の行を書く）")
        出所.append(f"決定DB {日.group(0)} {印.group(0)}")
    if not 出所:
        return 名, [], f"確かめた人「{_字(字)}」の確かめの出所が読めない（{出所の書き方}）"
    return 名, 出所, None


def 確かめる(支給月: str, 会社名: str, タブ: dict, 例, *, 法の線: dict, 段, 繋, 今日: date | None = None) -> dict:
    """その会社の例を全部、今のマスタ（タブ）の値で芯に通して照らす。返す物は頭の文のとおり。

    タブ: 段の解決.解く に渡すタブ（月を回す と同じ物）。例: 例の行（`MDから例を読む` が返す並び。get_values の形か dict の並びも
      受ける。None は渡されない）。
    法の線: 月を回す と同じ法の線。段・繋: 月次 が読み込んだ 段の解決・入口の文脈（同じ物を使う）。今日: 確かめた日の照らし（既定は今日）。
    例の 確かめた人 は `確かめた人を読む` で読み、確かめの出所（受付番号・決定DB の行・問いの番号・過去の結果の照らし）が無ければ通さない
      （2026-11-19 オーナーの決定。誰が答えてもよい＝名簿は照らさない）。

    例ごとの照らしの後に、2 つを照らす（2026-11-18 オーナーの決定）:
      覆い: マスタの会社の行と勤務の型に値のある勤務の数え方の決まり（`覆う名`）は全部、どれかの例の 決まり の欄に名が書かれている。
            社員の列に置いた数え方の決まり（`人で覆う名`）は、社員に在る値ごとに、人の値にその値を置いて名を書いた例が在る
            （社員の列の時間・時刻・数の形の値＝人ごとの契約の量〔日の所定 など〕は決まりの文の写しでない＝覆いに数えない）
      見分け: 例が名を書いた 1 日で見分けられる決まり（`日で見分ける名`）は、選べる値のほかの値に替えると、その名を書いた
              例のどれかが合わなくなる（替えても全部合う＝例はその値の取り違えを見分けない）。社員の列の決まりは例の人の値を替える。
              替えた値で思わぬ誤り（例の誤り でない例外）が出たら、見分けたか分からない＝止める"""
    止め: list[str] = []
    合わない: list[dict] = []
    今日 = 今日 or date.today()
    if 例 is None:
        return {"通った": False, "数": 0, "合わない": [], "止め": ["例が渡されない（殻は 給与のルール.md の字を 月を回す・賞与を回す の `給与のルール=` で渡す）"]}
    例たち = [e for e in 行たち(例) if _字(e.get("会社")) == 会社名]
    if not 例たち:
        return {"通った": False, "数": 0, "合わない": [],
                "止め": [f"{会社名} の例が 1 つも無い（給与のルール.md の決まりごとの見出しの下に例の表を書き、事務所が確かめる）"]}
    見た番号 = set()
    書いた名: dict[str, list[dict]] = {}
    for e in 例たち:
        番号 = _字(e.get("例の番号")) or "（番号が無い）"

        def 外れ(訳, 番号=番号, e=e):
            合わない.append({"例の番号": 番号, "決まり": _字(e.get("決まり")), "訳": 訳})

        if 番号 in 見た番号:
            外れ("例の番号が 2 つある")
            continue
        見た番号.add(番号)
        種類 = _字(e.get("種類"))
        if 種類 not in 種類たち:
            外れ(f"種類「{種類}」は {'・'.join(種類たち)} のどれでもない")
            continue
        try:
            _対(_字(e.get("人の値")))   # 覆い・見分けは読めた例だけを数える（読めない人の値で後の照らしを落とさない）
        except 例の誤り as x:
            外れ(f"例が読めない: {x}")
            continue
        for n in 例の決まりの名(e):
            書いた名.setdefault(n, []).append(e)
        if 種類 == "書けない":
            備考 = _字(e.get("備考"))
            外れ(備考 if 備考.startswith(読めない印) else
                 "マスタに書けない決まり（芯が決まりどおりに数えられない。型の側へ項目を頼むまで止める）")
            continue
        try:
            日 = _字(e.get("確かめた日"))
            if not 日:
                外れ("事務所が確かめた日が無い（例が決まりどおりかを事務所が読んで、確かめた日を書く）")
            elif _読める日(日, "確かめた日") > 今日:
                外れ(f"確かめた日「{日}」が今日より後")
            _, _, 出所の止め = 確かめた人を読む(e.get("確かめた人"))
            if 出所の止め:
                外れ(出所の止め)
            訳 = _照らす一つ(段, 繋, 支給月, 会社名, タブ, e, 法の線)
        except 例の誤り as x:
            外れ(f"例が読めない: {x}")
            for 並び in 書いた名.values():   # 読めない例は覆い・見分けに数えない
                if e in 並び:
                    並び.remove(e)
            continue
        if 訳:
            外れ(訳)
    # 覆い: マスタの会社の行・勤務の型に値のある勤務の数え方の決まりに、名を書いた例が無い
    for n in sorted(覆う名()):
        if _会社の値(段, 会社名, タブ, n, 人も=False) and n not in 書いた名:
            合わない.append({"例の番号": "（覆い）", "決まり": n,
                          "訳": f"マスタに {n} の値があるのに、決まり の欄に {n} を書いた例が無い（例を足し、事務所が確かめる）"})
    from 芯 import 設定
    # 覆い（人）: 社員の列に置いた数え方の決まりの値ごとに、人の値にその値を置き 決まり に名を書いた例が無い
    for n in sorted(人で覆う名()):
        書いた値 = {_人の値の例(e, n) for e in 書いた名.get(n, ())} - {None}
        選べる = {_ならす(x) for x in 設定.表()[n].get("選べる値") or ()}
        # 選べる値の外の字の人は 段の解決 がその人を仮にする（ここで会社の全員を止めない）
        for v in sorted(v for v in _人の値たち(段, 会社名, タブ, n) - 書いた値 if not 選べる or v in 選べる):
            合わない.append({"例の番号": "（覆い）", "決まり": n,
                          "訳": f"社員の列に {n}={v} の人が居るのに、人の値に {n}={v} を置いて決まり の欄に {n} を書いた例が無い"
                                "（その人の決まりの例を足し、事務所が確かめる）"})
    # 見分け: ほかのどの照らしも通った時だけ（数えの外れと 2 重に出さない）
    if not 合わない:

        def 合う(替, 例たち) -> bool | str:
            """替えたマスタ・例で、例が全部合うか。例が読めない＝その値とは見分けた（False）。思わぬ例外は訳の字で返す＝止める。"""
            try:
                return all(_照らす一つ(段, 繋, 支給月, 会社名, 替, e, 法の線) is None for e in 例たち)
            except 例の誤り:
                return False
            except (ValueError, KeyError) as x:
                return f"{type(x).__name__}: {x}"

        def 見分けを照らす(n, 替える, 例たち, 今, 何):
            if not 例たち:
                合わない.append({"例の番号": "（見分け）", "決まり": n,
                              "訳": f"{n}{何} を名に書いた日の例が無い（1 日で見分けられる決まり＝日の例で照らす）"})
                return
            見分けない, 数えられない = [], []
            for alt in 設定.表()[n].get("選べる値") or ():
                if _ならす(alt) in 今:
                    continue
                r = 合う(*替える(alt))
                if r is True:
                    見分けない.append(alt)
                elif isinstance(r, str):
                    数えられない.append(f"{alt}（{r}）")
            if 見分けない:
                合わない.append({"例の番号": "（見分け）", "決まり": n, "訳": (
                    f"{n}{何} を {'・'.join(見分けない)} に替えても例が全部合う＝例がその取り違えを見分けない（違いが出る打刻の例を足す）")})
            if 数えられない:
                合わない.append({"例の番号": "（見分け）", "決まり": n,
                              "訳": f"{n}{何} を替えた値で例を数えられない＝見分けたか分からない（{'・'.join(数えられない)}）"})

        for n in sorted(set(書いた名) & 日で見分ける名()):
            日の例 = [e for e in 書いた名[n] if _字(e.get("種類")) == "日"]
            # 会社の行・勤務の型の値（人の値に n を置かない例で照らす）
            会社の例 = [e for e in 日の例 if _人の値の例(e, n) is None]
            会社の値 = {_ならす(v) for v in _会社の値(段, 会社名, タブ, n, 人も=False)}
            if 会社の値 or 会社の例 or n not in 人で覆う名():
                今 = 会社の値 or {_ならす(設定.表()[n].get("既定"))}
                見分けを照らす(n, lambda alt, n=n, 例=会社の例: (_替えたタブ(段, 会社名, タブ, n, alt), 例), 会社の例, 今, "")
            # 人の値ごと（人の値に n=v を置いた例の v を替える）
            if n in 人で覆う名():
                for v in sorted({_人の値の例(e, n) for e in 日の例} - {None}):
                    例 = [e for e in 日の例 if _人の値の例(e, n) == v]
                    見分けを照らす(n, lambda alt, n=n, 例=例: (タブ, [_人の値を替えた例(e, n, alt) for e in 例]), 例, {v},
                                f"（人の値 {v}）")
    止め += [f"{会社名} 例 {x['例の番号']}（{x['決まり'] or '決まりの欄が空'}）: {x['訳']}" for x in 合わない]
    return {"通った": not 合わない, "数": len(例たち), "合わない": 合わない, "止め": 止め}
