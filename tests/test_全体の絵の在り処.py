"""値の表 config/skill-values.json の docs-kit.big-picture.agreed が、合意した全体の絵の在り処を指すか（注入の試験）。

なぜ在るか: 給与の合意した全体の絵の正は Notion の案件のページで、値の表が在り処を指していないと、土台の
big_picture.py pick は repo の docs/全体の絵.json を探し、無いので「照らせない」になる。合意した設計の仕事の終わりの
1 回の照らし（完了の報告に「設計図どおり」か「差とその扱い」を書く）で合意した絵を引けるよう、在り処を値の表に持つ。
照らしは合流の条件ではない。

在り処の照らしは値の形で分けず、取り得る形を全部数えて既定で赤にする（前は「.json で終わる時だけ中身を見て、
ほかは何でも緑」で、実の値＝案件のページの名には何も当たっていなかった）:
- 並び（製品ごと）: 各行が {name, path, covers}（土台の big_picture.py pick と同じ形）。各 path を下と同じく照らす。
- repo の道に見える字（/ を含む・拡張子が在る・repo に在る）: .json で終わり・repo に在り・合意した絵の中身。
  .json でない道（.yaml・.md・拡張子無し）は土台が絵として読めないので赤。
- 案件のページの名: 公開の repo に URL を置かない（「://」を含めば赤）・改行や前後の空白が無い・
  土台の型どおり「全体の絵: <仕組みの名>」で始まる。ページの中身は repo の外（Notion）なので、ここでは照らせない。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _agreed(values):
    return ((values.get("docs-kit") or {}).get("big-picture") or {}).get("agreed")


def _problems(values, root):
    v = _agreed(values)
    if isinstance(v, list):
        if not v:
            return ["docs-kit.big-picture.agreed の並びが空"]
        out = []
        for i, ent in enumerate(v):
            if not isinstance(ent, dict) or set(ent) != {"name", "path", "covers"}:
                out.append("agreed[%d] が {name, path, covers} でない" % i)
                continue
            if not isinstance(ent["name"], str) or not ent["name"].strip():
                out.append("agreed[%d] の name が無い" % i)
            c = ent["covers"]
            if not isinstance(c, list) or not c or not all(isinstance(x, str) and x for x in c):
                out.append("agreed[%d] の covers（覆う path の頭の並び）が無い" % i)
            out += _在り処の問題(ent["path"], root)
        return out
    return _在り処の問題(v, root)


ページの名の頭 = "全体の絵: "


def _在り処の問題(v, root):
    if not isinstance(v, str) or not v.strip():
        return ["docs-kit.big-picture.agreed が無い（合意した絵の在り処＝案件のページの名か repo の中の .json）"]
    if v != v.strip() or "\n" in v:
        return ["在り処「%s」の前後に空白か改行が在る" % v]
    if "/" in v or "\\" in v or Path(v).suffix or (root / v).exists():
        if not v.endswith(".json"):
            return ["在り処「%s」は道に見えるが .json でない（土台は .json の絵しか読めない）" % v]
        if not (root / v).exists():
            return ["docs-kit.big-picture.agreed の %s が repo に無い" % v]
        return _絵の中身の問題(root / v)
    if "://" in v:
        return ["在り処「%s」に URL が在る（公開の repo では案件のページを名で書く）" % v]
    if not v.startswith(ページの名の頭) or not v[len(ページの名の頭):].strip():
        return ["在り処「%s」が案件のページの名の型「%s<仕組みの名>」でない" % (v, ページの名の頭)]
    return []


def _絵の中身の問題(path):
    """在るだけでなく、合意した絵の形か（前は "{}" でも緑だった）。形の正本は土台の big_picture.py check で、
    ここはその中の「合意した絵と言える最小」だけを見る: object・meta.kind が 合意・meta.agreed.by が owner・箱が 1 つ以上。"""
    try:
        pic = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        return ["%s が JSON として読めない: %s" % (path.name, e)]
    if not isinstance(pic, dict):
        return ["%s が JSON の object でない" % path.name]
    meta = pic.get("meta") if isinstance(pic.get("meta"), dict) else {}
    out = []
    if meta.get("kind") != "合意":
        out.append("%s の meta.kind が 合意 でない" % path.name)
    if not isinstance(meta.get("agreed"), dict) or meta["agreed"].get("by") != "owner":
        out.append("%s に meta.agreed（by=owner）が無い＝合意した版と言えない" % path.name)
    boxes = pic.get("boxes")
    if not isinstance(boxes, list) or not boxes or not all(isinstance(b, dict) for b in boxes):
        out.append("%s に箱（boxes）が無い" % path.name)
    return out


def test_値の表が合意した全体の絵の在り処を指す():
    values = json.loads((ROOT / "config" / "skill-values.json").read_text(encoding="utf-8"))
    assert _problems(values, ROOT) == []


def test_在り処が無い値の表は拒む(tmp_path):
    assert _problems({"docs-kit": {"qa-html": {}}}, tmp_path)
    assert _problems({"docs-kit": {"big-picture": {"agreed": " "}}}, tmp_path)
    assert _problems({"docs-kit": {"big-picture": {"agreed": "docs/全体の絵.json"}}}, tmp_path)
    (tmp_path / "docs").mkdir()
    絵 = tmp_path / "docs" / "全体の絵.json"
    値 = {"docs-kit": {"big-picture": {"agreed": "docs/全体の絵.json"}}}
    合意 = {"meta": {"kind": "合意", "agreed": {"by": "owner"}}, "boxes": [{"id": "芯"}]}
    絵.write_text(json.dumps(合意, ensure_ascii=False), encoding="utf-8")
    assert _problems(値, tmp_path) == []
    # 注入: 在るだけの空・壊れ・合意でない絵は拒む（前は "{}" でも緑）
    for 中 in ("{}", "[]", "{", json.dumps({**合意, "boxes": []}), json.dumps({**合意, "meta": {"kind": "実物"}}),
               json.dumps({**合意, "meta": {"kind": "合意"}})):
        絵.write_text(中, encoding="utf-8")
        assert _problems(値, tmp_path), 中


def test_実の値は照らしの枝を通る():
    """実の値が、何も見ない枝で緑になっていない事（前は .json でない値は無条件に緑だった）。"""
    values = json.loads((ROOT / "config" / "skill-values.json").read_text(encoding="utf-8"))
    v = _agreed(values)
    在り処たち = [e.get("path") for e in v] if isinstance(v, list) else [v]
    for x in 在り処たち:
        assert x.endswith(".json") or x.startswith(ページの名の頭), x


def test_注入_ページの名の在り処の誤りは拒む(tmp_path):
    for 値 in ("docs/全体の絵.yaml", "docs/全体の絵", "全体の絵.md", "https://example.invalid/絵",
              "全体の絵: ", "給与計算", " 全体の絵: 給与計算", "全体の絵: 給与計算\n", [], [{"name": "給与"}],
              [{"name": "給与", "path": "全体の絵: 給与計算", "covers": []}],
              [{"name": "給与", "path": "docs/x.json", "covers": ["/"]}], 3):
        assert _problems({"docs-kit": {"big-picture": {"agreed": 値}}}, tmp_path), 値
    for 値 in ("全体の絵: 給与計算", [{"name": "給与", "path": "全体の絵: 給与計算", "covers": ["/"]}]):
        assert _problems({"docs-kit": {"big-picture": {"agreed": 値}}}, tmp_path) == [], 値


def test_注入_並びの中の合意でない絵の中身も拒む(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "x.json").write_text("{}", encoding="utf-8")
    値 = {"docs-kit": {"big-picture": {"agreed": [{"name": "給与", "path": "docs/x.json", "covers": ["/"]}]}}}
    assert _problems(値, tmp_path)
