"""値の表 config/skill-values.json の docs-kit.big-picture.agreed が、合意した全体の絵の在り処を指すか（注入の試験）。

なぜ在るか: 給与の合意した全体の絵の正は Notion の案件のページで、値の表が在り処を指していないと、土台の
big_picture.py pick は repo の docs/全体の絵.json を探し、無いので「照らせない」になる。合意した設計の仕事の終わりの
1 回の照らし（完了の報告に「設計図どおり」か「差とその扱い」を書く）で合意した絵を引けるよう、在り処を値の表に持つ。
照らしは合流の条件ではない。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _agreed(values):
    return ((values.get("docs-kit") or {}).get("big-picture") or {}).get("agreed")


def _problems(values, root):
    v = _agreed(values)
    if not isinstance(v, str) or not v.strip():
        return ["docs-kit.big-picture.agreed が無い（合意した絵の在り処＝案件のページの名か repo の中の .json）"]
    if v.endswith(".json") and not (root / v).exists():
        return ["docs-kit.big-picture.agreed の %s が repo に無い" % v]
    return []


def test_値の表が合意した全体の絵の在り処を指す():
    values = json.loads((ROOT / "config" / "skill-values.json").read_text(encoding="utf-8"))
    assert _problems(values, ROOT) == []


def test_在り処が無い値の表は拒む(tmp_path):
    assert _problems({"docs-kit": {"qa-html": {}}}, tmp_path)
    assert _problems({"docs-kit": {"big-picture": {"agreed": " "}}}, tmp_path)
    assert _problems({"docs-kit": {"big-picture": {"agreed": "docs/全体の絵.json"}}}, tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "全体の絵.json").write_text("{}", encoding="utf-8")
    assert _problems({"docs-kit": {"big-picture": {"agreed": "docs/全体の絵.json"}}}, tmp_path) == []
