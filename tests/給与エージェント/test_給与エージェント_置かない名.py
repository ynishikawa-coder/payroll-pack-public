"""plugin payroll-agent の bin・hooks に、殻の名（pixel-office・その道具の path）・Drive などの ID・製品の名・側の名を置かない検査。

防ぐ故障: 給与エージェントの照らしが片側の殻の置き場や特定の製品に結びつき、もう片側の事務所でそのまま正しくない
  （docs/設計/入れてよい物.md の線）。各検査は、わざと入れた物を拒む事も見る（検査が何も見ていない形にならない）。
"""
import re

from 手伝い import PLUGIN, 根

見る所 = ("bin", "hooks")
殻の名 = ("pixel-office", "agents/kyuyo", "kyuyo", "fleet.yaml", "drive_upload")
_長い字 = re.compile(r"[A-Za-z0-9_-]{25,}")
_十六進 = re.compile(r"\b[0-9a-f]{32}\b")


def _束(name: str) -> list[str]:
    out = []
    for line in (根 / "tests" / "data" / name).read_text(encoding="utf-8").splitlines():
        w = line.split("#", 1)[0].strip()
        if w:
            out.append(w)
    return out


def ID_らしい(字: str) -> list[str]:
    """Drive・シート・Notion の ID の形（大小の英字と数字の混ざった 25 字以上・32 字の十六進）。"""
    got = [t for t in _長い字.findall(字) if re.search(r"\d", t) and re.search(r"[a-z]", t) and re.search(r"[A-Z]", t)]
    return got + _十六進.findall(字)


def 外れ(根の_dir) -> list[str]:
    語 = list(殻の名) + _束("製品の名.txt") + _束("側の名.txt")
    out = []
    for d in 見る所:
        for f in sorted((根の_dir / d).rglob("*")):
            if not f.is_file() or "__pycache__" in f.parts:
                continue
            rel = f.relative_to(根の_dir).as_posix()
            t = f.read_text(encoding="utf-8")
            out += [f"{rel}: 語「{w}」" for w in 語 if w in t or w in f.name]
            out += [f"{rel}: ID らしい字「{x}」" for x in ID_らしい(t)]
    return out


def test_binとhooksに殻の名とIDと製品の名が無い():
    assert (PLUGIN / "bin").is_dir() and (PLUGIN / "hooks").is_dir()
    assert 外れ(PLUGIN) == []


def test_入れると赤になる(tmp_path):
    (tmp_path / "bin").mkdir()
    (tmp_path / "hooks").mkdir()
    (tmp_path / "bin" / "a.py").write_text("x = 1\n", encoding="utf-8")
    assert 外れ(tmp_path) == []
    製品 = _束("製品の名.txt")[0]
    側 = _束("側の名.txt")[0]
    (tmp_path / "bin" / "a.py").write_text(
        f"P = 'agents/kyuyo/bin/ship_gate.py'\nR = 'pixel-office'\nF = '1AbCdEfGhIjKlMnOpQrStUvWxYz012345'\nT = '{製品}'\nS = '{側}'\n",
        encoding="utf-8")
    (tmp_path / "hooks" / "h.json").write_text('{"id": "' + "0123456789abcdef" * 2 + '"}', encoding="utf-8")
    got = 外れ(tmp_path)
    for want in ("語「pixel-office」", "語「agents/kyuyo」", "ID らしい字「1AbC", f"語「{製品}」", f"語「{側}」", "h.json: ID らしい字"):
        assert any(want in g for g in got), want
