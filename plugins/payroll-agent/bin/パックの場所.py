"""給与エージェントの照らしが読むパックの 1 か所（出口の名の形・証明を照らす口・前の答えを照らす口）を探して読む。

照らしの決まり（出す物の名の形・証明の形）はパックの出口に 1 か所だけ在る。ここは写さず、パックの dir を見つけてそこから読む。
探す順: 引数 → 環境 PAYROLL_PACK_DIR（確認ページ/前の答え.py と同じ名）→ この file から上へ辿って `出口/名と版.py` が在る dir
→ この plugin を入れた目録の複製（Claude Code が plugin を入れた所 `<plugins>/cache/<目録>/<plugin>/<版>/` の隣の
`<plugins>/marketplaces/<目録>/`）で、その複製の HEAD の commit がこの plugin の版（commit の頭）と同じ時だけ
（plugin とパックは同じ版の印を読む＝違う版の複製は使わない）。
見つからない時は None（呼ぶ側が止める＝知らない決まりで照らさない）。その時の知らせの文は `分からない訳` の 1 か所。Python 3 の標準ライブラリだけ。
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import re
import subprocess
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
    return 入れた目録()


def _目録の複製(here: Path | None = None) -> tuple[Path, str, str | None] | None:
    """この plugin を入れた目録の複製と、plugin の版・複製の HEAD。plugin が目録から入っていない・複製が無ければ None。"""
    up = (here or Path(__file__)).resolve().parents
    if len(up) < 6 or up[4].name != "cache":
        return None
    版, 目録 = up[1].name, up[3].name
    複製 = up[5] / "marketplaces" / 目録
    if not (複製 / 目印).is_file() or not re.fullmatch(r"[0-9a-f]{7,40}", 版):
        return None
    try:
        r = subprocess.run(["git", "-C", str(複製), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return 複製, 版, None
    return 複製, 版, (r.stdout.strip() if r.returncode == 0 else None)


def 入れた目録(here: Path | None = None) -> Path | None:
    """この plugin を入れた目録の複製（同じ commit の時だけ）。plugin が目録から入っていない・複製が無い・版が違えば None。"""
    x = _目録の複製(here)
    return x[0] if x and x[2] and x[2].startswith(x[1]) else None


def 分からない訳(何が: str, 引数: str | None = None, here: Path | None = None) -> str:
    """パックの場所が分からない時の知らせの文の正本（照らしの道具と見張りはここを使う＝文を写さない）。
    何が＝読めない物と、そのため止めた・照らしていない事。なぜ分からないかと、直し方（plugin を入れ直す・PAYROLL_PACK_DIR）を必ず言う。"""
    渡した = 引数 or os.environ.get("PAYROLL_PACK_DIR")
    x = _目録の複製(here)
    if 渡した:
        なぜ = f"渡されたパックの dir {渡した}（--パック か環境 PAYROLL_PACK_DIR）に {目印} が無い"
    elif x and x[2] and not x[2].startswith(x[1]):
        なぜ = (f"plugin を入れた目録の複製の版（{x[2][:12]}）が plugin の版（{x[1]}）と違う"
              "（目録の複製だけが後から更新された）")
    else:
        なぜ = "環境 PAYROLL_PACK_DIR が無く、plugin を入れた同じ版の目録の複製も見つからない"
    return (f"パックの場所が分からない（{なぜ}）＝{何が}。直し方: plugin payroll-agent を入れ直す"
            "（目録の複製と同じ版にする）か、環境 PAYROLL_PACK_DIR（道具なら --パック）に同じ版のパックの dir を渡す")


def 読む(パック: Path, 名: str):
    """パックの部品（例 `出口.名と版`）を読む。"""
    d = str(パック)
    if d not in sys.path:
        sys.path.insert(0, d)
    return importlib.import_module(名)


def 出す物の置き場(パック: Path) -> dict[str, str]:
    """物 → 置く所（2_出す物・出口/名と版.py の 出す物の置き場）。出す物の名の頭 `<物>_` もここから作る。"""
    return dict(読む(パック, "出口.名と版").出す物の置き場)


def 番号の形たち(パック: Path) -> tuple[str, ...]:
    """人へ見せる文に出る番号の形（問いの番号・確認ページの受付番号）の正規表現の字を、パックの正本から読む（写さない）。
    正本: 初期設定/型の口.py の `問いの番号の形`・確認ページ/確認ページ.py の `受付番号の形`。読めなければ例外。"""
    型の口 = 読む(パック, "初期設定.型の口")
    f = パック / "確認ページ" / "確認ページ.py"   # 試験の束の名とぶつからないよう file から読む（確認ページの名の形 と同じ道）
    s = importlib.util.spec_from_file_location("給与エージェント_確認ページ", f)
    確認 = importlib.util.module_from_spec(s)
    s.loader.exec_module(確認)
    return (型の口.問いの番号の形.pattern, 確認.受付番号の形.pattern)


def 名の頭たち(パック: Path) -> tuple[str, ...]:
    """出荷の口だけが書く本の名の頭（取り込み_・賞与の取り込み_・支給控除一覧_…・有給休暇管理表_ ほか）。長い順。"""
    return tuple(sorted({f"{物}_" for 物 in 出す物の置き場(パック)}, key=len, reverse=True))


def 字の口(パック: Path):
    """字のそろえ方の正本（パックの 芯/字.py）。名・頭・語で意味を決める照らしは、両側をこれでそろえてから比べる（写さない）。"""
    return 読む(パック, "芯.字")


def 守るタブたち(パック: Path) -> tuple[str, ...]:
    """管理表の回の状況のタブ（月の状況・賞与の状況…＝管理表の型で「回」を持つタブの全部）。出荷の欄はこのタブたちに在る。
    正本はパックの 管理表/管理表.py の 型（初期設定/型.json）。読めない時は例外。"""
    管理表 = 読む(パック, "管理表.管理表")
    return tuple(t["タブ"] for t in 管理表.型()["タブ"] if t.get("回") is not None)


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
