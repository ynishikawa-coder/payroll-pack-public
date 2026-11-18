"""状況の正本（00_事務所/管理表）の書く口と、事務所の段の道具。Drive を開かない。

殻が今のタブの値（get_values の 2 次元の配列・1 行目が見出し）を渡し、この口が「書く手順」を返す。殻は手順を順に当てるだけ。

  python3 管理表/管理表.py 書く     < 入力.json   # 窓の口: 受け持つ組の行だけを鍵で探して書く
  python3 管理表/管理表.py 月の行   < 入力.json   # 事務所の段: 会社×支給月の行を起こす
  python3 管理表/管理表.py 会社の行 < 入力.json   # 事務所の段: 会社の行を起こす
  python3 管理表/管理表.py 型の版   < 入力.json   # 会社の「型の版」を読む（寄せる道具の入力の 型の版 へ）
  python3 管理表/管理表.py 立ち上げ < 入力.json   # 事務所の段: 管理表に型のタブ（見出しまで）を足す

入力の形は 管理表/README.md。
"""
import json
import re
import sys
from pathlib import Path

ここ = Path(__file__).resolve().parent


# 書く手順の 書き方: 値は字のまま書く（Sheets の valueInputOption=RAW）＝数だけの字・日付の字を数や日付に読ませない
字のまま = "RAW"


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


def _見出しの違い(名: str, 今: list) -> str:
    型の = 見出し(名)
    無い = [c for c in 型の if c not in 今]
    外 = [c for c in 今 if c not in 型の]
    違い = [f"型に在って無い列 {無い}" if 無い else "", f"型に無い列 {外}" if 外 else "",
          "列の並びが型と違う" if not 無い and not 外 else ""]
    return "・".join(x for x in 違い if x)


def _見出しを照らす(名: str, 値: list[list]) -> None:
    今 = [str(c) for c in (値[0] if 値 else [])]
    if 今 != 見出し(名):
        raise 拒む(f"{名}: 見出しが型と違う（{_見出しの違い(名, 今)}）。事務所の管理表を管理表の型にそろえてから書く"
                 "（タブ「{名}」が無い管理表は `立ち上げ` が足す手順を返す）".replace("{名}", 名))


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
            手順.append({"する": "行を足す", "タブ": 名, "値": [新[k] for k in h], "書き方": 字のまま})
            今の行.append(新)
            continue
        _値を照らす(名, {**今の行[i], **行})
        for k, v in 行.items():
            if k in タブ(名)["鍵"] or str(今の行[i][k]) == str(v):
                continue
            手順.append({"する": "値を書く", "タブ": 名, "セル": f"{列の字(h.index(k))}{i + 2}", "列": k, "前": 今の行[i][k], "値": v,
                         "書き方": 字のまま})
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
            手順.append({"する": "行を足す", "タブ": 名, "値": [新[k] for k in h], "書き方": 字のまま})
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
            手順.append({"する": "行を足す", "タブ": 名, "値": [新[k] for k in h], "書き方": 字のまま})
            今の行.append(新)
    return 手順


def 型の版(入力: dict) -> dict:
    """会社のタブの「型の版」を読む口（寄せる道具の入力 `型の版` へ渡す）。入力: 今の値（会社のタブ）・会社たち（無ければ全社）。

    書く口（`書く`）と同じタブ・同じ見出しの照らしで読む＝読む側と書く側の型が 1 つ。行の無い会社は拒む（黙って 0 にしない）。
    空の版は 0（版の無い会社＝寄せる道具.md §1.3）として返し、`版が空` に名を出す。寄せる道具は版に頼らず形からも前の形を
    見つける（直しは前の形を確かめて当てる）ので、空や古い記録でも前の形を黙って通さない。"""
    名 = "会社"
    _見出しを照らす(名, 入力["今の値"])
    今の行 = _行の辞書(名, 入力["今の値"])
    会社たち = 入力.get("会社たち") or [r["会社"] for r in 今の行]
    版, 空 = {}, []
    for c in 会社たち:
        i = _探す(名, 今の行, {"会社": c})
        if i is None:
            raise 拒む(f"{名}: 会社 {c} の行が無い（行を起こすのは事務所の段の 会社の行）")
        v = str(今の行[i]["型の版"]).strip()
        if v and not re.fullmatch(r"\d+", v):
            raise 拒む(f"{名}.型の版: 数でない {v!r}（会社 {c}）")
        版[c] = int(v) if v else 0
        if not v:
            空.append(c)
    return {"型の版": 版, "版が空": 空}


def 立ち上げ(入力: dict) -> list[dict]:
    """事務所の段。管理表（00_事務所/管理表）に型のタブを足す手順。入力: 今のタブ＝{タブの名: 今の値（get_values）}（管理表の全部のタブ）。

    型のタブが無ければ見出しまで 1 手で足す（`タブを足す`）。在って見出しが型と同じなら何もしない。在って見出しが違う時は
    書き換えず拒む（前の管理表の値は事務所の物＝列の移し方は事務所が決める・違いを並べる）。型に無いタブ（前の管理表の 全社_会社 など）は
    触らない＝型のタブとは別の物（書く口・型の版を読む口は型のタブの名だけを読む）。何度当てても同じ。"""
    今 = 入力.get("今のタブ") or {}
    手順, 違う = [], []
    for 名, h in 全部の見出し().items():
        if 名 not in 今:
            手順.append({"する": "タブを足す", "タブ": 名, "見出し": list(h), "書き方": 字のまま})
            continue
        値 = 今[名] or []
        見 = [str(c) for c in (値[0] if 値 else [])]
        if not 見 and len(値) <= 1:
            手順.append({"する": "行を足す", "タブ": 名, "値": list(h), "書き方": 字のまま})   # 空のタブに見出しを置く
        elif 見 != h:
            違う.append(f"{名}（{_見出しの違い(名, 見)}）")
    if 違う:
        raise 拒む(f"見出しが型と違うタブ: {'・'.join(違う)}。前の値の移し方は事務所が決める（このタブは書き換えない）")
    return 手順


if __name__ == "__main__":
    何 = sys.argv[1]
    入力 = json.load(sys.stdin)
    try:
        out = {"書く": 書く, "月の行": 月の行, "会社の行": 会社の行, "型の版": 型の版,
               "立ち上げ": 立ち上げ}[何](入力)
    except 拒む as e:
        json.dump({"拒む": str(e)}, sys.stdout, ensure_ascii=False)
        print()
        sys.exit(2)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
