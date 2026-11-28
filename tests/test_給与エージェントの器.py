"""給与エージェントの部分（plugins/payroll-agent/）の口と起動の試験。

1. 口: 手順と決まりが呼ぶ〔口: 名〕は口の一覧の名だけ・一覧の口は全部どこかで呼ばれる。
2. 起動: hooks.json は SessionStart の差し込みだけを登録し（PreToolUse の見張りを持たない）、差し込む口は決まり.md を起動時の形で返す。
壊すと赤・戻すと緑の自己検査は作り物の語だけを使う。
"""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

根 = Path(__file__).resolve().parent.parent
PLUGIN名 = "payroll-agent"
PLUGIN = 根 / "plugins" / PLUGIN名
口の書き方 = re.compile(r"〔口: ([^〕]+)〕")


def _files(base: Path):
    for f in sorted(base.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            yield f


def _読む(f: Path) -> str:
    try:
        return f.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


# ---- 1. 口 ----
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
                if n not in 名たち and n != "寄せる":   # 寄せの一式は後片付けの PR で畳む（それまで一覧の中の言及を誤りに数えない）
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


# ---- 2. 起動 ----
def _差し込む(*args):
    return subprocess.run([sys.executable, str(PLUGIN / "scripts" / "差し込む.py"), *args],
                          capture_output=True, text=True)


def test_hooksはSessionStartの差し込みだけ():
    """hooks.json が読め、SessionStart で差し込む口を呼び、PreToolUse（道具の呼び出しを止める見張り）を持たない。"""
    d = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert set(d["hooks"]) == {"SessionStart"}, d["hooks"].keys()
    cmds = [h["command"] for 組 in d["hooks"]["SessionStart"] for h in 組["hooks"]]
    assert cmds == ['python3 "${CLAUDE_PLUGIN_ROOT}/scripts/差し込む.py" inject']


def test_決まりを起動時の形で差し込む():
    r = _差し込む("inject")
    assert r.returncode == 0
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    assert out["additionalContext"].startswith("# 給与エージェントの決まり")
    assert "payroll-steps" in out["additionalContext"]


def test_決まりが読めなくても起動を止めない(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("差し込む", PLUGIN / "scripts" / "差し込む.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.setattr(m, "決まり", tmp_path / "無い.md")
    assert m.inject() == 0
