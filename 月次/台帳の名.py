"""年の台帳のタブの名と、日のタブの写しの列の正本（月次の中の 1 か所・置き場を開かない）。

タブの名の正本は 型.json（初期設定/型の口.py が読む）。月次は物の名（鍵）で呼び、型の名へここで結ぶ:
- 型に同じ名のタブが在ればそれ（例 `締めの記録`）。
- 番号つきの名（例 `3_確定した勤怠`）なら番号を外した名で結ぶ。
- 締めの記録・人ごとの月の数字は、型に別のタブが無ければ `計算の結果（人ごと）`（番号つきでも）へ結ぶ＝締めの記録の置き場は
  6_計算の結果（人ごと）。
"""
import importlib.util
import re
import sys
from pathlib import Path

_根 = Path(__file__).resolve().parent.parent
_番号 = re.compile(r"\d+_")
_人ごとの結果 = "計算の結果（人ごと）"
_人ごとの結果へ = ("締めの記録", "人ごとの月の数字")

# 日のタブの写しの列（人が見るための写し・芯は読まない）と、1 次と 2 次で比べない列（写し＋殻が書く原本の Drive の URL）。
写しの列 = ("氏名", "曜日", "出勤の時刻", "退勤の時刻", "休憩の合計", "労働の合計")
比べない列 = (*写しの列, "原本のリンク")


def 型の口():
    名 = "月次_型の口"
    if 名 not in sys.modules:
        spec = importlib.util.spec_from_file_location(名, _根 / "初期設定" / "型の口.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules[名] = m
        spec.loader.exec_module(m)
    return sys.modules[名]


def 番号を外す(名: str) -> str:
    return _番号.sub("", str(名), count=1) if _番号.match(str(名)) else str(名)


def タブの名(シート: str, 鍵: str, 名たち=None) -> str:
    """物の名（鍵）→ 型のそのシートのタブの名。結べなければ鍵のまま返す（型の口が無いタブとして止める）。"""
    if 名たち is None:
        名たち = _名たち(シート)
    名たち = list(名たち)
    if 鍵 in 名たち:
        return 鍵
    for n in 名たち:
        if 番号を外す(n) == 鍵:
            return n
    if 鍵 in _人ごとの結果へ:
        for n in 名たち:
            if 番号を外す(n) == _人ごとの結果:
                return n
    return 鍵


def _名たち(シート: str) -> list[str]:
    for sh in 型の口().型()["シート"]:
        if sh.get("シート") == シート:
            return [t["タブ"] for t in sh["タブ"]]
    return []
