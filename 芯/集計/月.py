"""1 人×1 月: 休日の区分・週と制度の判定・日数・月の数字（縦の形）。"""
from datetime import date, timedelta
from decimal import Decimal

from . import 日 as 日の
from . import 会社の残業
from .形 import (仮, 決まり, 法の線, 形の誤り, 空, 整数, 時間の分, 日付, 曜日, 詰め, 月の語, 単位, 分ける語, 時間の語)

週の起算の既定 = "日"
所定の無い区分 = ("委託",)  # 人.区分 がこれなら所定が無い（入口/口.py の 所定の無い区分 と同じ語）


def 週の頭(d: date, 起算: str) -> date:
    return d - timedelta(days=(d.weekday() - 曜日.index(起算)) % 7)


def 休日の区分を決める(行たち: list[dict], 決: 決まり, 線: 法の線, 起算: str, 知っている日: set) -> tuple[dict, list]:
    """休日・休日勤務の日を 法定／所定 に分ける。表 A に区分があればそれ、空なら `休日.法定休日の決め方`。"""
    暦, 仮たち, 待ち = {}, [], []
    for r in 行たち:
        if r["日の種類"] not in ("休日", "休日勤務"):
            continue
        k = r.get("休日の区分") or ""
        if k in ("法定", "所定"):
            暦[r["日付"]] = k
        elif k:
            仮たち.append(仮(f"休日の区分「{k}」は選べる値の外", r["日付"]))
            待ち.append(r)
        else:
            待ち.append(r)
    if not 待ち:
        return 暦, 仮たち
    決め方 = 詰め(決.引く("休日.法定休日の決め方")) or "曜日を決める"
    種類 = {r["日付"]: r["日の種類"] for r in 行たち}
    if 決め方 == "曜日を決める":
        曜 = 決.引く("休日.法定休日の曜日") or "日"
        for r in 待ち:
            暦[r["日付"]] = "法定" if 曜日[r["日付"].weekday()] == 曜 else "所定"
        return 暦, 仮たち
    if 決め方 == "週の最後の休日":
        週たち = {}
        for r in 待ち:
            週たち.setdefault(週の頭(r["日付"], 起算), []).append(r["日付"])
        for 頭, 日たち in 週たち.items():
            週 = [頭 + timedelta(days=i) for i in range(7)]
            if any(暦.get(x) == "法定" for x in 週):
                for x in 日たち:
                    暦[x] = "所定"
                continue
            休んだ = [x for x in 週 if 種類.get(x) == "休日"]
            働いた = sorted(x for x in 日たち if 種類.get(x) == "休日勤務")
            法定の日 = 休んだ[-1] if 休んだ else (働いた[-1] if 働いた else None)
            for x in 日たち:
                暦[x] = "法定" if x == 法定の日 else "所定"
            if not 休んだ and any(x not in 知っている日 for x in 週):
                for x in 働いた:
                    仮たち.append(仮("週の最後の休日が期間の外にかかり法定休日が決まらない", x))
        return 暦, 仮たち
    if 決め方 == "4週4休":
        起算日 = 決.引く("休日.4週の起算日")
        数 = 線.四週の休日数
        if 起算日 is None or 数 is None:
            理由 = "休日.4週の起算日 が無い" if 起算日 is None else "法の線に 休日.4週の休日数 が無い"
            for r in 待ち:
                暦[r["日付"]] = "法定"
                if r["日の種類"] == "休日勤務":
                    仮たち.append(仮(f"{理由}（休日勤務を法定で置いた）", r["日付"]))
            return 暦, 仮たち
        起算日 = 日付(起算日)
        塊たち = {}
        for r in 待ち:
            塊たち.setdefault((r["日付"] - 起算日).days // 28, []).append(r["日付"])
        for i, 日たち in 塊たち.items():
            塊 = [起算日 + timedelta(days=i * 28 + j) for j in range(28)]
            休んだ = sum(1 for x in 塊 if 種類.get(x) == "休日")
            足りない = max(0, 数 - 休んだ - sum(1 for x in 塊 if 暦.get(x) == "法定" and 種類.get(x) == "休日勤務"))
            働いた = sorted(x for x in 日たち if 種類.get(x) == "休日勤務")
            法定たち = set(働いた[len(働いた) - 足りない:]) if 足りない else set()
            for x in 日たち:
                暦[x] = "法定" if x in 法定たち or 種類.get(x) == "休日" else "所定"
            if any(x not in 知っている日 for x in 塊):
                for x in 働いた:
                    仮たち.append(仮("4 週の塊が期間の外にかかり法定休日が決まらない", x))
        return 暦, 仮たち
    for r in 待ち:
        暦[r["日付"]] = "法定" if 曜日[r["日付"].weekday()] == "日" else "所定"
    仮たち.append(仮(f"休日.法定休日の決め方「{決め方}」は選べる値の外（日曜を法定で置いた）"))
    return 暦, 仮たち


def 週の法定(決: 決まり, 線: 法の線) -> tuple[int, list]:
    v = 時間の分(決.引く("時間.週の法定"))
    if v is None or v <= 線.週の法定 or v == 線.週の法定の特例:
        return (v or 線.週の法定), []
    return 線.週の法定, [仮("時間.週の法定 が法の線を超える（法の線で数えた）", None, frozenset(分ける語))]


def 移す(結果たち: list, 量: int, 元: tuple[str, ...], 先: str = "法定外"):
    """後ろの日から順に、元の時間を先へ移す（後に働いた分ほど超えた分）。"""
    for r in sorted(結果たち, key=lambda r: r.日付, reverse=True):
        for a in 元:
            if 量 <= 0:
                return
            x = min(量, getattr(r, a))
            setattr(r, a, getattr(r, a) - x)
            setattr(r, 先, getattr(r, 先) + x)
            量 -= x


def 一人を集計する(日たち: list[dict], 区間たち: list[dict], 決まりの値: dict, 線: 法の線,
                 前の日たち: list[dict] = (), 前の区間たち: list[dict] = ()) -> dict:
    """1 人×1 支給月の表 A・B から、月の数字（縦の形）を出す。

    前の日たち・前の区間たち: 期間の頭の週が前の期間にかかる時の、前の期間の表 A・B（週の判定にだけ使う）。
    """
    決 = 決まり(決まりの値 or {})
    人 = {k: 日たち[0].get(k, "") for k in ("支給月", "会社", "NO", "勤怠の表記")}
    仮たち, 知らせ = [], []

    def 読む(行たち):
        out = {}
        for r in 行たち:
            r = dict(r)
            try:
                r["日付"] = 日付(r["日付"])
            except (形の誤り, KeyError) as e:
                仮たち.append(仮(f"表 A の日付が読めない: {e}"))
                continue
            if r["日付"] in out:
                仮たち.append(仮("表 A に同じ日が 2 行ある", r["日付"]))
                continue
            if r.get("日の種類") not in ("勤務", "休日勤務", "休暇", "欠勤", "休日", "休職・休業"):
                仮たち.append(仮(f"日の種類「{r.get('日の種類')}」は選べる値の外", r["日付"]))
                r["日の種類"] = "欠勤"
            out[r["日付"]] = r
        return out

    今 = 読む(日たち)
    前 = {d: r for d, r in 読む(前の日たち).items() if d not in 今}
    if not 今:
        return {"人": 人, "行": [], "仮": 仮たち, "知らせ": 知らせ, "日": {}}
    始め, 終わり = min(今), max(今)
    期間 = [始め + timedelta(days=i) for i in range((終わり - 始め).days + 1)]
    欠けた日 = [d for d in 期間 if d not in 今]
    for d in 欠けた日:
        仮たち.append(仮("期間の日に表 A の行が無い", d))
    区間 = {}
    for b in list(区間たち) + list(前の区間たち):
        try:
            区間.setdefault(日付(b["日付"]), []).append(b)
        except (形の誤り, KeyError):
            仮たち.append(仮("表 B の日付が読めない"))
    for d in 区間:
        if d not in 今 and d not in 前:
            仮たち.append(仮("表 B の区間に表 A の行が無い", d))

    起算 = 決.引く("時間.週の起算") or 週の起算の既定
    if 起算 not in 曜日:
        仮たち.append(仮(f"時間.週の起算「{起算}」は曜日でない（日で数えた）"))
        起算 = 週の起算の既定
    全 = {**前, **今}
    暦, 暦の仮 = 休日の区分を決める(list(全.values()), 決, 線, 起算, set(全))
    仮たち += [x for x in 暦の仮 if x.日付 is None or x.日付 in 今]

    def 区分を引く(x: date):
        """日またぎで引く日の休日の区分。表 A に無い日（期間の外）は決まりで出す。"""
        if x in 全:
            return 暦.get(x), None
        if (詰め(決.引く("休日.法定休日の決め方")) or "曜日を決める") == "曜日を決める":
            return ("法定" if 曜日[x.weekday()] == (決.引く("休日.法定休日の曜日") or "日") else None), None
        return None, "日またぎの勤務が表 A に無い日にかかり、その日が法定休日か決まらない（法定休日でないとして数えた）"

    結果 = {}
    for d, r in sorted(全.items()):
        結果[d] = 日の.日を数える(r, 区間.get(d, []), 決, 線, 区分を引く)
    for d in 今:
        仮たち += 結果[d].仮たち
        知らせ += 結果[d].知らせ
    今の結果 = [結果[d] for d in sorted(今)]

    # 週と制度の判定
    制度, 誤り = 日の.制度の値(決, None)
    仮たち += 誤り
    線の週, 誤り = 週の法定(決, 線)
    仮たち += 誤り
    印 = {}

    def 印す(項目, 文):
        印.setdefault(項目, []).append(文)

    # 委託だけの人（人.区分＝委託）は労基法の労働者でない＝前の期間の日を求めない（週の判定の仮を出さない）。
    # 週の移しは委託の式（芯/計算/委託.py の月額の残業）が受ける数なので今までどおり数える（期間の中の日だけで）。
    # 委託の併用の人の雇用分は労働者＝今までどおり前の期間の日を求める。
    委託だけ = 詰め(決.引く("人.区分")) in 所定の無い区分
    if 制度 in 日の.通常系 + 日の.変形:
        週の所定 = 時間の分(決.引く("時間.週の所定"))
        for 頭 in sorted({週の頭(d, 起算) for d in 今}):
            週 = [頭 + timedelta(days=i) for i in range(7)]
            線のこの週 = 線の週
            if 制度 in 日の.変形:
                知る = [結果[x].所定 for x in 週 if x in 結果]
                線のこの週 = max(線の週, 週の所定 if 週の所定 is not None and len(知る) < 7 else sum(知る))
            累 = 0
            移した = False
            for x in 週:
                if x not in 結果:
                    continue
                r = 結果[x]
                超え = min(r.法定外でない, max(0, 累 + r.法定外でない - 線のこの週))
                累 += r.法定外でない
                if 超え and x in 今:
                    移す([r], 超え, ("法定内", "所定内"))
                    移した = True
            # みなした日（定時扱い: 出勤簿が無い人を所定どおりとみなした日など）の時間も働いた時間と同じに週の線で数える。
            # 変形でない（時間.制度 が通常系）なら週の法定を超えた分は法定外＝37 条の割増（仮にしない）。変形なら上の週の線に従う。
            前が無い = [x for x in 週 if x < 始め and x not in 結果]
            if 前が無い and not 委託だけ and any(結果[x].法定外でない for x in 週 if x in 今):
                仮たち.append(仮("期間の頭の週が前の期間にかかり、前の期間の日を受けていない（週の法定の判定）",
                               頭, frozenset(分ける語)))
            if 制度 in 日の.変形 and 移した and any(x not in 結果 for x in 週) and 週の所定 is None:
                仮たち.append(仮("変形の週の所定が期間の外にかかり決まらない（時間.週の所定 が無い）",
                               頭, frozenset(分ける語)))
        if 制度 == "1か月変形":
            期 = 決.引く("時間.変形の期間") or {}
            if isinstance(期, dict) and 期.get("起算日") and 日付(期["起算日"]).day != 始め.day:
                仮たち.append(仮("1 か月変形の期間が給与の期間と揃っていない（期間の総枠を給与の期間で数えた）",
                               None, frozenset(分ける語)))
            総枠 = 線の週 * len(期間) // 7
            超え = sum(r.法定外でない for r in 今の結果) - 総枠
            if 超え > 0:
                移す(今の結果, 超え, ("法定内", "所定内"))
        elif 制度 == "1年変形":
            印す("法定外残業", "1 年変形の期間の総枠は期間の終わりに清算する（この月は日と週だけ）")
            期 = 決.引く("時間.変形の期間") or {}
            if isinstance(期, dict) and 期.get("終わりの日") and 始め <= 日付(期["終わりの日"]) <= 終わり:
                仮たち.append(仮("1 年変形の期間の終わりの月（期間の総枠の清算は期間の全部の日が要る）",
                               None, frozenset(分ける語)))
    elif 制度 == "フレックス":
        期 = 決.引く("時間.フレックスの清算期間") or {}
        所定総 = 時間の分(期.get("総労働時間")) if isinstance(期, dict) else None
        if 所定総 is None:
            所定総 = sum(r.所定 for r in 今の結果)
            仮たち.append(仮("時間.フレックスの清算期間 の総労働時間が無い（日の所定の和で置いた）",
                           None, frozenset(分ける語 + ("遅刻早退",))))
        if not (isinstance(期, dict) and 期.get("起算日") and 期.get("終わりの日")
                and 日付(期["起算日"]) == 始め and 日付(期["終わりの日"]) == 終わり):
            仮たち.append(仮("フレックスの清算期間が給与の期間と同じでない（1 か月を超える清算はこの部品で書けない）",
                           None, frozenset(分ける語 + ("遅刻早退",))))
        総 = sum(r.所定内 for r in 今の結果)
        枠 = 線の週 * len(期間) // 7
        移す(今の結果, max(0, 総 - 枠), ("所定内",))
        移す(今の結果, max(0, min(総, 枠) - 所定総), ("所定内",), "法定内")
        if 所定総 > 総:
            今の結果[-1].遅刻早退 += 所定総 - 総
            印す("遅刻早退", "フレックスの清算期間の不足の時間")
    else:  # 管理監督者・高度プロフェッショナル
        for r in 今の結果:
            r.所定内 += r.法定内 + r.法定外 + r.法定休日
            r.法定内 = r.法定外 = r.法定休日 = 0
            r.遅刻早退 = 0
        印す("所定内", f"{制度}（時間外・休日の割増の外。全部を所定内に置いた）")

    # 日数と月の数字
    値 = {k: (Decimal(0) if u == "日" else 0) for k, u in 月の語 if u != "日付"}
    出所 = {k: [] for k, _ in 月の語}
    年休の日 = []

    def 足す(項目, x, d):
        if x:
            値[項目] += x
            出所[項目].append(d)

    夜勤の数え方 = 詰め(決.引く("時間.夜勤の出勤日数"))
    半休の数え方 = 詰め(決.引く("時間.半休の日の数え方")).replace("+", "＋")
    休出 = 決.引く("休日.休日出勤の数え方") or {}
    休出に入れる = 詰め(休出.get("出勤日数に入れる")) if isinstance(休出, dict) else ""
    for 名, v, 選べる in (("時間.夜勤の出勤日数", 夜勤の数え方, ("", "1勤務=1日", "1勤務=2日")),
                        ("時間.半休の日の数え方", 半休の数え方, ("", "有給0.5＋出勤0.5", "有給0.5＋出勤1")),
                        ("休日.休日出勤の数え方 の 出勤日数に入れる", 休出に入れる, ("", "入れる", "入れない"))):
        if v not in 選べる:
            仮たち.append(仮(f"{名}「{v}」は選べる値の外（既定で数えた）", None,
                           frozenset({"出勤日数", "休日勤務日数（法定）", "休日勤務日数（所定）"})))
    半 = Decimal(1) / 2
    所定が無い = 委託だけ  # 委託など: 働いた日は所定日数に数えない（出勤日数だけ）
    for r in 今の結果:
        a = 今[r.日付]
        d = r.日付
        型 = a.get("勤務の型") or None
        休 = a.get("休暇の種類") or ""
        休の単位 = a.get("休暇の単位") or ""
        if r.種類 not in ("休日", "休日勤務") and not 所定が無い:
            足す("所定日数", Decimal(1), d)
        if r.種類 == "勤務":
            日数 = Decimal(2) if r.夜勤 and 詰め(決.引く("時間.夜勤の出勤日数", 型)) == "1勤務=2日" else Decimal(1)
            if 休の単位 in ("午前半休", "午後半休") and 詰め(決.引く("時間.半休の日の数え方", 型)).replace("+", "＋") != "有給0.5＋出勤1":
                日数 -= 半
            足す("出勤日数", 日数, d)
        elif r.種類 == "休日勤務":
            足す("休日勤務日数（法定）" if 暦.get(d) == "法定" else "休日勤務日数（所定）", Decimal(1), d)
            if 休出に入れる == "入れる":
                足す("出勤日数", Decimal(1), d)
        elif r.種類 == "欠勤":
            足す("欠勤", Decimal(1), d)
        elif r.種類 == "休職・休業":
            足す("休業", Decimal(1), d)
        # 休暇
        if 休 and r.種類 in ("勤務", "休暇"):
            量 = Decimal(1) if 休の単位 == "全日" else 半 if 休の単位 in ("午前半休", "午後半休") else Decimal(0)
            if 休 == "年休":
                if 休の単位 == "全日":
                    足す("年休（全日）", Decimal(1), d)
                elif 休の単位 in ("午前半休", "午後半休"):
                    足す("年休（半日）", 1, d)
                elif 休の単位 == "時間":
                    try:
                        足す("年休（時間）", 整数(a.get("休暇の時間")) or 0, d)
                    except 形の誤り as e:
                        仮たち.append(仮(f"表 A の形の誤り: {e}", d))
                if 休の単位 in ("全日", "午前半休", "午後半休"):
                    年休の日.append(d)
            elif 休 == "特別休暇（有給）" or (休 in 日の.看護など and 日の.休暇は有給か(休, 決)):
                足す("特別休暇（有給）", 量, d)
            elif 休 == "特別休暇（無給）" or 休 in 日の.看護など:
                足す("特別休暇（無給）", 量, d)
            elif 休 == "出勤扱い" and r.種類 == "休暇":
                足す("出勤日数", 量, d)
            elif 休 == "代休":
                知らせ.append(f"{d}: 代休の日（月の数字の語に代休が無い。代休の相手の日 {a.get('代休の相手の日', '')}）")
            if 休の単位 == "時間" and 休 != "年休":
                知らせ.append(f"{d}: 時間単位の「{休}」（月の数字の語は日で持つので数えていない）")
        if r.種類 == "休暇" and not 休:
            仮たち.append(仮("休暇の日に休暇の種類が無い", d))
        if r.種類 == "休暇" and 休の単位 in ("午前半休", "午後半休"):
            仮たち.append(仮("半休だけで勤務の無い日（残りの半日が分からない。半休として数えた）", d))
        足す("所定内", r.所定内, d)
        足す("法定内残業", r.法定内, d)
        足す("法定外残業", r.法定外, d)
        足す("法定休日", r.法定休日, d)
        足す("所定休日", r.所定休日, d)
        足す("深夜", r.深夜, d)
        足す("遅刻早退", r.遅刻早退, d)
        足す("夜勤の回数", 1 if r.夜勤 else 0, d)
        for k, v in r.印.items():
            印.setdefault(k, []).extend(v)
    値["総労働"] = 値["所定内"] + 値["法定内残業"] + 値["法定外残業"] + 値["法定休日"]
    出所["総労働"] = sorted(set(出所["所定内"] + 出所["法定内残業"] + 出所["法定外残業"] + 出所["法定休日"]))
    if 線.六十時間 is None:
        仮たち.append(仮("法の線に 割増.60時間超の境 が無い", None, frozenset({"60 時間超"})))
    else:
        値["60 時間超"] = max(0, 値["法定外残業"] - 線.六十時間)
        if 値["60 時間超"]:
            出所["60 時間超"] = 出所["法定外残業"]

    会社 = 会社の残業.数える(決, 線, 制度, 今の結果, 値)
    if 会社:
        仮たち += 会社["仮"]
        知らせ += 会社["知らせ"]

    行たち = []
    for 項目, u in 月の語:
        if 項目 == "年休を取った日":
            for d in 年休の日:
                行たち.append(行を作る(人, 項目, d.isoformat(), [d], [], 仮たち))
            continue
        行たち.append(行を作る(人, 項目, 値[項目], sorted(set(出所[項目])), 印.get(項目, []), 仮たち))
    if 会社 and 会社["値"]:
        # 会社の数え方の語は、日の時間（時間の語）を変える仮にも効く
        関わる = frozenset(時間の語)
        for 項目, u in 会社の残業.会社の語:
            行たち.append(行を作る(人, 項目, 会社["値"][項目], sorted(set(会社["出所"].get(項目, []))),
                               会社["印"].get(項目, []), 仮たち, u, 関わる))
    return {"人": 人, "行": 行たち, "仮": [x for x in 仮たち], "知らせ": 知らせ, "日": 結果}


def 行を作る(人: dict, 項目: str, 値, 出所: list, 印: list, 仮たち: list, u: str | None = None,
          関わる: frozenset = frozenset()) -> dict:
    効く = [x for x in 仮たち if x.項目 is None or 項目 in x.項目 or 関わる & x.項目]
    return {
        **人,
        "項目": 項目,
        "値": 値,
        "単位": u or 単位[項目],
        "状態": "仮" if 効く else "確定",
        "出所": "、".join(d.isoformat() if isinstance(d, date) else str(d) for d in 出所),
        "印": "、".join(dict.fromkeys(印)),
        "見当": 値 if 効く else "",
        "見当の拠り所": "、".join(dict.fromkeys(x.理由 for x in 効く)),
        "_仮": 効く,
    }
