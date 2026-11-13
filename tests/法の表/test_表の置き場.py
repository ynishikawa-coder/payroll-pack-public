"""法の表は `法の表/` の 1 つの置き場にだけ置き、全部が 引く口 の基準で引ける形（docs/設計/法の表.md §1）。

法の表の形（`表の名`・`基準`・`行` を持つ json）が `法の表/` の外に在れば赤（前の 有給/付与の表.json のように、
効く範囲を見ずに 1 行目で読む表が外に残らないための見張り。試験の作り物は除く）。
"""
import json
import sys
from pathlib import Path

根 = Path(__file__).resolve().parents[2]
if str(根) not in sys.path:
    sys.path.insert(0, str(根))
from 芯.計算 import 引く口  # noqa: E402


def _表の形か(p: Path) -> bool:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError):
        return False
    return isinstance(d, dict) and {"表の名", "基準", "行"} <= d.keys()


def test_法の表の形の_json_は法の表の外に無い():
    外 = [str(p.relative_to(根)) for p in 根.rglob("*.json")
         if p.parts[len(根.parts)] not in ("法の表", "tests", ".git") and _表の形か(p)]
    assert 外 == []


def test_法の表の全部が引く口の基準で引ける():
    for p in sorted((根 / "法の表").glob("*.json")):
        t = 引く口.表(p.stem)
        assert t is not None and t["表の名"] == p.stem, p.name
        assert t["基準"] in 引く口.基準たち and t["欠けた時"] in ("止める", "仮で計算し問う"), p.name
