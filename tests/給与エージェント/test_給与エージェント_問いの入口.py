"""問いの照らしの入口（パックの 確認ページ/前の答え.py だけ・plugin に表を受ける入口を置かない）の試験。作り物だけ。

防ぐ故障: 答え済みの問いを事務所の担当者へ出す。窓が組んだ表で関所を通す入口が plugin に在る。
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from 手伝い import 根

sys.path.insert(0, str(根))
from 初期設定 import 質問と回答 as qa  # noqa: E402


def 答え済みの表():
    """作り物の 質問と回答（3 タブ）。Q209901-1 は答えた問い。"""
    return {qa.Driveのタブ("問い"): [qa.見出し("問い"), ["Q209901-1", "作り物の会社", "2099-01", "2099-01-05",
                                                     "通勤の手当の上限はいくらですか", "", "答えた"]],
            qa.Driveのタブ("答え"): [qa.見出し("答え"), ["Q209901-1", "月 1 万", "2099-01-06", ""]],
            qa.Driveのタブ("振り分け"): [qa.見出し("振り分け")]}


芯 = 根 / "確認ページ" / "前の答え.py"


def test_答え済みの問いは本物のパックの口で止める(tmp_path):
    rows = tmp_path / "qa.json"
    rows.write_text(json.dumps(答え済みの表(), ensure_ascii=False), encoding="utf-8")
    qs = tmp_path / "qs.txt"
    qs.write_text("通勤の手当の上限はいくらですか\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(芯), "--rows", str(rows), "--questions", str(qs)], capture_output=True, text=True)
    assert r.returncode == 2 and "答え済み" in r.stderr
    qs.write_text("新しい作り物の手当はありますか\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(芯), "--rows", str(rows), "--questions", str(qs)], capture_output=True, text=True)
    assert r.returncode == 0


# 偽の芯: 呼ばれた（命令でも読み込みでも）ら印を残し、答え済みで止める形で返す（本物の芯と同じ出口の形）
偽の芯 = """import pathlib, sys
with open(pathlib.Path(__file__).with_name("呼ばれた"), "a", encoding="utf-8") as f:
    f.write(" ".join(sys.argv) + "\\n")
if __name__ == "__main__":
    print("答え済み", file=sys.stderr)
    sys.exit(2)
"""


def _偽のパック(tmp_path):
    """本物のパックの写し（plugin も中に在る）の芯だけを偽の芯に替える。道具がどの道（--パック・環境・file の上）で
    パックを探しても、行き着く芯はこの偽の芯になる。"""
    写し = tmp_path / "パック"
    shutil.copytree(根, 写し, ignore=shutil.ignore_patterns(".git", "__pycache__", "tests", "node_modules"))
    (写し / "確認ページ" / "前の答え.py").write_text(偽の芯, encoding="utf-8")
    return 写し


def 芯へ表を流す道具(パック, tmp_path):
    """パックの plugin の中の Python の道具（どの dir でも）を 1 つずつ、質問の表と答え済みの問いを渡せる形の全部（--rows・位置の引数・
    環境・標準入力、使い方に出る下の命令ごと）で回し、表を芯へ流した（偽の芯が呼ばれた）道具の名を返す。"""
    plugin = パック / "plugins" / "payroll-agent"
    rows, qs = tmp_path / "qa.json", tmp_path / "qs.txt"
    rows.write_text(json.dumps(答え済みの表(), ensure_ascii=False), encoding="utf-8")
    qs.write_text("通勤の手当の上限はいくらですか\n", encoding="utf-8")
    印 = パック / "確認ページ" / "呼ばれた"
    env = {**os.environ, "PAYROLL_PACK_DIR": str(パック), "PAYROLL_QA_ROWS": str(rows), "PAYROLL_QA_COMPANY": "作り物の会社"}
    流す = []
    for f in sorted(plugin.rglob("*.py")):
        使い方 = subprocess.run([sys.executable, str(f)], capture_output=True, text=True, env=env, input="", timeout=60)
        下 = sorted(set(re.findall(re.escape(f.name) + r"\s+([^\s<\[-]\S*)", 使い方.stdout + 使い方.stderr)))
        for sub in [None, *下]:
            頭 = [sub] if sub else []
            for 尾 in ([], [str(rows)]):
                subprocess.run([sys.executable, str(f), *頭, *尾, "--rows", str(rows), "--questions", str(qs), "--company",
                                "作り物の会社", "--パック", str(パック)], capture_output=True, text=True, env=env,
                               input=qs.read_text(encoding="utf-8"), timeout=60, cwd=パック)
        if 印.exists():
            流す.append(f.name)
            印.unlink()
    return 流す


# 誤りの類（窓が組んだ質問の表を受けて芯へ渡す入口）の形。畳んだ bin/問いの照らし.py と同じ形・名を変えて argv をそのまま渡す形・
# 芯の path を部品から組む形・芯を命令でなく読み込みで回す形・環境だけで表を受ける形
入口の形 = {
    "問いの照らし.py": """import subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
a = sys.argv[1:]
p = Path(a[a.index("--パック") + 1]) if "--パック" in a else Path(__file__).resolve().parents[3]
if "--rows" not in a:
    sys.exit(2)
if "--パック" in a:
    i = a.index("--パック"); del a[i:i + 2]
sys.exit(subprocess.run([sys.executable, str(p / "確認ページ" / "前の答え.py"), *a]).returncode)
""",
    "聞き直しの見張り.py": """import os, subprocess, sys
from pathlib import Path
p = Path(os.environ["PAYROLL_PACK_DIR"])
sys.exit(subprocess.run([sys.executable, str(p.joinpath("確認" + "ページ", "前の" + "答え" + ".py")), *sys.argv[1:]]).returncode)
""",
    "文の点検.py": """import importlib.util, sys
from pathlib import Path
for d in Path(__file__).resolve().parents:
    c = d / "確認ページ" / ("前の" + "答え.py")
    if c.is_file():
        s = importlib.util.spec_from_file_location("x", c); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        break
""",
    "表の点検.py": """import os, subprocess, sys
from pathlib import Path
表 = os.environ.get("PAYROLL_QA_ROWS")
if 表 and len(sys.argv) > 1 and sys.argv[1] == "見る":
    p = Path(os.environ["PAYROLL_PACK_DIR"])
    sys.exit(subprocess.run([sys.executable, str(next(p.glob("*/前の*.py")))], env=os.environ).returncode)
if len(sys.argv) < 2:
    print("使い方: python3 表の点検.py 見る", file=sys.stderr)
""",
}


def test_注入_plugin_に質問の表を受ける入口を置かない(tmp_path):
    """前は plugin の bin/問いの照らし.py が表の file を --rows で受け、殻を通らずに窓が組んだ表で照らせた（2026-11-22 に畳んだ）。
    表を受けるのはパックの芯 1 か所だけ。字でなく振る舞いで見る: 芯を偽の芯に替えたパックで plugin の中の Python の道具を
    表を渡せる形の全部で回し、芯が呼ばれたら赤。入口の形をわざと plugin の bin に置くと、どの形も赤になる。"""
    パック = _偽のパック(tmp_path)
    assert 芯へ表を流す道具(パック, tmp_path) == []
    bin_ = パック / "plugins" / "payroll-agent" / "bin"
    bin_.mkdir(exist_ok=True)
    for 名, 中身 in 入口の形.items():
        (bin_ / 名).write_text(中身, encoding="utf-8")
        assert 芯へ表を流す道具(パック, tmp_path) == [名], 名
        (bin_ / 名).unlink()
