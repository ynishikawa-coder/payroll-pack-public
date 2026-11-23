"""見張り: 寄せる道具.md の 1.4 の選べる答えと、人が見る物・雛形の置き場の書き方が、道具と Drive の型に合う（原因の台帳 束 J）。

1. 1.4 の表の「… へ写して消す」は、道具（道具/寄せ/当てる.py）が並べる答えの字と同じ（畳んだ 99_ を紙に残さない）。
2. 人が見る物の置き場は Drive の型の「確認事項の置き場の表」に在る置き場で書く（在りもしない「確認の HTML の置き場」を書かない）。
3. 紙は Drive に雛形の写しを置く段を持たない（Drive の型は「Drive に雛形のフォルダを置かない」）。
注入: 紙の 1.4 に「99_ へ写して消す」を戻す・人が見る物の置き場を「確認の HTML の置き場」に戻すと赤。
"""
import re
from pathlib import Path

根 = Path(__file__).resolve().parent.parent.parent
紙 = (根 / "docs" / "設計" / "寄せる道具.md").read_text(encoding="utf-8")
道具 = (根 / "道具" / "寄せ" / "当てる.py").read_text(encoding="utf-8")
型 = (根 / "docs" / "設計" / "Drive の型.md").read_text(encoding="utf-8")


def _節(見出し: str) -> str:
    i = 紙.index(見出し)
    j = 紙.find("\n### ", i + 1)
    return 紙[i:j if j > 0 else None]


def test_選べる答えの写して消すは道具の字と同じ():
    頭 = re.search(r'^写しの頭 = "([^"/]+)/', 道具, re.M).group(1)   # 道具の写しの置き場（9_履歴）が正本
    紙の答え = set(re.findall(r"([0-9]+_\S*) へ写して消す", _節("### 1.4")))
    assert 紙の答え == {頭}, (紙の答え, 頭)
    assert f'"{頭} へ写して消す"' in 道具


def test_置き場は_Drive_の型の表に在る物で書く():
    assert "確認の HTML の置き場" not in 紙
    assert "Drive に雛形のフォルダを置かない" in 型
    assert "雛形の写しを上書き" not in 紙
    for 置き場 in ("`10_会社/<会社>/8_確認事項/`", "`00_事務所/`"):
        assert 置き場 in 型
