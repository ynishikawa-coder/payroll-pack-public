"""見張り: 寄せる道具.md の 1.4 の選べる答えと、人が見る物・雛形の置き場の書き方が、道具と Drive の型に合う（原因の台帳 束 J）。

1. 1.4 の表の「… へ写して消す」は、道具（道具/寄せ/当てる.py）が並べる答えの字と同じ（畳んだ 99_ を紙に残さない）。
2. 人が見る物の置き場は Drive の型の「確認事項の置き場の表」に在る置き場で書く（在りもしない「確認の HTML の置き場」を書かない）。
3. 紙は Drive に雛形の写しを置く段を持たない（Drive の型は「Drive に雛形のフォルダを置かない」）。
注入: 紙の 1.4 に「99_ へ写して消す」を戻す・人が見る物の置き場を「確認の HTML の置き場」に戻すと赤。
"""
import json
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
    頭 = json.loads((根 / "初期設定" / "型.json").read_text(encoding="utf-8"))["木"]["名"]["履歴"]   # 写しの置き場の名の正本（型.json）
    import sys
    sys.path.insert(0, str(根 / "道具" / "寄せ"))
    import 当てる
    # 道具の写しの置き場は型の 履歴 から引き、消す_ の名の形は 確認ページ.消す名 から引く（字を写さない）
    assert 当てる.写しの頭 == f"{頭}/{当てる.確認ページの形().消す名の頭}"
    assert 当てる.写しの先("2026-01-31", "a/b.md").startswith(f"{頭}/")
    紙の答え = set(re.findall(r"([0-9]+_\S*) へ写して消す", _節("### 1.4")))
    assert 紙の答え == {頭}, (紙の答え, 頭)
    assert f'"{頭} へ写して消す"' in 道具


def test_置き場は_Drive_の型の表に在る物で書く():
    assert "確認の HTML の置き場" not in 紙
    assert "Drive に雛形のフォルダを置かない" in 型
    assert "雛形の写しを上書き" not in 紙
    # 置き場の道は文書に写さず 型.json の 木.確認事項の置き場 を指す（道の正本は 1 か所）
    assert "木.確認事項の置き場" in 型 and "python3 初期設定/型の口.py 木" in 型
    木 = json.loads((根 / "初期設定" / "型.json").read_text(encoding="utf-8"))["木"]
    assert set(木["確認事項の置き場"]) == {"<組>", "事務所"}
