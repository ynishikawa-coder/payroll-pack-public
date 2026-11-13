"""骨の自己検査。

1. 設計の目次（docs/設計/README.md）の全行の file・dir が在るか。
2. 顧客の語が repo に載っていないか（語の束は repo に持たない。環境から渡す。無ければ skip）。
3. 版の約束（docs/版の出し方.md）: 「互換が切れる:」は行の頭・型の版の上げに印・呼び口を変えた枝は CHANGELOG も変える。
4. 入れてよい物の線（docs/設計/入れてよい物.md）: 製品の名・事務所と側の名が載っていないか・直しはどの事務所にも当たる型の版の上げか。
   束と外しの一覧は tests/data/ の 1 か所。
"""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parent.parent
目次 = 根 / "docs" / "設計" / "README.md"

# 目次から消えてはいけない最低限の行。
要る設計書 = {
    f"docs/設計/{名}.md" for 名 in ("勤怠の形", "会社の決まり", "Drive の型", "法の表", "確かめと仮", "寄せる道具", "入れてよい物")
}
要る置き場 = {
    "法の表/", "芯/計算/", "芯/集計/", "入口/", "出口/",
    "初期設定/", "有給/", "管理表/", "道具/寄せ/", "tests/作り物/",
}
見ない = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}


def 目次の行(text: str) -> list[str]:
    """表の行から path を拾う。path は行の中の最初の `…`。"""
    行たち = []
    for line in text.splitlines():
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        m = re.search(r"`([^`]+)`", line)
        if m:
            行たち.append(m.group(1))
    return 行たち


def 無い物(text: str, base: Path) -> list[str]:
    out = []
    for p in 目次の行(text):
        target = base / p
        if p.endswith("/"):
            if not (target / "README.md").is_file():
                out.append(p + "README.md")
        elif not target.is_file():
            out.append(p)
    return out


def test_目次が在る():
    assert 目次.is_file()


def test_目次の全行の物が在る():
    assert 無い物(目次.read_text(encoding="utf-8"), 根) == []


def test_目次に最低限の行がある():
    rows = set(目次の行(目次.read_text(encoding="utf-8")))
    assert 要る設計書 <= rows
    assert 要る置き場 <= rows


def test_無い物を見つけられる(tmp_path):
    text = "| file | 中身 |\n|---|---|\n| `在る.md` | a |\n| `無い.md` | b |\n| `空/` | c |\n"
    (tmp_path / "在る.md").write_text("x", encoding="utf-8")
    (tmp_path / "空").mkdir()
    assert 無い物(text, tmp_path) == ["無い.md", "空/README.md"]


def 顧客の語() -> list[str]:
    words = []
    path = os.environ.get("PAYROLL_NG_WORDS_FILE", "").strip()
    if path:
        words += Path(path).read_text(encoding="utf-8").splitlines()
    words += os.environ.get("PAYROLL_NG_WORDS", "").splitlines()
    return sorted({w.strip() for w in words if w.strip() and not w.strip().startswith("#")})


def 載っている所(base: Path, words: list[str]) -> list[str]:
    hits = []
    for f in sorted(base.rglob("*")):
        if not f.is_file() or 見ない & set(f.relative_to(base).parts):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        name = str(f.relative_to(base))
        for w in words:
            if w in text or w in name:
                # 語そのものは出さない（出力に顧客の語を書かない）
                hits.append(f"{name}: 顧客の語の束の {words.index(w) + 1} 番目")
    return hits


def test_顧客の語が載っていない():
    words = 顧客の語()
    if not words:
        pytest.skip("顧客の語の束が渡されていない（PAYROLL_NG_WORDS_FILE / PAYROLL_NG_WORDS）")
    assert 載っている所(根, words) == []


def test_顧客の語を見つけられる(tmp_path):
    (tmp_path / "a.md").write_text("作り物の値だけ", encoding="utf-8")
    (tmp_path / "b.md").write_text("ここに禁じ語あり", encoding="utf-8")
    assert 載っている所(tmp_path, ["禁じ語"]) == ["b.md: 顧客の語の束の 1 番目"]


# ---- 3. 版の約束（docs/版の出し方.md の CHANGELOG）----
CHANGELOG = 根 / "CHANGELOG.md"
印 = "互換が切れる:"
印の無い最後の型の版 = 5  # v0.1.3 までの節は書き替えない（出した版の記録）。6 からは型の版の行に印が要る


def 版の節(text: str) -> dict[str, list[str]]:
    """CHANGELOG の `## ` 見出しごとの行（`- ` の行だけ）。"""
    out, 今 = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            今 = line[3:].strip()
            out[今] = []
        elif 今 is not None and line.startswith("- "):
            out[今].append(line)
    return out


def 印の誤り(text: str, 型の版: int) -> list[str]:
    赤 = []
    for 節, 行たち in 版の節(text).items():
        for line in 行たち:
            if "互換が切れる" in re.sub(r"`[^`]*`", "", line) and not line.startswith("- " + 印):  # `…` の中は語の話
                赤.append(f"{節}: 「互換が切れる」が行の頭の `- {印}` の形でない: {line[:40]}")
    if 型の版 > 印の無い最後の型の版:
        行たち = [l for ls in 版の節(text).values() for l in ls if re.search(rf"型の版 *{型の版}(?!\d)", l)]
        if not any(l.startswith("- " + 印) for l in 行たち):
            赤.append(f"型の版 {型の版} の行に `{印}` が無い（型の版の上げは殻の渡す形が変わる）")
    return 赤


def test_互換が切れるの印の形と型の版():
    型の版 = json.loads((根 / "初期設定" / "型.json").read_text(encoding="utf-8"))["版"]
    assert 印の誤り(CHANGELOG.read_text(encoding="utf-8"), 型の版) == []


def test_印の誤りを見つけられる():
    t = "## 未リリース\n- 型の版 6: 列を足した\n- 寄せ: 互換が切れる 所がある\n## [v0.1.3] - 2026-11-12\n- 型の版 5\n"
    assert len(印の誤り(t, 6)) == 2
    assert 印の誤り("## 未リリース\n- 互換が切れる: 型の版 6: 列を足した\n- 決まり: 頭に `互換が切れる:` を書く\n", 6) == []
    assert 印の誤り("## [v0.1.3] - 2026-11-12\n- 型の版 5: 列\n", 5) == []


呼び口の形 = re.compile(r"\.(py|json|html)$")


def 呼び口を変えたのに_changelog_が無い(変えた: list[str]) -> list[str]:
    """main からの枝で変えた path → CHANGELOG を変えていなければ、変えた呼び口の path（tests/ の外の .py・.json・.html）。"""
    if "CHANGELOG.md" in 変えた:
        return []
    return [p for p in 変えた if 呼び口の形.search(p) and not p.startswith(("tests/", ".github/", ".claude/"))]


def _main_からの変更() -> list[str] | None:
    def git(*a):
        return subprocess.run(["git", "-C", str(根), *a], capture_output=True, text=True, check=True).stdout
    for ref in ("origin/main", "main"):
        try:
            基 = git("merge-base", "HEAD", ref).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
        return [l for l in git("-c", "core.quotepath=off", "diff", "--name-only", 基).splitlines() if l]
    return None


def test_呼び口を変えた枝は_changelog_に行を足す():
    変えた = _main_からの変更()
    if 変えた is None:
        pytest.skip("main が手元に無い（CI の浅い checkout など）")
    assert 呼び口を変えたのに_changelog_が無い(変えた) == []


def test_呼び口を変えたのに_changelog_が無いを見つけられる():
    assert 呼び口を変えたのに_changelog_が無い(["有給/有給.py", "tests/有給/test_x.py", "docs/a.md"]) == ["有給/有給.py"]
    assert 呼び口を変えたのに_changelog_が無い(["有給/有給.py", "CHANGELOG.md"]) == []
    assert 呼び口を変えたのに_changelog_が無い(["tests/有給/test_x.py", "docs/a.md"]) == []


# ---- 4. 入れてよい物の線（docs/設計/入れてよい物.md・⟦鍵:給与計算/パックの関所の機械の赤⟧）----
# a. 製品の名の束が .py・.json・.md・.html（md・html は <!-- 例 -->〜<!-- /例 --> の外）と file・dir の名に出たら赤
# b. 事務所・側の名の束が .py・.json に出たら赤（設計書の地の文は見ない）
# c. 直し（道具/寄せ/直し/直し_NNNN.json）に「どの事務所にも当たる型の版の上げ」の印が無ければ赤
#    （出た版の直しで印を持たない 2・4・5 は中身の指紋で固定＝版 ≤ 5 を名乗るだけの新しい file は通さない）
# 外し（tests/data/外し.json）は path ごと。外した file が当たらなくなったら、その行が赤（消し忘れを残さない）。
データ = 根 / "tests" / "data"
束を見ない = ("tests/data/", "CHANGELOG.md")  # 束そのもの・出した版の記録（書き替えない）
例の節 = re.compile(r"<!-- 例 -->.*?<!-- /例 -->", re.S)
# 出た版の直しのうち印を持たずに通る物（中身は変えない決まり）。どの事務所にも当たると棚卸しした 2・4・5 だけで、
# 中身の指紋（json を鍵の順に並べた字の sha256）が合う時だけ通す。直し 1・3 は便 2 で前の形の読み替えを外し、印を持つ。
出た直しの指紋 = {
    2: "a92e46b23f0fe2ea5e6983aa8e0d64887248699a533c98cdc908bd5bda44e541",
    4: "0575c42a1cd39fcb64a1cce4b9fde16211c1ca17c4a5399aba9eb287406751de",
    5: "bb6a01d64ddaaa18e8ed5f103edd6ff92552c71ca8bbc0c7f7a05b8246d25f2c",
}
当たるの印 = "全ての事務所"


def 束(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        w = line.split("#", 1)[0].strip()
        if w and w not in out:
            out.append(w)
    return out


def 外しの一覧(path: Path = データ / "外し.json") -> dict[str, dict[str, dict]]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return {k: {e["path"]: e for e in v} for k, v in d.items() if isinstance(v, list)}


def _files(base: Path):
    for f in sorted(base.rglob("*")):
        rel = f.relative_to(base)
        if 見ない & set(rel.parts) or not f.is_file():
            continue
        yield f, rel.as_posix()


def 製品の名の当たる所(base: Path, words: list[str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for f, name in _files(base):
        if name.startswith(束を見ない):
            continue
        text = ""
        if f.suffix in (".py", ".json", ".md", ".html"):
            try:
                text = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                text = ""
            if f.suffix in (".md", ".html"):
                text = 例の節.sub("", text)
        for w in words:
            if w in name:
                hits.setdefault(name, []).append(f"名に製品の名「{w}」")
            elif w in text:
                hits.setdefault(name, []).append(f"中に製品の名「{w}」")
    return hits


def 側の名の当たる所(base: Path, words: list[str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for f, name in _files(base):
        if name.startswith(束を見ない) or f.suffix not in (".py", ".json"):
            continue
        text = f.read_text(encoding="utf-8")
        for w in words:
            if w in text:
                hits.setdefault(name, []).append(f"中に事務所・側の名「{w}」")
    return hits


def 指紋(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def 直しの当たらない所(base: Path, 型の版: int, 出た=出た直しの指紋) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    dir_ = base / "道具" / "寄せ" / "直し"
    for f in sorted(dir_.glob("直し_*.json")) if dir_.is_dir() else []:
        name = f.relative_to(base).as_posix()
        d = json.loads(f.read_text(encoding="utf-8"))
        版 = d.get("版")
        m = re.fullmatch(r"直し_(\d{4})\.json", f.name)
        if not m or not isinstance(版, int) or int(m.group(1)) != 版:
            hits[name] = [f"file の名の番号と版（{版}）が違う"]
            continue
        if 版 in 出た and 指紋(d) == 出た[版]:
            continue  # 出た版の直し（中身は変えない・どの事務所にも当たると棚卸し済み）
        誤り = []
        if d.get("当たる") != 当たるの印:
            誤り.append(f"`\"当たる\": \"{当たるの印}\"` の印が無い（1 社のための直しは入れない）")
        if not isinstance(版, int) or d.get("前の版") != 版 - 1 or 版 > 型の版:
            誤り.append(f"型の版の上げの組でない（版 {版}・前の版 {d.get('前の版')}・初期設定/型.json の版 {型の版}）")
        if 誤り:
            hits[name] = 誤り
    return hits


def 線の赤(hits: dict[str, list[str]], 外し: dict[str, dict]) -> list[str]:
    赤 = [f"{p}: {m}" for p, ms in hits.items() if p not in 外し for m in ms]
    for p, e in 外し.items():
        if not str(e.get("なぜ", "")).strip() or not str(e.get("畳む", "")).strip():
            赤.append(f"外し {p}: なぜ と 畳む が要る")
        if p not in hits:
            赤.append(f"外し {p}: もう当たらない（外し.json からこの行を消す）")
    return 赤


def _型の版(base: Path = 根) -> int:
    return json.loads((base / "初期設定" / "型.json").read_text(encoding="utf-8"))["版"]


def test_製品の名が載っていない():
    hits = 製品の名の当たる所(根, 束(データ / "製品の名.txt"))
    assert 線の赤(hits, 外しの一覧()["製品の名"]) == []


def test_事務所と側の名が載っていない():
    hits = 側の名の当たる所(根, 束(データ / "側の名.txt"))
    assert 線の赤(hits, 外しの一覧()["側の名"]) == []


def test_直しはどの事務所にも当たる型の版の上げ():
    hits = 直しの当たらない所(根, _型の版())
    assert 線の赤(hits, 外しの一覧()["直しの当たる"]) == []


def test_外しの一覧の形():
    d = json.loads((データ / "外し.json").read_text(encoding="utf-8"))
    assert set(k for k, v in d.items() if isinstance(v, list)) == {"製品の名", "側の名", "直しの当たる"}
    for v in 外しの一覧().values():
        for p, e in v.items():
            assert (根 / p).is_file(), p


# 自己検査の試験: 壊すと赤・戻すと緑（作り物の語だけを使う）
def test_製品の名を見つけられる(tmp_path):
    (tmp_path / "芯").mkdir()
    (tmp_path / "芯" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "b.md").write_text("地の文\n<!-- 例 -->\n作り物ソフトの例\n<!-- /例 -->\n", encoding="utf-8")
    words = ["作り物ソフト"]
    assert 線の赤(製品の名の当たる所(tmp_path, words), {}) == []  # 緑（例の節の中は見ない）
    (tmp_path / "芯" / "a.py").write_text("形 = '作り物ソフト'\n", encoding="utf-8")  # 壊す: コードに
    (tmp_path / "docs" / "c.md").write_text("作り物ソフトの形\n", encoding="utf-8")  # 壊す: 例の節の外に
    (tmp_path / "入口" / "作り物ソフト").mkdir(parents=True)
    (tmp_path / "入口" / "作り物ソフト" / "README.md").write_text("x", encoding="utf-8")  # 壊す: dir の名に
    赤 = 線の赤(製品の名の当たる所(tmp_path, words), {})
    assert 赤 == ["docs/c.md: 中に製品の名「作り物ソフト」", "入口/作り物ソフト/README.md: 名に製品の名「作り物ソフト」",
                 "芯/a.py: 中に製品の名「作り物ソフト」"]
    外し = {"芯/a.py": {"なぜ": "作り物の移行", "畳む": "便 2 で畳む"}}
    assert len(線の赤(製品の名の当たる所(tmp_path, words), 外し)) == 2  # 外しは path ごと
    (tmp_path / "芯" / "a.py").write_text("x = 1\n", encoding="utf-8")  # 戻す
    (tmp_path / "docs" / "c.md").unlink()
    (tmp_path / "入口" / "作り物ソフト" / "README.md").unlink()
    assert 線の赤(製品の名の当たる所(tmp_path, words), {}) == []  # 緑
    assert 線の赤(製品の名の当たる所(tmp_path, words), 外し) == ["外し 芯/a.py: もう当たらない（外し.json からこの行を消す）"]


def test_側の名を見つけられる(tmp_path):
    (tmp_path / "a.json").write_text('{"側": "作り物の側"}', encoding="utf-8")
    (tmp_path / "b.md").write_text("作り物の側の窓が読む", encoding="utf-8")  # 地の文は見ない
    words = ["作り物の側"]
    assert 線の赤(側の名の当たる所(tmp_path, words), {}) == ["a.json: 中に事務所・側の名「作り物の側」"]  # 赤
    (tmp_path / "a.json").write_text('{"側": "入口"}', encoding="utf-8")  # 戻す
    assert 線の赤(側の名の当たる所(tmp_path, words), {}) == []  # 緑
    assert 線の赤({}, {"a.json": {"なぜ": "", "畳む": "便 2"}}) == [
        "外し a.json: なぜ と 畳む が要る", "外し a.json: もう当たらない（外し.json からこの行を消す）"]


def test_直しの印を見つけられる(tmp_path):
    dir_ = tmp_path / "道具" / "寄せ" / "直し"
    dir_.mkdir(parents=True)

    def 置く(版, 名=None, **k):
        d = {"版": 版, "前の版": 版 - 1, **k}
        (dir_ / (名 or f"直し_{版:04d}.json")).write_text(json.dumps(d), encoding="utf-8")
        return d

    出た = {2: 指紋(置く(2))}  # 印の無い出た版の直し（指紋で固定）
    置く(1, 当たる=当たるの印)
    置く(6, 当たる=当たるの印)
    p = "道具/寄せ/直し/直し_{:04d}.json".format
    assert 線の赤(直しの当たらない所(tmp_path, 6, 出た), {}) == []  # 緑（2 は指紋が合う・1 と 6 は印）
    assert 線の赤(直しの当たらない所(tmp_path, 6, {}), {}) == [
        f"{p(2)}: `\"当たる\": \"{当たるの印}\"` の印が無い（1 社のための直しは入れない）"]  # 指紋の無い 2 は印が要る
    置く(2, なぜ="作り物の 1 社の読み替え")  # 壊す: 出た版の直しの中身を変えた
    assert len(線の赤(直しの当たらない所(tmp_path, 6, 出た), {})) == 1
    置く(2)  # 戻す
    置く(2, 名="直し_0009.json")  # 壊す: 版 ≤ 5 を名乗る新しい file（指紋が合っても名の番号と版が違う）
    assert 線の赤(直しの当たらない所(tmp_path, 6, 出た), {}) == [f"{p(9)}: file の名の番号と版（2）が違う"]
    (dir_ / "直し_0009.json").unlink()
    置く(7)  # 壊す: 印の無い新しい直し
    置く(8, 当たる="作り物の会社だけ")  # 壊す: 1 社のための直し
    赤 = 線の赤(直しの当たらない所(tmp_path, 8, 出た), {})
    assert len(赤) == 2 and all("印が無い" in r for r in 赤)
    assert len(線の赤(直しの当たらない所(tmp_path, 6, 出た), {})) == 4  # 壊す: 型の版を上げていない（7・8 が型の版 6 より上）
    外し = {p(7): {"なぜ": "作り物の移行", "畳む": "便 3 で畳む"}}
    assert len(線の赤(直しの当たらない所(tmp_path, 8, 出た), 外し)) == 1  # 外しは path ごと
    置く(7, 当たる=当たるの印)  # 戻す
    置く(8, 当たる=当たるの印)
    assert 線の赤(直しの当たらない所(tmp_path, 8, 出た), {}) == []  # 緑
    assert 線の赤(直しの当たらない所(tmp_path, 8, 出た), 外し) == [f"外し {p(7)}: もう当たらない（外し.json からこの行を消す）"]
