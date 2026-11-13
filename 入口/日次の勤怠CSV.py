"""列名つきの日次の勤怠 CSV（1 行＝1 人×1 日）の読み口。勤怠ツールが書き出す日次の CSV の一般の形。

製品の名と既定の列名を持たない（⟦鍵:給与計算/パックに製品ごとの物を置かない⟧）。殻が渡す物:
- CSV の字（ヘッダーの行つき）・原本の名前・文脈（つなぎ を含む）。入口は Drive も勤怠ツールも開かない。
- 道具: マスタ⑥つなぎ の「道具」の字（事務所が付けた勤怠ツールの呼び名）。人と列名をこの字の行から引く。
- 列名: 役 → その CSV の見出しの字。渡さなければ 文脈.つなぎ の 側＝入口・道具＝<道具>・NO が空 の行
  （その道具での番号＝`列.<役>`・その道具での名＝見出しの字）から引く。どちらにも 番号・日付・出・退 が無ければ止まる。
人: 文脈.つなぎ の 側＝入口・道具＝<道具>・NO 有り の行で「その道具での番号」→ NO。無ければ 氏名 を マスタの勤怠の表記 で引く。
区分: 勤務区分の語は顧客ごとに作れる。既定の区分に無い語は 文脈.区分の読み替え で渡す（無ければ要確認）。
ツールが出した実働・深夜は 原本の時間 へ（照らす用・計算に使わない）。残業時間は法定内か法定外かがツールの設定次第なので 備考 へ字のまま。
"""
import csv
import io

from . import 口

種別 = "勤怠システムの月報"  # 勤怠の形.md の 原本の種別 の語（ツールの名は表 A に出さない）
役たち = ("番号", "氏名", "日付", "区分", "出", "退", "休憩", "外出", "戻", "実働", "深夜", "残業", "備考")
要る役 = ("番号", "日付", "出", "退")
列の印 = "列."


def つなぎの列名(つなぎ, 道具: str) -> dict:
    """マスタ⑥つなぎ の会社の行（NO 空・側＝入口・道具＝<道具>・その道具での番号＝`列.<役>`）→ {役: 見出しの字}。"""
    out = {}
    for t in つなぎ or ():
        番 = str(t.get("その道具での番号", "") or "").strip()
        if (t.get("側") == "入口" and str(t.get("道具", "")).strip() == 道具
                and not str(t.get("NO", "") or "").strip() and 番.startswith(列の印)):
            out[番[len(列の印):]] = str(t.get("その道具での名", "") or "").strip()
    return out


def 読む(csv字: str, 原本の名前: str, 文脈, 道具: str, 列名: dict | None = None) -> 口.結果:
    道具 = str(道具 or "").strip()
    if not 道具:
        raise ValueError("日次の勤怠CSV: 道具（マスタ⑥つなぎ の勤怠ツールの呼び名）を殻が渡す")
    名 = {k: v for k, v in (列名 if 列名 is not None else つなぎの列名(文脈.つなぎ, 道具)).items() if v}
    知らない = [k for k in 名 if k not in 役たち]
    if 知らない:
        raise ValueError(f"日次の勤怠CSV: 列名の役「{'・'.join(知らない)}」は {'・'.join(役たち)} の外")
    足りない = [r for r in 要る役 if r not in 名]
    if 足りない:
        raise ValueError(f"日次の勤怠CSV: 列名に {'・'.join(足りない)} が無い（マスタ⑥つなぎ の {道具} の会社の行"
                         f"〔その道具での番号＝{列の印}<役>〕か 列名 で殻が渡す。既定の列名は持たない）")
    番号から = {str(t.get("その道具での番号", "")).strip(): str(t["NO"]).strip()
             for t in 文脈.つなぎ
             if t.get("側") == "入口" and str(t.get("道具", "")).strip() == 道具 and str(t.get("NO", "")).strip()}
    rd = csv.DictReader(io.StringIO(csv字.lstrip("\ufeff")))
    無い列 = [r for r in 要る役 if 名[r] not in (rd.fieldnames or [])]
    if 無い列:
        raise ValueError(f"CSV に {道具} の列「{'・'.join(名[r] for r in 無い列)}」が無い（列名 を直す）")
    材料たち = []
    for row in rd:
        def g(r, row=row):  # 渡されなかった役（任意の列）は空
            return str(row.get(名[r], "") or "").strip() if r in 名 else ""
        if not g("番号") and not g("氏名"):
            continue
        d = 口.日付を決める(g("日付"), 文脈)
        if d is None:
            continue  # 期間の外の日（CSV は月より広く出せる）は読まない
        # つなぎに無く氏名も空の人は 仮:<番号> にする（違う人を 1 人に寄せない）
        no = 番号から.get(g("番号"), "") or ("" if g("氏名") else f"仮:{g('番号')}")
        m = 口.日の材料(g("氏名"), d, 原本の名前, NO=no)
        if g("区分"):
            m.区分を足す(g("区分"), 文脈)
        m.労働(g("出"), g("退"), "打刻")
        if g("外出") or g("戻"):
            s, e = 口.分(g("外出")), 口.分(g("戻"))
            if s is None or e is None:
                m.理由.append("外出と戻りが組にならない")
            else:
                m.区間.append(("外出", s, e if e > s else e + 1440, "打刻"))
        if g("休憩"):
            v = 口.長さの分(g("休憩"))
            if v is None:
                m.理由.append(f"休憩「{g('休憩')}」が読めない")
            else:
                m.事実["時刻の無い休憩"] = str(v)
        for r, 語 in (("実働", "総労働"), ("深夜", "深夜")):
            v = 口.長さの分(g(r), "60進") if g(r) else None
            if v is not None:
                m.原本の時間[語] = v
        if g("残業"):
            m.備考.append(f"残業 {g('残業')}")
        if g("備考"):
            m.備考.append(g("備考"))
        材料たち.append(m)
    return 口.仕上げる(材料たち, 文脈, 種別)
