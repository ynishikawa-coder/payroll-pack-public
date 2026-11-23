#!/usr/bin/env python3
"""口の約束（給与エージェント）— 口の一覧（`口の一覧.md`）の行を、口ごとの約束の条（渡す物・返す物・守る事の 1 文ずつ）に
分けて指紋を付け、各社の側（殻）の試験がどの条を確かめたかの表と照らす判定。

なぜ在るか（根治・2026-11-23）: 口の一覧の「守る事」は文に書いただけで、殻の口の実物を口の決まりと照らす試験が無い口が
  在った（読み直して照らす・在り処を書かない・1 件ずつ置く…が紙の上だけ）。条を正本（この 1 か所の分け方と指紋）から
  機械で取り出し、殻は条ごとに確かめた試験か、試験の無い訳（穴）を持つ。口の一覧の文を変えると指紋が変わり、
  見直していない殻は赤になる＝条を変えたのに殻の試験を見直さずに通らない。
覆いの印は試験の中に置く（2026-11-23）: 前は殻の別の表に「条 → 試験の名」を書き、道具は名が在るかだけを見た。名の在る
  試験が条と違う物を試していても緑で通った。今は条を確かめる試験が自分の本文に `口の約束 <指紋>` の印を持ち、条の文が
  変わると指紋が変わって試験そのものを直さないと赤になる（表だけ直して通らない）。
印は確かめの文に付ける（2026-11-23）: 印が在るかだけを見ると、assert True だけの試験・skip や xfail で飛ばされる試験の
  印でも緑で通った。今は印のコメントが条を確かめる文（定数でない assert・pytest.raises / warns の with・self.assert…）の
  真上か同じ行に在り、試験が飛ばされない（試験・class の飾り・module の pytestmark・本文の skip/xfail/importorskip の
  呼び出しが無い）時だけ印を数え、ほかは外れに出す（docstring の印は数えない）。
残る穴: 印の付いた確かめが条の意味を本当に確かめるかと、fixture・手伝いの関数の中で飛ばす試験は機械で見られない
  （印の付いた試験の中身はレビューの目で照らす）。

使い方:
  python3 口の約束.py 一覧 [--パック <dir>]
      条の並びを JSON で出す（[{"口", "欄", "文", "指紋"}...]）。欄は 渡す物・返す物・守る事。
  python3 口の約束.py 照らす <殻の穴の表.json> --殻の根 <dir> [--パック <dir>]
      殻の穴の表: {"穴": [{"口", "指紋", "訳"}...]}（覆いは書かない＝試験の中の印が正本）。
      殻の根の下の `test_*.py` の試験（`def test_…`）の本文の `口の約束 <指紋>` の印（確かめの文の真上か同じ行・
      飛ばされない試験だけ）を集める。今の条の全部が
      印（試験が 1 つ以上）か 穴（訳が空でない）のどちらか 1 つに在り、印と表に今の一覧に無い指紋（古い条）が無く、
      数えない印（試験の外・確かめに付いていない・飛ばされる試験の中）が無ければ緑。
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
_外す_dir = {".git", "node_modules", "__pycache__", ".venv", "venv"}
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
    """文が指す file → パックの file。根・plugin・plugin/bin の下の path か、dir を書かない名ならパックにただ 1 つの同じ名の file。"""
    for d in (パック, パック / 一覧の在り処.parent, パック / 一覧の在り処.parent / "bin"):
        if (d / path).is_file():
            return d / path
    if "/" not in path:
        hits = [p for p in パック.rglob(path) if not (_外す_dir | {"tests"}) & set(p.relative_to(パック).parts)]
        return hits[0] if len(hits) == 1 else None
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
    hits = [p for p in パック.rglob(f"{名}.py") if not ((_外す_dir | {"tests"}) & set(p.relative_to(パック).parts))]
    return hits[0] if len(hits) == 1 else None


_の形 = re.compile(r"`?([\w/ぁ-んァ-ヶ一-龥ー]+\.py)`?\s*の\s*`([^`\s(.]+)")
_囲み = re.compile(r"`([^`]*)`")
_口の形 = re.compile(r"([^\s]+\.py) (.+)")
_部品の形 = re.compile(r"([^./\s]+)\.([^.\s]+)")
_file_の形 = re.compile(r"[^\s<>*{}]+\.(?:py|md|json|sh|txt|csv|html|yaml|yml|toml)")   # 囲みの全部が file の名（型の <名>・* は名と読まない）


def 死んだ名(パック: Path, text: str, 口の行だけ: bool = True) -> list[str]:
    """文が指すパックの部品の名が在るか（名の指し方の正本＝この 1 か所。口の一覧と plugin の文の試験が同じ物を読む）。
    指し方は 4 つ: 〈file〉 の 〈名〉（名を ` で囲む・上の段の名・file の ` は無くてもよい）・〈file〉 〈名〉・〈名〉（全体を ` で囲む・
    道具の口の名＝その file の字の定数か上の段の名）・〈file〉（全体を ` で囲む・拡張子で file と読み部品.名と読まない）・〈部品〉.〈名〉（` で囲む・部品がパックに在る時だけ・部品の中の file の名も可・
    事務所の設定の項目の名〔初期設定/項目.json〕は名のまま照らす）。file は .py で、dir を書かなければパックにただ 1 つの同じ名。path の file が無いのも外れ（黙って飛ばさない）。
    口の行だけ: 真なら `| 〔口:` で始まる行だけ（口の一覧）、偽なら全部の行（plugin の docstring・md）。無い名の文の並び。"""
    項目 = {x["項目"] for x in json.loads((パック / "初期設定" / "項目.json").read_text(encoding="utf-8"))["項目"]}
    外れ: list[str] = []
    for line in text.splitlines():
        if 口の行だけ and not line.startswith("| 〔口:"):
            continue
        の_file = set()
        for m in _の形.finditer(line):
            の_file.add(m.group(1))
            f = _置き場(パック, m.group(1))
            if f is None:
                外れ.append(f"指す file が無い: {m.group(1)}")
            elif m.group(2) not in _上の名(f):
                外れ.append(f"{m.group(1)} に {m.group(2)} が無い")
        囲み = [m.group(1) for m in _囲み.finditer(line)]   # ` の対は頭から組む（対の間の字を名と読まない）
        for m in filter(None, map(_口の形.fullmatch, 囲み)):
            f = _置き場(パック, m.group(1))
            if f is None:
                外れ.append(f"指す file が無い: {m.group(1)}")
                continue
            字 = _字の定数(f) | _上の名(f)
            外れ += [f"{m.group(1)} に口 {n} が無い" for n in m.group(2).split("・") if n not in 字]
        外れ += [f"指す file が無い: {x}" for x in 囲み
                 if _file_の形.fullmatch(x) and x not in の_file and _置き場(パック, x) is None]
        for m in filter(None, map(_部品の形.fullmatch, (x for x in 囲み if not _file_の形.fullmatch(x)))):
            if m.group(0) in 項目:   # 事務所の設定の項目の名（正本 初期設定/項目.json）
                continue
            f = _部品の在り処(パック, m.group(1))
            if f is not None and m.group(2) not in _上の名(f) and not (f.parent / f"{m.group(2)}.py").is_file():
                外れ.append(f"{m.group(1)} に {m.group(2)} が無い")
    return 外れ


印の書き方 = re.compile(r"口の約束 ([0-9a-f]{12})")


_飛ばす名 = {"skip", "skipif", "xfail", "skipIf", "skipUnless", "expectedFailure", "importorskip", "skipTest"}
_確かめの名 = {"raises", "warns", "deprecated_call", "assertRaises", "assertRaisesRegex", "assertWarns", "assertWarnsRegex"}


def _名たち(n) -> set[str]:
    import ast
    return {x.id if isinstance(x, ast.Name) else x.attr for x in ast.walk(n) if isinstance(x, (ast.Name, ast.Attribute))}


def _呼ぶ名(c) -> str:
    import ast
    f = c.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""


def _中の節(fn):
    """試験の本文の節（中の def・class・lambda の中は見ない）。"""
    import ast
    待ち = list(fn.body)
    while 待ち:
        n = 待ち.pop()
        yield n
        待ち += [c for c in ast.iter_child_nodes(n)
               if not isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))]


def _確かめ(n) -> bool:
    """条を確かめる文か: 定数でない assert・pytest.raises / warns の with・assert で始まる名の呼び出し（self.assertEqual 等）。
    いつも同じ答えの assert（assert True・assert 1・assert "字"・assert 1 == 1 のように名を読まない物・assert (x, "訳")）は確かめでない。"""
    import ast
    if isinstance(n, ast.Assert):
        return bool(_名たち(n.test)) and not (isinstance(n.test, ast.Tuple) and n.test.elts)
    if isinstance(n, (ast.With, ast.AsyncWith)):
        return any(isinstance(i.context_expr, ast.Call) and _呼ぶ名(i.context_expr) in _確かめの名 for i in n.items)
    if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
        return _呼ぶ名(n.value).startswith("assert")
    return False


def _飛ばす訳(fn, 包み: list, 頭の印: bool) -> str | None:
    """試験が飛ばされる（skip・xfail）なら訳。飾り（試験・class）・module の pytestmark・本文の skip/xfail/importorskip の呼び出し。"""
    import ast
    for d in fn.decorator_list:
        if _名たち(d) & _飛ばす名:
            return "試験の飾りに skip か xfail"
    for k in 包み:
        if any(_名たち(d) & _飛ばす名 for d in k.decorator_list):
            return f"class {k.name} の飾りに skip か xfail"
    if 頭の印:
        return "module の pytestmark に skip か xfail"
    for n in _中の節(fn):
        if isinstance(n, ast.Call) and _呼ぶ名(n) in _飛ばす名:
            return f"本文で {_呼ぶ名(n)} を呼ぶ"
    return None


def _試験たち(木):
    """(試験の def, 包む class の並び)。module の上の段と class の中（入れ子も）の def test_…。"""
    import ast
    def 下(節, 包み):
        for n in 節:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_"):
                yield n, 包み
            elif isinstance(n, ast.ClassDef):
                yield from 下(n.body, 包み + [n])
    yield from 下(木.body, [])


def 印を集める(殻の根: Path) -> tuple[dict[str, list[str]], list[str]]:
    """殻の根の下の test_*.py から 試験の本文の `口の約束 <指紋>` の印を集める。
    印が数えられるのは、印のコメントが条を確かめる文（_確かめ）の真上（コメントの行だけを挟んでよい）か同じ行に在り、
    その試験が飛ばされない（_飛ばす訳 が無い）時だけ。数えない印は外れの文に出す（条は確かめていない条でも赤になる）。
    → ({指紋: ["<path>::<試験の名>"...]}, 外れの文の並び)。"""
    import ast
    印: dict[str, list[str]] = {}
    外れ: list[str] = []
    for f in sorted(殻の根.rglob("test_*.py")):
        rel = f.relative_to(殻の根)
        if _外す_dir & set(rel.parts):
            continue
        text = f.read_text(encoding="utf-8")
        if not 印の書き方.search(text):
            continue
        行 = text.splitlines()
        木 = ast.parse(text)
        頭の印 = any(isinstance(n, (ast.Assign, ast.AnnAssign)) and "pytestmark" in _名たち(n) and _名たち(n) & _飛ばす名
                   for n in 木.body)
        中: set[int] = set()
        for fn, 包み in _試験たち(木):
            名 = f"{rel.as_posix()}::{fn.name}"
            中 |= set(range(fn.lineno, (fn.end_lineno or fn.lineno) + 1))
            印たち = [(i, m.group(1)) for i in range(fn.lineno, (fn.end_lineno or fn.lineno) + 1)
                    for m in 印の書き方.finditer(行[i - 1])]
            if not 印たち:
                continue
            訳 = _飛ばす訳(fn, 包み, 頭の印)
            if 訳:
                外れ.append(f"印の試験が飛ばされる: {名}（{訳}＝条を確かめない。飛ばさずに確かめるか、穴に訳を書く）")
                continue
            確かめ = [(n.lineno, n.end_lineno or n.lineno) for n in _中の節(fn) if _確かめ(n)]
            for i, fp in 印たち:
                付く = any(頭 <= i <= 末 for 頭, 末 in 確かめ) or (
                    行[i - 1].lstrip().startswith("#")
                    and any(頭 > i and all(行[j - 1].lstrip().startswith("#") or not 行[j - 1].strip() for j in range(i + 1, 頭))
                            for 頭, _ in 確かめ))
                if 付く:
                    印.setdefault(fp, []).append(名)
                else:
                    外れ.append(f"印が確かめに付いていない: {rel.as_posix()}:{i} 口の約束 {fp}"
                                "（印は条を確かめる assert・pytest.raises の真上のコメントか同じ行に置く。いつも真の assert は確かめでない）")
        for i, line in enumerate(行, 1):
            if i not in 中:
                外れ += [f"印が試験の外: {rel.as_posix()}:{i} 口の約束 {m.group(1)}（試験 def test_… の本文に置く）"
                         for m in 印の書き方.finditer(line)]
    return 印, 外れ


def 照らす(条: list[dict], 表: dict, 印: dict[str, list[str]]) -> list[str]:
    """殻の穴の表と試験の印を今の条と照らす。外れの文の並び（空なら緑）。"""
    今 = {c["指紋"]: c for c in 条}
    外れ: list[str] = []
    if "覆い" in 表:
        外れ.append("殻の表に 覆い が在る（覆いは試験の本文の `口の約束 <指紋>` の印で持つ＝表から消す）")
    行たち = 表.get("穴", [])
    if not isinstance(行たち, list):
        return 外れ + ["殻の表の 穴 が並びでない"]
    見た: set[str] = set()
    for r in 行たち:
        fp, 口 = str(r.get("指紋", "")), str(r.get("口", ""))
        if fp not in 今:
            外れ.append(f"穴: 今の口の一覧に無い指紋 {fp}（口「{口}」・条が変わったか消えた＝見直して表を直す）")
            continue
        if 今[fp]["口"] != 口:
            外れ.append(f"穴: 指紋 {fp} は口「{今[fp]['口']}」の条（表は「{口}」）")
        if fp in 見た:
            外れ.append(f"穴: 指紋 {fp} が表に 2 度")
        見た.add(fp)
        if fp in 印:
            外れ.append(f"穴: 指紋 {fp}（口「{口}」）は試験 {印[fp][0]} が印で確かめている（穴から消す）")
        if not str(r.get("訳", "")).strip():
            外れ.append(f"穴: 指紋 {fp}（口「{口}」）に訳が無い")
    for fp, 試験 in 印.items():
        if fp not in 今:
            外れ.append(f"印: 今の口の一覧に無い指紋 {fp}（{'・'.join(試験)}・条が変わったか消えた＝試験を見直して印を直す）")
    for fp, c in 今.items():
        if fp not in 見た and fp not in 印:
            外れ.append(f"殻が確かめていない条 {fp}: 口「{c['口']}」の{c['欄']}「{c['文'][:60]}」")
    return 外れ


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("一覧", "照らす") or (argv[0] == "照らす" and (len(argv) < 2 or "--殻の根" not in argv[:-1])):
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
    殻 = Path(値("--殻の根"))
    if not 殻.is_dir():
        print(f"殻の根が無い: {殻}", file=sys.stderr)
        return 2
    印, 外れ = 印を集める(殻)
    外れ += 照らす(条, 表, 印)
    for x in 外れ:
        print(x)
    if not 外れ:
        穴 = len(表.get("穴", []))
        print(f"緑: 条 {len(条)}（試験の印 {len(条) - 穴}・穴 {穴}）")
    return 1 if 外れ else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:  # noqa: BLE001  壊れた回を結果（1）と分ける
        print(f"✗ 道具が壊れた（口の約束・終わりの値 2＝結果ではない）: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
