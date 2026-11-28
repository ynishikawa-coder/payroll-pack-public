"""試験の手伝い: 作り物の 質問と回答（3 タブ）の今の表を組む 1 か所（設問・始める・答え合わせ・月次の試験が読む）。

設問の 既にある は 質問と回答.読む の戻り（表）か空の並び [] だけを受ける（前の 1 枚の表の行は止める）。
試験は「この文の問いを聞いた・この答えが来た」を短く書きたい＝ここで行の並びから表を組む（答えの形は 2_答え の 回答 の字のまま）。
"""
import sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
if str(根) not in sys.path:
    sys.path.insert(0, str(根))
from 初期設定 import 質問と回答 as qa  # noqa: E402


def _月(x) -> str:
    return qa.口.支給月の字.そろえる(x, "中") or ""


def 表(*行たち, 支給月="2099-01", 顧客ID="") -> "qa.表":
    """行 {質問（か 文）, 回答?, 問いの鍵（か 鍵）?, 支給月?, 顧客ID?, 状態?, 回答日?} の並び → 質問と回答.表。
    回答 の在る行は 2_答え に答えの行を置き状態を 答えた にする。回答 に並びを渡すと送り直し（下の行が今の答え）。
    鍵 を省くと Q1, Q2 … を振る。支給月 は YYYY.MM支給 でも YYYY-MM でもよい（1_問い の 聞いた支給月 へそろえる）。"""
    t = qa.表()
    for i, r in enumerate(行たち, 1):
        鍵 = str(r.get("問いの鍵") or r.get("鍵") or f"Q{i}")
        回答 = r.get("回答", "")
        回答たち = list(回答) if isinstance(回答, (list, tuple)) else ([回答] if 回答 else [])
        状態 = r.get("状態") or (qa.答えた if 回答たち else qa.聞いている)
        t.問いたち.append(qa.問い(鍵, str(r.get("顧客ID", 顧客ID)), _月(r.get("支給月") or 支給月), str(r.get("聞いた日", "")),
                              str(r.get("質問") or r.get("文") or ""), "", 状態))
        for a in 回答たち:
            t.答えたち.append(qa.答え(鍵, a, str(r.get("回答日", "")), ""))
    return t


def 格子たち(t: "qa.表") -> dict:
    """表 → {Drive のタブの名: 格子}（PAYROLL_QA_ROWS・始める の 既にある の JSON・殻が読んだ形）。"""
    out = {qa.Driveのタブ(x): [qa.見出し(x)] for x in qa.タブたち}
    for q in t.問いたち:
        out[qa.Driveのタブ("問い")].append(qa._行の値("問い", q))
    for a in t.答えたち:
        out[qa.Driveのタブ("答え")].append(qa._行の値("答え", a))
    for f in t.振り分けたち:
        out[qa.Driveのタブ("振り分け")].append(qa._行の値("振り分け", f))
    return out
