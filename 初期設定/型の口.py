"""型の正本（型.json・項目.json・雛形/）を読む口。寄せる道具・始める道具・殻はここから今の型を引く。

  python3 初期設定/型の口.py 見出し      # 全部のシート×タブの見出しの並び（JSON）
  python3 初期設定/型の口.py md          # md の雛形 4 枚の見出しの並び（JSON）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent


def 型() -> dict:
    return json.loads((ここ / "型.json").read_text(encoding="utf-8"))


def 版() -> int:
    return 型()["版"]


def 項目たち() -> list[dict]:
    return json.loads((ここ / "項目.json").read_text(encoding="utf-8"))["項目"]


def 項目(名: str) -> dict:
    for it in 項目たち():
        if it["項目"] == 名:
            return it
    raise KeyError(名)


def 列になる項目(段: str, 辞書: list[dict] | None = None) -> list[dict]:
    """その段に置ける 1 つの値の項目（仕組みだけの項目・行の束・優先 B を除く）を辞書の順に。
    辞書を渡せばその辞書から（寄せる道具が型の file を指して読む時）、無ければ 初期設定/項目.json から。"""
    return [it for it in (項目たち() if 辞書 is None else 辞書)
            if 段 in it["段"] and "置く所" not in it and not it.get("優先B")]


def タブの列(t: dict, 辞書: list[dict] | None = None) -> list[dict]:
    """型.json のタブ 1 つ → 列の名と意味の並び（「列」の後ろに「項目の列」を広げる）。列を広げる決まりはここ 1 か所。"""
    out = [dict(c) for c in t.get("列", [])]
    if t.get("項目の列"):
        out += [{"名": it["項目"], "意味": it.get("意味", "")} for it in 列になる項目(t["項目の列"], 辞書)]
    return out


def タブ(シート: str, タブ名: str) -> dict:
    for s in 型()["シート"]:
        if s["シート"] == シート:
            for t in s["タブ"]:
                if t["タブ"] == タブ名:
                    return t
    raise KeyError(f"{シート}/{タブ名}")


def 列(シート: str, タブ名: str) -> list[dict]:
    """列の名と意味の並び（項目の列を広げた後）。"""
    return タブの列(タブ(シート, タブ名))


def 見出し(シート: str, タブ名: str) -> list[str]:
    return [c["名"] for c in 列(シート, タブ名)]


def 全部の見出し() -> dict[str, list[str]]:
    return {f'{s["シート"]}/{t["タブ"]}': 見出し(s["シート"], t["タブ"]) for s in 型()["シート"] for t in s["タブ"]}


def 雛形(名: str) -> str:
    for m in 型()["md の雛形"]:
        if m["名"] == 名:
            return (ここ / m["雛形"]).read_text(encoding="utf-8")
    raise KeyError(名)


def md_の見出し(名: str) -> list[str]:
    return [l for l in 雛形(名).splitlines() if l.startswith("#")]


def 全部の_md_の見出し() -> dict[str, list[str]]:
    return {m["名"]: md_の見出し(m["名"]) for m in 型()["md の雛形"]}


def 見出しの違い(シート: str, タブ名: str, 今の見出し: list[str]) -> list[str]:
    """Drive のシートの 1 行目と型の見出しを照らし、違いを 1 行ずつ返す（無ければ []）。"""
    型の = 見出し(シート, タブ名)
    if 今の見出し == 型の:
        return []
    out = [f"無い列: {c}" for c in 型の if c not in 今の見出し]
    out += [f"型に無い列: {c}" for c in 今の見出し if c not in 型の]
    if not out:
        out.append("列の並びが型と違う")
    return out


if __name__ == "__main__":
    何 = sys.argv[1] if len(sys.argv) > 1 else "見出し"
    out = 全部の見出し() if 何 == "見出し" else 全部の_md_の見出し()
    json.dump({"版": 版(), 何: out}, sys.stdout, ensure_ascii=False, indent=1)
    print()
