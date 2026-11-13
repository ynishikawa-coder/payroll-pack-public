# -*- coding: utf-8 -*-
"""寄せた後の値を、段の解決（初期設定/段の解決.py）と 芯/計算 がそのまま使える形へ読む（型の版を上げない読み）。

直しの鎖（直し_NNNN＝型の版 N−1 → N）の後に、どの版の会社にも毎回当てる（版 5 の会社にも効く・今の形の値は飛ばす＝何度当てても同じ）。
前の語・前の名の表は `直し/今の型の読み.json`（前の版の名や語は 直し/ の中にしか置かない）。値を作らない: 読めない値・移せない値は問い（寄せられない物）。

1. 変更の記録の `適用支給月` を `YYYY.MM支給` へ（型の正の形。段の解決の 月にそろえる() は `2026-07` なども読むが、そろわない字の行は効かずその人が仮＋問いになる）。適用開始の列も同じ。
2. 変更の記録の `項目` の前の名を、直しの読み替え（社員の列の名を変える・列を畳む・項目の語を読み替える）で今の名へ（前の名のままでは 確かめ＝仮 が効かない）。
3. 支給控除の項目の `社保の報酬`・`雇保の対象` などの前の語（はい・いいえ・○・×…）を今の語（入る・入らない…）へ。
4. 芯が作る項目（芯/計算 の決まった項目・委託分の項目）の行を 支給控除の項目 に残さない（芯が ValueError で全員止まる）。
   率・丸めは芯の決まり（03_マスタ「会社」の行）へ移し、移せない物は問い。前の名（残業手当 など）は問い。
5. 人ごとの支給控除の芯が作る項目の行（住民税 → 住民税.額 は移す・前の単価の 残業手当・欠勤控除 などは問い）。
6. 単価の元＝固定の額（支給控除の項目に額の列は無い＝額は人ごとの支給控除）を 人の額 へ。額の出所が無い行は残さず `書かない物` に出す。
7. 支払.支給日 の `翌月25日` を 支払.支給の月＝翌月 と 支払.支給日＝25 に分ける。
8. 寄せが持ってこない値（支払.締め日・支払.支給日・会社.事業場の都道府県・時間.暦・休日.人の休日）が無ければ `無い値` に出す（書かない・段の解決が仮と問い）。
"""
import json
import os
import re

import 当てる as 当

置き場 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "直し", "今の型の読み.json")
マスタ = "03_マスタ"


def 読みを開く(path: str = 置き場) -> dict:
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    要る = {"変更の記録", "適用開始の列", "支給控除の項目の読み", "芯が作る項目", "芯が作る項目の前の名", "芯が作る項目の決まりへ",
          "芯が法で決める列", "出口だけが読む列", "人の額の行き", "支給日の月の語", "持ってくる値"}
    無い = 要る - set(d)
    if 無い:
        raise ValueError(f"今の型の読み.json: 鍵が無い {sorted(無い)}")
    前の名 = d["芯が作る項目の前の名"]
    外 = [k for k, v in 前の名.items() if v not in d["芯が作る項目"] or k in d["芯が作る項目"]]
    if 外:
        raise ValueError(f"今の型の読み.json: 芯が作る項目の前の名 の行き先が芯が作る項目に無いか、前の名が芯の名 {外}")
    return d


# ---------------------------------------------------------------- 小さな部品

def タブ(o, f, t):
    return o.シート.get(f, {}).get(t)


def 番(rows, 名):
    return 当.列の番号(rows, 名)


def 値(rows, r, 名) -> str:
    i = 番(rows, 名)
    return "" if i is None else str(rows[r][i]).strip()


def 空でない数(row) -> int:
    return sum(1 for v in row if not 当.空か(v))


def 外す(f, t, rows, 消す: set, o) -> list:
    if not 消す:
        return rows
    o.シート[f][t] = [rows[0]] + [rows[r] for r in range(1, len(rows)) if r not in 消す]
    return o.シート[f][t]


def 台帳たち(o) -> list[str]:
    return [f for f in o.シート if re.fullmatch(r"04_台帳_\d{4}", f)]


# ---------------------------------------------------------------- 当てる（照らすの前）

def 当てる(o, K: dict, 型: dict, 記, 直したち: list[dict], 読み: dict | None = None):
    読み = 読み or 読みを開く()
    適用開始をそろえる(o, 記, 読み)
    変更の記録の月(o, 記, 読み)
    変更の記録の項目(o, K, 型, 記, 直したち, 読み)
    支給控除の項目の語(o, 記, 読み)
    残る名 = 芯が作る行(o, 記, 読み)
    人の芯が作る行(o, 記, 読み, 残る名)
    額の出所(o, 記)


def 当てる_照らすの後(o, 前, 記, 読み: dict | None = None):
    読み = 読み or 読みを開く()
    支給日を分ける(o, 記, 読み)
    無い値を出す(o, 前, 記, 読み)


# ---- 1 適用開始・適用支給月

def 適用開始をそろえる(o, 記, 読み):
    for f, t, 列 in 読み["適用開始の列"]:
        rows = タブ(o, f, t)
        if not rows or 番(rows, 列) is None:
            continue
        op = {"する": "値をそろえる", "ファイル": f, "タブ": t, "列": 列, "形": "支給月",
              "なぜ": "適用開始は 効き始める支給月（YYYY.MM支給）。型の正の形にそろえる（段の解決はそろわない字の行を効かせず仮＋問いにする）"}
        当.値をそろえる当てる(o, f, t, rows, op, 記, 0, 0, {})


def 記録の名(rows, r) -> str:
    return "/".join(f"{c}={値(rows, r, c)}" for c in ("NO", "項目", "記録日") if 値(rows, r, c)) or f"{r + 1} 行目"


def 変更の記録の月(o, 記, 読み):
    f, t = マスタ, "変更の記録"
    rows = タブ(o, f, t)
    if not rows:
        return
    where = f"{f}/{t}"
    消す = set()
    for 列 in 読み["変更の記録"]["日の列"]:
        i = 番(rows, 列)
        for r in range(1, len(rows)) if i is not None else ():
            w = 当.日付(rows[r][i])
            if w and w != str(rows[r][i]).strip():
                rows[r][i] = w
                記.当てた.append((0, 0, "値をそろえる", f"{where}/{列}/{記録の名(rows, r)}"))
    for 列 in 読み["変更の記録"]["支給月の列"]:
        i = 番(rows, 列)
        if i is None:
            continue
        for r in range(1, len(rows)):
            if not any(not 当.空か(v) for k, v in enumerate(rows[r]) if rows[0][k] != "会社"):
                continue
            v = str(rows[r][i]).strip()
            名 = 記録の名(rows, r)
            鍵 = f"{where}/そろえる:{列}/{名}"
            ans = o.人の答え.get(鍵, "")
            w = 当.支給月へ(v) if v else None
            if w is None and ans.startswith("値:"):
                w = 当.支給月へ(ans[2:])
            if w is not None:
                if w != v:
                    rows[r][i] = w
                    記.数["足した"] += not v  # 空の所へ人の答えの値
                    記.当てた.append((0, 0, "値をそろえる", f"{where}/{列}/{名}"))
                continue
            if ans == "行ごと外す":
                消す.add(r)
                n = 空でない数(rows[r])
                記.数["捨てた（人の答え）"] += n
                記.持たない.append((f"{where}/{名}", n, f"人が行ごと外した（{列}「{v}」が支給月に読めない）"))
                continue
            記.出せない(鍵, "形の合わない値", where,
                      f"{名}「{列}」= {v or '（空）'}（YYYY.MM支給 へ読めない。段の解決もそろえられず、この行は効かずに仮＋問いになる）",
                      ["値:<YYYY.MM支給>", "行ごと外す"], "変更の記録の 適用支給月 は その変更が効き始める支給月（例 2026.08支給）")
    外す(f, t, rows, 消す, o)


# ---- 2 変更の記録の項目の前の名

def 名の読み替え(直したち: list[dict]) -> dict:
    """直しの鎖が社員・会社・人ごとの支給控除の名に当てる読み替え {前の名: 今の名}（鎖をたどった後の名）。"""
    m = {}

    def 足す(前, 後):
        if 前 != 後:
            m.setdefault(前, 後)  # 同じ前の名は早い版が先（後の版の読み替えは鎖をたどって当たる）
    for d in sorted(直したち, key=lambda x: x["版"]):
        for op in d["操作"]:
            する, t = op["する"], op.get("タブ")
            if する == "列の名を変える" and t == "社員":
                足す(op["前"], op["後"])
            elif する == "列を畳む" and t == "社員" and isinstance(op.get("先"), dict) and "項目" in op["先"].get("足す行", {}):
                足す(op["列"], op["先"]["足す行"]["項目"])
            elif する == "値の語を読み替える" and t in ("会社", "人ごとの支給控除") and op.get("列") == "項目" and op.get("合わせ", "全体") == "全体":
                足す(op["前"], op["後"])

    def 終わり(名):
        見た = set()
        while 名 in m and 名 not in 見た and m[名] != 名:
            見た.add(名)
            名 = m[名]
        return 名
    return {k: 終わり(k) for k in m}


def 今の名たち(o, K, 型) -> set:
    名 = {c["名"] for c in (当.型のファイル(K, マスタ) or {}).get("社員", [])}
    名 |= {it["項目"] for it in 型.get("_項目", [])}
    for t in ("人ごとの支給控除", "支給控除の項目"):
        rows = タブ(o, マスタ, t)
        if rows and 番(rows, "項目") is not None:
            名 |= {値(rows, r, "項目") for r in range(1, len(rows))}
    return {x for x in 名 if x}


def 変更の記録の項目(o, K, 型, 記, 直したち, 読み_=None):
    f, t = マスタ, "変更の記録"
    rows = タブ(o, f, t)
    if not rows or 番(rows, "項目") is None:
        return
    where = f"{f}/{t}"
    i = 番(rows, "項目")
    読み = 名の読み替え(直したち)
    今 = 今の名たち(o, K, 型)
    読み_ = 読み_ or 読みを開く()
    芯の名 = set(読み_["芯が作る項目"]) | set(読み_["芯が作る項目の前の名"])
    for r in range(1, len(rows)):
        v = str(rows[r][i]).strip()
        if not v:
            continue
        w = 読み.get(v, v)
        鍵 = f"{where}/項目:{v}"
        ans = o.人の答え.get(鍵, "")
        if (w not in 今 or w in 芯の名) and ans.startswith("値:") and ans[2:].strip():
            w = ans[2:].strip()
        if ans == "そのまま":
            continue  # 人が前の名のまま残すと答えた記録（今の計算に効かない記録）
        if w in 芯の名:
            # 芯が作る項目（前の単価・保険料など）へ当たる記録は今の項目に効かない＝黙って通さない（その人は答えまで書かない）
            記.出せない(鍵, "形の合わない値", where,
                      f"項目「{v}」は芯が作る「{w}」に当たる（芯は法の式で出し、この記録を読まない＝確かめ＝仮 も効かない）",
                      ["値:<今の項目>", "そのまま"],
                      "その変更が効く今の項目（例 社保.標準報酬・人ごとの支給控除の項目）を 値:<今の項目> で。今の計算に効かない記録なら そのまま")
            continue
        if w in 今:
            if w != v:
                rows[r][i] = w
                記.当てた.append((0, 0, "値の語を読み替える", f"{where}/項目/{記録の名(rows, r)}"))
                記.知らせ.append(f"{where}/{記録の名(rows, r)}: 項目の前の名「{v}」を今の名「{w}」へ（直しの読み替え）")
            continue
        if ans == "そのまま":
            continue
        記.出せない(鍵, "形の合わない値", where,
                  f"項目「{v}」は今の社員の列・項目の名・支給控除の項目に無い（前の名のままでは段の解決の 確かめ＝仮 が効かない）",
                  ["値:<今の項目>", "そのまま"], "社員の列（例 社保.標準報酬）・項目の名（`分野.名`）・人ごとの支給控除の項目 のどれか")


# ---- 3 支給控除の項目の前の語

def 支給控除の項目の語(o, 記, 読み):
    f, t = マスタ, "支給控除の項目"
    rows = タブ(o, f, t)
    if not rows:
        return
    for 列, 表 in 読み["支給控除の項目の読み"].items():
        if 番(rows, 列) is None:
            continue
        m = {前: 今 for 今, 前たち in 表.items() for 前 in 前たち}
        m.update({今: 今 for 今 in 表})
        op = {"する": "値をそろえる", "ファイル": f, "タブ": t, "列": 列, "形": "読み", "読み": m,
              "なぜ": f"{列} の今の語は {'・'.join(表)} だけ（外の語を 芯/計算 は既定と違う向きに読む＝例 雇保の対象 が はい なら 雇用保険 0 で確定）。空は芯の既定"}
        当.値をそろえる当てる(o, f, t, rows, op, 記, 0, 0, {})


# ---- 4 芯が作る項目の行（支給控除の項目）

def 数か(v):
    try:
        return float(str(v).replace("％", "%").rstrip("%"))
    except ValueError:
        return None


def 会社の行を探す(会社rows, 会社名, 項目, 適用開始):
    for r in range(1, len(会社rows)):
        if 値(会社rows, r, "項目") == 項目 and (番(会社rows, "会社") is None or 値(会社rows, r, "会社") in ("", 会社名)) \
                and 値(会社rows, r, "適用開始") == 適用開始:
            return r
    return None


def 芯が作る行(o, 記, 読み) -> set:
    """支給控除の項目の芯が作る項目の行を外す。残った行の名の集まりを返す（人ごとの支給控除の行の扱いに使う）。"""
    f, t = マスタ, "支給控除の項目"
    rows = タブ(o, f, t)
    if not rows or 番(rows, "項目") is None:
        return set()
    会社rows = タブ(o, f, "会社")
    where = f"{f}/{t}"
    芯の名, 前の名 = set(読み["芯が作る項目"]), 読み["芯が作る項目の前の名"]
    法, 出口 = set(読み["芯が法で決める列"]), set(読み["出口だけが読む列"])
    消す = set()
    for r in range(1, len(rows)):
        名 = 値(rows, r, "項目")
        if 名 not in 芯の名 and 名 not in 前の名:
            continue
        適用 = 値(rows, r, "適用開始")
        行名 = f"項目={名}" + (f"/適用開始={適用}" if 適用 else "")
        鍵 = f"{where}/芯が作る項目/{行名}"
        ans = o.人の答え.get(鍵, "")
        if ans.startswith("値:") and ans[2:].strip() and ans[2:].strip() not in 芯の名 and ans[2:].strip() not in 前の名:
            rows[r][番(rows, "項目")] = ans[2:].strip()  # 部品の行として残す（会社が自分で付けた手当の名）
            記.当てた.append((0, 0, "値の語を読み替える", f"{where}/項目/{行名}"))
            continue
        芯 = 名 if 名 in 芯の名 else 前の名[名]
        if 名 in 前の名 and ans != "芯が作る":
            記.出せない(鍵, "芯が作る項目", where,
                      f"{行名}: 前の名「{名}」は芯が作る「{芯}」と同じ意味かもしれない（部品の行に残すと芯の {芯} と二重に払う・引く）",
                      ["芯が作る", "値:<部品の名>"],
                      f"芯が作る＝行を外し率・丸めを芯の決まりへ移す（{芯} は芯が法の式で出す）。会社が自分で決めた額の手当なら 値:<部品の名>（例 値:{名}）で部品の行に残す")
            continue
        会社名 = 値(rows, r, "会社") or o.会社
        移す, 移せない, 捨てる, 出口の値 = [], [], [], []
        for k, c in enumerate(rows[0]):
            v = str(rows[r][k]).strip()
            if 当.空か(v) or c in ("会社", "項目", "適用開始"):
                continue
            if c in 出口:
                出口の値.append((c, v))
                continue
            if c in 法:
                捨てる.append((c, v))
                continue
            行き = 読み["芯が作る項目の決まりへ"].get(芯, {}).get(c)
            if not 行き:
                移せない.append((c, v, "芯の決まりに行き先が無い"))
                continue
            先, 形 = 行き
            if 形 in ("倍", "足す"):
                x = 数か(v)
                if x is None or (形 == "倍" and x < 1) or (形 == "足す" and not 0 < x < 1):
                    移せない.append((c, v, f"{先} の形（{'1 以上の倍' if 形 == '倍' else '0〜1 の足す率'}）に読めない"))
                    continue
            if 会社rows is None or 番(会社rows, "項目") is None or 番(会社rows, "今の値") is None:
                移せない.append((c, v, "03_マスタ「会社」のタブが無い"))
                continue
            既 = 会社の行を探す(会社rows, 会社名, 先, 適用)
            if 既 is not None and 値(会社rows, 既, "今の値") not in ("", v):
                移せない.append((c, v, f"会社の {先} が既に {値(会社rows, 既, '今の値')}"))
                continue
            移す.append((c, v, 先, 既))
        鍵2 = f"{where}/芯が作る項目の決まり/{行名}"
        ans2 = o.人の答え.get(鍵2, "")
        if 移せない and not (ans2.startswith("持たない:") and ans2[len("持たない:"):].strip()):
            記.出せない(鍵2, "芯が作る項目", where,
                      f"{行名}: 芯が作る「{芯}」の行の値を芯の決まりへ移せない（" + "・".join(f"{c}＝{v}: {w}" for c, v, w in 移せない) + "）",
                      ["持たない:<なぜ>"],
                      "03_マスタ「会社」に芯の決まり（割増.*の率・欠勤.控除の端数・社保.端数 など）を人が書いてから 持たない:<なぜ> と答える（前の値は寄せの写しに在る）")
            continue
        # 当てる: 行を外し、移せる値は会社の行へ
        for c, v, 先, 既 in 移す:
            if 既 is not None and 値(会社rows, 既, "今の値") == v:
                記.数["重ねた"] += 1
                continue
            if 既 is not None:
                会社rows[既][番(会社rows, "今の値")] = v
                記.数["他の所へ移した"] += 1
                記.数["足した"] += 1
                continue
            new = [""] * len(会社rows[0])
            for cc, w in (("会社", 会社名 if 番(会社rows, "会社") is not None else None), ("項目", 先), ("今の値", v), ("適用開始", 適用)):
                if w is not None and 番(会社rows, cc) is not None:
                    new[番(会社rows, cc)] = w
            会社rows.append(new)
            記.数["他の所へ移した"] += 1
            記.数["足した"] += 空でない数(new)
            記.渡すタブ.add((f, t))
        n = 空でない数(rows[r]) - len(移す)
        記.数["捨てた（直しの持たない）"] += n
        記.持たない.append((f"{where}/{行名}", n,
                         f"芯が作る項目「{芯}」は部品の行に置かない（芯/計算 が決まった項目の名とぶつかり止まる）" +
                         (f"。{'・'.join(f'{c}→{先}' for c, _, 先, _ in 移す)} は会社の決まりへ移した" if 移す else "") +
                         (f"。芯が法で決める {'・'.join(c for c, _ in 捨てる)} は持たない" if 捨てる else "") +
                         (f"。{ans2[len('持たない:'):].strip()}（人の答え）" if 移せない else "")))
        if 出口の値:
            記.書かない.append({"所": f"{where}/{行名}", "行": 1,
                             "なぜ": f"芯が作る項目「{芯}」の行は支給控除の項目に置かない。{'・'.join(f'{c}＝{v}' for c, v in 出口の値)} は出口の欄の対応が読む値（寄せの写しに在る。殻が出口へ渡す欄の対応に足す）"})
        記.知らせ.append(f"{where}/{行名}: 芯が作る項目「{芯}」の行を外した（芯/計算 が自分で作る）")
        消す.add(r)
    rows = 外す(f, t, rows, 消す, o)
    return {値(rows, r, "項目") for r in range(1, len(rows))}


# ---- 5 人ごとの支給控除の芯が作る項目の行

def 人の芯が作る行(o, 記, 読み, 残る名: set):
    f, t = マスタ, "人ごとの支給控除"
    rows = タブ(o, f, t)
    if not rows or 番(rows, "項目") is None:
        return
    where = f"{f}/{t}"
    ki = 番(rows, "項目")
    芯の名, 前の名, 行き = set(読み["芯が作る項目"]), 読み["芯が作る項目の前の名"], 読み["人の額の行き"]
    消す = set()
    for r in range(1, len(rows)):
        名 = 値(rows, r, "項目")
        if 名 in 残る名 or (名 not in 芯の名 and 名 not in 前の名):
            continue
        行名 = f"{当.行の名(rows, r)}/項目={名}"
        鍵 = f"{where}/芯が作る項目/項目={名}"
        ans = o.人の答え.get(鍵, "")
        先 = 行き.get(名) or 行き.get(前の名.get(名, ""))
        if not 先 and ans.startswith("値:") and ans[2:].strip() not in 芯の名 | set(前の名):
            先 = ans[2:].strip()
        if 先:
            同じ = [x for x in range(1, len(rows)) if x != r and x not in 消す and 値(rows, x, "項目") == 先
                   and all(値(rows, x, c) == 値(rows, r, c) for c in ("会社", "NO", "適用開始"))]
            if 同じ and 値(rows, 同じ[0], "額") != 値(rows, r, "額") and not ans.startswith("持たない:"):
                記.出せない(鍵, "ぶつかり", where, f"{行名}: 額 {値(rows, r, '額')} と 今の行「{先}」の額 {値(rows, 同じ[0], '額')}",
                          ["持たない:<なぜ>"], f"今の行「{先}」の額を正にするなら 持たない:<なぜ>（前の行の値は寄せの写しに在る）")
                continue
            if 同じ:
                消す.add(r)
                記.数["重ねた" if 値(rows, 同じ[0], "額") == 値(rows, r, "額") else "捨てた（人の答え）"] += 空でない数(rows[r])
                continue
            rows[r][ki] = 先
            記.当てた.append((0, 0, "値の語を読み替える", f"{where}/項目/{行名}"))
            記.知らせ.append(f"{where}/{行名}: 芯が作る「{名}」の人の額を 項目「{先}」へ（段の解決が芯の読む値へ渡す）")
            continue
        if ans.startswith("持たない:") and ans[len("持たない:"):].strip():
            消す.add(r)
            n = 空でない数(rows[r])
            記.数["捨てた（人の答え）"] += n
            記.持たない.append((f"{where}/{行名}", n, f"人の答え: {ans[len('持たない:'):].strip()}"))
            continue
        芯 = 名 if 名 in 芯の名 else 前の名[名]
        記.出せない(鍵, "芯が作る項目", where,
                  f"項目「{名}」の人の額（{'・'.join(当.行の名(rows, x) + '＝' + 値(rows, x, '額') for x in range(1, len(rows)) if 値(rows, x, '項目') == 名)}）は"
                  f"芯が作る「{芯}」の額か前の道具の単価（芯は法の式で出し、この額を読まない）",
                  ["持たない:<なぜ>", "値:<今の項目>"],
                  f"前の道具の単価（時間外単価・欠勤単価 など）なら 持たない:芯が単価を出す（前の単価は寄せの写しで照らす）。"
                  f"会社が決めた額の手当なら支給控除の項目にその名の行を足してから 値:<部品の名>")
    外す(f, t, rows, 消す, o)


# ---- 6 単価の元＝固定の額 と額の出所

def 額の出所(o, 記):
    f, t = マスタ, "支給控除の項目"
    rows = タブ(o, f, t)
    人 = タブ(o, f, "人ごとの支給控除")
    if not rows or 番(rows, "項目") is None or 番(rows, "単価の元") is None:
        return
    where = f"{f}/{t}"
    人の名 = {(値(人, r, "会社"), 値(人, r, "項目")) for r in range(1, len(人)) if 値(人, r, "額")} if 人 and 番(人, "項目") is not None else set()
    月の名 = set()
    for tf in 台帳たち(o):
        mv = タブ(o, tf, "月の変動")
        if mv and 番(mv, "項目") is not None:
            月の名 |= {値(mv, r, "項目") for r in range(1, len(mv))}
    待つ = {x["鍵"] for x in 記.寄せられない}
    消す = set()
    for r in range(1, len(rows)):
        名, 元 = 値(rows, r, "項目"), 値(rows, r, "単価の元")
        if not 名 or 元 not in ("", "固定の額", "回ごとの額", "人の額"):
            continue
        if any(k.startswith(f"{where}/") and k.endswith(f"/項目={名}") for k in 待つ):
            continue  # 前の直しの問い（計算の仕方が読めない など）を待つ
        会社名 = 値(rows, r, "会社")
        人に在る = (会社名, 名) in 人の名 or ("", 名) in 人の名 or (not 会社名 and any(n == 名 for _, n in 人の名))
        if 人に在る:
            if 元 != "人の額":
                rows[r][番(rows, "単価の元")] = "人の額"
                if not 元:
                    記.数["足した"] += 1
                記.当てた.append((0, 0, "値をそろえる", f"{where}/単価の元/項目={名}"))
                記.知らせ.append(f"{where}/項目={名}: 単価の元「{元 or '（空＝固定の額）'}」→ 人の額"
                               "（支給控除の項目に額の列は無い＝額は人ごとの支給控除に在る）")
            continue
        if 元 == "人の額" or not 値(rows, r, "給与ソフトの欄"):
            continue  # 人の額を後で入れる行・欄の無い行は残す（額が無ければ段の解決・芯が仮と問い）。外すのは前の道具の給与ソフトの欄だけの行
        if 値(rows, r, "数量の元") == "入力の値" or 名 in 月の名:
            if 名 in 月の名 and 値(rows, r, "数量の元") != "入力の値":
                記.知らせ.append(f"{where}/項目={名}: 額は台帳「月の変動」に在るが 数量の元 が 入力の値 でない（人が確かめる）")
            continue
        n = 空でない数(rows[r])
        記.数["捨てた（直しの持たない）"] += n
        記.持たない.append((f"{where}/項目={名}", n, "額の出所が無い行（人ごとの支給控除・月の変動に額が無く、単価の元が額を持たない）"))
        記.書かない.append({"所": f"{where}/項目={名}", "行": 1,
                         "なぜ": "額の出所が無い（前の道具の給与ソフトの欄だけの行。人ごとの支給控除にも月の変動にも額が無い）＝支給控除の項目に残さない（寄せの写しに在る）"})
        消す.add(r)
    外す(f, t, rows, 消す, o)


# ---------------------------------------------------------------- 当てる（照らすの後）

# ---- 7 支払.支給日 の 翌月25日

def 支給日を分ける(o, 記, 読み):
    f, t = マスタ, "会社"
    rows = タブ(o, f, t)
    if not rows or 番(rows, "項目") is None or 番(rows, "今の値") is None:
        return
    where = f"{f}/{t}"
    語 = 読み["支給日の月の語"]
    pat = re.compile(r"(" + "|".join(map(re.escape, sorted(語, key=len, reverse=True))) + r")の?(\d{1,2}日?|末日?|月末日?)(支給|払い?)?")
    vi = 番(rows, "今の値")
    for r in range(1, len(rows)):
        if 値(rows, r, "項目") != "支払.支給日":
            continue
        s = re.sub(r"\s", "", str(rows[r][vi])).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
        m = pat.fullmatch(s)
        if not m:
            continue
        月, 日 = 語[m.group(1)], m.group(2).removesuffix("日")
        日 = "末" if 日 in ("末", "月末") else 日
        会社名, 適用 = 値(rows, r, "会社") or o.会社, 値(rows, r, "適用開始")
        既 = 会社の行を探す(rows, 会社名, "支払.支給の月", 適用)
        鍵 = f"{where}/支給日の月/{当.行の名(rows, r)}"
        ans = o.人の答え.get(鍵, "")
        if 既 is not None and 値(rows, 既, "今の値") not in ("", 月) and ans not in ("前を取る", "後を取る"):
            記.出せない(鍵, "ぶつかり", where, f"支払.支給日「{rows[r][vi]}」の {月} と 支払.支給の月＝{値(rows, 既, '今の値')}",
                      ["前を取る", "後を取る"], "前を取る＝支払.支給日 の月の語を 支払.支給の月 へ・後を取る＝今の 支払.支給の月 のまま")
            continue
        rows[r][vi] = 日
        if 既 is None:
            new = [""] * len(rows[0])
            for c, w in (("会社", 会社名), ("項目", "支払.支給の月"), ("今の値", 月), ("適用開始", 適用)):
                if 番(rows, c) is not None and w:
                    new[番(rows, c)] = w
            rows.append(new)
            記.数["足した"] += 空でない数(new)
        elif 値(rows, 既, "今の値") != 月 and ans == "前を取る":
            rows[既][vi] = 月
            記.数["捨てた（人の答え）"] += 1
            記.数["足した"] += 1
        elif 値(rows, 既, "今の値") == "":
            rows[既][vi] = 月
            記.数["足した"] += 1
        記.当てた.append((0, 0, "値をそろえる", f"{where}/支払.支給日"))
        記.知らせ.append(f"{where}: 支払.支給日「{s}」を 支払.支給の月＝{月}・支払.支給日＝{日} に分けた（段の解決は 1〜28・末 だけを読む）")


# ---- 8 寄せが持ってこない値

def 無い値を出す(o, 前, 記, 読み):
    会社rows = タブ(o, マスタ, "会社") or []
    型rows = タブ(o, マスタ, "勤務の型") or []
    社員 = タブ(o, マスタ, "社員") or []

    def 会社に在る(項目):
        return bool(会社rows) and 番(会社rows, "項目") is not None and any(
            値(会社rows, r, "項目") == 項目 and 値(会社rows, r, "今の値") for r in range(1, len(会社rows)))

    週休 = ""
    for tabs in 前.シート.values():
        rows = tabs.get("会社")
        if rows and 番(rows, "項目") is not None:
            週休 = next((v for r in range(1, len(rows)) if 値(rows, r, "項目") == "週休形態"
                       for v in [値(rows, r, "今の値") or 値(rows, r, "値")] if v), 週休)
    for x in 読み["持ってくる値"]:
        項目, 段 = x["項目"], x["段"]
        無い = []
        if 段 == "会社" and not 会社に在る(項目):
            無い = [f"{マスタ}/会社"]
        elif 段 == "勤務の型" and not 会社に在る(項目) and 型rows:
            i = 番(型rows, 項目)
            無い = [f"{マスタ}/勤務の型/{当.行の名(型rows, r)}" for r in range(1, len(型rows))
                   if i is None or 当.空か(型rows[r][i])]
        elif 段 == "人" and 社員 and len(社員) > 1:
            i = 番(社員, 項目)
            if i is None or all(当.空か(社員[r][i]) for r in range(1, len(社員))):
                無い = [f"{マスタ}/社員"]
        for 所 in 無い:
            なぜ = "寄せた後に値が無い＝書かない（段の解決・芯が無い値として仮と問いにする。寄せは値を作らない）"
            if 項目 == "時間.暦" and 段 == "会社" and 週休:
                なぜ += f"。前の 週休形態「{週休}」が寄せの写しに在る（時間.暦 を書く時の手がかり）"
            記.無い値.append({"項目": 項目, "段": 段, "所": 所, "前の道具": x["前の道具"], "なぜ": なぜ})
