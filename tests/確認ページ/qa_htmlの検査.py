"""試験の手伝い: qa-html の check.mjs（環境の QA_HTML_CHECK）を確認ページに当てる 1 か所（tests/確認ページ・tests/初期設定 が読む）。

値の表（config/skill-values.json）に前の答えの命令（docs-kit.qa-html.prior_check_cmd）が在ると、check.mjs は照らした結果の無いページを
赤にする（「前の答えを照らした結果が無い」）。--run-prior でその命令（確認ページ/前の答え.py）を走らせてから照らす。
質問と回答は見出しだけの作り物の表（答え済み 0＝新しい会社）。
"""
import json
import os
import subprocess
from pathlib import Path

根 = Path(__file__).resolve().parents[2]
質問の見出し = ["問いの番号", "会社", "対象", "質問", "回答", "反映先", "答えで変わる項目と人", "理由"]


def 当てる(f: Path, *足す: str, tmp: Path) -> subprocess.CompletedProcess:
    t = tmp / "質問と回答.json"
    t.write_text(json.dumps({"values": [質問の見出し]}, ensure_ascii=False), encoding="utf-8")
    env = {**os.environ, "PAYROLL_QA_ROWS": str(t), "PAYROLL_PACK_DIR": str(根)}
    return subprocess.run(["node", os.environ["QA_HTML_CHECK"], str(f), *足す, "--run-prior",
                           "--values", str(根 / "config" / "skill-values.json")], capture_output=True, text=True, env=env, cwd=tmp)
