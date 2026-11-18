"""給与エージェントの部分（plugins/payroll-agent/）の器と線の試験。

1. 器の形: 根の .claude-plugin/marketplace.json と plugin の plugin.json の名・置き場・版を書かない事。skill の頭の形。
2. 線: plugin の中のどの file にも、製品の名・側の名・環境の名（tests/data/ の束）・置き場の在り処（Drive・Notion の ID の形）が無い。
3. 口: 手順と決まりが呼ぶ〔口: 名〕は口の一覧の名だけ・一覧の口は全部どこかで呼ばれる。
4. 指す先: plugin の md が指す path（`…/….md|py|json`）が在る（死んだ参照を残さない）。
5. 公開版へ載る: scripts/public_mirror.py の持っていかない物に plugin と marketplace が入っていない。
6. 差し込む口: 決まり.md を SessionStart の形で差し込み、上限の内。
壊すと赤・戻すと緑の自己検査は作り物の語だけを使う。
"""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parent.parent
データ = 根 / "tests" / "data"
PLUGIN名 = "payroll-agent"
PLUGIN = 根 / "plugins" / PLUGIN名
MARKET = 根 / ".claude-plugin" / "marketplace.json"
口の書き方 = re.compile(r"〔口: ([^〕]+)〕")
指す先 = re.compile(r"`([^`\s][^`]*?\.(?:md|py|json))`")
# 置き場の在り処の形（Drive の file・フォルダの ID・Notion の頁の ID）。名の束でなく形で見る。
在り処の形 = (
    ("Drive の ID の形", re.compile(r"(?<![A-Za-z0-9_-])1[A-Za-z0-9_-]{24,43}(?![A-Za-z0-9_-])")),
    ("Notion の ID の形", re.compile(r"(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])")),
    ("Notion の ID の形", re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")),
)


def 束(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        w = line.split("#", 1)[0].strip()
        if w and w not in out:
            out.append(w)
    return out


def _files(base: Path):
    for f in sorted(base.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            yield f


def _読む(f: Path) -> str:
    try:
        return f.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


# ---- 1. 器の形 ----
def 器の誤り(根_: Path) -> list[str]:
    誤り = []
    m = 根_ / ".claude-plugin" / "marketplace.json"
    if not m.is_file():
        return ["根に .claude-plugin/marketplace.json が無い"]
    d = json.loads(m.read_text(encoding="utf-8"))
    if d.get("name") != "payroll-pack":
        誤り.append(f"marketplace の名が payroll-pack でない: {d.get('name')}")
    if not isinstance(d.get("owner"), dict) or not d["owner"].get("name"):
        誤り.append("marketplace に owner.name が無い")
    plugins = d.get("plugins") or []
    名たち = [p.get("name") for p in plugins]
    if PLUGIN名 not in 名たち:
        誤り.append(f"marketplace に {PLUGIN名} が無い")
    if len(名たち) != len(set(名たち)):
        誤り.append("marketplace の plugin の名が重なる")
    if "version" in d or "version" in d.get("metadata", {}):
        誤り.append("marketplace に版を書いた（版はパックの版の印だけ）")
    for p in plugins:
        名 = p.get("name")
        if "version" in p:
            誤り.append(f"marketplace の {名} に版を書いた（版はパックの版の印だけ）")
        if p.get("source") != f"./plugins/{名}":
            誤り.append(f"{名} の source が ./plugins/{名} でない: {p.get('source')}")
            continue
        pj = 根_ / "plugins" / 名 / ".claude-plugin" / "plugin.json"
        if not pj.is_file():
            誤り.append(f"plugins/{名}/.claude-plugin/plugin.json が無い")
            continue
        q = json.loads(pj.read_text(encoding="utf-8"))
        if q.get("name") != 名:
            誤り.append(f"plugins/{名} の plugin.json の名が違う: {q.get('name')}")
        if "version" in q:
            誤り.append(f"plugins/{名} の plugin.json に版を書いた（版はパックの版の印だけ）")
        if not str(q.get("description", "")).strip():
            誤り.append(f"plugins/{名} の plugin.json に description が無い")
        skills = 根_ / "plugins" / 名 / "skills"
        for s in sorted(skills.iterdir()) if skills.is_dir() else []:
            md = s / "SKILL.md"
            if not md.is_file():
                誤り.append(f"plugins/{名}/skills/{s.name} に SKILL.md が無い")
                continue
            頭 = re.match(r"---\n(.*?)\n---\n", md.read_text(encoding="utf-8"), re.S)
            if not 頭:
                誤り.append(f"plugins/{名}/skills/{s.name}/SKILL.md に頭（--- の間）が無い")
                continue
            鍵 = dict(re.findall(r"^(\w+):\s*(.+)$", 頭.group(1), re.M))
            if 鍵.get("name") != s.name:
                誤り.append(f"plugins/{名}/skills/{s.name}/SKILL.md の name が dir の名と違う: {鍵.get('name')}")
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", s.name):
                誤り.append(f"plugins/{名}/skills/{s.name}: skill の名は英小文字・数字・- だけ")
            if not 鍵.get("description", "").strip():
                誤り.append(f"plugins/{名}/skills/{s.name}/SKILL.md に description が無い")
    # plugins/ の下の dir は全部 marketplace に載る（載らない plugin を置かない）
    for dir_ in sorted((根_ / "plugins").iterdir()) if (根_ / "plugins").is_dir() else []:
        if dir_.is_dir() and dir_.name not in 名たち:
            誤り.append(f"plugins/{dir_.name} が marketplace に無い")
    return 誤り


def test_器の形():
    assert 器の誤り(根) == []


def test_器の誤りを見つけられる(tmp_path):
    import shutil
    shutil.copytree(根 / ".claude-plugin", tmp_path / ".claude-plugin")
    shutil.copytree(PLUGIN, tmp_path / "plugins" / PLUGIN名, ignore=shutil.ignore_patterns("__pycache__"))
    assert 器の誤り(tmp_path) == []  # 緑
    pj = tmp_path / "plugins" / PLUGIN名 / ".claude-plugin" / "plugin.json"
    d = json.loads(pj.read_text(encoding="utf-8"))
    pj.write_text(json.dumps({**d, "version": "0.0.1"}), encoding="utf-8")  # 壊す: 版を 2 か所に
    (tmp_path / "plugins" / "作り物の束").mkdir()  # 壊す: marketplace に載らない plugin
    s = tmp_path / "plugins" / PLUGIN名 / "skills" / "作り物"
    s.mkdir()
    (s / "SKILL.md").write_text("---\nname: other\ndescription: x\n---\n", encoding="utf-8")  # 壊す: 名が違う・英字でない
    赤 = 器の誤り(tmp_path)
    assert any("版を書いた" in r for r in 赤)
    assert any("作り物の束 が marketplace に無い" in r for r in 赤)
    assert any("name が dir の名と違う" in r for r in 赤)
    assert any("英小文字" in r for r in 赤)
    m = tmp_path / ".claude-plugin" / "marketplace.json"
    md = json.loads(m.read_text(encoding="utf-8"))
    md["plugins"][0]["source"] = "./作り物"  # 壊す: 置き場が違う
    m.write_text(json.dumps(md), encoding="utf-8")
    assert any("source が" in r for r in 器の誤り(tmp_path))


# ---- 2. 線 ----
def 線の当たる所(base: Path, 語たち: dict[str, list[str]]) -> list[str]:
    hits = []
    for f in _files(base):
        name = f.relative_to(base).as_posix()
        text = _読む(f)
        for 種類, words in 語たち.items():
            for w in words:
                if w in name:
                    hits.append(f"{name}: 名に{種類}「{w}」")
                elif w in text:
                    hits.append(f"{name}: 中に{種類}「{w}」")
        for 種類, pat in 在り処の形:
            m = pat.search(text)
            if m:
                hits.append(f"{name}: 中に{種類}「{m.group(0)}」")
    return hits


def _語たち() -> dict[str, list[str]]:
    return {"製品の名": 束(データ / "製品の名.txt"), "側の名": 束(データ / "側の名.txt"),
            "環境の名": 束(データ / "環境の名.txt")}


def test_plugin_に製品と側と環境の名と在り処が無い():
    assert 線の当たる所(PLUGIN, _語たち()) == []
    assert 線の当たる所(根 / ".claude-plugin", _語たち()) == []


def test_線の当たりを見つけられる(tmp_path):
    (tmp_path / "a.md").write_text("口の名だけで呼ぶ\n", encoding="utf-8")
    語 = {"側の名": ["作り物の側"], "環境の名": ["作り物の環境/道具"]}
    assert 線の当たる所(tmp_path, 語) == []  # 緑
    (tmp_path / "a.md").write_text("作り物の側の窓は 作り物の環境/道具 を使う\n", encoding="utf-8")  # 壊す: md の地の文に
    (tmp_path / "b.json").write_text('{"置き場": "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"}', encoding="utf-8")  # 壊す: 在り処の形
    (tmp_path / "c.py").write_text("頁 = '0123456789abcdef0123456789abcdef'\n", encoding="utf-8")  # 壊す: 頁の ID の形
    赤 = 線の当たる所(tmp_path, 語)
    assert "a.md: 中に側の名「作り物の側」" in 赤 and "a.md: 中に環境の名「作り物の環境/道具」" in 赤
    assert any(r.startswith("b.json: 中にDrive の ID の形") for r in 赤)
    assert any(r.startswith("c.py: 中にNotion の ID の形") for r in 赤)
    for f in ("a.md", "b.json", "c.py"):
        (tmp_path / f).write_text("口の名だけで呼ぶ\n", encoding="utf-8")  # 戻す
    assert 線の当たる所(tmp_path, 語) == []


# ---- 3. 口 ----
def 一覧の口(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        if line.startswith("|") and not set(line) <= set("|- "):
            m = 口の書き方.search(line.split("|")[1])
            if m:
                out.append(m.group(1))
    return out


def 口の誤り(base: Path) -> list[str]:
    一覧 = base / "口の一覧.md"
    名たち = 一覧の口(一覧.read_text(encoding="utf-8"))
    誤り = [f"口の一覧に同じ口が 2 行: {n}" for n in sorted({n for n in 名たち if 名たち.count(n) > 1})]
    呼ばれた: set[str] = set()
    for f in _files(base):
        if f.suffix != ".md":
            continue
        name = f.relative_to(base).as_posix()
        for line in _読む(f).splitlines():
            if f == 一覧 and line.startswith("|"):
                cells = line.split("|")
                line = "|".join(cells[2:])  # 一覧の 1 列目（口の名の定め）は呼んだに数えない
            for n in 口の書き方.findall(line):
                if n not in 名たち:
                    誤り.append(f"{name}: 口の一覧に無い口「{n}」")
                if f != 一覧:
                    呼ばれた.add(n)
    for n in 名たち:
        if n not in 呼ばれた:
            誤り.append(f"口の一覧の「{n}」を手順と決まりのどこも呼ばない（使わない口を残さない）")
    return 誤り


def test_口は一覧の名だけ():
    assert 口の誤り(PLUGIN) == []


def test_口の誤りを見つけられる(tmp_path):
    (tmp_path / "口の一覧.md").write_text("| 口 | 渡す物 |\n|---|---|\n| 〔口: 作り物を読む〕 | x |\n", encoding="utf-8")
    (tmp_path / "手順.md").write_text("〔口: 作り物を読む〕で読む\n", encoding="utf-8")
    assert 口の誤り(tmp_path) == []  # 緑
    (tmp_path / "手順.md").write_text("〔口: 作り物の道具〕で読む\n", encoding="utf-8")  # 壊す: 一覧に無い口・一覧の口を呼ばない
    assert 口の誤り(tmp_path) == ["手順.md: 口の一覧に無い口「作り物の道具」",
                                 "口の一覧の「作り物を読む」を手順と決まりのどこも呼ばない（使わない口を残さない）"]


# ---- 4. 指す先 ----
def 無い指す先(plugin: Path, 根_: Path) -> list[str]:
    out = []
    for f in _files(plugin):
        if f.suffix != ".md":
            continue
        for p in 指す先.findall(_読む(f)):
            if "<" in p or "*" in p:
                continue  # 形の例（<名> を含む）
            if not ((根_ / p).exists() or (plugin / p).exists()):
                out.append(f"{f.relative_to(plugin).as_posix()}: 指す先が無い `{p}`")
    return out


def test_plugin_の指す先が在る():
    assert 無い指す先(PLUGIN, 根) == []


def test_無い指す先を見つけられる(tmp_path):
    p = tmp_path / "p"
    p.mkdir()
    (tmp_path / "在る.md").write_text("x", encoding="utf-8")
    (p / "a.md").write_text("`在る.md` と `作り物/無い.py`\n", encoding="utf-8")
    assert 無い指す先(p, tmp_path) == ["a.md: 指す先が無い `作り物/無い.py`"]


# ---- 5. 公開版へ載る ----
def test_plugin_と_marketplace_は公開版へ載る():
    spec = importlib.util.spec_from_file_location("public_mirror", 根 / "scripts" / "public_mirror.py")
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)
    tracked = subprocess.run(["git", "ls-files", ".claude-plugin", "plugins"], cwd=根, capture_output=True,
                             text=True).stdout.split()
    for rel in [".claude-plugin/marketplace.json", f"plugins/{PLUGIN名}/.claude-plugin/plugin.json"] + tracked:
        assert not pm.omitted(rel), rel


# ---- 6. 差し込む口 ----
def _差し込む(*args):
    return subprocess.run([sys.executable, str(PLUGIN / "scripts" / "差し込む.py"), *args],
                          capture_output=True, text=True)


def test_決まりを起動時の形で差し込む():
    r = _差し込む("inject")
    assert r.returncode == 0
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    assert out["additionalContext"].startswith("# 給与エージェントの決まり")
    assert "payroll-steps" in out["additionalContext"]


def test_決まりは上限の内():
    r = _差し込む("check")
    assert r.returncode == 0, r.stdout


def test_決まりが読めなくても起動を止めない(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("差し込む", PLUGIN / "scripts" / "差し込む.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.setattr(m, "決まり", tmp_path / "無い.md")
    assert m.inject() == 0
    assert m.check() == 2
    (tmp_path / "大きい.md").write_text("あ" * 2000, encoding="utf-8")  # 6000 バイト
    monkeypatch.setattr(m, "決まり", tmp_path / "大きい.md")
    assert m.check() == 1
