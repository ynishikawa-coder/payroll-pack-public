"""試験の手伝い: 土台の qa-html の check.mjs（確認ページ.py の qa_htmlの道具＝CI は QA_HTML_CHECK・窓は入った docs-kit）を確認ページに当てる 1 か所（tests/確認ページ・tests/初期設定 が読む）。

値の表（config/skill-values.json）に前の答えの命令（docs-kit.qa-html.prior_check_cmd）が在ると、check.mjs は照らした結果の無いページを
赤にする（「前の答えを照らした結果が無い」）。--run-prior でその命令（確認ページ/前の答え.py）を走らせてから照らす。
質問と回答は見出しだけの作り物の表（答え済み 0＝新しい会社）。
"""
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

根 = Path(__file__).resolve().parents[2]
_s = importlib.util.spec_from_file_location("確認ページ_道具の在り処", 根 / "確認ページ" / "確認ページ.py")
_口 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(_口)


def 道具() -> str:
    """土台の check.mjs の path（無ければ ""）。"""
    try:
        return str(_口.qa_htmlの道具())
    except FileNotFoundError:
        return ""


在る = bool(道具() and shutil.which("node"))
無い訳 = "土台の qa-html の check.mjs（CI は QA_HTML_CHECK・窓は入った plugin docs-kit）か node が無い"


def 答えを照らす(答え: dict) -> subprocess.CompletedProcess:
    """答え（qa-html/2）を土台の答えの形の正本（check.mjs --answer）で照らす。"""
    return subprocess.run(["node", 道具(), "--answer", "-", "--json"], input=json.dumps(答え, ensure_ascii=False),
                          capture_output=True, text=True)
質問の見出し = ["問いの番号", "会社", "対象", "質問", "回答", "反映先", "答えで変わる項目と人", "理由"]


def 当てる(f: Path, *足す: str, tmp: Path) -> subprocess.CompletedProcess:
    t = tmp / "質問と回答.json"
    t.write_text(json.dumps({"values": [質問の見出し]}, ensure_ascii=False), encoding="utf-8")
    env = {**os.environ, "PAYROLL_QA_ROWS": str(t), "PAYROLL_PACK_DIR": str(tmp / "無いパックの場所")}   # 道具は値の表の repo の根から引く（環境に頼らない）
    return subprocess.run(["node", 道具(), str(f), *足す, "--run-prior",
                           "--values", str(根 / "config" / "skill-values.json")], capture_output=True, text=True, env=env, cwd=tmp)
