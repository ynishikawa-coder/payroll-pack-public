"""検証した先端の照らし（scripts/検証した先端の照らし.py）と、それを呼ぶ workflow（.github/workflows/verify-base.yml）・PR の型の欄。

防ぐ故障（c64af441263a）: PR 本文の検証（他の PR とのぶつかり）を作った時の結果のまま置き、base が進んでも照らし直さない
（本文が事実と違う「ぶつからない」を書いたまま残る）。本文の `検証した base の先端:` と今の base の先端が違えば知らせる（止めない）。
欄の字だけを今の先端に書き換え、PR の先端が base を含まない時も success にしない（success は記録＝compare で決める）。
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

根 = Path(__file__).resolve().parent.parent
道具 = 根 / "scripts" / "検証した先端の照らし.py"
_spec = importlib.util.spec_from_file_location("検証した先端の照らし", 道具)
照 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(照)

古い = "1111111111111111111111111111111111111111"
今 = "2222222222222222222222222222222222222222"


def _本文(c: str) -> str:
    return f"job: 作り物\n{照.欄の名}: {c}\n\n## 検証\n- #999 とぶつからない\n"


def test_今の先端で検証し_PRの先端がそれを含む本文は通る():
    for c in (今, 今[:7], 今[:12], 今.upper()):
        r = 照.照らす(_本文(c), 今, "main", 含む=True)
        assert r["conclusion"] == "success", c


def test_注入_baseを取り込まずに今の先端の字だけを書いた本文は知らせる():
    """欄は今の main の先端と同じ字でも、PR の先端がそれを含まなければ（取り込んでいない）success にしない。"""
    r = 照.照らす(_本文(今), 今, "main", 含む=False)
    assert r["conclusion"] == "neutral"
    assert "含まない" in r["title"] and "取り込" in r["summary"]


def test_注入_PRの先端が含むかを読めない時は申告だけでsuccessにしない(tmp_path):
    assert 照.照らす(_本文(今), 今, "main")["conclusion"] == "neutral"          # 含むを渡さない＝既定は知らせる
    assert 照.照らす(_本文(今), 今, "main", 含む=None)["conclusion"] == "neutral"
    f = tmp_path / "本文.txt"
    f.write_text(_本文(今), encoding="utf-8")
    for 足す in ([], ["--compare", ""], ["--compare", "behind"], ["--compare", "diverged"], ["--compare", "わからない"]):
        out = subprocess.run([sys.executable, str(道具), "--本文", str(f), "--先端", 今, "--base", "main", *足す],
                             capture_output=True, text=True)
        assert out.returncode == 0 and json.loads(out.stdout)["conclusion"] == "neutral", 足す
    for st in ("ahead", "identical"):
        out = subprocess.run([sys.executable, str(道具), "--本文", str(f), "--先端", 今, "--base", "main", "--compare", st],
                             capture_output=True, text=True)
        assert json.loads(out.stdout)["conclusion"] == "success", st


def test_注入_compareのstatusから含むかの対応は照らしの正本1か所で_全部の値を照らす():
    """含むかを決めるのは照らしの道具の `含むか` だけ。behind・diverged・空・知らない値を含む側へ倒すと落ちる。"""
    期待 = {"ahead": True, "identical": True, "AHEAD": True, " identical\n": True,
            "behind": False, "diverged": False,
            "": None, None: None, "unknown": None, "yes": None, "true": None}
    for st, want in 期待.items():
        assert 照.含むか(st) is want, st
    # workflow は compare の status を決めずに生のまま渡す（shell で ahead などを yes/no へ写さない）
    wf = (根 / ".github" / "workflows" / "verify-base.yml").read_text(encoding="utf-8")
    for 字 in ("ahead", "identical", "behind", "diverged", "contains=yes", "--含む"):
        assert 字 not in wf, 字
    assert '--compare "$status"' in wf


def test_注入_baseが進んだ後の本文は知らせる_止めない():
    """main が進んだ後に、前の先端で検証した本文（「ぶつからない」）を置いたままにすると neutral で知らせる。"""
    r = 照.照らす(_本文(古い), 今, "main", 含む=True)   # 取り込んでいても欄が古ければ本文は古い
    assert r["conclusion"] == "neutral"
    assert "進んだ" in r["title"] and 古い[:12] in r["summary"] and 今[:12] in r["summary"]
    assert "検証" in r["summary"] and "書き直す" in r["summary"]
    assert r["conclusion"] != "failure"   # 止めない（止める形はオーナーの同意が要る新しい止める物）


def test_注入_欄が無い_崩れた_2つ在る_型のままの本文も黙って通さない():
    型 = (根 / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    悪い = [
        "親窓: 作り物\n## 検証\n- ぶつからない\n",                     # 欄が無い
        _本文("main の先端"),                                         # commit の形でない
        _本文("12345"),                                               # 短すぎる
        _本文("ghijklmn"),                                            # 16 進でない
        _本文(古い) + f"{照.欄の名}: {今}\n",                           # 2 つ在る（どちらを読むか決まらない）
        型,                                                           # PR の型のまま（欄の中身が型の注）
    ]
    for b in 悪い:
        r = 照.照らす(b, 今, "main", 含む=True)
        assert r["conclusion"] == "neutral", b[:60]
    # 今の base の先端を読めない時も success にしない
    assert 照.照らす(_本文(今), "", "main", 含む=True)["conclusion"] == "neutral"
    assert 照.照らす(_本文(今), "読めない", "main", 含む=True)["conclusion"] == "neutral"


def test_PRの型に照らしと同じ名の欄が1つ在る():
    型 = (根 / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert len(照.欄の形.findall(型)) == 1   # 欄の名の正本は照らしの道具（型はその名で書く）


def test_道具はfileと引数で受けて1行のJSONを出し_いつもexit0(tmp_path):
    f = tmp_path / "本文.txt"
    f.write_text(_本文(古い), encoding="utf-8")
    out = subprocess.run([sys.executable, str(道具), "--本文", str(f), "--先端", 今, "--base", "main"],
                         capture_output=True, text=True)
    assert out.returncode == 0
    assert json.loads(out.stdout)["conclusion"] == "neutral"


def test_workflowは照らしを呼び_止めず_本文をshellの字へ差し込まない():
    wf = (根 / ".github" / "workflows" / "verify-base.yml").read_text(encoding="utf-8")
    assert "scripts/検証した先端の照らし.py" in wf
    assert "/compare/$tip...$head" in wf and "--compare" in wf   # 含むかは本文の申告でなく PR の先端の記録で決める
    # 照らしは base（既定の枝）の物で動かす＝PR が照らしの道具・workflow を書き換えて自分を success にできない
    assert "pull_request_target:" in wf and "\n  pull_request:" not in wf
    assert "ref: ${{ github.event.repository.default_branch }}" in wf
    assert "github.event.pull_request.head" not in wf   # PR の中身を checkout しない
    assert "set -e" not in wf.replace("set -euo pipefail", "")  # 1 つの PR の失敗で残りの PR を照らし落とさない
    assert "set -euo" not in wf
    assert "checks: write" in wf and "check-runs" in wf
    assert "pull_request.body" not in wf          # 本文は file で渡す（字の差し込みで命令にならない）
    assert "conclusion=failure" not in wf and "exit 1" not in wf   # 止めない
    for 契機 in ("pull_request_target:", "edited", "synchronize", "push:"):
        assert 契機 in wf, 契機                    # 本文を直した時・枝が進んだ時に照らし直す
