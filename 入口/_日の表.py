"""日ごとの時刻の表を読む共通の手（PDF タイムカード・Excel 出勤簿・勤怠システムの月報が使う。会社ごとに作らない）。

1 枚の表＝1 人。殻は表の字を 見出し と 行（字の list）で渡す。見出しの語は 欄の役 へ読み替える:
  日・出・退（2 組目からも 出・退 と並べてよい）・外出・戻・休憩（長さ）・区分・備考・時間数（印字の 退−出）・
  書き足した残業（余白・欄に手書きで足された残業の長さ＝表 A の 書き足した残業へ。読めなければ備考へ字のまま＋要確認）・
  それと 原本の時間 へ写す欄（総労働・所定内・深夜 など 5 節の語）。どの役にも当たらない欄は 備考 へ字のまま。
"""
from __future__ import annotations

import re

from . import 口
from .口 import 日の材料, 分, 長さの分, 時刻

役たち = {"日", "出", "退", "外出", "戻", "休憩", "区分", "備考", "時間数", "書き足した残業"}
合計の語 = ("合計", "小計", "計", "総計")
# 書き足した残業の欄の既定の見出し（様式で違う語は殻が 読み替え で 役 書き足した残業 へ）
書き足した残業の見出し = {"書き足した残業": "書き足した残業", "手書きの残業": "書き足した残業", "残業（手書き）": "書き足した残業",
                  "余白の残業": "書き足した残業"}
書き足しの印 = re.compile(r"\(手\)|（手）|手書き")


def 書き足した残業(v, 書き方: str) -> tuple[str, list, list]:
    """書き足した残業の欄の字 → (分の字, 備考, 要確認の理由)。`1:30` はいつも読む。数だけの字（`1.5`・`2`）は表の 書き方 が
    `10進`／`60進` と決まっている時だけ読む（書き方が決まらないと `1.5` が 90 分か 110 分か決まらない）。
    `1h`・`30分` などの読めない字は推さず、備考へ字のまま残して要確認にする。"""
    s = str(v if v is not None else "").strip()
    if not s:
        return "", [], []
    t = re.sub(r"^残業", "", 書き足しの印.sub("", s).strip()).strip()
    w = 長さの分(t, 書き方) if 書き方 in ("10進", "60進") or ":" in t.replace("：", ":") else None
    if w is None or w <= 0:
        return "", [f"書き足した残業 {s}"], [f"書き足した残業「{s}」が時間に読めない"]
    return str(w), [], []


def セル(v, 役: str) -> tuple[str, str, list, list, list]:
    """1 つの時刻の欄 → (時刻の字, 時刻の出所, 印, 備考, 要確認の理由)。
    黒塗り・取消は入れない／手書き の印／1 欄に 2 つの時刻は 出＝早い方・退＝遅い方（印 二重打刻）／
    `*` は勤怠システムで手で直した／`!` と式のエラーは要確認。"""
    s = str(v if v is not None else "").strip()
    出所, 印, 備考, 理由 = "打刻", [], [], []
    if not s:
        return "", 出所, 印, 備考, 理由
    if any(w in s for w in ("黒塗り", "■", "取消")):
        return "", 出所, 印, [f"{役} 黒塗り"], 理由
    if s.startswith("#"):
        return "", 出所, 印, [f"{役} {s}"], [f"{役}の欄が式のエラー（{s}）"]
    if "!" in s or "！" in s:
        理由.append(f"{役}の欄に打刻エラーの印")
        備考.append(f"{役} !打刻エラー")
        s = s.replace("!", "").replace("！", "").strip()
    if "*" in s or "＊" in s:
        出所 = "申請で直した"
        印.append("手で直した")
        s = s.replace("*", "").replace("＊", "").strip()
    if "(手)" in s or "（手）" in s or "手書き" in s:
        出所 = "手書き"
        備考.append("手書き")
        s = re.sub(r"\(手\)|（手）|手書き", "", s).strip()
    parts = [p for p in re.split(r"[\s/／,、]+", s) if p]
    if len(parts) > 1:
        ms = [分(p) for p in parts]
        if all(m is not None for m in ms):
            pick = min(ms) if 役 in ("出", "外出") else max(ms)
            印.append("二重打刻")
            備考.append(f"{役} {s}")
            return 時刻(pick), 出所, 印, 備考, 理由
    if 分(s) is None and parts:
        return "", 出所, 印, [f"{役} {s}"], [f"{役}の時刻「{s}」が読めない"]
    return 時刻(分(s)), 出所, 印, 備考, 理由


def 要確認の時刻(文脈, *欄とセル) -> list[str]:
    """読めた時刻のうち、事務所・会社の決まり `時間.要確認の時刻`（文脈.要確認の時刻）に当たる欄×時刻の出所の要確認の理由。"""
    return [口.要確認の時刻の理由(欄, c[1]) for 欄, c in 欄とセル
            if c[0] and hasattr(文脈, "要確認の時刻か") and 文脈.要確認の時刻か(欄, c[1])]


二つ目の読みを照らす役 = ("出", "退", "外出", "戻", "休憩", "時間数")


def _同じ読みか(a, b) -> bool:
    a, b = str(a if a is not None else "").strip(), str(b if b is not None else "").strip()
    if a == b:
        return True
    ma, mb = 分(a), 分(b)
    return ma is not None and ma == mb


def 二つの読みを照らす(役: list, 行たち: list, 読み2: list) -> tuple[dict, list[str]]:
    """殻が同じ原本を 2 度読んだ時（分の読みが 2 通りあり得る原本＝`18:16` と `18:15` など）の照らし。
    返す物: ({日の字: [要確認の理由]}, 表の全体の理由)。時刻・休憩・時間数の欄が 1 つでも違えばその日は要確認（どちらの読みも採らない）。"""
    if len(読み2) != len(行たち):
        return {}, [f"2 つの読みの行の数が合わない（{len(行たち)} 行／{len(読み2)} 行）"]
    日ごと = {}
    for 行, 行2 in zip(行たち, 読み2):
        x, y = 口.組にする(役, 行), 口.組にする(役, 行2)
        日字 = str(x.get("日", "")).strip()
        if 日字 != str(y.get("日", "")).strip():
            return {}, [f"2 つの読みの日の並びが合わない（{日字}／{str(y.get('日', '')).strip()}）"]
        違う = [f"{k.split('_')[0]}の 2 つの読みが合わない（{str(x.get(k, '')).strip()}／{str(y.get(k, '')).strip()}）"
              for k in dict.fromkeys([*x, *y]) if k.split("_")[0] in 二つ目の読みを照らす役 and not _同じ読みか(x.get(k), y.get(k))]
        if 違う:
            日ごと.setdefault(日字, []).extend(違う)
    return 日ごと, []


def 読む(表記: str, 原本の名前: str, 見出し: list, 行たち: list, 文脈, 読み替え: dict,
       原本の時間の語: dict, 書き方: str = "分", 読み2: list | None = None,
       時間数の語: str = "") -> tuple[list[日の材料], list[str]]:
    """→ (材料たち, その人の表の全体に掛かる要確認の理由)。

    原本の形に印字の時間数の欄がある表（見出しに 時間数 の役）は、時刻のある日に時間数が無ければ要確認（照らす材料が欠けた日を確認済にしない）。
    ただし手書きの時刻の欄のある日は時間数を求めない（印字の機械は手書きの時刻の時間数を出さない＝手書きの要確認と答えで足りる）。
    時間数の語: 渡せば、読めて 退−出 と合った印字の時間数をその日の 原本の時間 `<語>=<分>` へ写す（照らす用・計算に使わない）。
    読み2: 同じ原本の 2 つ目の読み（行の並びは 行たち と同じ）。合わない欄のある日は要確認（`二つの読みを照らす`）。"""
    役 = 口.欄の役(見出し, 読み替え)
    時の書き方 = "10進" if 書き方 == "10進" else "60進"  # 時間数・原本の時間の数だけの字は時間で読む（休憩は 書き方）
    材料たち, 表の理由 = [], []
    時間数の欄がある = "時間数" in 役
    二つ目, 表の理由 = 二つの読みを照らす(役, 行たち, 読み2) if 読み2 is not None else ({}, [])
    合計 = None
    for 行 in 行たち:
        x = 口.組にする(役, 行)
        日字 = str(x.get("日", "")).strip()
        if 日字 in 合計の語:
            合計 = x
            continue
        if not 日字 and not any(str(v).strip() for v in x.values()):
            continue
        if not 日字:  # 日の空いた行の注（「土曜日の出勤は計算しない」など）は日に結べない＝字ごと表の全体の要確認へ
            表の理由.append(口.結べない字の理由(口.行の字(x)))
            continue
        d = 口.日付を決める(日字, 文脈)
        if d is None:
            表の理由.append(f"日「{日字}」が期間の中の日付に読めない")
            continue
        m = 日の材料(表記, d, 原本の名前)
        m.理由 += 二つ目.get(日字, [])
        n = 1
        手書き = False
        while f"出_{n}" in x or f"退_{n}" in x:
            a = セル(x.get(f"出_{n}"), "出")
            b = セル(x.get(f"退_{n}"), "退")
            手書き = 手書き or "手書き" in (a[1], b[1])
            m.印 += a[2] + b[2]
            m.備考 += a[3] + b[3]
            m.理由 += a[4] + b[4] + 要確認の時刻(文脈, ("出", a), ("退", b))
            出所 = next((o for o in (a[1], b[1]) if o != "打刻"), "打刻")
            m.労働(a[0], b[0], 出所, 名="出退" if n == 1 else f"出退の {n} 組目")
            n += 1
        n = 1
        while f"外出_{n}" in x:
            a, b = セル(x.get(f"外出_{n}"), "外出"), セル(x.get(f"戻_{n}"), "戻")
            m.備考 += a[3] + b[3]
            m.理由 += a[4] + b[4] + 要確認の時刻(文脈, ("外出", a), ("戻", b))
            if a[0] or b[0]:
                s, e = 分(a[0]), 分(b[0])
                if s is None or e is None:
                    m.理由.append("外出と戻が組にならない")
                else:
                    m.区間.append(("外出", s, e + 1440 if e <= s else e, a[1]))
            n += 1
        休 = str(x.get("休憩", "")).strip()
        if 休:
            v = 長さの分(休, 書き方)
            if v is None:
                m.理由.append(f"休憩「{休}」が読めない")
                m.備考.append(f"休憩 {休}")
            else:
                m.事実["時刻の無い休憩"] = str(v)
        if str(x.get("区分", "")).strip():
            m.区分を足す(x["区分"], 文脈)
        足, 足の備考, 足の理由 = 書き足した残業(x.get("書き足した残業"), 書き方)
        if 足:
            m.事実["書き足した残業"] = 足   # 列の定義は口.表Aの列（芯の持ち物）
        m.備考 += 足の備考
        m.理由 += 足の理由
        字たち = []
        if str(x.get("備考", "")).strip():
            m.備考.append(str(x["備考"]).strip())
            字たち.append(x["備考"])
        時 = str(x.get("時間数", "")).strip()
        労 = [(s, e) for k, s, e, _ in m.区間 if k == "労働"]
        if 時:
            v = 長さの分(時, 時の書き方)
            if v is None or not 労 or any(e is None for _, e in 労) or sum(e - s for s, e in 労) != v:
                m.理由.append(f"印字の時間数「{時}」と 退−出 が合わない")
                m.備考.append(f"印字 {時}")
            elif 時間数の語:
                m.原本の時間[時間数の語] = v
        elif 時間数の欄がある and 労 and not 手書き:   # 照らす材料が欠けた日は照らしを飛ばして確認済にしない
            m.理由.append("印字の時間数が無い（退−出 を照らせない）")
        for k, v in x.items():
            base = k.split("_")[0]
            if base in 役たち or not str(v).strip():
                continue
            語 = 原本の時間の語.get(k)
            if 語:
                w = 長さの分(v, 時の書き方)
                if w is None:
                    w = 分(v)  # `7:30:00`・Excel の小数（0.3125＝7:30）
                if w is None:
                    m.備考.append(f"{k} {v}")
                else:
                    m.原本の時間[語] = w
            else:
                m.備考.append(f"{k} {str(v).strip()}")
                字たち.append(v)
        m.理由 += 口.区間に無い時刻の範囲(字たち, m.区間)
        材料たち.append(m)
    if 合計 is not None and 時間数の欄がある and not str(合計.get("時間数", "")).strip():
        表の理由.append("表の合計の時間数が無い（日ごとの和を照らせない）")
    elif 合計 is not None and str(合計.get("時間数", "")).strip():
        want = 長さの分(合計["時間数"], 時の書き方)
        got = sum(e - s for m in 材料たち for k, s, e, _ in m.区間 if k == "労働" and e is not None)
        if want != got:
            表の理由.append(f"表の合計の時間数「{合計['時間数']}」と日ごとの和（{時刻(got)}）が合わない")
            for m in 材料たち:
                m.備考.append(f"表の合計 {合計['時間数']}")
    return 材料たち, 表の理由


def _月のメモ(ms: list, メモ: dict) -> list[str]:
    """表の月のメモ（カードの右の欄など・{語: 回数か分}）→ 読んだ最後の日の 原本の時間 `<語>=<数>`（月の和として照らす用・
    計算に使わない）。数でない値は備考へ字のまま残し、行に結べない字として表の全体の要確認の理由を返す。"""
    if not メモ or not ms:
        return [口.結べない字の理由(f"{語} {v}") for 語, v in (メモ or {}).items() if str(v if v is not None else "").strip()]
    out = []
    m = max(ms, key=lambda x: x.日付)
    for 語, v in メモ.items():
        s = str(v if v is not None else "").strip()
        w = int(s) if re.fullmatch(r"\d+", s) else 長さの分(s, "60進") if ":" in s else None
        if w is None:
            m.備考.append(f"月のメモ {語} {s}")
            if s:
                out.append(口.結べない字の理由(f"{語} {s}"))
        else:
            m.原本の時間[str(語).strip()] = m.原本の時間.get(str(語).strip(), 0) + w
    return out


def 人ごとに読む(表たち: list[dict], 文脈, 種別: str, 読み替え: dict, 原本の時間の語: dict, 書き方: str = "分",
            時間数の語: str = ""):
    """表（1 人 1 枚）の list → 結果。表 = {勤怠の表記, 原本の名前, 見出し, 行, 読み替え?(その様式の見出しの語),
    読み2?(同じ原本の 2 つ目の読みの行＝分の読みが 2 通りあり得る原本。入口/README.md「2 つの読み」),
    月のメモ?({語: 数}＝カードの月のメモ〔夜休憩の回数など〕。読んだ最後の日の 原本の時間 へ＝月の和として照らす用),
    メモ?([字]＝表の頭・余白など日の行に結べない字。その人の全日に 行に結べない字 の要確認)}"""
    全部 = []
    for t in 表たち:
        rw = dict(読み替え)
        rw.update(t.get("読み替え", {}))
        ms, 表の理由 = 読む(t["勤怠の表記"], t["原本の名前"], t["見出し"], t["行"], 文脈, rw, 原本の時間の語, 書き方,
                       t.get("読み2"), 時間数の語=時間数の語)
        表の理由 = 表の理由 + _月のメモ(ms, t.get("月のメモ") or {})
        表の理由 += [口.結べない字の理由(メモ) for メモ in t.get("メモ") or [] if str(メモ).strip()]
        if 表の理由:
            if not ms:  # 1 日も読めない表でも人は出す（全日が 原本に無い になる）
                d = 文脈.日付たち()[0]
                ms = [日の材料(t["勤怠の表記"], d, t["原本の名前"], 行がある=False)]
            for m in ms:
                m.理由 += 表の理由
        全部 += ms
    return 口.仕上げる(全部, 文脈, 種別)
