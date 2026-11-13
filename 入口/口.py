"""入口の口の型（どの読み口も同じ呼び口・同じ出力）。

形の正本は docs/設計/勤怠の形.md（表 A「日」・表 B「区間」・5 節の月の数字の口）。
入口は Drive を開かない。殻（環境の口）が渡す値（get_values の行・CSV の字・PDF から読んだ字）を受け、
表 A・B（か月の数字の口）を返すだけ。芯の数え方（深夜・残業・法定休日の時間）は出さない。
勤怠ツールの名と列名は殻が渡し（パックに置かない）、ここで作る表に出さない。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

# ---- 出力の列（勤怠の形.md の表の順） ----
表Aの列 = [
    "支給月", "会社", "NO", "勤怠の表記", "日付", "日の種類", "休日の区分", "休暇の種類", "休暇の単位",
    "休暇の時間", "勤務の型", "所定の始業", "所定の終業", "所定時間", "働いた場所", "印", "遅延証明の分",
    "振替の相手の日", "代休の相手の日", "申請の残業", "時刻の無い休憩", "時刻の無い労働時間", "所属",
    "原本の時間", "原本の名前", "原本の種別", "読み取りの確かめ", "備考",
]
表Bの列 = ["支給月", "会社", "NO", "日付", "区間の番号", "区間の種別", "始め", "終わり", "時刻の出所"]
月の数字の列 = ["支給月", "会社", "NO", "勤怠の表記", "項目", "値", "原本の名前", "原本の種別", "読み取りの確かめ", "備考"]
# 手当控除の行き先（Drive の型.md §4 の台帳「月の変動」・マスタ「②人ごとの支給控除」）
月の変動の列 = ["会社", "支給月", "NO", "項目", "値", "原本の名前", "確認"]
人ごとの支給控除の列 = ["会社", "NO", "項目", "額", "適用開始"]

日の種類たち = ("勤務", "休日勤務", "休暇", "欠勤", "休日", "休職・休業")
休暇の種類たち = ("年休", "特別休暇（有給）", "特別休暇（無給）", "子の看護等休暇", "介護休暇", "生理休暇", "代休", "出勤扱い",
             "会社都合の休業", "産前産後休業", "育児休業", "介護休業", "休職")
休暇の単位たち = ("全日", "午前半休", "午後半休", "時間")
働いた場所たち = ("事業所", "在宅", "直行直帰", "出張", "みなし")
印たち = ("遅刻", "早退", "定時扱い", "打刻抜け", "二重打刻", "手で直した", "原本に無い")
区間の種別たち = ("労働", "休憩", "外出")
時刻の出所たち = ("打刻", "手書き", "申請で直した", "所定で埋めた")
原本の種別たち = ("PDFタイムカード", "Excel出勤簿", "勤怠システムの月報", "集計済み勤怠表", "メールとメモ")

# 月の数字の口の項目と単位（勤怠の形.md 5 節。この外の語は置かない）
月の項目 = {
    "所定日数": "日", "出勤日数": "日", "休日勤務日数（法定）": "日", "休日勤務日数（所定）": "日",
    "年休（全日）": "日", "年休（半日）": "回", "年休（時間）": "分", "特別休暇（有給）": "日", "特別休暇（無給）": "日",
    "欠勤": "日", "休業": "日", "総労働": "分", "所定内": "分", "法定内残業": "分", "法定外残業": "分",
    "60 時間超": "分", "深夜": "分", "法定休日": "分", "所定休日": "分", "遅刻早退": "分", "夜勤の回数": "回",
    "年休を取った日": "日付",
}

確認済 = "確認済"
所定の無い区分 = ("委託",)  # 人.区分 がこれなら所定が無い（空の日は働いていない日。勤務日に数えない）
長すぎる日またぎ = 16 * 60  # 日またぎと読んだ労働の区間がこれより長ければ要確認（13:00〜12:00 の読み違いなど）
要確認 = "要確認"

# ---- 区分の語 → 表 A の事実（どの原本にも出る一般の語だけ。顧客だけの語は殻が 区分の読み替え で渡す） ----
既定の区分 = {
    "出勤": {}, "勤務": {}, "通常": {}, "平日": {},
    "休日": {"日の種類": "休日"}, "公休": {"日の種類": "休日"},
    "所定休日": {"日の種類": "休日", "休日の区分": "所定"}, "法定休日": {"日の種類": "休日", "休日の区分": "法定"},
    "休日出勤": {"日の種類": "休日勤務"}, "休出": {"日の種類": "休日勤務"},
    "法定休日出勤": {"日の種類": "休日勤務", "休日の区分": "法定"}, "所定休日出勤": {"日の種類": "休日勤務", "休日の区分": "所定"},
    "欠勤": {"日の種類": "欠勤"},
    "有給": {"日の種類": "休暇", "休暇の種類": "年休", "休暇の単位": "全日"},
    "有休": {"日の種類": "休暇", "休暇の種類": "年休", "休暇の単位": "全日"},
    "有給休暇": {"日の種類": "休暇", "休暇の種類": "年休", "休暇の単位": "全日"},
    "年休": {"日の種類": "休暇", "休暇の種類": "年休", "休暇の単位": "全日"},
    "年次有給休暇": {"日の種類": "休暇", "休暇の種類": "年休", "休暇の単位": "全日"},
    "午前半休": {"休暇の種類": "年休", "休暇の単位": "午前半休"}, "午前休": {"休暇の種類": "年休", "休暇の単位": "午前半休"},
    "午後半休": {"休暇の種類": "年休", "休暇の単位": "午後半休"}, "午後休": {"休暇の種類": "年休", "休暇の単位": "午後半休"},
    "代休": {"日の種類": "休暇", "休暇の種類": "代休", "休暇の単位": "全日"},
    "振休": {"日の種類": "休日", "振替": "1"}, "振替休日": {"日の種類": "休日", "振替": "1"},
    "振替出勤": {"日の種類": "勤務", "振替": "1"},
    "休職": {"日の種類": "休職・休業", "休暇の種類": "休職", "休暇の単位": "全日"},
    "休業": {"日の種類": "休職・休業", "休暇の種類": "会社都合の休業", "休暇の単位": "全日"},
    "遅刻": {"印": "遅刻"}, "早退": {"印": "早退"}, "定時扱い": {"印": "定時扱い"},
    "在宅": {"働いた場所": "在宅"}, "テレワーク": {"働いた場所": "在宅"}, "出張": {"働いた場所": "出張"},
    "直行直帰": {"働いた場所": "直行直帰"}, "直行": {"働いた場所": "直行直帰"}, "直帰": {"働いた場所": "直行直帰"},
}


# ---- 文脈と結果 ----
@dataclass
class 文脈:
    """殻が渡す、その月・その会社の前提。どれも Drive から殻が読んだ値（入口は Drive を開かない）。"""
    支給月: str                       # YYYY-MM
    会社: str                         # 会社の鍵
    期間の始め: str                    # YYYY-MM-DD（締めの期間。会社の決まりから殻が出す）
    期間の終わり: str                  # YYYY-MM-DD
    社員: dict = field(default_factory=dict)        # 勤怠の表記 → NO（マスタ①社員）
    休日: set = field(default_factory=set)          # 会社の暦で休日の日付（会社の決まり 時間.暦 から殻が出す）
    区分の読み替え: dict = field(default_factory=dict)  # 顧客だけの区分の語 → 既定の区分の語 か 事実の dict
    つなぎ: list = field(default_factory=list)       # マスタ⑥つなぎ の行（NO・側・道具・その道具での名・その道具での番号）
    # ---- 人ごとの前提（どれも任意。鍵は NO か 勤怠の表記。値は殻が会社の決まり・マスタの段から出す） ----
    人の型: dict = field(default_factory=dict)       # 人 → 勤務の型の鍵（表 A の 勤務の型 へ置く・型の休日 を引く）
    型の休日: dict = field(default_factory=dict)     # 勤務の型 → 休日の日付の set か {日付: True=休日／False=勤務日}
    人の休日: dict = field(default_factory=dict)     # 人 → 休日の日付の set か {日付: True／False}（その人だけの会社の休み）
    人の区分: dict = field(default_factory=dict)     # 人 → 人.区分（社員・パート・役員・兼務役員・委託）
    所定の無い人: set = field(default_factory=set)   # 人.区分 のほかに 所定の無い人（空の日は働いていない日）
    出勤簿が無い: dict = field(default_factory=dict)  # 人 → その人の日の所定時間（分）。時間.出勤簿が無い の人＝空の勤務日は所定どおりとみなす
    勤怠を取らない人: set = field(default_factory=set)  # 勤怠が無いのが正しい人（役員など。殻が決める）＝空のタブ・空の日を要確認にしない

    def 日付たち(self) -> list[str]:
        a, b = date.fromisoformat(self.期間の始め), date.fromisoformat(self.期間の終わり)
        return [(a + timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]

    def 人の値(self, 表: dict, no: str, 表記: str = ""):
        """人ごとの表を NO で引き、無ければ 勤怠の表記 で引く。"""
        if not isinstance(表, dict):
            return None
        if no in 表:
            return 表[no]
        return 表.get(表記) if 表記 else None

    def 休日か(self, d: str, no: str = "", 表記: str = "") -> bool:
        """会社の休日・勤務の型の休日・人の休日の 3 段。狭い方が勝つ（人 → 型 → 会社）。
        段の値が set ならその日付は休日、{日付: bool} なら書かれた日だけを決める（書かれない日は広い段へ）。"""
        型 = self.人の値(self.人の型, no, 表記)
        for 段 in (self.人の値(self.人の休日, no, 表記), self.型の休日.get(型) if 型 else None):
            if isinstance(段, dict):
                if d in 段:
                    return bool(段[d])
            elif 段 is not None and d in 段:
                return True
        return d in self.休日

    def 勤怠を取らないか(self, no: str, 表記: str = "") -> bool:
        return no in self.勤怠を取らない人 or (bool(表記) and 表記 in self.勤怠を取らない人)

    def 所定が無いか(self, no: str, 表記: str = "") -> bool:
        return (self.人の値(self.人の区分, no, 表記) in 所定の無い区分
                or no in self.所定の無い人 or (bool(表記) and 表記 in self.所定の無い人))


@dataclass
class 結果:
    日: list = field(default_factory=list)          # 表 A の行（dict）
    区間: list = field(default_factory=list)        # 表 B の行（dict）
    月の数字: list = field(default_factory=list)     # 月の数字の口の行（dict）
    月の変動: list = field(default_factory=list)     # 台帳「月の変動」へ足す行
    人ごとの支給控除: list = field(default_factory=list)  # マスタ「②人ごとの支給控除」へ足す行
    要確認: list = field(default_factory=list)       # {NO, 勤怠の表記, 日付, 理由}

    def 人の状態(self) -> dict:
        """NO → 仮／確定。要確認が 1 つでも残る人は仮（出口へ出さない ⟦鍵:給与計算/足りない時は仮で計算し出さない⟧）。"""
        out = {}
        for r in self.日 + self.月の数字:
            out.setdefault(r["NO"], "確定")
            if r["読み取りの確かめ"] == 要確認:
                out[r["NO"]] = "仮"
        for r in self.月の変動:
            out.setdefault(r["NO"], "確定")
            if r["確認"] == 要確認:
                out[r["NO"]] = "仮"
        for q in self.要確認:
            if q.get("NO"):
                out[q["NO"]] = "仮"
        return out


# ---- 値の読み方 ----
def 分(t) -> int | None:
    """時刻・時間の字 → 分。`8:30`・`08:30:00`・`32:00`・`翌1:00`・Excel の小数（0.354166…＝8:30・1.0416…＝翌 1:00）。読めなければ None。"""
    if t is None:
        return None
    s = str(t).strip().replace("：", ":")
    if not s:
        return None
    plus = 0
    if s.startswith("翌"):
        plus, s = 1440, s[1:].strip()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", s)
    if m:
        if int(m.group(2)) >= 60 or (m.group(3) and int(m.group(3)) >= 60):
            return None
        return int(m.group(1)) * 60 + int(m.group(2)) + plus
    if re.fullmatch(r"\d*\.\d+|\d+", s) and "." in s:
        return round(float(s) * 1440) + plus
    return None


def 長さの分(t, 書き方: str = "分") -> int | None:
    """時間の長さの字 → 分。`1:30`＝90 はどの書き方でも同じ。数だけの字は 書き方 で読む:
    `分`＝分（`45`＝45 分・日の表の休憩）／`10進`＝時間（`1.5`＝90 分）／`60進`＝時間と分（`160.30`＝160 時間 30 分・`8`＝8 時間）。"""
    if t is None or str(t).strip() == "":
        return None
    s = str(t).strip().replace("：", ":")
    m = re.fullmatch(r"(\d+):(\d{2})(?::00)?", s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    if 書き方 == "60進":
        m = re.fullmatch(r"(\d+)(?:\.(\d{1,2}))?", s)
        if not m or (m.group(2) and int(m.group(2).ljust(2, "0")) >= 60):
            return None
        return int(m.group(1)) * 60 + int((m.group(2) or "0").ljust(2, "0"))
    try:
        v = float(s)
    except ValueError:
        return None
    return round(v * 60) if 書き方 == "10進" else (round(v) if v == int(v) else None)


def 時刻(m: int | None) -> str:
    return "" if m is None else f"{m // 60}:{m % 60:02d}"


def 日の数(s) -> float | None:
    try:
        v = float(str(s).strip())
    except ValueError:
        return None
    return v if v * 2 == int(v * 2) else None


def 日付を決める(s, 文脈: 文脈) -> str | None:
    """`2026-11-03`・`2026/11/3`・`11/3`・`3`（日だけ）・`3日` → 期間の中の日付。期間の外・読めなければ None。"""
    t = str(s).strip().replace("日", "")
    days = 文脈.日付たち()
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", t)
    if m:
        d = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        return d if d in days else None
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", t)
    if m:
        hit = [d for d in days if int(d[5:7]) == int(m.group(1)) and int(d[8:]) == int(m.group(2))]
        return hit[0] if len(hit) == 1 else None
    if re.fullmatch(r"\d{1,2}", t):
        hit = [d for d in days if int(d[8:]) == int(t)]
        return hit[0] if len(hit) == 1 else None
    return None


def 区分を読む(字: str, 文脈: 文脈) -> tuple[dict, list[str]]:
    """区分の欄の字（`有給`・`午前半休、遅刻` など）→ (事実, 読めなかった語)。"""
    事実, 読めない = {}, []
    for w in [w for w in re.split(r"[、,・/\s]+", str(字 or "").strip()) if w]:
        v = 文脈.区分の読み替え.get(w, w)
        f = 既定の区分.get(v) if isinstance(v, str) else v
        if f is None:
            読めない.append(w)
            continue
        for k, x in f.items():
            if k == "印":
                事実.setdefault("印", [])
                事実["印"].append(x)
            else:
                事実[k] = x
    return 事実, 読めない


# ---- 読み口の中で使う 1 人×1 日の材料 ----
@dataclass
class 日の材料:
    勤怠の表記: str
    日付: str
    原本の名前: str
    NO: str = ""                        # 引ける読み口（つなぎ）は先に入れる。空なら 勤怠の表記 から引く
    事実: dict = field(default_factory=dict)   # 表 A の列名 → 値（区分を読んだ物など）
    区間: list = field(default_factory=list)   # (種別, 始めの分, 終わりの分 or None, 出所)
    印: list = field(default_factory=list)
    備考: list = field(default_factory=list)
    原本の時間: dict = field(default_factory=dict)  # 5 節の語 → 分（照らす用）
    理由: list = field(default_factory=list)   # 要確認の理由
    行がある: bool = True                       # 原本にこの日の行（欄）がある

    def 区分を足す(self, 字: str, 文脈: 文脈):
        f, bad = 区分を読む(字, 文脈)
        self.印 += f.pop("印", [])
        self.事実.update(f)
        for w in bad:
            self.理由.append(f"区分「{w}」が読めない")
            self.備考.append(w)

    def 労働(self, a, b, 出所="打刻", 名="出退"):
        """出と退の字から労働の区間を足す。退が出より前なら日またぎ（+24h）。"""
        ma, mb = 分(a), 分(b)
        sa, sb = str(a or "").strip(), str(b or "").strip()
        if not sa and not sb:
            return
        if (sa and ma is None) or (sb and mb is None):
            self.理由.append(f"{名}の時刻「{sa}」「{sb}」が読めない")
            self.備考.append(f"{名} {sa}〜{sb}")
            return
        if ma is None:
            self.理由.append(f"{名}の始めが無い")
            self.備考.append(f"{名} 〜{sb}")
            return
        if mb is not None and mb == ma:  # 出と退が同じ時刻は 24 時間の勤務と決めず打刻抜けにする
            self.理由.append(f"{名}の出と退が同じ時刻（{sa}）")
            self.備考.append(f"{名} {sa}〜{sb}")
            mb = None
        elif mb is not None and mb < ma:
            mb += 1440
            if mb - ma > 長すぎる日またぎ:
                self.理由.append(f"{名}を日またぎと読むと {時刻(mb - ma)} になる（長すぎる）")
        self.区間.append(("労働", ma, mb, 出所))

    def 日またぎに寄せる(self):
        """労働の区間が 0:00 を越える日は、労働の始めより前の時刻の外出・休憩の区間に +24h する（夜勤の中の外出）。"""
        労働 = [z for z in self.区間 if z[0] == "労働"]
        if not any(e is not None and e > 1440 for _, _, e, _ in 労働):
            return
        始め = min(s for _, s, _, _ in 労働)
        self.区間 = [(k, s + 1440, None if e is None else e + 1440, o) if k != "労働" and s < 始め else (k, s, e, o)
                   for k, s, e, o in self.区間]


def NOを引く(材料: 日の材料, 文脈: 文脈) -> str:
    if 材料.NO:
        return 材料.NO
    no = 文脈.社員.get(材料.勤怠の表記)
    if no:
        return str(no)
    return f"仮:{材料.勤怠の表記}"


# ---- 表 B の形の検査（勤怠の形.md 2 節・芯の入口でも同じ検査を回す） ----
def 形の検査(a: dict, bs: list[dict]) -> list[str]:
    errs = []
    if a["日の種類"] not in 日の種類たち:
        errs.append(f"日の種類「{a['日の種類']}」が選べる値の外")
    労働 = sorted((分(b["始め"]), 分(b["終わり"])) for b in bs if b["区間の種別"] == "労働")
    for b in bs:
        s, e = 分(b["始め"]), 分(b["終わり"])
        if s is None:
            errs.append(f"区間 {b['区間の番号']} の始めが無い")
        elif e is not None and not s < e:
            errs.append(f"区間 {b['区間の番号']} の始めが終わりより後")
        if b["区間の種別"] != "労働" and s is not None and e is not None:
            if not any(x <= s and (y is None or e <= y) for x, y in 労働 if x is not None):
                errs.append(f"区間 {b['区間の番号']}（{b['区間の種別']}）が労働の区間の外")
    for (s1, e1), (s2, e2) in zip(労働, 労働[1:]):
        if e1 is None or (s2 is not None and s2 < e1):
            errs.append("労働の区間が重なる")
    if a["時刻の無い休憩"] != "" and any(b["区間の種別"] == "休憩" for b in bs):
        errs.append("時刻の無い休憩と休憩の区間が同じ日にある")
    if a["時刻の無い労働時間"] != "" and 労働:
        errs.append("時刻の無い労働時間と労働の区間が同じ日にある")
    if a["日の種類"] in ("勤務", "休日勤務") and not 労働 and a["時刻の無い労働時間"] == "" and a["働いた場所"] != "みなし":
        errs.append("勤務の日に労働の区間も時刻の無い労働時間も無い")
    if a["日の種類"] not in ("勤務", "休日勤務") and 労働:
        errs.append(f"日の種類「{a['日の種類']}」の日に労働の区間がある")
    if a["休暇の種類"] and not a["休暇の単位"]:
        errs.append("休暇の種類があるのに単位が無い")
    if a["休暇の単位"] == "時間" and a["休暇の時間"] == "":
        errs.append("時間の休暇に時間が無い")
    if a["休暇の種類"] == "代休" and not a["代休の相手の日"]:
        errs.append("代休の相手の日が無い")
    return errs


# ---- 材料 → 表 A・B ----
def 仕上げる(材料たち: list[日の材料], 文脈: 文脈, 原本の種別: str, 全日を置く: bool = True) -> 結果:
    """材料を表 A・B にする。全日を置く なら期間の全部の日に表 A の行を置く（原本に無い日は 休日／欠勤・要確認・印 原本に無い）。"""
    assert 原本の種別 in 原本の種別たち
    寄せ: dict = {}
    for m in 材料たち:
        no = NOを引く(m, 文脈)
        k = (no, m.日付)
        if k in 寄せ:  # 同じ人×日が 2 回出たら 1 つの日に寄せる（組は区間に並べる）
            x = 寄せ[k]
            for 種別, s, e, o in m.区間:
                if any(z[1] == s and z[2] == e and z[0] == 種別 for z in x.区間):
                    x.印.append("二重打刻")
                    x.備考.append(f"重なった{種別} {時刻(s)}〜{時刻(e)}")
                else:
                    x.区間.append((種別, s, e, o))
            for f, v in m.事実.items():
                if f in x.事実 and x.事実[f] != v:
                    x.理由.append(f"{f} が 2 つ（{x.事実[f]}・{v}）")
                x.事実.setdefault(f, v)
            x.印 += m.印
            x.備考 += m.備考
            x.理由 += m.理由
            x.原本の時間.update(m.原本の時間)
        else:
            寄せ[k] = m
    # 勤怠を取らない人（役員など）の空のタブ（どの日も時刻・区分・印・理由が無い）は人ごと出さない＝勤怠が無いのが正しい
    # （芯/集計 が 勤怠が無い 役員を確認済にする）。1 日でも書いてあれば今までどおり読む（空の日は下の _一日 が要確認にしない）
    空の人 = {no for (no, _), m in 寄せ.items() if 文脈.勤怠を取らないか(no, m.勤怠の表記)}
    for (no, _), m in 寄せ.items():
        if no in 空の人 and (m.区間 or m.事実 or m.理由 or m.印 or m.備考 or m.原本の時間):
            空の人.discard(no)
    寄せ = {k: m for k, m in 寄せ.items() if k[0] not in 空の人}
    人たち: dict = {}
    for (no, d), m in 寄せ.items():
        人たち.setdefault(no, m.勤怠の表記)
    if 全日を置く:
        for no, 表記 in 人たち.items():
            for d in 文脈.日付たち():
                if (no, d) not in 寄せ:
                    寄せ[(no, d)] = 日の材料(表記, d, 原本の名前="", NO=no, 行がある=False)
        原本名 = {no: next(m.原本の名前 for (n, _), m in 寄せ.items() if n == no and m.原本の名前) for no in 人たち}
        for (no, d), m in 寄せ.items():
            if not m.原本の名前:
                m.原本の名前 = 原本名[no]

    out = 結果()
    for (no, d) in sorted(寄せ):
        m = 寄せ[(no, d)]
        m.日またぎに寄せる()
        a, bs, 理由 = _一日(m, no, d, 文脈, 原本の種別)
        out.日.append(a)
        out.区間 += bs
        if no.startswith("仮:"):
            理由.insert(0, "勤怠の表記がマスタの社員に無い（NO を引けない）")
        for r in 理由:
            out.要確認.append({"NO": no, "勤怠の表記": m.勤怠の表記, "日付": d, "理由": r})
        if 理由:
            a["読み取りの確かめ"] = 要確認
    return out


def _一日(m: 日の材料, no: str, d: str, 文脈: 文脈, 種別: str):
    f = dict(m.事実)
    印 = list(m.印)
    理由 = list(m.理由)
    所定が無い = 文脈.所定が無いか(no, m.勤怠の表記)
    休日の日 = 文脈.休日か(d, no, m.勤怠の表記) and not 所定が無い  # 所定の無い人に休日勤務は無い
    みなしの所定 = 文脈.人の値(文脈.出勤簿が無い, no, m.勤怠の表記)
    出勤簿が無い = みなしの所定 is not None or no in 文脈.出勤簿が無い or m.勤怠の表記 in 文脈.出勤簿が無い
    型 = 文脈.人の値(文脈.人の型, no, m.勤怠の表記)
    if 型 and not f.get("勤務の型"):
        f["勤務の型"] = 型
    労働がある = any(z[0] == "労働" for z in m.区間) or f.get("時刻の無い労働時間", "") != ""
    種 = f.get("日の種類", "")
    空の日 = not 種 and not 労働がある and not f.get("休暇の種類")
    長さが決まらない = False
    if 空の日 and 所定が無い:
        種 = "休日"  # 所定の無い人（委託など）の空の日は働いていない日（勤務日に数えない）
        m.備考.append("所定の無い人の空の日（働いていない日）")
    elif 空の日 and 文脈.勤怠を取らないか(no, m.勤怠の表記):
        種 = "休日"  # 勤怠を取らない人（役員など）の空の日は勤怠が無いのが正しい（欠勤にも要確認にもしない）
        m.備考.append("勤怠を取らない人の空の日")
    elif 空の日 and 出勤簿が無い and not 休日の日:
        種 = "勤務"  # 時間.出勤簿が無い の人の空の勤務日は所定どおり働いたとみなす
        印.append("定時扱い")
        m.備考.append("出勤簿が無い（所定どおり働いたとみなした）")
        所定 = みなしの所定 if isinstance(みなしの所定, int) and not isinstance(みなしの所定, bool) else (
            int(みなしの所定) if isinstance(みなしの所定, str) and みなしの所定.strip().isdigit() else None)
        if 所定:
            f["所定時間"] = str(所定)
            f["時刻の無い労働時間"] = str(所定)
        else:
            理由.append("出勤簿が無い人の日の所定時間が渡されていない")
    elif 空の日 and 出勤簿が無い:
        種 = "休日"
    elif not m.行がある:
        種 = "休日" if 休日の日 else "欠勤"
        印.append("原本に無い")
        理由.append("原本にこの日が無い")
    elif not 種:
        if 労働がある:
            種 = "休日勤務" if 休日の日 else "勤務"
        elif f.get("休暇の種類"):
            種 = "休暇"  # 半休だけの日など。残りの半日は芯が見る
        elif 休日の日:
            種 = "休日"
        else:
            種 = "欠勤"
            理由.append("勤務日に時刻も区分も無い")
    elif 種 == "休日" and 労働がある:
        種 = "休日勤務"
    elif (種 == "休暇" and 労働がある and f.get("休暇の種類") == "年休" and f.get("休暇の単位", "全日") == "全日"
          and not 休日の日 and not 所定が無い):
        種, 単位 = "勤務", 年休と勤務の単位(m, f)  # 年休を書いた日に勤務の時刻もある＝その日の一部を休んだ日
        f["休暇の単位"] = 単位
        長さが決まらない = not 単位
        if 単位:
            m.備考.append(f"年休の日に勤務の時刻がある（{単位}＋勤務と読んだ）")
        else:
            理由.append("年休の日に勤務の時刻がある（年休の長さ＝半日か時間かが原本から決まらない）")
    if f.pop("振替", None):
        if not f.get("振替の相手の日"):
            理由.append("振替の相手の日が無い")
    if f.get("休暇の種類") and not f.get("休暇の単位") and not 長さが決まらない:
        f["休暇の単位"] = "全日"
    if 種 in ("勤務", "休日勤務") and not f.get("働いた場所"):
        f["働いた場所"] = "事業所"

    a = {c: "" for c in 表Aの列}
    a.update({k: str(v) for k, v in f.items() if k in a})
    a.update({
        "支給月": 文脈.支給月, "会社": 文脈.会社, "NO": no, "勤怠の表記": m.勤怠の表記, "日付": d, "日の種類": 種,
        "原本の名前": m.原本の名前, "原本の種別": 種別, "読み取りの確かめ": 確認済,
    })
    bs = []
    for i, (k, s, e, o) in enumerate(sorted(m.区間, key=lambda z: (z[1], 区間の種別たち.index(z[0]))), 1):
        if e is None:
            印.append("打刻抜け")
            理由.append(f"{k}の終わりが無い（打刻抜け）")
        if o == "所定で埋めた":
            理由.append("所定で埋めた時刻がある")
        bs.append({"支給月": 文脈.支給月, "会社": 文脈.会社, "NO": no, "日付": d, "区間の番号": str(i),
                   "区間の種別": k, "始め": 時刻(s), "終わり": 時刻(e), "時刻の出所": o})
    a["印"] = "、".join(dict.fromkeys(x for x in 印 if x))
    a["原本の時間"] = "、".join(f"{k}={v}" for k, v in m.原本の時間.items())
    a["備考"] = "、".join(dict.fromkeys(x for x in m.備考 if x))
    理由 += 形の検査(a, bs)
    return a, bs, list(dict.fromkeys(理由))


正午 = 12 * 60
昼の終わり = 13 * 60


def 年休と勤務の単位(m: 日の材料, f: dict) -> str:
    """年休（全日と読んだ区分）の日に勤務の時刻もある日の、年休の単位。原本から決まらなければ ''（要確認）。
    休暇の時間がある＝時間。労働の区間が全部 正午 から後（日をまたがない）＝午前半休、全部 13:00 までに終わる＝午後半休。
    どちらにも当たる・どちらにも当たらない・時刻の無い労働時間だけ・打刻抜け＝決まらない（黙って全日にも半日にもしない）。"""
    if str(f.get("休暇の時間", "")).strip():
        return "時間"
    労 = [(s, e) for k, s, e, _ in m.区間 if k == "労働"]
    if not 労 or any(e is None for _, e in 労):
        return ""
    午後だけ = min(s for s, _ in 労) >= 正午 and max(e for _, e in 労) <= 1440
    午前だけ = max(e for _, e in 労) <= 昼の終わり
    if 午後だけ == 午前だけ:
        return ""
    return "午前半休" if 午後だけ else "午後半休"


def 重ねる(基: 結果, 上: 結果) -> 結果:
    """2 つの原本の結果を重ねる。上に在る人×日は、基の表 A・B の行と要確認を上の物で置き換える（読む順は作業のルール）。"""
    keys = {(r["NO"], r["日付"]) for r in 上.日}
    out = 結果()
    out.日 = sorted([r for r in 基.日 if (r["NO"], r["日付"]) not in keys] + 上.日, key=lambda r: (r["NO"], r["日付"]))
    out.区間 = sorted([r for r in 基.区間 if (r["NO"], r["日付"]) not in keys] + 上.区間,
                    key=lambda r: (r["NO"], r["日付"], int(r["区間の番号"])))
    out.要確認 = [q for q in 基.要確認 if (q["NO"], q.get("日付")) not in keys] + 上.要確認
    out.月の数字 = 基.月の数字 + 上.月の数字
    out.月の変動 = 基.月の変動 + 上.月の変動
    out.人ごとの支給控除 = 基.人ごとの支給控除 + 上.人ごとの支給控除
    return out


# ---- 日ごとの時刻の表（PDF タイムカード・Excel 出勤簿・勤怠システムの月報が共に使う） ----
# 欄の役: 日・出・退（出 2・退 2…と並べてよい）・外出・戻・休憩（長さ）・区分・備考・時間数（印字。照らす用）
def 欄の役(見出し: list[str], 読み替え: dict) -> list[str]:
    return [読み替え.get(str(h).strip(), str(h).strip()) for h in 見出し]


def 組にする(役: list[str], 行: list) -> dict:
    """1 行を 役 → 値（出・退は 出_1, 退_1, 出_2… と順に番号を振る）。"""
    out, n = {}, {}
    for r, v in zip(役, list(行) + [""] * (len(役) - len(行))):
        if r in ("出", "退", "外出", "戻"):
            n[r] = n.get(r, 0) + 1
            out[f"{r}_{n[r]}"] = v
        else:
            out[r] = v
    return out
