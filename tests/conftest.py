"""tests 全体 — 試験が黙って飛ぶのを既定で止める（skip は許しの表に在る物だけ）。

なぜ在るか（根治・2026-11-23）: pytest の skip は緑に数えられ、検査の入口（scripts/check_all.sh）も「緑: 全部の検査が
  通った」と出す。試験が消えても誰も気付かなかった（在る部品を「まだ無い」と importorskip で飛ばす・CI の版が上がると
  skipif で飛ぶ・fixture の中の skip）。skip を既定で赤に替え、飛んでよい物は下の 1 つの表 `許す飛ばし` にだけ持つ。
  表の行は「試験の file（tests/ からの path）・飛ばしの訳の頭・なぜ許すか」。表に無い飛ばしは試験の本文・飾り・fixture・
  手伝いの関数・file の頭（importorskip・allow_module_level）のどこから出ても赤（落ちた試験として名が出る）。
  xfail（落ちると分かっている印）はここで扱わない。
"""
from __future__ import annotations

from pathlib import Path

import pytest

_根 = Path(__file__).resolve().parent

# (試験の file〔tests/ からの path〕, 飛ばしの訳の頭, なぜ許すか)。足す時は「CI でも飛ぶか」を訳に書く。
許す飛ばし: tuple[tuple[str, str, str], ...] = (
    ("test_版の印はCIの緑の後.py", "tag.yml の無い公開の写し",
     "公開の写しは版の印を打たない＝見る物が無い（本 repo には tag.yml が在り必ず回る）"),
    ("test_検査の入口.py", "入口の中の入口",
     "check_all.sh の中から check_all.sh を回す試験の、内側の回だけを飛ばす（外側の回で当たる）"),
    ("確認ページ/test_確認ページ.py", "土台の qa-html の check.mjs",
     "手元に check.mjs・node が無い時だけ。CI では 確認ページ/test_確認ページの検査の道具.py が無いことを赤にする"),
    ("確認ページ/test_確認ページの検査の道具.py", "CI でだけ見る",
     "道具が無いことを赤にするのは CI だけ（手元は上の行の skip でよい）"),
    ("test_骨.py", "顧客の語の束が渡されていない",
     "語の束は repo に持たず環境から渡す（CONTRIBUTING.md §3）。渡されない環境では照らす物が無い"),
    ("test_骨.py", "git の履歴・印が手元に無い: ",
     "浅い clone の手元だけ（test_骨.py の _手元に無い が付ける頭）。CI（GITHUB_ACTIONS）では同じ所が pytest.fail で赤"),
    ("test_取り込みの照らし.py", "手元に main が無い",
     "手元だけ。CI（GITHUB_ACTIONS）では同じ所が pytest.fail で赤"),
    ("入口/test_入口_見張り.py", "見張りの期待を書き直した",
     "PAYROLL_IRIGUCHI_MIHARI_KAKINAOSU を渡して期待を書き直した回だけ（照らしていない＝緑に見せない訳を出す）"),
    ("test_前の置き場の名の見張り.py", "git が無い",
     "git の無い所（展開した写し）だけ。CI は git で checkout する"),
)


def 許すか(file: str, 訳: str) -> bool:
    """tests/ からの path と飛ばしの訳が、許しの表のどれかの行に合うか。"""
    return any(file == f and 訳.startswith(頭) for f, 頭, _ in 許す飛ばし)


def _訳(rep) -> str:
    lr = rep.longrepr
    s = lr[2] if isinstance(lr, tuple) and len(lr) == 3 else str(lr or "")
    return s[len("Skipped: "):] if s.startswith("Skipped: ") else s


def _file(path: str | Path) -> str:
    p = Path(path)
    p = p if p.is_absolute() else Path.cwd() / p
    try:
        return p.resolve().relative_to(_根).as_posix()
    except ValueError:
        return p.as_posix()


def _赤の訳(file: str, 訳: str) -> str:
    return (f"許しの表に無い飛ばし（tests/conftest.py の 許す飛ばし）: {file}: {訳}\n"
            "飛ばさずに回す形に直す。本当に飛んでよいなら、許しの表に file・訳の頭・なぜ許すかを足す。")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    結果 = yield
    rep = 結果.get_result()
    if rep.skipped and not hasattr(rep, "wasxfail"):
        file = _file(item.path)
        訳 = _訳(rep)
        if not 許すか(file, 訳):
            結果.force_result(pytest.TestReport(rep.nodeid, rep.location, rep.keywords, "failed", _赤の訳(file, 訳),
                                                rep.when, rep.sections, rep.duration))


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector):
    結果 = yield
    rep = 結果.get_result()
    if rep.skipped and isinstance(collector, pytest.Module):
        file = _file(collector.path)
        訳 = _訳(rep)
        if not 許すか(file, 訳):
            結果.force_result(pytest.CollectReport(rep.nodeid, "failed", _赤の訳(file, 訳), []))
