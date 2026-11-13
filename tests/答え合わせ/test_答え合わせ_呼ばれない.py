"""答え合わせは開発の間だけの道具: 芯/・出口/・入口/ のどの file からも import されない・名も出ない（grep の試験）。"""
import re
from pathlib import Path

根 = Path(__file__).resolve().parents[2]
_呼ぶ形 = re.compile(r"答え合わせ")


def 呼んでいる所(根: Path, 置き場=("芯", "出口", "入口")) -> list[str]:
    out = []
    for d in 置き場:
        for p in sorted((根 / d).rglob("*.py")):
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
                if re.match(r"\s*(from|import)\s", line) and _呼ぶ形.search(line):
                    out.append(f"{p.relative_to(根)}:{n}")
    return out


def test_芯と出口と入口から呼ばれない():
    assert 呼んでいる所(根) == []


def test_呼んでいる所を見つけられる(tmp_path):
    (tmp_path / "芯" / "計算").mkdir(parents=True)
    (tmp_path / "芯" / "計算" / "x.py").write_text("from 道具.答え合わせ import 照合の段\n", encoding="utf-8")
    assert 呼んでいる所(tmp_path) == ["芯/計算/x.py:1"]


def test_道具は芯を呼ばない():
    """道具は芯の計算の結果を受けて照らすだけ。芯/ を import して中を書き換えたり回したりしない。"""
    for p in sorted((根 / "道具" / "答え合わせ").rglob("*.py")):
        for line in p.read_text(encoding="utf-8").splitlines():
            assert not re.match(r"\s*(from|import)\s+芯", line), f"{p.relative_to(根)}: {line}"
