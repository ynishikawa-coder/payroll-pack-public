"""消した項目の見張り（型の版 29）: 芯が読まない会社の決まりの項目を、辞書にも、聞く・埋める・写す所にも戻さない。

芯（芯/）・月次・出口・初期設定の照らし・plugins/ のどこも読まない 19 項目を消した（決定 17「使わない項目や式を増やさない」）。うち 休日.代休の日の控除 は芯/集計 が読むようになり辞書へ戻した。
辞書（項目.json）に戻すと、社員の列（型.json の項目の列）・型ごとの網・法の線の点検 から担当者に聞く・埋めさせる値が増える。
芯が読むようになった時は、読む所と一緒にこの並びから外して戻す。
"""
import importlib.util
import json
from pathlib import Path

import pytest

根 = Path(__file__).resolve().parent.parent.parent
初期設定 = 根 / "初期設定"

消した項目 = (
    "支払.組", "支払.勤怠の締め", "支払.支払額の端数", "支払.方法",
    "休日.振替", "休日.代休",
    "割増.代替休暇", "欠勤.割る数", "欠勤.遅刻早退の単位",
    "有給.1日の賃金", "有給.時間単位",
    "休暇.特別休暇", "休暇.産休育休の賃金",
    "手当.通勤の形", "手当.通勤の定期",
    "控除.差押", "現物.行", "委託.法定休日の曜日",
)


def _読む(名):
    return json.loads((初期設定 / 名).read_text(encoding="utf-8"))


def _型の口():
    s = importlib.util.spec_from_file_location("初期設定_型の口_消した項目", 初期設定 / "型の口.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _段の解決():
    s = importlib.util.spec_from_file_location("初期設定_段の解決_消した項目", 初期設定 / "段の解決.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_消した項目は18():
    # 休日.代休の日の控除 は芯/集計 が読むようになり辞書へ戻した（月給などの人の代休の日を引くか）
    assert len(set(消した項目)) == 18


@pytest.mark.parametrize("名", 消した項目)
def test_消した項目は辞書に無い(名):
    assert 名 not in {it["項目"] for it in _読む("項目.json")["項目"]}


def test_消した項目を聞く所と埋める所に無い():
    網 = {n for t in _読む("型ごとの網.json")["型"] for c in t["網"].values() for n in c["項目"]}
    点検 = {r["項目"] for v in _読む("法の線の点検.json").values() if isinstance(v, list) for r in v if isinstance(r, dict) and "項目" in r}
    型の列 = {c for 見出し in _型の口().全部の見出し().values() for c in 見出し}   # 項目の列（辞書から出す列）も含む
    assert not set(消した項目) & 網
    assert not set(消した項目) & 点検
    assert not set(消した項目) & 型の列
    assert not set(消した項目) & set(_段の解決().人の行の束)


def test_芯が読む名に消した項目は無い():
    """芯が読む名（芯/設定の表.json）に消した名が在れば、消してはいけなかった（読む所が在る）。"""
    表 = json.loads((根 / "芯" / "設定の表.json").read_text(encoding="utf-8"))
    名たち = json.dumps(表, ensure_ascii=False)
    assert [n for n in 消した項目 if f'"{n}"' in 名たち] == []


def _人ごとの行(名, 額="10000"):
    return _段の解決().解く("2027.02支給", 社員=[{"会社": "C1", "NO": "1"}],
                         支給控除の項目=[{"会社": "C1", "項目": "住宅手当", "適用開始": ""}],
                         人ごとの支給控除=[{"会社": "C1", "NO": "1", "項目": 名, "額": 額, "適用開始": ""}])


@pytest.mark.parametrize("名", ["控除.差押", "現物.行", "住宅手当x"])
def test_人ごとの支給控除の置けない名は黙って入れず仮(名):
    """前の会社に残る 控除.差押・現物.行 の行や打ち間違いは、項目.人の額 に入れず知らせ＋その人を仮にし問う
    （差押は手取りを減らす控除＝黙って落とすと払いすぎのまま出る）。"""
    r = _人ごとの行(名)
    assert 名 not in r["人"][("C1", "1")].get("項目.人の額", {}) and 名 not in r["人"][("C1", "1")]
    assert [(x["NO"], x["項目"]) for x in r["仮の値"]] == [("1", 名)] and r["仮の値"][0]["問い"]
    assert any(名 in s for s in r["知らせ"])


def test_人ごとの支給控除の支給控除の項目はそのまま人の額():
    r = _人ごとの行("住宅手当", "5000")
    assert r["人"][("C1", "1")]["項目.人の額"] == {"住宅手当": "5000"} and r["仮の値"] == []


@pytest.mark.parametrize("元", ["額:資格単価", "額:資格単価÷所定日数", "額:資格単価×日の所定÷月の所定時間"])
def test_単価の元の額で読む名は人の額へ渡る(元):
    """支給控除の項目の名でなくても、その会社の行の 単価の元 `額:<名>` が読む名（芯/計算 が 項目.人の額 から引く）は置ける名。"""
    r = _段の解決().解く("2027.02支給", 社員=[{"会社": "C1", "NO": "1"}],
                       支給控除の項目=[{"会社": "C1", "項目": "資格手当", "単価の元": 元, "数量の元": "勤怠の数:出勤日数", "適用開始": ""}],
                       人ごとの支給控除=[{"会社": "C1", "NO": "1", "項目": "資格単価", "額": "1000", "適用開始": ""}])
    assert r["人"][("C1", "1")]["項目.人の額"] == {"資格単価": "1000"} and r["仮の値"] == [] and r["知らせ"] == []
