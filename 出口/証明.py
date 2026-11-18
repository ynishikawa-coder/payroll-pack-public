"""出口の証明（形「給与の証明/4」）: 出口が作った表に付ける証明と、それを照らす口。

なぜ在るか（根治・2026-11-17）: 出口の外で値を差し替えた表が、殻の手で先方へ出せた。殻の出荷の口は、出口が作り
この証明を付けた表だけを通す（殻の `agents/kyuyo/bin/ship_gate.py`）。証明は `月次.月を回す` と `月次.賞与を回す` だけが付ける
（`出口.書き口` の 出す物 と、計算の前の 例の確かめ・関所 の結果を 1 つに結ぶ。月と賞与は同じ口・同じ形・同じ照らし）。

証明の形（dict・JSON にそのまま書ける）:
  形: "給与の証明/4"
  会社・支給月（出す名と同じ字＝`出口/名と版.py` の `出す支給月`: 月 `YYYY-MM`・賞与 `YYYY-MM-賞与`。
    `/3` までは `YYYY.MM支給` を書き、名の字と合わなかった）・回（月／賞与）・物（取り込み／賞与の取り込み／支給控除一覧／
    有給休暇管理表）・名（出す名の名。`<物>_<会社>_<支給月>_v<n>` で、証明の 物・会社・支給月 と同じ字＝`出口/名と版.py` の `出す名か`）
  表の指紋: 出す物の表の指紋（下の `表の指紋`。殻は同じ式で数え直す＝1 字でも差し替えた表は別の指紋）
  パックの版: 作った時のパックの版（`パックの版()`。版の印の無い中身で作った証明は `+未リリース` が付き、殻の名簿の版と合わない）
  関所: {通った: 出す物が `関所を通った` から作られた, 外した人: 外した人の数}
  例の照らし: {通った, 数, 合わない: 合わない例の数}（`月次/例の確かめ.py` の結果）
  入力の指紋: 計算の元の指紋 {名: 指紋}（下の `入力の指紋`）。計算が読む材料の全部（`入力の名` の回ごと。月は マスタ・確定した勤怠・
    前の確定した勤怠・その月だけの指示・人ごとの月の数字・月の数字・有給の値・法の線・給与のルール（MD の例）、賞与は マスタ・
    その月だけの指示・人ごとの月の数字・支給一覧・賞与の引数・法の線・給与のルール）。証明を作った後に元が 1 字でも変わったら
    （直して計算し直さずに）出せない。計算が読む材料と結ぶ材料が同じかは `月次.引数の扱い` と試験が照らす。

照らす(出す物, 証明の物=None, *, 入力) -> {"通す": bool, "赤": [訳]}
  証明の形・鍵・回（物と名に照らす）・物・表の指紋（数え直す）・パックの版（今のこの中身）・関所・例の照らし・入力の指紋 を照らし、
  1 つでも外れたら通さない。
  入力＝計算に渡した元（`入力の名` の形・月を回す・賞与を回す に渡した物と同じ）は必ず渡す（入力の指紋を数え直す）。
  入力が無い・形が違う時は照らせないので通さない（欠けた材料で黙って通さない）。
  知らない形・欠けた鍵・読めない値は通さない（既定は止める側）。

出口は Drive を開かない。Python 3 の標準ライブラリだけ。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .名と版 import 出す名か, 出す支給月, 回たち

形の名 = "給与の証明/4"
鍵たち = ("形", "会社", "支給月", "回", "物", "表の指紋", "パックの版", "関所", "例の照らし", "入力の指紋")
_賞与だけの物 = {"賞与の取り込み"}
_月だけの物 = {"取り込み", "有給休暇管理表"}
# 回ごとの計算の元（入力の指紋の名）＝計算が読む材料の全部。入力 は {名: 値}:
#   マスタ: {タブの名: 行}（2_マスタ のタブ〔型の正本 初期設定/型.json から名を読む〕と 00_事務所 の 事務所。その会社の行だけ数える）
#   確定した勤怠・確定した勤怠の区間: 年の台帳の同じ名のタブ（その会社の行の全部＝有給も読む）
#   前の確定した勤怠・前の確定した勤怠の区間: 前の支給月（年をまたぐ時は前の年）の台帳の確定した勤怠（月の頭の週・有給の数え。
#     その会社の行の全部。無い時は空の並びを渡す）
#   その月だけの指示・人ごとの月の数字: 年の台帳の同じ名のタブ（その会社・その支給月の行）
#   月の数字: 月の数字の口の行（その会社の行）
#   有給の値: 月を回す の 有給の値（None＝有給を回さない）・法の線: 渡した法の線（None＝パックの 法の表/ から引く＝パックの版で結ぶ）
#   支給一覧・賞与の引数: 賞与を回す の 支給一覧 と {支給日, 前月の課税対象額 など残りの引数}
#   給与のルール: 給与のルール.md の字（MD の例の表の置き場。改行と行末の空白をそろえて数える）
入力の名 = {"月": ("マスタ", "確定した勤怠", "前の確定した勤怠", "その月だけの指示", "人ごとの月の数字", "月の数字",
                 "有給の値", "法の線", "給与のルール"),
           "賞与": ("マスタ", "その月だけの指示", "人ごとの月の数字", "支給一覧", "賞与の引数", "法の線", "給与のルール")}
# 名に添えて同じ指紋に結ぶ名（渡す時は両方を渡す）
添える名 = {"確定した勤怠": "確定した勤怠の区間", "前の確定した勤怠": "前の確定した勤怠の区間"}
# None を値として受ける名（None＝渡さなかった事も計算の元。鍵そのものが無いのは渡し忘れ＝照らせない）
空でよい名 = ("有給の値", "法の線")
_事務所のタブ = ("事務所",)
_根 = Path(__file__).resolve().parent.parent


def _指紋(行たち) -> str:
    rows = [[("" if c is None else str(c)) for c in r] for r in 行たち]
    raw = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def 表の指紋(表) -> str:
    """表（行の並び）の指紋。殻の出荷の口の `table_fingerprint` と同じ式（字のまま・None は空・JSON・sha256）。"""
    return _指紋(表)


def _字(v) -> str:
    return str(v if v is not None else "").strip()


def _行たち(表) -> list[dict]:
    """get_values の形（1 行目が見出し）か dict の並び → dict の並び。読めない形は ValueError。"""
    if isinstance(表, (str, bytes, dict)):
        raise ValueError(f"行の並びでない（{type(表).__name__}）")
    xs = list(表 or ())
    if xs and isinstance(xs[0], (list, tuple)):
        h = [_字(c) for c in xs[0]]
        return [dict(zip(h, r)) for r in xs[1:]]
    if any(not isinstance(r, dict) for r in xs):
        raise ValueError("行が dict でない")
    return [dict(r) for r in xs]


def _束の指紋(行たち) -> str:
    """行の束の指紋。列の並び・行の並び・空の欄・前後の空白では変わらず、値の 1 字が変われば変わる（get_values の形も dict の並びも同じ）。"""
    束 = sorted(sorted((_字(k), _字(v)) for k, v in r.items() if _字(v) and not _字(k).startswith("_")) for r in 行たち)
    return _指紋([[f"{k}={v}" for k, v in r] for r in 束])


def _月の字(v) -> str:
    m = re.match(r"\s*(\d{4})[.\-](\d{2})", _字(v))
    return f"{m.group(1)}-{m.group(2)}" if m else _字(v)


def _マスタのタブ() -> tuple[str, ...]:
    """2_マスタ のタブの名（型の正本 初期設定/型.json から読む＝ここに写さない）。"""
    import importlib.util
    import sys
    名 = "出口_型の口"
    if 名 not in sys.modules:
        spec = importlib.util.spec_from_file_location(名, _根 / "初期設定" / "型の口.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules[名] = m
        spec.loader.exec_module(m)
    for シ in sys.modules[名].型()["シート"]:
        if シ["シート"] == "2_マスタ":
            return tuple(t["タブ"] for t in シ["タブ"])
    raise ValueError("型に 2_マスタ が無い")


def 計算が読むマスタのタブ() -> tuple[str, ...]:
    """入力の マスタ に結ぶタブ（2_マスタ のタブと 00_事務所 の 事務所＝段の解決・入口の文脈が読むマスタの全部）。"""
    return _マスタのタブ() + _事務所のタブ


def 計算の元に要る名(回: str) -> tuple[str, ...]:
    """照らす(…, 入力=) に渡す計算の元の名の全部（`入力の名[回]` と添える名）。殻と出す前の照らしはここから読む（写さない）。"""
    if 回 not in 入力の名:
        raise ValueError(f"回 {回!r} は {'・'.join(回たち)} のどれでもない")
    out = []
    for k in 入力の名[回]:
        out += [k, *((添える名[k],) if k in 添える名 else ())]
    return tuple(out)


def _そろえる(v):
    if isinstance(v, dict):
        return {str(k): _そろえる(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_そろえる(x) for x in v]
    return v


def _値の指紋(v) -> str:
    """dict などの値の指紋（鍵の並び・tuple と list の違い・JSON を通した数の字では変わらない）。"""
    raw = json.dumps(_そろえる(v), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def 入力の指紋(入力: dict, *, 会社: str, 支給月: str, 回: str) -> dict:
    """計算の元 → {名: 指紋}（`入力の名[回]` の名ごと）。足りない名・読めない形は ValueError（照らせない＝通さない）。"""
    if 回 not in 入力の名:
        raise ValueError(f"回 {回!r} は {'・'.join(回たち)} のどれでもない")
    if not isinstance(入力, dict):
        raise ValueError("入力 は {名: 値} の形で渡す")
    欠け = [k for k in 計算の元に要る名(回) if k not in 入力 or (入力[k] is None and k not in 空でよい名)]
    if 欠け:
        raise ValueError(f"入力に {'・'.join(欠け)} が無い")
    その会社 = lambda xs: [r for r in xs if _字(r.get("会社")) in (会社, "")]
    out = {}
    for k in 入力の名[回]:
        v = 入力[k]
        if k == "マスタ":
            if not isinstance(v, dict):
                raise ValueError("入力のマスタ は {タブの名: 行} の形で渡す")
            out[k] = _指紋([[t, _束の指紋(その会社(_行たち(v.get(t, ()))))] for t in 計算が読むマスタのタブ()])
        elif k in 添える名:
            out[k] = _指紋([_束の指紋(その会社(_行たち(v))), _束の指紋(その会社(_行たち(入力[添える名[k]] or ())))])
        elif k in ("その月だけの指示", "人ごとの月の数字"):
            月 = _月の字(支給月)
            out[k] = _束の指紋([r for r in その会社(_行たち(v)) if _月の字(r.get("支給月")) == 月])
        elif k in ("月の数字", "支給一覧"):
            out[k] = _束の指紋(その会社(_行たち(v)))
        elif k in ("有給の値", "法の線", "賞与の引数"):
            if v is not None and not isinstance(v, dict):
                raise ValueError(f"入力の{k} は {{名: 値}} の形で渡す（{type(v).__name__} は読まない）")
            out[k] = _値の指紋(v)
        elif k == "給与のルール":
            if not isinstance(v, str):
                raise ValueError("入力の給与のルール は 給与のルール.md の字で渡す")
            out[k] = hashlib.sha256("\n".join(x.rstrip() for x in v.replace("\r\n", "\n").strip().split("\n"))
                                    .encode("utf-8")).hexdigest()
        else:   # 入力の名に足した名は数え方もここに足す（黙って数えない名を作らない）
            raise ValueError(f"入力の名 {k} の数え方が無い")
    return out


def パックの版() -> str:
    """CHANGELOG の一番上の版の節（`## [vX.Y.Z]`）。「未リリース」に行があれば `+未リリース` を付ける
    （版の印の中身でない＝殻の名簿の版と合わない＝出せない）。読めなければ空（照らす は通さない）。"""
    try:
        t = (_根 / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r"^## \[(v\d+\.\d+\.\d+)\]", t, re.M)
    if not m:
        return ""
    頭 = t[: m.start()]
    未 = re.search(r"^## 未リリース\s*$(.*)", 頭, re.M | re.S)
    return m.group(1) + ("+未リリース" if 未 and re.search(r"^\s*-\s+\S", 未.group(1), re.M) else "")


def _物の値(出す物, 名: str):
    return 出す物.get(名) if isinstance(出す物, dict) else getattr(出す物, 名, None)


def _名の字(出す物):
    名 = _物の値(出す物, "名")
    if 名 is None or isinstance(名, str):
        return 名
    return getattr(名, "名", None) if not isinstance(名, dict) else 名.get("名")


def _回の外れ(回, 物, 名) -> list[str]:
    """回（月／賞与）が 物 に合うか。賞与の取り込みは賞与・取り込みは月。
    名と回（支給控除一覧 は物では見分けない）は `_名の外れ` が 回 で直した支給月の字（`出す支給月`）で照らす（名を渡さない出荷は 回 と 物 だけ）。"""
    if 回 not in 回たち:
        return [f"回 {回!r} は {'・'.join(回たち)} のどれでもない"]
    赤 = []
    if (物 in _賞与だけの物 and 回 != "賞与") or (物 in _月だけの物 and 回 != "月"):
        赤.append(f"回 {回} が物 {物} と合わない（月の表と賞与の表を取り違えて出さない）")
    return 赤


def _名の外れ(名, 物, 会社, 支給月) -> list[str]:
    """名（渡した時だけ）が 物・会社・支給月 の出す名の形か（`出口/名と版.py` の `出す名か` を読む＝形を写さない）。"""
    if not isinstance(名, str) or not 名:
        return []
    if 出す名か(名, str(物), str(会社), str(支給月)):
        return []
    return [f"名 {名} が `{物}_{会社}_{支給月}_v<n>` の形でない（名の 物・会社・支給月 が証明と同じ字でない・"
            "月の表と賞与の表の取り違えも、回 と合わない名として止める）"]


def 証明を付ける(出す物, *, 会社: str, 支給月: str, 回: str, 外した人: int, 例の結果: dict, 入力: dict) -> dict:
    """出口が作った 出す物 の証明（`月次.月を回す`・`月次.賞与を回す` が呼ぶ）。回＝月／賞与。
    例の結果＝`月次/例の確かめ.確かめる` の返す物・入力＝計算の元（`入力の名[回]`）。回が物・名と合わない・入力が足りない時は付けない（止める）。"""
    外れ = _回の外れ(回, _物の値(出す物, "物"), _名の字(出す物))
    if 外れ:
        raise ValueError("証明を付けない: " + "・".join(外れ))
    支給月 = 出す支給月(支給月, 回)   # 名と同じ字（月を回す・賞与を回す の `YYYY.MM支給` も受ける）
    外れ = _名の外れ(_名の字(出す物), _物の値(出す物, "物"), 会社, 支給月)
    if 外れ:
        raise ValueError("証明を付けない: " + "・".join(外れ))
    return {
        "形": 形の名, "会社": 会社, "支給月": 支給月, "回": 回, "物": _物の値(出す物, "物"),
        "名": _名の字(出す物),
        "表の指紋": 表の指紋(_物の値(出す物, "表") or ()),
        "パックの版": パックの版(),
        "関所": {"通った": True, "外した人": int(外した人)},
        "例の照らし": {"通った": bool(例の結果.get("通った")), "数": int(例の結果.get("数") or 0),
                   "合わない": len(例の結果.get("合わない") or ())},
        "入力の指紋": 入力の指紋(入力, 会社=会社, 支給月=支給月, 回=回),
    }


def 照らす(出す物, 証明の物=None, *, 入力=None) -> dict:
    # 入力 は必ず渡す（None は「渡し忘れ」として赤にする。引数を省いた呼び方も TypeError でなく赤で返す）
    """殻の出荷の口が呼ぶ。返す物 {"通す": bool, "赤": [訳]}。赤が 1 つでもあれば 通す＝False。"""
    証明 = 証明の物 if 証明の物 is not None else _物の値(出す物, "証明")
    if not isinstance(証明, dict):
        return {"通す": False, "赤": ["証明が無い（出口の 月を回す・賞与を回す が付けた 証明 を渡す）"]}
    if 証明.get("形") != 形の名:
        return {"通す": False, "赤": [f"証明の形が {証明.get('形')!r}（{形の名} だけ照らす）"]}
    赤 = [f"証明に {k} が無い" for k in 鍵たち if 証明.get(k) in (None, "", {})]
    物, 表 = _物の値(出す物, "物"), _物の値(出す物, "表")
    if 物 != 証明.get("物"):
        赤.append(f"物が違う（出す物 {物!r}・証明 {証明.get('物')!r}）")
    名 = _名の字(出す物)
    赤 += _回の外れ(証明.get("回"), 物, 名)
    if 名 is not None and 名 != 証明.get("名"):
        赤.append(f"名が違う（出す物 {名!r}・証明 {証明.get('名')!r}）")
    if 証明.get("回") in 回たち:
        try:
            字 = 出す支給月(証明.get("支給月"), 証明["回"])
        except ValueError as x:
            赤.append(f"証明の支給月が出口の字でない（{x}）")
        else:
            if 字 != 証明.get("支給月"):
                赤.append(f"証明の支給月 {証明.get('支給月')!r} が出口の字 {字!r} でない（`{形の名}` は名と同じ字を書く）")
            赤 += _名の外れ(名, 物, 証明.get("会社"), 字)
    if not 表:
        赤.append("出す物に表が無い")
    elif 証明.get("表の指紋") != 表の指紋(表):
        赤.append("表の指紋が合わない＝出口が作った後に表が変わった（計算の外で直さず、上流を直して出口で作り直す）")
    今の版 = パックの版()
    if not 今の版 or "+" in 今の版:
        赤.append(f"照らすパックの版が版の印の中身でない（{今の版 or '読めない'}）")
    elif 証明.get("パックの版") != 今の版:
        赤.append(f"証明の版 {証明.get('パックの版')} が照らすパックの版 {今の版} と違う（その版の出口で作り直す）")
    関 = 証明.get("関所") if isinstance(証明.get("関所"), dict) else {}
    if 関.get("通った") is not True:
        赤.append("関所を通っていない")
    例 = 証明.get("例の照らし") if isinstance(証明.get("例の照らし"), dict) else {}
    if 例.get("通った") is not True:
        赤.append("例の照らしを通っていない（給与のルール.md の例が合わない・確かめた日が無い・確かめた人が空か名簿に居ない・書けない・無い）")
    elif not isinstance(例.get("数"), int) or 例["数"] < 1 or 例.get("合わない") != 0:
        赤.append(f"例の照らしの中身が通ったと合わない（数 {例.get('数')!r}・合わない {例.get('合わない')!r}）")
    if 入力 is None:
        赤.append("入力（計算の元: `計算の元に要る名(回)` の名の全部）が無い＝入力の指紋を照らせない"
                 "（出荷の口は 照らす(出す物, 証明, 入力={…}) と呼ぶ）")
    elif not isinstance(証明.get("入力の指紋"), dict):
        赤.append(f"入力の指紋が {{名: 指紋}} の形でない（{type(証明.get('入力の指紋')).__name__}）＝照らせない")
    elif 証明.get("回") not in 入力の名:
        赤.append("回が月・賞与でない＝入力の指紋を照らせない")
    else:
        try:
            今 = 入力の指紋(入力, 会社=str(証明.get("会社", "")), 支給月=str(証明.get("支給月", "")), 回=証明["回"])
        except (TypeError, ValueError) as x:
            赤.append(f"入力 を読めない＝入力の指紋を照らせない（{x}）")
        else:
            for k in 入力の名[証明["回"]]:
                if 証明["入力の指紋"].get(k) != 今[k]:
                    赤.append(f"入力の指紋が合わない（{k}）＝証明を作った後に {k} が変わった（今の元で月を回し直す）")
    return {"通す": not 赤, "赤": 赤}
