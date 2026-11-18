"""前の形の置き場の名が repo に戻らない見張り（型の版 30・直し 30・docs/設計/Drive の型.md §10）。

前の名は直し 30 の「前の置き場を止める」の 前 から読む（写さない）。git の全部の file の字に 1 つでも在れば赤。
許す所: 出した直しの記録（直し_NNNN.json）・CHANGELOG の版の節（過去の記録）・Drive の型.md §10 の対応の表・
前の名で止まるのを確かめる試験・この見張り。
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parent.parent
直し30 = json.loads((根 / "道具" / "寄せ" / "直し" / "直し_0030.json").read_text(encoding="utf-8"))
前の名たち = sorted({op["前"].rstrip("/").rstrip("_") for op in 直し30["操作"] if op["する"] == "前の置き場を止める"})
許すfile = {
    "tests/寄せ/test_寄せ_前の置き場の名で止める.py",
    "tests/寄せ/test_寄せ_道具.py",
    "tests/test_前の置き場の名の見張り.py",
}


def _files():
    out = subprocess.run(["git", "-c", "core.quotepath=off", "ls-files"], cwd=根, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("git が無い")
    return [p for p in out.stdout.splitlines() if p]


def _見る字(p: str, text: str) -> str:
    if p == "CHANGELOG.md":   # 版の節は過去の記録＝未リリースの節だけ見る
        m = re.search(r"^## 未リリース\n(.*?)(?=^## \[)", text, re.M | re.S)
        return m.group(1) if m else text
    if p == "docs/設計/Drive の型.md":   # §10 の前と新しい形の表は対応の正本
        return re.sub(r"^## 10\. 前の形から畳む物\n.*?(?=^### |^## |\Z)", "", text, flags=re.M | re.S)
    return text


def 当たり(files: dict[str, str]) -> list[str]:
    out = []
    for p, text in files.items():
        if p in 許すfile or re.fullmatch(r"道具/寄せ/直し/直し_\d{4}\.json", p):
            continue
        字 = _見る字(p, text)
        for 名 in 前の名たち:
            for n, line in enumerate(字.splitlines(), 1):
                if 名 in line:
                    out.append(f"{p}: 前の置き場の名「{名}」: {line.strip()[:80]}")
    return out


def test_前の名は直し30から読める():
    assert len(前の名たち) == 10 and "03_マスタ" in 前の名たち


def test_前の置き場の名がrepoの字に無い():
    files = {}
    for p in _files():
        try:
            files[p] = (根 / p).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
    assert 当たり(files) == []


def test_見張りは文書に戻した前の名を拒む():
    assert 当たり({"月次/README.md": "マスタは 03_マスタ「社員」"}) != []
    assert 当たり({"CHANGELOG.md": "# C\n\n## 未リリース\n- 90_履歴 へ\n\n## [v0.1.0] - 2026-01-01\n- 03_マスタ\n"}) != []
    assert 当たり({"CHANGELOG.md": "# C\n\n## 未リリース\n- 今の名\n\n## [v0.1.0] - 2026-01-01\n- 03_マスタ\n"}) == []
    assert 当たり({"道具/寄せ/直し/直し_0005.json": "03_マスタ"}) == []
