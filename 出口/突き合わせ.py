"""人×項目の突き合わせ（確かめと仮.md §2・§4）。照らす芯は出口にこの 1 本だけ。

- こちら＝関所を通った芯の行。給与ソフト＝読み口の行。仮で外した人は突き合わせない（表に出さない）。
- 差は 0 だけを一致（許す幅を持たない。丸めの違いも差として出す）。片方だけも差。
- 差のある行は質問と回答へ回す問いにして返す（同じ見立て・同じ出所は 1 問）。差を見てマスタや計算を直さない。
- 「差 0 の月」と、会社ごとの続けて差 0 の月数（給与ソフトを外す条件の数）を返す。外すかどうかは事務所が決める。
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .形 import 対応にする
from .行 import 行, 賞与か, 支給月の並び
from .関所 import 関所を通った, 通ったかを確かめる

列 = ("支給月", "会社", "NO", "項目", "こちら", "給与ソフト", "差", "差の見立て", "差の出所")
見立てたち = ("入力の違い", "決まりの違い", "丸め", "片方だけ", "不明")
場面たち = ("入社", "退社", "賞与", "年の変わり目", "料率の変わる月")
丸めを見る形 = ("円", "分")   # 円は 1 円・分は 1 分（10進の時間の字の四捨五入）以下を丸めと見立てる。日・回は見ない
答え方 = ("こちらが違う（決まりの md・マスタを答えを出所に直す）", "給与ソフトが違う（事務所が給与ソフトの入力を直す）")


def _字(v: Decimal | None) -> str:
    if v is None:
        return ""
    v = v.normalize()
    return str(int(v)) if v == v.to_integral_value() else format(v, "f")


@dataclass(frozen=True)
class 突き合わせの行:
    支給月: str
    会社: str
    NO: str
    項目: str
    こちら: Decimal | None
    給与ソフト: Decimal | None
    差の見立て: str
    差の出所: str

    @property
    def 片方だけ(self) -> bool:
        return self.こちら is None or self.給与ソフト is None

    @property
    def 差(self) -> Decimal | None:
        return None if self.片方だけ else self.こちら - self.給与ソフト

    @property
    def 一致(self) -> bool:
        return not self.片方だけ and self.差 == 0

    def 字の行(self) -> tuple[str, ...]:
        差 = "片方だけ" if self.片方だけ else _字(self.差)
        return (self.支給月, self.会社, self.NO, self.項目, _字(self.こちら), _字(self.給与ソフト),
                差, self.差の見立て, self.差の出所)


@dataclass(frozen=True)
class 突き合わせの結果:
    行たち: tuple[突き合わせの行, ...]
    人の状態: dict           # (支給月, 会社, NO) → 一致・差あり・未突き合わせ
    問い: tuple[dict, ...]
    照らさなかった項目: tuple[str, ...]   # こちらにあるが対応に受ける欄が無い項目（照らせない）
    外した人: tuple
    照らさなかった人: tuple[str, ...] = ()  # 給与ソフトへ渡さなかった人（業務委託など）
    要確認: tuple[str, ...] = ()

    def 表(self) -> list[tuple[str, ...]]:
        return [列] + [r.字の行() for r in self.行たち]

    def 差の行(self) -> list[突き合わせの行]:
        return [r for r in self.行たち if not r.一致]


def _見立て(r_こちら: 行 | None, 給与ソフト: Decimal | None, 欄, 入力の違いがある人: bool) -> str:
    if r_こちら is None or 給与ソフト is None:
        return "片方だけ"
    差 = r_こちら.値 - 給与ソフト
    if 欄.渡す:
        return "入力の違い"           # 給与ソフトへ渡した値と給与ソフトが使った値が違う
    if 欄.形 in 丸めを見る形 and abs(差) <= 1:
        return "丸め"
    return "不明" if 入力の違いがある人 else "決まりの違い"


def 突き合わせる(通った: 関所を通った, 給与ソフトの行, 欄の対応, 渡さなかった人=()) -> 突き合わせの結果:
    """渡さなかった人: 給与ソフトへ取り込みを渡していない人の NO（委託も取り込む が無い事務所の業務委託の人）。
    給与ソフトに結果が無いのが正しい人なので照らさず、`照らさなかった人` に返す。"""
    通った = 通ったかを確かめる(通った)
    渡さない = {str(x) for x in 渡さなかった人}
    受ける = {x.項目: x for x in 対応にする(欄の対応) if x.受ける}
    外した = 通った.外した人の鍵()
    こちら = {r.鍵: r for r in 通った.行たち if r.項目 in 受ける and r.NO not in 渡さない}
    照らさない = list(dict.fromkeys(r.項目 for r in 通った.行たち if r.項目 not in 受ける and r.NO not in 渡さない))
    相手_行たち = getattr(給与ソフトの行, "行たち", 給与ソフトの行)
    相手 = {}
    要確認 = []
    for r in 相手_行たち:
        if r.項目 not in 受ける:
            要確認.append(f"給与ソフトの行 {r.NO} の項目「{r.項目}」は対応に受ける欄が無い（照らしていない）")
            continue
        if r.人 in 外した or r.NO in 渡さない:
            continue                  # 仮で外した人・渡さなかった人は給与ソフトに居ても突き合わせない
        相手[r.鍵] = r
    鍵たち = sorted(set(こちら) | set(相手), key=lambda k: (支給月の並び(k[0]), k[1], k[2], list(受ける).index(k[3])))
    # 先に入力の違いのある人を見る（決まりの違いと不明を分けるため）
    入力違い = set()
    for k in 鍵たち:
        a, b = こちら.get(k), 相手.get(k)
        if a is not None and b is not None and a.値 != b.値 and 受ける[k[3]].渡す:
            入力違い.add(k[:3])
    out = []
    for k in 鍵たち:
        a, b = こちら.get(k), 相手.get(k)
        bv = b.値 if b is not None else None
        same = a is not None and b is not None and a.値 == b.値
        見立て = "" if same else _見立て(a, bv, 受ける[k[3]], k[:3] in 入力違い)
        出所 = "" if same else (a.出所 if a is not None else (b.出所 if b is not None else ""))
        out.append(突き合わせの行(*k, こちら=a.値 if a is not None else None, 給与ソフト=bv,
                               差の見立て=見立て, 差の出所=出所))
    状態 = {}
    for r in out:
        k = (r.支給月, r.会社, r.NO)
        状態[k] = "差あり" if (not r.一致 or 状態.get(k) == "差あり") else "一致"
    for k in 外した:
        状態[k] = "未突き合わせ"
    return 突き合わせの結果(行たち=tuple(out), 人の状態=状態, 問い=tuple(_問いにする(out)),
                          照らさなかった項目=tuple(照らさない), 外した人=通った.外した人たち,
                          照らさなかった人=tuple(sorted(渡さない & {r.NO for r in 通った.行たち})),
                          要確認=tuple(要確認))


def _問いにする(rows: list[突き合わせの行]) -> list[dict]:
    組: dict[tuple, list[突き合わせの行]] = {}
    for r in rows:
        if not r.一致:
            組.setdefault((r.支給月, r.会社, r.差の見立て, r.差の出所), []).append(r)
    out = []
    for (支給月, 会社, 見立て, 出所), rs in 組.items():
        人 = list(dict.fromkeys(r.NO for r in rs))
        項目 = list(dict.fromkeys(r.項目 for r in rs))
        out.append({
            "支給月": 支給月, "会社": 会社, "差の見立て": 見立て, "差の出所": 出所,
            "人": tuple(人), "項目": tuple(項目), "行": tuple(r.字の行() for r in rs),
            "文": f"{支給月} 会社 {会社}: こちらと給与ソフトに差が {len(rs)} 件（見立て {見立て}・人 {'・'.join(人)}・項目 {'・'.join(項目)}）。"
                 f"どちらが違いますか",
            "答え方の例": 答え方,
        })
    return out


# ---- 差 0 の月の数え方 ----

def 月の記録(結果: 突き合わせの結果, 会社: str, 支給月: str, 給与ソフトが違うで閉じた: int = 0, 場面=()) -> dict:
    """1 会社 1 支給月の記録（管理表の「突き合わせ」「外した人」の元）。殻が管理表へ書き、次の月に渡し返す。

    給与ソフトが違うで閉じた: その月の差の問いのうち「給与ソフトが違う」で閉じた数（殻が質問と回答から数える）。
    場面: その月にあった場面（入社・退社・年の変わり目・料率の変わる月）。賞与は支給月から出口が足す。
    """
    会社 = str(会社)
    人 = {k for k in 結果.人の状態 if k[0] == 支給月 and k[1] == 会社}
    外した = [x for x in 結果.外した人 if x.支給月 == 支給月 and x.会社 == 会社]
    差 = [r for r in 結果.差の行() if r.支給月 == 支給月 and r.会社 == 会社]
    突き合わせた = len([k for k in 人 if 結果.人の状態[k] != "未突き合わせ"])
    場面 = set(場面)
    知らない = 場面 - set(場面たち)
    if 知らない:
        raise ValueError(f"場面「{'・'.join(sorted(知らない))}」は {'・'.join(場面たち)} の外")
    if 賞与か(支給月):
        場面.add("賞与")
    return {
        "支給月": 支給月, "会社": 会社, "突き合わせた人": 突き合わせた, "差の行": len(差),
        "外した人": len(外した), "給与ソフトが違うで閉じた": int(給与ソフトが違うで閉じた),
        "場面": tuple(x for x in 場面たち if x in 場面),
        "差0の月": 突き合わせた > 0 and not 差 and not 外した and not 給与ソフトが違うで閉じた,
    }


def _次の月(支給月: str) -> str:
    y, m, _ = 支給月の並び(支給月)
    return f"{y + (m == 12)}-{m % 12 + 1:02d}"


def 続けて差0の月数(記録たち, N: int = 3) -> dict:
    """会社ごとに、最新の月から遡って続けて差 0 の月を数える（賞与も 1 回を 1 か月）。

    1 つでも外れた月・記録の無い給与の月（突き合わせなかった月）で 0 に戻る。
    まだ見ていない場面＝数えた月のどれにも無かった場面。N は事務所の設定（推奨 3）。判断はしない。
    """
    会社ごと: dict[str, list[dict]] = {}
    for r in 記録たち:
        会社ごと.setdefault(str(r["会社"]), []).append(r)
    out = {}
    for 会社, rs in sorted(会社ごと.items()):
        rs = sorted(rs, key=lambda r: 支給月の並び(r["支給月"]))
        数えた = []
        後の給与の月 = None
        for r in reversed(rs):
            if not r["差0の月"]:
                break
            if not 賞与か(r["支給月"]):
                if 後の給与の月 is not None and _次の月(r["支給月"]) != 後の給与の月:
                    break             # 間に記録の無い月がある
                後の給与の月 = r["支給月"]
            数えた.append(r)
        見た = {s for r in 数えた for s in r.get("場面", ())}
        out[会社] = {"月数": len(数えた), "N": N,
                    "数えた月": tuple(r["支給月"] for r in reversed(数えた)),
                    "まだ見ていない場面": tuple(s for s in 場面たち if s not in 見た)}
    return out
