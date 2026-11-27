"""確認ページ — 質問と回答の行から、配る用の 1 枚の自己完結 HTML と、その名・置き場・貼り戻し・管理表の 1 行を返す。

正本は質問と回答。確認ページは道具が起こす表示と配る用の写し（置き場と名の形の正本は 初期設定/型.json の 木・名の形）。
HTML は qa-html の 1 つの型（土台 docs-kit の skill qa-html の型。repo に写さず、入った docs-kit の check.mjs の `--template` で毎回読む）で起こし、
答えは型の答えの形 qa-html/2（問いの鍵・版・受付番号）で受けて、鍵で質問と回答の行へ戻す。
この道具は Drive を開かない。問いの一覧を受けて文字列を返すだけで、置くのは殻（環境の口）。
返す HTML は外へ通信しない（外の script・style・画像・fetch を持たない）。
"""
from __future__ import annotations

import datetime as _dt
import functools
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

ここ = Path(__file__).resolve().parent
根 = ここ.parent
if str(根) not in sys.path:
    sys.path.insert(0, str(根))


def _読み込む(名: str, path: Path):
    s = importlib.util.spec_from_file_location(名, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


段 = _読み込む("確認ページ_段の解決", 根 / "初期設定" / "段の解決.py")
型 = _読み込む("確認ページ_型の口", 根 / "初期設定" / "型の口.py")
_表 = _読み込む("確認ページ_管理表", 根 / "管理表" / "管理表.py")   # 状況の字の正本（管理表/型.json の 値の役）
表 = _表   # 管理表の口（ほかの file から状況の字を引く名）
取り下げ = "取り下げ"   # 問いを下げた行の回答の頭（`取り下げ→<訳>`・書くのは 月次/問いの取り下げ.py・設問.閉じた頭 と同じ字）
取り下げの頭 = 取り下げ + "→"

from 芯 import 支給月の字  # noqa: E402  (支給月の字の読み書きの正本)
from 芯.計算 import 暦  # noqa: E402  (締めた期間の式を 1 か所に)



def qa_htmlの道具() -> Path:
    """土台の qa-html の check.mjs の path（型・検査・答えの形の正本・写さず直に読む＝土台の qa-html の SKILL.md §配り方）。

    CI は環境の QA_HTML_CHECK（ci.yml が土台の main の先端から取って渡す）。窓は Claude Code の台帳
    （<CLAUDE_CONFIG_DIR か ~/.claude>/plugins/installed_plugins.json）の docs-kit の installPath（今入っている 1 つ）。
    plugin の cache の「新しい物」は拾わない。見つからない・2 つに割れる時は止める（別の版の型で起こさない）。
    """
    env = os.environ.get("QA_HTML_CHECK", "")
    if env:
        if Path(env).is_file():
            return Path(env)
        raise FileNotFoundError(f"QA_HTML_CHECK の file が無い: {env}")
    台帳 = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "plugins" / "installed_plugins.json"
    try:
        入った = json.loads(台帳.read_text(encoding="utf-8")).get("plugins") or {}
    except (OSError, ValueError, AttributeError):
        入った = {}
    在る = sorted({str(Path(行["installPath"]) / "skills" / "qa-html" / "check.mjs")
                 for 名, 行たち in 入った.items() if str(名).split("@")[0] == "docs-kit"
                 for 行 in (行たち if isinstance(行たち, list) else []) if isinstance(行, dict) and 行.get("installPath")})
    在る = [p for p in 在る if Path(p).is_file()]
    if len(在る) == 1:
        return Path(在る[0])
    if 在る:
        raise FileNotFoundError(f"入った docs-kit が {len(在る)} つに割れている（どれの型か決まらない）: {在る}")
    raise FileNotFoundError("土台の qa-html の検査（plugin docs-kit の skills/qa-html/check.mjs）が見つからない。"
                            "窓は plugin docs-kit を入れる・CI は QA_HTML_CHECK に土台の main の check.mjs を渡す（型の写しは repo に置かない）")


@functools.lru_cache(maxsize=None)
def _型を読む(道具: str) -> str:
    node = shutil.which("node")
    if not node:
        raise FileNotFoundError("node が無く、土台の qa-html の型を読めない（check.mjs --template）")
    p = subprocess.run([node, 道具, "--template"], capture_output=True, text=True, timeout=60)
    if p.returncode != 0 or "<!--qa:css-->" not in p.stdout:
        raise ValueError(f"土台の check.mjs が型を返さない（--template を知らない古い docs-kit か壊れた）: {道具}: {p.stderr.strip()[-200:]}")
    return p.stdout


def 雛形を読む() -> str:
    """qa-html の 1 つの型（土台の正本そのもの）。qa:css・qa:js・qa:foot は 1 字も変えずに使う。"""
    return _型を読む(str(qa_htmlの道具()))


def ページの検査(html: str) -> list[str]:
    """作った 1 枚を土台の qa-html の検査（型を返した同じ check.mjs・`<file> --json`）に通し、赤の訳の並びを返す（空＝緑）。

    作る側と確かめる側が別の約束を持たない（前は資料のリンクの URL を作る側が独自の正規表現で通し、検査が拒む `&` を
    許していた＝作ったのに配れない 1 枚が出た）＝ページの決まりの正本は check.mjs の 1 か所。値の表は repo の根の
    config/skill-values.json（なぜ聞くかの給与の語）を渡す。前の答えの照らし（prior_check_cmd）は質問と回答の表が要る＝
    表を持たない 作る では当てず、殻が配る前に `--run-prior` で当てる（その鍵だけを外した値の表を渡す）。
    道具が無い・node が無い時は型を読む時（--template）と同じく止まる。検査が働けない（終わりの値 2・JSON でない）時も止める。"""
    道具 = str(qa_htmlの道具())
    node = shutil.which("node")
    if not node:
        raise FileNotFoundError("node が無く、土台の qa-html の検査を当てられない（check.mjs <file> --json）")
    値 = json.loads((根 / "config" / "skill-values.json").read_text(encoding="utf-8"))
    ((値.get("docs-kit") or {}).get("qa-html") or {}).pop("prior_check_cmd", None)
    with tempfile.TemporaryDirectory() as d:
        f, v = Path(d) / "確認.html", Path(d) / "skill-values.json"
        f.write_text(html, encoding="utf-8")
        v.write_text(json.dumps(値, ensure_ascii=False), encoding="utf-8")
        p = subprocess.run([node, 道具, str(f), "--json", "--values", str(v)], capture_output=True, text=True, timeout=120, cwd=d)
    try:
        結果 = json.loads(p.stdout) if p.returncode in (0, 1) else None
    except ValueError:
        結果 = None
    if not isinstance(結果, dict) or not isinstance(結果.get("red"), list):
        raise ValueError(f"土台の check.mjs がページを照らせない（終わりの値 {p.returncode}）: {道具}: {(p.stderr or p.stdout).strip()[-300:]}")
    return [str(x) for x in 結果["red"]]


def _資料を名指す(赤: list[str], 資料: list[dict]) -> list[str]:
    """検査の赤が指す読んだ資料（鍵 d1… か href の URL）に、資料の名と URL の全文を添える（どの資料のリンクを直すかが分かる＝
    行の `資料のリンク` か 読んだ資料 の url を直してから作り直す）。"""
    out = []
    for x in 赤:
        h = re.search(r'href="([^"]+)', x)   # 検査は要素の頭だけを見せる＝見えた所から始まる URL の資料
        当たる = [d for d in 資料 if d.get("url") and (f"読んだ資料 {d['鍵']} " in x
                                                    or (h and escape(d["url"], True).startswith(h.group(1))))]
        out.append(x + "".join(f"（読んだ資料「{d['名']}」の url: {d['url']}）" for d in 当たる))
    return out


既定の支給の月 = "翌月"  # 初期設定/項目.json の 支払.支給の月 の既定・芯/計算/要る値 と同じ

用たち = ("立ち上げ", "毎月")
宛先たち = ("send", "copy", "artifact")   # 送る＝配る口へ／写す＝貼り戻しの字／確認のページ（Artifact）
形たち = ("choose", "mismatch", "fact", "judge")
まとまりたち = ("rule", "person", "once", "later")   # 会社の決まり → 人ごとの事実 → 今回だけの事 → 先に決めておきたい事（この順・later はいつも最後）
# 問いの 2 種類（オーナーの決定 2026-11-16・正本は docs/設計/設問の作り方.md §2）。1 枚の中で前半＝会社の決まり・後半＝原本。
# 会社の決まり＝まとまり rule・原本＝person と once（並びは qa-html の rule → person → once のまま 2 部に分かれる）
種類たち = ("会社の決まり", "原本")
_種類のまとまり = {"会社の決まり": ("rule", "later"), "原本": ("person", "once", "later")}
# まだ起きていない場面の問い（今月の原本で当たる人がいない決まり）の 何について の「いつ」（初期設定/設問.py の 後でのいつ と同じ字）
後でのいつ = "当たる人が出た時"
_道具の都合の字 = re.compile(r"文字の種類|文字コード|エンコード|番号の付け方|採番|置き場|フォルダ|ファイルの名|ファイル名|列の並び|CSV の形|CSVの形|シートの形")
_前の問いの字 = re.compile(r"前の問い|上の問い|前の答え|ほかの問いの答え|別の問いの答え")
見当のとおり = "見当のとおり"   # 前の版の行の語（読めば「見込みのとおり」・見込みの別枠が無ければ赤）
推奨の印 = "（推奨）"   # 前の版の行の印（読めば外す・付いていれば検査が赤＝おすすめの印は出さない）
# qa-html/2 の答えの形と、フォームの項目の名（型の約束）
答えの形 = "qa-html/2"
自由記入 = "__自由記入__"
版の名 = "__版__"
受付番号の名 = "__受付番号__"
# 受付番号の形の正本（qa-html の型: R<YYMMDD>-<英数 4 字>）。月次/例の確かめ.py も例の確かめの出所をここで照らす
受付番号の形 = re.compile(r"R\d{6}-[A-Z0-9]{4}")
分からない = "__unknown__"
分からないの字 = "分からない・確かめてから答える"   # 型の字のまま（検査が見る）
分からないの語 = "分からない"   # 質問と回答の 回答 に書く語
当てはまらない = "当てはまらない"
# 形ごとに道具が後ろへ足す選択肢（ひとことに書かせる選択肢がもうあれば足さない）。fact は「当てはまらない」
足す選択肢 = {"choose": "ほかの答え", "mismatch": "ほかの答え", "judge": "別の決め方"}
# 問いの箱（何が無いか の頭の字・正本は docs/設計/設問の作り方.md）と、形が無い行の既定の形
その月だけの物 = "その月だけの物"
箱の既定の形 = {"読み方": "choose", "法の線": "choose", その月だけの物: "fact"}
その月だけの物の当てはまらない = "この月は払う物・引く物・人の変わりが 1 つも無い"
# この答えで変わる事（small.chg）の既定（設問が出す決まった語）。行の `変わる事` か選択肢の {見出し, 変わる事} が勝つ
変わる事の既定 = {
    "原本を送る": "資料を受け取るまで、この値は確定しません",
    "決まりは無い": "決まりの無い物として計算します",
    "法の線に直して払う": "法の最低線に合わせて計算し直します",
    "今の払い方のまま払う": "会社の決まりのまま計算し、法律との差は毎月お知らせします",
    "読んだとおり": "上の読んだ物のとおり計算します",
}
# なぜ聞くか（data-why）の決まった 4 文（qa-html の check.mjs の RULES.why と同じ字）と、行の 理由 の日本語
理由の文 = {
    "mismatch": "資料どうしで食い違っています",
    "missing": "資料に書いてありません",
    "law": "今の決まりが法律の決まりと合っていません",
    "once": "今回だけの事を確かめます",
}
# 給与の語への言い換えは repo の根の config/skill-values.json の docs-kit.qa-html.why（check.mjs も同じ所を読む＝文は 1 か所）
理由の文.update(json.loads((根 / "config" / "skill-values.json").read_text(encoding="utf-8"))
              .get("docs-kit", {}).get("qa-html", {}).get("why", {}))
理由の語 = {"食い違い": "mismatch", "書いてない": "missing", "法の線": "law", "今回だけ": "once"}
対象の上限 = 3
枚の問いの上限 = 12   # qa-html の check.mjs の questions_per_page と同じ（超えたら 作る が同じ版の枚に分ける）
見つけた事の字の上限 = 60   # qa-html の check.mjs の known_line_chars と同じ
くわしくの行の上限 = 3
切り抜きの上限 = 2
分かっている事の行の上限 = 2
# 選択肢の頭の記号（A・B・①・1. など）と、記号で選択肢を指す字（qa-html の check.mjs の option_symbol・symbol_ref と同じ）
記号の頭 = re.compile(r"^\s*(?:案\s*[A-Za-zＡ-Ｚ0-9０-９]|[A-Za-zＡ-Ｚａ-ｚ](?:\s*[.．:：、)）]|\s+)|[0-9０-９]{1,2}\s*[.．:：、)）](?![0-9０-９])|[①-⑳])"
                  r"|^\s*[(（](?:[A-Za-zＡ-Ｚ]|[0-9]{1,2})[)）]")
記号で指す = re.compile(r"(?<![A-Za-z0-9])(?:案\s*)?[A-DＡ-Ｄ]\s*(?:なら|の場合|案|を選)")
# 既定で見る内部の言葉（呼ぶ側が 内部の言葉 の引数で足す）。顧客の語はここに書かない。
# Drive の物の名（質問と回答・マスタ・台帳・決まり）は 型.json の 木 から読む（写さない）
既定の内部の言葉 = ("立ち上げ", "照合", "逆算", "道具", "部品",
                 型.名("質問と回答"), 型.名("マスタ"), 型.台帳の名().split("<", 1)[0], 型.名("決まり"), ".md")
# header と受付の既定の字（殻が事務所の設定から渡せば勝つ）
既定の色 = "#0f6e66"
# qa-html の check.mjs の limits（evidence・where_chars・quote_chars・reading_line_chars・estimate_chars・basis_chars）と同じ数
根拠の上限 = {"数": 3, "場所": 60, "原文": 80, "読みの行": 80, "見込み": 40, "拠り所": 60}
既定の答えるまでの扱い = "答えが届くまで、この点は確定せずにお待ちします。"
既定のまとまりの1行 = {"rule": "前半・会社の決まり: 資料で決めきれない所と法律と違う所です",
                   "person": "後半・原本の確かめ: 人ごとの事で資料に書いていなかった所です",
                   "once": "今回だけの事を確かめます",
                   "later": "今月の計算には関係しません。起きた時の決め方を先に伺います。"}   # later は qa-html の決まった文（check.mjs の later_lead）
既定の後半の頭 = "後半・原本の確かめ: "   # 後半（原本）の最初のまとまりの 1 行の頭（person が無く once から始まる時）
既定のまとまりの見出し = {"person": "原本・人ごとの事", "once": "原本・今回だけの事", "later": "先に決めておきたい事"}   # data-glabel（毎月の once は「原本・M 月分だけの事」）
既定の宛名 = "ご担当者様"
# 型から外した欄（2026-11-14 オーナー決定・qa-html の型が宛先で変えるのは宛名と会社の色だけ）
外した欄 = ("差出人", "連絡先")
既定の期限の字 = "分かる所からお答えください。"
既定のこの後_毎月 = "いただいた答えで給与を計算し、結果をお送りします。"
既定のこの後_立ち上げ = "いただいた答えで給与計算の設定を決め、最初の月の結果をお送りします。"


# ── 名と置き場 ─────────────────────────────────────────────

def _支給の月を読む(支給の月) -> str | None:
    """`支払.支給の月` の字 → 当月・翌月・翌々月（段の解決 と同じそろえ方）。空・読めなければ None。"""
    if 支給の月 is None or not str(支給の月).strip():
        return None
    return 段.字をそろえる("支払.支給の月", 支給の月)


def 支給月の名と知らせ(支給月: str, 支給の月=None) -> tuple[str, list[str]]:
    """`YYYY.MM支給` か `YYYY.MM支給（M月分）` → (`YYYY.MM支給（M月分）`, 知らせ)。

    M は締めた期間の終わりの月（芯/計算/暦.期間 と同じ式）: 会社の `支払.支給の月` が 当月 なら支給月・翌月 なら前の月・
    翌々月 なら 2 つ前の月。支給の月が渡されない・読めない時は拒まず知らせ、名に（M月分）があればそれを、無ければ
    既定の 翌月 で出す。支給の月が分かっていて（M月分）が合わない時は ValueError。"""
    m = re.fullmatch(r"(.+?支給)(?:（(\d{1,2})月分）)?", 支給月.strip())
    頭 = m.group(1) if m else ""
    if not re.fullmatch(r"\d{4}\.\d{2}支給", 頭):
        raise ValueError(f"支給月 {支給月!r} は YYYY.MM支給 の形でない")
    if not 支給月の字.その形か(頭, "殻"):
        raise ValueError(f"支給月 {支給月!r} の月が 1〜12 でない")
    書いた = int(m.group(2)) if m.group(2) else None
    中 = 支給月の字.そろえる(頭, "中")

    def 月分(語: str) -> int:
        return 暦.期間(中, "末", 語)[1].month

    語 = _支給の月を読む(支給の月)
    知らせ = []
    if 語 is not None:
        M = 月分(語)
        if 書いた is not None and 書いた != M:
            raise ValueError(f"支給月 {支給月!r} の（M月分）が 支払.支給の月＝{語} の {M} 月分でない")
    else:
        何 = "渡されていない" if 支給の月 is None or not str(支給の月).strip() else f"{str(支給の月).strip()!r} が読めない"
        合う = {月分(w): w for w in 段.支給の月の語}
        if 書いた is not None and 書いた in 合う:
            M = 書いた
            知らせ.append(f"支払.支給の月 が{何}。名の（{M}月分）はそのまま使った（{合う[M]} に当たる）")
        else:
            M = 月分(既定の支給の月)
            外れ = f"名の（{書いた}月分）は 当月〜翌々月 のどれにも当たらない。" if 書いた is not None else ""
            知らせ.append(f"支払.支給の月 が{何}。{外れ}既定の {既定の支給の月} で {M} 月分とした")
    return 支給月の字.字にする(*支給月の字.読む(頭), "置き場", 月分=M), 知らせ   # 置き場の字を組むのは正本だけ


def 支給月の名(支給月: str, 支給の月=None) -> str:
    """`支給月の名と知らせ` の名だけ（知らせは捨てる・`作る` は知らせも返す）。"""
    return 支給月の名と知らせ(支給月, 支給の月)[0]


# ── 名と置き場（会社の Drive の形・2026-11-18 オーナーと確定した設計の決定 5） ──
# 会社の確認事項のページの名は `確認事項_<組>_<支給月>_v<版>.html`（事務所の担当者に聞くページの写し）。聞く相手はいつも
# 事務所の担当者 1 人（決定 19）。置き場と前の版の行き先の正本は 初期設定/型.json の 木.確認事項の置き場 の 1 か所で、
# ここは 型の口 から読む（写さない＝型と道具が食い違えない）。読めない・形が違えば読み込みで止まる。
会社の印 = 型.組の印()   # 外の口（plugins/payroll-agent/bin/パックの場所.py が読む＝_ を付けない）。型.json の 置き場（`10_会社/<組>`）と同じ印＝紙と道具で名を分けない
下書きの頭 = 型.名の形("確認事項")["下書きの頭"]
名の頭 = 型.名の形("確認事項")["形"].split("_", 1)[0]


def 置き場の表を確かめる(表) -> dict[str, tuple[str, str]]:
    """型の口.確認事項の置き場の表() → {"<組>": (置き場, 前の版の置き場), "事務所": (…)} を確かめて返す。
    行が 2 つ（`<組>` と `事務所`）でない・置き場が `/` で終わらない・`<組>` の行に `<組>` が無い時は ValueError
    （読めない表から置き場を推し量らない）。"""
    if not isinstance(表, dict):
        raise ValueError(f"確認事項の置き場の表は dict で受ける: {表!r}")
    out = {}
    for k, r in 表.items():
        r = tuple(r) if isinstance(r, (list, tuple)) else r
        if not isinstance(r, tuple) or len(r) != 2 or not all(isinstance(c, str) and c.endswith("/") for c in r):
            raise ValueError(f"確認事項の置き場の表の行が読めない（置き場と前の版の 2 つ・どちらも / で終わる）: {k}: {r!r}")
        out[k] = r
    if set(out) != {会社の印, "事務所"}:
        raise ValueError(f"確認事項の置き場の表の行は `{会社の印}` と `事務所` の 2 つ: {sorted(out)}")
    if not all(会社の印 in c for c in out[会社の印]) or any(会社の印 in c for c in out["事務所"]):
        raise ValueError(f"確認事項の置き場の表: `{会社の印}` の行だけが {会社の印} を持つ: {out}")
    return out


置き場の表 = 置き場の表を確かめる(型.確認事項の置き場の表())
# 会社の置き場と前の版の置き場のフォルダの名（給与エージェントの見張り・初期設定/始める が読む）。表から引く
置き場の名 = 置き場の表[会社の印][0].rstrip("/").rsplit("/", 1)[-1]
履歴の名 = 置き場の表[会社の印][1].rstrip("/").rsplit("/", 1)[-1]
# 確認事項を置いてよいフォルダの名を、問いの種類（`<組>`・`事務所`）ごとに（給与エージェントの見張りが読む＝名の 組 が
# 事務所なら 事務所 の名・ほかは `<組>` の名のフォルダにだけ置ける）。表から引く
置き場の名たち = {k: v[0].rstrip("/").rsplit("/", 1)[-1] for k, v in 置き場の表.items()}
# 置き場に在ってよい名の形（配った版と下書き）。組は字のまま・支給月は `YYYY.MM支給（M月分）`・版と枚は 1 から
名の形 = re.compile(rf"(?P<下書き>{re.escape(下書きの頭)})?{re.escape(名の頭)}_(?P<組>[^/\\]+?)_(?P<月>\d{{4}}\.\d{{2}}支給（\d{{1,2}}月分）)"
                   r"_v(?P<版>[1-9]\d*)(?:-(?P<枚>[1-9]\d*))?\.html")
# 前の形の名の頭（月ごとに切った確認ページの置き場の頃の名 確認ページ_…）
古い名の頭 = "確認ページ"
古い名の形 = re.compile(rf"(?:{re.escape(下書きの頭)})?{re.escape(古い名の頭)}_.*")
# 確認ページの名の頭（今の形と前の形・下書きも）。給与エージェントの見張りがパックの場所から読む（写さない）
名の頭たち = tuple(f"{d}{h}_" for h in (名の頭, 古い名の頭) for d in ("", 下書きの頭))


def _表の所(組: str, 列: int) -> str:
    if not 組 or "/" in 組 or "\\" in 組:
        raise ValueError(f"組 {組!r} が置き場に使えない")
    if 組 == "事務所":
        return 置き場の表["事務所"][列]
    return 置き場の表[会社の印][列].replace(会社の印, 組)


def 置き場(組: str, 支給月: str, 支給の月=None) -> str:
    """確認事項のページを置くフォルダ（型.json の 木.確認事項の置き場: 会社は `10_会社/<組>/8_確認事項/`・
    組が「事務所」なら表の「事務所」の行）。月のフォルダは切らない（支給月は名が持つ）。
    支給月は名と同じに確かめる（会社の `支払.支給の月` と合わなければ ValueError）。"""
    支給月の名(支給月, 支給の月)
    return _表の所(組, 0)


def 名(組: str, 支給月: str, 版: int, 下書き: bool = False, 支給の月=None, 枚: int | None = None) -> str:
    """確認事項のページの名 `確認事項_<組>_<支給月の名>_v<版>.html`。1 回に配る問いが 1 枚の上限を超えて分けた時は
    `_v<版>-<枚>.html`（同じ版の 1 枚目・2 枚目＝版は配り直しの数・枚は分けた何枚目）。配る前は頭に `下書き_`。"""
    if not isinstance(版, int) or isinstance(版, bool) or 版 < 1:
        raise ValueError(f"版 {版!r} は 1 から")
    if 枚 is not None and (not isinstance(枚, int) or isinstance(枚, bool) or 枚 < 1):
        raise ValueError(f"枚 {枚!r} は 1 から")
    if not 組 or "/" in 組 or "\\" in 組:
        raise ValueError(f"組 {組!r} が名に使えない")
    本 = f"{名の頭}_{組}_{支給月の名(支給月, 支給の月)}_v{版}" + (f"-{枚}" if 枚 else "") + ".html"
    if not 名の形.fullmatch(本):   # 作った名が置き場の形から外れたら出さない（組の字が形を壊す時など）
        raise ValueError(f"名 {本!r} が確認事項の名の形に合わない")
    return 下書きの頭 + 本 if 下書き else 本


# ── 確認事項の置き場（8_確認事項/）と前の版の置き場（9_履歴/）の名の読み分け ──
# 正本はここ 1 つ。次の版（版を数える）と 道具/寄せ/当てる.py の 確認事項の前の形を移す（前の形を片付ける）が同じ表を読む（写さない）。
#   今の形: `名の形`。版を数え、動かさない。
#   前の名: 名の頭が前の形（確認ページ_）か、支給月の字が前の字（（M月分）の無い `YYYY.MM支給`・`YYYY-MM` など 芯/支給月の字 が読む字）の名
#     ＝組・支給月（年月）・版が読める。版に数え（番号を戻さない）、寄せの移しが 9_履歴/ へ移す（止めない）。
#   読めない物: 置き場の下のフォルダ（月ごとに切った前の置き場）・ほかの名（寄せ_人が見る物_…・写しの「(1)」・版の読めない名 など）
#     ＝中に前の版が在り得て版を数えられない。寄せの移しが 9_履歴/ へ移す（消さない）。次の版は寄せの移しを当てるまで版を付けない。
置き場の名の類 = {
    "今の形": "版を数える・動かさない",
    "前の名": "版を数える・寄せの移しが 9_履歴/ へ移す",
    "読めない物": "版を数えられない・寄せの移しが 9_履歴/ へ移す",
}
前の名の形 = re.compile(rf"(?P<下書き>{re.escape(下書きの頭)})?(?:{re.escape(名の頭)}|{re.escape(古い名の頭)})_(?P<組>[^/\\]+?)"
                     r"_(?P<月>[^_/\\]+)_v(?P<版>[1-9]\d*)(?:-(?P<枚>[1-9]\d*))?\.html")
寄せの移しを当てる = (f"道具/寄せ の寄せ（上げ直しでもよい）を当てる＝{置き場の名}/ の今の形でない物を {履歴の名}/ へ"
               f"`消す_<日>_<元の名>` で移す（消さない・版は {履歴の名}/ でも数える）")


def _片付け方(組: str) -> str:
    """今の形でない物の片付け方（次の版・作る の知らせと止める時の答え）。会社の置き場は寄せの移し（当てる.確認事項の前の形を移す）が
    この表で片付ける。事務所の置き場（寄せの移しの外）は同じ形で置き場の {履歴の名}/ へ移す。"""
    if 組 != "事務所":
        return 寄せの移しを当てる
    return (f"{_表の所(組, 0)} の今の形でない確認事項を {_表の所(組, 1)} へ `消す_<日>_<元の名>` で移す"
            f"（消さない・寄せの移しは会社の {置き場の名}/ だけを見る・版は {履歴の名}/ でも数える）")


def _月の年月(月: str) -> tuple[int, int] | None:
    """名の中の支給月の字（今の字 `YYYY.MM支給（M月分）`・前の字 `YYYY.MM支給`・`YYYY-MM` など）→ (年, 月)。読めなければ None。"""
    m = re.fullmatch(r"(.+?)(?:（\d{1,2}月分）)?", 月)
    頭 = m.group(1) if m else ""
    return 支給月の字.読む(頭) if re.fullmatch(r"\d{4}[.\-]\d{2}(?:支給)?", 頭) else None


def 置き場の名を分ける(名) -> tuple[str, dict | None]:
    """確認事項の置き場の 1 つの名 → (類, 読み)。類は `置き場の名の類` の 1 つ。読みは 今の形・前の名 の時
    {下書き, 組, 支給月, 年月, 版, 枚}（支給月は名の字のまま・年月は (年, 月)）、読めない物 は None。フォルダは名の末の `/`。"""
    n = str(名)
    for 類, 形 in (("今の形", 名の形), ("前の名", 前の名の形)):
        m = 形.fullmatch(n)
        年月 = _月の年月(m["月"]) if m else None
        if 年月:
            return 類, {"下書き": bool(m["下書き"]), "組": m["組"], "支給月": m["月"], "年月": 年月, "版": int(m["版"]),
                       "枚": int(m["枚"]) if m["枚"] else None}
    return "読めない物", None


def ほかの組の名か(名, 組: str) -> bool:
    """置き場の 1 つの名が読めた名（今の形も前の名も）で、組が `組` でないか＝置き違い（その組の置き場の物）。
    組の照らしはここ 1 か所（次の版 が止める置き違いと、寄せの移し〔道具/寄せ/当てる.確認事項の前の形を移す〕が移さない物は同じ）。
    読めない物は組を読めない＝False（読めない物として別に扱う）。"""
    類, r = 置き場の名を分ける(名)
    return 類 != "読めない物" and r["組"] != 組


def 名を読む(名: str) -> dict:
    """置き場の今の形の名 → {下書き, 組, 支給月, 版, 枚}。今の形でなければ ValueError（前の名・読めない物は寄せの移しで片付ける）。"""
    n = str(名)
    類, r = 置き場の名を分ける(n)
    if 類 != "今の形":
        raise ValueError(f"{n!r} は {置き場の名}/ の今の名の形 `{名の頭}_<組>_<YYYY.MM支給（M月分）>_v<版>.html` でない"
                         f"（{類}: {置き場の名の類[類]}）。{寄せの移しを当てる}・事務所の置き場は {_片付け方('事務所')}")
    return {k: r[k] for k in ("下書き", "組", "支給月", "版", "枚")}


def _名の並びか(何: str, 並び) -> None:
    """前の版の名の並びを必ず受ける（前の版が無ければ空の並び `[]`）。省く・None・1 つの字・dict は止める＝前の版を見ずに黙って v1 を付けない。"""
    if not isinstance(並び, (list, tuple)):   # None・字・dict・使い切る並び（generator）も止める
        raise ValueError(f"{何} を名の並びで渡す（前の版が無ければ []）。渡さないと前の版の番号を見られない＝版を付けない"
                         f"（受けた物: {並び!r}）")
    if any(not isinstance(n, str) for n in 並び):
        raise ValueError(f"{何} の中身は名の字だけで渡す（Drive の一覧の dict などは名の字へ直す）。字でない物は版を読めない"
                         f"＝黙って v1 を付けない（受けた物: {並び!r}）")


# 9_履歴/ へ移した物（確認事項の前の版・寄せと配りの写し）の名 `消す_<消す日>_<元の名>` の形の正本はここ 1 か所。
# 組む側（差し替え・配る手順・道具/寄せ/当てる.py の写し）も読む側（次の版・道具/寄せ/見回り.py の期限と写し）もここから引く。
消す名の頭 = "消す_"
消す名の日 = r"\d{4}-\d{2}-\d{2}"
消す名の形 = re.compile(re.escape(消す名の頭) + r"(?P<日>" + 消す名の日 + r")_(?P<元>[^/]+/?)")


def 消す名(消す日, 元の名: str) -> str:
    """`消す_<消す日 YYYY-MM-DD>_<元の名>`（元の名は / を含まない 1 つの名。フォルダは末の / ごと）。形に合わなければ拒む。"""
    名 = f"{消す名の頭}{消す日}_{元の名}"
    m = 消す名の形.fullmatch(名)
    if not m:
        raise ValueError(f"消す名 {名!r} が {消す名の頭}<YYYY-MM-DD>_<元の名> の形でない")
    try:
        _dt.date.fromisoformat(m.group("日"))
    except ValueError as e:
        raise ValueError(f"消す名 {名!r} の消す日が暦に無い日") from e
    return 名


def 消す名を読む(名: str) -> tuple[str, str] | None:
    """`消す_<日>_<元の名>` を (日, 元の名) に読む（形でなければ None）。"""
    m = 消す名の形.fullmatch(名) if isinstance(名, str) else None
    return (m.group("日"), m.group("元")) if m else None


def 履歴の名を分ける(名) -> tuple[str, dict | None]:
    """前の版の置き場（9_履歴/）の 1 つの名 → (類, 読み)。差し替え・寄せの移しが付ける `消す_<日>_` を外して `置き場の名を分ける` で読む
    （置き場と同じ表＝今の形も前の名も同じに数える）。9_履歴/ はほかの物の前の版も並ぶ所＝読めない物は確認事項でない物。"""
    消す = 消す名を読む(str(名))
    return 置き場の名を分ける(消す[1] if 消す else 名)


def 次の版(組: str, 支給月: str, 今ある名, 履歴にある名, 支給の月=None) -> dict:
    """置き場（`置き場` の返すフォルダ）に今ある名と、前の版の置き場（`9_履歴/`）にある名の一覧から、次に配る版と、差し替える前の版を返す。
    新しい版は同じ組・支給月（年月で比べる）の前の版（どちらの置き場の名も・今の形も前の名も）の最大の次。2 つは必ず渡す（前の版が無ければ `[]`。
    省く・None・1 つの字・dict は止める＝前の版を見ずに黙って v1 を付けない）。分けた枚（`_v<版>-<枚>.html`）も同じ版に数える。
    下書きは数えない。ほかの支給月の名は数えない（同じ置き場に月が並ぶ）。名の読み分けは `置き場の名を分ける` の 1 つの表。

    同じ組の前の名（`確認ページ_…`・前の支給月の字の名）は版に数えて止めない（寄せで移す物 に返す・寄せの移しが 9_履歴/ へ移す）。
    止める物（ValueError を 1 つ・在る物を全部並べる）: 読めない物（フォルダ・形の外の名＝中や名に前の版が在り得る）は答えを
    1 つ「寄せの移しを当てる」に寄せる。読めた名（今の形も前の名も）のほかの組の名は置き違い（その組の置き場へ・寄せで移す物にしない）。黙って飛ばすと版を 1 から数え直す。
    事務所の置き場（`00_事務所/`）は事務所のルール.md・管理表 などと同じフォルダ＝確認事項の頭（`確認事項_`・`確認ページ_`・下書きも）の
    無い名だけは確認事項でないと見て数えない。
    9_履歴/ の名は `履歴の名を分ける` で読み、同じ組・支給月の配った版だけ数える（読めない物は確認事項でない物＝飛ばす）。
    返す物: 版・名・下書きの名・置き場・前の版（無ければ None・前の版を分けていれば 1 枚目）・前の版たち（今の置き場の今の形の
    前の版の全部の枚の名）・寄せで移す物（今の置き場の前の名の並び）。前の版たちは 差し替え の手順で 1 つずつ 9_履歴/ へ移す。"""
    _名の並びか("今ある名（置き場の名）", 今ある名)
    _名の並びか("履歴にある名（9_履歴/ の名）", 履歴にある名)
    月 = 支給月の名(支給月, 支給の月)
    年月 = _月の年月(月)
    読んだ, 前の名たち, 読めない, 置き違い = [], [], [], []
    for n in map(str, 今ある名):
        if 組 == "事務所" and not n.startswith(名の頭たち):
            continue   # 00_事務所 に並ぶ確認事項でない物（事務所のルール.md・管理表・質問と回答・9_履歴/）
        類, r = 置き場の名を分ける(n)
        if 類 == "読めない物":
            読めない.append(n)
        elif ほかの組の名か(n, 組):   # 読めた名（今の形も前の名も）の組を、類で分ける前に 1 か所で照らす（寄せの移しも同じ口）
            置き違い.append(n)
        elif 類 == "前の名":
            前の名たち.append(n)
        if r and r["組"] == 組 and r["年月"] == 年月 and not r["下書き"]:
            読んだ.append((r["版"], r["枚"] or 0, n, 類))
    if 読めない or 置き違い:
        raise ValueError("版を数えられない: " + "／".join(
            ([f"読めない物 {読めない!r}（{置き場の名の類['読めない物']}）＝{_片付け方(組)}"] if 読めない else [])
            + ([f"置き違い {置き違い!r}＝ほかの組の名（組「{組}」の置き場 {置き場(組, 支給月, 支給の月)}）。その組の置き場へ移す"]
               if 置き違い else [])))
    古い = [r["版"] for 類, r in map(履歴の名を分ける, map(str, 履歴にある名))
            if r and r["組"] == 組 and r["年月"] == 年月 and not r["下書き"]]
    読んだ.sort()
    今の = [x for x in 読んだ if x[3] == "今の形"]
    前 = 今の[-1][0] if 今の else None
    前たち = [n for v, _, n, _ in 今の if v == 前]
    版 = max([v for v, _, _, _ in 読んだ] + 古い, default=0) + 1
    return {
        "版": 版,
        "名": 名(組, 支給月, 版, 支給の月=支給の月),
        "下書きの名": 名(組, 支給月, 版, 下書き=True, 支給の月=支給の月),
        "置き場": 置き場(組, 支給月, 支給の月),
        "前の版": 前たち[0] if 前たち else None,
        "前の版たち": 前たち,
        "寄せで移す物": 前の名たち,
    }


def 差し替え(組: str, 支給月: str, 前の名: str, 消す日: str, 支給の月=None) -> dict:
    """配り直した時に前の版を型の文書の表の「前の版」（`10_会社/<組>/9_履歴/`・事務所は `00_事務所/9_履歴/`）へ `消す_<日>_` を付けて移す手順（殻が当てる）。
    前の名は同じ組の確認事項の名でなければ ValueError（古い形の名・ほかの組の名を移す手順を出さない）。"""
    if not re.fullmatch(消す名の日, 消す日):
        raise ValueError(f"消す日 {消す日!r} は YYYY-MM-DD でない")
    r = 名を読む(前の名)
    if r["組"] != 組 or r["下書き"]:
        raise ValueError(f"{前の名!r} は組「{組}」の配った版の名でない")
    return {"する": "移す", "元": 置き場(組, 支給月, 支給の月) + 前の名, "先": _表の所(組, 1) + 消す名(消す日, 前の名)}


def 前の版の消す日(今日: str) -> str:
    """配り直して 9_履歴/ へ移す前の版・下書きの消す日（`docs/設計/寄せる道具.md` §4.2「人が要らないと決めた物」と同じ
    置いた日の翌月末）。殻・窓が日を選ばない＝ここ 1 か所。今日は YYYY-MM-DD。"""
    import datetime as _dt
    import calendar as _cal
    try:
        d = _dt.date.fromisoformat(str(今日))
    except ValueError:
        raise ValueError(f"今日 {今日!r} は YYYY-MM-DD でない") from None
    y, m = d.year + d.month // 12, d.month % 12 + 1
    return _dt.date(y, m, _cal.monthrange(y, m)[1]).isoformat()


# 1 つの版の枚の印（作る が枚ごとの HTML の頭に書く `<!-- 確認事項の枚 <枚>/<枚の数> -->`・分けない時も 1/1）。
# 配る手順 は置く物の中身のこの印で、作る が返した枚の全部が 1 度に渡ったか（枚の数・並び）を見る
枚の印の形 = re.compile(r"<!-- 確認事項の枚 (?P<枚>[1-9]\d*)/(?P<数>[1-9]\d*) -->")
_版の項目の形 = re.compile(r'<input type="hidden" name="__版__" value="(?P<字>[^"]*)">')


def 枚の印(枚: int, 枚の数: int) -> str:
    return f"<!-- 確認事項の枚 {枚}/{枚の数} -->"


def 枚の印を読む(html: str) -> tuple[int, int]:
    """確認事項の HTML の枚の印 → (枚, 枚の数)。印が無い・2 つ以上・枚が枚の数を超える時は ValueError（作る の出した物でない）。"""
    m = 枚の印の形.findall(str(html))
    if len(m) != 1:
        raise ValueError(f"確認事項の HTML に枚の印（{枚の印(1, 1)} の形）が {len(m)} 個＝作る が出した物でない（作る で作り直す）")
    枚, 数 = int(m[0][0]), int(m[0][1])
    if 枚 > 数:
        raise ValueError(f"枚の印 {枚}/{数} の枚が枚の数を超える")
    return 枚, 数


def 配る手順(組: str, 支給月: str, 置く物, 今ある名, 履歴にある名, 今日: str, 下書き: bool = False,
          支給の月=None) -> dict:
    """殻の配る口（確認ページを Drive に置く口）が当てる手順（`Drive の型.md` §2「殻が Drive に置く物」の確認事項の行）。
    1 回に置くのは 1 つの版の全部の枚（`作る` の 枚たち の全部・分けない時は 1 つ）＝置く物は `(名, html)` の並びで 1 度に受ける。
    名を殻・窓が組まない: 置く名の並びは 次の版 が今の置き場（`今ある名`）と前の版の置き場（`履歴にある名`）から決めた版の
    名の並び（分けない時 `[_v<版>.html]`・分けた時 `[_v<版>-1.html, …, _v<版>-<枚の数>.html]`・下書きなら `下書き_` つき）と
    1 字も違えば ValueError（前と同じ版・飛んだ版・下書き_ のまま配る・枚を 1 つずつ渡す・枚が欠ける／多い を通さない）。
    中身も照らす: 各 html の枚の印（`枚の印を読む`）が並びの何枚目／枚の数と、`__版__` の値が 版の字 と違えば ValueError
    （名だけ付け替えた file・別の版の枚・作る の返した枚の一部だけ を通さない）。

    返す物:
      名たち・置き場・版＝新しく置く file の名の並びと置き場（同じ名の file が在っても上書きしない＝前の版の file の中身を差し替えない）
      上書き＝下書きを置き直す時だけ、今の置き場に在る同じ名の下書きの名の並び（その file の中身を差し替える。無ければ []）
      移す＝全部の枚を置いた後に 1 回当てる移しの手順（`{する: 移す, 元, 先}`）: 配る時は前の版たち（全部の枚）と、同じ組・支給月の
        残った下書きの全部を前の版の置き場へ `消す_<前の版の消す日>_<名>` で移す。下書きを置く時は、今置く下書きの名に無い
        古い下書き（ほかの版・枚の分け方が変わった下書き）だけを移す。移した file はリンク共有を外す（殻）。"""
    if (not isinstance(置く物, (list, tuple)) or not 置く物
            or any(not isinstance(x, (list, tuple)) or len(x) != 2 or not all(isinstance(y, str) for y in x) for x in 置く物)):
        raise ValueError("置く物は 1 つの版の全部の枚の (名, html) の並びで 1 度に渡す（作る の 枚たち の全部・1 枚ずつ渡さない）"
                         f"（受けた物の形: {type(置く物).__name__}）")
    v = 次の版(組, 支給月, 今ある名, 履歴にある名, 支給の月)
    数 = len(置く物)
    枚たち = [k if 数 > 1 else None for k in range(1, 数 + 1)]
    want = [名(組, 支給月, v["版"], 下書き=下書き, 支給の月=支給の月, 枚=k) for k in 枚たち]
    置く名たち = [n for n, _ in 置く物]
    if 置く名たち != want:
        raise ValueError(f"置く名 {置く名たち!r} が置き場の今の名から決めた{'下書きの' if 下書き else ''}名の並び {want!r} と違う"
                         "＝確認ページを `作る` で今の置き場の名から作り直し、返った枚の全部を 1 度に置く（名を手で組まない）")
    for k, (n, h) in zip(range(1, 数 + 1), 置く物):
        印 = 枚の印を読む(h)
        if 印 != (k, 数):
            raise ValueError(f"{n!r} の中身の枚の印 {印[0]}/{印[1]} が置く並びの {k}/{数} と違う＝作る が返した枚の全部を 1 度に置く"
                             "（枚が欠けた・ほかの回の枚が混ざった）")
        m = _版の項目の形.findall(h)
        字 = 版の字(支給月, v["版"], 支給の月, 枚たち[k - 1])
        if m != [字]:
            raise ValueError(f"{n!r} の中身の版 {m!r} が名の版の字 {字!r} と違う＝名だけ付け替えた file を置かない（作る で作り直す）")
    消す日 = 前の版の消す日(今日)
    元の所, 先の所 = v["置き場"], _表の所(組, 1)
    月 = 支給月の名(支給月, 支給の月)
    残った下書き = []
    for n in 今ある名:
        m = 名の形.fullmatch(str(n))
        if m and m["下書き"] and m["組"] == 組 and m["月"] == 月 and not (下書き and str(n) in want):
            残った下書き.append(str(n))
    移す = [] if 下書き else [差し替え(組, 支給月, n, 消す日, 支給の月) for n in v["前の版たち"]]
    移す += [{"する": "移す", "元": 元の所 + n, "先": 先の所 + 消す名(消す日, n)} for n in 残った下書き]
    今の = set(map(str, 今ある名))
    return {"名たち": want, "置き場": 元の所, "版": v["版"], "下書き": bool(下書き),
            "上書き": [n for n in want if 下書き and n in 今の], "移す": 移す}


# ── 問いの行を読む ─────────────────────────────────────────

def _鍵(番号: str) -> str:
    """問いの番号 → 問いの鍵（data-qkey・答えの name。半角英数字と _）。"""
    return re.sub(r"[^A-Za-z0-9_]", "_", 番号)


def _選択肢の字(行: dict) -> list[str]:
    if isinstance(行.get("選択肢"), list):
        return [str(x.get("見出し", "") if isinstance(x, dict) else x).strip() for x in 行["選択肢"]
                if str(x.get("見出し", "") if isinstance(x, dict) else x).strip()]
    return [x.strip() for x in re.split(r"[／|｜]", str(行.get("答え方の例", ""))) if x.strip()]


def _字の並び(v, 区切り=r"[／\n]") -> list[str]:
    """list か、区切りの字で並べた文字列 → 空でない字の list。"""
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in re.split(区切り, str(v or "")) if x.strip()]


def _分かっている事(行: dict) -> list[str]:
    """見つけた事（`.known`）の行。`分かっている事`（資料名・場所・値）か、無ければ探した資料と見当から起こす。"""
    v = 行.get("分かっている事")
    行たち = _字の並び(v, r"\n") if v else []
    if 行たち:
        return 行たち
    探した = _字の並び(行.get("探した資料"), r"[、,\n]")
    if 探した:
        行たち.append(f"{'、'.join(探した)} に書いてありません。")
    return 行たち   # 見込みは見つけた事に書かない（拠り所のある時だけ選択肢の後の別枠）


def _資料の名たち(行: dict) -> list[str]:
    """見つけた事が指す読んだ資料の名（`資料` と `探した資料`）。"""
    return list(dict.fromkeys([*_字の並び(行.get("資料"), r"[、,\n]"), *_字の並び(行.get("探した資料"), r"[、,\n]")]))


def _対象(行: dict) -> tuple[list[str], list[str]]:
    """何について（`対象`＝誰／いつ／何・`人:` を頭に付けた物は問いの人）→ (札たち, 問いの人の名たち)。"""
    札, 人 = [], []
    for x in _字の並び(行.get("対象")):
        if x.startswith("人:"):
            x = x[2:].strip()
            人.append(x)
        札.append(x)
    return 札, 人


def _理由(行: dict) -> str:
    """なぜ聞くか（data-why）。行の `理由`（mismatch・missing・law・once か 食い違い・書いてない・法の線・今回だけ）が勝つ。
    無ければ 形 mismatch＝mismatch・箱 法の線＝law・その月だけの物＝once・ほか missing。"""
    v = str(行.get("理由") or "").strip()
    if v:
        return 理由の語.get(v, v)
    if _形(行) == "mismatch":
        return "mismatch"
    return {"法の線": "law", その月だけの物: "once"}.get(_問いの箱(行), "missing")


def _くわしく(行: dict) -> list[str]:
    return _字の並び(行.get("くわしく"), r"\n")


def 読点で分ける(字) -> list[str]:
    """「、」で並べた字を分ける（「…」の中の 、 では分けない）。初期設定/設問.py の 読点で分ける と同じ。"""
    out, 今, 深さ = [], "", 0
    for c in str(字 or ""):
        深さ += (c == "「") - (c == "」")
        if c == "、" and 深さ <= 0:
            out.append(今)
            今 = ""
        else:
            今 += c
    out.append(今)
    return [x.strip() for x in out if x.strip()]


def _根拠(行: dict) -> list[dict]:
    """根拠（`場所`＝「資料の名：場所「原文」」を、で並べた字・型の版 16）→ [{資料, 場所, 原文}]。資料か場所の欠けた物は数えない。"""
    out = []
    for x in 読点で分ける(行.get("場所")):
        資料, _, 残り = x.partition("：")
        m = re.fullmatch(r"(.*?)「(.*)」", 残り.strip())
        場所, 原文 = ((m.group(1), m.group(2)) if m else (残り, ""))
        if 資料.strip() and 場所.strip():
            out.append({"資料": 資料.strip(), "場所": 場所.strip(), "原文": 原文.strip()})
    return out


def _リンクの表(行: dict) -> dict:
    """`資料のリンク`（資料の Drive の URL を、で並べる・資料・探した資料 と同じ順・無い物は「（リンク無し: 訳）」）→
    {資料の名: {url, no_url}}。"""
    out = {}
    for 名, v in zip(_資料の名たち(行), 読点で分ける(行.get("資料のリンク"))):
        m = re.fullmatch(r"（リンク無し(?:[:：]\s*(.*))?）", v.strip())
        out[名] = {"url": "", "no_url": (m.group(1) or "").strip() or "訳なし"} if m else {"url": v.strip(), "no_url": ""}
    return out


def _見込み(行: dict) -> dict | None:
    """見込みの別枠 {値, 拠り所}。見当があり、拠り所の頭が見込みの頭（型.json の 見当の拠り所 の 頭）の時だけ。計算の置き値
    （既定・法の線・知らせ・無し）と型に無い頭は見込みでない＝出さない（2026-11-17 オーナー: 根拠の無い見込みを前提にさせない）。"""
    値, 拠り所 = str(行.get("見当") or "").strip(), str(行.get("見当の拠り所") or "").strip()
    if not 値 or not 型.見込みの拠り所か(拠り所):
        return None
    return {"値": 値, "拠り所": 拠り所}


def _問いの箱(行: dict) -> str:
    何 = str(行.get("何が無いか", "")).strip()
    if 何 == その月だけの物 or 何.startswith(その月だけの物 + ":"):
        return その月だけの物
    return next((b for b in ("読み方", "法の線") if 何.startswith(b + ":")), "足りない値")


def _形(行: dict) -> str:
    """行の形。無ければ箱の既定（読み方・法の線＝choose・その月だけの物＝fact・ほか judge）。"""
    return 行.get("形") or 箱の既定の形.get(_問いの箱(行), "judge")


def _まとまり(行: dict) -> str:
    """並べ方のまとまり（data-group）: rule＝会社の決まり → person＝人ごとの事実 → once＝今回だけの事。

    行の `まとまり` が勝つ。無ければ箱から: 読み方・法の線＝rule・その月だけの物＝once・足りない値は 何が無いか の項目の段
    （会社・勤務の型・事務所に置ける＝rule・人だけ＝person）で、項目でない物（原本の名など）は once・何が無いか が空は rule。"""
    if 行.get("まとまり"):
        return str(行["まとまり"])
    if 後でのいつ in _字の並び(行.get("対象")):
        return "later"   # まだ起きていない場面の問い＝先に決めておきたい事（いつも最後）
    箱 = _問いの箱(行)
    if 箱 == その月だけの物:
        return "once"
    if 箱 != "足りない値":
        return "rule"
    何 = str(行.get("何が無いか", "")).strip()
    名 = (re.fullmatch(r"「([^」]+)」が無い.*", 何) or [None, 何])[1]   # 種を集める の「<項目>」が無い の形も
    try:
        段たち = set(型.項目(名).get("段") or ()) if 何 else set()
        項目だ = bool(何)
    except KeyError:
        段たち, 項目だ = set(), False
    先たち = 型.反映先を読む(行.get("反映先"))
    if 先たち:   # 反映先が全部 会社の決まりの先（型の口.会社の決まりの先か）なら会社の決まり
        if all(型.会社の決まりの先か(w) for w in 先たち):
            return "rule"
        return "person" if 項目だ else "once"
    if not 何:
        return "rule"
    if not 項目だ:
        return "once"
    return "rule" if 段たち & {"会社", "勤務の型", "事務所"} else "person"


def _種類(行: dict) -> str:
    """問いの種類（会社の決まり／原本）。行の `種類` が勝つ。無ければまとまりから（rule＝会社の決まり・person と once＝原本）。
    初期設定/設問.py の `種類` と同じ決まり（質問と回答の列だけから決まる）。"""
    v = str(行.get("種類") or "").strip()
    if v:
        return v
    if _まとまり(行) == "later":   # まだ起きていない場面の問い＝中身の種類は箱と反映先から（まとまりを外して読む）
        return _種類({**行, "まとまり": "", "対象": ""})
    return "会社の決まり" if _まとまり(行) == "rule" else "原本"


def _値の鍵(語: str) -> str:
    """選択肢の字 → 選択肢の鍵（value）。字から決まる（版が変わっても同じ字なら同じ鍵）。"""
    return "c" + hashlib.sha1(語.encode("utf-8")).hexdigest()[:8]


def _変わる事の表(行: dict) -> dict:
    v = 行.get("変わる事")
    if isinstance(v, dict):
        return {str(k).strip(): str(x).strip() for k, x in v.items()}
    out = {}
    for x in _字の並び(v):   # 「語＝変わる事／語＝変わる事」
        if "＝" in x:
            k, _, w = x.partition("＝")
            out[k.strip()] = w.strip()
    return out


def _選択肢(行: dict) -> list[dict]:
    """行の選択肢 → [{鍵, 語, 見出し, 変わる事, 添え書き, 推奨}]。語＝質問と回答の 回答 に書く字。
    変わる事（small.chg）は行の `変わる事`（{語: 文}・「語＝文／…」）か選択肢の {見出し, 変わる事} か、語ごとの既定。
    最後に形ごとの「ほかの答え」「別の決め方」か「当てはまらない」を足す（「分からない」は HTML の側で全問の最後に置く）。"""
    形 = _形(行)
    箱 = _問いの箱(行)
    見当 = str(行.get("見当", "")).strip()
    表 = _変わる事の表(行)
    out = []
    元 = 行.get("選択肢") if isinstance(行.get("選択肢"), list) else _選択肢の字(行)
    if 形 == "fact" and not 元:
        元 = ["分かる（補足に書く）"]
    for o in 元:
        if isinstance(o, dict):
            語 = str(o.get("見出し", "")).strip()
            推奨, 見出し, 変わる = bool(o.get("推奨")), 語, str(o.get("変わる事", "")).strip()   # 推奨は検査が赤にするだけ（出さない）
            if m := re.fullmatch(r"(.+?)（(補足に[^）]*)）", 語):
                見出し = m.group(1)   # 見出しには書かない＝印（data-supp）で欄の名が「この答えでは書いてください」に変わる
        else:
            語 = str(o).strip()
            推奨 = 語.endswith(推奨の印)
            if 推奨:
                語 = 語[: -len(推奨の印)].strip()
            見出し, 変わる = 語, ""
            if m := re.fullmatch(r"(.+?)（(補足に[^）]*)）", 語):
                見出し = m.group(1)
                変わる = ("訳を" if "訳" in m.group(2) else "") + "ひとことに書いた事で計算します"
        if not 語 or (形 == "fact" and 語 == 当てはまらない):
            continue   # fact の「当てはまらない」は形の最後に 1 つだけ足す
        if 語 == 見当のとおり:   # 前の版の行の語。おすすめにせず、見込みの別枠を指す見出しにする
            見出し = "下の灰色の枠のとおり"   # 「見込み」の字は .estimate の枠の外に書かない（qa-html の検査）
            変わる = 変わる or (f"「{見当}」のまま計算します" if 0 < len(見当) <= 24 else "下の灰色の枠のまま計算します")
        変わる = 表.get(語) or 変わる or 変わる事の既定.get(見出し, "")
        out.append({"鍵": "estimate" if 語 == 見当のとおり else _値の鍵(語), "語": 語, "見出し": 見出し,
                    "変わる事": 変わる, "添え書き": "", "推奨": 推奨})
    for o in out:
        o["要る"] = bool(re.search(r"（補足に[^）]*）$", o["語"])) or _ひとことを頼む(o)
    ひとこと型 = any("ひとこと" in o["変わる事"] for o in out) or any(o["見出し"] in 足す選択肢.values() for o in out)
    if 形 == "fact":
        out.append({"鍵": "none", "語": 当てはまらない, "見出し": 当てはまらない, "変わる事": "",
                    "添え書き": その月だけの物の当てはまらない if 箱 == その月だけの物 else "", "推奨": False})
    elif not ひとこと型:
        語 = 足す選択肢[形]
        out.append({"鍵": "other", "語": 語, "見出し": 語, "変わる事": "", "添え書き": "下のひとことに書いてください", "推奨": False})
    for o in out:
        o["要る"] = o.get("要る") or o["鍵"] == "other" or o["見出し"] in 足す選択肢.values() or _ひとことを頼む(o)
    return out


# ひとことに書かせる選択肢の字（qa-html の check.mjs の RULES.supp_ask と同じ）。当たる選択肢には data-supp="need" を付ける
_ひとことの字 = re.compile(r"ひとこと|補足に書|補足欄|下の欄")


def _ひとことを頼む(o: dict) -> bool:
    """選択肢がひとことに書く事を頼むか（見出し・添え書き・変わる事の字）。"""
    return bool(_ひとことの字.search(" ".join((o["見出し"], o["添え書き"], o["変わる事"]))))


# ── 問いの検査 ─────────────────────────────────────────────

def 問いの検査(行たち: list[dict], 内部の言葉: list[str] | tuple = ()) -> list[str]:
    """qa-html の決まりのうち機械で見られる物。決まり外れを赤の 1 行ずつで返す（空なら緑）。

    1 問 1 行・形が 4 つ・まとまりが 4 つのどれか・選択肢 2 つ以上・おすすめの印を付けない・選択肢に記号を付けない・
    記号で選択肢を指さない・内部の言葉を含まない・問いの番号が在って重ならない。
    前提（qa-html の前提の 3 段）: 何について（`対象` 1〜3 つ）・なぜ聞くか（`理由` が 4 つのどれか）・見つけた事（2 行まで）と
    それが指す読んだ資料（`資料` か `探した資料`）・くわしく（3 行まで）・選択肢ごとの変わる事・切り抜き（2 枚まで・写る人は
    問いの人だけ）・根拠（場所・実物＝原文か切り抜き・AI の読み）・前の問いに寄りかからない・道具の都合を聞かない。前提が書けない問いは出さない。長さ・1 問に 2 つ・数を書かせる形は配る前に qa-html の check.mjs で見る。"""
    赤 = []
    if not 行たち:
        return ["問いが 1 つも無い"]
    語たち = [w for w in (*既定の内部の言葉, *内部の言葉) if w]
    鍵たち: dict[str, str] = {}
    for i, 行 in enumerate(行たち, 1):
        番号 = str(行.get("問いの番号", "")).strip()
        id = f"問い {i}（{番号 or '番号なし'}）"
        if not 番号:
            赤.append(f"{id}: 問いの番号が無い")
        elif _鍵(番号) in 鍵たち:
            赤.append(f"{id}: 問いの番号が {鍵たち[_鍵(番号)]} と重なる")
        else:
            鍵たち[_鍵(番号)] = 番号
        問い = str(行.get("質問", "")).strip()
        if not 問い:
            赤.append(f"{id}: 質問が空")
        elif "\n" in 問い or "\r" in 問い:
            赤.append(f"{id}: 質問が 2 行以上（1 問 1 行にする・見つけた事は別に渡す）")
        形 = _形(行)
        if 形 not in 形たち:
            赤.append(f"{id}: 形 {形!r} は {'・'.join(形たち)} のどれでもない")
            continue
        if _まとまり(行) not in まとまりたち:
            赤.append(f"{id}: まとまり {_まとまり(行)!r} は {'・'.join(まとまりたち)} のどれでもない")
        elif _種類(行) not in 種類たち:
            赤.append(f"{id}: 種類 {_種類(行)!r} は {'・'.join(種類たち)} のどれでもない")
        elif _まとまり(行) not in _種類のまとまり[_種類(行)]:
            赤.append(f"{id}: 種類 {_種類(行)} とまとまり {_まとまり(行)} が合わない（会社の決まり＝rule・原本＝person か once）")
        # 前提の 4 欄（書けない問いは出さない）
        札, 人 = _対象(行)
        if not 札:
            赤.append(f"{id}: 何について（対象＝誰／いつ／何）が無い（前提が書けない問いは出さない）")
        elif len(札) > 対象の上限:
            赤.append(f"{id}: 何についての札が {len(札)} つ（{対象の上限} つまで）")
        理由 = _理由(行)
        if 理由 not in 理由の文:
            赤.append(f"{id}: なぜ聞くか（理由）{理由!r} は {'・'.join(理由の文)} のどれでもない")
        elif 形 == "mismatch" and 理由 != "mismatch":
            赤.append(f"{id}: 食い違いの問い（mismatch）のなぜ聞くかは mismatch")
        if _まとまり(行) == "person" and not 人:
            赤.append(f"{id}: 人ごとの事実の問いに問いの人（対象 の 人:<名>）が無い")
        if 形 == "mismatch" and len(行.get("切り抜き") or []) not in (0, 2):
            赤.append(f"{id}: 食い違いの問いの切り抜きは 0 枚か 2 枚（2 つの資料を横に並べる）")
        分かる = _分かっている事(行)
        if not 分かる:
            赤.append(f"{id}: 見つけた事（資料名・場所・値）が無い（前提が書けない問いは出さない）")
        elif len(分かる) > 分かっている事の行の上限:
            赤.append(f"{id}: 見つけた事が {len(分かる)} 行（{分かっている事の行の上限} 行まで・残りは くわしく へ）")
        for x in 分かる:
            if len(re.sub(r"\s", "", x)) > 見つけた事の字の上限:
                赤.append(f"{id}: 見つけた事の 1 行が {len(re.sub(r'\s', '', x))} 字（{見つけた事の字の上限} 字まで・残りは くわしく へ）")
        if not _資料の名たち(行):
            赤.append(f"{id}: 見つけた事が読んだ資料を指していない（資料 か 探した資料 に資料の名）")
        くわ = _くわしく(行)
        if not くわ:
            赤.append(f"{id}: くわしく が無い（前提が書けない問いは出さない）")
        elif len(くわ) > くわしくの行の上限:
            赤.append(f"{id}: くわしく が {len(くわ)} 行（{くわしくの行の上限} 行まで）")
        切 = 行.get("切り抜き") or []
        if len(切) > 切り抜きの上限:
            赤.append(f"{id}: 切り抜きが {len(切)} 枚（{切り抜きの上限} 枚まで）")
        for c in 切:
            if str(c.get("資料", "")).strip() not in _資料の名たち(行):
                赤.append(f"{id}: 切り抜きの資料「{c.get('資料', '')}」が 資料・探した資料 に無い（読んだ資料の一覧に載らない）")
            if not re.fullmatch(r"data:image/(?:png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+", str(c.get("画像", ""))):
                赤.append(f"{id}: 切り抜きの画像は data:image/…;base64 だけ（ページに埋め込む）")
            if not str(c.get("写っている事", "")).strip():
                赤.append(f"{id}: 切り抜きに写っている事が無い")
            for n in _字の並び(c.get("写っている人"), r"[、,\n]"):
                if n not in 人:
                    赤.append(f"{id}: 切り抜きに問いの人の外の名「{n}」が写っている（ほかの人の行は塗る）")
        字 = _選択肢の字(行)
        if 形 != "fact" and len(字) < 2:
            赤.append(f"{id}: 選択肢が {len(字)} つ（2 つ以上）")
        if 形 in ("choose", "mismatch") and len(字) >= 3 and "どちら" in 問い:
            赤.append(f"{id}: 選択肢が {len(字)} つなのに「どちら」と聞いている（3 つ以上は「どれ」）")
        選 = _選択肢(行)
        if any(o["推奨"] for o in 選):
            赤.append(f"{id}: 選択肢におすすめの印がある（見込みを前提にさせない・見込みは拠り所のある時だけ 見当・見当の拠り所 の別枠）")
        if any(o["語"] == 見当のとおり for o in 選) and not _見込み(行):
            赤.append(f"{id}: 「{見当のとおり}」があるのに見込みの別枠が無い（見当と、見込みの拠り所が要る）")
        # 根拠（2026-11-17 オーナー: どのファイルのどこをどう読んだから聞くかを、リンクと実物で見せる）
        根拠 = _根拠(行)
        if not 根拠:
            赤.append(f"{id}: 根拠の場所が無い（場所＝「資料の名：PDF はページと欄・シートはタブとセルの範囲」）")
        elif not (any(e["原文"] for e in 根拠) or 切):
            赤.append(f"{id}: 根拠の実物が無い（場所の原文の引用か切り抜きが 1 つ以上）")
        if len(根拠) > 根拠の上限["数"]:
            赤.append(f"{id}: 根拠が {len(根拠)} つ（{根拠の上限['数']} つまで）")
        for e in 根拠:
            if e["資料"] not in _資料の名たち(行):
                赤.append(f"{id}: 根拠の資料「{e['資料']}」が 資料・探した資料 に無い（読んだ資料の一覧に載らない）")
            if len(e["場所"]) > 根拠の上限["場所"]:
                赤.append(f"{id}: 根拠の場所が {len(e['場所'])} 字（{根拠の上限['場所']} 字まで）: {e['場所'][:20]}")
            if len(e["原文"]) > 根拠の上限["原文"]:
                赤.append(f"{id}: 根拠の原文の引用が {len(e['原文'])} 字（{根拠の上限['原文']} 字まで・長い原文は 原文 の列へ）")
        読み = _字の並び(行.get("AIの読み"), r"\n")
        if not 読み:
            赤.append(f"{id}: AI の読みが無い（こう読んだ→ここが決まらない を 1〜3 行）")
        elif len(読み) > 3:
            赤.append(f"{id}: AI の読みが {len(読み)} 行（3 行まで）")
        for l in 読み:
            if len(l) > 根拠の上限["読みの行"]:
                赤.append(f"{id}: AI の読みの 1 行が {len(l)} 字（{根拠の上限['読みの行']} 字まで）: {l[:20]}")
        if (見 := _見込み(行)) and (len(見["値"]) > 根拠の上限["見込み"] or len(見["拠り所"]) > 根拠の上限["拠り所"]):
            赤.append(f"{id}: 見込みの別枠が長い（見当 {根拠の上限['見込み']} 字・見当の拠り所 {根拠の上限['拠り所']} 字まで）")
        if _道具の都合の字.search(問い):
            赤.append(f"{id}: 道具・システムの都合を担当者に聞いている（オーナーに聞く）")
        for o in 選:
            if 記号の頭.match(o["見出し"]):
                赤.append(f"{id}: 選択肢に記号を付けない（中身の見出しで書く）: {o['見出し'][:20]}")
            if o["鍵"] not in ("other", "none") and not o["変わる事"]:
                赤.append(f"{id}: 選択肢「{o['見出し'][:20]}」にこの答えで変わる事が無い（変わる事 に 誰の・何が・いくら）")
        if any(_前の問いの字.search(x) for x in [問い, *分かる, *くわ]):
            赤.append(f"{id}: 前の問いの答えに寄りかかっている（要る事をこの問いの中に書く）")
        for s in [問い, *分かる]:
            if m := 記号で指す.search(s):
                赤.append(f"{id}: 記号「{m.group(0)}」で選択肢を指している（中身の言葉で書く）")
                break
        見える = [問い, *札, *分かる, *くわ, *(o["見出し"] for o in 選), *(o["変わる事"] for o in 選), *(o["添え書き"] for o in 選)]
        for w in 語たち:
            for s in 見える:
                if w in s:
                    赤.append(f"{id}: 内部の言葉「{w}」: {s[:40]}")
                    break
    return 赤


# ── HTML ──────────────────────────────────────────────────

def _月の数(支給月: str, 支給の月=None) -> str:
    return re.search(r"（(\d+)月分）", 支給月の名(支給月, 支給の月)).group(1)


def _見出し(用: str, 支給月: str, 支給の月=None) -> tuple[str, str]:
    if 用 == "立ち上げ":
        return "給与計算の設定のご確認", "答えていただいた内容で、給与計算の設定を決めます。"
    月 = _月の数(支給月, 支給の月)
    return f"{月} 月分 給与計算のご確認", f"答えていただいた内容で、{月} 月分の給与を計算します。"


def 版の字(支給月: str, 版: int, 支給の月=None, 枚: int | None = None) -> str:
    """答えに付く版（`__版__`・半角英数字と . _ -）。その組×支給月の配った版の番号と同じ: `2099.04-v2`。
    分けた枚は枚も付ける（`2099.04-v2-1`・名の `_v2-1` と同じ＝どの枚への答えかが分かる・枚どうしで版が重ならない）。"""
    return f"{支給月の名(支給月, 支給の月)[:7]}-v{版}" + (f"-{枚}" if 枚 else "")


def _読んだ資料(入力: dict, 行たち: list[dict]) -> tuple[list[dict], list[str]]:
    """はじめの画面の読んだ資料の一覧 [{鍵, 名, 字, url, no_url, 置き場}]。入力の `読んだ資料`（字か {名, 期間, 受け取った日,
    url, 置き場, no_url}）に、
    問いが指すのに一覧に無い資料の名を足して知らせる。鍵は d1・d2… の順。"""
    資料, 知らせ = [], []
    for d in 入力.get("読んだ資料") or []:
        if isinstance(d, dict):
            名 = str(d.get("名", "")).strip()
            添え = "・".join(str(d[k]).strip() for k in ("期間", "受け取った日") if str(d.get(k) or "").strip())
            資料.append({"名": 名, "字": 名 + (f"（{添え}）" if 添え else ""),
                       "url": str(d.get("url") or "").strip(), "no_url": str(d.get("no_url") or "").strip(),
                       "置き場": str(d.get("置き場") or "").strip().strip("/")})
        elif str(d).strip():
            資料.append({"名": str(d).strip(), "字": str(d).strip(), "url": "", "no_url": "", "置き場": ""})
    ある = {d["名"] for d in 資料}
    for 行 in 行たち:
        for 名 in _資料の名たち(行):
            if 名 not in ある:
                資料.append({"名": 名, "字": 名, "url": "", "no_url": "", "置き場": ""})
                ある.add(名)
                知らせ.append(f"読んだ資料に「{名}」が無かったので一覧に足した（読んだ資料 に期間・受け取った日を付けて渡す）")
    # 資料のリンク: 読んだ資料の url が無ければ行の `資料のリンク` の列から（質問と回答を読み直した行）
    for d in 資料:
        if not (d["url"] or d["no_url"]):
            for 行 in 行たち:
                x = _リンクの表(行).get(d["名"])
                if x:
                    d["url"], d["no_url"] = x["url"], x["no_url"]
                    break
    for i, d in enumerate(資料, 1):
        d["鍵"] = f"d{i}"
    return 資料, 知らせ


def _リンクの検査(資料: list[dict], 行たち: list[dict], 組: str) -> list[str]:
    """問いが指す資料（資料・探した資料・根拠）のリンク: どれも url（Drive などの URL）か no_url（無い訳）を持つ。
    URL の形（https だけ・使ってよい字）はここで見ない＝作ったページを通す土台の check.mjs が正本（`ページの検査`・写しを持たない）。
    url を出せるのは受け取った原本の箱（型の口 `原本の箱の道`）の物だけ＝読んだ資料に 置き場（file の入ったフォルダの道）を渡し、
    箱の外（出す物・台帳・マスタ・確認事項・決まりの md など、こちらで作った物）か 置き場 の無い物のリンクは赤（2026-11-24・
    下書きのリンクがこちらで作った表を指していた）。パックは Drive を開かないので、置き場は殻が file を読んだフォルダを渡す。"""
    指す = {n for 行 in 行たち for n in [*_資料の名たち(行), *(e["資料"] for e in _根拠(行))]}
    赤 = []
    for d in 資料:
        if d["名"] in 指す and not d["url"] and not d["no_url"]:
            赤.append(f"読んだ資料「{d['名']}」にリンクが無い（url か、無い訳の no_url を渡す）")
        elif d["url"] and not 型.原本の箱か(d.get("置き場", ""), 組):
            赤.append(f"読んだ資料「{d['名']}」のリンクが受け取った原本の箱（{型.原本の箱の道(組)}）の物でない"
                     f"（置き場 {d.get('置き場') or '無し'}）。先方から受け取った原本の url と、その置き場を渡す。"
                     "原本が無ければ no_url に訳を書く")
    return 赤


def _資料の字(d: dict) -> str:
    """読んだ資料の一覧の 1 行 `li[data-doc][data-url]`（qa-html の型・リンクは li の中の同じ URL の <a href>。別のタブで
    開くのは型の JS）。リンクが無い資料は data-url="" と data-no-url="訳"（「リンクなし: 訳」は型の CSS が出す）。"""
    if d.get("url"):
        u = escape(d["url"], True)
        return f'<li data-doc="{d["鍵"]}" data-url="{u}"><a href="{u}">{escape(d["字"])}</a></li>'
    return f'<li data-doc="{d["鍵"]}" data-url="" data-no-url="{escape(d.get("no_url") or "", True)}">{escape(d["字"])}</li>'



def _選択肢の行(鍵: str, o: dict, 最初: bool) -> str:
    印 = ""   # おすすめの印は出さない（2026-11-17 オーナー: 見込みを前提にさせない）
    小 = (f'<small class="chg">{escape(o["変わる事"])}</small>' if o["変わる事"] else "") + \
        (f"<small>{escape(o['添え書き'])}</small>" if o["添え書き"] else "")
    req = " required" if 最初 else ""
    印2 = ' data-supp="need"' if o.get("要る") else ""
    return (f'<label class="opt"><input type="radio" name="{鍵}" value="{o["鍵"]}"{req}{印2}>'
            f"<span><b>{escape(o['見出し'])}{印}</b>{小}</span></label>")


def _箱(行: dict, glabel: str | None, glead: str | None, 資料の鍵: dict) -> str:
    """問いの箱 1 つ。glabel＝まとまりの見出し（data-glabel・無ければ型の既定の見出し）・glead＝まとまりの最初の問いの 1 行。"""
    鍵 = _鍵(str(行["問いの番号"]).strip())
    形 = _形(行)
    問い = str(行["質問"]).strip()
    選 = _選択肢(行)
    分かる = _分かっている事(行)
    見出し = str(行.get("見出し", "")).strip() or 問い
    まとまり = _まとまり(行)
    理由 = _理由(行)
    札, 人 = _対象(行)
    gl = f' data-glabel="{escape(glabel, True)}"' if glabel else ""
    表 = 行.get("表") or []
    表の字 = ""
    if 表:
        表の字 = "\n<table>" + "".join(
            "<tr>" + "".join(f"<{t}>{escape(str(c))}</{t}>" for c in r) + "</tr>"
            for k, r in enumerate(表) for t in ["th" if k == 0 else "td"]) + "</table>"
    docs = " ".join(資料の鍵[n] for n in _資料の名たち(行))
    切 = []
    for c in 行.get("切り抜き") or []:
        写る = " ".join(_字の並び(c.get("写っている人"), r"[、,\n]"))
        切.append(f'<figure class="clip" data-doc="{資料の鍵.get(str(c.get("資料", "")).strip(), "")}" data-shows="{escape(写る, True)}">'
                 f'<img src="{escape(str(c["画像"]), True)}" alt="{escape(str(c.get("写っている事", "")), True)}">'
                 f'<figcaption>{escape(str(c.get("場所", "")))}</figcaption></figure>')
    根 = []   # qa-html の型: li[data-doc][data-where]＝<b>資料名</b>・場所＋原文の引用 .quote（括弧は型が付ける）
    for e in _根拠(行):
        根.append(f'<li data-doc="{資料の鍵.get(e["資料"], "")}" data-where="{escape(e["場所"], True)}">'
                 f'<b>{escape(e["資料"])}</b>・{escape(e["場所"])}'
                 + (f'<span class="quote">{escape(e["原文"])}</span>' if e["原文"] else "") + "</li>")
    読み = "<br>".join(escape(x) for x in _字の並び(行.get("AIの読み"), r"\n"))
    見込み = _見込み(行)
    原文 = str(行.get("原文", "")).strip()
    くわ = "<br>".join(escape(x) for x in _くわしく(行)) + (f'<div class="orig">{escape(原文)}</div>' if 原文 else "")
    return "\n".join(x for x in [
        f'<fieldset class="q" data-qkey="{鍵}" data-qlabel="{escape(見出し, True)}" data-kind="{形}" data-group="{まとまり}"{gl}>',
        f'<p class="glead">{escape(glead)}</p>' if glead else "",
        '<p class="about">' + "".join(f'<span class="who">{escape(x)}</span>' if x in 人 else f"<span>{escape(x)}</span>" for x in 札) + "</p>",
        f"<legend>{escape(問い)}</legend>",
        f'<p class="why" data-why="{理由}">{理由の文[理由]}</p>',
        f'<p class="reading">{読み}</p>' if 読み else "",   # 頭の「AI の読み: 」は型の CSS が付ける
        f'<div class="known" data-docs="{docs}">{"<br>".join(escape(x) for x in 分かる)}{表の字}</div>',
        f'<ul class="evidence">{"".join(根)}</ul>' if 根 else "",
        f'<div class="clips">{"".join(切)}</div>' if 切 else "",
        f'<details class="more"><summary>くわしく</summary>{くわ}</details>',
        '<div class="opts">',
        *(_選択肢の行(鍵, o, j == 0) for j, o in enumerate(選)),
        '<p class="or">または</p>',
        f'<label class="opt"><input type="radio" name="{鍵}" value="{分からない}"><span><b>{分からないの字}</b></span></label>',
        "</div>",
        # 頭の「AI の今の見込み: 」と後ろの「（根拠: …）。見込みに合わせず、事実で選んでください。」は型の CSS が付ける
        (f'<p class="estimate" data-basis="{escape(見込み["拠り所"], True)}">{escape(見込み["値"])}</p>') if 見込み else "",
        f'<div class="supp"><label for="supp_{鍵}">ひとこと（なくても大丈夫です）</label>'
        f'<textarea id="supp_{鍵}" name="supp_{鍵}" rows="2"></textarea></div>',
        "</fieldset>",
    ] if x)


def 作る(入力: dict) -> dict:
    """確認ページを 1 枚起こす（qa-html の 1 つの型・前提の 3 段・答えの形 qa-html/2）。

    入力: 組・支給月・用（立ち上げ／毎月）・問い（質問と回答の行の list）・今ある名（置き場の名の並び）・履歴にある名
          （前の版の置き場 9_履歴/ の名の並び）＝2 つは必ず渡す（前の版が無ければ []・無いと止まる＝版は前の版の最大の次）・
          支給の月（会社の `支払.支給の月`・任意・無ければ既定の翌月で知らせ）・宛先（send・copy・artifact・既定 send）・
          読んだ資料（字か {名, 期間, 受け取った日, url, 置き場, no_url} の list・url は受け取った原本の箱の物だけ）・答えるまでの扱い・まとまりの1行（{rule|person|once: 1 行}）・
          宛名・期限・この後のこと・会社の色（#rrggbb）・内部の言葉（どれも任意）。差出人・連絡先の欄は型から外した
          （名乗りと問い合わせ先は配る人の送る文に書く）＝渡されても使わず知らせる。
    並べ方: 1 枚の中で前半＝会社の決まり（rule）・後半＝原本（person → once）の 2 部（オーナーの決定 2026-11-16）。
    返す物: 赤（空でなければ HTML を返さない・作った枚は全部、土台の qa-html の check.mjs〔`ページの検査`〕に通し、その赤も入る）・知らせ・版・版の字・名・下書きの名・置き場・前の版・前の版たち・問いの数・
    部（{会社の決まり: 問いの数, 原本: 問いの数}）・html・枚たち（[{枚, 名, 下書きの名, 版の字, 問いの数, 問いの番号, 部, html}]）。
    問いが 1 枚の上限（12 問）を超えたら、並びのまま同じ版の枚に分ける（名 `_v<版>-<枚>`・版の字 `…-v<版>-<枚>`）。その時は
    上の段の 名・下書きの名・版の字・html は None で、枚たち を全部配る（1 回の呼び出しで分ける＝分けた枚どうしで版が重ならない）。"""
    組, 支給月, 用 = 入力["組"], 入力["支給月"], 入力["用"]
    支給の月 = 入力.get("支給の月")
    知らせ = 支給月の名と知らせ(支給月, 支給の月)[1]
    if 用 not in 用たち:
        raise ValueError(f"用 {用!r} は {'・'.join(用たち)} のどれか")
    宛先 = 入力.get("宛先", "send")
    if 宛先 not in 宛先たち:
        raise ValueError(f"宛先 {宛先!r} は {'・'.join(宛先たち)} のどれか")
    色 = 入力.get("会社の色") or 既定の色
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", 色):
        raise ValueError(f"会社の色 {色!r} は #rrggbb の 1 色")
    行たち = 入力["問い"]
    版 = 次の版(組, 支給月, 入力.get("今ある名"), 入力.get("履歴にある名"), 支給の月)
    if 版["寄せで移す物"]:
        知らせ.append(f"{版['置き場']} に前の名 {版['寄せで移す物']!r} が在る（版は数えた）。{_片付け方(組)}")
    版の = 版の字(支給月, 版["版"], 支給の月)
    赤 = 問いの検査(行たち, 入力.get("内部の言葉", ()))
    赤 += _リンクの検査(_読んだ資料(入力, 行たち)[0], 行たち, 組)
    # 同じ月の次の版（配り直し）は前の版がその月だけの物の問いを持っている＝最初の版にだけ当てる
    if 用 == "毎月" and 版["版"] == 1 and not any(_問いの箱(行) == その月だけの物 for 行 in 行たち):
        赤.append(f"毎月の確認ページに「{その月だけの物}」の問いが無い（初期設定/設問.py の その月だけの物の問い で起こして足す）")
    返す = {"知らせ": 知らせ, **版, "版の字": 版の, "問いの数": len(行たち)}
    if 赤:
        return {"赤": 赤, **返す, "html": None}
    for k in 外した欄:
        if k in 入力:
            知らせ.append(f"{k} は確認ページの型から外した欄（使わない）。名乗りと問い合わせ先は配る人の送る文に書く（呼ぶ側から {k} を外す）")
    資料, k = _読んだ資料(入力, 行たち)
    知らせ += k
    資料の鍵 = {d["名"]: d["鍵"] for d in 資料}
    題, 前書き = _見出し(用, 支給月, 支給の月)
    期限 = str(入力.get("期限") or "").strip()
    次 = str(入力.get("この後のこと") or "").strip() or (既定のこの後_立ち上げ if 用 == "立ち上げ" else 既定のこの後_毎月)
    月 = None if 用 == "立ち上げ" else _月の数(支給月, 支給の月)
    glabels = {**既定のまとまりの見出し, **({"once": f"原本・{月} 月分だけの事"} if 月 else {})}
    渡した1行 = {str(k): str(v) for k, v in (入力.get("まとまりの1行") or {}).items()}
    gleads = {"rule": 既定のまとまりの1行["rule"], "person": 既定のまとまりの1行["person"],
              "once": f"{月} 月分だけの事を確かめます" if 月 else 既定のまとまりの1行["once"],
              "later": 既定のまとまりの1行["later"]}
    # 1 枚の中で前半＝会社の決まり（rule）・後半＝原本（person → once）。並びは qa-html の rule → person → once のまま
    並び = sorted(行たち, key=lambda r: まとまりたち.index(_まとまり(r)))
    # 1 枚の問いの上限（qa-html の 12 問）を超えたら、並びのまま枚に分ける。分けた枚は同じ版の 1 枚目・2 枚目
    # （名 `_v<版>-<枚>`・版の字 `…-v<版>-<枚>`）＝枚どうしで名と版が重ならず、次の版（配り直し）は全部の枚を前の版に数える
    分ける = len(並び) > 枚の問いの上限
    枚の数 = max(1, -(-len(並び) // 枚の問いの上限))
    枚たち = []
    for i in range(0, len(並び), 枚の問いの上限):
        束 = 並び[i:i + 枚の問いの上限]
        枚 = i // 枚の問いの上限 + 1 if 分ける else None
        g1 = dict(gleads)
        if not any(_まとまり(r) == "person" for r in 束):
            g1["once"] = 既定の後半の頭 + g1["once"]   # 後半が今回だけの事から始まる
        g1.update(渡した1行)
        箱たち, 見た = [], set()
        for 行 in 束:
            g = _まとまり(行)
            箱たち.append(_箱(行, glabels.get(g), g1[g] if g not in 見た else None, 資料の鍵))
            見た.add(g)
        字 = 版の字(支給月, 版["版"], 支給の月, 枚)
        枚たち.append({
            "枚": 枚 or 1, "名": 名(組, 支給月, 版["版"], 支給の月=支給の月, 枚=枚),
            "下書きの名": 名(組, 支給月, 版["版"], 下書き=True, 支給の月=支給の月, 枚=枚),
            "版の字": 字, "問いの数": len(束), "問いの番号": [str(r.get("問いの番号", "")) for r in 束],
            "部": {k: sum(1 for r in 束 if _種類(r) == k) for k in 種類たち},
            "html": _一枚の_html(入力, 題, 前書き, 宛先, 色, 資料, 期限, 次, 字, 箱たち, (枚 or 1, 枚の数)),
        })
    # 出口: 作った枚を全部、土台の qa-html の検査（check.mjs）に通す。赤が 1 つでもあれば HTML を返さない（配れない 1 枚を出さない）
    赤 = [f"{x['名']}: {r}" if 分ける else r for x in 枚たち for r in _資料を名指す(ページの検査(x["html"]), 資料)]
    if 赤:
        return {"赤": 赤, **返す, "html": None}
    部 = {k: sum(1 for r in 行たち if _種類(r) == k) for k in 種類たち}
    if 分ける:   # 分けた時は 名・下書きの名・版の字・html を 枚たち で返す（上の段は None＝1 枚の名と取り違えない）
        知らせ.append(f"問いが {len(並び)} 問（1 枚 {枚の問いの上限} 問まで）＝{len(枚たち)} 枚に分けた（同じ版 v{版['版']} の枚・枚たち を全部配る）")
        return {"赤": [], **返す, "名": None, "下書きの名": None, "版の字": None, "部": 部, "html": None, "枚たち": 枚たち}
    return {"赤": [], **返す, "部": 部, "html": 枚たち[0]["html"], "枚たち": 枚たち}


def _一枚の_html(入力: dict, 題: str, 前書き: str, 宛先: str, 色: str, 資料: list[dict], 期限: str, 次: str, 版の: str,
              箱たち: list[str], 枚: tuple[int, int]) -> str:
    t = 雛形を読む()
    # 型の頭のコメントを外し、枚の印（配る手順 が 1 つの版の全部の枚が 1 度に渡ったかを見る）を置く
    t = re.sub(r"^<!doctype html>\n<!--.*?-->\n", lambda _: f"<!doctype html>\n{枚の印(*枚)}\n", t, count=1, flags=re.S)
    if 枚の印を読む(t) != 枚:
        raise ValueError("雛形の頭に枚の印を置けない（土台の qa-html の型の頭が変わった＝この道具を型に合わせて直す）")
    t = re.sub(r"<title>\{\{[^}]*\}\}</title>", lambda _: f"<title>{escape(題)}</title>", t, count=1)
    t = re.sub(r'<body data-dest="\{\{[^}]*\}\}" style="--brand:#[0-9a-fA-F]{6}">',
               lambda _: f'<body data-dest="{宛先}" style="--brand:{色}">', t, count=1)
    頭 = "\n".join([
        '<header class="top">',
        f'  <p class="to">{escape(入力.get("宛名") or 既定の宛名)}</p>',
        f"  <h1>{escape(題)}</h1>",
        f'  <p class="lead">{escape(前書き)}</p>',
        '  <div class="docs"><h2>読んだ資料（この中から聞いています）</h2>',
        "  <ul>" + "".join(_資料の字(d) for d in 資料) + "</ul>",
        "  <p>リンクは新しいタブで開きます。開けない時も、各問いに資料の切り抜きか原文を載せています。"
        "ほかに新しい資料がある時は、最後の「ほかに伝えたい事」で教えてください。</p></div>",
        f'  <p class="hold">{escape(str(入力.get("答えるまでの扱い") or "").strip() or 既定の答えるまでの扱い)}</p>',
        f'  <div class="box">{escape(f"{期限} までにお願いします。" if 期限 else 既定の期限の字)}</div>',
        "</header>",
    ])
    t = re.sub(r'<header class="top">.*?</header>', lambda _: 頭, t, count=1, flags=re.S)
    t = re.sub(r'(<input type="hidden" name="__版__" value=")\{\{[^}]*\}\}(">)', lambda m: m.group(1) + 版の + m.group(2), t, count=1)
    印 = '<input type="hidden" name="__受付番号__" value="">\n'
    前, 後 = t.split(印, 1)
    後 = 後[後.index('<fieldset class="q free"'):]
    t = 前 + 印 + "\n" + "\n\n".join(箱たち) + "\n\n" + 後
    t = re.sub(r'(<p class="next">)\{\{[^}]*\}\}(</p>)', lambda m: m.group(1) + escape(次) + m.group(2), t, count=1)
    if "{{" in t:
        raise ValueError(f"雛形の差し込みが残った: {re.findall(r'{{[^}]*}}', t)[:3]}（土台の qa-html の型の差し込みが変わった＝この道具を型に合わせて直す）")
    return t


# ── 貼り戻し（qa-html/2 の答え → 質問と回答の行） ───────────────

def _受付番号を出す(回答日: str, p: dict) -> str:
    """JS が切られて受付番号が空で届いた時に、受ける側が同じ形 R<YYMMDD>-<英数 4 字> で出す（中身から決まる）。"""
    d = re.sub(r"\D", "", 回答日)[2:8]
    h = hashlib.sha1(json.dumps([p.get("answers"), p.get("supp"), p.get("free")], ensure_ascii=False, sort_keys=True).encode()).digest()
    字 = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return f"R{d}-" + "".join(字[b % len(字)] for b in h[:4])


def _並び(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return [str(v).strip()] if str(v).strip() else []


def _送信を読む(答え, 回答日: str, 鍵たち=()) -> tuple[dict | None, list[str]]:
    """1 送信 → qa-html/2 の形（answers・labels・supp・free・version・receipt）。読めなければ (None, 赤)。

    受ける物: qa-html/2 の JSON（dict）・写す形の貼り戻しの字（最後の行 `qa-json: {…}` を読む）・送る形のフォームの値
    （{鍵: 選択肢の鍵, supp_鍵: 文, __自由記入__, __版__, __受付番号__}・配る口が足した自分の印〔シート・トークン・答えた方〕は
    問いの鍵たちの外なので読まない）。前の形の写し（qa-json の行が無い）は読まない。写しに qa-json の行が幾つもあれば最後の行。"""
    if isinstance(答え, str):
        m = re.findall(r"^qa-json: (\{.*\})[ \t\r]*$", 答え, re.M)
        if not m:
            return None, ["写しに qa-json の行が無い（前の形の確認ページの写しは読まない＝今の版で配り直して答えていただく）"]
        try:
            p = json.loads(m[-1])
        except json.JSONDecodeError as e:
            return None, [f"qa-json の行が JSON として読めない: {e}"]
    elif isinstance(答え, dict) and "form" in 答え:
        p = dict(答え)
    elif isinstance(答え, dict):   # 送る形のフォームの値
        answers, supp = {}, {}
        for k, v in 答え.items():
            if k.startswith("supp_") and k[5:] in 鍵たち:
                if _並び(v):
                    supp[k[5:]] = "\n".join(_並び(v))
            elif k in 鍵たち:
                answers[k] = _並び(v)
        p = {"form": 答えの形, "answers": answers, "labels": {}, "supp": supp,
             "free": "\n".join(_並び(答え.get(自由記入))), "version": "\n".join(_並び(答え.get(版の名))),
             "receipt": "\n".join(_並び(答え.get(受付番号の名)))}
    else:
        return None, [f"答えの形が読めない（{type(答え).__name__}）"]
    if p.get("form") != 答えの形:
        return None, [f"答えの形 {p.get('form')!r} は {答えの形} でない"]
    p = {**p, "answers": {str(k): _並び(v) for k, v in (p.get("answers") or {}).items()},
         "labels": {str(k): _並び(v) for k, v in (p.get("labels") or {}).items()},
         "supp": {str(k): str(v).strip() for k, v in (p.get("supp") or {}).items() if str(v).strip()},
         "free": str(p.get("free") or "").strip(), "version": str(p.get("version") or "").strip(),
         "receipt": str(p.get("receipt") or "").strip()}
    if not p["receipt"]:
        p["receipt"] = _受付番号を出す(回答日, p)
    elif not 受付番号の形.fullmatch(p["receipt"]):
        return None, [f"受付番号 {p['receipt']!r} が R<YYMMDD>-<英数 4 字> でない"]
    return p, []


def _答えの語(行: dict, 値たち: list[str], 見出したち: list[str]) -> tuple[list[str], list[str]]:
    """選択肢の鍵 → 質問と回答に書く語。今の行の選択肢に無い鍵は、答えに付いた見出しで書いて知らせる。"""
    表 = {o["鍵"]: o["語"] for o in _選択肢(行)}
    語たち, 知らせ = [], []
    for i, v in enumerate(値たち):
        if v == 分からない:
            語たち.append(分からないの語)
        elif v in 表:
            語たち.append(表[v])
        else:
            見 = 見出したち[i] if i < len(見出したち) else v
            語たち.append(見)
            知らせ.append(f"問い {行['問いの番号']}: 選択肢の鍵 {v!r} が今の問いに無い（見出し「{見}」のまま書いた）")
    return 語たち, 知らせ


_版の字の形 = re.compile(r"(?P<頭>.+)-v(?P<版>\d+)(?:-(?P<枚>\d+))?")
版の字の形 = _版の字の形


def 答えの版(答えの版の字, 今の版の字: str) -> tuple[bool, str]:
    """答えに付いた版の字と今配っている版の字（`版の字`）→ (古い版か, 赤)。
    同じ組×支給月で今より前の版・ほかの枚の版・版の無い答えは古い版。今より新しい版・別の支給月の版は赤（配った版と取り違えた
    ＝新しい答えとして貼らない）。大小は番号で見る（字の同じか違うかだけで見ない）。"""
    今 = _版の字の形.fullmatch(str(今の版の字))
    答 = _版の字の形.fullmatch(str(答えの版の字 or ""))
    if not 答:
        return True, ""
    if 答["頭"] != 今["頭"]:
        return False, f"版 {答えの版の字} は今配っている版 {今の版の字} と別の支給月の版（その月の質問と回答へ貼る）"
    if int(答["版"]) > int(今["版"]):
        return False, f"版 {答えの版の字} は今配っている版 {今の版の字} より新しい（今の版の字を取り違えていないか）"
    return 答えの版の字 != 今の版の字, ""


def 貼り戻し(行たち: list[dict], 答え, 回答日: str, 版: str) -> dict:
    """確認ページの答え（qa-html/2）を、問いの鍵で質問と回答の行へ戻す。

    行たち＝その確認ページの問いの質問と回答の行（シートの今の行。送り直しで足した行があればそれも）。
    答え＝1 送信か送信の並び（古い順）。1 送信は qa-html/2 の JSON・写す形の貼り戻しの字・送る形のフォームの値のどれか。
    版＝今配っている版の字（`版の字`・分けた枚はその枚の版の字）。必ず渡す（省く・None・空・版の字の形でない時は赤＝古い版かを
    見ずに貼らない）。答えの版が今より前・ほかの枚・版の無い答えは 回答 に「古い版」の印を付け、今より新しい版・別の支給月の版は赤。

    返す物:
      受付たち: 1 送信 1 行（受付番号・版・古い版・回答日）＝送り直しは新しい行（前の受付を消さない）。
      行たち: 質問と回答へ当てる手順。問いの鍵ごとに、今の行の 回答 が空なら {する: 書く, 問いの番号, 回答, 回答日}、
        答えが既にあれば {する: 足す, 行: 今の行の写しに新しい 回答・回答日}（前の答えの行は消さない）。同じ受付番号を
        その問いの番号のどの行かにもう在る受付番号は飛ばす（2 回貼っても同じ・古い送信を貼り直しても新しい答えの下に来ない）。
        表として読む時は問いの番号ごとに一番下の行が正。
      全体の補足・知らせ・赤（1 送信でも読めなければ全部を返さない＝赤を直してから全部を貼り直す）。
    回答 の字: 「<答え>[ ／ 補足: …] ／ 受付: <受付番号>（版 <版>[・古い版]）」。分からない は「分からない」。"""
    if not isinstance(版, str) or not _版の字の形.fullmatch(版):
        return {"受付たち": [], "行たち": [], "全体の補足": "", "知らせ": [],
                "赤": [f"今配っている版の字（版の字 `YYYY.MM-v<n>`・分けた枚は `…-v<n>-<枚>`）を 版 で渡す。渡さないと古い版の答えを"
                      f"新しい答えの下に足し、一番下の行が正の読みで新しい答えを上書きする（受けた物: {版!r}）"]}
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(回答日)):
        return {"受付たち": [], "行たち": [], "全体の補足": "", "知らせ": [], "赤": [f"回答日 {回答日!r} は YYYY-MM-DD でない"]}
    送信たち = 答え if isinstance(答え, list) else [答え]
    今の行: dict[str, dict] = {}
    貼った: dict[str, set] = {}   # 問いの鍵 → その番号のどれかの行に在る受付番号
    for 行 in 行たち:
        番号 = str(行.get("問いの番号", "")).strip()
        if 番号:
            今の行[_鍵(番号)] = dict(行)   # 同じ番号が幾つもあれば一番下の行が今の行
            貼った.setdefault(_鍵(番号), set()).update(re.findall(r"受付: (R\d{6}-[A-Z0-9]{4})（", str(行.get("回答", ""))))
    赤, 知らせ, 受付たち, 手順, 全体 = [], [], [], [], []
    for 答 in 送信たち:
        p, r = _送信を読む(答, 回答日, 今の行)
        if r:
            赤 += r
            continue
        外 = [k for k in (*p["answers"], *p["supp"]) if k not in 今の行]
        if 外:
            赤.append(f"受付 {p['receipt']}: 配った問いに無い鍵 {sorted(set(外))}（問いの行を配った時の物にそろえて渡す）")
            continue
        古い, 版の赤 = 答えの版(p["version"], 版)
        if 版の赤:
            赤.append(f"受付 {p['receipt']}: {版の赤}")
            continue
        受付たち.append({"受付番号": p["receipt"], "版": p["version"], "古い版": 古い, "回答日": 回答日})
        印 = f"受付: {p['receipt']}（版 {p['version'] or '無し'}{'・古い版' if 古い else ''}）"
        if p["free"]:
            全体.append(p["free"])
        for 鍵, 行 in 今の行.items():
            値たち, s = p["answers"].get(鍵, []), p["supp"].get(鍵, "")
            if not 値たち and not s:
                continue
            if str(行.get("回答", "")).strip().startswith(取り下げの頭):   # 下げた問い＝答えを受け付けない（開き直さない）
                知らせ.append(f"問い {行['問いの番号']} は取り下げた＝受付 {p['receipt']} の答えは受け付けない")
                continue
            if p["receipt"] in 貼った.get(鍵, set()):
                continue
            語たち, k = _答えの語(行, 値たち, p["labels"].get(鍵, []))
            知らせ += k
            a = "、".join(語たち)
            回答 = " ／ ".join(x for x in [a, f"補足: {s.replace(chr(10), ' / ')}" if s else "", 印] if x)
            if str(行.get("回答", "")).strip():
                新 = {**行, "回答": 回答, "回答日": 回答日, "反映済み": ""} if "反映済み" in 行 else {**行, "回答": 回答, "回答日": 回答日}
                手順.append({"する": "足す", "問いの番号": 行["問いの番号"], "回答": 回答, "回答日": 回答日, "行": 新})
            else:
                新 = {**行, "回答": 回答, "回答日": 回答日}
                手順.append({"する": "書く", "問いの番号": 行["問いの番号"], "回答": 回答, "回答日": 回答日})
            今の行[鍵] = 新
            貼った.setdefault(鍵, set()).add(p["receipt"])
    if 赤:
        return {"受付たち": [], "行たち": [], "全体の補足": "", "知らせ": 知らせ, "赤": 赤}
    return {"受付たち": 受付たち, "行たち": 手順, "全体の補足": "\n".join(全体), "知らせ": 知らせ, "赤": []}


def _状況(役: str) -> str:
    return _表.値の字("確認ページ", "状況", 役)


def 管理表の行(会社: str, 支給月: str | None, 用: str, 何のための質問か: str, 問いの数: int, URL: str, 載せた日: str,
             支給の月=None) -> dict:
    """管理表「確認ページ」タブの 1 行（管理表/ の書く口の 行たち に渡す形）。支給月が None なら「全社の決まり」。"""
    if 用 not in 用たち:
        raise ValueError(f"用 {用!r} は {'・'.join(用たち)} のどれか")
    return {
        "載せた日": 載せた日, "会社": 会社,
        "支給月": 支給月の名(支給月, 支給の月) if 支給月 else "全社の決まり",
        "何の確認か": 用, "何のための質問か": 何のための質問か, "問いの数": 問いの数,
        "確認ページ": URL, "答えていただいた日": "", "答えた方": "", "状況": _状況("待ち"),
    }


def 差し替えの行(前の行: dict) -> dict:
    """配り直した時、前の行の状況を 差し替え にする（鍵の列と書く列だけ）。"""
    return {"会社": 前の行["会社"], "載せた日": 前の行["載せた日"], "確認ページ": 前の行["確認ページ"], "状況": _状況("差し替え")}


def 取り下げの行(前の行: dict) -> dict:
    """配った確認ページの問いを全部下げた時、その行の状況を 取り下げ にする（鍵の列と書く列だけ）。"""
    return {"会社": 前の行["会社"], "載せた日": 前の行["載せた日"], "確認ページ": 前の行["確認ページ"], "状況": _状況("取り下げ")}


def お答えの行(前の行: dict, 答えていただいた日: str, 答えた方: str) -> dict:
    return {"会社": 前の行["会社"], "載せた日": 前の行["載せた日"], "確認ページ": 前の行["確認ページ"],
            "答えていただいた日": 答えていただいた日, "答えた方": 答えた方, "状況": _状況("答えた")}


# ── 呼び口 ────────────────────────────────────────────────

def _口(名: str, 入力: dict):
    if 名 == "作る":
        return 作る(入力)
    if 名 == "検査":
        return {"赤": 問いの検査(入力["問い"], 入力.get("内部の言葉", ()))}
    if 名 == "貼り戻し":
        return 貼り戻し(入力["問い"], 入力["答え"], 入力["回答日"], 入力.get("版"))   # 版を省くと赤（既定の空を畳んだ）
    if 名 == "管理表の行":
        return 管理表の行(**入力)
    raise SystemExit(f"口 {名!r} は 作る・検査・貼り戻し・管理表の行 のどれか")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("使い方: python3 確認ページ/確認ページ.py <作る|検査|貼り戻し|管理表の行> < 入力.json")
    out = _口(sys.argv[1], json.load(sys.stdin))
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    sys.exit(2 if isinstance(out, dict) and out.get("赤") else 0)
