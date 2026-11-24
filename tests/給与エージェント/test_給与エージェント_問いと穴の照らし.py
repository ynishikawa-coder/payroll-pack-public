"""問いの照らしの入口（パックの 確認ページ/前の答え.py だけ・plugin に表を受ける入口を置かない）と穴の照らし（bin/穴の照らし.py）の試験。作り物だけ。

防ぐ故障: 答え済みの問いを事務所の担当者へ出す。窓が組んだ表で関所を通す入口が plugin に在る。穴を文で書いただけで課題の行にしない。
  開いた課題のある月を出す。閉じた状態が渡されないのに全部を開いた／閉じたと決める。
"""
import json
import os
import re
import shutil
import subprocess
import sys

from 手伝い import BIN, 根, 課題の_id

import 穴の照らし as H  # noqa: E402

見出し = ["問いの番号", "会社", "対象", "質問", "回答", "反映先", "答えで変わる項目と人", "理由"]
芯 = 根 / "確認ページ" / "前の答え.py"


def test_答え済みの問いは本物のパックの口で止める(tmp_path):
    rows = tmp_path / "qa.json"
    rows.write_text(json.dumps({"values": [見出し, ["Q209901-1", "作り物の会社", "会社", "通勤の手当の上限はいくらですか", "月 1 万", "", "", ""]]},
                               ensure_ascii=False), encoding="utf-8")
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
    """本物のパックの写し（plugin の bin も中に在る）の芯だけを偽の芯に替える。道具がどの道（--パック・環境・file の上）で
    パックを探しても、行き着く芯はこの偽の芯になる。"""
    写し = tmp_path / "パック"
    shutil.copytree(根, 写し, ignore=shutil.ignore_patterns(".git", "__pycache__", "tests", "node_modules"))
    (写し / "確認ページ" / "前の答え.py").write_text(偽の芯, encoding="utf-8")
    return 写し


def 芯へ表を流す道具(パック, tmp_path):
    """パックの plugin の bin の道具を 1 つずつ、質問の表と答え済みの問いを渡せる形の全部（--rows・位置の引数・環境・標準入力、
    使い方に出る下の命令ごと）で回し、表を芯へ流した（偽の芯が呼ばれた）道具の名を返す。"""
    bin_ = パック / "plugins" / "payroll-agent" / "bin"
    rows, qs = tmp_path / "qa.json", tmp_path / "qs.txt"
    rows.write_text(json.dumps({"values": [見出し, ["Q209901-1", "作り物の会社", "会社", "通勤の手当の上限はいくらですか", "月 1 万",
                                                  "", "", ""]]}, ensure_ascii=False), encoding="utf-8")
    qs.write_text("通勤の手当の上限はいくらですか\n", encoding="utf-8")
    印 = パック / "確認ページ" / "呼ばれた"
    env = {**os.environ, "PAYROLL_PACK_DIR": str(パック), "PAYROLL_QA_ROWS": str(rows), "PAYROLL_QA_COMPANY": "作り物の会社"}
    流す = []
    for f in sorted(bin_.glob("*.py")):
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
import パックの場所 as 場所
a = sys.argv[1:]
p = 場所.探す(a[a.index("--パック") + 1] if "--パック" in a else None)
if "--rows" not in a or p is None:
    sys.exit(2)
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
    表を受けるのはパックの芯 1 か所だけ＝殻（〔口: 問いの関所〕）がシートを読んで渡す。字でなく振る舞いで見る: 芯を偽の芯に替えた
    パックで bin の道具を表を渡せる形の全部で回し、芯が呼ばれたら赤。入口の形をわざと bin に置くと、どの形も赤になる。"""
    パック = _偽のパック(tmp_path)
    assert 芯へ表を流す道具(パック, tmp_path) == []
    bin_ = パック / "plugins" / "payroll-agent" / "bin"
    for 名, 中身 in 入口の形.items():
        (bin_ / 名).write_text(中身, encoding="utf-8")
        assert 芯へ表を流す道具(パック, tmp_path) == [名], 名
        (bin_ / 名).unlink()


def test_穴の行は課題の_id_か起票の行があれば起票済み():
    link = "https://example.invalid/p/" + 課題の_id
    assert H.起票していない穴(f"- 休憩の境を表せない <{link}>", {課題の_id}) == []
    text = "- 休憩の境を表せない（引き継ぎ）\n- 課題 " + link + ": 「休憩の境を表せない（引き継ぎ）」"
    assert H.起票していない穴(text, {課題の_id}) == []
    # ハイフン付きの id も同じ課題
    hy = f"{課題の_id[:8]}-{課題の_id[8:12]}-{課題の_id[12:16]}-{課題の_id[16:20]}-{課題の_id[20:]}"
    assert H.起票していない穴(f"- 直されていない <https://example.invalid/{hy}>", {課題の_id}) == []


def test_課題でないリンクしか無い穴と仕組みの名():
    assert H.起票していない穴("- 直されていない所 <https://example.invalid/" + "b" * 32 + ">", {課題の_id})
    assert H.起票していない穴("### 穴の起票（2099-01-01）\n- 給与・穴の照らし", set()) == []
    assert H.起票していない穴("### 穴の起票\n- 端数の決まりを表せない", set())


def test_開いた課題は月の無い題を全月として数え_別の月だけの題と閉じた課題は飛ばす():
    rows = [{"題": "課題: 休憩の境", "状態": "進行中"}, {"題": "課題: 2099.02支給 別の月", "状態": "進行中"},
            {"題": "課題: 2099.01支給 済んだ", "状態": "完了"}, {"題": "課題: 全月 端数", "状態": "未着手"},
            {"題": "ただの行", "状態": "進行中"}]
    got = [r["題"] for r in H.開いた課題(rows, "2099.01支給", ["完了"])]
    assert got == ["課題: 休憩の境", "課題: 全月 端数"]


def test_閉じた状態が渡されない時は照らせない():
    m = {"課題": [], "課題の id": [], "閉じた状態": [], "月の本文": ""}
    assert any("閉じた状態" in r for r in H.課題と穴の赤(m, "2099.01支給"))
    assert H.課題と穴の赤({**m, "閉じた状態": ["完了"]}, "2099.01支給") == []


def test_命令の照らすと起票の案(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({"課題": [], "課題の id": [], "閉じた状態": ["完了"], "月の本文": "- 端数を表せない"}, ensure_ascii=False),
                 encoding="utf-8")
    r = subprocess.run([sys.executable, str(BIN / "穴の照らし.py"), "照らす", str(f), "--支給月", "2099.01支給",
                        "--パック", str(根)], capture_output=True, text=True)
    assert r.returncode == 2 and "起票していない穴" in r.stdout
    r = subprocess.run([sys.executable, str(BIN / "穴の照らし.py"), "起票の案", str(f), "--支給月", "2099.01支給",
                        "--パック", str(根)], capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout)[0]["題"].startswith("課題: 2099.01支給")


def test_字の揺れをそろえて照らす_全角の頭と幅の無い字と年月の書き方():
    # 壊す: 字のそのままの一致だと、全角の「課題：」・頭の空白・幅の無い字を挟んだ穴の語・「2099年1月」の題が数えられず通った（台帳 束 K3）
    rows = [{"題": "　課題：２０９９年１月 端数", "状態": "進行中"}, {"題": "課\u200b題: 2099/02 別の月", "状態": "進行中"},
            {"題": "課題: 2099.01支給 済んだ", "状態": " 完了 "}]
    assert [r["題"] for r in H.開いた課題(rows, "2099.01支給", ["完了"])] == ["　課題：２０９９年１月 端数"]
    assert [r["題"] for r in H.開いた課題(rows, "2099.02支給", ["完了"])] == ["課\u200b題: 2099/02 別の月"]
    assert H.起票していない穴("- 端数の決まりを表\u200bせない", set()) == ["- 端数の決まりを表\u200bせない"]
    assert H.起票していない穴("- 休憩の境が直されて　いない", set())
    assert H.拾う("ｘ 穴 が在る\n仕組み: 穴の\u200b照らし") == ["ｘ 穴 が在る"]


def test_支給月が読めない時は照らせない():
    m = {"課題": [{"題": "課題: x", "状態": "進行中"}], "課題の id": [], "閉じた状態": ["完了"], "月の本文": ""}
    assert any("照らせない" in r for r in H.課題と穴の赤(m, "来月"))
