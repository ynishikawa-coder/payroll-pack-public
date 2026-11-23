#!/usr/bin/env python3
"""口の約束（給与エージェント）— 口の一覧（`口の一覧.md`）の行を、口ごとの約束の条（渡す物・返す物・守る事の 1 文ずつ）に
分けて指紋を付け、各社の側（殻）の試験がどの条を確かめたかの表と照らす判定。

なぜ在るか（根治・2026-11-23）: 口の一覧の「守る事」は文に書いただけで、殻の口の実物を口の決まりと照らす試験が無い口が
  在った（読み直して照らす・在り処を書かない・1 件ずつ置く…が紙の上だけ）。条を正本（この 1 か所の分け方と指紋）から
  機械で取り出し、殻は条ごとに確かめた試験の名か、試験の無い訳（穴）を表に書く。口の一覧の文を変えると指紋が変わり、
  殻の表が古いと赤になる＝条を変えたのに殻の試験を見直さずに通らない。

使い方:
  python3 口の約束.py 一覧 [--パック <dir>]
      条の並びを JSON で出す（[{"口", "欄", "文", "指紋"}...]）。欄は 渡す物・返す物・守る事。
  python3 口の約束.py 照らす <殻の表.json> [--パック <dir>] [--殻の根 <dir>]
      殻の表: {"覆い": [{"口", "指紋", "試験": ["<path>::<試験の名>"...]}...],
               "穴":   [{"口", "指紋", "訳"}...]}
      今の条の全部が 覆い（試験が 1 つ以上）か 穴（訳が空でない）のどちらか 1 つに在り、表に今の一覧に無い指紋
      （古い条）が無ければ緑。--殻の根 を渡すと、試験の path が在り、その file に試験の名の def が在るかも照らす。
  終わりの値: 0＝緑・1＝赤（外れを標準出力へ 1 行ずつ）・2＝道具が壊れた・使い方の誤り（結果ではない）。
パックの口の一覧は パックの場所.py で探す（見つからなければ照らさずに止める）。Python 3 の標準ライブラリだけ。外を開かない。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import パックの場所 as 場所  # noqa: E402

一覧の在り処 = Path("plugins") / "payroll-agent" / "口の一覧.md"
欄たち = ("渡す物", "返す物", "守る事")
口の書き方 = re.compile(r"^〔口: ([^〕]+)〕$")
_開き, _閉じ = "（(「『", "）)」』"


def 文に分ける(字: str) -> list[str]:
    """括弧（（）・()・「」・『』）の外の 。 で切る。空の文は捨てる。"""
    out, 今, 深さ = [], "", 0
    for c in 字:
        今 += c
        if c in _開き:
            深さ += 1
        elif c in _閉じ and 深さ:
            深さ -= 1
        elif c == "。" and 深さ == 0:
            out.append(今.strip().rstrip("。"))
            今 = ""
    if 今.strip():
        out.append(今.strip().rstrip("。"))
    return [s for s in out if s]


def 指紋(口: str, 欄: str, 文: str) -> str:
    return hashlib.sha256(f"{口}\0{欄}\0{文}".encode("utf-8")).hexdigest()[:12]


def 条たち(text: str) -> list[dict]:
    """口の一覧の md → 条の並び。表の形が崩れた行（列の数が違う・口の名の形でない）は例外（黙って捨てない）。"""
    out: list[dict] = []
    for line in text.splitlines():
        if not line.startswith("| 〔口:"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) != 1 + len(欄たち):
            raise ValueError(f"口の一覧の行の列が {len(cells)}（{1 + len(欄たち)} のはず）: {line[:40]}")
        m = 口の書き方.match(cells[0])
        if not m:
            raise ValueError(f"口の一覧の 1 列目が口の名の形でない: {cells[0]}")
        口 = m.group(1)
        for 欄, 字 in zip(欄たち, cells[1:]):
            文たち = 文に分ける(字) if 欄 == "守る事" else ([字] if 字 else [])
            if not 文たち:
                raise ValueError(f"口「{口}」の {欄} が空")
            out += [{"口": 口, "欄": 欄, "文": s, "指紋": 指紋(口, 欄, s)} for s in 文たち]
    if not out:
        raise ValueError("口の一覧に口の行が 1 つも無い")
    return out


def _置き場(パック: Path, path: str) -> Path | None:
    for d in (パック, パック / 一覧の在り処.parent, パック / 一覧の在り処.parent / "bin"):
        if (d / path).is_file():
            return d / path
    return None


def _上の名(f: Path) -> set[str]:
    import ast
    out: set[str] = set()
    for n in ast.parse(f.read_text(encoding="utf-8")).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                out |= {x.id for x in ast.walk(t) if isinstance(x, ast.Name)}
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            out |= {(a.asname or a.name).split(".")[0] for a in n.names}
    return out


def _字の定数(f: Path) -> set[str]:
    import ast
    return {n.value for n in ast.walk(ast.parse(f.read_text(encoding="utf-8")))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def _部品の在り処(パック: Path, 名: str) -> Path | None:
    """`月次`・`確認ページ`・`設問` → パックの部品の file（`<名>/__init__.py`・`<名>/<名>.py`・ただ 1 つの `**/<名>.py`）。無ければ None。"""
    for c in (パック / 名 / "__init__.py", パック / 名 / f"{名}.py", パック / f"{名}.py"):
        if c.is_file():
            return c
    hits = [p for p in パック.rglob(f"{名}.py") if not ({"tests", ".git"} & set(p.relative_to(パック).parts))]
    return hits[0] if len(hits) == 1 else None


def 死んだ名(パック: Path, text: str) -> list[str]:
    """口の一覧の行が指すパックの部品の名が在るか。`<path>.py` の `<名>`（上の段の名）・`<path>.py <名>・<名>`（道具の口の名＝
    その file の字の定数）・`<部品>.<名>`（部品がパックに在る時だけ・事務所の設定の項目の名
    〔初期設定/項目.json〕は名のまま照らす）。無い名の文の並び。"""
    項目 = {x["項目"] for x in json.loads((パック / "初期設定" / "項目.json").read_text(encoding="utf-8"))["項目"]}
    外れ: list[str] = []
    for line in text.splitlines():
        if not line.startswith("| 〔口:"):
            continue
        for m in re.finditer(r"`([^`]+\.py)`\s*の\s*`([^`]+)`", line):
            f = _置き場(パック, m.group(1))
            if f is None:
                外れ.append(f"指す file が無い: {m.group(1)}")
            elif m.group(2) not in _上の名(f):
                外れ.append(f"{m.group(1)} に {m.group(2)} が無い")
        for m in re.finditer(r"`([^`\s]+\.py) ([^`]+)`", line):
            f = _置き場(パック, m.group(1))
            if f is None:
                外れ.append(f"指す file が無い: {m.group(1)}")
                continue
            字 = _字の定数(f) | _上の名(f)
            外れ += [f"{m.group(1)} に口 {n} が無い" for n in m.group(2).split("・") if n not in 字]
        for m in re.finditer(r"`([^`./\s]+)\.([^`.\s]+)`", line):
            if m.group(0).strip("`") in 項目:   # 事務所の設定の項目の名（正本 初期設定/項目.json）
                continue
            f = _部品の在り処(パック, m.group(1))
            if f is not None and m.group(2) not in _上の名(f):
                外れ.append(f"{m.group(1)} に {m.group(2)} が無い")
    return 外れ


def 照らす(条: list[dict], 表: dict, 殻の根: Path | None = None) -> list[str]:
    """殻の表を今の条と照らす。外れの文の並び（空なら緑）。"""
    今 = {c["指紋"]: c for c in 条}
    外れ: list[str] = []
    見た: dict[str, str] = {}
    for 種, 行たち in (("覆い", 表.get("覆い", [])), ("穴", 表.get("穴", []))):
        if not isinstance(行たち, list):
            外れ.append(f"殻の表の {種} が並びでない")
            continue
        for r in 行たち:
            fp, 口 = str(r.get("指紋", "")), str(r.get("口", ""))
            if fp not in 今:
                外れ.append(f"{種}: 今の口の一覧に無い指紋 {fp}（口「{口}」・条が変わったか消えた＝試験を見直して表を直す）")
                continue
            if 今[fp]["口"] != 口:
                外れ.append(f"{種}: 指紋 {fp} は口「{今[fp]['口']}」の条（表は「{口}」）")
            if fp in 見た:
                外れ.append(f"{種}: 指紋 {fp} が表に 2 度（{見た[fp]} と {種}）")
            見た[fp] = 種
            if 種 == "覆い":
                試験 = r.get("試験") or []
                if not 試験:
                    外れ.append(f"覆い: 指紋 {fp}（口「{口}」）に試験が無い（無いなら 穴 に訳を書く）")
                for t in 試験:
                    外れ += _試験の在り処(str(t), 殻の根)
            elif not str(r.get("訳", "")).strip():
                外れ.append(f"穴: 指紋 {fp}（口「{口}」）に訳が無い")
    for fp, c in 今.items():
        if fp not in 見た:
            外れ.append(f"殻が確かめていない条 {fp}: 口「{c['口']}」の{c['欄']}「{c['文'][:60]}」")
    return 外れ


def _試験の在り処(t: str, 殻の根: Path | None) -> list[str]:
    if "::" not in t:
        return [f"試験の名の形が違う（<path>::<試験の名>）: {t}"]
    if 殻の根 is None:
        return []
    path, 名 = t.split("::", 1)
    f = 殻の根 / path
    if not f.is_file():
        return [f"試験の file が無い: {path}"]
    if not re.search(rf"^\s*def {re.escape(名)}\(", f.read_text(encoding="utf-8"), re.M):
        return [f"試験が無い: {t}"]
    return []


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("一覧", "照らす") or (argv[0] == "照らす" and len(argv) < 2):
        print(__doc__.split("使い方:")[1].split("パックの口の一覧は")[0], file=sys.stderr)
        return 2
    def 値(名: str) -> str | None:
        return argv[argv.index(名) + 1] if 名 in argv[:-1] else None
    パック = 場所.探す(値("--パック"))
    if パック is None:
        print(場所.分からない訳("口の一覧を読めず口の約束を照らせない", 値("--パック")), file=sys.stderr)
        return 2
    条 = 条たち((パック / 一覧の在り処).read_text(encoding="utf-8"))
    if argv[0] == "一覧":
        print(json.dumps(条, ensure_ascii=False, indent=1))
        return 0
    表 = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    殻 = 値("--殻の根")
    外れ = 照らす(条, 表, Path(殻) if 殻 else None)
    for x in 外れ:
        print(x)
    if not 外れ:
        穴 = len(表.get("穴", []))
        print(f"緑: 条 {len(条)}（試験 {len(条) - 穴}・穴 {穴}）")
    return 1 if 外れ else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:  # noqa: BLE001  壊れた回を結果（1）と分ける
        print(f"✗ 道具が壊れた（口の約束・終わりの値 2＝結果ではない）: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
