# -*- coding: utf-8 -*-
"""直しを 1 社の値に当てる 1 つの中身（docs/設計/寄せる道具.md §1）。

Drive を開かない。殻が読んだ値（get_values の JSON・md の本文・置き場の一覧）と型を受け、
寄せた後の値・書く手順・戻す手順・寄せられない物・足りない値・人が見る物・値の保ちの照らしを返す。
書くのは殻。寄せられない物が 1 つでも残れば書く手順は空（1 社は全部か無し）。

会社の物（入力の JSON）:
  {"会社": "作り物の会社", "型の版": 0, "選んだ部品": [],
   "シート": {"03_マスタ": {"社員": [[見出し…], [値…], …]}, …},   ← タブごとの get_values
   "式": {"03_マスタ": {"社員": [[行, 列], …]}},                  ← 式のセル（0 始まり・任意）
   "md": {"01_ルール/給与のルール.md": "本文"},
   "置き場": ["01_ルール/", "01_ルール/給与のルール.md", …],       ← 組の根からの名（フォルダは / で終わる）
   "人の答え": {"<寄せられない物の鍵>": "<選んだ答え>",
              "前の形の読み替え": [{"版": N, "操作": [...], "手がかり": {...}}]}}   ← 任意（下の 前の形を足す）
型（初期設定/型.json を 型を開く() で読んだ物。形は 型を読む() の説明）。
"""
import copy
import calendar
import json
import datetime as dt
import re

import 直し as 直しの形

# 型の読み方（タブの列に項目の列を広げる決まり）は 初期設定/型の口.py の 1 か所を使う
import importlib.util as _imp
from pathlib import Path as _Path
_spec = _imp.spec_from_file_location("初期設定_型の口_寄せ", _Path(__file__).resolve().parents[2] / "初期設定" / "型の口.py")
型の口 = _imp.module_from_spec(_spec)
_spec.loader.exec_module(型の口)

旧の頭 = "旧_"


前の形の鍵 = "前の形の読み替え"
前の形の塊の鍵 = {"版", "操作", "手がかり", "なぜ"}


def 前の形を足す(直したち: list[dict], 前の形) -> list[dict]:
    """事務所が人の答えで渡す「前の形の読み替え」を、同じ版のパックの直しの操作の前に足した鎖を返す。

    パックの直しは どの事務所にも当たる型の作り（タブ・列を足す・並び）だけを持つ。1 つの事務所の前の道具の形に
    結びつく読み替え（前の列の名 → 今の列・前の語 → 今の項目・前の置き場や md の見出しの名・前の語の手がかり）は
    パックに置かず、その事務所の Drive の寄せの記録に置き、殻が 人の答え の `前の形の読み替え` で渡す
    （docs/設計/入れてよい物.md ⟦鍵:給与計算/移行だけの物はパックに入れない⟧）。
    形: [{"版": N, "操作": [直しの閉じた一覧の操作…], "手がかり": {…}, "なぜ": "…"}]。版 N の塊は、この回に当てる
    版 N の直しの操作の前に当てる（会社の版が N 以上なら当てない）。操作の形は直しと同じに確かめる。
    """
    if not 前の形:
        return 直したち
    if not isinstance(前の形, list):
        raise 直しの形.直しの誤り(f"人の答え「{前の形の鍵}」は [{{版・操作・手がかり}}…] の形")
    塊 = {}
    # 塊は同じ版のパックの直し（型の作り）の前に当たる。前の形の操作が型の作りに頼る時（例 鍵 会社 で畳む前の 列「会社」を足す）は、
    # その操作も塊に入れる（型の作りの操作は二度当てても同じ＝前の版の直しの全部の操作を入れてもよい）
    for i, b in enumerate(前の形, 1):
        名 = f"人の答え「{前の形の鍵}」の {i} つ目"
        if not isinstance(b, dict) or type(b.get("版")) is not int or b["版"] < 1 or not isinstance(b.get("操作", []), list):
            raise 直しの形.直しの誤り(f"{名}: 版（1 以上の数）と 操作（並び）が要る")
        知らない = set(b) - 前の形の塊の鍵
        if 知らない:
            raise 直しの形.直しの誤り(f"{名}: 知らない鍵 {sorted(知らない)}")
        if not isinstance(b.get("手がかり", {}), dict):
            raise 直しの形.直しの誤り(f"{名}: 手がかり は {{鍵: 字}} の形")
        if not all(isinstance(op, dict) for op in b.get("操作", [])):
            raise 直しの形.直しの誤り(f"{名}: 操作 の 1 つ 1 つは {{\"する\": …}} の形")
        誤り = 直しの形.形を確かめる({"版": b["版"], "前の版": b["版"] - 1, "なぜ": b.get("なぜ", "前の形の読み替え"),
                                 "操作": b.get("操作", [])}, 名)
        if 誤り:
            raise 直しの形.直しの誤り("\n".join(誤り))
        if b["版"] in 塊:
            raise 直しの形.直しの誤り(f"{名}: 版 {b['版']} の塊が 2 つ（1 つにまとめる）")
        塊[b["版"]] = b
    最後 = 直したち[-1]["版"] if 直したち else 0
    先 = sorted(v for v in 塊 if v > 最後)
    if 先:  # 消した古い直しの版の塊は当てる所が無い（全社がその版より上）＝黙って飛ばす
        raise 直しの形.直しの誤り(f"人の答え「{前の形の鍵}」: 版 {先} の直しがパックにまだ無い（前の形の読み替えは同じ版の直しの前に当てる）")
    out = []
    for d in 直したち:
        b = 塊.get(d["版"])
        if b is None:
            out.append(d)
            continue
        out.append({**d, "操作": [*b.get("操作", []), *d["操作"]],
                    "手がかり": {**d.get("手がかり", {}), **b.get("手がかり", {})}, "前の形の操作": len(b.get("操作", []))})
    return out


class 保ちの誤り(RuntimeError):
    """値の保ちの照らしが合わない＝道具の誤り。道具は止まる。"""


# ---------------------------------------------------------------- 型

def 型を開く(path) -> dict:
    """型の正本（初期設定/型.json）と、同じ置き場の 項目.json・雛形/ を読んで 1 つの dict にする（Drive は開かない）。"""
    from pathlib import Path
    p = Path(path)
    型 = json.loads(p.read_text(encoding="utf-8"))
    項 = p.parent / "項目.json"
    型["_項目"] = json.loads(項.read_text(encoding="utf-8"))["項目"] if 項.is_file() else []
    型["_md"] = {m["名"]: (p.parent / m["雛形"]).read_text(encoding="utf-8") for m in 型.get("md の雛形", [])}
    return 型


def 組の根から(置き場: str, 名: str) -> str:
    """型の 置き場＋名 を、殻が渡す名（組の根からの名。事務所の物は 00_事務所/…）にする。"""
    rel = re.sub(r"^10_会社/<組>/?", "", 置き場)
    return f"{rel}/{名}" if rel else 名


def 型を読む(型: dict) -> dict:
    """型の正本の形（初期設定/型.json＝B11）を道具の中の形にそろえる。読むのはこの 1 か所。

    {"版", "シート": [{"シート", "置き場", "タブ": [{"タブ", "列": [{"名", "意味"}], "項目の列"?: 段, "語"?: [...]}]}],
     "md の雛形": [{"名", "置き場", "雛形"}]}（型を開く() が 項目.json を "_項目"・雛形の本文を "_md" に足す）。
    列は「列」の後ろに「項目の列」を辞書の順に並べる（広げ方は 初期設定/型の口.py の タブの列() を使う＝読み方は 1 か所）。
    """
    out = {"版": int(型.get("版", 0) or 0), "ファイル": {}, "md": {}}
    項目たち = 型.get("_項目", [])
    for s in 型.get("シート", []):
        tabs = {}
        for t in s.get("タブ", []):
            cols = 型の口.タブの列(t, 項目たち)
            for c in cols:
                if c["名"] == "会社":
                    c["必須"] = True  # Drive の型 §1: 全タブの列「会社」は必須
                if c["名"] == "項目" and t.get("語"):
                    c["選べる値"] = list(t["語"])
                if c["名"] == "項目" and s["シート"] == "03_マスタ" and t["タブ"] == "会社":
                    c["形"] = r"[^.\s]+\.\S+"  # 会社の決まり.md §1.3: 項目は `分野.名`
            tabs[t["タブ"]] = cols
        out["ファイル"][組の根から(s.get("置き場", ""), s["シート"])] = tabs
    for m in 型.get("md の雛形", []):
        text = 型.get("_md", {}).get(m["名"], "")
        heads = [l for l in text.splitlines() if l.startswith("## ") and "<" not in l]
        out["md"][組の根から(m.get("置き場", ""), m["名"])] = heads
    return out


def 名の型(pattern: str) -> re.Pattern:
    return re.compile(re.escape(pattern).replace(re.escape("<支給年>"), r"\d{4}") + "$")


def 型のファイル(K: dict, f: str):
    for p, tabs in K["ファイル"].items():
        if 名の型(p).match(f):
            return tabs
    return None


# ---------------------------------------------------------------- 会社の物

def 空か(v) -> bool:
    return v is None or str(v).strip() == ""


def そろえる(rows: list) -> list[list[str]]:
    """get_values と同じ形にそろえる: 行の長さを合わせ、終わりの空の行・空の列を落とす。"""
    rows = [["" if v is None else v for v in r] for r in rows]
    while rows and all(空か(v) for v in rows[-1]):
        rows.pop()
    w = max((len(r) for r in rows), default=0)
    while w and all(len(r) < w or 空か(r[w - 1]) for r in rows):
        w -= 1
    return [(r + [""] * (w - len(r)))[:w] for r in rows]


class 物:
    def __init__(self, d: dict):
        self.会社 = d["会社"]
        self.版 = int(d.get("型の版", 0) or 0)
        self.部品 = list(d.get("選んだ部品", []))
        self.シート = {f: {t: そろえる(v) for t, v in tabs.items()} for f, tabs in d.get("シート", {}).items()}
        self.式 = {(f, t, int(r), int(c)) for f, tabs in d.get("式", {}).items() for t, cells in tabs.items() for r, c in cells}
        self.md = dict(d.get("md", {}))
        self.置き場 = list(d.get("置き場", []))
        # 寄せの写しの置き場は 90_履歴/ の 1 つ（README）。前の答えの語「99_ へ写して消す」も同じ意味で受ける
        答え = dict(d.get("人の答え", {}))
        self.前の形 = 答え.pop(前の形の鍵, [])  # 事務所が渡す前の形の読み替え（前の形を足す）。問いの鍵ではない
        self.人の答え = {k: (v.replace("99_ へ写して消す", "90_履歴 へ写して消す") if isinstance(v, str) else v)
                      for k, v in 答え.items()}

    def 出す(self) -> dict:
        return {"会社": self.会社, "型の版": self.版, "選んだ部品": self.部品,
                "シート": copy.deepcopy(self.シート), "md": dict(self.md), "置き場": list(self.置き場)}


def 数える(シート: dict) -> int:
    """見出しの下の空でないセルの数（旧_ のタブは数えない）。"""
    return sum(1 for tabs in シート.values() for t, rows in tabs.items() if not t.startswith(旧の頭)
               for r in rows[1:] for v in r if not 空か(v))


class 記録:
    def __init__(self):
        self.寄せられない = []
        self.足りない = []
        self.数 = {"足した": 0, "重ねた": 0, "md へ移した": 0, "他の所へ移した": 0, "捨てた（直しの持たない）": 0, "捨てた（人の答え）": 0}
        self.持たない = []      # (所, 件数, なぜ)
        self.知らせ = []
        self.消す問い = []
        self.タブの名 = []      # (ファイル, 前, 後)
        self.足したタブ = []    # (ファイル, タブ)
        self.移した = []        # (前, 後)
        self.当てた = []        # (版, 操作の番号, する, 所)
        self.渡すタブ = set()    # (ファイル, タブ)＝値を他のタブ・md へ渡したタブ（書く手順で受け取る側の後に書く）
        self.ぶつかる列 = set()  # (ファイル, タブ, 列)＝ぶつかりで残った前の列（照らすで二重に出さない）
        self.待つタブ = set()    # (ファイル, タブ)＝人の答えで消す問いへ回した前のタブ（照らすで二重に出さない）
        self.答えで項目を変えた = {}  # (ファイル, タブ) → 行の id の集まり＝人の答え（値:<項目>）で項目を今の名にした行
        self.書かない = []      # 計算の形.py が外した行のうち、出口などが読む値の在った物（書かない物の一覧へ足す）
        self.無い値 = []        # 寄せた後に無い値（段の解決・芯が仮と問いにする。寄せは値を作らない）

    def 解けた(self, 鍵):
        """前の直しが出した問いを、後の直しが解いた（同じ鍵の値が今の形になった）。"""
        self.寄せられない = [x for x in self.寄せられない if x["鍵"] != 鍵]

    def 出せない(self, 鍵, 種類, 所, 中身, 答え, 手がかり=""):
        if any(x["鍵"] == 鍵 for x in self.寄せられない):
            return
        self.寄せられない.append({"鍵": 鍵, "種類": 種類, "所": 所, "中身": 中身, "選べる答え": 答え, "手がかり": 手がかり})


# ---------------------------------------------------------------- 小さな部品

def 日付(v) -> str:
    """YYYY-MM-DD・YYYY/M/D・YYYY.M.D の頭を YYYY-MM-DD にする（読めなければ空）。"""
    m = re.match(r"\s*(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", str(v or ""))
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""


def 列の番号(rows, 名):
    if not rows:
        return None
    try:
        return rows[0].index(名)
    except ValueError:
        return None


def 列を消す(rows, i):
    for r in rows:
        del r[i]


def 行が合う(row, head, 行) -> bool:
    for c, want in 行.items():
        if c not in head:
            if want == "":  # 列が無い＝その列は空と見る（メモの無い会社のタブなど）
                continue
            return False
        v = str(row[head.index(c)]).strip()
        if isinstance(want, dict) and "頭" in want:
            if not v.startswith(want["頭"]):
                return False
        elif v != str(want):
            return False
    return True


def 行の名(rows, r) -> str:
    head = rows[0]
    for k in ("NO", "項目", "ID", "型の名"):
        if k in head and not 空か(rows[r][head.index(k)]):
            return f"{k}={rows[r][head.index(k)]}"
    return f"{r + 1} 行目"


def 見出しの行(text: str, 見出し: str):
    lines = text.split("\n")
    want = 見出し.lstrip("#").strip()
    for i, l in enumerate(lines):
        if l.startswith("#") and l.lstrip("#").strip() == want:
            return i, lines
    return None, lines


def md_の見出しへ足す(text: str, 見出し: str, 足す: list[str]) -> str:
    """見出しの節の終わりへ行を足す。節に同じ行が在れば足さない（途中で落ちた後のやり直しで二重にしない）。"""
    i, lines = 見出しの行(text, 見出し)
    level = len(lines[i]) - len(lines[i].lstrip("#"))
    j = i + 1
    while j < len(lines) and not (lines[j].startswith("#") and len(lines[j]) - len(lines[j].lstrip("#")) <= level):
        j += 1
    在る = {l.strip() for l in lines[i + 1:j]}
    足す = [l for l in 足す if l.strip() not in 在る]
    k = j
    while k > i + 1 and lines[k - 1].strip() == "":
        k -= 1
    if 足す and k == i + 1:
        足す = [""] + 足す
    return "\n".join(lines[:k] + 足す + lines[k:])


def ファイルたち(o: 物, pattern: str) -> list[str]:
    p = 名の型(pattern)
    return [f for f in o.シート if p.match(f)]


# ---------------------------------------------------------------- 操作（どれも前の形を確かめ、当たっていれば飛ばす）

def 当てる操作(o: 物, op: dict, K: dict, 記: 記録, 版: int, 番: int, 手がかり: dict):
    する = op["する"]
    所 = f"直し {版} の操作 {番}「{する}」"

    if する == "file を置き場へ移す":
        前, 後 = op["前"], op["後"]
        在る前 = any(x == 前 or x.startswith(前) for x in o.置き場) if 前.endswith("/") else 前 in o.置き場
        在る後 = any(x == 後 or x.startswith(後) for x in o.置き場) if 後.endswith("/") else 後 in o.置き場
        if not 在る前:
            return
        if 在る後:
            記.出せない(f"置き場:{前}→{後}", "ぶつかり", 前, f"{前} と {後} の両方が在る", ["中身を照らして 1 つにする（人）"])
            return
        o.置き場 = [後 + x[len(前):] if (x == 前 or (前.endswith("/") and x.startswith(前))) else x for x in o.置き場]
        for d in (o.シート, o.md):
            for k in list(d):
                if k == 前 or (前.endswith("/") and k.startswith(前)):
                    d[後 + k[len(前):]] = d.pop(k)
        o.式 = {((後 + f[len(前):]) if (f == 前 or (前.endswith("/") and f.startswith(前))) else f, t, r, c) for f, t, r, c in o.式}
        記.移した.append((前, 後))
        記.当てた.append((版, 番, する, f"{前}→{後}"))
        return

    if する in ("md の見出しの名を変える", "md の見出しを足す"):
        m = op["md"]
        if m not in o.md:
            return
        if する == "md の見出しの名を変える":
            i, lines = 見出しの行(o.md[m], op["前"])
            j, _ = 見出しの行(o.md[m], op["後"])
            if i is None:
                return
            if j is not None:
                記.出せない(f"md:{m}:見出し:{op['前']}→{op['後']}", "ぶつかり", m, f"見出し「{op['前']}」と「{op['後']}」の両方が在る", ["中身を 1 つの見出しへまとめる（人）"])
                return
            level = lines[i][: len(lines[i]) - len(lines[i].lstrip("#"))]
            lines[i] = f"{level} {op['後'].lstrip('#').strip()}"
            o.md[m] = "\n".join(lines)
        else:
            i, lines = 見出しの行(o.md[m], op["見出し"])
            if i is not None:
                return
            text = o.md[m].rstrip("\n")
            o.md[m] = text + ("\n\n" if text else "") + op["見出し"] + "\n"
        記.当てた.append((版, 番, する, m))
        return

    if する == "値の語を読み替える" and "md" in op:
        for m in sorted(o.md):
            if op["md"] in ("*", m) and op["前"] in o.md[m]:
                o.md[m] = o.md[m].replace(op["前"], op["後"])
                記.当てた.append((版, 番, する, m))
        return

    for f in ファイルたち(o, op["ファイル"]):
        tabs = o.シート[f]
        if する == "人の列へ移す":
            人の列へ移す当てる(o, f, op, 記, 版, 番)
            continue
        if する == "タブを足す":
            t = op["タブ"]
            if t in tabs and tabs[t] and any(not 空か(v) for v in tabs[t][0]):
                continue
            tk = 型のファイル(K, f) or {}
            if t not in tk:
                記.出せない(f"{f}/{t}/型に無いタブを足す", "直しの誤り", f"{f}/{t}", "直しが足すタブが型に無い", ["直しか型を直す（PR）"])
                continue
            tabs[t] = [[c["名"] for c in tk[t]]]
            記.足したタブ.append((f, t))
            記.当てた.append((版, 番, する, f"{f}/{t}"))
            continue

        if する == "タブの名を変える":
            前, 後 = op["前"], op["後"]
            if 前 not in tabs:
                continue
            if 後 in tabs:
                鍵 = f"{f}/タブ:{前}→{後}"
                if o.人の答え.get(鍵) == "前を 90_履歴 へ写して消す":  # 今のタブを正とし、前のタブは消す問いへ（消すのはオーナーの OK の後に殻）
                    記.待つタブ.add((f, 前))
                    記.消す問い.append({"物": f"タブ {前}", "置き場": f, "中身はどこに在るか": f"寄せの写しの中だけ（今のタブ「{後}」が正）", "推奨": "消す",
                                    "消す手順": [{"する": "タブを消す", "ファイル": f, "タブ": 前}]})
                    continue
                記.出せない(鍵, "ぶつかり", f, f"タブ「{前}」と「{後}」の両方が在る",
                          ["中身を照らして 1 つにする（人）", "前を 90_履歴 へ写して消す"], 手がかり.get(f"タブ:{前}→{後}", ""))
                continue
            tabs[後] = tabs.pop(前)
            o.式 = {(ff, 後 if (ff == f and t == 前) else t, r, c) for ff, t, r, c in o.式}
            記.タブの名.append((f, 前, 後))
            記.当てた.append((版, 番, する, f"{f}/{前}→{後}"))
            continue

        t = op["タブ"]
        if t not in tabs:
            continue
        rows = tabs[t]
        if not rows:
            continue
        head = rows[0]
        where = f"{f}/{t}"

        if する == "列を足す":
            名 = op["見出し"]
            i = 列の番号(rows, 名)
            条件 = op.get("条件")
            if i is None:
                for r in rows:
                    r.append("")
                head[-1] = 名
                i = len(head) - 1
                記.当てた.append((版, 番, する, f"{where}/{名}"))
            elif not 条件:
                continue
            値 = op["値"]
            if 値 == "<会社>":
                値 = o.会社
            elif isinstance(値, dict):
                値 = 値.get("既定", "")
            if 空か(値):
                continue
            ci = 列の番号(rows, 条件["列"]) if 条件 else None
            for r in rows[1:]:
                if not 空か(r[i]):
                    continue
                if 条件:
                    if ci is None or not (日 := 日付(r[ci])) or not 日 < 条件["より前"]:
                        continue
                elif not any(not 空か(v) for v in r):
                    continue
                r[i] = 値
                記.数["足した"] += 1
            continue

        if する == "値をそろえる":
            値をそろえる当てる(o, f, t, rows, op, 記, 版, 番, 手がかり)
            continue

        if する == "列の名を変える":
            前, 後 = op["前"], op["後"]
            i, j = 列の番号(rows, 前), 列の番号(rows, 後)
            if i is None:
                continue
            if j is None:
                head[i] = 後
                記.当てた.append((版, 番, する, f"{where}/{前}→{後}"))
                continue
            ぶつかる = []
            for r in range(1, len(rows)):
                a, b = rows[r][i], rows[r][j]
                if 空か(a) or 空か(b) or str(a).strip() == str(b).strip():
                    continue
                鍵 = f"{where}/ぶつかり:{前}→{後}/{行の名(rows, r)}"
                ans = o.人の答え.get(鍵)
                if ans not in ("前を取る", "後を取る"):
                    ぶつかる.append(r)
                    記.出せない(鍵, "ぶつかり", where, f"{行の名(rows, r)}: 「{前}」={a} と「{後}」={b}", ["前を取る", "後を取る"])
            if ぶつかる:
                記.ぶつかる列.add((f, t, 前))
                continue
            for r in range(1, len(rows)):
                a, b = rows[r][i], rows[r][j]
                if 空か(a):
                    continue
                if 空か(b):
                    rows[r][j] = a
                elif str(a).strip() == str(b).strip():
                    記.数["重ねた"] += 1
                else:
                    鍵 = f"{where}/ぶつかり:{前}→{後}/{行の名(rows, r)}"
                    if o.人の答え[鍵] == "前を取る":
                        rows[r][j] = a
                    記.数["捨てた（人の答え）"] += 1
            列を消す(rows, i)
            記.当てた.append((版, 番, する, f"{where}/{前}→{後}"))
            continue

        if する == "列の並びをそろえる":
            tk = (型のファイル(K, f) or {}).get(t)
            if tk is None:
                continue
            want = [c["名"] for c in tk]
            if not set(want) <= set(head):
                continue
            order = [head.index(c) for c in want] + [k for k, c in enumerate(head) if c not in want]
            if order == list(range(len(head))):
                continue
            tabs[t] = [[r[k] for k in order] for r in rows]
            o.式 = {(ff, tt, r, order.index(c)) if (ff == f and tt == t) else (ff, tt, r, c) for ff, tt, r, c in o.式}
            記.当てた.append((版, 番, する, where))
            continue

        if する == "値の語を読み替える":
            i = 列の番号(rows, op["列"])
            if i is None:
                continue
            合わせ = op.get("合わせ", "全体")
            for r in range(1, len(rows)):
                v = str(rows[r][i])
                if (v.startswith(op["前"]) if 合わせ != "全体" else v.strip() == op["前"]):
                    rows[r][i] = op["後"] + (v[len(op["前"]):] if 合わせ == "頭" else "")
                    記.当てた.append((版, 番, する, f"{where}/{op['列']}/{行の名(rows, r)}"))
                    if op.get("問いを起こす"):
                        記.足りない.append({"所": where, "行": 行の名(rows, r), "項目": op["列"],
                                          "なぜ": f"「{op['前']}」は確かめに数えない＝{op['後']}へ直した。1 問で確かめる（確かめと仮.md）"})
            continue

        if する == "列を md の見出しへ移す":
            i = 列の番号(rows, op["列"])
            if i is None:
                continue
            m, 見出し = op["md"], op["見出し"]
            sel = op.get("行")
            targets = [r for r in range(1, len(rows)) if (行が合う(rows[r], head, sel) if sel else not 空か(rows[r][i]))]
            if not targets:
                if not sel:
                    列を消す(rows, i)
                continue
            if m not in o.md or 見出しの行(o.md[m], 見出し)[0] is None:
                記.出せない(f"{where}/md:{m}#{見出し}", "直しの誤り", where, f"移す先の md「{m}」の見出し「{見出し}」が無い", ["md の見出しを型どおりにしてからもう一度"])
                continue
            足す = []
            for r in targets:
                cells = [(head[k], rows[r][k]) for k in range(len(head)) if not 空か(rows[r][k]) and (sel or k != i)]
                if sel:
                    名 = rows[r][head.index("項目")] if "項目" in head else 行の名(rows, r)
                    rest = [f"{h} {v}" for h, v in cells if h not in ("項目", op["列"])]
                    足す.append(f"- {名}: {rows[r][i]}" + (f"（{'・'.join(rest)}）" if rest else ""))
                    記.数["md へ移した"] += len(cells)
                else:
                    足す.append(f"- {行の名(rows, r)}: {op['列']}＝{rows[r][i]}")
                    記.数["md へ移した"] += 1
            o.md[m] = md_の見出しへ足す(o.md[m], 見出し, 足す)
            記.渡すタブ.add((f, t))
            if sel:
                tabs[t] = [rows[0]] + [rows[r] for r in range(1, len(rows)) if r not in targets]
            else:
                列を消す(rows, i)
            記.当てた.append((版, 番, する, f"{where}/{op['列']}→{m}#{見出し}"))
            continue

        if する == "列を畳む":
            i = 列の番号(rows, op["列"])
            if i is None:
                continue
            sel = op.get("行")
            先 = op["先"]
            if 先 == "持たない":
                if sel:
                    targets = [r for r in range(1, len(rows)) if 行が合う(rows[r], head, sel)]
                    if not targets:
                        continue
                    n = sum(1 for r in targets for v in rows[r] if not 空か(v))
                    tabs[t] = [rows[0]] + [rows[r] for r in range(1, len(rows)) if r not in targets]
                else:
                    n = sum(1 for r in rows[1:] if not 空か(r[i]))
                    列を消す(rows, i)
                記.数["捨てた（直しの持たない）"] += n
                if n:
                    記.持たない.append((f"{where}/{op['列']}" + (f"（行 {sel}）" if sel else ""), n, op.get("なぜ", "")))
                記.当てた.append((版, 番, する, f"{where}/{op['列']}"))
                continue
            # 鍵で行を合わせて先へ移す
            tf = 先.get("ファイル", f)
            dst = o.シート.get(tf, {}).get(先["タブ"])
            if not dst:
                記.出せない(f"{where}/{op['列']}/先が無い", "直しの誤り", where, f"畳む先「{tf}/{先['タブ']}」が無い", ["直しの並びを直す（PR）"])
                continue
            dh = dst[0]
            足す行 = 先.get("足す行", {})
            need = list(先["鍵"]) + list(足す行) + [先["列"]]
            if any(c not in dh for c in need) or any(c not in head for c in 先["鍵"]):
                記.出せない(f"{where}/{op['列']}/先の列が無い", "直しの誤り", where, f"畳む先か元に鍵の列が無い {need}", ["直しの並びを直す（PR）"])
                continue
            plan, ぶつかる = [], False
            for r in range(1, len(rows)):
                v = rows[r][i]
                if 空か(v):
                    continue
                key = {c: rows[r][head.index(c)] for c in 先["鍵"]}
                want = {**key, **足す行}
                hit = next((x for x in range(1, len(dst)) if all(str(dst[x][dh.index(c)]).strip() == str(w).strip() for c, w in want.items())), None)
                if hit is not None:
                    b = dst[hit][dh.index(先["列"])]
                    if 空か(b):
                        plan.append(("書く", hit, v))
                    elif str(b).strip() == str(v).strip():
                        plan.append(("重ねる", hit, v))
                    else:
                        鍵 = f"{where}/ぶつかり:{op['列']}→{先['タブ']}.{先['列']}/{行の名(rows, r)}"
                        ans = o.人の答え.get(鍵)
                        if ans == "前を取る":
                            plan.append(("上書き", hit, v))
                        elif ans == "後を取る":
                            plan.append(("捨てる", hit, v))
                        else:
                            ぶつかる = True
                            記.出せない(鍵, "ぶつかり", where, f"{行の名(rows, r)}: 「{op['列']}」={v} と {先['タブ']}「{先['列']}」={b}", ["前を取る", "後を取る"])
                else:
                    plan.append(("行を足す", want, v))
            if ぶつかる:
                記.ぶつかる列.add((f, t, op["列"]))
                continue
            for kind, x, v in plan:
                if kind in ("書く", "上書き"):
                    dst[x][dh.index(先["列"])] = v
                    if kind == "上書き":
                        記.数["捨てた（人の答え）"] += 1
                elif kind == "重ねる":
                    記.数["重ねた"] += 1
                elif kind == "捨てる":
                    記.数["捨てた（人の答え）"] += 1
                else:
                    new = [""] * len(dh)
                    for c, w in x.items():
                        new[dh.index(c)] = w
                    new[dh.index(先["列"])] = v
                    dst.append(new)
                    記.数["足した"] += sum(1 for w in x.values() if not 空か(w))
            列を消す(rows, i)
            if (tf, 先["タブ"]) != (f, t):
                記.渡すタブ.add((f, t))
            記.当てた.append((版, 番, する, f"{where}/{op['列']}→{tf}/{先['タブ']}.{先['列']}"))
            continue


# ---------------------------------------------------------------- 値をそろえる（形の一覧。どれも今の形の値は飛ばす＝何度当てても同じ）

支給月の形 = "{:04d}.{:02d}支給"  # 型.json の 適用開始「効き始める支給月（YYYY.MM支給）」・段の解決の 月() が読む形
都道府県たち = ("北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県",
            "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県",
            "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県",
            "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県")


def 支給月へ(v: str):
    """2026/4・2026年4月・2026-04-01・2026.4・令和8年4月・R8.4 → YYYY.MM支給（読めなければ None）。"""
    s = re.sub(r"\s", "", str(v)).translate(str.maketrans("０１２３４５６７８９／．－", "0123456789/.-"))
    s = re.sub(r"(支給|分|支給分)$", "", s)
    m = re.fullmatch(r"(\d{4})(?:[-/.年])(\d{1,2})(?:月)?(?:[-/.](\d{1,2})日?|(\d{1,2})日)?", s)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
    else:
        m = re.fullmatch(r"(?:令和|R|r)(\d{1,2}|元)[年.\-/](\d{1,2})月?(?:[-/.]?\d{1,2}日?)?", s)
        if not m:
            return None
        y, mo = 2018 + (1 if m.group(1) == "元" else int(m.group(1))), int(m.group(2))
    return 支給月の形.format(y, mo) if 1 <= mo <= 12 else None


def 都道府県へ(v: str):
    """協会けんぽの支部の語（東京・東京支部・全国健康保険協会 東京支部・東京都）→ 法の表の 都道府県 の名（芯が引く鍵）。"""
    s = re.sub(r"\s", "", str(v))
    s = re.sub(r"^(全国健康保険協会|協会けんぽ|協会)", "", s)
    s = re.sub(r"支部$", "", s)
    if s in 都道府県たち:
        return s
    hit = [p for p in 都道府県たち if p == s + ("都" if p.endswith("都") else "府" if p.endswith("府") else "県") or (p == "北海道" and s == "北海道")]
    return hit[0] if len(hit) == 1 else None


def _時間の字(x):
    """6・6.5・"6"・"6:00"・"6時間"・"6時間30分" → "6:00" の形（読めなければ None）。"""
    s = re.sub(r"\s", "", str(x))
    s = re.sub(r"(超|を超える|より長い)$", "", s)
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
    if m and int(m.group(2)) < 60:
        return f"{int(m.group(1))}:{m.group(2)}"
    m = re.fullmatch(r"(\d{1,2})時間(?:(\d{1,2})分)?", s)
    if m:
        return f"{int(m.group(1))}:{int(m.group(2) or 0):02d}"
    try:
        f = float(s)
    except ValueError:
        return None
    mins = round(f * 60)
    return f"{mins // 60}:{mins % 60:02d}" if f >= 0 and abs(f * 60 - mins) < 1e-9 else None


def _分の数(x):
    s = re.sub(r"\s", "", str(x))
    m = re.fullmatch(r"(\d+)(?:分)?", s)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


_休憩の窓 = r"\d{1,2}:\d{2}\s*[〜~～\-－]\s*\d{1,2}:\d{2}"
_休憩の長さ = r"\d{1,2}:\d{2}超\d+分"


def 休憩の長さへ(v: str):
    """前の JSON の休憩の表（何時間を超えたら何分）→ 今の型の長さの形 `6:00超45分、8:00超60分`。
    今の形（時間帯の形・長さの形）はそのまま返す。読めなければ None。"""
    s = str(v).strip()
    片 = [x.strip() for x in re.split(r"[、,，]", s) if x.strip()]
    if 片 and (all(re.fullmatch(_休憩の窓, x) for x in 片) or all(re.fullmatch(_休憩の長さ, x) for x in 片)):
        return s
    try:
        d = json.loads(s)
    except ValueError:
        return None
    if isinstance(d, dict) and len(d) == 1 and isinstance(next(iter(d.values())), (list, dict)):
        d = next(iter(d.values()))  # {"休憩": [...]} の包み
    組 = []
    if isinstance(d, dict):
        組 = list(d.items())
    elif isinstance(d, list):
        for x in d:
            if isinstance(x, (list, tuple)) and len(x) == 2:
                組.append(tuple(x))
            elif isinstance(x, dict):
                h = next((x[k] for k in x if any(w in str(k) for w in ("超", "時間", "長さ", "hour", "over", "以上"))), None)
                m = next((x[k] for k in x if any(w in str(k) for w in ("分", "休憩", "min", "break"))), None)
                組.append((h, m))
            else:
                return None
    else:
        return None
    out = []
    for h, m in 組:
        hh, mm = _時間の字(h) if h is not None else None, _分の数(m) if m is not None else None
        if hh is None or mm is None:
            return None
        out.append((tuple(map(int, hh.split(":"))), f"{hh}超{mm}分"))
    if not out or len({k for k, _ in out}) != len(out):
        return None
    return "、".join(x for _, x in sorted(out))


def _時間の値か(v: str) -> bool:
    """欄の名でなく時間の値に見える（h:mm・時間の数）。"""
    return bool(re.fullmatch(r"\d+(?::\d{2})?(?:\.\d+)?(?:時間)?", re.sub(r"\s", "", str(v))))


def そろえる値(op: dict, v: str):
    """(今の値 or None＝読めない, 今の形か)。"""
    形 = op["形"]
    if 形 == "支給月":
        w = 支給月へ(v)
        return w, w == v.strip()
    if 形 == "都道府県":
        w = 都道府県へ(v)
        return w, w == v.strip()
    if 形 == "休憩の長さ":
        w = 休憩の長さへ(v)
        return w, w == v.strip()
    if 形 == "欄の名":
        return (None, False) if _時間の値か(v) else (v, True)
    読み = op.get("読み", {})
    今たち = set(読み.values())
    s = v.strip()
    if s in 今たち:
        return s, True
    if s in 読み:
        return 読み[s], False
    if op.get("先の列"):  # 長い文の中の語で読む（1 つの今の語だけに当たる時）
        hit = {w for k, w in 読み.items() if k and k in s}
        if len(hit) == 1:
            return hit.pop(), False
    return None, False


def 時間の値を項目へ(rows: list, r: int, i: int, op: dict, where: str, 鍵: str, v: str, 名: str, 記: 記録, 版: int, 番: int) -> bool:
    """形＝欄の名 の行に時間の値（`160:00`・`160`）が入っていれば、それは欄の名でなく会社の段の定数＝行の 項目 を
    `時間の値の項目`（例 委託.雇用分の出勤時間）へ変える（値・適用開始はそのまま）。同じ会社にその項目の値の在る行が既に在れば問い。
    変えたか問いにしたら True（呼ぶ側は次の行へ）。"""
    行き = op["時間の値の項目"]
    k, c = 列の番号(rows, "項目"), 列の番号(rows, "会社")
    if k is None:
        return False
    既 = [x for x in range(1, len(rows)) if x != r and str(rows[x][k]).strip() == 行き and not 空か(rows[x][i])
         and (c is None or str(rows[x][c]).strip() == str(rows[r][c]).strip())]
    if 既:
        記.解けた(鍵)  # 前の直しの問い（形の合わない値）を、この直しの問い（ぶつかり）に置き換える
        記.出せない(鍵, "ぶつかり", where,
                  f"{名}「{op['列']}」= {v} は時間の値（会社の定数）で、{行き} の行が既に在る（{rows[既[0]][i]}）",
                  ["値:<欄の名>", "空にする"], op.get("なぜ", ""))
        return True
    rows[r][k] = 行き
    記.解けた(鍵)
    記.当てた.append((版, 番, "値をそろえる", f"{where}/項目/{名}→{行き}"))
    return True


def 値をそろえる当てる(o: 物, f: str, t: str, rows: list, op: dict, 記: 記録, 版: int, 番: int, 手がかり: dict,
                  だけ: set | None = None):
    """`だけ`（行の id の集まり）を渡せば、その行だけに当てる（答えで項目を今の名にした行へ、後から読み替えを通す）。"""
    head = rows[0]
    where = f"{f}/{t}"
    i = 列の番号(rows, op["列"])
    if i is None:
        return
    j = 列の番号(rows, op["先の列"]) if op.get("先の列") else None
    if op.get("先の列") and j is None:
        記.出せない(f"{where}/{op['先の列']}/先の列が無い", "直しの誤り", where, f"先の列「{op['先の列']}」が無い", ["直しの並びを直す（PR）"])
        return
    sel = op.get("行")
    for r in range(1, len(rows)):
        if sel and not 行が合う(rows[r], head, sel):
            continue
        if だけ is not None and id(rows[r]) not in だけ:
            continue
        v = str(rows[r][i])
        if 空か(v):
            continue
        名 = 行の名(rows, r)
        鍵 = f"{where}/そろえる:{op['列']}" + (f"→{op['先の列']}" if j is not None else "") + f"/{名}"
        w, 今の形 = そろえる値(op, v)
        ans = o.人の答え.get(鍵, "")
        if w is None and ans.startswith("値:"):
            w = ans[2:]
        if w is None and op.get("時間の値の項目") and ans != "空にする":
            if 時間の値を項目へ(rows, r, i, op, where, 鍵, v, 名, 記, 版, 番):
                continue
        if j is not None:  # 読んだ値を先の列へ（元の列は残す）
            if w is None:
                if ans == "そのまま":
                    if 空か(rows[r][j]):
                        記.足りない.append({"所": where, "行": 名, "項目": op["先の列"], "なぜ": f"「{op['列']}」の「{v}」から読めない＝人がそのままにした"})
                    continue
                if not 空か(rows[r][j]):  # 先の列が埋まっていれば読まない（人が書いた値が勝つ）
                    continue
                記.出せない(鍵, "形の合わない値", where, f"{名}「{op['列']}」= {v}（{op['先の列']} へ読めない）",
                          [f"値:<{op['先の列']}>", "そのまま"], 手がかり.get(f"{t}/{op['列']}", op.get("なぜ", "")))
                continue
            b = str(rows[r][j]).strip()
            if 空か(b):
                rows[r][j] = w
                記.数["足した"] += 1
                記.当てた.append((版, 番, "値をそろえる", f"{where}/{op['先の列']}/{名}"))
            elif b != w and not ans.startswith("値:"):
                記.出せない(鍵, "ぶつかり", where, f"{名}「{op['列']}」から読んだ {w} と「{op['先の列']}」= {b}",
                          [f"値:{b}", f"値:{w}"], op.get("なぜ", ""))
            elif b != w:
                rows[r][j] = w
            continue
        if w is not None:
            記.解けた(鍵)  # 前の直し（例 直し 4）が問いにした値を後の直し（直し 5）の読みが解く
            if not 今の形:
                rows[r][i] = w
                記.当てた.append((版, 番, "値をそろえる", f"{where}/{op['列']}/{名}"))
            continue
        if ans == "空にする":
            rows[r][i] = ""
            記.数["捨てた（人の答え）"] += 1
            記.足りない.append({"所": where, "行": 名, "項目": op["列"], "なぜ": f"読めない「{v}」を人が空にした"})
            continue
        記.解けた(鍵)  # 同じ値を後の直しも読めない＝後の直しの手がかり・なぜで問う
        記.出せない(鍵, "形の合わない値", where, f"{名}「{op['列']}」= {v}（{op['形']} の形へ読めない）",
                  ["値:<直した値>", "空にする"], 手がかり.get(f"{t}/{op['列']}", op.get("なぜ", "")))


def 人の列へ移す当てる(o: 物, f: str, op: dict, 記: 記録, 版: int, 番: int):
    """会社の行の前の語（例 給与の形＝委託）を、同じ会社の社員の 先の列（例 人.区分）へ移す。
    人の値（先の列か 人の値の列）の在る人は人が勝つ（段の決まり: 人＞会社）。移る人が 0 なら問いに残す。
    列の行き: 社員の前の語の列（例 支払.賃金の形＝委託）も 先の列 へ移す（元の値は消す・先に違う値があれば問い）。"""
    tabs = o.シート[f]
    社員 = tabs.get("社員")
    if not 社員:
        return
    sh = 社員[0]
    if op["先の列"] not in sh:
        return
    pi = sh.index(op["先の列"])
    hi = sh.index(op["人の値の列"]) if op.get("人の値の列") in sh else None
    読み = op["値"]
    行き = op.get("列の行き")
    if 行き and 行き["列"] in sh:
        ci = sh.index(行き["列"])
        for r in range(1, len(社員)):
            v = str(社員[r][ci]).strip()
            if v not in 読み:
                continue
            w, b = 読み[v], str(社員[r][pi]).strip()
            鍵 = f"{f}/社員/区分:{行き['列']}→{op['先の列']}/{行の名(社員, r)}"
            if 空か(b) or b == w or o.人の答え.get(鍵) == "前を取る":
                社員[r][pi] = w
                社員[r][ci] = ""
                記.当てた.append((版, 番, "人の列へ移す", f"{f}/社員/{行の名(社員, r)}"))
            elif o.人の答え.get(鍵) == "後を取る":
                社員[r][ci] = ""
                記.数["捨てた（人の答え）"] += 1
            else:
                記.出せない(鍵, "ぶつかり", f"{f}/社員", f"{行の名(社員, r)}: 「{行き['列']}」={v}（{op['先の列']}＝{w} の意味）と「{op['先の列']}」={b}", ["前を取る", "後を取る"])
    会社 = tabs.get("会社")
    if not 会社:
        return
    ch = 会社[0]
    vc = next((c for c in ("今の値", "値") if c in ch), None)
    if vc is None:
        return
    外す = []
    for r in range(1, len(会社)):
        if not 行が合う(会社[r], ch, op["行"]):
            continue
        v = str(会社[r][ch.index(vc)]).strip()
        if v not in 読み:
            continue  # 読めない語は照らすが「形の合わない値」の問いに残す
        w = 読み[v]
        c = str(会社[r][ch.index("会社")]).strip() if "会社" in ch else ""
        人たち = [x for x in 社員[1:] if any(not 空か(y) for y in x) and (not c or "会社" not in sh or str(x[sh.index("会社")]).strip() in ("", c))]
        書く = [x for x in 人たち if 空か(x[pi]) and (hi is None or 空か(x[hi]))]
        if not 書く and not any(str(x[pi]).strip() == w for x in 人たち):
            鍵 = f"{f}/会社/形:項目/{行の名(会社, r)}"
            if not o.人の答え.get(鍵):
                記.知らせ.append(f"{f}/会社/{行の名(会社, r)}: 「{v}」を {op['先の列']}＝{w} へ移す人が居ない（人の値が在る）＝問いに残す")
            continue
        for x in 書く:
            x[pi] = w
            記.数["足した"] += 1
        記.数["他の所へ移した"] += sum(1 for y in 会社[r] if not 空か(y))
        外す.append(r)
        記.渡すタブ.add((f, "会社"))
        記.当てた.append((版, 番, "人の列へ移す", f"{f}/会社/{行の名(会社, r)}"))
    if 外す:
        tabs["会社"] = [ch] + [会社[r] for r in range(1, len(会社)) if r not in 外す]


# ---------------------------------------------------------------- 照らす（今の型と同じ形か）

def 答えの行へ読み替えを通す(o: 物, f: str, t: str, rows: list, 記: 記録, 直したち: list[dict], 手がかり: dict):
    """人の答え（値:<項目>）で項目を今の名にした行へ、当てた直しの「値をそろえる」（行を項目で選ぶ物）を版の順にもう一度通す。
    当てる順は 版の直し → 照らす（人の答え）なので、答えで今の名になった行には直しの読み替えがまだ当たっていない。
    答えは項目の名（意味）を決めるだけ＝値の語は直しの読み替えで今の語へそろえる。読み替えに無い語は問い（黙って通さない）。"""
    だけ = 記.答えで項目を変えた.get((f, t))
    if not だけ or not rows:
        return
    前の値 = {id(r): list(r) for r in rows[1:] if id(r) in だけ}
    for d in 直したち:
        for n, op in enumerate(d["操作"], 1):
            if op["する"] != "値をそろえる" or not op.get("行") or op["タブ"] != t or not 名の型(op["ファイル"]).match(f):
                continue
            値をそろえる当てる(o, f, t, rows, op, 記, d["版"], n, 手がかり, だけ)
    for r in range(1, len(rows)):
        a = 前の値.get(id(rows[r]))
        if a is not None and a != rows[r]:
            記.知らせ.append(f"{f}/{t}/{行の名(rows, r)}: 人の答えで今の項目にした行の値を、直しの読み替えで今の語へ"
                           f"（{'・'.join(f'{x}→{y}' for x, y in zip(a, rows[r]) if x != y)}）")


def 照らす(o: 物, K: dict, 記: 記録, 手がかり: dict, 前の物: 物, 直したち: list[dict] = ()):
    for f in sorted(o.シート):
        tk = 型のファイル(K, f)
        if tk is None:
            記.知らせ.append(f"{f}: 型に無いシート（寄せの外。置き場の検査で見る）")
            continue
        tabs = o.シート[f]
        for t in list(tabs):
            rows = tabs[t]
            where = f"{f}/{t}"
            if t.startswith(旧の頭) or (f, t) in 記.待つタブ:
                continue
            if t not in tk:
                n = sum(1 for r in rows[1:] for v in r if not 空か(v))
                if n == 0:
                    記.消す問い.append({"物": f"タブ {t}", "置き場": f, "中身はどこに在るか": "空（値が無い）", "推奨": "消す",
                                    "消す手順": [{"する": "タブを消す", "ファイル": f, "タブ": t}]})
                    continue
                鍵 = f"{where}/行き先の無いタブ"
                ans = o.人の答え.get(鍵)
                if ans == "90_履歴 へ写して消す":  # その場で消さない（消す問いへ・オーナーの OK の後に殻が消す）
                    記.消す問い.append({"物": f"タブ {t}", "置き場": f, "中身はどこに在るか": "寄せの写しの中だけ（90_履歴/消す_<日>_<名>）", "推奨": "消す",
                                    "消す手順": [{"する": "タブを消す", "ファイル": f, "タブ": t}]})
                    continue
                記.出せない(鍵, "行き先の無いタブ", where, f"型にも直しにも無いタブ（値 {n} 個）",
                          ["型へ足す（B3 へ直しを頼む）", "90_履歴 へ写して消す"], 手がかり.get(t, ""))
                continue
            want = [c["名"] for c in tk[t]]
            head = rows[0] if rows else []
            待つ, 未解決 = set(), set()
            for k in reversed(range(len(head))):
                c = head[k]
                if c in want:
                    continue
                if (f, t, c) in 記.ぶつかる列:
                    未解決.add(c)
                    continue
                n = sum(1 for r in rows[1:] if not 空か(r[k]))
                if n == 0:  # 見出しだけの列も人の手の物かもしれない＝外さず消す問いへ
                    待つ.add(c)
                    記.消す問い.append({"物": f"列 {c}", "置き場": where, "中身はどこに在るか": "空（見出しだけ）", "推奨": "消す",
                                    "消す手順": [{"する": "列を消す", "ファイル": f, "タブ": t, "見出し": c}]})
                    continue
                鍵 = f"{where}/行き先の無い列:{c}"
                ans = o.人の答え.get(鍵, "")
                if ans == "90_履歴 へ写して消す":  # 列は型の列の後ろに残し、消す問いへ（消すのはオーナーの OK の後に殻）
                    待つ.add(c)
                    記.消す問い.append({"物": f"列 {c}", "置き場": where, "中身はどこに在るか": "寄せの写しの中だけ（90_履歴/消す_<日>_<名>）", "推奨": "消す",
                                    "消す手順": [{"する": "列を消す", "ファイル": f, "タブ": t, "見出し": c}]})
                    continue
                if ans.startswith(今の列へ移す):
                    残る = 今の列へ移す当てる(rows, k, ans, want, 記)
                    if not 残る:
                        continue
                    未解決.add(c)
                    記.出せない(鍵, "行き先の無い列", where, f"型にも直しにも無い列「{c}」（値 {n} 個）。今の列へ移せない: {'・'.join(残る)}",
                              ["型へ足す（B3 へ直しを頼む）", "今の列へ移す:<今の列>|<前の値>=<今の値>|…", "md へ移す:<md の名>#<見出し>", "90_履歴 へ写して消す"],
                              手がかり.get(f"{t}/{c}", 手がかり.get(c, "")))
                    continue
                if ans.startswith("md へ移す:") and "#" in ans:
                    m, 見出し = ans[len("md へ移す:"):].split("#", 1)
                    sub = 記録()
                    当てる操作(o, {"する": "列を md の見出しへ移す", "ファイル": f, "タブ": t, "列": c, "md": m, "見出し": 見出し}, K, sub, 0, 0, {})
                    if not sub.寄せられない:
                        記.数["md へ移した"] += sub.数["md へ移した"]
                        記.渡すタブ.add((f, t))
                        continue
                未解決.add(c)
                記.出せない(鍵, "行き先の無い列", where, f"型にも直しにも無い列「{c}」（値 {n} 個）",
                          ["型へ足す（B3 へ直しを頼む）", "今の列へ移す:<今の列>|<前の値>=<今の値>|…", "md へ移す:<md の名>#<見出し>", "90_履歴 へ写して消す"],
                          手がかり.get(f"{t}/{c}", 手がかり.get(c, "")))
            無い = [c for c in want if c not in rows[0]] if rows else want
            if 無い:
                記.出せない(f"{where}/型の列が無い", "直しの誤り", where, f"型に在るが直しが足さない列 {無い}", ["直しを直す（PR）"])
                continue
            if rows[0][: len(want)] != want or set(rows[0][len(want):]) - 待つ - 未解決:
                記.出せない(f"{where}/並び", "直しの誤り", where, "列の並びが型と違う（直しに「列の並びをそろえる」が無い）", ["直しを直す（PR）"])
                continue
            if "項目" in want:  # 項目を人が空にした行・項目の空な行は行ごと外す（名の無い値を残さない）
                rows = tabs[t] = 項目の空な行を外す(o, f, t, rows, want.index("項目"), tk[t][want.index("項目")], 記)
            if "項目" in want:  # 項目の語の合わない行を、人の答えで行ごと今の所へ移す（月の変動・月の前提の語・社員の列・持たない）
                rows = tabs[t] = 行の答えを当てる(o, f, t, rows, want.index("項目"), tk[t][want.index("項目")], 記)
            for k, spec in enumerate(tk[t]):
                for r in range(1, len(rows)):  # 型の列だけを照らす（待つ列は後ろ）
                    v = rows[r][k]
                    if 空か(v):
                        if spec.get("必須") and any(not 空か(x) for x in rows[r]):
                            記.足りない.append({"所": where, "行": 行の名(rows, r), "項目": spec["名"], "なぜ": "型が要る値が空"})
                        continue
                    ok = True
                    if spec.get("選べる値") and str(v).strip() not in spec["選べる値"]:
                        ok = False
                    if spec.get("形") and not re.fullmatch(spec["形"], str(v).strip()):
                        ok = False
                    if ok:
                        continue
                    鍵 = f"{where}/形:{spec['名']}/{行の名(rows, r)}"
                    ans = o.人の答え.get(鍵, "")
                    if ans == "空にする":
                        rows[r][k] = ""
                        記.数["捨てた（人の答え）"] += 1
                        記.足りない.append({"所": where, "行": 行の名(rows, r), "項目": spec["名"], "なぜ": "形の合わない値を人が空にした"})
                        continue
                    if ans.startswith("値:"):
                        rows[r][k] = ans[2:]
                        if spec["名"] == "項目":
                            記.答えで項目を変えた.setdefault((f, t), set()).add(id(rows[r]))
                        continue
                    記.出せない(鍵, "形の合わない値", where, f"{行の名(rows, r)}「{spec['名']}」= {v}",
                              ["値:<直した値>", "空にする"] + (行の答えの形.get(t, []) if spec["名"] == "項目" else []),
                              手がかり.get(f"{t}/{v}", ""))
            答えの行へ読み替えを通す(o, f, t, rows, 記, 直したち, 手がかり)
        for t in tk:
            if t not in tabs:
                記.出せない(f"{f}/{t}/型のタブが無い", "直しの誤り", f, f"型に在るタブ「{t}」が無い（直しが足していない）", ["直しを直す（PR）"])
    # 一点物（式）: 変わるタブに式があれば、人が「値へ置く」と答えるまで書かない
    for f, t, r, c in sorted(o.式):
        前 = 前の物.シート.get(f, {}).get(t)
        if o.シート.get(f, {}).get(t) == 前:
            continue
        鍵 = f"{f}/{t}/式"
        if o.人の答え.get(鍵) == "値へ置く":
            continue
        記.出せない(鍵, "一点物", f"{f}/{t}", "式のセルが在るタブを書き換える（書くと式が値になる）", ["値へ置く", "型へ足す（B3 へ直しを頼む）"])
    for m, heads in K["md"].items():
        if m not in o.md:
            continue
        無い = [h for h in heads if 見出しの行(o.md[m], h)[0] is None]
        型の = {h.lstrip("#").strip() for h in heads}
        余り = [l for l in o.md[m].splitlines() if l.startswith("## ") and l.lstrip("#").strip() not in 型の]
        if heads and 余り:
            記.知らせ.append(f"{m}: 型の雛形に無い見出し {余り}（中身を型の見出しの下へまとめる＝人。道具は消さない）")
        if 無い:
            記.出せない(f"md:{m}/見出し", "直しの誤り", m, f"型の見出しが無い {無い}", ["直しを直す（PR）"])


def 項目の空な行を外す(o: 物, f: str, t: str, rows: list, ki: int, spec: dict, 記: 記録) -> list:
    """縦のタブ（項目の行）で、項目に人が「空にする」と答えた行と、項目が空で値だけ在る行を、行ごと外す。
    項目の名の無い値は段の解決が読めない＝残さない。外した値は黙って捨てず、寄せの写し（90_履歴/消す_<日>_<名>）に在ると
    「型が持たないと決めた値」に件数を出す。項目が空の行は人が 値:<項目> か 行ごと外す と答えるまで問いに残す。"""
    where = f"{f}/{t}"
    外す = []
    for r in range(1, len(rows)):
        v = str(rows[r][ki]).strip()
        名 = 行の名(rows, r)
        値たち = [x for k, x in enumerate(rows[r]) if k != ki and rows[0][k] != "会社" and not 空か(x)]
        if 空か(v):
            if not 値たち:
                continue
            鍵 = f"{where}/項目が空/{名}"
            ans = o.人の答え.get(鍵, "")
            if ans.startswith("値:") and ans[2:].strip():
                rows[r][ki] = ans[2:].strip()
                記.数["足した"] += 1
                記.答えで項目を変えた.setdefault((f, t), set()).add(id(rows[r]))
                continue
            if ans != "行ごと外す":
                記.出せない(鍵, "形の合わない値", where, f"{名}: 項目が空で値だけ在る（{'・'.join(map(str, 値たち))}）",
                          ["値:<項目>", "行ごと外す"], "項目の名の無い値は段の解決が読めない")
                continue
        else:
            ok = (not spec.get("選べる値") or v in spec["選べる値"]) and (not spec.get("形") or re.fullmatch(spec["形"], v))
            if ok or o.人の答え.get(f"{where}/形:{spec['名']}/{名}") != "空にする":
                continue
        n = sum(1 for x in rows[r] if not 空か(x))
        外す.append(r)
        記.数["捨てた（人の答え）"] += n
        記.持たない.append((f"{where}/{名}", n, "人が項目を空にした＝行ごと外した（前の値は寄せの写し 90_履歴/消す_<日>_<名> に在る）"))
    if not 外す:
        return rows
    return [rows[0]] + [rows[r] for r in range(1, len(rows)) if r not in 外す]


今の列へ移す = "今の列へ移す:"


def 読み替えを読む(片: list[str]) -> dict | None:
    """`前=後` の並びを {前: 後} に（`=` の無い片が在れば None）。"""
    out = {}
    for x in 片:
        if "=" not in x:
            return None
        a, b = x.split("=", 1)
        out[a.strip()] = b.strip()
    return out


def 今の列へ移す当てる(rows: list, k: int, ans: str, want: list[str], 記: 記録) -> list[str]:
    """行き先の無い列 k の値を、同じタブの今の型の列へ値ごと移す（人の答え `今の列へ移す:<列>|<前>=<後>|…`）。
    読み替えが在れば、読み替えに無い値は移さない（黙って捨てない）。`<前>=`（後が空）は人が捨てると決めた値。
    今の列に違う値が在る行も移さない。移せない値が 1 つでも在れば何もせず、移せない物を返す（問いに残す）。
    全部移せれば列を外して空の並びを返す（2 回目は列が無い＝何もしない）。"""
    head = rows[0]
    片 = ans[len(今の列へ移す):].split("|")
    先 = 片[0].strip()
    読み = 読み替えを読む(片[1:]) if len(片) > 1 else {}
    if 読み is None:
        return [f"読み替えの形が違う（`前=後` を | で並べる）: {ans}"]
    if 先 not in want or 先 not in head or 先 == head[k]:
        return [f"「{先}」はこのタブの今の型の列でない"]
    j = head.index(先)
    plan, 残る = [], []
    for r in range(1, len(rows)):
        v = str(rows[r][k]).strip()
        if 空か(v):
            continue
        if 読み and v not in 読み:
            残る.append(f"{行の名(rows, r)} の「{v}」（読み替えに無い）")
            continue
        w = 読み.get(v, v) if 読み else v
        b = str(rows[r][j]).strip()
        if 空か(w):
            plan.append((r, "捨てる", w))
        elif 空か(b):
            plan.append((r, "書く", w))
        elif b == w:
            plan.append((r, "重ねる", w))
        else:
            残る.append(f"{行の名(rows, r)} の「{v}」→「{w}」（今の列に {b} が在る）")
    if 残る:
        return 残る
    for r, kind, w in plan:
        if kind == "書く":
            rows[r][j] = w
        elif kind == "重ねる":
            記.数["重ねた"] += 1
        else:
            記.数["捨てた（人の答え）"] += 1
    列を消す(rows, k)
    return []


# 項目の語が合わない行（台帳「月の前提」・マスタ「会社」）へ人が選べる、行ごと今の所へ移す答え
行の答えの形 = {
    "月の前提": ["月の前提の語へ:<語>=<値>|…", "月の変動へ:<項目>|<NO>=<値>|<NO>|…", "入口が読み直す", "持たない:<なぜ>"],
    "会社": ["人の列へ:<列>=<値>|<NO>|…", "持たない:<なぜ>"],
}


def 行の答えを当てる(o: 物, f: str, t: str, rows: list, ki: int, spec: dict, 記: 記録) -> list:
    """項目の語が型に合わない行を、人の答えで行ごと移す（移した行は外す）。答えの形が違う・ぶつかる時は何もせず
    知らせに出し、行は残す（照らすが「形の合わない値」の問いに残す）。値は数を合わせる（値の保ち）:
    外した行の値は 他の所へ移した、足した行・セルの値は 足した、持たない・入口が読み直す は 捨てた（人の答え）。"""
    head = rows[0]
    where = f"{f}/{t}"
    形 = 行の答えの形.get(t, [])
    if not 形:
        return rows
    頭たち = {x.split(":")[0] for x in 形}
    外す = set()
    名の数 = {}
    for r in range(1, len(rows)):
        名の数[行の名(rows, r)] = 名の数.get(行の名(rows, r), 0) + 1

    def 値の列():
        return next((c for c in ("今月の値", "今の値", "値") if c in head), None)

    for r in range(1, len(rows)):
        v = str(rows[r][ki]).strip()
        if 空か(v):
            continue
        ok = (not spec.get("選べる値") or v in spec["選べる値"]) and (not spec.get("形") or re.fullmatch(spec["形"], v))
        if ok:
            continue
        名 = 行の名(rows, r)
        ans = o.人の答え.get(f"{where}/形:{spec['名']}/{名}", "")
        頭, _, 体 = ans.partition(":")
        if 頭 not in 頭たち:
            continue
        m_old = sum(1 for x in rows[r] if not 空か(x))
        行 = dict(zip(head, rows[r]))
        vc = 値の列()
        前の値 = str(行.get(vc, "")).strip() if vc else ""

        def だめ(なぜ):
            記.知らせ.append(f"{where}/{名}: 答え「{ans}」を当てられない（{なぜ}）＝問いに残す")

        if 頭 == "持たない" or 頭 == "入口が読み直す":
            if 頭 == "持たない" and not 体.strip():
                だめ("持たない:<なぜ> の なぜ が空")
                continue
            外す.add(r)
            記.数["捨てた（人の答え）"] += m_old
            if 頭 == "持たない":
                記.持たない.append((f"{where}/{名}", m_old, f"人の答え: {体.strip()}"))
            else:
                記.足りない.append({"所": where, "行": 名, "項目": v,
                                  "なぜ": "入口が原本から勤怠の日の行へ読み直す（前の値は寄せの写しに在る）"})
            continue
        片 = [x for x in 体.split("|")]
        if 頭 == "月の前提の語へ":
            読み = 読み替えを読む(片)
            if not 読み or any(w not in spec.get("選べる値", []) for w in 読み):
                だめ("語は 月の前提 の語だけ・`語=値` を | で並べる")
                continue
            if 名の数[名] > 1 and any(x for x in 読み.values()):
                だめ(f"同じ「{名}」の行が {名の数[名]} 行在る（支給月ごとに分けて答える）")
                continue
            足す = []
            for w, x in 読み.items():
                new = list(rows[r])
                new[ki] = w
                if vc:
                    new[head.index(vc)] = x if x else 前の値
                足す.append(new)
            ぶつかる = [n for n in 足す if any(rr[ki] == n[ki] and rr != n and all(rr[i] == n[i] for i, c in enumerate(head) if c in ("会社", "支給月"))
                                              for rr in rows[1:])]
            if ぶつかる:
                だめ("同じ支給月に同じ語の行が在る")
                continue
            足す = [n for n in 足す if n not in rows[1:]]  # 同じ行が既に在れば足さない（重ねる）
            外す.add(r)
            rows.extend(足す)
            記.数["他の所へ移した"] += m_old
            記.数["足した"] += sum(1 for n in 足す for x in n if not 空か(x))
            continue
        if 頭 == "月の変動へ":
            dst = o.シート.get(f, {}).get("月の変動")
            項目 = 片[0].strip() if 片 else ""
            人たち = [x.split("=", 1) if "=" in x else [x, 前の値] for x in 片[1:]]
            人たち = [(a.strip(), b.strip()) for a, b in 人たち if a.strip()]
            if not dst or not 項目 or not 人たち:
                だめ("月の変動 のタブ・項目・NO が要る（月の変動へ:<項目>|<NO>=<値>|<NO>）")
                continue
            if 名の数[名] > 1 and any("=" in x for x in 片[1:]):
                だめ(f"同じ「{名}」の行が {名の数[名]} 行在る（支給月ごとに分けて答える）")
                continue
            dh = dst[0]
            if not {"NO", "項目", "値"} <= set(dh):
                だめ("月の変動 の見出しが型と違う")
                continue
            足す, 合う = [], 0
            for no, x in 人たち:
                want = {"会社": 行.get("会社", "") or o.会社, "支給月": 行.get("支給月", ""), "NO": no, "項目": 項目}
                hit = next((d for d in dst[1:] if all(str(d[dh.index(c)]).strip() == str(w).strip() for c, w in want.items() if c in dh)), None)
                if hit is not None:
                    if str(hit[dh.index("値")]).strip() == x:
                        合う += 1
                        continue
                    足す = None
                    break
                new = [""] * len(dh)
                for c, w in {**want, "値": x}.items():
                    if c in dh:
                        new[dh.index(c)] = w
                足す.append(new)
            if 足す is None:
                だめ("月の変動 に同じ人・項目の違う値が在る")
                continue
            外す.add(r)
            dst.extend(足す)
            記.渡すタブ.add((f, t))
            記.数["他の所へ移した"] += m_old
            記.数["足した"] += sum(1 for n in 足す for x in n if not 空か(x))
            continue
        if 頭 == "人の列へ":
            dst = o.シート.get(f, {}).get("社員")
            読み = 読み替えを読む(片[:1])
            NOたち = [x.strip() for x in 片[1:] if x.strip()]
            if not dst or not 読み or not NOたち or "NO" not in dst[0] or next(iter(読み)) not in dst[0] or next(iter(読み)) in ("会社", "NO"):
                だめ("人の列へ:<社員の列>=<値>|<NO>|… の形・社員の列が要る")
                continue
            列, x = next(iter(読み.items()))
            dh = dst[0]
            ci, ni = dh.index(列), dh.index("NO")
            書く, 無い = [], []
            for no in NOたち:
                hit = [d for d in dst[1:] if str(d[ni]).strip() == no]
                if len(hit) != 1 or (not 空か(hit[0][ci]) and str(hit[0][ci]).strip() != x):
                    無い.append(no)
                elif 空か(hit[0][ci]):
                    書く.append(hit[0])
            if 無い or 空か(x):
                だめ(f"社員に 1 行だけ無いか、違う値が在る NO {無い}" if 無い else "値が空")
                continue
            for d in 書く:
                d[ci] = x
            外す.add(r)
            記.渡すタブ.add((f, t))
            記.数["他の所へ移した"] += m_old
            記.数["足した"] += len(書く)
            continue
    if not 外す:
        return rows
    return [rows[0]] + [rows[r] for r in range(1, len(rows)) if r not in 外す]


def 旧のタブを照らす(o: 物, 記: 記録, 手がかり: dict | None = None):
    """旧_ のタブの値が今のタブか md に在るか（寄せる道具.md §4.1）。消さない。消す問いへ並べる。"""
    for f in sorted(o.シート):
        tabs = o.シート[f]
        在る = {str(v).strip() for t, rows in tabs.items() if not t.startswith(旧の頭) for r in rows for v in r if not 空か(v)}
        本文 = "\n".join(o.md.values())
        for t in sorted(tabs):
            if not t.startswith(旧の頭):
                continue
            vals = [str(v).strip() for r in tabs[t][1:] for v in r if not 空か(v)]
            無い = [v for v in vals if v not in 在る and v not in 本文]
            if not 無い:
                記.消す問い.append({"物": f"タブ {t}", "置き場": f, "中身はどこに在るか": "今のタブ", "推奨": "消す",
                                "消す手順": [{"する": "タブを消す", "ファイル": f, "タブ": t}]})
                continue
            鍵 = f"{f}/{t}/旧のタブ"
            if o.人の答え.get(鍵) == "90_履歴 へ写して消す":
                記.消す問い.append({"物": f"タブ {t}", "置き場": f, "中身はどこに在るか": f"寄せの写しの中だけ（今に無い値 {len(無い)} 個）", "推奨": "消す",
                                "消す手順": [{"する": "タブを消す", "ファイル": f, "タブ": t}]})
                continue
            記.出せない(鍵, "旧_ のタブ", f"{f}/{t}", f"今のタブに無い値が {len(無い)} 個", ["型へ足す（B3 へ直しを頼む）", "90_履歴 へ写して消す"],
                      (手がかり or {}).get(t, ""))


# ---------------------------------------------------------------- 書く手順と戻す手順

def 列の字(n: int) -> str:
    s = ""
    n = max(n, 1)
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def 期限の日(今日: dt.date) -> str:
    """寄せの写しの消す日（推奨）: 寄せた日の翌々月末。突き合わせ（§1.6）の後の月末までに見回りが消す問いへ並べる。"""
    y, m = 今日.year + (今日.month + 1) // 12, (今日.month + 1) % 12 + 1
    return dt.date(y, m, calendar.monthrange(y, m)[1]).isoformat()


def 大きさ(*grids):
    return max((len(g) for g in grids), default=1) or 1, max((len(r) for g in grids for r in g), default=1) or 1


def 敷く(grid, h, w):
    """値を書く 1 手で前の値を残さないよう、前と後の大きい方まで空で埋めた格子にする（消してから書く 2 手にしない）。"""
    return [[(grid[r][c] if r < len(grid) and c < len(grid[r]) else "") for c in range(w)] for r in range(h)]


def 空でない数(rows) -> int:
    return sum(1 for r in rows[1:] for v in r if not 空か(v))


def 写しから戻す(o: 物, K: dict) -> dict:
    """書く手順が md を 90_履歴 へ移した所で落ち、同じ名の md がまだ作られていない時、移した写しを元の md として読む
    （頭からやり直せるように）。{戻した md の名: 実の写しの名} を返す（書く手順はその md を移さず作るだけ。
    戻す手順は実の写しの名を使う＝落ちた後の寄せ直しが月をまたいでも、写しの日がずれない）。"""
    戻した = {}
    for m in K["md"]:
        if m in o.md:
            continue
        写し = sorted(k for k in o.md if re.fullmatch(r"90_履歴/消す_\d{4}-\d{2}-\d{2}_" + re.escape(m.replace("/", "_")), k))
        if 写し:
            o.md[m] = o.md[写し[-1]]
            戻した[m] = 写し[-1]
    return 戻した


def 手順を作る(前: 物, 後: 物, 記: 記録, 今日: dt.date, 戻した_md: dict | None = None):
    """書く手順と戻す手順。どこで途中で落ちても、もう一度 寄せる で頭から当て直せる並びにする:
    受け取る側（新しいタブ・md・他のタブ）を先に書き、渡す側（値を他のタブ・md へ移したタブ。操作で決める）を後に書く。
    新しいタブは見出しまで 1 手で足す。1 つのタブは 値を書く 1 手（消してから書くの 2 手にしない）。"""
    名の移り = list(記.移した)

    def 今の名(f):
        for a, b in 名の移り:
            if f == a or (a.endswith("/") and f.startswith(a)):
                f = b + f[len(a):]
        return f

    タブの前の名 = {}
    for f, a, b in 記.タブの名:
        f = 今の名(f)
        タブの前の名[(f, b)] = タブの前の名.pop((f, a), a)
    足した = {(今の名(f), t) for f, t in 記.足したタブ}
    消す日 = 期限の日(今日)

    変わる = []  # (前のファイル, 前のタブ, 今のファイル, 今のタブ, 前の格子 or None, 後の格子)
    for f, tabs in 前.シート.items():
        nf = 今の名(f)
        for t, rows in tabs.items():
            nt = next((b for (ff, b), a in タブの前の名.items() if ff == nf and a == t), t)
            after = 後.シート.get(nf, {}).get(nt)
            if after is None or (nf, nt) in 足した:
                continue
            if after != rows:
                変わる.append((f, t, nf, nt, rows, after))
    for nf, nt in sorted(足した):
        前の = next((rows for f, tabs in 前.シート.items() for t, rows in tabs.items() if 今の名(f) == nf and t == nt), None)
        変わる.append((None, None, nf, nt, 前の, 後.シート[nf][nt]))
    md_変わる = [(m, 後.md[今の名(m)]) for m in 前.md if 今の名(m) in 後.md and 後.md[今の名(m)] != 前.md[m]]
    書かない = 書かない物(前, 後, 今の名, タブの前の名, 足した)

    # 渡す側は操作で決める（値を他のタブ・md へ移したタブ）。名の変わりを後へたどって今の名にする
    渡す = set()
    for f, t in 記.渡すタブ:
        f = 今の名(f)
        for ff, a, b in 記.タブの名:
            if 今の名(ff) == f and a == t:
                t = b
        渡す.add((f, t))
    受け = [x for x in 変わる if (x[2], x[3]) not in 渡す]
    渡し = [x for x in 変わる if (x[2], x[3]) in 渡す]
    書く, 戻す = [], []
    for f in sorted({x[0] for x in 変わる if x[0]}):
        書く.append({"する": "file を写す", "元": f, "先": f"90_履歴/消す_{消す日}_{f.replace('/', '_')}"})
    for a, b in 記.移した:
        書く.append({"する": "file を移す", "前": a, "後": b})
    for f, a, b in 記.タブの名:
        書く.append({"する": "タブの名を変える", "ファイル": 今の名(f), "前": a, "後": b})
    for nf, nt in sorted(足した):
        書く.append({"する": "タブを足す", "ファイル": nf, "タブ": nt, "見出し": list(後.シート[nf][nt][0]) if 後.シート[nf][nt] else []})
    # md は Drive の口で中身を直せない（canEdit=false）＝元を 90_履歴 へ移し（寄せの写しを兼ねる）、同じ名で新しく作る
    for m, text in md_変わる:
        if m not in 戻した_md:  # 写しから戻した md は元がもう 90_履歴 に在る＝作るだけ
            書く.append({"する": "file を移す", "前": 今の名(m), "後": f"90_履歴/消す_{消す日}_{今の名(m).replace('/', '_')}"})
        書く.append({"する": "md を作る", "名": 今の名(m), "本文": text})
    for _, _, nf, nt, rows, after in 受け + 渡し:
        h, w = 大きさ(rows or [], after)
        書く.append({"する": "値を書く", "ファイル": nf, "タブ": nt, "範囲": f"A1:{列の字(w)}{h}", "値": 敷く(after, h, w)})

    # 戻す手順＝全部書いた後の形に当てる逆（寄せの前の値から作る）。値が戻るタブ（渡した側）を先に、md・受けた側を後に
    for _, _, nf, nt, rows, after in 渡し + 受け:
        if (nf, nt) in 足した and not rows:
            continue
        h, w = 大きさ(rows or [], after)
        戻す.append({"する": "値を書く", "ファイル": nf, "タブ": nt, "範囲": f"A1:{列の字(w)}{h}", "値": 敷く(rows or [], h, w)})
    戻した_md = 戻した_md or {}
    for m, _ in md_変わる:  # 作った md を 90_履歴 へ外し、移した元（写しから戻した md は実の写しの名）を同じ名へ戻す
        写し = 戻した_md.get(m) or f"90_履歴/消す_{消す日}_{今の名(m).replace('/', '_')}"
        戻す.append({"する": "file を移す", "前": 今の名(m), "後": f"90_履歴/寄せた後_{消す日}_{今の名(m).replace('/', '_')}"})
        戻す.append({"する": "file を移す", "前": 写し, "後": 今の名(m)})
    for nf, nt in sorted(足した, reverse=True):
        if not any(今の名(f) == nf and nt in tabs for f, tabs in 前.シート.items()):
            戻す.append({"する": "タブを消す", "ファイル": nf, "タブ": nt})
    for f, a, b in reversed(記.タブの名):
        戻す.append({"する": "タブの名を変える", "ファイル": 今の名(f), "前": b, "後": a})
    for a, b in reversed(記.移した):
        戻す.append({"する": "file を移す", "前": b, "後": a})
    return 書く, 戻す, sorted({f"{x[2]}/{x[3]}" for x in 変わる}), 書かない


入口が書くタブ = ("勤怠", "勤怠の区間")  # 台帳の表 A・B（入口が原本から書く。寄せは形をそろえるだけ）


def 書かない物(前: 物, 後: 物, 今の名, タブの前の名: dict, 足した: set) -> list[dict]:
    """入れた物（タブ・md）のうち書く手順に出ない物と、なぜ。黙って捨てたと見えないよう一覧で返す。
    寄せは入れた値を Drive に在る形と見て、変わった所だけを書く（値を作らない）。前と同じ物は書かない。"""
    出す = []
    for f, tabs in 前.シート.items():
        nf = 今の名(f)
        for t, rows in tabs.items():
            nt = next((b for (ff, b), a in タブの前の名.items() if ff == nf and a == t), t)
            after = 後.シート.get(nf, {}).get(nt)
            if after is None or (nf, nt) in 足した or after != rows:
                continue
            n = max(len(rows) - 1, 0)
            if t.startswith(旧の頭):
                なぜ = "旧_ のタブ（書かない。消す問い・寄せられない物で扱う）"
            elif nt in 入口が書くタブ and nf.startswith("04_台帳_"):
                なぜ = ("入口が書く物（台帳の表 A・B）。寄せは形をそろえるだけで、入れた値が今の形のままなら書かない"
                       "（入れた値＝Drive に在る値と見る）。Drive に無い勤怠を置くのは入口の口（寄せの入力に入れても書かない）")
            else:
                なぜ = "前と同じ（今の形のまま＝書く事が無い）"
            出す.append({"所": f"{nf}/{nt}", "行": n, "なぜ": なぜ})
    for m, text in 前.md.items():
        if 後.md.get(今の名(m)) == text:
            出す.append({"所": 今の名(m), "行": 0, "なぜ": "前と同じ（今の形のまま＝書く事が無い）"})
    return 出す


def 手順を当てる(d: dict, 手順: list[dict]) -> dict:
    """書く手順・戻す手順を値の上で当てる（殻が Drive に当てるのと同じ順・試験で照らすのに使う）。"""
    d = copy.deepcopy(d)
    S, M = d.setdefault("シート", {}), d.setdefault("md", {})
    d.setdefault("置き場", [])

    def mv(a, b):
        for dd in (S, M):
            for k in list(dd):
                if k == a or (a.endswith("/") and k.startswith(a)):
                    dd[b + k[len(a):]] = dd.pop(k)
        d["置き場"] = [b + x[len(a):] if (x == a or (a.endswith("/") and x.startswith(a))) else x for x in d["置き場"]]

    for s in 手順:
        k = s["する"]
        if k == "file を写す":
            continue
        if k == "file を移す":
            mv(s["前"], s["後"])
        elif k == "タブの名を変える":
            S[s["ファイル"]][s["後"]] = S[s["ファイル"]].pop(s["前"])
        elif k == "タブを足す":
            S.setdefault(s["ファイル"], {})[s["タブ"]] = [list(s["見出し"])] if s["見出し"] else []
        elif k == "タブを消す":
            S[s["ファイル"]].pop(s["タブ"])
        elif k == "値を書く":
            S[s["ファイル"]][s["タブ"]] = そろえる(copy.deepcopy(s["値"]))
        elif k in ("md を書く", "md を作る"):
            M[s["名"]] = s["本文"]
            if s["名"] not in d["置き場"]:
                d["置き場"].append(s["名"])
    return d


# ---------------------------------------------------------------- 見通す（1 社）

def 見通す(会社: dict, 型: dict, 直したち: list[dict], 今日: dt.date | None = None) -> dict:
    """1 社の今の版から型の版まで、直しを順に当てた結果を返す（書かない）。"""
    今日 = 今日 or dt.date.today()
    K = 型を読む(型)
    前 = 物(会社)
    o = 物(会社)
    記 = 記録()
    直したち = 前の形を足す(直したち, o.前の形)
    当てる = 直しの形.当てる直し(直したち, o.版, o.部品)
    for d in 当てる:
        if d.get("前の形の操作"):
            記.知らせ.append(f"前の形の読み替え（人の答え）の操作 {d['前の形の操作']} を、直し {d['版']} の前に当てた")
    最後 = 直したち[-1]["版"] if 直したち else 0
    if 最後 != K["版"]:
        raise 直しの形.直しの誤り(f"型の版 {K['版']} と直しの最後の版 {最後} が違う（直しの無い型の直し）")
    if o.版 > K["版"]:
        raise 直しの形.直しの誤り(f"会社の版 {o.版} が型の版 {K['版']} より新しい")
    戻した_md = {**写しから戻す(前, K), **写しから戻す(o, K)}
    手がかり = {}
    for d in 当てる:  # 手がかりは先に全部を重ねる（後の直しの手がかりが前の直しの操作の止まりにも出る・後が勝つ）
        手がかり.update(d.get("手がかり", {}))
    for d in 当てる:
        for n, op in enumerate(d["操作"], 1):
            当てる操作(o, op, K, 記, d["版"], n, 手がかり)
    # 答えで今の項目にした行へは、この回に当てる直しだけでなく今の版までの直し全部の読み替えを通す
    # （型の版が今の版の会社でも、答えの行には直しの読み替えがまだ一度も当たっていない）
    答えへ = [d for d in 直したち if d.get("部品", "共通") in ["共通", *o.部品]]
    # 型の版を上げない読み（直し/今の型の読み.json）: 段の解決・芯/計算 がそのまま使える形へ。どの版の会社にも毎回当てる
    import 計算の形
    読み = 計算の形.読みを開く()
    計算の形.当てる(o, K, 型, 記, 答えへ, 読み)
    照らす(o, K, 記, 手がかり, 前, 答えへ)
    旧のタブを照らす(o, 記, 手がかり)
    計算の形.当てる_照らすの後(o, 前, 記, 読み)
    # 型の版を上げない読み: 前の 勤務の長さの丸め（直し 3 が 時間.打刻の丸めの単位 へ移した値）を黙って使わず 委託.実働の丸め への問いに。どの版の会社にも毎回
    import 実働の丸め
    実働の丸め.当てる(o, 記, 前)

    n前, n後 = 数える(前.シート), 数える(o.シート)
    c = 記.数
    出た = sum(int(re.search(r"値 (\d+) 個", x["中身"]).group(1)) for x in 記.寄せられない if re.search(r"値 (\d+) 個", x["中身"]) and x["種類"] in ("行き先の無い列", "行き先の無いタブ"))
    捨てた = c["捨てた（直しの持たない）"] + c["捨てた（人の答え）"]
    移った = n後 - c["足した"] - 出た + c["重ねた"] + c["md へ移した"] + c["他の所へ移した"]
    保ち = {"前の空でない値": n前, "後へ移った": 移った, "寄せられない物に出た": 出た, "捨てた": 捨てた,
           "内訳": dict(c), "合う": n前 == 移った + 出た + 捨てた}
    if not 保ち["合う"]:
        raise 保ちの誤り(f"値の保ちが合わない: {保ち}")

    for x in 記.消す問い:
        x.update({"会社": o.会社, "中を見た窓": x.get("中を見た窓", ""), "期限": x.get("期限", ""), **x})
    o.版 = K["版"]
    書く, 戻す, 変わるタブ, 書かない = 手順を作る(前, o, 記, 今日, 戻した_md)
    書かない += 記.書かない
    for x in 書かない:
        if x["行"] and x["所"].rsplit("/", 1)[-1] in 入口が書くタブ:
            記.知らせ.append(f"{x['所']}: 入れた {x['行']} 行は書く手順に出ない（{x['なぜ']}）")
    出せない = bool(記.寄せられない)
    結果 = {
        "会社": o.会社, "前の版": 前.版, "今の版": K["版"], "当てた直し": [d["版"] for d in 当てる],
        # 寄せられない物が在る時は、寄せた後の値＝寄せの前の値（書かない）。半ば寄った形は「見通しの値」で見るだけ
        "寄せた後の値": 前.出す() if 出せない else o.出す(), "見通しの値": o.出す() if 出せない else None,
        "書く手順": [] if 出せない else 書く, "戻す手順": [] if 出せない else 戻す,
        "寄せられない物": 記.寄せられない, "足りない値": 記.足りない,
        "消す問い": 記.消す問い, "変わるタブ": 変わるタブ, "書かない物": 書かない, "持たない": [list(x) for x in 記.持たない],
        "知らせ": 記.知らせ, "値の保ち": 保ち, "無い値": 記.無い値,
    }
    結果["人が見る物"] = 人が見る物(結果)
    return 結果


def 人が見る物(r: dict) -> str:
    """1 社の見通しを 1 枚にした md（置き場は Drive の確認ページの置き場・repo には出さない）。"""
    L = [f"# 寄せの見通し: {r['会社']}", "",
         f"- 版: {r['前の版']} → {r['今の版']}（当てる直し: {', '.join(map(str, r['当てた直し'])) or 'なし'}）",
         f"- 変わるタブ: {len(r['変わるタブ'])}（{'・'.join(r['変わるタブ']) or 'なし'}）",
         f"- 入れたが書かない物: {len(r['書かない物'])}（前と同じ・入口が書く物。下の表）",
         f"- 寄せられない物: {len(r['寄せられない物'])}（1 つでもあれば書かない）",
         f"- 足りない値: {len(r['足りない値'])}（仮と 1 問の口へ）",
         f"- 消す問いへ並べる物: {len(r['消す問い'])}",
         f"- 寄せた後に無い値: {len(r['無い値'])}（書かない・段の解決と芯が仮と問いにする）",
         f"- 値の保ち: 前 {r['値の保ち']['前の空でない値']} ＝ 移った {r['値の保ち']['後へ移った']} ＋ 寄せられない {r['値の保ち']['寄せられない物に出た']} ＋ 捨てた {r['値の保ち']['捨てた']}（{'合う' if r['値の保ち']['合う'] else '合わない'}）", ""]
    if r["書かない物"]:
        L += ["## 入れたが書かない物（捨てない・Drive に在るまま）", "", "| 所 | 行 | なぜ |", "|---|---|---|"]
        L += [f"| {x['所']} | {x['行']} | {x['なぜ']} |" for x in r["書かない物"]] + [""]
    if r["無い値"]:
        L += ["## 寄せた後に無い値（書かない。段の解決と芯が仮と問いにする）", "", "| 項目 | 段 | 所 | 前の道具 | なぜ |", "|---|---|---|---|---|"]
        L += [f"| {x['項目']} | {x['段']} | {x['所']} | {x['前の道具']} | {x['なぜ']} |" for x in r["無い値"]] + [""]
    if r["持たない"]:
        L += ["## 型が持たないと決めた値（捨てる）", "", "| 所 | 件数 | なぜ |", "|---|---|---|"]
        L += [f"| {a} | {n} | {w} |" for a, n, w in r["持たない"]] + [""]
    if r["寄せられない物"]:
        L += ["## 寄せられない物と選べる答え", "", "| 鍵 | 種類 | 中身 | 選べる答え | 手がかり |", "|---|---|---|---|---|"]
        L += [f"| `{x['鍵']}` | {x['種類']} | {x['中身']} | {' ／ '.join(x['選べる答え'])} | {x['手がかり']} |" for x in r["寄せられない物"]] + [""]
    return "\n".join(L)
