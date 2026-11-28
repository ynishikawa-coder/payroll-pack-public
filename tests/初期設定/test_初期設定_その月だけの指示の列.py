"""台帳「その月だけの指示」（段の解決の中の名は 月の変動）の型の列と、段の解決が読む列が揃う事。作り物の値だけ。

根（2026-11-28）: 段の解決は 確認（要確認の行を使わない）と 原本の名前（同じ原本の読み直しを 1 行に）を読むのに、
型.json の列に無く、殻が型どおりに作ったタブでは読む列が欠けた（Drive の型.md §4・§10）。
読む列は段の解決のコードから拾う（ここに写さない）＝読む側が列を足せば型に無い列としてここで赤になる。
"""
import ast
import importlib.util
from pathlib import Path

根 = Path(__file__).resolve().parents[2]


def _読む(名, path):
    s = importlib.util.spec_from_file_location(名, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


口 = _読む("その月だけの指示の列_型の口", 根 / "初期設定" / "型の口.py")
段 = _読む("その月だけの指示の列_段の解決", 根 / "初期設定" / "段の解決.py")

# 月の変動の行（r）だけを読む関数（月の変動の入力 は 部品の行 も r で読むので外す・読む列は下の関数と同じ 項目・値・確認）
読む関数 = ("人の鍵", "その月の変動", "雇用分の欄の値", "_確認済か")


def _読む列() -> set[str]:
    木 = ast.parse((根 / "初期設定" / "段の解決.py").read_text(encoding="utf-8"))
    列 = set()
    for f in 木.body:
        if not (isinstance(f, ast.FunctionDef) and f.name in 読む関数):
            continue
        for n in ast.walk(f):
            # r.get("列") ・ r["列"]
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" \
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "r" \
                    and n.args and isinstance(n.args[0], ast.Constant):
                列.add(n.args[0].value)
            if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == "r" \
                    and isinstance(n.slice, ast.Constant):
                列.add(n.slice.value)
            # r.get(c) for c in ("項目", "値", "原本の名前")
            if isinstance(n, ast.comprehension) and isinstance(n.iter, ast.Tuple):
                列 |= {e.value for e in n.iter.elts if isinstance(e, ast.Constant)}
    return 列


def test_段の解決が読む列は型の列に在る():
    読む = _読む列()
    assert {"会社", "NO", "支給月", "項目", "値", "確認", "原本の名前"} <= 読む   # 拾い方が崩れれば止める
    型 = set(口.見出し(口.台帳の名(), "その月だけの指示"))
    assert 読む <= 型, f"段の解決が読むのに型に無い列: {sorted(読む - 型)}"


def test_型の見出しの行で確認と原本の名前が効く():
    """型の見出しだけで作った行で、要確認の行は使わず・同じ原本の読み直しは 1 行になる（作り物）。"""
    見 = 口.見出し(口.台帳の名(), "その月だけの指示")

    def 行(**v):
        return {k: v.get(k, "") for k in 見}

    rows = [行(会社="C作り物", NO="0001", 支給月="2099.04支給", 項目="欄の作り物", 値="10", 確認="要確認", 原本の名前="作り物.csv"),
            行(会社="C作り物", NO="0002", 支給月="2099.04支給", 項目="欄の作り物", 値="20", 原本の名前="作り物.csv"),
            行(会社="C作り物", NO="0002", 支給月="2099.04支給", 項目="欄の作り物", 値="20", 原本の名前="作り物.csv")]
    out, 外れ = 段.その月の変動("2099.04支給", rows)
    assert not 外れ and len(out[("C作り物", "0002")]) == 1
    assert 段.雇用分の欄の値("欄の作り物", out[("C作り物", "0001")]) is None
    assert 段.雇用分の欄の値("欄の作り物", out[("C作り物", "0002")]) == "20"
