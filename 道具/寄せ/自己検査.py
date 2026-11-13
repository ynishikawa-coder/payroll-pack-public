# -*- coding: utf-8 -*-
"""道具の自分の検査 4 つ（docs/設計/寄せる道具.md §5.2）。会社の値は使わない。雛形（型から起こした空のシート）だけを使う。

1. 直しの一致: 前の版の雛形に足した直しを当てると、今の版の雛形と同じになる。直しの無い型の直しはここで赤。
   直し 1（前の版 0）は前の版の型が無いので、直しが書く今の名（タブ・列・md の見出し）が全部型に在るかを見る。
2. 二度当て: 当てた後へもう一度当てても変わらない。
3. 値の保ち: 雛形に作り物の値を置いて当て、前の値が全部どこかへ移るか、寄せられない物・捨てた数に出る。
4. 型に移行の物が無い: 型に別名・要る日・読み替え・移した印・旧の語などの欄が 0。
どれも誤りの文の一覧を返す（空なら緑）。
"""
import copy
import datetime as dt

import 当てる
import 直し as 直しの形

今日 = dt.date(2000, 1, 1)  # 雛形の検査は日を見ない（写しの名にだけ入る）


def 雛形(型: dict, 版: int | None = None) -> dict:
    K = 当てる.型を読む(型)
    シート = {f.replace("<支給年>", "2000"): {t: [[c["名"] for c in cols]] for t, cols in tabs.items()} for f, tabs in K["ファイル"].items()}
    md = {m: "\n\n".join(heads) + "\n" for m, heads in K["md"].items()}
    置き場 = sorted({p for f in list(シート) + list(md) for p in [f] + [f.rsplit("/", 1)[0] + "/"] * ("/" in f)})
    return {"会社": "雛形", "型の版": K["版"] if 版 is None else 版, "選んだ部品": [], "シート": シート, "md": md, "置き場": 置き場}


def 形だけ(d: dict) -> dict:
    return {"シート": d["シート"], "md": d["md"]}


def 一致(型: dict, 直したち: list[dict], 前の型: dict | None = None) -> list[str]:
    K = 当てる.型を読む(型)
    誤り = []
    最後 = 直したち[-1]["版"] if 直したち else 0
    if 最後 != K["版"]:
        return [f"型の版 {K['版']} に直しが無い（直しの最後は版 {最後}）＝型・雛形・直しは同じ PR で出す"]
    if not 直したち:
        return []
    d = 直したち[-1]
    if 前の型 is not None:
        r = 当てる.見通す(雛形(前の型), 型, 直したち, 今日)
        if r["寄せられない物"]:
            誤り += [f"直し {d['版']}: 前の版の雛形で寄せられない物 {x['鍵']}（{x['中身']}）" for x in r["寄せられない物"]]
        elif 形だけ(r["寄せた後の値"]) != 形だけ(雛形(型)):
            誤り.append(f"直し {d['版']}: 前の版の雛形に当てた結果が今の版の雛形と違う")
    else:
        誤り += 名が型に在る(d, K)
    return 誤り


def 名が型に在る(d: dict, K: dict) -> list[str]:
    誤り = []
    def タブ(f, t):
        tk = 当てる.型のファイル(K, f.replace("<支給年>", "2000"))
        return None if tk is None else tk.get(t)
    for n, op in enumerate(d["操作"], 1):
        する, 所 = op["する"], f"直し {d['版']} 操作 {n}「{op['する']}」"
        if する in ("タブを足す",) and タブ(op["ファイル"], op["タブ"]) is None:
            誤り.append(f"{所}: 型に無いタブ {op['ファイル']}/{op['タブ']}")
        if する == "タブの名を変える" and タブ(op["ファイル"], op["後"]) is None:
            誤り.append(f"{所}: 型に無いタブ {op['ファイル']}/{op['後']}")
        if する in ("列を足す", "列の名を変える"):
            cols = タブ(op["ファイル"], op["タブ"])
            want = op.get("見出し", op.get("後"))
            if cols is not None and want not in [c["名"] for c in cols]:
                誤り.append(f"{所}: 型に無い列 {op['ファイル']}/{op['タブ']}/{want}")
        if する == "列を畳む" and isinstance(op["先"], dict):
            cols = タブ(op["先"].get("ファイル", op["ファイル"]), op["先"]["タブ"])
            names = [c["名"] for c in cols] if cols is not None else []
            無い = [c for c in [*op["先"]["鍵"], *op["先"].get("足す行", {}), op["先"]["列"]] if c not in names]
            if 無い:
                誤り.append(f"{所}: 畳む先に無い列 {op['先']['タブ']}/{無い}")
        if する in ("列を md の見出しへ移す", "md の見出しを足す", "md の見出しの名を変える"):
            heads = K["md"].get(op["md"])
            h = op.get("見出し", op.get("後"))
            if heads is not None and 当てる.見出しの行("\n".join(heads), h)[0] is None:
                誤り.append(f"{所}: 型の md に無い見出し {op['md']}#{h}")
    return 誤り


def 二度当て(型: dict, 直したち: list[dict], 前の型: dict | None = None) -> list[str]:
    始め = 雛形(前の型) if 前の型 is not None else 雛形(型, 版=直したち[0]["版"] - 1 if 直したち else 0)
    一 = 当てる.見通す(始め, 型, 直したち, 今日)
    二入 = copy.deepcopy(一["寄せた後の値"])
    二入["型の版"] = 始め["型の版"]
    二 = 当てる.見通す(二入, 型, 直したち, 今日)
    誤り = []
    if 形だけ(一["寄せた後の値"]) != 形だけ(二["寄せた後の値"]):
        誤り.append("二度当てで値が変わった")
    if 二["書く手順"]:
        誤り.append(f"二度目にも書く手順が出た（{len(二['書く手順'])} 個）")
    return 誤り


def 値の保ち(型: dict, 直したち: list[dict], 前の型: dict | None = None) -> list[str]:
    始め = 雛形(前の型) if 前の型 is not None else 雛形(型, 版=直したち[0]["版"] - 1 if 直したち else 0)
    n = 0
    for tabs in 始め["シート"].values():
        for t, rows in tabs.items():
            vals = []
            for _ in rows[0]:
                n += 1
                vals.append(f"作り物{n:04d}")
            rows.append(vals)
    try:
        r = 当てる.見通す(始め, 型, 直したち, 今日)
    except 当てる.保ちの誤り as e:
        return [str(e)]
    後 = r["寄せた後の値"]
    在る = {v for tabs in 後["シート"].values() for rows in tabs.values() for row in rows for v in row}
    本文 = "\n".join(後["md"].values())
    無い = [f"作り物{k:04d}" for k in range(1, n + 1) if f"作り物{k:04d}" not in 在る and f"作り物{k:04d}" not in 本文]
    保 = r["値の保ち"]
    if len(無い) > 保["捨てた"] + 保["内訳"]["重ねた"]:
        return [f"値が {len(無い)} 個消えた（捨てた {保['捨てた']}・重ねた {保['内訳']['重ねた']}）: {無い[:5]}"]
    return []


移行の鍵 = {"別名", "要る日", "読み替え", "名の読み替え", "答えの読み替え", "移した印", "前の印", "旧", "旧の語", "旧の形", "畳んだ列", "前の名", "旧の列の行き先"}


def 移行の物(型: dict) -> list[str]:
    out = []
    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in 移行の鍵 or any(w in str(k) for w in ("読み替え", "移した印", "要る日")):
                    out.append(f"型に移行の物「{k}」（{p or '/'}）＝直しへ写して型から外す")
                walk(v, f"{p}/{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]")
    walk(型, "")
    return out


def 全部(型: dict, 直したち: list[dict] | None = None, 前の型: dict | None = None) -> dict:
    直したち = 直しの形.読む() if 直したち is None else 直したち
    結果 = {"1 直しの一致": 一致(型, 直したち, 前の型), "4 型に移行の物が無い": 移行の物(型)}
    if not 結果["1 直しの一致"]:
        結果["2 二度当て"] = 二度当て(型, 直したち, 前の型)
        結果["3 値の保ち"] = 値の保ち(型, 直したち, 前の型)
    else:
        結果["2 二度当て"] = 結果["3 値の保ち"] = ["1 が赤なので見ていない"]
    return 結果
