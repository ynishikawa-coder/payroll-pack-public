#!/usr/bin/env python3
"""前の答えを照らす口（給与の問い）: 先方へ出す問いを、質問と回答の答え済みと照らす。答え済みの問いは出せない。

なぜ在るか（根治・2026-11-17）: ある顧問先の月で、窓が答え済みの問いを新しい番号で先方へ出しかけた。確認ページの型の検査
（土台の qa-html の check.mjs）は「前の答えを照らす口」を持つが、給与の値の表にその命令が無く、給与の問いでは一度も照らして
いなかった。照らしの芯はパックのここ 1 か所に置き、値の表 `config/skill-values.json` の `docs-kit.qa-html.prior_check_cmd`
がこれを指す（どちらのアカウントの殻でも同じ照らし）。命令の約束は qa-html の §前の答えを照らす口（形 qa-prior/1）。

照らし方（答えが決まり切らない行〔分からない・不明・確かめる・確認中・打ち合わせ〕・「出し直し」の行・回答の空の行は答え済みに数えない
＝問いの番号ごとに一番下の行が正）:
  1. 同じ問いの番号に答えがある → 答え済み
  2. 番号が違っても、この問いの行の 反映先・答えで変わる項目と人 か問いの字に出る 2_マスタ の設定の項目が、答え済みの問いの
     反映先と重なる（人の問いは 対象 の人も同じ）→ 答え済み
  3. 問いの字の 2 字組の 8 割以上が答え済みの問いの字に在り、人の問いは対象の人も同じ（言い回しだけ変えた聞き直し）→ 答え済み
     （聞き直す時は、質問と回答のその問いの行の 理由 に「聞き直し: <前の問いの番号>・<訳>」と書く＝記録に残る形でだけ外せる）
  4. 答え済みでなく、上の 1〜3 の当たり方で決まり切らない前の答え（不明・確かめる など）に当たる → 詰め直し（何度目かを数え、
     出力の `詰め直し` に前の問いの番号と答えを添える）。同じ前の問いに当たる新しい問いが 2 つ以上あれば 2 つ目からは答え済みに
     数える（前の答えを添えて 1 つにまとめる＝同じ人の同じ日を何度も聞かない）。

止める形（2026-11-18・照らしが黙って空回りしない）: パックは今の型だけを読む（前の形の読み替えは寄せる道具の中＝`docs/設計/寄せる道具.md`）。
1 行目が見出しでない表（上に URL などの行がある）・前の見出し（ID）・今の形 `Q<6 桁>-<順>` でない問いの番号（`Q2026.11-05` など）・
今の形でない 聞き直し の番号は、訳と所を名指しして照らさずに止める（前は見出しが無いとだけ言うか、番号の形が違う行を別の問いと読み、
答え済みの問いをすり抜けさせた）。

パックは Drive を開かない。質問と回答（タブ 質問・get_values の形・1 行目が見出し）は殻が読んで file に置き、その path を渡す:
  確認ページ（check.mjs --run-prior が呼ぶ・標準入力に qa-prior/1）:
      環境 PAYROLL_QA_ROWS=<質問の表の JSON の path>・PAYROLL_QA_COMPANY=<会社>（任意）・PAYROLL_PACK_DIR=<パックの dir>
  手で: python3 確認ページ/前の答え.py --rows <path> [--company <会社>] [--questions <1 行 1 問の file>]
出力: {"answered": {鍵: "<前の問いの番号>（<訳>）"}, "checked": {鍵: "照らした: 質問と回答 N 行・答え済み M 問"},
      "詰め直し": {鍵: {"前の問い": [番号…], "前の答え": [字…], "回目": N}}}（詰め直しは checked の鍵にも訳を添える）。
exit: 0＝照らした（--questions の時は答え済みが 1 つでもあれば 2）／2＝照らせない（表が無い・読めない・見出しが無い・入力の形が違う・
  渡した会社の行が無くほかの会社の行がある＝名の打ち違い・上の 止める形）。
照らせない時は何も出さず 2 で終わる＝check.mjs が赤にする（黙って全部 checked にしない）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # パックの根（check.mjs が file を直に呼ぶ）
from 芯 import 字 as _字  # noqa: E402  字のそろえ方の正本（答え・番号・対象の字の揺れをそろえて比べる）

形の名 = "qa-prior/1"
タブ = "質問"
近さの線 = 0.8
分からない = "分からない"
出し直し = "出し直し"
# 答えが決まり切らない答えの頭（答え済みに数えない＝詰め直しの元）。設問.反映の照らし もここを読む（正本はここ 1 か所）
# 「確かめました。18:00 で数える」のような決まった答えを拾わないよう、確かめる の形は 決まっていない言い方だけ並べる
決まり切らない頭 = (分からない, "わからない", "不明", "確かめる", "確かめます", "確かめて", "確認中", "確認します", "確認して", "打ち合わせ")
番号の形 = re.compile(r"Q\d{6}-\d+")
聞き直し = re.compile(r"聞き直し[:：]\s*(Q[^\s・、,，;；（(]+)")
要る見出し = ("問いの番号", "質問", "回答")
# 型の前の見出し（今の名）。読み替えはしない＝見つけたら名指しして止める
前の見出し = {"ID": "問いの番号"}
見出しを探す行 = 5


def 決まり切らない(回答) -> bool:
    """答えの字が 分からない・不明・確かめる など決まり切らない答えか（答え済みに数えず、詰め直しの元にする）。
    頭だけでなく字の中を、字の揺れをそろえて見る（「まだ分からない」「今は不明」も決まり切らない＝聞き直しを止めない側）。"""
    return _字.含む(回答, 決まり切らない頭, 大小も=False)


def 鍵(no: str) -> str:
    """問いの番号 → 確認ページの問いの鍵（英数字と _ だけ）。"""
    return re.sub(r"[^0-9A-Za-z_]", "_", str(no).strip())


def _ならす(s: str) -> str:
    s = _字.そろえる(s, 大小も=False)
    return re.sub(r"[\s、。・,.!?？！「」『』（）()【】:：/／\-ー〜~]", "", s)


def 足りない見出し(values: list[list]) -> list[str]:
    """照らすのに要る見出しのうち、表の 1 行目に無い物（無ければ答え済み 0 で全部 checked＝黙って緑になる）。"""
    h = [str(x).strip() for x in (values[0] if values else [])]
    return [k for k in 要る見出し if k not in h]


def 見出しの訳(values: list[list]) -> str:
    """見出しが足りない時の訳（1 行目が見出しでない・前の見出し）。足りていれば空。"""
    miss = 足りない見出し(values)
    if not miss:
        return ""
    訳 = [f"見出しに {'・'.join(miss)} が無い"]
    for i, r in enumerate(values[1:見出しを探す行 + 1], start=2):
        if isinstance(r, list) and not 足りない見出し([r]):
            頭 = next((str(c).strip() for c in (values[0] or []) if str(c).strip()), "")
            訳.append(f"見出しは {i} 行目に在り 1 行目が見出しでない（1 行目: {頭[:40]!r}）＝見出しを 1 行目へ（上の行を消すか別のセルへ）")
            break
    h = {str(x).strip() for x in (values[0] if values else [])}
    前 = [f"{k}（今の名 {v}）" for k, v in 前の見出し.items() if k in h and v in miss]
    if 前:
        訳.append(f"前の見出し {'・'.join(前)}＝寄せる道具で今の型へ直す（パックは前の形を読み替えない）")
    return "・".join(訳)


def 読めない番号(行たち: list[dict]) -> list[str]:
    """今の形 Q<6 桁>-<順> でない問いの番号と、理由 の 聞き直し の番号（前の形 Q2026.11-05 など）。
    黙って別の問いと読むと答え済みの問いがすり抜ける＝見つけたら照らさずに止める。"""
    out = []
    for i, r in enumerate(行たち, start=2):
        no = str(r.get("問いの番号", "")).strip()
        if no and not 番号の形.fullmatch(no):
            out.append(f"{no!r}（問いの番号）")
        for w in 聞き直し.findall(str(r.get("理由", ""))):
            if not 番号の形.fullmatch(w):
                out.append(f"{w!r}（{no or '?'} の 理由 の 聞き直し）")
    return list(dict.fromkeys(out))


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
        if a and not 決まり切らない(a) and not _字.頭が(a, 出し直し):   # 出し直し→ は別の問いへ移った印
            out[no] = r
    return out


def 決まり切らない行(行たち: list[dict]) -> dict[str, list[dict]]:
    """問いの番号ごとの、答えが決まり切らない行の全部（何度聞いたかを数える）。一番下の行が答え済みの番号は外す。"""
    済 = 答え済みの行(行たち)
    out: dict[str, list[dict]] = {}
    for r in 行たち:
        no = str(r.get("問いの番号", "")).strip()
        if no and no not in 済 and 決まり切らない(r.get("回答")):
            out.setdefault(no, []).append(r)
    return out


def 設定の項目(字: str) -> set[str]:
    """反映先・答えで変わる項目の字から、2_マスタ の設定の項目の名を取り出す（`2_マスタ/会社/時間.始業前の打刻・休憩の表` →
    {始業前の打刻, 休憩の表}）。項目の頭の分け（時間. など）は外す。md の節・台帳（台帳/）は数えない（広すぎる）。"""
    out: set[str] = set()
    in_master = False
    for part in re.split(r"[・、,，;；\n]", str(字 or "")):
        part = part.strip()
        if not part:
            continue
        if ".md" in part:   # 決まりの md の節は設定の項目でない（広すぎる）＝ここで 2_マスタ の続きも切る
            in_master = False
            continue
        if "/" in part:
            in_master = "2_マスタ/" in part
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


def _当たり(k: str, 字: str, mine: dict, 候補: dict[str, dict], 鍵から: dict[str, str]) -> tuple | None:
    """同じ番号／同じ設定の項目（人の問いは対象の人も同じ）／字のほぼ同じ の順に、候補（番号 → 行）から当たる物を 1 つ。"""
    return next(_当たりたち(k, 字, mine, 候補, 鍵から), None)


def _当たりたち(k: str, 字: str, mine: dict, 候補: dict[str, dict], 鍵から: dict[str, str]):
    """候補（番号 → 行）のうち当たる物を全部（同じ番号を先に）。"""
    if k in 鍵から and 鍵から[k] in 候補:
        no = 鍵から[k]
        yield no, 候補[no], "同じ問いの番号"
    外す = set(聞き直し.findall(str(mine.get("理由", ""))))
    項目 = 設定の項目(mine.get("反映先", "")) | 設定の項目(mine.get("答えで変わる項目と人", ""))
    対象 = _ならす(mine.get("対象", ""))
    for no, r in 候補.items():
        if no in 外す or (k in 鍵から and 鍵から[k] == no):
            continue
        人の問い = _字.頭が(r.get("対象", ""), "人") or _字.頭が(mine.get("対象", ""), "人")
        同じ人 = not 人の問い or (対象 and 対象 == _ならす(r.get("対象", "")))
        前の項目 = 設定の項目(r.get("反映先", "")) | 設定の項目(r.get("答えで変わる項目と人", ""))
        名指し = {i for i in 前の項目 if len(i) >= 4 and i in 字}
        重なり = (項目 & 前の項目) | 名指し
        if 重なり and 同じ人:
            yield no, r, f"同じ設定の項目 {'・'.join(sorted(重なり))}"
            continue
        c = 含み(字, r.get("質問", ""))
        if c >= 近さの線 and (同じ人 or (not 対象 and _名指す(字, r.get("対象", "")))):
            # 人の問いは対象の人も同じ時だけ（別の人の同じ言い回しの問いを答え済みにしない）。この問いの行がまだ無い
            # （対象が分からない）時は、前の問いの対象の人の名が問いの字に在る時だけ
            yield no, r, f"字の重なり {c:.2f}"


def _名指す(字: str, 対象) -> bool:
    """前の問いの対象（`人 <名>`）の名が、問いの字に在るか（字の揺れと空白をそろえて見る）。名の無い対象は False。"""
    名 = _ならす(re.sub(r"^\s*人", "", _字.そろえる(対象, 大小も=False, 空白も=False)))
    return bool(名) and 名 in _ならす(字)


def 照らす(問いたち: list[dict], 行たち: list[dict], 会社: str | None = None) -> dict:
    """同じ番号の答え／同じ設定の項目に映った答え（人の問いは対象の人も同じ）／字のほぼ同じ問い の 3 つで答え済み。
    答え済みに当たらず、決まり切らない前の答え（不明・確かめる など）に当たる問いは 詰め直し（何度目か・前の答えを添える）。"""
    if 会社:
        行たち = [r for r in 行たち if str(r.get("会社", "")).strip() in (会社, "")]
    済 = 答え済みの行(行たち)
    未決 = 決まり切らない行(行たち)
    未決の下 = {no: rs[-1] for no, rs in 未決.items()}
    鍵から = {鍵(str(r.get("問いの番号", "")).strip()): str(r.get("問いの番号", "")).strip() for r in 行たち}
    自分 = {}
    for r in 行たち:   # 問いの番号ごとの一番下の行（この問いそのものの行＝反映先・対象・理由を読む）
        自分[鍵(r.get("問いの番号", ""))] = r
    answered, checked, 詰め直し = {}, {}, {}
    まとめ先: dict[str, str] = {}   # 前の決まり切らない問いの番号 → それを詰め直す今の問いの鍵（1 つにまとめる）
    for q in 問いたち:
        k = q["key"]
        字 = q.get("question", "") or ""
        mine = 自分.get(k) or {}
        当たり = _当たり(k, 字, mine, 済, 鍵から)
        if 当たり:
            訳 = "" if 当たり[2] == "同じ問いの番号" else f"{当たり[2]}・答え "
            answered[k] = f"{当たり[0]}（{訳}{str(当たり[1].get('回答', ''))[:30]}）"
            continue
        当たりたち = list(_当たりたち(k, 字, mine, 未決の下, 鍵から))
        if 当たりたち:
            nos = [x[0] for x in 当たりたち]
            先 = next((まとめ先[no] for no in nos if no in まとめ先 and まとめ先[no] != k), None)
            if 先:
                answered[k] = f"{nos[0]}（詰め直しは {先} に 1 つにまとめる・前の答え {str(当たりたち[0][1].get('回答', ''))[:30]}）"
                continue
            for no in nos:
                まとめ先[no] = k
            前の行 = [r for no in nos for r in 未決[no]]
            # 何度目か: 当たった前の問いを聞いた行の数（同じ番号の送り直しも数える）＋今回。今の問い自身の番号の行が在れば今回は数えない
            回目 = len(前の行) + (0 if 鍵から.get(k) in nos else 1)
            詰め直し[k] = {"前の問い": nos, "前の答え": [str(r.get("回答", "")).strip()[:60] for r in 前の行], "回目": 回目}
            checked[k] = (f"照らした: 質問と回答 {len(行たち)} 行・答え済み {len(済)} 問・詰め直し {回目} 回目"
                          f"（{'・'.join(nos)}・{当たりたち[0][2]}・前の答え {'／'.join(詰め直し[k]['前の答え'])[:60]}）＝前の答えを添えて聞く")
            continue
        checked[k] = f"照らした: 質問と回答 {len(行たち)} 行・答え済み {len(済)} 問"
    return {"answered": answered, "checked": checked, "詰め直し": 詰め直し}


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
    訳 = 見出しの訳(values)
    if 訳:
        print(f"質問と回答の{訳}＝照らせない（タブ {タブ} の 1 行目を見る）", file=sys.stderr)
        return 2
    行たち = 行にする(values)
    悪い = 読めない番号(行たち)
    if 悪い:
        print(f"質問と回答に今の形（Q<支給年月 6 桁>-<順>）でない問いの番号: {'・'.join(悪い[:5])}"
              f"{f' ほか {len(悪い) - 5} 件' if len(悪い) > 5 else ''}＝照らせない（別の問いと読むと答え済みがすり抜ける。"
              "寄せる道具で今の形へ直す）", file=sys.stderr)
        return 2
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
