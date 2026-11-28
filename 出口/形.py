"""給与ソフトの形と、欄と項目の対応（書き口と読み口が同じ 1 つを使う）。

- 給与ソフトの欄の名・並び・文字コードは出口の中だけ（芯は知らない）。
- 会社ごとに違う対応は Drive のマスタ「項目」の給与ソフトの欄から窓が引数で渡す（`欄の対応`）。
- 書き口は対応を順に引き、読み口は同じ対応を逆に引く（読み用の対応を別に持たない・確かめと仮.md §2）。
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_UP, Decimal

from .行 import 数にする

# 値の形（単位）。芯の値は 円＝整数・日＝数・分＝時間（勤怠の形.md §5 の単位）・回＝数。
値の形たち = ("円", "日", "分", "回")
# 時間の書き方（給与ソフトへ書く・読む字の形）。会社のマスタ「時間の書き方」から窓が渡す。
時間の書き方たち = ("60進", "時:分", "10進")
# 取り込みの渡し方。CSV＝給与ソフトが取り込む file（文字コードが要る）・表＝2_出す物 のスプレッドシートの表（人が給与ソフトへ写す）
渡し方たち = ("CSV", "表")


@dataclass(frozen=True)
class 欄:
    """1 項目 → 1 欄。渡す＝取り込みに書く。受ける＝給与ソフトの出力から読む（突き合わせる）。
    1 つの欄に幾つかの項目を当ててよい（足す。例 時給・日給・基本給 → 基本給の欄）＝`欄の組たち` が欄ごとにまとめる。"""
    項目: str
    欄: str
    形: str = "円"
    渡す: bool = True
    受ける: bool = True

    def __post_init__(self):
        if self.形 not in 値の形たち:
            raise ValueError(f"欄「{self.欄}」の形「{self.形}」は {'・'.join(値の形たち)} の外")
        if not (self.渡す or self.受ける):
            raise ValueError(f"欄「{self.欄}」は渡すも受けるも無い")


@dataclass(frozen=True)
class 欄の組:
    """給与ソフトの 1 つの欄と、そこへ足す項目たち（1 つなら今までの 1 項目 1 欄）。"""
    欄: str
    形: str
    渡す: bool
    受ける: bool
    項目たち: tuple[str, ...]

    @property
    def 項目(self) -> str:
        """読み口・突き合わせが使う項目の名（足す欄は項目を ＋ で並べた名）。"""
        return "＋".join(self.項目たち)


def 対応にする(rows) -> tuple[欄, ...]:
    """欄の対応（窓が渡す dict の並びか `欄の対応を組む` の結果）を対応にする。

    1 項目に 1 欄（同じ項目が 2 つの欄に出ると止まる）。1 つの欄に幾つかの項目を当てると、書く時に足す（読む時は足した値と照らす）。
    同じ欄に当てた項目は 形・渡す・受ける がそろう（そろわなければ止まる）。1 行の 項目 に並び（list）を渡してもよい。
    dict の行は 形・渡す・受ける を必須で持つ（既定は無い）: 欠けた形を「円」・欠けた渡す/受けるを「はい」と読むと、
    分の欄が円で書かれる・渡さない欄が給与ソフトへ渡るので止める。渡す・受けるは はい/いいえ の語だけ受ける（知らない語は止める）。"""
    out = []
    for d in rows:
        if isinstance(d, 欄):
            out.append(d)
            continue
        欠け = [k for k in ("形", "渡す", "受ける") if d.get(k) is None or str(d.get(k)).strip() == ""]
        if 欠け:
            raise ValueError(f"欄の対応: 欄「{d.get('欄')}」の行に {'・'.join(欠け)} が無い"
                             "（形＝円・日・分・回、渡す・受ける＝はい・いいえ を行ごとに書く。既定で円・はい と読まない）")
        項目たち = d["項目"] if isinstance(d["項目"], (list, tuple)) else [d["項目"]]
        for 名 in (str(x).strip() for x in 項目たち):
            if 名:
                out.append(欄(項目=名, 欄=str(d["欄"]), 形=str(d["形"]).strip(),
                             渡す=_はいかいいえ(d["渡す"], f"欄の対応: 欄「{d['欄']}」の 渡す"), 受ける=_はいかいいえ(d["受ける"], f"欄の対応: 欄「{d['欄']}」の 受ける")))
    seen: dict[str, str] = {}
    for x in out:
        if x.項目 in seen:
            raise ValueError(f"対応に同じ項目が 2 つ: {x.項目}（欄「{seen[x.項目]}」と「{x.欄}」）")
        seen[x.項目] = x.欄
    欄たち_(out)
    return tuple(out)


def 欄たち_(対応) -> tuple[欄の組, ...]:
    組: dict[str, list[欄]] = {}
    for x in 対応:
        組.setdefault(x.欄, []).append(x)
    out = []
    for 名, xs in 組.items():
        if len({(x.形, x.渡す, x.受ける) for x in xs}) > 1:
            raise ValueError(f"欄「{名}」に足す項目（{'・'.join(x.項目 for x in xs)}）の 形・渡す・受ける がそろわない")
        out.append(欄の組(欄=名, 形=xs[0].形, 渡す=xs[0].渡す, 受ける=xs[0].受ける, 項目たち=tuple(x.項目 for x in xs)))
    return tuple(out)


def 欄の組たち(欄の対応) -> tuple[欄の組, ...]:
    """欄の対応 → 欄ごとの組（欄の並びは対応に初めて出た順）。書き口・読み口・突き合わせが同じこの 1 つを使う。"""
    return 欄たち_(対応にする(欄の対応))


# ---- 欄の対応を事務所の Drive の値から組む ----
# 置き場（docs/設計/Drive の型.md §4「製品ごとの値の置き場」）:
#   2_マスタ ④支給控除の項目 の「給与ソフトの欄」（会社の行の項目・形は円・渡す／受ける）と
#   2_マスタ ⑥つなぎ の会社の行（NO 空・側＝出口・道具＝事務所が付けた給与ソフトの呼び名・その道具での名＝欄の字）。
#   その道具での番号は `欄.<項目>`（渡す・受ける）・`渡す.<項目>`（書くだけ）・`受ける.<項目>`（読んで照らすだけ）。
#   ⑥つなぎ には芯が作る項目（時間外手当・総支給額 など）と勤怠の欄（出勤日数・法定外残業 など＝形は芯/集計 の単位）を置く。
つなぎの印 = {"欄.": (True, True), "渡す.": (True, False), "受ける.": (False, True)}


def _比べる月(v, どこ: str) -> str:
    """支給月の字 → 比べる字 `YYYY.MM`（正本 芯/支給月の字.py）。空は ""（適用開始の無い行）。読めない字は止める
    （黙って「適用開始の無い行」と読んで、まだ効かない欄を出さない）。"""
    from 芯 import 支給月の字
    if v is None or not str(v).strip():
        return ""
    x = 支給月の字.そろえる(v, "比べる")
    if x is None:
        raise ValueError(f"{どこ}「{str(v).strip()}」が支給月の字として読めない（YYYY.MM支給）")
    return x


def 欄の対応を組む(会社: str, 道具: str | None = None, 支給控除の項目=(), つなぎ=(), 支給月: str | None = None) -> list[dict]:
    """事務所の Drive の値（窓が読んだ行の dict の並び）→ 欄の対応の行。窓が手で対応を組まない（どの窓も同じ物）。

    支給控除の項目: その会社の行の「給与ソフトの欄」が空でない行（適用開始が 支給月 より後の行は使わない・同じ項目は新しい行）。
    つなぎ: その会社の行（NO 空・側＝出口・道具＝<道具>）。道具を渡さなければ つなぎ は読まない。
    同じ項目が 2 つの欄に出たら止まる（対応にする）。同じ欄に幾つかの項目なら足す。"""
    from 芯.集計.形 import 出す語
    from 芯.計算.支給控除 import 芯の作る名
    単位 = {k: v for k, v in 出す語 if v in 値の形たち}
    # 円の項目: 芯/計算 の作る項目（総支給額・時間外手当 …）とその会社の ④支給控除の項目（形は円）
    円の名 = set(芯の作る名) | {str(r.get("項目", "")).strip() for r in 支給控除の項目 or ()
                            if str(r.get("会社", "")).strip() == str(会社)}
    月 = _比べる月(支給月, "支給月")
    新しい: dict[str, tuple[str, dict]] = {}
    for r in 支給控除の項目 or ():
        if str(r.get("会社", "")).strip() != str(会社) or not str(r.get("給与ソフトの欄") or "").strip():
            continue
        始め = _比べる月(r.get("適用開始"), f"支給控除の項目 {str(r.get('項目', '')).strip()} の 適用開始")
        if 月 and 始め and 始め > 月:
            continue
        名 = str(r.get("項目", "")).strip()
        if 名 not in 新しい or 始め >= 新しい[名][0]:
            新しい[名] = (始め, r)
    # 支給控除の項目は円の額・給与ソフトへ渡し、出力から受けて照らす（④の項目の意味＝形・渡す・受けるを明示で書く）
    out = [{"項目": 名, "欄": str(r["給与ソフトの欄"]).strip(), "形": "円", "渡す": True, "受ける": True}
           for 名, (_, r) in 新しい.items()]
    for t in つなぎ or () if 道具 else ():
        番 = str(t.get("その道具での番号", "") or "").strip()
        if (str(t.get("会社", "")).strip() != str(会社) or t.get("側") != "出口" or str(t.get("NO", "") or "").strip()
                or str(t.get("道具", "")).strip() != str(道具).strip()):
            continue
        印 = next((k for k in つなぎの印 if 番.startswith(k)), None)
        欄名 = str(t.get("その道具での名", "") or "").strip()
        if not 印 or not 欄名:
            continue
        名 = 番[len(印):].strip()
        渡す, 受ける = つなぎの印[印]
        if 名 in 単位:
            形の字 = 単位[名]
        elif 名 in 円の名:
            形の字 = "円"
        else:   # 前: 黙って円と読み、分の項目が分の数のまま給与ソフトへ渡った
            raise ValueError(f"⑥つなぎ の項目「{名}」の形が引けない（芯/集計 の語・芯/計算 の作る項目・その会社の ④支給控除の項目 の"
                             f"どれでもない）＝黙って円で書かない")
        out.append({"項目": 名, "欄": 欄名, "形": 形の字, "渡す": 渡す, "受ける": 受ける})
    対応にする(out)   # 同じ項目が 2 つの欄・足す欄の形がそろわない を今止める
    return out


# ---- 給与ソフトへ入れない人を事務所の Drive の値から組む ----
# 置き場（docs/設計/Drive の型.md §4「製品ごとの値の置き場」）は 1 か所:
#   2_マスタ ⑥つなぎ の人の行（NO＝その人・側＝出口・道具＝事務所が付けた給与ソフトの呼び名・その道具での番号＝`渡さない`）。
#   その人は計算し支給控除一覧には載るが、その給与ソフトの取り込み・`空の欄`・突き合わせには出さない（例 給与ソフトに載せない代表）。
渡さない印 = "渡さない"


def 渡さない人を組む(会社: str, 道具: str | None, つなぎ=()) -> tuple[str, ...]:
    """⑥つなぎ の人の行（NO 有り・側＝出口・道具＝<道具>・その道具での番号＝`渡さない`）→ その給与ソフトへ入れない人の NO の並び。
    道具が無いと止める（どの給与ソフトの行か分からない＝前は空の並びを返し、外す人が誰も外れないまま取り込みに載った）。
    窓が手で人を外さない（どの窓も同じ物）。
    印は `渡さない` の 4 字と同じ時だけ。印を含むが同じでない字（`渡さない予定` など）は止める（黙って外さない・黙って載せない）。"""
    if not str(道具 or "").strip():
        raise ValueError("渡さない人を組む: 道具（⑥つなぎ の給与ソフトの呼び名）を渡す（渡さない人はその道具の人の行から読む。"
                         "道具が無いと外す人を黙って取り込みに載せる）")
    out = []
    for t in つなぎ or ():
        no = str(t.get("NO", "") or "").strip()
        if (not no or str(t.get("会社", "")).strip() != str(会社) or t.get("側") != "出口"
                or str(t.get("道具", "")).strip() != str(道具).strip()):
            continue
        番号 = str(t.get("その道具での番号", "") or "").strip()
        if 番号 != 渡さない印 and 渡さない印 in "".join(番号.split()):
            # 「渡さない予定」「渡さないを解除」「渡 さない」など印に似た字は、外すか載せるかを黙って決めない＝止める
            raise ValueError(f"⑥つなぎ の人の行（NO={no}・道具={道具}）のその道具での番号が「{番号}」: "
                             f"給与ソフトへ入れない人は「{渡さない印}」の 4 字だけ。外すなら「{渡さない印}」に、"
                             f"入れるなら給与ソフトでの番号に直す")
        if 番号 == 渡さない印 and no not in out:
            out.append(no)
    return tuple(out)


def _はい(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip() in ("はい", "true", "True", "1", "○")


_はいの語 = ("はい", "true", "True", "1", "○")
_いいえの語 = ("いいえ", "false", "False", "0", "×")


def _はいかいいえ(v, どこ: str) -> bool:
    """はい／いいえ だけを読む（欄の対応の 渡す・受ける、給与ソフトの形の 委託も取り込む）。知らない語は止める（黙って いいえ と読まない）。"""
    if isinstance(v, bool):
        return v
    x = str(v).strip()
    if x in _はいの語:
        return True
    if x in _いいえの語:
        return False
    raise ValueError(f"{どこ}「{v}」は はい・いいえ の外（はい＝{'・'.join(_はいの語)}／いいえ＝{'・'.join(_いいえの語)}）")


@dataclass(frozen=True)
class 給与ソフトの形:
    """給与ソフトごとの取り込み・出力の file の形。欄の中身（項目）は `欄の対応` が持つ。"""
    名: str
    鍵の欄: str | None = None          # 人を引く欄（社員の番号）
    氏名の欄: str | None = None        # 書く時だけ。窓が NO→氏名 を渡した時に埋める
    後ろの欄: tuple[str, ...] = ()     # 書く時に後ろへ空で足す欄
    文字コード: str | None = None
    区切り: str = ","
    向き: str = "横"                   # 出力を読む時の向き。横＝人が行・縦＝人が列
    確かめた: bool = True              # False の所は公開の仕様で確かめていない＝窓が全部を渡すまで使えない
    渡し方: str = "CSV"                # 取り込みを CSV の file で渡すか、2_出す物 の表に書いて人が写すか（渡し方たち）
    委託も取り込む: bool | None = None  # 業務委託の人も取り込みに載せるか（事務所の給与ソフトの決まり）。None＝書いていない＝委託の人が居る月は止まる
    要る: tuple[str, ...] = field(default=("鍵の欄", "文字コード"))

    def 使える形(self, **上書き) -> "給与ソフトの形":
        f = replace(self, **上書き) if 上書き else self
        if f.渡し方 not in 渡し方たち:
            raise ValueError(f"{f.名}: 渡し方「{f.渡し方}」は {'・'.join(渡し方たち)} の外")
        # 表で渡す時は file を作らない＝文字コードは要らない（給与ソフトの出力を bytes で読む時は 読み口 が求める）
        要る = tuple(k for k in f.要る if not (f.渡し方 == "表" and k == "文字コード"))
        無い = [k for k in 要る if not getattr(f, k)]
        if 無い:
            raise ValueError(f"{f.名}: {'・'.join(無い)} が無い（事務所のルール「給与ソフトと取り込みの形」から窓が渡す）")
        if f.向き not in ("横", "縦"):
            raise ValueError(f"{f.名}: 向き「{f.向き}」は 横・縦 の外")
        return f


# 給与ソフトの形の値は持たない（⟦鍵:給与計算/パックに製品ごとの物を置かない⟧）。窓が事務所のルール.md
# 「## 1 給与ソフトと取り込みの形」から読んで 形を組む に渡す（置き場は docs/設計/Drive の型.md §4「製品ごとの値の置き場」）。
形の鍵たち = ("名", "鍵の欄", "氏名の欄", "後ろの欄", "文字コード", "区切り", "向き", "確かめた", "渡し方", "委託も取り込む")


def 形を組む(値: "dict | 給与ソフトの形") -> 給与ソフトの形:
    """窓が事務所の設定から読んだ値（dict）か組んだ 給与ソフトの形 → 使える形。名・鍵の欄・文字コード（渡し方＝CSV の時）が無ければ止まる。

    既定の形は持たない（黙って既定で書かない）。後ろの欄は 並び か 読点・カンマ区切りの字。確かめた は はい／いいえ。
    委託も取り込む は はい／いいえ（空＝書いていない＝委託の人が居る月の取り込みで止まる・`書き口.取り込み`）。
    渡し方 は CSV（空も＝前からの形）か 表（2_出す物 のスプレッドシートに書いて人が写す・文字コードは要らない）。"""
    if isinstance(値, 給与ソフトの形):
        f = 値
    else:
        d = dict(値 or {})
        知らない = [k for k in d if k not in 形の鍵たち]
        if 知らない:
            raise ValueError(f"給与ソフトの形: 「{'・'.join(知らない)}」は {'・'.join(形の鍵たち)} の外")
        名 = str(d.get("名") or "").strip()
        if not 名:
            raise ValueError("給与ソフトの形: 名 が無い（事務所のルール「給与ソフトと取り込みの形」から窓が渡す）")
        後ろ = d.get("後ろの欄") or ()
        if isinstance(後ろ, str):
            後ろ = [x for x in 後ろ.replace("、", ",").split(",")]
        kw = {"名": 名, "後ろの欄": tuple(str(x).strip() for x in 後ろ if str(x).strip())}
        for k in ("鍵の欄", "氏名の欄", "文字コード", "区切り", "向き", "渡し方"):
            v = str(d.get(k) or "").strip()
            if v:
                kw[k] = v
        if "確かめた" in d:
            kw["確かめた"] = _はい(d["確かめた"])
        if str(d.get("委託も取り込む") if d.get("委託も取り込む") is not None else "").strip():
            kw["委託も取り込む"] = _はいかいいえ(d["委託も取り込む"], "給与ソフトの形: 委託も取り込む")
        f = 給与ソフトの形(**kw)
    return f.使える形()



形の見出し = "給与ソフトと取り込みの形"


def 形をmdから読む(md: str, 会社たち=()) -> dict:
    """事務所のルール.md の「## <番号> 給与ソフトと取り込みの形」の `- <鍵>: <値>` の行 → 形を組む へ渡す dict。

    鍵は 形の鍵たち だけを読む（ほかの箇条書きは説明として読まない）。小見出し（### の前）までが事務所の共通の形で、
    「### <会社の呼び名か顧客ID>」の下の行がその会社の分だけ共通を上書きする（会社ごとに違う時・Drive の型.md §4）。
    会社たち: その会社の呼び名・顧客ID（どれか 1 つに合う小見出しを使う）。止める: 節が無い・同じ部分に同じ鍵が 2 つ・
    合う小見出しが 2 つ。名 が無いかは 形を組む が止める（ここは読むだけ・既定で埋めない）。"""
    import re
    行たち = str(md or "").splitlines()
    始め = next((i for i, x in enumerate(行たち) if re.match(rf"^##\s+(\d+\s+)?{形の見出し}\s*$", x.strip())), None)
    if 始め is None:
        raise ValueError(f"事務所のルール.md に「## {形の見出し}」の節が無い（給与ソフトの形を書く置き場・Drive の型.md §4）")
    節: list[str] = []
    for x in 行たち[始め + 1:]:
        if re.match(r"^##\s", x.strip()):
            break
        節.append(x)
    部分: list[tuple[str | None, list[str]]] = [(None, [])]
    for x in 節:
        m = re.match(r"^###\s+(.+?)\s*$", x.strip())
        if m:
            部分.append((m.group(1).strip(), []))
        else:
            部分[-1][1].append(x)
    名たち = {str(c).strip() for c in 会社たち if str(c or "").strip()}

    def 読む(見出し, xs) -> dict:
        d: dict = {}
        for x in xs:
            m = re.match(r"^\s*[-*]\s*([^:：]+?)\s*[:：]\s*(.*?)\s*$", x)
            if not m or m.group(1) not in 形の鍵たち:
                continue
            if m.group(1) in d:
                raise ValueError(f"事務所のルール.md「{形の見出し}」{'の「' + 見出し + '」' if 見出し else ''}に {m.group(1)} が 2 つ")
            d[m.group(1)] = m.group(2)
        return d

    合う = [(h, xs) for h, xs in 部分[1:] if h in 名たち]
    if len(合う) > 1:
        raise ValueError(f"事務所のルール.md「{形の見出し}」に会社の小見出しが 2 つ合う（{'・'.join(h for h, _ in 合う)}）")
    共通 = 読む(None, 部分[0][1])
    return {**共通, **(読む(*合う[0]) if 合う else {})}


# ---- 値 ↔ 字 ----

def 字にする(値: Decimal, 形: str, 時間の書き方: str | None) -> str:
    if 形 == "円":
        if 値 != 値.to_integral_value():
            raise ValueError(f"円の値に端数がある: {値}（丸めは芯の決まりの後の値で渡す）")
        return str(int(値))
    if 形 == "分":
        return 分を字に(値, 時間の書き方)
    return 数の字(値)


def 字を数に(字: str, 形: str, 時間の書き方: str | None) -> Decimal | None:
    """空なら None。円の 1,234・¥ は外す。時間は分にそろえる。"""
    s = str(字).strip().replace(",", "").replace("¥", "").replace("円", "")
    if s == "":
        return None
    if 形 == "分":
        return 字を分に(s, 時間の書き方)
    return 数にする(s)


def 数の字(v: Decimal) -> str:
    v = v.normalize()
    if v == v.to_integral_value():
        return str(int(v))
    return format(v, "f")


def 時間の書き方を読む(時間の書き方):
    """会社のマスタ `出口.時間の書き方` の字 → `時間の書き方たち` の 1 つ。項目の辞書（初期設定/項目.json）の書き方
    （`60進（h:mm）`・`10進（h.hh）`＝後ろの（…）は説明）も、空白・全角半角の揺れも同じに読む（辞書のとおりに書いて止めない）。"""
    s = "".join(unicodedata.normalize("NFKC", str(時間の書き方 or "")).split())
    if s.endswith(")") and "(" in s and s.split("(", 1)[0] in 時間の書き方たち:
        s = s.split("(", 1)[0]
    if s not in 時間の書き方たち:
        raise ValueError(f"時間の書き方「{時間の書き方}」は {'・'.join(時間の書き方たち)} の外（会社のマスタから窓が渡す）")
    return s


def 分を字に(分: Decimal, 時間の書き方: str | None) -> str:
    w = 時間の書き方を読む(時間の書き方)
    if w == "10進":
        return format((Decimal(分) / 60).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")
    if 分 != 分.to_integral_value():
        raise ValueError(f"分に端数がある: {分}（60進では書けない）")
    m = int(分)
    sign, m = ("-", -m) if m < 0 else ("", m)
    sep = "." if w == "60進" else ":"
    return f"{sign}{m // 60}{sep}{m % 60:02d}"


def 字を分に(字: str, 時間の書き方: str | None) -> Decimal:
    w = 時間の書き方を読む(時間の書き方)
    s = 字.strip()
    if w == "10進":
        return 数にする(s) * 60
    sign = -1 if s.startswith("-") else 1
    s = s.lstrip("-")
    for sep in (":", "."):
        if sep in s:
            h, m = s.split(sep, 1)
            if len(m) != 2 or not (h.isdigit() and m.isdigit()) or int(m) >= 60:
                raise ValueError(f"時間の字が {w} の形でない: {字!r}")
            return Decimal(sign * (int(h) * 60 + int(m)))
    if s.isdigit():
        return Decimal(sign * int(s) * 60)
    raise ValueError(f"時間の字が {w} の形でない: {字!r}")
