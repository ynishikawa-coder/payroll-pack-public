"""法の表の改定の前に版を出すための見張り（docs/設計/法の表.md §3.4）。

各表の頭の `次の改定` から改定の日を出し、次の物を挙げる（種類の正本は 挙げた.種類）。
- 近い: 今日から N 日以内に次の改定の日が来るのに、その日からの `出た` 行が無い表（鍵ごと）
- 過ぎた: 一番近い過ぎた改定の日からの `出た` 行が無い表（鍵ごと）
- 欄: `次の改定` の欄が無い・形が違う表・`日` の並びの最後の日を過ぎた表（次の日を書き足すまで挙げ続ける）

「その日からの行」＝その鍵に当たる（行の鍵の全部が合う）行で、状態が `出た`、効く始めが改定の日以後（表の基準の粒で比べる）、かつ次の改定の日より前の行。
効く終わりが null の前の行は改定の日も覆うが、それは「前の値のまま」なので数えない。

`次の改定` の形（どれか 1 つ）:
  {"毎年": "MM-DD", "から": 年（任意）, "おき": 年（任意・既定 1）, "鍵": {…}（任意）, "例年": "…"}
  {"日": ["YYYY-MM-DD", …], "鍵": {…}（任意）, "例年": "…"}
  {"無し": "決まった月が無い訳"}
`鍵` があれば、その鍵の値を持つ行の組だけを見る。

日付に頼るので CI の試験（scripts/check_all.sh）からは回さない（日が進むと不意に赤になって他の PR を止めるため）。
回すのは人か窓が版を出す前（docs/版の出し方.md）。試験は決まった日付を渡して照らす（tests/法の表/test_見張り.py）。

  python3 道具/法の表の見張り.py   # 引数は受けない（日＝今日〔日本時間〕・日数＝`既定の日数`・置き場＝repo の 法の表/ は口が決める）
`無し` の表は毎回 `見張りの外:` の行に訳ごと出す（訳 1 つで黙って見張りから外れた表を残さない）。
終わりの値: 挙げた物が無ければ 0・あれば 1・見張りそのものが壊れた（読めない表・使い方の誤りなど）時は 2（1 と混ぜない）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
if str(根) not in sys.path:
    sys.path.insert(0, str(根))
from 芯.計算 import 引く口  # noqa: E402  表の読み方は引く口の 1 つ（写さない）

既定の日数 = 90
_形の鍵 = {"毎年", "から", "おき", "日", "鍵", "例年", "無し"}


@dataclass(frozen=True)
class 挙げた:
    種類: str  # 近い | 過ぎた | 欄
    表の名: str
    改定の日: str | None
    鍵: dict
    訳: str

    def 行(self) -> str:
        鍵の字 = "・".join(f"{k}={v}" for k, v in self.鍵.items())
        頭 = {"近い": "近い", "過ぎた": "過ぎた", "欄": "欄の誤り"}[self.種類]
        日 = f" {self.改定の日}" if self.改定の日 else ""
        return f"{頭}: 法の表「{self.表の名}」{日}{' ' + 鍵の字 if 鍵の字 else ''}: {self.訳}"


class 欄の誤り(ValueError):
    pass


def _日(s: str) -> date:
    return date.fromisoformat(s)


def 改定の日たち(欄: dict, まで: date) -> list[date]:
    """`次の改定` の欄から、まで（含む）の年の 1 年先までの改定の日を古い順に。無し は []。"""
    if not isinstance(欄, dict) or not 欄:
        raise 欄の誤り("`次の改定` の欄が無い")
    余り = set(欄) - _形の鍵
    if 余り:
        raise 欄の誤り(f"`次の改定` に知らない鍵: {'・'.join(sorted(余り))}")
    形 = [k for k in ("毎年", "日", "無し") if k in 欄]
    if len(形) != 1:
        raise 欄の誤り("`次の改定` は 毎年・日・無し のどれか 1 つを持つ")
    if 形 == ["無し"]:
        if not str(欄["無し"]).strip():
            raise 欄の誤り("`次の改定.無し` に訳が無い")
        return []
    if 形 == ["日"]:
        日たち = 欄["日"]
        if not isinstance(日たち, list) or not 日たち:
            raise 欄の誤り("`次の改定.日` は日の並び")
        try:
            return sorted(_日(d) for d in 日たち)
        except (TypeError, ValueError) as e:
            raise 欄の誤り(f"`次の改定.日` の日が読めない: {e}") from None
    m = re.fullmatch(r"(\d\d)-(\d\d)", str(欄["毎年"]))
    if not m:
        raise 欄の誤り("`次の改定.毎年` は MM-DD")
    から, おき = 欄.get("から", 2000), 欄.get("おき", 1)
    if not (isinstance(から, int) and isinstance(おき, int) and おき >= 1):
        raise 欄の誤り("`次の改定.から`・`おき` は整数（おき は 1 以上）")
    try:
        return [date(y, int(m[1]), int(m[2])) for y in range(から, まで.year + 2, おき)]
    except ValueError as e:
        raise 欄の誤り(f"`次の改定.毎年` の日が無い日: {e}") from None


def _粒(基準: str, d: date) -> str:
    """改定の日を表の基準の粒の字に（月分 YYYY-MM・年分 YYYY・ほか YYYY-MM-DD）。"""
    s = d.isoformat()
    return s[:7] if 基準 == "月分" else s[:4] if 基準 == "年分" else s


def _鍵の字(鍵) -> str:
    return json.dumps(鍵 or {}, ensure_ascii=False, sort_keys=True)


def _覆う(表: dict, 鍵: dict, 始め: str, 次: str | None) -> bool:
    for r in 表["行"]:
        if any(鍵.get(a) != b for a, b in (r.get("鍵") or {}).items()) or r.get("状態") != "出た":
            continue  # 行の鍵の全部が合う行（空の鍵 {} はどの鍵にも当たる＝引く口と同じ読み）
        s = r.get("効く始め")
        if s is None:
            continue
        s = s[: len(始め)]
        if s >= 始め and (次 is None or s < 次):
            return True
    return False


def 見る_表(表: dict, 今日: date, 日数: int) -> list[挙げた]:
    名 = 表.get("表の名", "?")
    try:
        日たち = 改定の日たち(表.get("次の改定"), 今日 + timedelta(days=日数))
    except 欄の誤り as e:
        return [挙げた("欄", 名, None, {}, str(e))]
    if not 日たち:
        return []
    out = []
    if "日" in 表["次の改定"] and 日たち[-1] <= 今日:
        # 決まった日を使い切った表を黙って見張りの外にしない（改定が来ても終わり null の前の行が覆って気づかない）。
        # 最後の改定の日の照らし（過ぎた）も続けて行う
        out.append(挙げた("欄", 名, None, {}, f"`次の改定.日` の最後 {日たち[-1]} を過ぎた＝次の改定の日を書き足す"
                           "（決まった月が無いなら `無し` と訳）"))
    基準 = 表["基準"]
    絞る = (表.get("次の改定") or {}).get("鍵") or {}
    鍵たち = {}
    for r in 表["行"]:
        k = r.get("鍵") or {}
        if all(k.get(a) == b for a, b in 絞る.items()) and (k or not 表.get("引く鍵")):
            鍵たち.setdefault(_鍵の字(k), k)  # 引く鍵のある表の空の鍵 {} の行は鍵の組に数えない（全部の鍵に当たる行）
    if not 鍵たち and not 絞る:
        鍵たち = {_鍵の字({}): {}}  # 鍵ごとの行が無い表は表の全体を 1 つの組として見る
    if not 鍵たち:
        return [挙げた("欄", 名, None, 絞る, "`次の改定.鍵` に当たる行が無い")]

    過ぎた = [d for d in 日たち if d <= 今日]
    来る = [d for d in 日たち if 今日 < d <= 今日 + timedelta(days=日数)]
    for 種類, d in (("過ぎた", 過ぎた[-1] if 過ぎた else None), ("近い", 来る[0] if 来る else None)):
        if d is None:
            continue
        後 = [x for x in 日たち if x > d]
        始め, 次 = _粒(基準, d), (_粒(基準, 後[0]) if 後 else None)
        欠け = [k for k in 鍵たち.values() if not _覆う(表, k, 始め, 次)]
        if not 欠け:
            continue
        訳 = ("改定の日を過ぎたのに、その日からの「出た」行が無い" if 種類 == "過ぎた"
              else f"{(d - 今日).days} 日後に改定が来るのに、その日からの「出た」行が無い")
        例年 = (表.get("次の改定") or {}).get("例年")
        訳 += f"（例年: {例年}）" if 例年 else ""
        if len(欠け) == len(鍵たち) > 1:
            out.append(挙げた(種類, 名, 始め, {}, f"鍵 {len(欠け)} 個の全部で・{訳}"))  # 全部の鍵なら 1 行にまとめる
        else:
            out += [挙げた(種類, 名, 始め, k, 訳) for k in 欠け]
    return out


def 見る(今日: date, 日数: int = 既定の日数, 置き場=None) -> list[挙げた]:
    置き場 = Path(置き場 or 引く口.既定の置き場)
    out = []
    for p in sorted(置き場.glob("*.json")):
        表 = 引く口.表(p.stem, 置き場)
        out += 見る_表(表, 今日, 日数)
    return out


def 外した表(置き場=None) -> list[str]:
    """`次の改定` が `無し`（見張りの外）の表の名と訳の行。呼び口は毎回これを出す（訳 1 つで黙って外れた表を残さない）。"""
    置き場 = Path(置き場 or 引く口.既定の置き場)
    out = []
    for p in sorted(置き場.glob("*.json")):
        欄 = 引く口.表(p.stem, 置き場).get("次の改定")
        if isinstance(欄, dict) and set(欄) == {"無し"}:
            out.append(f"見張りの外: 法の表「{p.stem}」: {欄['無し']}")
    return out


def _今日() -> date:
    from datetime import datetime, timezone
    return datetime.now(timezone(timedelta(hours=9))).date()


def main(argv=None, *, 今日: date | None = None, 置き場=None) -> int:
    """呼び口。見る日は時計（日本時間）・日数は既定・置き場は repo の 法の表/ に決める＝呼ぶ人の申告で見張りをずらさない
    （前は --日・--日数・--置き場 を受け、日をずらす・0 日にする・空の置き場を指すだけで「無し」で通った）。
    今日・置き場 は試験が関数で渡すだけ（呼び口の引数にしない）。"""
    argparse.ArgumentParser(description="法の表の改定の前に版を出す見張り（引数は受けない＝日・日数・置き場は口が決める）").parse_args(argv)
    今日 = 今日 or _今日()
    挙げ = 見る(今日, 既定の日数, 置き場)
    for x in 挙げ:
        print(x.行())
    for x in 外した表(置き場):
        print(x)
    print(f"{'知らせ' if 挙げ else '無し'}: {今日} から {既定の日数} 日の見張り・挙げた {len(挙げ)} 件")
    return 1 if 挙げ else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 道具そのものが壊れた＝終わりの値 2（1 の「見つかった・赤」と混ぜない）
        import traceback
        traceback.print_exc()
        print(f"✗ 道具が壊れた（法の表の見張り・終わりの値 2＝結果ではない）: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
