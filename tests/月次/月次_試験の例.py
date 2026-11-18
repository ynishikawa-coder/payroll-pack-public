"""試験の例の行（前のマスタ「例」と同じ列の作り物）を 給与のルール.md の字にする（月次.月を回す・賞与を回す は MD の字だけから例を読む）。"""
import 月次


def 例をMDに(例) -> str | None:
    if 例 is None:
        return None
    列 = 月次.例の確かめ.MDの例の列
    md = ["# 給与のルール（作り物）", ""]
    for i, e in enumerate(月次.例の確かめ.行たち(例)):
        md += [f"### 例 {i + 1}", "", "| " + " | ".join(列) + " |", "|" + "---|" * len(列),
               "| " + " | ".join(str(e.get(c, "") or "").replace("|", "\\|") for c in 列) + " |", ""]
    return "\n".join(md)
