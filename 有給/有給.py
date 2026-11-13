"""有給の付与と残りを数え、有給休暇管理表の行を返す。Drive を開かない（殻が渡す値を受けて返す）。

  python3 有給/有給.py < 入力.json > 出力.json

入力・出力・選び方は 有給/README.md。
"""
import datetime as dt
import json
import sys
from decimal import Decimal
from pathlib import Path

ここ = Path(__file__).resolve().parent
根 = ここ.parent
if str(根) not in sys.path:
    sys.path.insert(0, str(根))

from 芯.計算 import 引く口  # noqa: E402  (法の表を引く口は 1 つ)

表の名 = "有給_付与日数"  # 法の表/有給_付与日数.json（基準＝労働した日・付与日で引く）
除く区分 = {"役員", "委託"}
週の分の上限 = 168 * 60  # 1 週は 168 時間。超える 時間.週の所定 は分で渡したとみて通さない（殻の ×60 が残った時の守り）


def 法の表(基準の日=None, 置き場=None) -> dict:
    """法の表/有給_付与日数 を、基準の日（付与日。無ければ今日）に効く行で引いた値。引けなければ 引く口.欠け（止める）。"""
    return 引く口.引く(表の名, 基準の日 or dt.date.today(), 置き場=置き場).値


def 型() -> dict:
    return json.loads((ここ / "型.json").read_text(encoding="utf-8"))


def 見出し() -> list[str]:
    return [c["名"] for c in 型()["列"]]


# ---- 日付 ----

def 日(s) -> dt.date | None:
    if not s:
        return None
    return dt.date.fromisoformat(str(s)[:10])


def 月を足す(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    末 = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return dt.date(y, m, min(d.day, 末))


def 時効の日(付与日: dt.date, 年: int) -> dt.date:
    return 月を足す(付与日, 12 * 年) - dt.timedelta(days=1)


# ---- 法の日数 ----

def _時間を分に(x) -> Decimal | None:
    """時間の数（`40`・`29.5`・`"30"`）→ 分（Decimal）。None は None。読めない・負は None。分に直すのは有給.py の中だけ。"""
    if x is None or isinstance(x, bool):
        return None
    try:
        h = Decimal(str(x).strip())
    except Exception:
        return None
    if not h.is_finite() or h < 0:
        return None
    return h * 60


def 法の日数(勤続の月: int, 週の所定日数=None, 週の所定時間=None, 表=None):
    """勤続の月と週の所定で引く法の付与日数 → (日数, 区分)。決められない時は (None, 理由)。

    週の所定時間は芯と同じ「時間の数」（`40`・`29.5`。段の解決が渡す `時間.週の所定` のまま）。中で分に直して表の上限（分）と比べる。
    週の所定時間が上限以上か、週の所定日数が上限を超えれば通常。どちらも上限より少なければ比例。"""
    表 = 表 or 法の表()
    段 = sum(1 for m in 表["勤続の月"] if 勤続の月 >= m) - 1
    if 段 < 0:
        return 0, "勤続 6 か月まで"
    時間の上限 = int(表["比例の週の所定時間の上限（分）"])
    日数の上限 = int(表["比例の週の所定日数の上限"])
    週の分 = _時間を分に(週の所定時間)
    if 週の所定時間 is not None and 週の分 is None:
        return None, f"時間.週の所定 {週の所定時間} を時間の数として読めない"
    if 週の分 is not None and 週の分 > 週の分の上限:
        return None, f"時間.週の所定 {週の所定時間} が週 168 時間を超える（分で渡したか。時間の数で渡す）"
    週の所定時間 = 週の分
    if 週の所定時間 is not None and 週の所定時間 >= 時間の上限:
        return 表["通常"][段], "通常"
    if 週の所定日数 is not None and int(週の所定日数) > 日数の上限:
        return 表["通常"][段], "通常"
    if 週の所定日数 is None:
        return None, "時間.週の所定日数 が無い"
    if 週の所定時間 is None:
        return None, "時間.週の所定 が無い（30 時間以上かで通常か比例かが決まる）"
    if int(週の所定日数) < 1:
        return 0, "週の所定日数 0"
    return 表["比例"][str(int(週の所定日数))][段], f"比例・週 {int(週の所定日数)} 日"


def 付与の日たち(入社日: dt.date, 終わり: dt.date, 揃えた日: str | None = None, 表=None):
    """終わりの日までの付与 → [(付与日, 段, 法の付与日)]。

    揃えた日（MM-DD）が有る時は、法の付与日ごとに (入社日, 法の付与日] の中で一番後の揃えた日へ前倒しする（無ければ法の付与日）。"""
    表 = 表 or 法の表()
    out, 段 = [], 0
    while True:
        月 = 表["勤続の月"][段] if 段 < len(表["勤続の月"]) else 表["勤続の月"][-1] + 12 * (段 - len(表["勤続の月"]) + 1)
        法の日 = 月を足す(入社日, 月)
        付与日 = 法の日
        if 揃えた日:
            mm, dd = (int(x) for x in 揃えた日.split("-"))
            for y in range(法の日.year, 入社日.year - 1, -1):
                try:
                    候補 = dt.date(y, mm, dd)
                except ValueError:
                    候補 = dt.date(y, mm, 28)
                if 入社日 < 候補 <= 法の日 and (not out or 候補 > out[-1][0]):
                    付与日 = 候補
                    break
        if 付与日 > 終わり:
            return out
        out.append((付与日, min(段, len(表["通常"]) - 1), 法の日))
        段 += 1


def 付与日数(段: int, 法の数, 区分: str, 会社の値: dict):
    """法の数と会社の選択から付与日数 → (日数, 仮の理由 or None)。会社の表が法を下回る段は法の数で仮。"""
    if 会社の値.get("有給.付与の表", "法の表") != "会社の表（法以上）" or not 区分.startswith("通常"):
        return 法の数, None
    表 = [x.strip() for x in str(会社の値.get("有給.会社の表") or "").replace("、", ",").split(",") if x.strip()]
    if len(表) != 7:
        return 法の数, "有給.会社の表 が無いか 7 つでない"
    数 = Decimal(表[段])
    if 数 < 法の数:
        return 法の数, "有給.会社の表 が法の表を下回る"
    return 数, None


# ---- 1 人を数える ----

def _取得の日数(r: dict, 一日の分) -> tuple[Decimal | None, str | None]:
    単位 = r.get("休暇の単位") or "全日"
    if 単位 == "全日":
        return Decimal(1), None
    if 単位 in ("午前半休", "午後半休"):
        return Decimal("0.5"), None
    if 単位 == "時間":
        if not 一日の分:
            return None, "有給.1日の時間 が無い（時間単位の有給を日に直せない）"
        return Decimal(int(r.get("休暇の時間") or 0)) / Decimal(int(一日の分)), None
    return None, f"休暇の単位 {単位} を読めない"


def 一人(p: dict, 入力: dict, 表: dict, 置き場=None) -> tuple[dict, list[dict]]:
    """表は基準の日に効く行（付与の日の並び）。各付与の日数・時効・年 5 日はその付与日に効く行で引き直す。"""
    会社, 支給月, 基準 = 入力["会社"], 入力["支給月"], 日(入力["基準の日"])
    会社の値 = 入力.get("会社の値", {})
    問い, 仮 = [], []

    def 聞く(何, 質問, 見当, 拠り所, 例):
        問い.append({"会社": 会社, "支給月": 支給月, "誰に": "先方", "何が無いか": 何, "質問": 質問,
                    "見当": 見当, "見当の拠り所": 拠り所, "答えで変わる項目と人": f"有給の残り、NO {p['NO']}", "答え方の例": 例})
        仮.append(何)

    入社日 = 日(p.get("入社日"))
    if not 入社日:
        聞く("入社日", f"NO {p['NO']} の方の入社日を教えてください。", "", "無し", "YYYY-MM-DD")
        return {"会社": 会社, "支給月": 支給月, "NO": p["NO"], "氏名": p.get("氏名", ""), "状態": "仮"}, 問い
    揃えた日 = 会社の値.get("有給.揃えた日") if 会社の値.get("有給.付与の基準日") == "会社で揃えた日（斉一的付与）" else None
    if 会社の値.get("有給.付与の基準日") == "会社で揃えた日（斉一的付与）" and not 揃えた日:
        聞く("有給.揃えた日", "有給を揃えて与える日（毎年の月日）を教えてください。", "入社日から数えた日", "有給.付与の基準日 の既定", "見当のとおり／MM-DD")
    足りない付与 = {日(x) for x in p.get("出勤率が足りない付与日", [])}

    付与たち = []
    for 付与日, 段, 法の日 in 付与の日たち(入社日, 基準, 揃えた日, 表):
        勤続 = (法の日.year - 入社日.year) * 12 + 法の日.month - 入社日.month
        その表 = 法の表(付与日, 置き場)  # 付与日に効く行（日数・時効・年 5 日）
        法の数, 区分 = 法の日数(勤続, p.get("時間.週の所定日数"), p.get("時間.週の所定"), その表)
        if 法の数 is None:
            聞く(区分.split(" ")[0], f"NO {p['NO']} の方の週の所定（日数と時間）を教えてください。", "週 5 日", "時間.週の所定日数 の既定",
                 "見当のとおり／週 N 日・N 時間")
            法の数, 区分 = 法の日数(勤続, 5, None, その表)
        数, 理由 = 付与日数(段, 法の数, 区分, 会社の値)
        if 理由:
            聞く("有給.会社の表", f"会社の有給の付与日数の表を教えてください（{理由}）。", f"法の表（{法の数} 日）", "法の表", "見当のとおり／7 つの日数")
        if 付与日 in 足りない付与:
            数 = Decimal(0)
        付与たち.append({"付与日": 付与日, "日数": Decimal(数), "残り": Decimal(数), "時効": 時効の日(付与日, int(その表["時効の年"])), "使った": [],
                      "表": その表})

    # 数え始め: 有給の始めの日の残り。無ければ入社日から（勤怠が入社日から揃っている時だけ）
    始め = 日(p.get("有給の始めの日"))
    勤怠の始め = 日(入力.get("勤怠の始め"))
    if 始め:
        生き = [g for g in 付与たち if g["付与日"] <= 始め <= g["時効"]]
        for g in 付与たち:
            if g["付与日"] <= 始め:
                g["残り"] = Decimal(0)
        if 生き:
            生き[-1]["残り"] = Decimal(str(p.get("有給の始めの残り") or 0))
        if len(生き) > 1:
            生き[-2]["残り"] = Decimal(str(p.get("有給の始めの繰越") or 0))
    else:
        始め = 入社日 - dt.timedelta(days=1)
        if 勤怠の始め and 勤怠の始め > 入社日 and any(g["付与日"] < 勤怠の始め for g in 付与たち):
            聞く("有給の始めの残り", f"NO {p['NO']} の方の、今の有給の残りの日数（前の年からの繰越を分けて）を教えてください。",
                 "0 日", "無し（入社日からの勤怠が無い）", "N 日（うち繰越 M 日）")

    for g in 付与たち:
        g["初め"] = g["残り"]
    取得 = []
    for r in 入力.get("勤怠", []):
        if str(r.get("NO")) != str(p["NO"]) or r.get("休暇の種類") != "年休":
            continue
        d = 日(r.get("日付"))
        if not d or d <= 始め or d > 基準:
            continue
        n, 理由 = _取得の日数(r, p.get("有給.1日の時間"))
        if 理由:
            聞く(理由.split(" ")[0], f"NO {p['NO']} の方の {d} の有給の時間を日に直せません（{理由}）。", "1 日", "全日とみなした", "見当のとおり／N 時間")
            n = Decimal(1)
        取得.append((d, n, r.get("支給月")))
    取得.sort(key=lambda x: x[0])

    超えた = Decimal(0)
    for d, n, _ in 取得:
        残す = n
        for g in 付与たち:
            if g["付与日"] <= d <= g["時効"] and g["残り"] > 0 and 残す > 0:
                使う = min(g["残り"], 残す)
                g["残り"] -= 使う
                g["使った"].append((d, 使う))
                残す -= 使う
        超えた += 残す
    if 超えた > 0:
        聞く("有給の残り", f"NO {p['NO']} の方の有給の取得が残りを {超えた} 日超えています。残りの日数か取得の日を教えてください。",
             "", "勤怠の年休と付与の数が合わない", "N 日／取得の日の直し")

    生き = [g for g in 付与たち if g["付与日"] <= 基準 <= g["時効"]]
    今 = 生き[-1] if 生き else None
    前 = 生き[-2] if len(生き) > 1 else None
    今月 = [(d, n) for d, n, pm in 取得 if pm == 支給月]
    行 = {"会社": 会社, "支給月": 支給月, "NO": p["NO"], "氏名": p.get("氏名", "")}
    if 今:
        年の終わり = 月を足す(今["付与日"], 12) - dt.timedelta(days=1)
        年の取得 = sum((n for d, n, _ in 取得 if 今["付与日"] <= d <= 年の終わり), Decimal(0))
        五日 = 今["日数"] >= int(今["表"]["年5日の付与日数の下限"])
        行.update({
            "付与日": 今["付与日"].isoformat(),
            "付与日数": _数(今["日数"]),
            "繰越日数": _数(前["初め"] - sum((n for d, n in 前["使った"] if d < 今["付与日"]), Decimal(0))) if 前 else "0",
            "付与日からの取得日数": _数(sum((n for d, n, _ in 取得 if d >= 今["付与日"]), Decimal(0))),
            "年5日の期限": 年の終わり.isoformat() if 五日 else "",
            "年5日の残り": _数(max(Decimal(0), Decimal(int(今["表"]["年5日の日数"])) - 年の取得)) if 五日 else "",
            "時効の日": (前 or 今)["時効"].isoformat(),
        })
    else:
        行.update({"付与日": "", "付与日数": "0", "繰越日数": "0", "付与日からの取得日数": "0", "年5日の期限": "", "年5日の残り": "", "時効の日": ""})
    行["今月の取得日数"] = _数(sum((n for _, n in 今月), Decimal(0)))
    行["今月の取得日"] = "、".join(d.isoformat() for d, _ in 今月)
    行["残日数"] = _数(sum((g["残り"] for g in 生き), Decimal(0)))
    次 = 付与の日たち(入社日, 月を足す(基準, 13), 揃えた日, 表)
    次 = [x for x in 次 if x[0] > 基準]
    if 次:
        付与日, 段, 法の日 = 次[0]
        勤続 = (法の日.year - 入社日.year) * 12 + 法の日.month - 入社日.month
        try:
            次の表 = 法の表(付与日, 置き場)  # 次の付与日に効く行。まだ無ければ次の付与日数は空（前の行で代えない）
        except 引く口.欠け:
            次の表 = None
        法の数, 区分 = 法の日数(勤続, p.get("時間.週の所定日数"), p.get("時間.週の所定"), 次の表) if 次の表 else (None, "")
        数 = 付与日数(段, 法の数, 区分, 会社の値)[0] if 法の数 is not None else None
        行["次の付与日"], 行["次の付与日数"] = 付与日.isoformat(), (_数(数) if 数 is not None else "")
    else:
        行["次の付与日"], 行["次の付与日数"] = "", ""
    行["状態"] = "仮" if 仮 else "確定"
    return 行, 問い


def _数(x) -> str:
    x = Decimal(x)
    return str(x.quantize(Decimal(1))) if x == x.to_integral() else str(x.normalize())


def 管理表(入力: dict, 置き場=None) -> dict:
    """入力（README の形）→ {"見出し", "行", "問い"}。役員・委託の人は出さない。退職日が基準の日より前の人も出さない。
    置き場は法の表の置き場（試験だけ渡す・既定は repo の 法の表/）。"""
    基準 = 日(入力["基準の日"])
    表 = 法の表(基準, 置き場)
    行たち, 問いたち = [], []
    for p in 入力.get("人", []):
        if p.get("人.区分") in 除く区分:
            continue
        退職 = 日(p.get("退職日"))
        if 退職 and 退職 < 基準:
            continue
        行, 問い = 一人(p, 入力, 表, 置き場)
        行たち.append({k: 行.get(k, "") for k in 見出し()})
        問いたち += 問い
    return {"見出し": 見出し(), "行": 行たち, "問い": 問いたち}


if __name__ == "__main__":
    json.dump(管理表(json.load(sys.stdin)), sys.stdout, ensure_ascii=False, indent=1)
    print()
