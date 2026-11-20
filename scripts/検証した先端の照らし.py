#!/usr/bin/env python3
"""検証した先端の照らし — PR 本文の「検証した base の先端」が、今の base の先端と同じかを見る（止めない・知らせるだけ）。

防ぐ故障: PR 本文の検証（他の PR とのぶつかり・試験の結果）を作った時の結果のまま置き、base が進んでも照らし直さず、
事実と違う本文（「ぶつからない」など）が残る。本文の頭の欄 `検証した base の先端: <commit>`（PR の型 .github/pull_request_template.md）
に書いた commit と、今の base の先端を照らし、違えば PR のチェックの表示（check run・neutral）で「検証し直す」と知らせる。

success の材料は本文の字（申告）だけにしない: 欄の commit が今の base の先端と同じで、かつ PR の先端がその先端を
実際に含む（GitHub の compare で base の先端 ... PR の先端 が ahead か identical）時だけ success にする。
含むかを読めない・渡されない時も success にしない（既定は知らせる）。base を取り込まずに今の先端の字だけを欄に書くと
「欄の commit を PR の先端が含まない」と知らせる。
欄（申告）を畳まない訳: 本文を書いた時の base は記録に無い（PR の先端が base を含むかは記録で分かるが、本文の検証を
いつ書いたかは本文にしか無い）。base を取り込んでも本文を書き直さなければ欄は古いまま残り、それで本文の古さが見える。

欄の形の正本はこの file の `欄の形`（PR の型の欄の名はここから読んで試験が照らす＝tests/test_検証した先端の照らし.py）。
欄が無い・commit の形でない・2 つ在る時も知らせる（黙って通さない）。commit は 7〜40 字の 16 進（短い形は頭で照らす）。

使い方（.github/workflows/verify-base.yml が呼ぶ。網に出ない＝本文と先端は file と引数で渡す）:
  python3 scripts/検証した先端の照らし.py --本文 <PR 本文の file> --先端 <今の base の先端の commit> --base <base の枝の名> \
      --compare <GitHub の compare（今の base の先端...PR の先端）の status を生のまま。読めなければ空>
  status → 含むかの対応の正本は `含むか`（workflow は字を写さず生のまま渡す）。
  → 1 行の JSON {"conclusion": "success"|"neutral", "title": …, "summary": …} を出す（exit はいつも 0＝止めない）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

欄の名 = "検証した base の先端"
欄の形 = re.compile(r"^[ \t]*" + re.escape(欄の名) + r"[ \t]*[:：][ \t]*(.*?)[ \t]*$", re.M)
_commit = re.compile(r"[0-9a-f]{7,40}")


# GitHub の compare（base...head）の status → PR の先端が base の先端を含むか。ここに無い値・空は None（success にしない）
_含む_status = {"ahead": True, "identical": True, "behind": False, "diverged": False}


def 含むか(status: str | None) -> bool | None:
    """compare の status（生の字）→ True（含む）／False（含まない）／None（読めない・知らない値）。"""
    return _含む_status.get((status or "").strip().lower())


def 照らす(本文: str, 先端: str, base: str = "base", 含む: bool | None = None) -> dict:
    """PR 本文・今の base の先端・PR の先端がその先端を含むか → {conclusion, title, summary}。
    欄の commit が今の先端と同じで、PR の先端が今の先端を含む（含む is True）時だけ success、ほかは neutral（知らせる）。"""
    先端 = (先端 or "").strip().lower()
    書いた = 欄の形.findall(本文 or "")
    直し方 = (f"今の {base} の先端 {先端[:12] or '（読めない）'} の上で検証（他の PR とのぶつかり・試験）をやり直し、"
           f"本文の検証の欄と `{欄の名}:` の commit を書き直す")
    if not _commit.fullmatch(先端):
        return {"conclusion": "neutral", "title": f"{base} の先端を読めない",
                "summary": f"今の {base} の先端（{先端 or '空'}）を読めないので、本文の検証の鮮度を照らしていない"}
    if not 書いた:
        return {"conclusion": "neutral", "title": f"本文に `{欄の名}:` の欄が無い",
                "summary": f"本文の頭に `{欄の名}: <検証した時の {base} の commit>` を書く（PR の型）。{直し方}"}
    if len(書いた) > 1:
        return {"conclusion": "neutral", "title": f"本文に `{欄の名}:` の欄が {len(書いた)} つ在る",
                "summary": f"欄は 1 つだけ書く。{直し方}"}
    c = 書いた[0].lower()
    if not _commit.fullmatch(c):
        return {"conclusion": "neutral", "title": f"`{欄の名}:` が commit の形でない",
                "summary": f"「{書いた[0][:40]}」は 7〜40 字の 16 進の commit でない。{直し方}"}
    if 先端.startswith(c) and 含む is not True:
        if 含む is None:
            return {"conclusion": "neutral", "title": f"PR の先端が今の {base} の先端を含むかを読めない",
                    "summary": f"本文の欄は今の {base} の先端 {先端[:12]} だが、PR の先端がそれを含むか（compare）を"
                               f"読めないので、検証の鮮度を success にしない。PR の check を回し直すと照らし直す"}
        return {"conclusion": "neutral", "title": f"欄の commit を PR の先端が含まない（{base} を取り込んでいない）",
                "summary": f"本文の欄は今の {base} の先端 {先端[:12]} だが、PR の先端はそれを含まない＝"
                           f"{base} を取り込まずに欄の字だけを書いた。{base} を取り込み、その上で検証（他の PR とのぶつかり・試験）をやり直して本文を書き直す"}
    if 先端.startswith(c):
        return {"conclusion": "success", "title": f"検証した {base} の先端は今の先端と同じ",
                "summary": f"本文の欄は今の {base} の先端 {先端[:12]} で、PR の先端はそれを含む"}
    return {"conclusion": "neutral", "title": f"{base} が検証の後に進んだ（検証し直す）",
            "summary": f"本文の検証は {c[:12]} の上で行った物で、今の {base} の先端は {先端[:12]}。"
                       f"本文の「ぶつからない」「緑」などは今の先端では確かめていない。{直し方}"}


def main(argv: list[str]) -> int:
    def 引数(名: str) -> str | None:
        return argv[argv.index(名) + 1] if 名 in argv[:-1] else None

    path, 先端, base = 引数("--本文"), 引数("--先端") or "", 引数("--base") or "base"
    含む = 含むか(引数("--compare"))
    try:
        本文 = Path(path).read_text(encoding="utf-8") if path else ""
    except OSError:
        本文 = ""
    print(json.dumps(照らす(本文, 先端, base, 含む), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
