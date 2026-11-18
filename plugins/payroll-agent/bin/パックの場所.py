"""給与エージェントの照らしが読むパックの 1 か所（出口の名の形・証明を照らす口・前の答えを照らす口）を探して読む。

照らしの決まり（出す物の名の形・証明の形）はパックの出口に 1 か所だけ在る。ここは写さず、パックの dir を見つけてそこから読む。
探す順: 引数 → 環境 PAYROLL_PACK_DIR（確認ページ/前の答え.py と同じ名）→ この file から上へ辿って `出口/名と版.py` が在る dir。
見つからない時は None（呼ぶ側が止める＝知らない決まりで照らさない）。Python 3 の標準ライブラリだけ。
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

目印 = Path("出口") / "名と版.py"


def 探す(引数: str | None = None) -> Path | None:
    for c in (引数, os.environ.get("PAYROLL_PACK_DIR")):
        if c:
            p = Path(c).expanduser().resolve()
            return p if (p / 目印).is_file() else None   # 渡された所に無い＝別の所を勝手に探さない
    for p in Path(__file__).resolve().parents:
        if (p / 目印).is_file():
            return p
    return None


def 読む(パック: Path, 名: str):
    """パックの部品（例 `出口.名と版`）を読む。"""
    d = str(パック)
    if d not in sys.path:
        sys.path.insert(0, d)
    return importlib.import_module(名)


def 出す物の置き場(パック: Path) -> dict[str, str]:
    """物 → 置く所（2_出す物・出口/名と版.py の 出す物の置き場）。出す物の名の頭 `<物>_` もここから作る。"""
    return dict(読む(パック, "出口.名と版").出す物の置き場)


def 名の頭たち(パック: Path) -> tuple[str, ...]:
    """出荷の口だけが書く本の名の頭（取り込み_・賞与の取り込み_・支給控除一覧_…・有給休暇管理表_ ほか）。長い順。"""
    return tuple(sorted({f"{物}_" for 物 in 出す物の置き場(パック)}, key=len, reverse=True))


def 確認ページの名の形(パック: Path):
    """確認ページの名の形（`確認事項_<組>_<支給月の名>_v<版>.html`）と、問いの種類ごとの置き場のフォルダの名
    （`{"<会社>": "8_確認事項", "事務所": "00_事務所"}`）を、パックの 1 か所（`確認ページ/確認ページ.py` の 名の形・置き場の名たち。
    置き場の正本は docs/設計/Drive の型.md §3「確認事項の置き場の表」で、確認ページ.py がそれを読む）から読む。
    置き場の名たち の無い前の版のパックは 置き場の名 を両方に使う（前の版は事務所の確認ページも同じ名のフォルダへ置いた）。
    無い・読めない時は None（見張りは確認ページを作る書く道具を止める＝名の形も置き場も写さない）。
    返す物 (正規表現の字, {"<会社>": フォルダの名, "事務所": フォルダの名})。"""
    f = パック / "確認ページ" / "確認ページ.py"
    if not f.is_file():
        return None
    s = importlib.util.spec_from_file_location("給与エージェント_確認ページ", f)
    m = importlib.util.module_from_spec(s)
    try:
        s.loader.exec_module(m)
    except Exception:  # noqa: BLE001  読めない版＝名の形を知らない
        return None
    形, 置き場, 置き場たち = getattr(m, "名の形", None), getattr(m, "置き場の名", None), getattr(m, "置き場の名たち", None)
    if not 形 or not 置き場:
        return None
    if 置き場たち is None:
        置き場たち = {"<会社>": str(置き場), "事務所": str(置き場)}
    if not isinstance(置き場たち, dict) or set(置き場たち) != {"<会社>", "事務所"} or not all(isinstance(v, str) and v for v in 置き場たち.values()):
        return None   # 形の分からない置き場の名たち＝見分けられない
    return (形.pattern if hasattr(形, "pattern") else str(形)), dict(置き場たち)
