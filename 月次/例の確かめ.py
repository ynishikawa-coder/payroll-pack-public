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

返す物: {"通った": bool, "数": 数えた例の数, "合わない": [{"例の番号", "決まり", "訳", "項目", "字"}], "止め": [訳],
         "人の止め": {NO: [訳]}, "人の外れ": {NO: [{"例の番号", "項目", "訳", "字"}]}, "当たらない例": [例の番号]}
  項目: 止めた例の項目 {"決まり": [決まり の欄の項目の名], "見出し": [給与のルール.md の見出し]}（例の行の外れは `例の鍵` の 2 つ。
  覆い・見分けは 決まり の名 1 つ。同じ例の番号の行が違う例を指せば None＝決まらない）。字: 止め・人の止め に置いた字そのもの
  （月次は字を割らず、項目 と 字 を読んで問いを組む）。
（`月次.月を回す`・`月次.賞与を回す` が 通った でなければ、その会社の全員を関所で外す＝出口へ出さない。通っても 人の止め の人は
その人だけを関所で外す）。

例の 支給月 はその例が当たる月（空なら回す月）。例はその支給月の決まりで解いて照らす。決まりの値は、
例の月も回す月も同じ 段の解決.解く（事務所・会社・勤務の型・人の段と、変更の記録でその月へ戻した人の段）の 1 本で引く。
例ごとに、例の人の決まりの値を例の支給月と回す月で、覆う名（`覆う名`）と例が 決まり の欄に書いた名について比べる。
比べる名・覆う名・止めの文の名は、どれもマスタの項目の名で数える（段の解決.解く が 1 つの項目を 2 つの鍵に分ける物〔時間.休憩の表〕は、
芯/設定の表.json の マスタの項目 で元の項目の名へ戻す＝対応の正本はその 1 か所）。
値の違う名は、その例ではその月の覆いと見分けに数えず、回す月にその名の値が在れば、回す月に当たる例でその名を書いた物を求め、
無ければ覆いの外れとして止める。決まり の欄に書いた名がどれも違う値になる例は回す月に当たらない（まだ当たらない・もう当たらない）＝その月は数えずに外す（照らさない・返す物の 当たらない例）。
名を 1 つも書かない例は外さず、例の支給月で照らすが、覆いと見分けには数えない。支給月 が空の日の例は、
どの月にも当たる例として回す月で照らす。支給月 が読めない例は止める。覆いが求める値（事務所・会社・勤務の型の段の値と、
社員の列の変更の記録で戻した値）と見分けの今の値も、回す月の 段の解決.解く から取る。回す月に当たる例が 1 つも無ければ止める（例の確かめは通らない）。
決まり の欄（MD の表の 決まり の升）には、マスタの項目の名（芯/設定の表.json の名）だけを ・ で並べて書く（空＝名を書かない例）。
名と完全に同じでない字（綴りの揺れ・説明の字・括弧）は「例が読めない」で止める（綴りの揺れた名を黙って拾わない）。
見出し（`### <決まりの名>`）は例の行の 見出し に別に持ち、名は読まない（見出しの括弧の説明を名と取り違えない）。
正本は docs/設計/Drive の型.md §4 の例の表。

例が要るかは場面で決める（2026-11-25 オーナーの決定「起きていない場面で止めない」）: 日の場面（休憩を書いていない日など・`初期設定/日の場面.py`）に
結んだ決まりの覆いと見分けは、その月の表 A・B でその場面の日がある人が居る時だけ求め、外れたらその人だけを 人の止め に置く
（場面の日が誰にも無ければ求めない）。表 A・B が渡されない・読めない時（賞与など）は今までどおり会社の全員で見る。

例は決まりの文から作る（過去の給与ソフトの答えからは作らない）。答え合わせではない: 照らす相手は確かめた例。例の確かめの出所に
過去の結果の照らし（人×項目の一致）を書いてよいが、照らしの結果を証しに渡した時だけ通る（出所の種類と証しの形の正本は `出所の種類たち`）。
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
from 芯 import 字 as 字のそろえ  # noqa: E402

_s = importlib.util.spec_from_file_location("例の確かめ_日の場面", _根 / "初期設定" / "日の場面.py")
日の場面 = importlib.util.module_from_spec(_s)   # 決まり→場面と、場面に当たる人の 1 か所（設問 の _今月に当たるか も同じ物を呼ぶ）
_s.loader.exec_module(日の場面)


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
見出しの外 = "（見出しの外）"   # `###` の下でない表の行の 見出し


def 例の所(e: dict) -> str:
    """止めの文に出す例の所: `給与のルール.md#<見出し>（<決まり の升>）`（見出しが無ければ升の字だけ）。名は読まない＝表示だけ。"""
    見, 決 = _字(e.get("見出し")), _字(e.get("決まり"))
    if not 見:
        return 決
    所 = 見 if 見 == 見出しの外 else f"給与のルール.md#{見}"
    return f"{所}（{決}）" if 決 else 所


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
    読めない）。決まり の列には照らすマスタの項目の名（芯/設定の表.json の名）を書く。読んだ行の 決まり は升の字のまま、
    見出し は `### <決まりの名>` の字（名は升だけから拾う＝見出しの字は名に数えない。表示は `例の所`）。
    HTML の注（<!-- -->）とコードの囲みの中は読まない。

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
                    "見出し": 見出し or 見出しの外, "種類": "書けない", "備考": f"{読めない印}: {訳}"})

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
            out.append({"会社": 会社, **{c: r[c] for c in MDの例の列}, **{c: r[c] for c in 任意の列 if c in r}, "見出し": 見出し})
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
    人の値 = _人の値(例)
    return NO, {**タブ, "社員": [*段.行たち(タブ.get("社員", ())), {**_仮の人の行(会社名, NO, _字(例.get("勤務の型"))), **人の値}]}


def _人の値(例: dict) -> dict[str, str]:
    """例の 人の値 → {名: 値}。`名=値` の形でない・人の段に置けない名は 例の誤り（例が読めない＝覆い・見分けに数えない）。"""
    人の値 = dict(_対(_字(例.get("人の値"))))
    外 = sorted(n for n in 人の値 if n not in _人の段の名())
    if 外:
        raise 例の誤り(f"人の値の {'・'.join(外)} は人の段に置ける項目でない（初期設定/項目.json の 段 に 人 が在る名だけ）")
    return 人の値


def _仮の人の行(会社名: str, NO: str, 型: str) -> dict:
    """決まりを引くために社員の表へ足す仮の人の行（人の値は持たない）。"""
    return {"会社": 会社名, "NO": NO, "氏名": "例", "勤怠の表記": NO, "勤務の型": 型, "入社日": "2000-01-01", "生年月日": "1980-01-01"}


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


def _例の月(支給月: str, 例: dict) -> str:
    """例を解く支給月: 例の 支給月（その例が当たる月）。空なら回す月（どの月にも当たる例）。"""
    return _字(例.get("支給月")) or 支給月


def _人の決まり(段, 月: str, 会社名: str, タブ: dict, 例: dict) -> dict:
    """例の人にその支給月に効く決まりの値 → {名: 値}。段の解決.解く（事務所・会社・勤務の型・人の段を重ね、人の値は変更の記録で
    その月へ戻した値）で引き、例の 勤務の型 の値を重ねる。例の確かめが決まりの値を引く道はこれと `_回す月の段` だけ（同じ 解く）。"""
    NO, タブ = _例の人を足す(段, 会社名, タブ, 例)
    d = dict(段.解く(月, **タブ)["決まり"].get((会社名, NO)) or {})
    return {**d, **(d.pop("勤務の型", None) or {}).get(_字(例.get("勤務の型")), {})}


@lru_cache(maxsize=1)
def _解く鍵の項目() -> dict[str, str]:
    """段の解決.解く が 1 つの項目を分けて作る鍵 → 元のマスタの項目の名（正本は 芯/設定の表.json の マスタの項目・ここで写さない）。"""
    from 芯 import 設定
    return {n: e["マスタの項目"] for n, e in 設定.表().items() if e.get("マスタの項目")}


def 項目の名(鍵: str) -> str:
    """解く の鍵 → マスタの項目の名（分けて作る鍵でなければそのまま）。覆う名・比べる名・止めの文はこの名で数える。"""
    return _解く鍵の項目().get(鍵, 鍵)


def _対の鍵(名: str) -> tuple[str, ...]:
    """マスタの項目の名 → 解く の鍵たち（その項目と、解く がその項目から分けて作る鍵。`_解く鍵の項目` を逆に引く）。"""
    return (名, *sorted(k for k, n in _解く鍵の項目().items() if n == 名))


def _比べる字(d: dict, 名: str) -> str:
    return json.dumps([d.get(k) for k in _対の鍵(名)], ensure_ascii=False, sort_keys=True, default=str)


def _値が在る(d: dict, 名: str) -> bool:
    """d に 名 の値が在る（None・空白の字・空の並びは無い）。"""
    return any(not (v is None or (isinstance(v, str) and not v.strip()) or v in ([], {}))
               for v in (d.get(k) for k in _対の鍵(名)))


def _人の段の字(d: dict, 名: str) -> str:
    """人の段の値を比べる 1 つの字: 字の値はならした字、字でない値（段の解決が分けた 時間.休憩の表 など）は `_比べる字`。"""
    v = [d.get(k) for k in _対の鍵(名)]
    return _ならす(v[0]) if len(v) == 1 and isinstance(v[0], str) else _比べる字(d, 名)


def _マスタの字(d: dict, 名: str) -> str:
    """止めの文に出す値: マスタに書く字（解く の中の形でなく）。休憩の表は分けた 2 つの鍵を 1 つの表の字
    （`12:00〜13:00`・`5:59超30分、8:00超60分`・曜日ごとは {曜日: 字} の JSON）に戻す。"""
    v = [d.get(k) for k in _対の鍵(名)]
    if len(v) == 1:
        return v[0] if isinstance(v[0], str) else json.dumps(v[0], ensure_ascii=False)

    def 一日(*ws) -> str:
        return "、".join(f"{x[0]}超{x[1]}分" if isinstance(x, (list, tuple)) else str(x) for w in ws for x in (w or ()))
    if any(isinstance(w, dict) for w in v):
        曜日たち = list(dict.fromkeys(k for w in v if isinstance(w, dict) for k in w))
        return json.dumps({k: 一日(*((w or {}).get(k) if isinstance(w, dict) else w for w in v)) for k in 曜日たち},
                          ensure_ascii=False)
    return 一日(*v)


def 回す月に違う名(段, 支給月: str, 会社名: str, タブ: dict, 例: dict) -> dict[str, bool]:
    """例の人に、回す月と例の 支給月 で違う値になる決まりの名 → {名: 回す月にその名の値が在るか}。比べる名は `覆う名` と
    例が 決まり の欄に書いた名（どれもマスタの項目の名・解く の鍵は `_対の鍵` で引く）。
    例の 支給月 が空か回す月と同じなら空。読めない支給月は 例の誤り。"""
    月 = _字(例.get("支給月"))
    if not 月 or _月(月) == 支給月の字.そろえる(支給月, "中"):
        return {}
    例の月, 回す月 = _人の決まり(段, 月, 会社名, タブ, 例), _人の決まり(段, 支給月, 会社名, タブ, 例)
    return {n: _値が在る(回す月, n) for n in sorted(覆う名() | 例の決まりの名(例))
            if _比べる字(例の月, n) != _比べる字(回す月, n)}


def _回す月の段(段, 支給月: str, 会社名: str, タブ: dict) -> tuple[dict[str, list], dict[str, dict[str, str]]]:
    """回す月の決まりの値を、例の人と同じ 段の解決.解く で引く → (型の段の値, 人の段の値)。
    型の段の値: その会社の勤務の型ごと（と型の空な人）の、人の値を持たない仮の人に効く値＝事務所・会社・勤務の型の段 → {名: [値…]}。
    人の段の値: 2_マスタ「社員」のその会社の人の、変更の記録でその月へ戻した人の段の値（`人で覆う名` の名）
    → {名: {比べる字（`_人の段の字`）: マスタの字（`_マスタの字`）}}。"""
    型たち = sorted({_字(r.get("型の名")) for r in 段.行たち(タブ.get("勤務の型", ())) if _字(r.get("会社")) == 会社名} | {""})
    仮 = [_仮の人の行(会社名, f"{_仮の人}-型-{i}", t) for i, t in enumerate(型たち)]
    r = 段.解く(支給月, **{**タブ, "社員": [*段.行たち(タブ.get("社員", ())), *仮]})
    型の値: dict[str, list] = {}
    for x in 仮:
        d = {k: v for k, v in (r["決まり"].get((会社名, x["NO"])) or {}).items() if k != "勤務の型"}
        for n in 覆う名():
            if _値が在る(d, n):
                型の値.setdefault(n, []).append(d.get(n))
    人の値: dict[str, dict[str, str]] = {}
    仮のNO = {x["NO"] for x in 仮}
    for (c, NO), p in r["人"].items():
        if c == 会社名 and NO not in 仮のNO:
            for n in 人で覆う名():
                if _値が在る(p, n):
                    人の値.setdefault(n, {}).setdefault(_人の段の字(p, n), _マスタの字(p, n))
    return 型の値, 人の値


def _日の例を数える(段, 支給月: str, 会社名: str, タブ: dict, 例: dict, 法の線: dict) -> dict:
    """種類＝日 の例 1 つを、例の 支給月（空なら回す月）のマスタの値で芯/集計に通す → {語: 値}（集計の行と、その日の 休憩・労働）。"""
    from 芯.集計 import 集計する
    支給月 = _例の月(支給月, 例)
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
    人の事実（`人.` の名・`支払.賃金の形`）は決まりでないので外し、締めの例が照らす `支払.締め日` を足す。
    名はマスタの項目の名（解く が分けて作る鍵〔時間.休憩の長さ〕は元の項目〔時間.休憩の表〕へ畳む＝`項目の名`）。"""
    from 芯 import 設定
    return frozenset({項目の名(n) for n, e in 設定.表().items() if "集計" in (e.get("読む所") or ())
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
    """例の 決まり の欄（MD の表の 決まり の升の字だけ・見出しは読まない）に書いたマスタの項目の名。欄を ・、, で分けた字が、
    どれも芯/設定の表.json の名と完全に同じ字でなければ 例の誤り（綴りの揺れ・説明の字・括弧を黙って名なしにしない）。
    表に在っても 項目の外 の名（マスタに列が無い名・解く が作る鍵）は 例の誤り（マスタの項目の名だけを書く。写して作る鍵は
    芯/設定の表.json の 写す元 を書く名として添える）。
    解く が分けて作る鍵（マスタの項目 を持つ名）は元の項目の名を添えて止める。空＝名を書かない例（set()）。"""
    from 芯 import 設定
    語 = [w.strip() for w in re.split(r"[・、,]", _字(e.get("決まり"))) if w.strip()]
    外 = [w for w in 語 if w not in 設定.表()]
    if 外:
        raise 例の誤り(f"決まり の欄の「{'・'.join(外)}」は芯/設定の表.json の項目の名でない"
                     "（決まり の欄には項目の名だけを完全に同じ字で ・ で並べて書く。説明は見出しか文へ）")
    項目の外 = [w for w in 語 if 設定.表()[w].get("項目の外") and 項目の名(w) == w]
    if 項目の外:
        元 = sorted({x for w in 項目の外 if (x := 設定.表()[w].get("写す元"))})
        raise 例の誤り(f"決まり の欄の「{'・'.join(項目の外)}」はマスタの項目の名でない（芯/設定の表.json の 項目の外 の名＝"
                     "マスタに列が無い名か段の解決が作る鍵。決まり の欄にはマスタの項目の名だけを書く"
                     + (f"。{'・'.join(元)} で書く" if 元 else "") + "）")
    内 = [w for w in 語 if 項目の名(w) != w]
    if 内:
        raise 例の誤り(f"決まり の欄の「{'・'.join(内)}」はマスタの項目の名でない（{'・'.join(sorted({項目の名(w) for w in 内}))} で書く）")
    return set(語)


def _人の値の例(e: dict, 名: str) -> str | None:
    """例の 人の値 に置いた 名 の値（ならした字）。置いていなければ None。"""
    d = dict(_対(_字(e.get("人の値"))))
    return _ならす(d[名]) if 名 in d else None


def _人の値を替えた例(e: dict, 名: str, 値: str) -> dict:
    d = dict(_対(_字(e.get("人の値"))))
    d[名] = 値
    return {**e, "人の値": "・".join(f"{k}={v}" for k, v in d.items())}


def _替えたタブ(段, 会社名: str, タブ: dict, 名: str, 値: str) -> dict:
    """その会社のマスタの 名 を全部 値 にしたタブ（適用開始が空の会社の行が無ければ足す＝どの支給月にも 値 が効く。
    後の月から当たる行だけが在る時も、例の月と回す月の両方で替えた値を引く）。"""
    会社 = [dict(r) for r in 段.行たち(タブ.get("会社", ()))]
    前から = False
    for r in 会社:
        if _字(r.get("会社")) == 会社名 and _字(r.get("項目")) == 名:
            r["今の値"] = 値
            前から = 前から or not _字(r.get("適用開始"))
    if not 前から:
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


# 例の確かめの出所（2026-11-19 オーナーの決定: 「確かめてよい人」の名簿を置かず、例に確かめの出所が付いている事だけを照らす。
# 誰が答えてもよい）。確かめた人 の字は `<答えた人の名かオーナー>（<片>・<片>…）`。
# 出所の種類・文法・書き方・照らしに要る証しは下の `出所の種類たち` の表 1 つが正本（ここにも docs にも写さない）。
# 文法は種類ごとに 1 つ（表の 文法）で、字の全体・片の 1 つ 1 つがその文法に全体で当たる時だけ読む（既定で閉じる。根治・2026-11-27:
# 片を区切りの字で切ってから読んだ前の読みは、区切りの変種・資料の名の中の空白に読めない字を隠せた）。下の部品は表の文法の材料。
過去の結果の印 = "過去の結果"
_括弧の組 = r"\([^\s:・、,;()「」]*\)"   # 名の中の括弧は 1 段の組だけ（`残業(作り物の数え方)`・`一覧(9月分)`）
_項目の字 = rf"(?:[^\s:・、,;()「」]|{_括弧の組})+"
_人と項目 = rf"[0-9A-Za-z]+:{_項目の字}"
_資料の名の字 = rf"「(?:[^「」()\t\n\r]|\([^「」()\t\n\r]*\))+」|(?:[^\s・、,;:()「」]|{_括弧の組})+"
_過去の結果の文法 = (rf"{過去の結果の印} (?P<月>\d{{4}}(?:[./-]\d{{1,2}}|年\d{{1,2}}月)(?:支給)?) (?P<資料>{_資料の名の字}) "
              rf"(?P<人>{_人と項目}(?:・{_人と項目})*) 一致")
過去の結果の書き方 = ("`過去の結果 <支給月> <資料の名> <NO>:<項目>[・<NO>:<項目>…] 一致`（間は半角の空白 1 つ・人×項目の間は ・ だけ。"
              "資料の名はその人×項目の答えの行の出所の file の名〔拡張子は除いてよい〕と字まで同じ名で、空白か ・ を含む名は「」で囲む。名の中の括弧は 1 段の組だけ。"
              "例 `過去の結果 2026.09支給 支給控除一覧表 000003:総支給・000003:残業手当 一致`。項目は芯の項目の名・照らしの差の表で差 0 の"
              "人×項目だけ）")


def 過去の結果の字(支給月: str, 資料の名: str, 人と項目) -> str:
    """過去の結果の照らしの字を表の文法どおりに組む 1 か所（読むのは `過去の結果を読む`）。支給月は文法の 月 の字（`2026-09`・`2026.09支給` など）、人と項目は [(NO, 項目)]。
    空白か ・ を含む資料の名は「」で囲む。資料の名が空なら文法に当たらない字のまま返す（読む側で止まる）。"""
    資料 = f"「{資料の名}」" if re.search(r"[\s・]", 資料の名) else 資料の名
    return " ".join((過去の結果の印, 支給月, 資料, "・".join(f"{n}:{k}" for n, k in 人と項目), "一致"))


def _過去の結果の片(m: re.Match) -> tuple[dict | None, str | None]:
    """表の 過去の結果 の文法に当たった字 → ({支給月（中の字）, 資料の名, 人と項目: [(NO, 項目)], 字}, 止めの訳)。"""
    月 = 支給月の字.読む(m["月"])
    if 月 is None:
        return None, f"過去の結果の支給月「{m['月']}」が読めない（{過去の結果の書き方}）"
    資料 = m["資料"][1:-1].strip() if m["資料"].startswith("「") else m["資料"]
    人 = [tuple(x.split(":", 1)) for x in m["人"].split("・")]
    return {"支給月": 支給月の字.字にする(*月), "資料の名": 資料, "人と項目": 人, "字": m.group(0)}, None


def 過去の結果を読む(字) -> tuple[list[dict], str | None]:
    """出所の字（変更の記録の 書類の名・MD の［出所］など、ほかの字の混ざる字）の中の過去の結果の照らし → (片たち, 止めの訳)。
    片は表 `出所の種類たち` の 過去の結果 の文法に全体で当たり、前後が区切り（空白・・、,;()）か字の端の字だけ（文法は写さずに表を引く）。
    `過去の結果` の語が無ければ ([], None)。語が文法に当たらない所が残れば訳を返す（既定で止める）。全角半角は NFKC でそろえる。"""
    s = unicodedata.normalize("NFKC", _字(字))
    if 過去の結果の印 not in s:
        return [], None
    形 = re.compile(rf"(?<![^\s・、,;(])(?:{出所の種類たち[過去の結果の印].文法})(?=\Z|[\s・、,;)\]])")
    out: list[dict] = []
    for m in 形.finditer(s):
        片, 止め = _過去の結果の片(m)
        if 止め:
            return out, 止め
        out.append(片)
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


def _受付番号の日(番号: str) -> date | None:
    """受付番号 R<YYMMDD>-… の日（20YY 年）。暦に無い日（R000000 など）は None。"""
    try:
        return date(2000 + int(番号[1:3]), int(番号[3:5]), int(番号[5:7]))
    except ValueError:
        return None


def _受付番号たち(行: dict) -> list[str]:
    return _受付番号の形().findall(unicodedata.normalize("NFKC", str(行.get("回答") or "")))


def _表の番号たち(問いの表, 会社名: str) -> dict[str, dict]:
    """質問と回答（get_values の形か dict の並び）→ {"問い": {その会社の答えのある問いの番号: その問いの今の行},
    "受付": {受付番号: [その番号を書いた今の行]}, "前の受付": {送り直しの前の行にだけ在る受付番号: [その問いの今の行]}}。
    行は例との関係（`_行が例を指す`）を見るのに使う。問いの番号ごとに一番下の行が今の行（送り直しは新しい行）で、問いの番号も
    受付番号も今の行だけで数える（R と Q を同じに判じる。根治・2026-11-27: 受付番号だけ送り直しの前の行でも数え、今の答えが別の所を
    指していても前の行で通った）。答えの芯が空か `分からない` の行は数えない（答えの無い受付を確かめの出所にしない）。
    答えのある問いは 勤怠の照らし.答えのある問いの番号たち と同じ読み。"""
    型 = _読み込む("例の確かめ_型の口", _根 / "初期設定" / "型の口.py")
    行 = [q for q in 型.格子を行へ(問いの表) if str(q.get("会社", "")).strip() == 会社名]
    今 = list(型.今の問いの行たち(行))
    今の行 = {str(q.get("問いの番号", "")).strip(): q for q in 今}
    答えた: dict[str, dict] = {}
    受付: dict[str, list[dict]] = {}
    for q in 今:
        答え = 型.答えの芯(q.get("回答"))
        if 答え and 答え != "分からない":
            答えた[str(q.get("問いの番号", "")).strip()] = q
            for x in _受付番号たち(q):
                受付.setdefault(x, []).append(q)
    前: dict[str, list[dict]] = {}
    for q in 行:
        for x in _受付番号たち(q):
            if x not in 受付:
                前.setdefault(x, []).append(今の行.get(str(q.get("問いの番号", "")).strip(), q))
    return {"問い": 答えた, "受付": 受付, "前の受付": 前}

def _型の口():
    return _読み込む("例の確かめ_型の口", _根 / "初期設定" / "型の口.py")


def _例の鍵(例: dict) -> tuple[set[str], set[str]]:
    """例 → (決まり の欄の項目の名, 見出し〔給与のルール.md の `###`〕)。読めない 決まり は名なし（指す鍵が無い＝関係を判じない）。"""
    try:
        名たち = 例の決まりの名(例)
    except 例の誤り:
        名たち = set()
    型 = _型の口()
    見 = 型.見出しの字(例.get("見出し"))   # 見出しのそろえの正本（反映先を組む口・読む口・設問.md_の節 と同じ）
    # 区切りを含む見出しは反映先で指せない＝鍵にしない（その例は `確かめる` が見出しの訳で止める）
    return 名たち, ({見} if 見 and 見 != 見出しの外 and not 型.見出しの区切りの訳(見) else set())


def 例の鍵(例: dict) -> tuple[set[str], set[str]]:
    """例の行 → (決まり の項目の名たち, 見出したち)。出所の行を照らす鍵と同じ物（例の問いの反映先を組む月次はこれを呼ぶ）。"""
    return _例の鍵(例)


def _行が例を指す(行: dict, 例: dict) -> bool:
    """質問と回答の行が、照らしている例を指すか。会社は `_表の番号たち` がそろえた物だけが来る（同じ会社）。
    人（NO）は例の側に列が無い（例は作り物の人 `例` で数える）＝人では判じない。鍵は型の列 `反映先`（、で並べた
    `2_マスタ/<タブ>/<項目>` か `<md の名>#<見出し>`）で判じる: 項目がこの例の 決まり の欄の名か、md が給与のルールで
    見出しがこの例の見出し（か 決まり の名）の時だけ指す。反映先 の空の行・ほかの所を指す行は指さない（既定で閉じる）。"""
    型 = _読み込む("例の確かめ_型の口", _根 / "初期設定" / "型の口.py")
    名たち, 見たち = _例の鍵(例)
    for 片 in 型.反映先を読む(行.get("反映先"), 揃える=True):   # 字の読み方の正本は 型の口.反映先を読む（例の問いも同じ口で組む）
        if 片.種 == "md" and 片.md_の名 == 型.名("給与のルール") and 片.乙 in 見たち | 名たち:
            return True
        if 片.種 == "マスタ" and 片.乙 in 名たち:
            return True
    return False


def _指す訳(何: str, 例: dict, 行たち=()) -> str:
    先 = "・".join(dict.fromkeys(_字(q.get("反映先")) or "（空）" for q in 行たち))
    return (f"{何} の答えの行が、照らしている例（{例の所(例) or _字(例.get('例の番号'))}）を指していない（"
            + (f"その答えの今の行の 反映先 は「{先}」。" if 先 else "")
            + "同じ会社で、型の列 反映先 が `2_マスタ/<タブ>/<この例の 決まり の項目>` か `給与のルール.md#<この例の見出し>` の行だけを"
            "出所にする）")

# 答えの資料の名（過去の結果の資料の名の照らし。道具/答え合わせ の 出所を見る もこれを呼ぶ＝照らしは 1 つ）。
# 字のそろえは 芯/字 の正本（`そろえる`）を当て、そろえた字どうしの == だけで当てる（含む・頭が では当てない。根治・2026-11-27:
# 含むかで当てた前の当て方は、答えの名の前後に字を足した名〔`作り物の一覧ではない`〕を通した）
_拡張子 = re.compile(r"\.(?:pdf|csv|xlsx?|xlsm|tsv|txt|json|html?|md|png|jpe?g)$", re.I)


def 答えの資料の名(字) -> str:
    """答えの行の出所（file の道・`#タブ` 付きでもよい）→ file の名（道と `#タブ` を外し、芯/字 の そろえる を当てる。大小は残す）。"""
    s = unicodedata.normalize("NFKC", str(字 or "")).split("#")[0].replace("\\", "/").rsplit("/", 1)[-1]
    return 字のそろえ.そろえる(s, 大小も=False)


def 資料の幹(字) -> str:
    """答えの行の出所 → file の名の拡張子を外した字（資料の名には拡張子を書かないことが多い）。"""
    return _拡張子.sub("", 答えの資料の名(字))


def 資料の名が当たるか(書いた, 出所) -> bool:
    """書いた資料の名が、答えの行の出所の file と字まで同じか。書いた側は 芯/字 の そろえる と拡張子を外すだけ（道・`#` で切らない）、
    出所の側は `資料の幹`。そろえた字の == だけで当てる（空は当てない）。"""
    a = _拡張子.sub("", 字のそろえ.そろえる(書いた, 大小も=False))
    return bool(a) and a == 資料の幹(出所)


class 食い違う出所(tuple):
    """同じ鍵（支給月・会社・NO・項目）の答えの行が 2 つ以上在り、出所の資料が違う（後の行で黙って上書きしない＝照らすと止める）。"""


def 答えの出所(答えの行) -> dict | None:
    """答えの行（道具/答え合わせ の 読む の出す行・dict か 行）→ {(支給月, 会社, NO, 項目): 出所の字}。None は渡していない。
    同じ鍵の行の出所の資料（`資料の幹`）が違えば、その鍵は `食い違う出所`（どちらの字も持つ）。鍵の字は NFKC でそろえる。"""
    if 答えの行 is None:
        return None
    out: dict = {}
    for r in 答えの行:
        g = (lambda k: r.get(k)) if isinstance(r, dict) else (lambda k: getattr(r, k, ""))
        k = tuple(unicodedata.normalize("NFKC", _字(g(x))) for x in ("支給月", "会社", "NO", "項目"))
        v = unicodedata.normalize("NFKC", _字(g("出所")))
        if k not in out:
            out[k] = v
            continue
        前 = out[k] if isinstance(out[k], 食い違う出所) else (out[k],)
        if all(資料の幹(v) != 資料の幹(x) for x in 前):
            out[k] = 食い違う出所((*前, v))
    return out


def _決定の鍵(x: str) -> str:
    """決定DB の印（`⟦鍵:<分野>/<名>⟧`・鍵の字・行の URL）→ 突き合わせる字（鍵は中の `<分野>/<名>`・URL はそのまま）。"""
    s = unicodedata.normalize("NFKC", str(x or "")).strip()
    m = re.fullmatch(r"⟦鍵:(.+)⟧", s)
    return (m.group(1) if m else s).strip()


def 照らしの一致(差の表) -> set[tuple[str, str, str, str]]:
    """照らしの結果の差の表（2 次元の並び・1 行目が見出し〔支給月・会社・NO・項目・差〕）→ 差 0 の (支給月, 会社, NO, 項目) の集まり。
    同じ鍵の行が 2 つ以上在り差が食い違えば（0 と 0 でない）、その鍵は一致に数えない（後の行で黙って勝たせない）。
    鍵の字は NFKC でそろえる。見出しが足りなければ ValueError（道具/答え合わせ の 出所を見る もこれを呼ぶ）。"""
    表 = [list(r) for r in 差の表]
    if not 表:
        return set()
    頭 = [_字(x) for x in 表[0]]
    要る = ("支給月", "会社", "NO", "項目", "差")
    if not set(要る) <= set(頭):
        raise ValueError(f"照らしの差の表の見出しに {'・'.join(要る)} が無い（{頭}）")
    i = {k: 頭.index(k) for k in 要る}
    零, 他 = set(), set()
    for r in 表[1:]:
        k = tuple(unicodedata.normalize("NFKC", _字(r[i[x]] if i[x] < len(r) else "")) for x in 要る[:4])
        (零 if i["差"] < len(r) and _字(r[i["差"]]) == "0" else 他).add(k)
    return 零 - 他


_片の間 = r" ?[・、] ?"   # 片と片の間（・ か 、。前後に半角の空白 1 つまで）


class 出所の種類:
    """出所の種類の表の 1 行。文法と、照らしに要る証し（`確かめた人を読む` などの引数の名）と、その証しで照らす関数を必ず持つ
    （どれかが無ければ作れない＝文法か証しの無い種類は表に入らない）。
      文法: この種類の片の正規表現の字（名前付きの組を持ってよい）か、それを返す関数。片はこの文法に全体で当たる時だけ読む。
      読む(m) → (片, 止めの訳): 文法に当たった字（re.Match）から照らす片を作る（暦に無い月などは訳）。
      要素(x) → 真偽: 証しの並びの 1 つの形。
      支度(証し, 会社名) → 照らしに使う物（読めなければ ValueError）。
      照らす(片, 支度した物, 今日, 会社名) → (読めた出所の字, 止めの訳)。
      会社が要る: 証しをその会社の物として照らす（証しを渡して 会社名 が無ければ ValueError）。
      形(証し) → 止めの訳か None: 証しが並びでない種類の形の照らし（無ければ 並び＋要素 で照らす）。
      関係(片, 支度した物, 例) → 止めの訳か None: 照らしている例をその片が指すか（`確かめた人を読む` に 例 を渡した時だけ当てる）。"""

    def __init__(self, 名: str, *, 言葉: str, 文法, 証し: str, 証しの言葉: str, 書き方: str, 読む, 要素, 支度, 照らす,
                 会社が要る: bool = True, 形=None, 関係=None):
        if not (名 and 文法 and 証し and callable(読む) and callable(要素) and callable(支度) and callable(照らす)):
            raise ValueError(f"出所の種類 {名}: 文法・証しの名・照らす関数の無い種類は表に入れない")
        self.名, self.言葉, self.証し, self.証しの言葉, self.書き方 = 名, 言葉, 証し, 証しの言葉, 書き方
        self.読む, self.要素, self.支度, self.照らす, self.会社が要る = 読む, 要素, 支度, 照らす, 会社が要る
        self.形, self.関係, self._文法, self._片の形 = 形, 関係, 文法, None

    @property
    def 文法(self) -> str:
        return self._文法() if callable(self._文法) else self._文法

    @property
    def 片の形(self) -> re.Pattern:
        """括弧の中で、この種類の片の始まりから当てる形（文法の全体の後が片の間か括弧の中の終わり）。"""
        if self._片の形 is None:
            self._片の形 = re.compile(rf"(?:{self.文法})(?=\Z|{_片の間})")
        return self._片の形


_並び = (list, tuple, set, frozenset)


def 証しの形(種類: 出所の種類, 証し) -> str | None:
    """証しの形を照らす 1 か所 → 止めの訳（None は形が合う）。証しはどれも並び（list・tuple・set）だけを受け、字（str）・dict・
    ほかの形は止める。並びの 1 つ 1 つも種類の `要素` で照らす。種類に `形` が在ればそれで照らす（組で渡す証し）。"""
    if 種類.形 is not None:
        return 種類.形(種類, 証し)
    if not isinstance(証し, _並び):
        return (f"{種類.証しの言葉}（引数 `{種類.証し}`）が並び（list・tuple・set）でない（{type(証し).__name__}）"
                "＝形の違う証しでは照らさない")
    外 = [x for x in 証し if not 種類.要素(x)]
    if 外:
        return f"{種類.証しの言葉}（引数 `{種類.証し}`）の中に形の違う物が在る（{外[0]!r}）＝照らさない"
    return None


def _日の訳(日: date | None, 今日: date, 何: str) -> str | None:
    if 日 is None:
        return f"{何} の日が暦に無い"
    if 日 > 今日:
        return f"{何} の日 {日} が今日 {今日} より後"
    return None


def _例の名(例: dict) -> str:
    return 例の所(例) or _字(例.get("例の番号"))


# --- R（確認ページの答えの受付番号。形の正本は 確認ページ/確認ページ.py の 受付番号の形）
def _Rを照らす(x: str, 番号たち, 今日: date, 会社名: str):
    訳 = _日の訳(_受付番号の日(x), 今日, f"受付番号 {x}（R<YYMMDD>）")
    if 訳:
        return x, 訳
    if x in 番号たち["前の受付"]:
        今 = "・".join(dict.fromkeys(_字(q.get("回答")) for q in 番号たち["前の受付"][x]))
        return x, (f"受付番号 {x} は {会社名} の質問と回答の送り直しの前の行にだけ在る（その問いの今の行の回答は「{今}」。"
                   "今の答えの受付番号を書く）")
    if x not in 番号たち["受付"]:
        return x, f"受付番号 {x} が {会社名} の質問と回答の答えの行に無い（`分からない`・答えの空の行の番号は数えない）"
    return x, None


def _Rが例を指す(x: str, 番号たち, 例: dict):
    行たち = 番号たち["受付"].get(x, ())
    return None if any(_行が例を指す(q, 例) for q in 行たち) else _指す訳(f"受付番号 {x}", 例, 行たち)


# --- Q（回答のある質問と回答の問いの番号。形の正本は 初期設定/型の口.py の 問いの番号を読む）
def _Qを照らす(x: str, 番号たち, 今日: date, 会社名: str):
    q = _問いの番号を読む(x)
    if q is None:
        return x, f"問いの番号 {x} の月（Q<YYYYMM>）が暦に無い"
    if q[0] > f"{今日.year:04d}.{今日.month:02d}":
        return x, f"問いの番号 {x} の月 {q[0]} が今日 {今日} の月より後"
    if x not in 番号たち["問い"]:
        return x, f"問いの番号 {x} が {会社名} の質問と回答の答えのある問いに無い"
    return x, None


def _Qが例を指す(x: str, 番号たち, 例: dict):
    q = 番号たち["問い"].get(x)
    return None if q is not None and _行が例を指す(q, 例) else _指す訳(f"問いの番号 {x}", 例, [q] if q else ())


def _問いの表の行か(x) -> bool:
    return isinstance(x, (list, tuple, dict))


# --- 決定DB（`決定DB <YYYY-MM-DD> <行の URL か ⟦鍵:<分野>/<名>⟧>`）
_決定の日 = r"\d{4}-\d{2}-\d{2}"
_決定の鍵の印 = r"⟦鍵:[^\s⟦⟧/]+/[^\s⟦⟧]+⟧"
_決定の行のURL = r"https?://[^\s・、,;()「」⟦⟧]+"


def _決定DBを照らす(片, 鍵たち: set, 今日: date, 会社名):
    日, 印 = 片
    字 = f"決定DB {日} {印}"
    try:
        決めた日 = date.fromisoformat(日)
    except ValueError:
        return 字, f"決定DB の行の日付 {日} が暦に無い"
    if 決めた日 > 今日:
        return 字, f"決定DB の行の日付 {日} が今日 {今日} より後"
    if _決定の鍵(印) not in 鍵たち:
        return 字, f"決定DB の行 {印} が渡された決定DB の鍵の並びに無い（会話で答えた事は先に決定DB の行にし、その鍵を渡す）"
    return 字, None


def _決定DBが例を指す(片, 鍵たち, 例: dict):
    """決定DB の行が照らしている例を指すかは、その行の 会社 と 反映先（どの決まりの項目か見出しか）で判じる。証しの
    決定DB の鍵の並びは鍵の字だけで、その 2 つの列が無い＝判じられない＝通さない（既定で閉じる。列を足すまで例を照らす口では止める）。"""
    return (f"決定DB の行 {片[1]} が照らしている例（{_例の名(例)}）を指すかを判じられない: 渡された決定DB の鍵の並び（引数 "
            "`決定の鍵たち`）は鍵の字だけで、その行の 会社 と 反映先（この例の 決まり の項目か見出しか）の列が無い（例を照らす口では、"
            "決定DB の行は出所に数えない。例の確かめには、この例を指す答えの行の受付番号か問いの番号を書く）")


# --- 過去の結果（初期設定の照らし〔道具/答え合わせ〕でその資料のその人×項目が差 0 だった事。2026-11-19 オーナーの決定:
#     過去の資料で埋め切り、分からない物だけ聞く）。照らしの結果（差の表と答えの行の組）を証しに渡された時だけ、同じ支給月・会社・
#     NO・項目の差 0（一致）が在り、その人×項目の答えの行の出所の資料の名が書いた資料の名と字まで同じなら通す。支給月が今日の月より後なら止める
def 過去の結果の外れ(x: dict, 会社名: str, 一致: set, 出所: dict) -> list[tuple[str, str, str, str]]:
    """過去の結果の片（`過去の結果を読む` の 1 つ）→ 外れの並び [(何, NO, 項目, 答えの行の出所の字)]。空は通る。
    何: `一致していない`（差の表に差 0 で無い）・`資料が違う`（答えの行の出所と字まで同じでない）・`答えの行が食い違う`。
    一致: `照らしの一致` の返す物。出所: `答えの出所` の返す物。
    照らしの 1 か所（道具/答え合わせ の 出所を見る もこれを呼ぶ＝月次と道具で照らし方を分けない）。"""
    外: list[tuple[str, str, str, str]] = []
    for NO, 項目 in x["人と項目"]:
        k = (x["支給月"], unicodedata.normalize("NFKC", 会社名), unicodedata.normalize("NFKC", NO),
             unicodedata.normalize("NFKC", 項目))
        if k not in 一致:
            外.append(("一致していない", NO, 項目, ""))
        先 = 出所.get(k, "")
        if isinstance(先, 食い違う出所):
            外.append(("答えの行が食い違う", NO, 項目, "・".join(先)))
        elif not 資料の名が当たるか(x["資料の名"], 先):
            外.append(("資料が違う", NO, 項目, 先))
    return 外


def _過去の結果を照らす(x: dict, 支度, 今日: date, 会社名: str):
    字 = 過去の結果の字(x["支給月"], x["資料の名"], x["人と項目"])
    if x["支給月"] > f"{今日.year:04d}-{今日.month:02d}":
        return 字, f"過去の結果の支給月 {x['支給月']} が今日 {今日} の月より後"
    for 何, NO, 項目, 先 in 過去の結果の外れ(x, 会社名, *支度):
        if 何 == "一致していない":
            return 字, (f"過去の結果 {x['支給月']} {NO}:{項目} が渡された照らしの結果（差の表）に差 0 で無い"
                       "（照らしで一致した人×項目だけを出所にする）")
        if 何 == "答えの行が食い違う":
            return 字, (f"過去の結果 {x['支給月']} {NO}:{項目} の答えの行が 2 つ以上在り、出所の資料が食い違う（{先}）＝どの資料の"
                       "一致かを決めない（答えの行を 1 つにしてから照らす）")
        return 字, (f"過去の結果 {x['支給月']} {NO}:{項目} の資料の名「{x['資料の名']}」が、照らしの結果の答えの行のその人×項目の"
                   f"出所「{先 or '（その人×項目の答えの行が無い）'}」と字まで同じでない（答えの行の出所の file の名を"
                   "そのまま書く。拡張子は除いてよい）")
    return 字, None


def _過去の結果が例を指す(x: dict, 支度, 例: dict):
    """過去の結果の人×項目の項目が、どれも照らしている例の 決まり の項目か見出しの時だけ指す（例と関係の無い一致で例を通さない）。"""
    名たち, 見たち = _例の鍵(例)
    外 = [項目 for _, 項目 in x["人と項目"] if unicodedata.normalize("NFKC", 項目) not in 名たち | 見たち]
    if not 外:
        return None
    return (f"過去の結果 {x['支給月']} の項目「{外[0]}」が、照らしている例（{_例の名(例)}）の 決まり の項目"
            f"（{'・'.join(sorted(名たち)) or '無し'}）でも見出し（{'・'.join(sorted(見たち)) or '無し'}）でもない"
            "（例と関係の無い人×項目の一致は、その例の出所にしない）")


_照らしの組 = ("差の表", "答えの行")


def _照らしの結果の形(種類, 証し) -> str | None:
    """照らしの結果は {差の表, 答えの行} の組（dict）だけ受ける（差の表だけでは資料の名を照らせない＝止める）。
    差の表は行（list・tuple）の並び・答えの行は出所を持つ行（dict か 出所 の在る物）の並び。"""
    if not isinstance(証し, dict) or not set(_照らしの組) <= set(証し):
        return (f"{種類.証しの言葉}（引数 `{種類.証し}`）が {{{'・'.join(_照らしの組)}}} の組でない（{type(証し).__name__}）"
                "＝資料の名を照らせない形では照らさない")
    for 名, 要素 in (("差の表", 種類.要素), ("答えの行", lambda r: isinstance(r, dict) or hasattr(r, "出所"))):
        if not isinstance(証し[名], _並び):
            return f"{種類.証しの言葉}（引数 `{種類.証し}`）の {名} が並び（list・tuple・set）でない（{type(証し[名]).__name__}）"
        外 = [x for x in 証し[名] if not 要素(x)]
        if 外:
            return f"{種類.証しの言葉}（引数 `{種類.証し}`）の {名} の中に形の違う物が在る（{外[0]!r}）＝照らさない"
    return None


def _照らしの結果の支度(証し, 会社名):
    return 照らしの一致(証し["差の表"]), 答えの出所(証し["答えの行"])


出所の種類たち: dict[str, 出所の種類] = {k.名: k for k in (
    出所の種類("過去の結果", 言葉="過去の結果の照らし", 文法=_過去の結果の文法, 証し="照らしの結果",
             証しの言葉="照らしの結果（{差の表: 照らしの差の表, 答えの行: 照らした答えの行} の組）",
             書き方="過去の結果の照らし " + 過去の結果の書き方, 読む=_過去の結果の片,
             要素=lambda r: isinstance(r, (list, tuple)), 支度=_照らしの結果の支度, 照らす=_過去の結果を照らす,
             形=_照らしの結果の形, 関係=_過去の結果が例を指す),
    出所の種類("R", 言葉="受付番号", 文法=lambda: _受付番号の形().pattern, 証し="問いの表", 証しの言葉="質問と回答",
             書き方="確認ページの答えの受付番号 R<YYMMDD>-<英数 4 字>（質問と回答のその会社の答えのある問いの今の行に在る物）",
             読む=lambda m: (m.group(0), None), 要素=_問いの表の行か,
             支度=lambda 証し, 会社名: _表の番号たち(証し, 会社名), 照らす=_Rを照らす, 関係=_Rが例を指す),
    出所の種類("Q", 言葉="問いの番号", 文法=r"Q\d{6}-\d+", 証し="問いの表", 証しの言葉="質問と回答",
             書き方="回答のある問いの番号 Q<YYYYMM>-<順>（質問と回答のその会社の答えのある問い）",
             読む=lambda m: (m.group(0), None), 要素=_問いの表の行か,
             支度=lambda 証し, 会社名: _表の番号たち(証し, 会社名), 照らす=_Qを照らす, 関係=_Qが例を指す),
    出所の種類("決定DB", 言葉="決定DB の行",
             文法=rf"決定DB (?P<日>{_決定の日}) (?P<印>{_決定の行のURL}|{_決定の鍵の印})", 証し="決定の鍵たち",
             証しの言葉="決定DB の鍵の並び",
             書き方="決定DB の行 `決定DB <YYYY-MM-DD> <行の URL か ⟦鍵:<分野>/<名>⟧>`（間は半角の空白 1 つ。殻が決定DB から引いた"
                  "鍵の並びに在る物。例を照らす口では数えない）",
             読む=lambda m: ((m["日"], m["印"]), None), 要素=lambda k: isinstance(k, str),
             支度=lambda 証し, 会社名: {_決定の鍵(k) for k in 証し}, 照らす=_決定DBを照らす, 会社が要る=False,
             関係=_決定DBが例を指す),
)}
証しの名たち = tuple(dict.fromkeys(k.証し for k in 出所の種類たち.values()))
出所の書き方 = ("確かめた人 を `<答えた人の名>（<片>・<片>…）` の形で書く。片は "
           + "・".join(k.書き方 for k in 出所の種類たち.values())
           + " のどれか（片の間は ・ か 、 だけ。字の全体と片の 1 つ 1 つがこの文法に全体で当たる時だけ読み、ほかの字が 1 つでも在れば"
           "止める。どれも照らしの証しを渡した時だけ通る）")


def _片たちに分ける(中: str) -> tuple[list[tuple[出所の種類, re.Match]], str | None]:
    """括弧の中の字 → ([(種類, 文法に当たった字)], 止めの訳)。頭から、表の種類の文法に全体で当たる片と片の間（`_片の間`）を
    交互に読み、終わりまで読み切れた時だけ通す（読めない字が残れば、その片を訳に出す）。"""
    if not 中:
        return [], "括弧の中に片が無い"
    間 = re.compile(_片の間)
    out: list[tuple[出所の種類, re.Match]] = []
    i = 0
    while True:
        当たり = next(((k, m) for k in 出所の種類たち.values() for m in (k.片の形.match(中, i),) if m), None)
        if 当たり is None:
            片 = 間.split(中[i:], maxsplit=1)[0]
            return out, (f"表の種類として読めない片「{片}」が在る" if 片 else f"片の無い区切り「{中[i:] or 中}」が在る")
        out.append(当たり)
        i = 当たり[1].end()
        if i == len(中):
            return out, None
        j = 間.match(中, i).end()
        if j == len(中):
            return out, f"片の無い区切り「{中[i:]}」が在る"
        i = j


_見せない字 = "CMZ"   # Unicode の分類の頭（制御・書式・結合・空白）。確かめた人 の中は半角の空白のほかは見える字だけ


def 確かめた人を読む(字, *, 今日: date | None = None, 会社名: str | None = None, 種類たち=None, 問いの表=None,
               決定の鍵たち=None, 照らしの結果=None, 例: dict | None = None) -> tuple[str, list[str], str | None]:
    """例の 確かめた人 の字 → (答えた人の名, 読めた出所の並び, 止めの訳)。全角半角は NFKC でそろえて読む（`（）` と `()` は同じ）。
    字の全体が `<名>（<片>・<片>…）` の文法にぴったり当たり、どの片も `出所の種類たち` の表のどれかの種類の文法に全体で当たる時だけ
    読む（既定で閉じる: 見えない字・半角でない空白・括弧の外の字・片の間の ・ 、 のほかの字・どの文法にも当たらない片が在れば
    その字か片を訳に出して止める）。名では照らさない（誰が答えてもよい＝根は出所の照らし）。
    出所の照らしは表を引くだけ: 読めた片ごとに、その種類の証し（引数 問いの表・決定の鍵たち・照らしの結果。名は表の 証し）が
    渡されない・形が違う・照らして外れれば止める。今日 は渡さなければ時計の今日。
    種類たち: この口が出所に数える種類の名の並び（既定は表の全部）。並びに無い種類の片が在れば止める（移す口の締めは R・Q・決定DB）。
    会社名: 照らしに使う（どの会社の答え・照らしかを見ずに照らさない）。証しを渡して会社名が無ければ ValueError。
    例: 照らしている例の行（`確かめる` が渡す）。渡せば、表の 関係 を持つ種類の片は、この例を指す時だけ通す（R・Q は答えの今の行の
    反映先〔指し方の正本は `_行が例を指す`〕、過去の結果は人×項目の項目、決定DB は判じる列が無い＝通さない）。
    渡さない口（移す口の締め）は例との関係を見ない。"""
    s = unicodedata.normalize("NFKC", _字(字))
    if not s:
        return "", [], "確かめた人が空（例を事務所に確かめてもらい、" + 出所の書き方 + "）"
    見えない = next((c for c in s if c != " " and unicodedata.category(c)[0] in _見せない字), None)
    if 見えない is not None:
        return "", [], (f"確かめた人「{_字(字)}」に見えない字か半角でない空白（U+{ord(見えない):04X}）が在る"
                        f"（字の全体が文法に当たる時だけ読む。{出所の書き方}）")
    m = re.fullmatch(r"(?P<名>[^()]*?) ?\((?P<中>(?:[^()]|\([^()]*\))*)\)", s)
    if not m:
        if "(" not in s:
            return s, [], f"確かめた人「{_字(字)}」に確かめの出所が付いていない（{出所の書き方}）"
        return "", [], (f"確かめた人「{_字(字)}」が `<名>（<片>・<片>…）` の形に当たらない（外の括弧は 1 組だけで、中の括弧は"
                        f"名の中の 1 段の組だけ・括弧の後に字を書かない。{出所の書き方}）")
    名, 中 = m["名"].strip(), m["中"]
    if not 名:
        return "", [], f"確かめた人「{_字(字)}」に答えた人の名が無い（{出所の書き方}）"
    今日 = 今日 or date.today()
    証したち = {"問いの表": 問いの表, "決定の鍵たち": 決定の鍵たち, "照らしの結果": 照らしの結果}
    if set(証したち) != set(証しの名たち):
        raise AssertionError(f"確かめた人を読む の証しの引数 {sorted(証したち)} が表の証し {sorted(証しの名たち)} と違う")
    要る = [k.証し for k in 出所の種類たち.values() if k.会社が要る and 証したち[k.証し] is not None]
    if 要る and not 会社名:
        raise ValueError(f"確かめた人を読む: {要る[0]} を渡す時は 会社名 も渡す（どの会社の物かを見ずに照らさない）")
    通す = set(出所の種類たち) if 種類たち is None else set(種類たち)
    if isinstance(種類たち, str) or not 通す <= set(出所の種類たち):
        raise ValueError(f"確かめた人を読む: 種類たち は表の種類（{'・'.join(出所の種類たち)}）の並びで渡す")
    片たち, 外れ = _片たちに分ける(中)
    if 外れ:
        return 名, [], (f"確かめた人「{_字(字)}」の確かめの出所が読めない: {外れ}（括弧の中は、どの片も表の種類の文法に全体で"
                       f"当たる時だけ読む。{出所の書き方}）")
    読めた片: list[tuple[出所の種類, object]] = []
    for 種類, mm in 片たち:
        片, 形の止め = 種類.読む(mm)
        if 形の止め:
            return 名, [], f"確かめた人「{_字(字)}」の{形の止め}"
        読めた片.append((種類, 片))
    def _見せる(片) -> str:
        return 片 if isinstance(片, str) else (片[1] if isinstance(片, tuple) else 片["字"])
    # この口が数えない種類の片は、証しを照らす前に（片の並びに依らず）止める
    for 種類, 片 in 読めた片:
        if 種類.名 not in 通す:
            return 名, [], (f"確かめた人「{_字(字)}」の{種類.言葉}「{_見せる(片)}」はこの口では出所に数えない"
                            f"（数える種類: {'・'.join(k for k in 出所の種類たち if k in 通す)}）")
    支度: dict[str, object] = {}
    出所: list[str] = []
    for 種類, 片 in 読めた片:
        見せる = _見せる(片)
        証し = 証したち[種類.証し]
        if 証し is None:
            return 名, 出所, (f"確かめた人「{_字(字)}」の{種類.言葉} {見せる} を照らす{種類.証しの言葉}が渡されない"
                              f"（引数 `{種類.証し}`。照らせない＝通さない）")
        形 = 証しの形(種類, 証し)
        if 形:
            return 名, 出所, f"確かめた人「{_字(字)}」の{種類.言葉} {見せる}: {形}"
        if 種類.名 not in 支度:
            try:
                支度[種類.名] = 種類.支度(証し, 会社名)
            except ValueError as e:
                return 名, 出所, f"確かめた人「{_字(字)}」の{種類.言葉} {見せる}: {種類.証しの言葉}が読めない（{e}）"
        読めた, 訳 = 種類.照らす(片, 支度[種類.名], 今日, 会社名)
        if not 訳 and 例 is not None and 種類.関係 is not None:
            訳 = 種類.関係(片, 支度[種類.名], 例)
        if 訳:
            return 名, 出所, f"確かめた人「{_字(字)}」の{訳}"
        出所.append(読めた)
    return 名, 出所, None


def 確かめる(支給月: str, 会社名: str, タブ: dict, 例, *, 法の線: dict, 段, 繋, 今日: date | None = None,
          表A=None, 表B=None, 問いの表=None, 決定の鍵たち=None, 照らしの結果=None) -> dict:
    """その会社の例を全部、今のマスタ（タブ）の値で芯に通して照らす。返す物は頭の文のとおり。

    タブ: 段の解決.解く に渡すタブ（月を回す と同じ物）。例: 例の行（`MDから例を読む` が返す並び。get_values の形か dict の並びも
      受ける。None は渡されない）。
    法の線: 月を回す と同じ法の線。段・繋: 月次 が読み込んだ 段の解決・入口の文脈（同じ物を使う）。今日: 確かめた日の照らし（既定は今日）。
    例の 確かめた人 は `確かめた人を読む` で読み、確かめの出所（受付番号・決定DB の行・問いの番号・過去の結果の照らし）が無ければ通さない
      （2026-11-19 オーナーの決定。誰が答えてもよい＝名簿は照らさない）。問いの表（その会社の組の 質問と回答「質問」のタブ）・
      決定の鍵たち（殻が決定DB から引いた鍵か行の URL の並び）・照らしの結果（形は表の 証しの言葉）・今日 も同じに渡す
      ＝出所の種類ごとの証し（`出所の種類たち` の表）が渡されなければ、その種類の出所は通らない。

    例ごとの照らしの後に、2 つを照らす（2026-11-18 オーナーの決定）:
      覆い: マスタの会社の行と勤務の型に値のある勤務の数え方の決まり（`覆う名`）は全部、どれかの例の 決まり の欄に名が書かれている。
            社員の列に置いた数え方の決まり（`人で覆う名`）は、社員に在る値ごとに、人の値にその値を置いて名を書いた例が在る
            （社員の列の時間・時刻・数の形の値＝人ごとの契約の量〔日の所定 など〕は決まりの文の写しでない＝覆いに数えない）
      見分け: 例が名を書いた 1 日で見分けられる決まり（`日で見分ける名`）は、選べる値のほかの値に替えると、その名を書いた
              例のどれかが合わなくなる（替えても全部合う＝例はその値の取り違えを見分けない）。社員の列の決まりは例の人の値を替える。
              替えた値で思わぬ誤り（例の誤り でない例外）が出たら、見分けたか分からない＝止める
    表A・表B: その月に計算する人の確定した勤怠（月を回す が芯へ渡す物）。日の場面に結んだ決まりの覆い・見分けの外れは、場面に
      当たる人だけの 人の止め にする（当たる人が居なければ求めない）。渡さない・読めない時は会社の全員を止める（今までどおり）"""
    止め: list[str] = []
    合わない: list[dict] = []
    人の止め: dict[str, list[str]] = {}
    人の外れ: dict[str, list[dict]] = {}
    当たる = 日の場面.当たる人(表A, 表B, 会社名)   # None＝分からない（会社の全員で見る）

    def 外れを置く(x: dict) -> None:
        """覆い・見分けの外れを置く: 日の場面に結んだ決まりは、場面に当たる人だけを止める（誰も当たらなければ例を求めない）。
        覆い・見分けの 項目 は 決まり の欄の名 1 つ（見出しは無い）。"""
        x = {**x, "項目": {"決まり": [x["決まり"]], "見出し": []}}
        場面 = 日の場面.決まりの場面({x["決まり"]})
        if not 場面 or 当たる is None:
            合わない.append(x)
            return
        字 = f"{会社名} 例 {x['例の番号']}（{x['決まり']}・{'・'.join(sorted(場面))}の日がある人）: {x['訳']}"
        for NO in sorted(set().union(*(当たる[k] for k in 場面))):
            人の止め.setdefault(NO, []).append(字)
            人の外れ.setdefault(NO, []).append({"例の番号": x["例の番号"], "項目": x["項目"], "訳": x["訳"], "字": 字})
    今日 = 今日 or date.today()
    if 例 is None:
        return {"通った": False, "数": 0, "合わない": [], "人の止め": {}, "人の外れ": {}, "当たらない例": [], "止め": ["例が渡されない（殻は 給与のルール.md の字を 月を回す・賞与を回す の `給与のルール=` で渡す）"]}
    例たち = [e for e in 行たち(例) if _字(e.get("会社")) == 会社名]
    if not 例たち:
        return {"通った": False, "数": 0, "合わない": [], "人の止め": {}, "人の外れ": {}, "当たらない例": [],
                "止め": [f"{会社名} の例が 1 つも無い（給与のルール.md の決まりごとの見出しの下に例の表を書き、事務所が確かめる）"]}
    見た番号 = set()
    書いた名: dict[str, list[dict]] = {}
    当たらない例: list[str] = []
    求める: dict[str, list[str]] = {}   # 回す月と例の支給月で例の人に値が違い、回す月に値の在る名 → [例の番号]
    for e in 例たち:
        番号 = _字(e.get("例の番号")) or "（番号が無い）"

        def 外れ(訳, 番号=番号, e=e, **項目):
            合わない.append({"例の番号": 番号, "決まり": 例の所(e), "訳": 訳, **項目})

        if 番号 in 見た番号:
            外れ("例の番号が 2 つある")
            continue
        見た番号.add(番号)
        if 訳 := _型の口().見出しの区切りの訳(e.get("見出し")):   # 反映先で指せない見出し＝問いにせず（項目 None）訳で止める
            外れ(f"例が読めない: {訳}", 項目=None)
            continue
        種類 = _字(e.get("種類"))
        if 種類 not in 種類たち:
            外れ(f"種類「{種類}」は {'・'.join(種類たち)} のどれでもない")
            continue
        try:
            _人の値(e)   # 覆い・見分けは読めた例だけを数える（読めない人の値で後の照らしを落とさない。書けない 例も同じ）
        except 例の誤り as x:
            外れ(f"例が読めない: {x}")
            continue
        try:
            try:
                名たち = 例の決まりの名(e)
            except 例の誤り:
                if 種類 != "書けない":
                    raise
                名たち = set()   # 書けない例（読めない MD の表・行を含む）は名が読めなくても 書けない の訳で止める
            違う = {} if 種類 == "書けない" else 回す月に違う名(段, 支給月, 会社名, タブ, e)
        except 例の誤り as x:
            外れ(f"例が読めない: {x}")
            continue
        for n in sorted(n for n, 在る in 違う.items() if 在る):
            求める.setdefault(n, []).append(番号)
        当たる名 = 名たち - set(違う)
        if 名たち and not 当たる名:   # まだ当たらない・もう当たらない例は数えずに外す（照らさない・覆いと見分けにも数えない）
            当たらない例.append(番号)
            continue
        for n in 当たる名:   # 回す月に値の違う名は、その月の覆いと見分けに数えない（その月の値の例を求める）
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
            _, _, 出所の止め = 確かめた人を読む(e.get("確かめた人"), 今日=今日, 問いの表=問いの表, 会社名=会社名,
                                         決定の鍵たち=決定の鍵たち, 照らしの結果=照らしの結果, 例=e)
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
    # 回す月の決まりの値（例の人と同じ 段の解決.解く で引く。事務所・会社・勤務の型の段と、変更の記録で戻した人の段）
    型の段の値, 人の段の値 = _回す月の段(段, 支給月, 会社名, タブ)
    # 覆い: 回す月に事務所・会社・勤務の型の段で値のある勤務の数え方の決まりに、回す月に当たる例で名を書いた物が無い
    覆いで置いた = set()
    for n in sorted(覆う名()):
        if 型の段の値.get(n) and n not in 書いた名:
            覆いで置いた.add(n)
            外れを置く({"例の番号": "（覆い）", "決まり": n,
                       "訳": f"マスタに {n} の値があるのに、{支給月} に当たる例で決まり の欄に {n} を書いた物が無い（例を足し、事務所が確かめる）"})
    # 覆い（月）: 例の人に回す月と例の支給月で値の違う名（覆う名と例が 決まり の欄に書いた名・どれもマスタの項目の名）は、回す月に値が在れば回す月に当たる例で
    # その名を書いた物を求める（例の人の値＝人の値に置いた名も、どの段の値も同じ 解く で比べる）
    for n in sorted(set(求める) - set(書いた名) - 覆いで置いた):
        外れを置く({"例の番号": "（覆い）", "決まり": n,
                   "訳": f"{支給月} の {n} の値が例の支給月の値と違い（例 {'・'.join(求める[n])}）、"
                         f"{支給月} に当たる例で {n} を書いた物が無い（その月の値の例を足し、事務所が確かめる）"})
    from 芯 import 設定
    # 覆い（人）: 社員の列に置いた数え方の決まりの、回す月の人の段の値（変更の記録で戻した値）ごとに、人の値にその名を置き
    # 決まり に名を書いた例で、回す月に解いた値が同じ物が無い
    書いた値: dict[str, set[str]] = {}
    for n in sorted(人で覆う名()):
        for e in 書いた名.get(n, ()):
            if _人の値の例(e, n) is not None:
                書いた値.setdefault(n, set()).add(_人の段の字(_人の決まり(段, 支給月, 会社名, タブ, e), n))
    for n in sorted(人で覆う名()):
        選べる = {_ならす(x) for x in 設定.表()[n].get("選べる値") or ()}
        # 選べる値の外の字・読めない字の人は 段の解決 がその人を仮にする（ここで会社の全員を止めない）
        値たち = 人の段の値.get(n, {})
        for k in sorted(k for k in set(値たち) - 書いた値.get(n, set()) if not 選べる or k in 選べる):
            v = 値たち[k]   # 止めの文はマスタに書く字（解く の中の形でなく）
            外れを置く({"例の番号": "（覆い）", "決まり": n,
                       "訳": f"社員の列に {n}={v} の人が居るのに（{支給月} の値・変更の記録で戻した値）、人の値に {n}={v} を置いて"
                                f"決まり の欄に {n} を書いた {支給月} に当たる例が無い（その人の決まりの例を足し、事務所が確かめる）"})
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
                外れを置く({"例の番号": "（見分け）", "決まり": n,
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
                外れを置く({"例の番号": "（見分け）", "決まり": n, "訳": (
                    f"{n}{何} を {'・'.join(見分けない)} に替えても例が全部合う＝例がその取り違えを見分けない（違いが出る打刻の例を足す）")})
            if 数えられない:
                外れを置く({"例の番号": "（見分け）", "決まり": n,
                           "訳": f"{n}{何} を替えた値で例を数えられない＝見分けたか分からない（{'・'.join(数えられない)}）"})

        for n in sorted(set(書いた名) & 日で見分ける名()):
            日の例 = [e for e in 書いた名[n] if _字(e.get("種類")) == "日"]
            # 会社の行・勤務の型の値（人の値に n を置かない例で照らす）
            会社の例 = [e for e in 日の例 if _人の値の例(e, n) is None]
            会社の値 = {_ならす(v) for v in 型の段の値.get(n, ()) if isinstance(v, str)}
            if 会社の値 or 会社の例 or n not in 人で覆う名():
                今 = 会社の値 or {_ならす(設定.表()[n].get("既定"))}
                見分けを照らす(n, lambda alt, n=n, 例=会社の例: (_替えたタブ(段, 会社名, タブ, n, alt), 例), 会社の例, 今, "")
            # 人の値ごと（人の値に n=v を置いた例の v を替える）
            if n in 人で覆う名():
                for v in sorted({_人の値の例(e, n) for e in 日の例} - {None}):
                    例 = [e for e in 日の例 if _人の値の例(e, n) == v]
                    見分けを照らす(n, lambda alt, n=n, 例=例: (タブ, [_人の値を替えた例(e, n, alt) for e in 例]), 例, {v},
                                f"（人の値 {v}）")
    数 = len(例たち) - len(当たらない例)
    if not 数:
        止め.append(f"{会社名} の例に {支給月} に当たる例が 1 つも無い（当たらない例: {'・'.join(当たらない例)}。"
                  "その月の決まりの例を足し、事務所が確かめる）")
    # 例の行の外れの 項目: その番号の行の例の鍵（同じ番号の行が違う例を指せば決まらない＝None）
    鍵たち: dict[str, set] = {}
    for e in 例たち:
        名たち, 見たち = _例の鍵(e)
        鍵たち.setdefault(_字(e.get("例の番号")) or "（番号が無い）", set()).add((tuple(sorted(名たち)), tuple(sorted(見たち))))
    for i, x in enumerate(合わない):
        if "項目" not in x:
            k = 鍵たち.get(x["例の番号"], set())
            x = {**x, "項目": ({"決まり": list(next(iter(k))[0]), "見出し": list(next(iter(k))[1])} if len(k) == 1 else None)}
        合わない[i] = {**x, "字": f"{会社名} 例 {x['例の番号']}（{x['決まり'] or '決まりの欄が空'}）: {x['訳']}"}
    止め += [x["字"] for x in 合わない]
    return {"通った": not 合わない and bool(数), "数": 数, "合わない": 合わない, "止め": 止め, "人の止め": 人の止め,
            "人の外れ": 人の外れ, "当たらない例": 当たらない例}
