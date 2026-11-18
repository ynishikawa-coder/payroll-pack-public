"""土台（agent-foundation-public）を読む版の印は .github/workflows/土台の版.json の 1 か所だけ。

workflow が土台を取る所（actions/checkout の repository か git clone の URL）は、印を字で書かず、
同じ job の「土台の版を読む」段（id af）が json から読んだ値（steps.af.outputs.ref）を使う。
印が 2 か所に書かれて食い違う（前は tag.yml が v0.3.0・public-mirror.yml が v0.4.9）のを入れない形にする。
"""
import json
import re
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
_印 = re.compile(r"v\d+\.\d+\.\d+")
_土台 = "agent-foundation-public"


def 版の表(根: Path) -> dict:
    return json.loads((根 / ".github" / "workflows" / "土台の版.json").read_text(encoding="utf-8"))


def 外れ(根: Path) -> list[str]:
    """workflow の中で、土台を取るのに版の表を通っていない所と、表に無い鍵を読む所を返す。"""
    表 = 版の表(根)
    out = []
    for p in sorted((根 / ".github" / "workflows").glob("*.y*ml")):
        行s = p.read_text(encoding="utf-8").splitlines()
        読む鍵 = re.findall(r'土台の版\.json", encoding="utf-8"\)\)\["([^"]+)"\]', "\n".join(行s))
        out += [f"{p.name}: 表に無い鍵 {k}" for k in 読む鍵 if k not in 表]
        for i, 行 in enumerate(行s):
            if re.search(rf"repository:\s*\S+/{_土台}\s*$", 行):
                後 = next((x for x in 行s[i + 1:i + 6] if x.strip().startswith("ref:")), "")
                if "${{ steps.af.outputs.ref }}" not in 後:
                    out.append(f"{p.name}:{i + 1}: checkout の ref が版の表を通っていない: {後.strip() or '(ref 無し)'}")
                if not 読む鍵:
                    out.append(f"{p.name}:{i + 1}: 土台の版を読む段が無い")
            elif re.search(rf"github\.com/\S+/{_土台}", 行) and "git clone" in 行:
                if "--branch" not in 行 or _印.search(行) or not 読む鍵:
                    out.append(f"{p.name}:{i + 1}: clone の版が版の表を通っていない")
    return out


def test_版の表の値は版の印の形():
    表 = 版の表(根)
    assert 表["土台"] and all(_印.fullmatch(v) for k, v in 表.items() if not k.endswith("訳")), 表


def test_workflowは土台の版を表からだけ読む():
    assert 外れ(根) == []


def test_土台を読むworkflowを数えている():
    # 照らしが空回りしていない（在る workflow のうち土台を取る 3 つが表を読む）。
    # tag.yml・public-mirror.yml は公開の写しへ持っていかない（scripts/public_mirror.py の OMIT）＝在る物だけ数える。
    # この元の repo に 3 つとも在ることは tests/test_公開版へ出す.py が見る。
    d = 根 / ".github" / "workflows"
    名 = {p.name for p in d.glob("*.yml") if _土台 in p.read_text(encoding="utf-8")}
    assert "ci.yml" in 名
    assert {n for n in ("tag.yml", "public-mirror.yml") if (d / n).exists()} <= 名


def test_印を字で書いたworkflowを見つける(tmp_path):
    # 注入の試験: 印を字で書いた checkout・表に無い鍵・印を字で書いた clone を置くと赤になる
    w = tmp_path / ".github" / "workflows"
    w.mkdir(parents=True)
    (w / "土台の版.json").write_text(json.dumps({"土台": "v0.4.14"}), encoding="utf-8")
    (w / "a.yml").write_text(
        "steps:\n"
        "  - uses: actions/checkout@v4\n"
        "    with:\n"
        "      repository: 持ち主/agent-foundation-public\n"
        "      ref: v0.3.0\n", encoding="utf-8")
    (w / "b.yml").write_text(
        "steps:\n"
        "  - run: python3 -c 'json.load(open(\".github/workflows/土台の版.json\", encoding=\"utf-8\"))[\"無い鍵\"]'\n"
        "  - run: git clone --branch v0.4.9 https://github.com/持ち主/agent-foundation-public x\n", encoding="utf-8")
    assert 外れ(tmp_path) == [
        "a.yml:4: checkout の ref が版の表を通っていない: ref: v0.3.0",
        "a.yml:4: 土台の版を読む段が無い",
        "b.yml: 表に無い鍵 無い鍵",
        "b.yml:3: clone の版が版の表を通っていない",
    ]
