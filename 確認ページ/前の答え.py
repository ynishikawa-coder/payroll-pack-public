#!/usr/bin/env python3
"""前の答えを照らす口（給与の問い）: 先方へ出す問いを、質問と回答の答え済みと照らす。答え済みの問いは出せない。

なぜ在るか（根治・2026-11-17）: ある顧問先の月で、窓が答え済みの問いを新しい番号で先方へ出しかけた。確認ページの型の検査
（土台の qa-html の check.mjs）は「前の答えを照らす口」を持つが、給与の値の表にその命令が無く、給与の問いでは一度も照らして
いなかった。照らしの芯はパックのここ 1 か所に置き、値の表 `config/skill-values.json` の `docs-kit.qa-html.prior_check_cmd`
がこれを指す（どちらのアカウントの殻でも同じ照らし）。命令の約束は qa-html の §前の答えを照らす口（形 qa-prior/1）。

照らし方（答えが「分からない」の行・「出し直し」の行・回答の空の行は答え済みに数えない＝問いの番号ごとに一番下の行が正）:
  1. 同じ問いの番号に答えがある → 答え済み
  2. 番号が違っても、この問いの行の 反映先・答えで変わる項目と人 か問いの字に出る 03_マスタ の設定の項目が、答え済みの問いの
     反映先と重なる（人の問いは 対象 の人も同じ）→ 答え済み
  3. 問いの字の 2 字組の 8 割以上が答え済みの問いの字に在る（言い回しだけ変えた聞き直し）→ 答え済み
     （聞き直す時は、質問と回答のその問いの行の 理由 に「聞き直し: <前の問いの番号>・<訳>」と書く＝記録に残る形でだけ外せる）

パックは Drive を開かない。質問と回答（タブ 質問・get_values の形・1 行目が見出し）は殻が読んで file に置き、その path を渡す:
  確認ページ（check.mjs --run-prior が呼ぶ・標準入力に qa-prior/1）:
      環境 PAYROLL_QA_ROWS=<質問の表の JSON の path>・PAYROLL_QA_COMPANY=<会社>（任意）・PAYROLL_PACK_DIR=<パックの dir>
  手で: python3 確認ページ/前の答え.py --rows <path> [--company <会社>] [--questions <1 行 1 問の file>]
出力: {"answered": {鍵: "<前の問いの番号>（<訳>）"}, "checked": {鍵: "照らした: 質問と回答 N 行・答え済み M 問"}}。
exit: 0＝照らした（--questions の時は答え済みが 1 つでもあれば 2）／2＝照らせない（表が無い・読めない・見出しが無い・入力の形が違う・
  渡した会社の行が無くほかの会社の行がある＝名の打ち違い）。
照らせない時は何も出さず 2 で終わる＝check.mjs が赤にする（黙って全部 checked にしない）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

形の名 = "qa-prior/1"
タブ = "質問"
近さの線 = 0.8
分からない = "分からない"
出し直し = "出し直し"
聞き直し = re.compile(r"聞き直し[:：]\s*(Q\d{6}-\d+)")
要る見出し = ("問いの番号", "質問", "回答")


def 鍵(no: str) -> str:
    """問いの番号 → 確認ページの問いの鍵（英数字と _ だけ）。"""
    return re.sub(r"[^0-9A-Za-z_]", "_", str(no).strip())


def _ならす(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"[\s、。・,.!?？！「」『』（）()【】:：/／\-ー〜~]", "", s)


def 足りない見出し(values: list[list]) -> list[str]:
    """照らすのに要る見出しのうち、表の 1 行目に無い物（無ければ答え済み 0 で全部 checked＝黙って緑になる）。"""
    h = [str(x).strip() for x in (values[0] if values else [])]
    return [k for k in 要る見出し if k not in h]


def 行にする(values: list[list]) -> list[dict]:
    if not values:
        return []
    h = [str(x).strip() for x in values[0]]
    return [{h[i]: (r[i] if i < len(r) else "") for i in range(len(h))} for r in values[1:] if any(str(c).strip() for c in r)]


def 答え済みの行(行たち: list[dict]) -> dict[str, dict]:
    """問いの番号ごとの一番下の行のうち、答えのある物（分からない・出し直し・空は外す）。"""
    last: dict[str, dict] = {}
    for r in 行たち:
        no = str(r.get("問いの番号", "")).strip()
        if no:
            last[no] = r
    out = {}
    for no, r in last.items():
        a = str(r.get("回答", "")).strip()
        if a and not a.startswith(分からない) and not a.startswith(出し直し):   # 出し直し→ は別の問いへ移った印
            out[no] = r
    return out


def 設定の項目(字: str) -> set[str]:
    """反映先・答えで変わる項目の字から、03_マスタ の設定の項目の名を取り出す（`03_マスタ/会社/時間.始業前の打刻・休憩の表` →
    {始業前の打刻, 休憩の表}）。項目の頭の分け（時間. など）は外す。md の節・台帳（04_台帳）は数えない（広すぎる）。"""
    out: set[str] = set()
    in_master = False
    for part in re.split(r"[・、,，;；\n]", str(字 or "")):
        part = part.strip()
        if not part:
            continue
        if ".md" in part:   # 決まりの md の節は設定の項目でない（広すぎる）＝ここで 03_マスタ の続きも切る
            in_master = False
            continue
        if "/" in part:
            in_master = "03_マスタ/" in part
            if not in_master:
                continue
            seg = [s for s in part.split("/") if s]
            item = seg[-1] if len(seg) >= 3 else ""
        else:
            item = part if in_master else ""
        item = re.sub(r"[（(].*$", "", item).split(".")[-1].strip()
        if len(item) >= 3:
            out.add(item)
    return out


def 含み(新: str, 前: str) -> float:
    """新しい問いの字の 2 字組のうち、前の問いに在る物の割合（言い回しを少し変えただけの聞き直しを拾う）。"""
    a, b = _ならす(新), _ならす(前)
    if len(a) < 2 or not b:
        return 0.0
    ga = {a[i:i + 2] for i in range(len(a) - 1)}
    gb = {b[i:i + 2] for i in range(len(b) - 1)}
    return len(ga & gb) / len(ga)


def 知らない会社(行たち: list[dict], 会社: str | None) -> bool:
    """会社を渡したのに、その会社の行が 1 つも無く、ほかの会社の行がある＝名の打ち違い・略した名（照らす行が 0 で全部
    checked になり黙って緑になる）。会社の欄が全部空の表（1 社だけの表）と、会社を渡さない時は False。"""
    if not 会社:
        return False
    名たち = {str(r.get("会社", "")).strip() for r in 行たち} - {""}
    return bool(名たち) and 会社 not in 名たち


def 照らす(問いたち: list[dict], 行たち: list[dict], 会社: str | None = None) -> dict:
    """同じ番号の答え／同じ設定の項目に映った答え（人の問いは対象の人も同じ）／字のほぼ同じ問い の 3 つで答え済み。"""
    if 会社:
        行たち = [r for r in 行たち if str(r.get("会社", "")).strip() in (会社, "")]
    済 = 答え済みの行(行たち)
    鍵から = {鍵(no): no for no in 済}
    自分 = {}
    for r in 行たち:   # 問いの番号ごとの一番下の行（この問いそのものの行＝反映先・対象・理由を読む）
        自分[鍵(r.get("問いの番号", ""))] = r
    済の項目 = {no: 設定の項目(r.get("反映先", "")) | 設定の項目(r.get("答えで変わる項目と人", "")) for no, r in 済.items()}
    answered, checked = {}, {}
    for q in 問いたち:
        k = q["key"]
        字 = q.get("question", "") or ""
        if k in 鍵から:
            r = 済[鍵から[k]]
            answered[k] = f"{鍵から[k]}（{str(r.get('回答', ''))[:30]}）"
            continue
        mine = 自分.get(k) or {}
        外す = set(聞き直し.findall(str(mine.get("理由", ""))))
        項目 = 設定の項目(mine.get("反映先", "")) | 設定の項目(mine.get("答えで変わる項目と人", ""))
        対象 = _ならす(mine.get("対象", ""))
        当たり = None
        for no, r in 済.items():
            if no in 外す:
                continue
            人の問い = str(r.get("対象", "")).startswith("人") or str(mine.get("対象", "")).startswith("人")
            同じ人 = not 人の問い or (対象 and 対象 == _ならす(r.get("対象", "")))
            名指し = {i for i in 済の項目[no] if len(i) >= 4 and i in 字}
            重なり = (項目 & 済の項目[no]) | 名指し
            if 重なり and 同じ人:
                当たり = (no, r, f"同じ設定の項目 {'・'.join(sorted(重なり))}")
                break
            c = 含み(字, r.get("質問", ""))
            if c >= 近さの線:
                当たり = (no, r, f"字の重なり {c:.2f}")
                break
        if 当たり:
            answered[k] = f"{当たり[0]}（{当たり[2]}・答え {str(当たり[1].get('回答', ''))[:30]}）"
        else:
            checked[k] = f"照らした: 質問と回答 {len(行たち)} 行・答え済み {len(済)} 問"
    return {"answered": answered, "checked": checked}


def main(argv: list[str], stdin=None) -> int:
    ap = argparse.ArgumentParser(description="給与の問いを質問と回答の答え済みと照らす（qa-prior/1）")
    ap.add_argument("--rows", default=os.environ.get("PAYROLL_QA_ROWS"),
                    help="質問と回答 タブ 質問 の JSON（get_values の形）の path。既定は環境 PAYROLL_QA_ROWS")
    ap.add_argument("--company", default=os.environ.get("PAYROLL_QA_COMPANY") or None,
                    help="この会社の行と組の全社の行だけで照らす。既定は環境 PAYROLL_QA_COMPANY")
    ap.add_argument("--questions", help="文面の問い（1 行 1 問の file）。無ければ標準入力の qa-prior/1")
    a = ap.parse_args(argv)
    if not a.rows:
        print("質問と回答の表が渡されない（殻がタブ 質問 を読んで file に置き、環境 PAYROLL_QA_ROWS か --rows で渡す）＝照らせない",
              file=sys.stderr)
        return 2
    try:
        values = json.loads(Path(a.rows).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"質問と回答が読めない: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    if isinstance(values, dict):
        values = values.get("values", [])
    if not isinstance(values, list):
        print("質問と回答の JSON が表（行の並び）でない", file=sys.stderr)
        return 2
    miss = 足りない見出し(values)
    if miss:
        print(f"質問と回答の見出しに {'・'.join(miss)} が無い＝照らせない（タブ {タブ} の 1 行目を見る）", file=sys.stderr)
        return 2
    行たち = 行にする(values)
    if 知らない会社(行たち, a.company):
        名たち = sorted({str(r.get("会社", "")).strip() for r in 行たち} - {""})
        print(f"会社 {a.company!r} の行が質問と回答に 1 つも無い（在る会社: {'・'.join(名たち)}）＝照らせない"
              "（名を表の 会社 の欄と同じ字で渡す）", file=sys.stderr)
        return 2
    if a.questions:
        lines = [x.strip() for x in Path(a.questions).read_text(encoding="utf-8").splitlines() if x.strip()]
        qs = [{"key": f"L{i + 1}", "question": t} for i, t in enumerate(lines)]
    else:
        try:
            data = json.load(stdin or sys.stdin)
        except ValueError as e:
            print(f"標準入力が JSON でない: {e}", file=sys.stderr)
            return 2
        if not isinstance(data, dict) or data.get("format") != 形の名 or not isinstance(data.get("questions"), list) \
                or not all(isinstance(q, dict) and q.get("key") for q in data["questions"]):
            print(f"標準入力が {形の名} でない（check.mjs <page> --prior-input の出力を渡す）", file=sys.stderr)
            return 2
        qs = data["questions"]
    res = 照らす(qs, 行たち, a.company)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if a.questions and res["answered"]:
        for k, v in res["answered"].items():
            print(f"✗ {k}: 答え済み {v}＝文面から外す", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
