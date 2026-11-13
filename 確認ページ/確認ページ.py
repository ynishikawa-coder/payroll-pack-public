"""確認ページ — 質問と回答の行から、配る用の 1 枚の自己完結 HTML と、その名・置き場・貼り戻し・管理表の 1 行を返す。

正本は質問と回答。確認ページは道具が起こす表示と配る用の写し（`docs/設計/Drive の型.md` §3）。
この道具は Drive を開かない。問いの一覧を受けて文字列を返すだけで、置くのは殻（環境の口）。
返す HTML は外へ通信しない（外の script・style・画像・fetch を持たない）。
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from html import escape
from pathlib import Path

ここ = Path(__file__).resolve().parent
根 = ここ.parent
if str(根) not in sys.path:
    sys.path.insert(0, str(根))
_spec = importlib.util.spec_from_file_location("確認ページ_段の解決", 根 / "初期設定" / "段の解決.py")
段 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(段)

from 芯.計算 import 暦  # noqa: E402  (締めた期間の式を 1 か所に)

雛形 = ここ / "雛形.html"
既定の支給の月 = "翌月"  # 初期設定/項目.json の 支払.支給の月 の既定・芯/計算/要る値 と同じ

用たち = ("立ち上げ", "毎月")
形たち = ("choose", "mismatch", "fact", "judge")
見当のとおり = "見当のとおり"
推奨の印 = "（推奨）"
自由記入 = "__自由記入__"
# 形ごとに道具が後ろへ足す選択肢（qa-html の 1 つの形）
足す選択肢 = {
    "choose": ["どちらでもない（補足に）"],
    "mismatch": ["どちらでもない（補足に）"],
    "judge": ["別の決め方（補足に）"],
    "fact": ["まだ分からない", "該当しない"],
}
既定の決まる事 = "給与の計算のしかた"
分かっている事の行の上限 = 2
# 既定で見る内部の言葉（呼ぶ側が 内部の言葉 の引数で足す）。顧客の語はここに書かない。
既定の内部の言葉 = ("立ち上げ", "照合", "逆算", "道具", "部品", "質問と回答", "03_マスタ", "04_台帳", "01_ルール", ".md")


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
    m = re.fullmatch(r"(\d{4})\.(\d{2})支給(?:（(\d{1,2})月分）)?", 支給月.strip())
    if not m:
        raise ValueError(f"支給月 {支給月!r} は YYYY.MM支給 の形でない")
    y, mm = int(m.group(1)), int(m.group(2))
    if not 1 <= mm <= 12:
        raise ValueError(f"支給月 {支給月!r} の月が 1〜12 でない")
    書いた = int(m.group(3)) if m.group(3) else None

    def 月分(語: str) -> int:
        return 暦.期間(f"{y:04d}-{mm:02d}", "末", 語)[1].month

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
    return f"{y:04d}.{mm:02d}支給（{M}月分）", 知らせ


def 支給月の名(支給月: str, 支給の月=None) -> str:
    """`支給月の名と知らせ` の名だけ（知らせは捨てる・`作る` は知らせも返す）。"""
    return 支給月の名と知らせ(支給月, 支給の月)[0]


def 置き場(組: str, 支給月: str, 支給の月=None) -> str:
    """確認ページを置くフォルダ。組が「事務所」なら事務所の根の 20_配る物/。支給の月は会社の `支払.支給の月`。"""
    月 = 支給月の名(支給月, 支給の月)
    if 組 == "事務所":
        return f"20_配る物/{月}/"
    return f"10_会社/{組}/20_配る物/{月}/"


def 名(組: str, 支給月: str, 版: int, 下書き: bool = False, 支給の月=None) -> str:
    if not isinstance(版, int) or 版 < 1:
        raise ValueError(f"版 {版!r} は 1 から")
    if not 組 or "/" in 組:
        raise ValueError(f"組 {組!r} が名に使えない")
    本 = f"確認ページ_{組}_{支給月の名(支給月, 支給の月)}_v{版}.html"
    return "下書き_" + 本 if 下書き else 本


def 次の版(組: str, 支給月: str, 今ある名: list[str], 支給の月=None) -> dict:
    """置き場に今ある名の一覧から、次に配る版と、差し替える前の版を返す。

    返す物: 版・名・下書きの名・置き場・前の版（無ければ None）。前の版は 差し替え の手順で 90_履歴/ へ移す。"""
    頭 = re.escape(f"確認ページ_{組}_{支給月の名(支給月, 支給の月)}_v")
    版たち = sorted(int(m.group(1)) for n in 今ある名 if (m := re.fullmatch(頭 + r"(\d+)\.html", n)))
    版 = (版たち[-1] + 1) if 版たち else 1
    return {
        "版": 版,
        "名": 名(組, 支給月, 版, 支給の月=支給の月),
        "下書きの名": 名(組, 支給月, 版, 下書き=True, 支給の月=支給の月),
        "置き場": 置き場(組, 支給月, 支給の月),
        "前の版": 名(組, 支給月, 版たち[-1], 支給の月=支給の月) if 版たち else None,
    }


def 差し替え(組: str, 支給月: str, 前の名: str, 消す日: str, 支給の月=None) -> dict:
    """配り直した時に前の版を 90_履歴/ へ `消す_<日>_` を付けて移す手順（殻が当てる）。"""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", 消す日):
        raise ValueError(f"消す日 {消す日!r} は YYYY-MM-DD でない")
    根 = "" if 組 == "事務所" else f"10_会社/{組}/"
    return {"する": "移す", "元": 置き場(組, 支給月, 支給の月) + 前の名, "先": f"{根}90_履歴/消す_{消す日}_{前の名}"}


# ── 問いの検査 ─────────────────────────────────────────────

def _選択肢(行: dict) -> list[str]:
    if isinstance(行.get("選択肢"), list):
        return [str(x).strip() for x in 行["選択肢"] if str(x).strip()]
    return [x.strip() for x in re.split(r"[／|｜]", str(行.get("答え方の例", ""))) if x.strip()]


def _分かっている事(行: dict) -> list[str]:
    v = 行.get("分かっている事")
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [x.strip() for x in v.splitlines() if x.strip()]
    return [f"今の見込みは「{行['見当']}」です。"] if str(行.get("見当", "")).strip() else []


def _鍵(番号: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", 番号)


def 問いの検査(行たち: list[dict], 内部の言葉: list[str] | tuple = ()) -> list[str]:
    """qa-html の決まりのうち機械で見られる物。決まり外れを赤の 1 行ずつで返す（空なら緑）。

    1 問 1 行・分かっている事 2 行まで・形が 4 つのどれか・選択肢 2 つ以上・推奨は 1 つ目だけ・内部の言葉を含まない・
    問いの番号が在って重ならない。"""
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
            赤.append(f"{id}: 質問が 2 行以上（1 問 1 行にする・分かっている事は別に渡す）")
        分かる = _分かっている事(行)
        if len(分かる) > 分かっている事の行の上限:
            赤.append(f"{id}: 分かっている事が {len(分かる)} 行（{分かっている事の行の上限} 行まで）")
        形 = 行.get("形", "judge")
        if 形 not in 形たち:
            赤.append(f"{id}: 形 {形!r} は {'・'.join(形たち)} のどれでもない")
        選 = _選択肢(行)
        if 形 != "fact" and len(選) < 2:
            赤.append(f"{id}: 選択肢が {len(選)} つ（2 つ以上）")
        推奨 = [j for j, o in enumerate(選) if o == 見当のとおり or o.endswith(推奨の印)]
        if len(推奨) > 1:
            赤.append(f"{id}: 推奨が {len(推奨)} つ（1 つだけ）")
        if any(j != 0 for j in 推奨):
            赤.append(f"{id}: 推奨が 1 つ目でない")
        if 見当のとおり in 選 and not str(行.get("見当", "")).strip():
            赤.append(f"{id}: 「{見当のとおり}」があるのに見当が空")
        見える = [問い, *分かる, *選, str(行.get("決まる事", ""))]
        for w in 語たち:
            for s in 見える:
                if w in s:
                    赤.append(f"{id}: 内部の言葉「{w}」: {s[:40]}")
                    break
    return 赤


# ── HTML ──────────────────────────────────────────────────

def _見出し(用: str, 支給月: str, 数: int, 支給の月=None) -> tuple[str, str]:
    if 用 == "立ち上げ":
        return "給与計算の設定のご確認", f"給与計算の設定で確かめたい事が {数} 件あります。"
    月 = re.search(r"（(\d+)月分）", 支給月の名(支給月, 支給の月)).group(1)
    return f"{月} 月分 給与計算のご確認", f"{月} 月分の給与計算で確かめたい事が {数} 件あります。"


def _選択肢の行(鍵: str, 値: str, 見せる: str, 推奨: bool, 中身: str = "") -> str:
    印 = '<span class="tag-rec">推奨</span>' if 推奨 else ""
    小 = f"<small>{escape(中身)}</small>" if 中身 else ""
    return (f'<label class="opt"><input type="radio" name="{鍵}" value="{escape(値, True)}">'
            f"<span><b>{escape(見せる)}{印}</b>{小}</span></label>")


def _箱(行: dict, 順: int) -> str:
    鍵 = _鍵(str(行["問いの番号"]).strip())
    形 = 行.get("形", "judge")
    問い = str(行["質問"]).strip()
    選 = _選択肢(行)
    if 形 == "fact" and not 選:
        選 = ["分かる（補足に書く）"]
    opts = []
    for j, o in enumerate(選):
        推奨 = o == 見当のとおり or o.endswith(推奨の印)
        値 = o[: -len(推奨の印)] if o.endswith(推奨の印) else o
        見せる = f"{見当のとおり}（{行['見当']}）" if o == 見当のとおり else 値
        opts.append(_選択肢の行(鍵, 値, 見せる, 推奨 and j == 0))
    for o in 足す選択肢[形]:
        if o not in 選:
            opts.append(_選択肢の行(鍵, o, o, False))
    分かる = _分かっている事(行)
    決まる = str(行.get("決まる事", "")).strip() or 既定の決まる事
    return "\n".join([
        f'<fieldset class="q" data-qkey="{鍵}" data-qlabel="{escape(問い, True)}" data-kind="{形}">',
        f"<legend>{順}. {escape(問い)}</legend>",
        f'<div class="known">{"<br>".join(escape(x) for x in 分かる)}</div>' if 分かる else "",
        '<div class="opts">', *opts, "</div>",
        f'<p class="decides">{escape(決まる)}</p>',
        f'<div class="supp"><label for="supp_{鍵}">補足（自由に）</label>'
        f'<textarea id="supp_{鍵}" name="supp_{鍵}" rows="2"></textarea></div>',
        "</fieldset>",
    ]).replace("\n\n", "\n")


def 作る(入力: dict) -> dict:
    """確認ページを 1 枚起こす。

    入力: 組・支給月・用（立ち上げ／毎月）・問い（質問と回答の行の list）・今ある名（置き場の名の一覧・任意）・
          支給の月（会社の `支払.支給の月`・任意・無ければ既定の翌月で知らせ）・
          宛先（send か copy・既定 send）・宛名（任意）・内部の言葉（任意）。
    返す物: 赤（空でなければ HTML を返さない）・知らせ・版・名・下書きの名・置き場・前の版・問いの数・html。"""
    組, 支給月, 用 = 入力["組"], 入力["支給月"], 入力["用"]
    支給の月 = 入力.get("支給の月")
    知らせ = 支給月の名と知らせ(支給月, 支給の月)[1]
    if 用 not in 用たち:
        raise ValueError(f"用 {用!r} は {'・'.join(用たち)} のどれか")
    宛先 = 入力.get("宛先", "send")
    if 宛先 not in ("send", "copy"):
        raise ValueError(f"宛先 {宛先!r} は send か copy")
    行たち = 入力["問い"]
    版 = 次の版(組, 支給月, 入力.get("今ある名", []), 支給の月)
    赤 = 問いの検査(行たち, 入力.get("内部の言葉", ()))
    if 赤:
        return {"赤": 赤, "知らせ": 知らせ, **版, "問いの数": len(行たち), "html": None}
    題, 前書き = _見出し(用, 支給月, len(行たち), 支給の月)
    t = 雛形.read_text(encoding="utf-8")
    t = re.sub(r"^<!doctype html>\n<!--.*?-->\n", "<!doctype html>\n", t, count=1, flags=re.S)
    箱たち = "\n\n".join(_箱(行, i) for i, 行 in enumerate(行たち, 1))
    for k, v in (("{{題}}", 題), ("{{宛先}}", 宛先), ("{{宛名}}", 入力.get("宛名") or "ご確認のお願い"), ("{{前書き}}", 前書き)):
        t = t.replace(k, escape(v))
    t = t.replace("<!--問い-->", 箱たち)
    return {"赤": [], "知らせ": 知らせ, **版, "問いの数": len(行たち), "html": t}


# ── 貼り戻しと管理表 ─────────────────────────────────────────

def _写しを読む(写し: str) -> tuple[list[dict], str]:
    """qa-html の写す形の貼り戻しの文字列 → [{見出し, 回答, 補足}]・全体の補足。"""
    out, 全体, 中 = [], [], None
    for line in 写し.splitlines():
        if m := re.match(r"■ 問(\d+): (.*)$", line):
            out.append({"順": int(m.group(1)), "見出し": m.group(2), "回答": "", "補足": ""})
            中 = "問"
        elif line.startswith("■ その他・全体の意向:"):
            中 = "全体"
        elif 中 == "問" and (m := re.match(r"\s*→ 回答: (.*)$", line)):
            out[-1]["回答"] = "" if m.group(1) == "（未選択）" else m.group(1)
        elif 中 == "問" and (m := re.match(r"\s*→ 補足: (.*)$", line)):
            out[-1]["補足"] = m.group(1)
        elif 中 == "全体" and line.strip() and line.strip() != "（なし）":
            全体.append(line.strip())
    return out, "\n".join(全体)


def _元の答え(行: dict, 見えた答え: str) -> str:
    """画面の字（見当のとおり（X）・推奨の字）を質問と回答に書く答えの字へ戻す。"""
    if not 見えた答え:
        return ""
    if 見えた答え == 見当のとおり or 見えた答え.startswith(見当のとおり + "（"):
        return 見当のとおり
    return 見えた答え


def 貼り戻し(行たち: list[dict], 答え, 回答日: str) -> dict:
    """HTML の答えを質問と回答の行へ戻す。答え は写す形の文字列か、送る形のフォームの値（{鍵: 値, supp_鍵: 補足}）。

    返す物: 行たち（{問いの番号, 回答, 回答日}・答えの無い問いは出さない）・全体の補足・赤。
    回答 の字は「選んだ答え」か「選んだ答え ／ 補足: …」（補足だけなら「補足: …」）。"""
    赤, 戻す = [], []
    if isinstance(答え, str):
        読んだ, 全体 = _写しを読む(答え)
        if len(読んだ) != len(行たち):
            return {"行たち": [], "全体の補足": 全体, "赤": [f"写しの問いが {len(読んだ)} つ（配った問いは {len(行たち)} つ）"]}
        組たち = []
        for 行, r in zip(行たち, 読んだ):
            if r["見出し"] != str(行["質問"]).strip():
                赤.append(f"問{r['順']}: 見出しが配った問いと違う")
            組たち.append((行, r["回答"], r["補足"]))
    else:
        全体 = str(答え.get(自由記入, "")).strip()
        組たち = []
        for 行 in 行たち:
            鍵 = _鍵(str(行["問いの番号"]).strip())
            v = 答え.get(鍵, "")
            v = "、".join(map(str, v)) if isinstance(v, list) else str(v)
            組たち.append((行, v.strip(), str(答え.get("supp_" + 鍵, "")).strip()))
    if 赤:
        return {"行たち": [], "全体の補足": 全体, "赤": 赤}
    for 行, a, s in 組たち:
        a = _元の答え(行, a)
        if not a and not s:
            continue
        回答 = a + (f" ／ 補足: {s}" if a and s else "") + (f"補足: {s}" if s and not a else "")
        戻す.append({"問いの番号": str(行["問いの番号"]).strip(), "回答": 回答, "回答日": 回答日})
    return {"行たち": 戻す, "全体の補足": 全体, "赤": []}


def 管理表の行(会社: str, 支給月: str | None, 用: str, 何のための質問か: str, 問いの数: int, URL: str, 載せた日: str,
             支給の月=None) -> dict:
    """管理表「確認ページ」タブの 1 行（管理表/ の書く口の 行たち に渡す形）。支給月が None なら「全社の決まり」。"""
    if 用 not in 用たち:
        raise ValueError(f"用 {用!r} は {'・'.join(用たち)} のどれか")
    return {
        "載せた日": 載せた日, "会社": 会社,
        "支給月": 支給月の名(支給月, 支給の月) if 支給月 else "全社の決まり",
        "何の確認か": 用, "何のための質問か": 何のための質問か, "問いの数": 問いの数,
        "確認ページ": URL, "答えていただいた日": "", "答えた方": "", "状況": "お答え待ち",
    }


def 差し替えの行(前の行: dict) -> dict:
    """配り直した時、前の行の状況を 差し替え にする（鍵の列と書く列だけ）。"""
    return {"会社": 前の行["会社"], "載せた日": 前の行["載せた日"], "確認ページ": 前の行["確認ページ"], "状況": "差し替え"}


def お答えの行(前の行: dict, 答えていただいた日: str, 答えた方: str) -> dict:
    return {"会社": 前の行["会社"], "載せた日": 前の行["載せた日"], "確認ページ": 前の行["確認ページ"],
            "答えていただいた日": 答えていただいた日, "答えた方": 答えた方, "状況": "お答えいただいた"}


# ── 呼び口 ────────────────────────────────────────────────

def _口(名: str, 入力: dict):
    if 名 == "作る":
        return 作る(入力)
    if 名 == "検査":
        return {"赤": 問いの検査(入力["問い"], 入力.get("内部の言葉", ()))}
    if 名 == "貼り戻し":
        return 貼り戻し(入力["問い"], 入力["答え"], 入力["回答日"])
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
