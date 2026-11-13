"""状況の正本（00_事務所/管理表）の書く口と、事務所の段の道具。Drive を開かない。

殻が今のタブの値（get_values の 2 次元の配列・1 行目が見出し）を渡し、この口が「書く手順」を返す。殻は手順を順に当てるだけ。

  python3 管理表/管理表.py 書く     < 入力.json   # 窓の口: 受け持つ組の行だけを鍵で探して書く
  python3 管理表/管理表.py 月の行   < 入力.json   # 事務所の段: 会社×支給月の行を起こす
  python3 管理表/管理表.py 会社の行 < 入力.json   # 事務所の段: 会社の行を起こす
  python3 管理表/管理表.py 目次の式 < 入力.json   # 00_目次 の「月の状況」へ引く式

入力の形は 管理表/README.md。
"""
import json
import re
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent


class 拒む(Exception):
    """書く口が書かない時（他の組の行・見出しの違い・選べない値・行を起こす権の無い窓）。"""


def 型() -> dict:
    return json.loads((ここ / "型.json").read_text(encoding="utf-8"))


def タブ(名: str) -> dict:
    for t in 型()["タブ"]:
        if t["タブ"] == 名:
            return t
    raise 拒む(f"型に無いタブ: {名}")


def 見出し(名: str) -> list[str]:
    return [c["名"] for c in タブ(名)["列"]]


def 全部の見出し() -> dict[str, list[str]]:
    return {t["タブ"]: [c["名"] for c in t["列"]] for t in 型()["タブ"]}


def 列の字(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _見出しを照らす(名: str, 値: list[list]) -> None:
    今 = [str(c) for c in (値[0] if 値 else [])]
    if 今 != 見出し(名):
        raise 拒む(f"{名}: 見出しが型と違う（寄せる道具で型へそろえてから書く）")


def _値を照らす(名: str, 行: dict) -> None:
    for k, v in 行.items():
        if str(v).startswith(("=", "+", "@")):
            raise 拒む(f"{名}.{k}: 式か式に読める字は書かない {v!r}")
    for c in タブ(名)["列"]:
        if c["名"] not in 行:
            continue
        v = 行[c["名"]]
        if "選べる値" in c and v not in c["選べる値"]:
            raise 拒む(f"{名}.{c['名']}: 選べない値 {v!r}")
        if c.get("形") == "数" and v != "" and not re.fullmatch(r"\d+", str(v)):
            raise 拒む(f"{名}.{c['名']}: 数でない {v!r}")
        if c.get("形") == "日付" and v != "" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
            raise 拒む(f"{名}.{c['名']}: YYYY-MM-DD でない {v!r}")
    if 名 == "月の状況" and str(行.get("外した人", "0") or "0") != "0":
        for c in ("取り込み", "納品"):
            if 行.get(c) == "済":
                raise 拒む(f"月の状況.{c}: 外した人が 0 でないので 済 にしない")


def _行の辞書(名: str, 値: list[list]) -> list[dict]:
    h = 見出し(名)
    return [{k: (r[i] if i < len(r) else "") for i, k in enumerate(h)} for r in 値[1:]]


def _探す(名: str, 行たち: list[dict], 鍵の値: dict) -> int | None:
    当たり = [i for i, r in enumerate(行たち) if all(str(r[k]) == str(鍵の値[k]) for k in タブ(名)["鍵"])]
    if len(当たり) > 1:
        raise 拒む(f"{名}: 鍵 {鍵の値} の行が 2 つある")
    return 当たり[0] if 当たり else None


def 書く(入力: dict) -> list[dict]:
    """窓の書く口。入力: タブ・今の値・会社の一覧（会社→組）・受け持つ組・行たち・今日。

    受け持つ組の会社の行だけを鍵で探して書く。月の状況・会社の行は起こさない（事務所の段）。
    確認ページの行は無ければ足す。行を消さない。見出し・他の組の行・他のタブには書かない。"""
    名, 値 = 入力["タブ"], 入力["今の値"]
    _見出しを照らす(名, 値)
    組の = 入力["会社の一覧"]
    受け持つ = 入力["受け持つ組"]
    h = 見出し(名)
    今の行 = _行の辞書(名, 値)
    手順 = []
    for 行 in 入力["行たち"]:
        会社 = 行.get("会社")
        if 組の.get(会社) != 受け持つ and not (名 == "確認ページ" and 会社 == 受け持つ):
            raise 拒む(f"{名}: 会社 {会社} は受け持つ組 {受け持つ} の会社でない")
        if 名 == "月の状況" and "更新日" not in 行 and 入力.get("今日"):
            行 = {**行, "更新日": 入力["今日"]}
        外 = set(行) - set(h)
        if 外:
            raise 拒む(f"{名}: 型に無い列 {sorted(外)}")
        欠け = [k for k in タブ(名)["鍵"] if str(行.get(k, "")) == ""]
        if 欠け:
            raise 拒む(f"{名}: 鍵の列 {欠け} が無い")
        i = _探す(名, 今の行, 行)
        if i is not None and "組" in h and 今の行[i]["組"] != 受け持つ:
            raise 拒む(f"{名}: 行の組が {今の行[i]['組']!r}（受け持つ組でない）")
        if "組" in 行 and (i is None or str(行["組"]) != str(今の行[i]["組"])):
            raise 拒む(f"{名}: 組は窓から書かない（書くのは事務所の段）")
        if i is None:
            if タブ(名)["起こすのは"] != "窓":
                raise 拒む(f"{名}: 鍵 {[行.get(k) for k in タブ(名)['鍵']]} の行が無い（行を起こすのは事務所の段）")
            新 = {k: 行.get(k, "") for k in h}
            _値を照らす(名, 新)
            手順.append({"する": "行を足す", "タブ": 名, "値": [新[k] for k in h]})
            今の行.append(新)
            continue
        _値を照らす(名, {**今の行[i], **行})
        for k, v in 行.items():
            if k in タブ(名)["鍵"] or str(今の行[i][k]) == str(v):
                continue
            手順.append({"する": "値を書く", "タブ": 名, "セル": f"{列の字(h.index(k))}{i + 2}", "列": k, "前": 今の行[i][k], "値": v})
            今の行[i][k] = v
    return 手順


def 月の行(入力: dict) -> list[dict]:
    """事務所の段。会社の一覧（会社・組・状態）の 止めた 以外の会社について、支給月の行が無ければ足す。"""
    名 = "月の状況"
    _見出しを照らす(名, 入力["今の値"])
    今の行 = _行の辞書(名, 入力["今の値"])
    h = 見出し(名)
    手順 = []
    for c in 入力["会社の一覧"]:
        if c.get("状態") == "止めた":
            continue
        鍵 = {"会社": c["会社"], "支給月": 入力["支給月"]}
        if _探す(名, 今の行, 鍵) is None:
            新 = {**{k: "" for k in h}, **鍵, "組": c["組"], "外した人": "0", "更新日": 入力.get("今日", "")}
            手順.append({"する": "行を足す", "タブ": 名, "値": [新[k] for k in h]})
            今の行.append(新)
    return 手順


def 会社の行(入力: dict) -> list[dict]:
    """事務所の段。会社の行が無ければ足す（型の版は渡された値・無ければ 0）。"""
    名 = "会社"
    _見出しを照らす(名, 入力["今の値"])
    今の行 = _行の辞書(名, 入力["今の値"])
    h = 見出し(名)
    手順 = []
    for c in 入力["会社の一覧"]:
        if _探す(名, 今の行, c) is None:
            新 = {**{k: "" for k in h}, "会社": c["会社"], "組": c["組"], "型の版": str(c.get("型の版", 0)), "選んだ部品": c.get("選んだ部品", "")}
            手順.append({"する": "行を足す", "タブ": 名, "値": [新[k] for k in h]})
            今の行.append(新)
    return 手順


def 目次の式(入力: dict) -> str:
    """00_目次 の「月の状況」の左上に置く式。管理表「月の状況」から組の行だけを引く（見るだけ）。管理表の ID は殻が置き場から渡す。"""
    h = 見出し("月の状況")
    終わり = 列の字(len(h) - 1)
    組の列 = h.index("組") + 1
    組 = str(入力["組"]).replace("'", "''")
    return (f'=QUERY(IMPORTRANGE("{入力["管理表のID"]}","月の状況!A:{終わり}"),'
            f'"select * where Col{組の列} = \'{組}\' order by Col{h.index("支給月") + 1} desc",1)')


if __name__ == "__main__":
    何 = sys.argv[1]
    入力 = json.load(sys.stdin)
    try:
        out = {"書く": 書く, "月の行": 月の行, "会社の行": 会社の行, "目次の式": 目次の式}[何](入力)
    except 拒む as e:
        json.dump({"拒む": str(e)}, sys.stdout, ensure_ascii=False)
        print()
        sys.exit(2)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
