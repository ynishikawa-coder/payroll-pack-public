"""寄せの人×項目の突き合わせの口（〔口: 寄せる〕が呼ぶ・寄せる道具.md §1.6）。置き場を開かない。

殻（事務所の側の口）が突き合わせる月の出す物を読み（寄せの前）、出荷の口の照らすで寄せた後を計算する。
比べる字・違いの数え方・比較の写しの締めの行・合わない時の訳はこの口だけが決める（殻に同じ判断を写さない）。

  python3 道具/寄せ/突き合わせ.py 字にする     < 入力.json   # {"出す物": {物: 表|{"CSV",…}}} → {"出す物"}（セルを比べる字に）
  python3 道具/寄せ/突き合わせ.py 突き合わせる < 入力.json   # {"前","後","元"} → {"違い": [字], "訳": 字|""}
  python3 道具/寄せ/突き合わせ.py 版の違い     < 入力.json   # {"出した物","前"} → {"版の違い"}
  python3 道具/寄せ/突き合わせ.py 比較の締めの行 < 入力.json # {"締めの記録","会社","支給月"} → {"行"}（版はこの口を置いたパックの版）

形の崩れた入力・比べられない物は {"拒む": 訳}・終わりの値 2（殻は訳のまま止める）。
"""
import base64
import csv
import io
import json
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent
if str(ここ.parent.parent) not in sys.path:
    sys.path.insert(0, str(ここ.parent.parent))

from 月次.口の入口 import 拒む, 回す  # noqa: E402  拒むの約束（どの崩れも {"拒む"}・終わりの値 2）は入口の 1 つだけ

版の列 = "パックの版"




def セルの字(v) -> str:
    """表のセルを比べる字にする（寄せの前と後で同じこの 1 つの口だけを通す）。数は書式を付けない字（整数の float は整数）。"""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def 字にする(出す物: dict) -> dict:
    """物ごとの表のセルを比べる字に。CSV（{"CSV": …}）は置いた字のまま。"""
    if not isinstance(出す物, dict):
        raise 拒む("出す物は {物: 表} で渡す")
    return {物: dict(x) if isinstance(x, dict) else [[セルの字(c) for c in r] for r in x] for 物, x in 出す物.items()}


def 表にする(x, spec) -> list:
    """突き合わせの片方を表にする。CSV は寄せた後の出す物の 文字コード・区切りで読む（前と後で同じ読み方）。"""
    if not isinstance(x, dict):
        return x
    raw = base64.b64decode(x["CSV"])
    if not isinstance(spec, dict) or not spec.get("文字コード"):
        raise 拒む("CSV の出す物を読む 文字コード が寄せた後の出す物に無い＝突き合わせられない")
    return [list(r) for r in csv.reader(io.StringIO(raw.decode(spec["文字コード"]), newline=""),
                                        delimiter=spec.get("区切り") or ",")]


def 違い(前: dict, 後: dict) -> list[dict]:
    """物ごとの表を 1 字ずつ照らした違い（物・人・項目・前・後、表の形の違いは 訳）。"""
    diff = []
    for 物 in sorted(set(前) | set(後)):
        a, b = 前.get(物), 後.get(物)
        if a is None or b is None:
            diff.append({"物": 物, "訳": f"{'寄せの前' if a is None else '寄せた後'}に無い"})
            continue
        if isinstance(a, dict) != isinstance(b, dict):
            diff.append({"物": 物, "訳": f"寄せの前は {'CSV' if isinstance(a, dict) else '表'}・寄せた後は "
                                         f"{'CSV' if isinstance(b, dict) else '表'}"})
            continue
        if isinstance(a, dict) and a["CSV"] == b["CSV"]:
            continue   # 置いた字と 1 バイトも違わない
        a, b = 表にする(a, b), 表にする(b, b)
        h = a[0] if a else []
        # 人が列の向きの表（パックの 出口/書き口.py の 支給控除一覧＝見出しの行が「項目＋人の NO…＋合計」）は、
        # 行の頭が項目の名・見出しが人。見出しの頭の字で向きを読む（表の名で決めない）
        縦 = bool(h) and str(h[0]) == "項目"
        for i in range(max(len(a), len(b))):
            ra = a[i] if i < len(a) else None
            rb = b[i] if i < len(b) else None
            if ra is None or rb is None:
                diff.append({"物": 物, "行": i + 1, "訳": f"{'寄せの前' if ra is None else '寄せた後'}に無い"})
                continue
            for j in range(max(len(ra), len(rb))):
                x = ra[j] if j < len(ra) else ""
                y = rb[j] if j < len(rb) else ""
                if str(x) != str(y):
                    行の頭, 見出し = (ra[0] if ra else ""), (h[j] if j < len(h) else j + 1)
                    diff.append({"物": 物, "人": 見出し if 縦 else 行の頭, "項目": 行の頭 if 縦 else 見出し,
                                 "前": x, "後": y})
    return diff


def 突き合わせる(前: dict, 後: dict) -> list[str]:
    """物ごとの表を 1 字ずつ照らす（寄せは給与の結果を 1 円も変えない）。違いを人×項目の形で返す。"""
    return [f"{d['物']} {d['行']} 行目: {d['訳']}" if "行" in d else f"{d['物']}: {d['訳']}" if "訳" in d else
            f"{d['物']} {d['人']}×{d['項目']}: 前 {d['前']!r} 後 {d['後']!r}" for d in 違い(前, 後)]


def 合わない訳(違いたち: list[str], 元: str) -> str:
    """突き合わせが合わない時に寄せ中のまま書く訳（違いが無ければ空）。"""
    if not 違いたち:
        return ""
    return f"人×項目の突き合わせが合わない（{len(違いたち)} 所: {'／'.join(違いたち[:3])}・突き合わせの元: {元}）"


def 版の違い(出した物: dict, 前: dict) -> list[dict]:
    """出した物（前の版で出した字）と、今の版で計算した寄せの前の違い＝版の出し方の違い。寄せの違いではない。
    寄せの記録と返りに残す物なので、値と人は書かず物ごとの所の数と項目の名だけ（会社の値を記録に写し直さない）。"""
    out: dict = {}
    for d in 違い(出した物, 前):
        x = out.setdefault(d["物"], {"物": d["物"], "所": 0, "項目": [], "訳": []})
        x["所"] += 1
        if "訳" in d:
            x["訳"].append(f"{d['行']} 行目: {d['訳']}" if "行" in d else d["訳"])
        elif str(d["項目"]) not in x["項目"]:
            x["項目"].append(str(d["項目"]))
    return list(out.values())


def 今の版() -> str:
    from 出口 import 証明
    return 証明.パックの版()


def 比較の締めの行(表: list, 会社: str, 支給月: str, 版: str | None = None) -> list:
    """比較用の写しの行だけ、実際に試算する版に揃える。台帳への締め・書込みではない。"""
    版 = 今の版() if 版 is None else 版
    if not 版 or not 会社 or not 支給月 or not 表:
        raise 拒む("比較の版・会社・月・締めの記録が揃わない＝比較を止める")
    header = list(表[0])
    # 型が古い台帳（寄せる前）には パックの版 の列が必ず無い＝それを足すのが寄せる理由。比べる写しにだけ列を足す（台帳には書かない）。
    # 2 つ在る・ほかの列が欠ける・重なる時は止める
    if 版の列 not in header:
        header.append(版の列)
    要る = ("会社", "支給月", "状態", 版の列)
    if any(header.count(k) != 1 for k in 要る):
        raise 拒む("比較用の締めの記録の見出しが揃わない")
    ic, im, ist, iv = (header.index(k) for k in 要る)
    out, found = [header], 0
    for 元の行 in 表[1:]:
        row = list(元の行)
        if len(row) > max(ic, im) and str(row[ic]).strip() == 会社 and str(row[im]).strip() == 支給月:
            if len(row) <= ist or str(row[ist]).strip() != "締まった":
                raise 拒む("比較対象の締めが未完了＝比較を止める")
            row.extend([""] * max(0, iv + 1 - len(row)))
            row[iv] = 版
            found += 1
        out.append(row)
    if not found:
        raise 拒む("比較対象の会社・月の締めの行が無い")
    return out


def _口(何: str, x) -> dict:
    if not isinstance(x, dict):
        raise 拒む("入力は JSON の表で渡す")
    if 何 == "字にする":
        return {"出す物": 字にする(x.get("出す物"))}
    if 何 == "突き合わせる":
        d = 突き合わせる(x.get("前") or {}, x.get("後") or {})
        return {"違い": d, "訳": 合わない訳(d, str(x.get("元") or ""))}
    if 何 == "版の違い":
        return {"版の違い": 版の違い(x.get("出した物") or {}, x.get("前") or {})}
    if 何 == "比較の締めの行":
        return {"行": 比較の締めの行(x.get("締めの記録"), str(x.get("会社") or ""), str(x.get("支給月") or ""))}
    raise 拒む(f"知らない口: {何}")


if __name__ == "__main__":
    回す(_口)
