"""出所を見る（確かめと仮.md §1「確かめ方」）。初期設定の照らしの終わりに、マスタの値の出所に過去の結果（答え）が 0 かを見る。

初期設定の照らしは本番の 0 段の手順。照らしを終えて毎月の計算へ進む前に、マスタ「変更の記録」の各行の出所
（書類の名・問いの番号）が 原本・決まりの MD・質問と回答 のどれかで、**過去の結果を出所とする値が 0** であることを見る。
1 つでもあれば止める（`止める` が真）＝その値は答えで決め直すまで毎月へ進まない。

止める行（どれも `外れ` に 1 行ずつ返す・黙って捨てない）:
- `過去の結果が書類`: 書類の名が照らした答えの file（答えの行の出所の file か、渡した答えの資料の名）。
- `過去の結果が見当`: 問いの番号の問い（質問と回答の一番下の行）にまだ答えが無く（空・分からない）、見当の拠り所が過去の結果。
- `答えの無い問いが出所`: 確かめ＝確認済 の値の問いに、まだ答えが無い（質問と回答の答えでなく見当で決めた値）。
- `出所が無い`: 書類の名も問いの番号も空（確かめ＝記録だけ の行は見ない）。
- `問いが無い`: 問いの番号が質問と回答に無い。
- `問いを確かめられない`: 問いの番号を出所にした行があるのに、質問と回答を渡していない（材料が無い時は止める）。

読み方:
- 書類の名は、答えの資料の名（拡張子を除き NFKC・空白を除いてそろえた字）と同じか、その字を中に含めば当てる
  （`（逆算）8〜10 月分の支給控除一覧表` は答えの資料 `8〜10月分の支給控除一覧表.pdf` に当たる）。
- 問いの番号の欄は 、・, で並べてよい（1 つずつ引く）。会社の質問と回答に無い番号は、渡せば事務所の質問と回答（00_事務所）から引く。
- 変更の記録のほかに、決まりの MD の `［出所］`（`[出所]`）の行と、台帳（確定した勤怠・その区間）の 直した訳 の `問い:<番号>` を
  `出所の行たち` で同じ形の行にして、同じ照らしへ通せる（`見る` の md・台帳 を渡す）。

Drive を開かない。殻が読んだタブの行（列名の dict の並び）と答えの file の名を受けて返すだけ。芯/ を import しない。
"""
from __future__ import annotations

import importlib.util
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


def _読み込む(名: str, path: Path):
    s = importlib.util.spec_from_file_location(名, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


# 答えの読み（回答 の字 → 答えの語・一番下の行が正）の正本は 初期設定/型の口.py（写さずに読む）
_型の口 = _読み込む("出所を見る_型の口", Path(__file__).resolve().parents[2] / "初期設定" / "型の口.py")

_過去の拠り所 = re.compile(r"過去の(?:結果|答え|支給)|給与ソフトの(?:結果|答え)")
_答えの無い答え = re.compile(r"^(?:|分からない.*)$")


@dataclass(frozen=True)
class 見た物:
    外れ: tuple[dict, ...]          # {訳, 行の番号, NO, 項目, 書類の名, 問いの番号, 字}
    見た行の数: int
    止める: bool = field(default=False)

    def 字の形(self) -> dict:
        return {"止める": self.止める, "見た行の数": self.見た行の数, "外れの数": len(self.外れ), "外れ": list(self.外れ)}


def _名(字) -> str:
    """file の名をそろえる（NFKC・空白を除く・`#タブ` と道を外す）。"""
    s = unicodedata.normalize("NFKC", str(字 or "")).split("#")[0].replace("\\", "/").rsplit("/", 1)[-1]
    return re.sub(r"\s", "", s)


_拡張子 = re.compile(r"\.(?:pdf|csv|xlsx?|xlsm|tsv|txt|json|html?|md|png|jpe?g)$", re.I)


def _幹(字) -> str:
    """名の拡張子を外した字（書類の名には拡張子を書かないことが多い）。"""
    return _拡張子.sub("", _名(字))


_含みの短さ = 4   # 中に含むかで当てる答えの名の短さの下限（`縦` のような 1 字の名をほかの名の中に当てない）


def _答えの書類か(書類: str, 答え: set[str]) -> bool:
    """書類の名が答えの資料の名と同じか、答えの資料の名（拡張子を除く）を中に含むか。"""
    幹 = _幹(書類)
    return bool(幹) and any(a and (幹 == a or len(a) >= _含みの短さ and a in 幹) for a in {_幹(x) for x in 答え})


_番号の区切り = re.compile(r"[、・,，;；\s]+")
_番号の形 = re.compile(r"Q\d{6}-\d+")
_出所の行 = re.compile(r"[［\[]出所[］\]]\s*[:：]?\s*(.+)$")
_訳の問い = re.compile(r"問い[:：]\s*([^\s、,，;；・／/（(]+)")


def 出所の行たち(md: dict | None = None, 台帳: dict | None = None, 会社: str | None = None) -> list[dict]:
    """決まりの MD の `［出所］<書類の名・問いの番号を 、・ で>` の行と、台帳（確定した勤怠・確定した勤怠の区間）の 直した訳 の
    `問い:<番号>` → 変更の記録と同じ形の行（{会社, 項目, NO, 書類の名, 問いの番号, 確かめ, 新しい値, 所}）。
    md: {md の名: 字}。台帳: {タブの名: 行（列名の dict の並びか、1 行目が見出しの 2 次元の並び）}。
    MD の出所は確かめ＝空（書類か問いの番号を見る）・台帳の答えは確かめ＝確認済（答えの無い問いで確定にしない）。"""
    out = []
    for 名, 字 in (md or {}).items():
        見出し = ""
        for n, 行 in enumerate(str(字 or "").splitlines(), 1):
            h = re.match(r"^#+\s*(.+?)\s*$", 行)
            if h:
                見出し = h.group(1)
                continue
            m = _出所の行.search(行)
            if not m:
                continue
            片 = [w for w in _番号の区切り.split(unicodedata.normalize("NFKC", m.group(1)).strip("（）() ")) if w]
            番号 = [w for w in 片 if _番号の形.fullmatch(w)]
            書類 = [w for w in re.split(r"[、,，]", m.group(1))
                  if w.strip() and not all(_番号の形.fullmatch(x) for x in _番号の区切り.split(unicodedata.normalize("NFKC", w)) if x)]
            out.append({"会社": 会社 or "", "項目": f"{名}#{見出し}", "NO": "", "書類の名": "、".join(x.strip() for x in 書類),
                        "問いの番号": "、".join(番号), "確かめ": "", "新しい値": 行.strip(), "所": f"{名} {n} 行目"})
    for タブ in ("確定した勤怠", "確定した勤怠の区間"):
        rows = (台帳 or {}).get(タブ) or []
        if rows and isinstance(rows[0], (list, tuple)):
            h = [str(x).strip() for x in rows[0]]
            rows = [dict(zip(h, r)) for r in rows[1:]]
        for n, r in enumerate(rows, 2):
            if 会社 is not None and _字(r.get("会社")) not in ("", 会社):
                continue
            番号 = _訳の問い.findall(_字(r.get("直した訳")))
            if 番号:
                out.append({"会社": _字(r.get("会社")), "項目": f"台帳/{タブ}", "NO": _字(r.get("NO")), "書類の名": "",
                            "問いの番号": "、".join(番号), "確かめ": "確認済", "新しい値": _字(r.get("直した訳")),
                            "所": f"台帳/{タブ} {n} 行目（{_字(r.get('日付'))}）"})
    return out


def _字(v) -> str:
    return str(v or "").strip()


def 答えの資料(答えの行) -> set[str]:
    """照らした答えの縦（行か dict）→ 答えの file の名の集まり。"""
    out = set()
    for r in 答えの行 or ():
        出所 = r.get("出所") if isinstance(r, dict) else getattr(r, "出所", "")
        if _名(出所):
            out.add(_名(出所))
    return out


def 見る(変更の記録, 答えの資料たち, 質問と回答=(), 会社: str | None = None, *, 事務所の質問と回答=(),
       md: dict | None = None, 台帳: dict | None = None) -> 見た物:
    """変更の記録の行 → 出所の外れ。答えの資料たち: 答えの file の名（`答えの資料` の返す物か名の並び）。
    質問と回答: その会社の質問と回答の行（問いの番号を出所にした行があれば要る・無ければ止める）。会社: 渡せばその会社の行だけ見る。
    事務所の質問と回答: 00_事務所 の質問と回答（会社の質問と回答に無い番号を引く）。md・台帳: `出所の行たち` へ渡し、
    出た行を変更の記録の後ろに足して同じに見る（行の番号は変更の記録の続き・`所` に MD の行・台帳の行を書く）。"""
    答え = {_名(x) for x in 答えの資料たち if _名(x)}
    今の問い = {_字(q.get("問いの番号")): q for q in _型の口.今の問いの行たち(事務所の質問と回答 or ())}
    今の問い.update({_字(q.get("問いの番号")): q for q in _型の口.今の問いの行たち(質問と回答 or ())
                 if 会社 is None or _字(q.get("会社")) in ("", 会社)})   # 同じ番号は一番下の行が正（送り直しは新しい行）
    質問と回答 = list(質問と回答 or ()) + list(事務所の質問と回答 or ())
    行たち = list(変更の記録 or ()) + 出所の行たち(md, 台帳, 会社)
    外れ, 見た = [], 0
    for i, r in enumerate(行たち, start=1):
        if 会社 is not None and _字(r.get("会社")) not in ("", 会社):
            continue
        if _字(r.get("確かめ")) == "記録だけ":
            continue
        見た += 1
        書類, 番号 = _字(r.get("書類の名")), _字(r.get("問いの番号"))
        基 = {"行の番号": i, "NO": _字(r.get("NO")), "項目": _字(r.get("項目")), "書類の名": 書類, "問いの番号": 番号,
              "字": _字(r.get("新しい値")), **({"所": r["所"]} if r.get("所") else {})}
        訳たち = []
        書類たち = [w for w in re.split(r"[、,]", 書類) if w.strip()]
        if any(_答えの書類か(w, 答え) for w in 書類たち):
            訳たち.append("過去の結果が書類")
        番号たち = [w for w in _番号の区切り.split(unicodedata.normalize("NFKC", 番号)) if w]
        if 番号たち and not 質問と回答:   # 問いが在るか・答えが来たか・見当が何からかを見る材料が無い＝進まない
            訳たち.append("問いを確かめられない")
        for no in 番号たち if 質問と回答 else ():
            q = 今の問い.get(no)
            if q is None:
                訳たち.append("問いが無い")
            elif _答えの無い答え.fullmatch(_型の口.答えの芯(q.get("回答"))):
                if _過去の拠り所.search(_字(q.get("見当の拠り所"))):
                    訳たち.append("過去の結果が見当")
                elif _字(r.get("確かめ")) == "確認済":
                    訳たち.append("答えの無い問いが出所")
        訳たち = list(dict.fromkeys(訳たち))
        if not 書類たち and not 番号:
            訳たち.append("出所が無い")
        外れ += [dict(基, 訳=w) for w in 訳たち]
    return 見た物(外れ=tuple(外れ), 見た行の数=見た, 止める=bool(外れ))
