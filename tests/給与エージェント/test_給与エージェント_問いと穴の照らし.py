"""問いの照らし（bin/問いの照らし.py＝パックの 確認ページ/前の答え.py を呼ぶだけ）と穴の照らし（bin/穴の照らし.py）の試験。作り物だけ。

防ぐ故障: 答え済みの問いを事務所の担当者へ出す。表やパックの口が無い時に黙って通す。穴を文で書いただけで課題の行にしない。
  開いた課題のある月を出す。閉じた状態が渡されないのに全部を開いた／閉じたと決める。
"""
import io
import json
import subprocess
import sys

from 手伝い import BIN, 根, 課題の_id

import 問いの照らし as Q  # noqa: E402
import 穴の照らし as H  # noqa: E402

見出し = ["問いの番号", "会社", "対象", "質問", "回答", "反映先", "答えで変わる項目と人", "理由"]


def test_答え済みの問いは本物のパックの口で止める(tmp_path):
    rows = tmp_path / "qa.json"
    rows.write_text(json.dumps({"values": [見出し, ["Q209901-1", "作り物の会社", "会社", "通勤の手当の上限はいくらですか", "月 1 万", "", "", ""]]},
                               ensure_ascii=False), encoding="utf-8")
    qs = tmp_path / "qs.txt"
    qs.write_text("通勤の手当の上限はいくらですか\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(BIN / "問いの照らし.py"), "--rows", str(rows), "--questions", str(qs), "--パック", str(根)],
                       capture_output=True, text=True)
    assert r.returncode == 2 and "答え済み" in r.stderr
    qs.write_text("新しい作り物の手当はありますか\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(BIN / "問いの照らし.py"), "--rows", str(rows), "--questions", str(qs), "--パック", str(根)],
                       capture_output=True, text=True)
    assert r.returncode == 0


def test_表とパックの口が無い時は呼ばずに_exit_2(tmp_path):
    def never(*a, **k):
        raise AssertionError("呼んだ")
    assert Q.main(["--questions", "x"], runner=never) == 2
    assert Q.main(["--rows", "x", "--パック", str(tmp_path)], runner=never) == 2


def test_穴の行は課題の_id_か起票の行があれば起票済み():
    link = "https://example.invalid/p/" + 課題の_id
    assert H.起票していない穴(f"- 休憩の境を表せない <{link}>", {課題の_id}) == []
    text = "- 休憩の境を表せない（引き継ぎ）\n- 課題 " + link + ": 「休憩の境を表せない（引き継ぎ）」"
    assert H.起票していない穴(text, {課題の_id}) == []
    # ハイフン付きの id も同じ課題
    hy = f"{課題の_id[:8]}-{課題の_id[8:12]}-{課題の_id[12:16]}-{課題の_id[16:20]}-{課題の_id[20:]}"
    assert H.起票していない穴(f"- 直されていない <https://example.invalid/{hy}>", {課題の_id}) == []


def test_課題でないリンクしか無い穴と仕組みの名():
    assert H.起票していない穴("- 直されていない所 <https://example.invalid/" + "b" * 32 + ">", {課題の_id})
    assert H.起票していない穴("### 穴の起票（2099-01-01）\n- 給与・穴の照らし", set()) == []
    assert H.起票していない穴("### 穴の起票\n- 端数の決まりを表せない", set())


def test_開いた課題は月の無い題を全月として数え_別の月だけの題と閉じた課題は飛ばす():
    rows = [{"題": "課題: 休憩の境", "状態": "進行中"}, {"題": "課題: 2099.02支給 別の月", "状態": "進行中"},
            {"題": "課題: 2099.01支給 済んだ", "状態": "完了"}, {"題": "課題: 全月 端数", "状態": "未着手"},
            {"題": "ただの行", "状態": "進行中"}]
    got = [r["題"] for r in H.開いた課題(rows, "2099.01支給", ["完了"])]
    assert got == ["課題: 休憩の境", "課題: 全月 端数"]


def test_閉じた状態が渡されない時は照らせない():
    m = {"課題": [], "課題の id": [], "閉じた状態": [], "月の本文": ""}
    assert any("閉じた状態" in r for r in H.課題と穴の赤(m, "2099.01支給"))
    assert H.課題と穴の赤({**m, "閉じた状態": ["完了"]}, "2099.01支給") == []


def test_命令の照らすと起票の案(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({"課題": [], "課題の id": [], "閉じた状態": ["完了"], "月の本文": "- 端数を表せない"}, ensure_ascii=False),
                 encoding="utf-8")
    r = subprocess.run([sys.executable, str(BIN / "穴の照らし.py"), "照らす", str(f), "--支給月", "2099.01支給",
                        "--パック", str(根)], capture_output=True, text=True)
    assert r.returncode == 2 and "起票していない穴" in r.stdout
    r = subprocess.run([sys.executable, str(BIN / "穴の照らし.py"), "起票の案", str(f), "--支給月", "2099.01支給",
                        "--パック", str(根)], capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout)[0]["題"].startswith("課題: 2099.01支給")


def test_字の揺れをそろえて照らす_全角の頭と幅の無い字と年月の書き方():
    # 壊す: 字のそのままの一致だと、全角の「課題：」・頭の空白・幅の無い字を挟んだ穴の語・「2099年1月」の題が数えられず通った（台帳 束 K3）
    rows = [{"題": "　課題：２０９９年１月 端数", "状態": "進行中"}, {"題": "課\u200b題: 2099/02 別の月", "状態": "進行中"},
            {"題": "課題: 2099.01支給 済んだ", "状態": " 完了 "}]
    assert [r["題"] for r in H.開いた課題(rows, "2099.01支給", ["完了"])] == ["　課題：２０９９年１月 端数"]
    assert [r["題"] for r in H.開いた課題(rows, "2099.02支給", ["完了"])] == ["課\u200b題: 2099/02 別の月"]
    assert H.起票していない穴("- 端数の決まりを表\u200bせない", set()) == ["- 端数の決まりを表\u200bせない"]
    assert H.起票していない穴("- 休憩の境が直されて　いない", set())
    assert H.拾う("ｘ 穴 が在る\n仕組み: 穴の\u200b照らし") == ["ｘ 穴 が在る"]


def test_支給月が読めない時は照らせない():
    m = {"課題": [{"題": "課題: x", "状態": "進行中"}], "課題の id": [], "閉じた状態": ["完了"], "月の本文": ""}
    assert any("照らせない" in r for r in H.課題と穴の赤(m, "来月"))
