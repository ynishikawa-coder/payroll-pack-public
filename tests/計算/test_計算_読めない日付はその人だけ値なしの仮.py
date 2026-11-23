"""注入の試験: 人の日付の値（入社日・退職日・生年月日・社保の取得日・喪失日）が日付として読めない時、素の ValueError で
月の計算を止めず、その人だけ値なしの仮＋問い 1 つにして、ほかの人は計算する（給与も賞与も）。

前は 支給控除・賞与 が date.fromisoformat を直に呼び、読めない字で素の ValueError が出て月の全員が止まった。
今は 1 つの正本 芯/計算/形.日付 が 形の誤り を出し、計算する・賞与を計算する の口がその人だけ値なしの仮にする。"""
import pytest

from 作る_計算 import 人, 月の数字, 決まり, 置き場
from 芯.計算 import 計算する, 賞与を計算する
from 芯.計算.形 import 形の誤り, 日付

悪い = ("2026-13-45", "令和8年4月1日", "abc", "  ", "　")   # 空白だけ＝名は在るのに読めない（黙って「無し」と読まない）
良い, 崩れ = ("C1", "0001"), ("C1", "0002")


def test_日付の正本は空をNoneに読めない字を形の誤りにする():
    assert 日付(None) is None and 日付("") is None
    assert str(日付("2026-04-01")) == "2026-04-01"
    for 値 in 悪い:
        with pytest.raises(形の誤り):
            日付(値, "人.入社日")


def _状態(r, 鍵):
    (s,) = [x["状態"] for x in r["人"] if (x["会社"], x["NO"]) == 鍵]
    return s


def _その人だけ値なしの仮(r, 名):
    assert _状態(r, 良い) == "確認済"
    assert _状態(r, 崩れ) == "仮"
    (q,) = [q for q in r["問い"] if 名 in q["何が無いか"]]
    assert q["人"] == [崩れ] and "全部" in q["変わる項目"]
    assert [x["値"] for x in r["行"] if (x["会社"], x["NO"]) == 崩れ] == [None]


@pytest.mark.parametrize("名", ["人.入社日", "人.退職日", "人.生年月日", "社保.取得日", "社保.喪失日"])
@pytest.mark.parametrize("値", 悪い)
def test_給与で読めない日付はその人だけ値なしの仮(tmp_path, 名, 値):
    r = 計算する(月の数字(NO="0001") + 月の数字(NO="0002"),
               決まり={良い: 決まり(), 崩れ: 決まり()}, 人={良い: 人(), 崩れ: 人(**{名: 値})}, 置き場=置き場(tmp_path))
    if 名 == "人.生年月日" and not 値.strip():
        # 空白だけの生年月日は 要る値 が先に「無い」と読み、年齢で変わる項目だけの仮＋問いにする（月は止めない・その人は出口へ出ない）
        assert _状態(r, 良い) == "確認済" and _状態(r, 崩れ) == "仮"
        (q,) = [q for q in r["問い"] if 名 in q["何が無いか"]]
        assert q["人"] == [崩れ]
        return
    _その人だけ値なしの仮(r, 名)


@pytest.mark.parametrize("値", 悪い)
def test_賞与で読めない退職日はその人だけ値なしの仮(tmp_path, 値):
    r = 賞与を計算する([{"会社": "C1", "NO": n, "額": 300000, "原本の名前": "作り物"} for n in ("0001", "0002")],
                   支給日="2027-02-26", 決まり={良い: 決まり(), 崩れ: 決まり()}, 人={良い: 人(), 崩れ: 人(**{"人.退職日": 値})},
                   前月の課税対象額={良い: 300000, 崩れ: 300000}, 前の標準賞与額={良い: 0, 崩れ: 0},
                   計算期間={良い: 6, 崩れ: 6}, 置き場=置き場(tmp_path))
    _その人だけ値なしの仮(r, "人.退職日")


def test_芯の計算で人の日付を直に読む所が無い():
    """人・決まりの日付の字は 形.日付 だけが読む（直の fromisoformat は素の ValueError で月を止める）。
    外す所: 形.py（正本）・__init__.py（呼ぶ側が渡す 支給日 の字）・暦.py（法の表の祝日の日）。"""
    from pathlib import Path
    根 = Path(__file__).resolve().parents[2] / "芯" / "計算"
    外す = {"形.py", "__init__.py", "暦.py"}
    直 = [f"{p.name}:{i}" for p in sorted(根.glob("*.py")) if p.name not in 外す
          for i, 行 in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if "fromisoformat" in 行]
    assert not 直, 直
