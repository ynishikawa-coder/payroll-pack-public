"""作り物の小さな答え（一覧表 2 つの向き・明細 1 枚）と芯の行。顧客の値は 1 つも無い。"""
import io
import zipfile
from xml.sax.saxutils import escape

月 = "2026-10"
会社 = "9"

つなぎ = [
    dict(項目="基本給", 欄="基本給", 形="円"),
    dict(項目="残業手当", 欄="残業手当", 形="円"),
    dict(項目="総支給", 欄="総支給額", 形="円"),
    dict(項目="残業時間", 欄="残業 時間", 形="分"),
]
読まない見出し = ("氏名", "所属", "作り物の給与明細", "作り物の勤怠と支給の一覧")

# 横（人が行）の CSV。合計の行は読まない・空のセルは 0・氏名と所属は読まない
一覧表_横 = (
    "作り物の支給控除一覧表\n"
    "NO,氏名,所属,基本給,残業手当,総支給額,残業 時間\n"
    "0001,作り物 一,本社,200000,12500,212500,10:00\n"
    "0002,作り物 二,本社,180000,,180000,0:00\n"
    "合計,,,380000,12500,392500,10:00\n"
)


def _列(j):
    s = ""
    j += 1
    while j:
        j, r = divmod(j - 1, 26)
        s = chr(65 + r) + s
    return s


def xlsx(タブたち):
    """{タブの名: [[値...]...]} → xlsx の bytes。数は数のセル・("時", 日の小数) は時刻の書式のセル・字は inlineStr。"""
    b = io.BytesIO()
    z = zipfile.ZipFile(b, "w")
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rns = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    sheets, rels = [], []
    for n, (名, rows) in enumerate(タブたち.items(), start=1):
        xs = []
        for i, row in enumerate(rows, start=1):
            cs = []
            for j, v in enumerate(row):
                ref = f"{_列(j)}{i}"
                if v == "" or v is None:
                    continue
                if isinstance(v, tuple):
                    cs.append(f'<c r="{ref}" s="1"><v>{v[1]}</v></c>')
                elif isinstance(v, int):
                    cs.append(f'<c r="{ref}"><v>{v}</v></c>')
                else:
                    cs.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(v)}</t></is></c>')
            xs.append(f'<row r="{i}">{"".join(cs)}</row>')
        z.writestr(f"xl/worksheets/sheet{n}.xml", f'<worksheet {ns}><sheetData>{"".join(xs)}</sheetData></worksheet>')
        sheets.append(f'<sheet name="{escape(名)}" sheetId="{n}" r:id="rId{n}"/>')
        rels.append(f'<Relationship Id="rId{n}" Type="worksheet" Target="worksheets/sheet{n}.xml"/>')
    z.writestr("xl/workbook.xml", f'<workbook {ns} {rns}><sheets>{"".join(sheets)}</sheets></workbook>')
    z.writestr("xl/_rels/workbook.xml.rels",
               f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{"".join(rels)}</Relationships>')
    z.writestr("xl/styles.xml", f'<styleSheet {ns}><numFmts count="1"><numFmt numFmtId="164" formatCode="[h]:mm"/></numFmts>'
               '<cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="164"/></cellXfs></styleSheet>')
    z.close()
    return b.getvalue()


# 縦（人が列）の xlsx。残業時間は時刻の書式（1.5 時間＝0.0625 日）・合計の列は読まない
一覧表_縦 = xlsx({"10月": [
    ["作り物の勤怠と支給の一覧", "", "", ""],
    ["ＮＯ", "0003", "0004", "合計"],
    ["氏名", "作り物 三", "作り物 四", ""],
    ["基本給", 150000, 160000, 310000],
    ["残業手当", 3000, 0, 3000],
    ["総支給額", 153000, 160000, 313000],
    ["残業 時間", ("時", "0.0625"), ("時", "0"), ("時", "0.0625")],
]})

# 明細（1 人 1 枚）。値は右か下
明細 = xlsx({"0005": [
    ["作り物の給与明細", "", ""],
    ["NO", "0005", ""],
    ["基本給", "残業手当", "総支給額"],
    [170000, 2001, 172001],
    ["残業 時間", "1:01", ""],
]})


def R(no, 項目, 値, 状態="確定", 月_=月, 出所="作り物の原本"):
    return dict(支給月=月_, 会社=会社, NO=no, 項目=項目, 値=値, 状態=状態, 出所=出所,
                問いの番号="Q-1" if 状態 == "仮" else "")


# 芯の計算の行（作り物）。0001 は全部一致・0002 は残業手当が片方だけ・0003 は総支給に 1 円（丸め）
# 0004 は基本給が違う（決まりの違い）・0005 は仮で外れる・2026-09 は答えが無い月
芯の行 = [
    R("0001", "基本給", 200000), R("0001", "残業手当", 12500), R("0001", "総支給", 212500), R("0001", "残業時間", 600),
    R("0002", "基本給", 180000), R("0002", "総支給", 180000), R("0002", "残業時間", 0),
    R("0003", "基本給", 150000), R("0003", "残業手当", 3000), R("0003", "総支給", 153001), R("0003", "残業時間", 90),
    R("0004", "基本給", 165000), R("0004", "残業手当", 0), R("0004", "総支給", 160000), R("0004", "残業時間", 0),
    R("0005", "基本給", 170000), R("0005", "残業手当", 2001, 状態="仮"),
    R("0001", "基本給", 200000, 月_="2026-09"),
]
