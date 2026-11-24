#!/usr/bin/env python3
"""オーナーへの文の照らし（給与エージェント）— オーナーへ出す問い・頼みの文に、番号だけの頼みと、担当者へ聞く物が混ざっていないかを見る。

決まりの正本は同じ plugin の `決まり.md`「聞く」（オーナーに回す物と知らせ方）。ここはその文の見分けだけを持つ（決まりを写さない）。
見る物:
  - 種類の印: オーナーへ選択肢の画面で聞いてよいのは「聞く」の節の決まった 1 行（`- 許す印: `〔…〕`・…`）の種類だけ＝許す種類だけ通す。
    印はその 1 行だけから読み（写さない・節のほかの `〔…〕` は印にしない）、問いの頭に印が無い問い（会社の決まり・人ごとの事実なども）を知らせる。
    その 1 行が無い・2 行在る・印の形でない物が混ざる時は印を空にし、どの問いも通さず読めないと知らせる（既定で止める）。語を足して拾う形にしない。
  - 問いの番号（`Q<支給年月>-<順>`）・受付番号（`R<YYMMDD>-<英数 4 字>`）: 番号だけでは、どこで何に答えるかが分からない。
  - 検算・原本の読み方: 事務所の担当者へ確認ページで聞く物で、オーナーに聞く物でない。
止めない（知らせるだけ）。hook の入口（../hooks/見張り.py）が選択肢の画面（AskUserQuestion）の文に当て、当たれば窓へ知らせる。
番号の形は写さず、パックの正本（パックの場所.番号の形たち）から読んで渡す。読めない時は番号を照らせないと知らせる。
使い方: python3 オーナーへの文の照らし.py [--パック <dir>] < 文   （終わりの値: 0=当たり無し／1=当たり有り〔数は出した行で見る〕／2=照らしが壊れた＝結果ではない）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import パックの場所 as 場所  # noqa: E402

担当者へ聞く物 = re.compile(r"検算|計算(が|は)合って|原本の読み|打刻の読み|勤怠の読み")

番号の訳 = ("番号（{何}）でオーナーに頼んでいる。番号だけでは、どこで何に答えるかが分からない。"
         "どの会社の担当者に・何を聞いたか（中身を文で）・どこで答えが見られるか（確認ページか質問と回答の在り処）を書き、番号は消す")
担当者の訳 = ("「{何}」をオーナーに聞いている。検算・原本の読み方は事務所の担当者へ確認ページで聞く物"
          "（オーナーに聞かない）。〔口: 問いの関所〕を通して次のまとめた問いに入れる")
読めない訳 = "番号の形を読めないので、問いの番号・受付番号は照らしていない"   # パックの場所が分からない時は 場所.分からない訳 に包む
印の無い訳 = ("問い「{問い}」は頭に種類の印が無い。オーナーへ選択肢の画面で聞くのは決まり.md「聞く」の種類（{印たち}）だけで、"
          "問いの頭にその印を名乗る。会社の決まり・人ごとの事実・検算・原本の読み方は事務所の担当者へ確認ページで聞く（〔口: 問いの関所〕）")
印を読めない訳 = "決まり.md「聞く」の「- 許す印: 」の 1 行から種類の印（`〔…〕`）を読めないので、問いの種類は照らしていない"
字を読めない訳 = ("字のそろえ方（同じ版のパックの 芯/字.py）を読めないので、全角・幅の無い字で書いた番号・語・印は"
            "そろえずに照らした（揺れた字を見落とし得る）")

決まりの置き場 = Path(__file__).resolve().parent.parent / "決まり.md"
_許す印の行 = re.compile(r"^- 許す印: (.*)$", re.M)
_印の形 = re.compile(r"`(〔[^`〔〕]+〕)`")


def _字():
    """字のそろえ方の正本（この照らしと同じ版のパックの 芯/字.py。写さない）。読めなければ None。"""
    try:
        パック = 場所.同じ版のパック(Path(__file__))
        return 場所.字の口(パック) if パック else None
    except Exception:   # 読めない時は照らしを止めず、そろえずに照らした事を知らせる
        return None


def _そろえた文(文: str, 字=None) -> str:
    """文 → NFKC・幅の無い字の消し・続いた空白を 1 つにした字（大小と語の間の 1 つの空白は残す）。字の口が無ければそのまま。"""
    return 字.そろえる(文, 大小も=False, 空白も=False) if 字 else (文 or "")


def 許す印たち(決まり: Path | None = None) -> tuple[str, ...]:
    """決まり.md の「## 聞く」の節の決まった 1 行 `- 許す印: `〔…〕`・`〔…〕`` の印の字（節のほかの所は読まない）。
    読めない・節が無い・その行が無いか 2 行以上・行に印の形（バッククォートの〔…〕を・で並べた物）でない物が在れば空（既定で止める）。"""
    try:
        s = (決まり or 決まりの置き場).read_text(encoding="utf-8")
    except OSError:
        return ()
    m = re.search(r"^## 聞く[ \t]*\n(.*?)(?=^## |\Z)", s, re.M | re.S)
    行たち = _許す印の行.findall(m.group(1)) if m else []
    if len(行たち) != 1:
        return ()
    項たち = [x.strip() for x in 行たち[0].split("・")]
    if not 項たち or not all(_印の形.fullmatch(x) for x in 項たち):
        return ()
    return tuple(dict.fromkeys(_印の形.fullmatch(x).group(1) for x in 項たち))


def 印を照らす(args: dict, 印たち) -> list[str]:
    """選択肢の画面の問いごとに、問いの字の頭が許す印のどれかで始まるかを見る（許す種類だけ通す）。当たった所の訳。"""
    if not 印たち:
        return [印を読めない訳]
    訳 = []
    字の口 = _字()
    for q in (args or {}).get("questions") or []:
        問い = str(q.get("question", "") if isinstance(q, dict) else q).strip()
        # 幅の無い字・全角の揺れは そろえて照らす（芯/字.py）。印の中の空白は崩した印のまま（空白は消さず 1 つにまとめるだけ）
        頭が = any(_そろえた文(問い, 字の口).startswith(_そろえた文(印, 字の口)) for 印 in 印たち)
        if not 頭が:
            訳.append(印の無い訳.format(問い=問い[:40], 印たち="・".join(印たち)))
    if not 字の口 and 訳:
        訳.append(字を読めない訳)
    return 訳


def 番号の形を組む(形たち) -> re.Pattern | None:
    """パックの正本の形の字たち → 文の中を探す 1 つの形（前後が英数字でない所だけ）。無ければ None。"""
    形たち = [f for f in (形たち or ()) if f]
    if not 形たち:
        return None
    return re.compile(r"(?<![A-Za-z0-9])(" + "|".join(f"(?:{f})" for f in 形たち) + r")(?![A-Za-z0-9])")


def 照らす(文: str, 形たち, パックが在る: bool = True, パック引数: str | None = None) -> list[str]:
    """当たった所の訳（当たり無しなら空）。形たち＝パックの正本の番号の形の字（パックの場所.番号の形たち）。
    パックが在る＝False の時、番号を照らしていない訳を パックの場所.分からない訳 で包む（直し方を言う）。
    パック引数＝道具に --パック で渡した dir（渡した dir に目印が無い訳を言うため。無ければ None）。"""
    字の口 = _字()
    文 = _そろえた文(文, 字の口)   # 全角のＱ・幅の無い字を挟んだ番号や語も同じ字で照らす（芯/字.py でそろえる）
    訳 = [] if 字の口 else [字を読めない訳]
    番号 = 番号の形を組む(形たち)
    nums = sorted(set(m.group(1) for m in 番号.finditer(文))) if 番号 else []
    if 番号 is None:
        訳.append(読めない訳 if パックが在る else 場所.分からない訳(読めない訳, パック引数))
    if nums:
        訳.append(番号の訳.format(何="・".join(nums)))
    for 何 in sorted(set(m.group(0) for m in 担当者へ聞く物.finditer(文.replace(" ", "")))):   # 語の中の空白も詰めて照らす
        訳.append(担当者の訳.format(何=何))
    return 訳


def 選択肢の画面の文(args: dict) -> str:
    """AskUserQuestion の入力から、オーナーが読む字（問い・見出し・選択肢の名と説明）を 1 つの文にする。"""
    字 = []
    for q in (args or {}).get("questions") or []:
        if not isinstance(q, dict):
            continue
        字 += [str(q.get("question", "")), str(q.get("header", ""))]
        for o in q.get("options") or []:
            if isinstance(o, dict):
                字 += [str(o.get("label", "")), str(o.get("description", ""))]
    return "\n".join(字)


def main(a: list[str]) -> int:
    """当たりを 1 行ずつ出す。終わりの値は 0＝当たり無し／1＝当たり有り（数は出した行で見る）。"""
    パック引数 = a[a.index("--パック") + 1] if "--パック" in a[:-1] else None
    パック = 場所.探す(パック引数)
    hits = 照らす(sys.stdin.read(), 場所.番号の形たち(パック) if パック else None, パック is not None, パック引数)
    for h in hits:
        print(h)
    return 1 if hits else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:  # 道具そのものが壊れた＝終わりの値 2（1 の「当たり有り」と混ぜない）
        import traceback
        traceback.print_exc()
        print(f"✗ 道具が壊れた（オーナーへの文の照らし・終わりの値 2＝結果ではない）: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
