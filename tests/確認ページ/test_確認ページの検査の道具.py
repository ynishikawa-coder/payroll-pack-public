"""CI では確認ページの検査（qa-html の check.mjs）の試験を飛ばさない。

check.mjs の試験（test_確認ページ.py の qa_html の 4 件と型・答えの形・tests/初期設定 の設問）は、土台の check.mjs と node が無いと skip になる。
手元では skip でよいが、CI（環境に CI=true）で道具が無いと黙って飛ぶので、ここで赤にする（ci.yml が取って渡す）。
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(os.environ.get("CI") != "true", reason="CI でだけ見る（手元は check.mjs が無ければ skip でよい）")
def test_CIでは確認ページの検査の道具が在る():
    f = os.environ.get("QA_HTML_CHECK", "")
    assert f, "CI に QA_HTML_CHECK が無い（.github/workflows/ci.yml の「確認ページの型と検査を土台の main から取る」）"
    assert Path(f).is_file(), f"QA_HTML_CHECK の file が無い: {f}"
    assert shutil.which("node"), "CI に node が無い"
    r = subprocess.run(["node", f, "--template"], capture_output=True, text=True)
    assert r.returncode == 0 and "<!--qa:css-->" in r.stdout, "土台の check.mjs が型を返さない（--template を知らない古い土台を取った）"
