"""CI と同じ版の Python の文法で、repo の全部の .py が読めるかを照らす（検査の入口 check_all.sh の最初の段）。

なぜ: 手元の Python（例 3.13）と CI の Python（3.12）の版が違うと、手元の緑が CI の緑を約束しない
（3.13 にだけ在る文法・名に使える字の違い。例 関数の名の「・」U+30FB は 3.12 で SyntaxError）。
`ast.parse(feature_version=…)` は名に使える字（Unicode の版）の違いを捕まえないので、照らしは
CI と同じ版の python そのもので compile する（版の決まりを写さない）。

- 版の正本は `.github/workflows/ci.yml` の `python-version`（ここに写さない）。読めない・2 つ以上なら赤。
- その版の python を探す順: 今の python → PATH の `python<版>` → `uv python find <版>`。無ければ赤（入れ方を出す）。
- 照らす file: 引数で渡せばそれだけ。渡さなければ git の file（追跡中＋まだ足していない・.gitignore の外）の .py 全部。
- 通れば 1 行目に `PYTHON=<その版の python の path>` を出す（入口が試験を同じ python で回せるかを見る）。
- 終了の値: 0 通り／1 読めない file が在る／2 照らしが働けない（版か python が決まらない・道具が壊れた）。
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
CIの定義 = 根 / ".github" / "workflows" / "ci.yml"

# 子（CI の版の python）で回す照らし。-I で cwd や repo の物を読まない。file の path は \0 区切りで stdin から
_子 = r"""
import sys
悪い = 0
try:
    for p in sys.stdin.buffer.read().decode("utf-8").split("\0"):
        if not p:
            continue
        try:
            with open(p, "rb") as f:
                compile(f.read(), p, "exec", dont_inherit=True)
        except SyntaxError as e:
            悪い += 1
            print(f"読めない: {p}:{e.lineno}: {e.msg}")
        except (OSError, ValueError) as e:
            悪い += 1
            print(f"読めない: {p}: {e}")
except Exception as e:  # 子そのものが壊れた＝2（1 の「読めない file が在る」と混ぜない）
    print(f"子が壊れた: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(2)
sys.exit(1 if 悪い else 0)
"""


def CIの版(字: str) -> str:
    """ci.yml の python-version を 1 つだけ読む。読めない・違う値が 2 つ以上なら ValueError（既定で止める）。"""
    行 = re.findall(r"^\s*-?\s*python-version:\s*(.*?)\s*$", 字, re.M)
    if not 行:
        raise ValueError("ci.yml に python-version が無い")
    版 = set()
    for v in 行:
        m = re.fullmatch(r"""(["']?)(3\.\d+)\1""", v)
        if not m:
            raise ValueError(f"ci.yml の python-version が読めない（3.N の形でない）: {v}")
        版.add(m[2])
    if len(版) != 1:
        raise ValueError(f"ci.yml の python-version が 1 つに決まらない: {sorted(版)}")
    return 版.pop()


def _版を聞く(py: str) -> str | None:
    try:
        r = subprocess.run([py, "-I", "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def 版のpython(版: str) -> str | None:
    if "%d.%d" % sys.version_info[:2] == 版:
        return sys.executable
    候補 = [shutil.which(f"python{版}")]
    uv = shutil.which("uv")
    if uv:
        try:
            r = subprocess.run([uv, "python", "find", "--no-project", 版], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                候補.append(r.stdout.strip())
        except (OSError, subprocess.TimeoutExpired):
            pass
    for py in 候補:
        if py and _版を聞く(py) == 版:   # 名でなく中の版を照らす（python3.12 という名の別の版を通さない）
            return py
    return None


def gitの_py() -> list[str]:
    r = subprocess.run(["git", "-C", str(根), "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.py"],
                       capture_output=True, check=True)
    return [str(根 / p) for p in r.stdout.decode("utf-8").split("\0") if p and (根 / p).is_file()]


def main(引数: list[str]) -> int:
    try:
        版 = CIの版(CIの定義.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"赤: CI の Python の版が決まらない（{e}）")
        return 2
    py = 版のpython(版)
    if py is None:
        print(f"赤: CI と同じ Python {版} が手元に無い（今の python は {'%d.%d' % sys.version_info[:2]}）。"
              f"入れ方の例: uv python install {版}（か OS の python{版}）")
        return 2
    file = [str(Path(p).resolve()) for p in 引数] if 引数 else gitの_py()
    r = subprocess.run([py, "-I", "-c", _子], input="\0".join(file).encode("utf-8"), capture_output=True)
    sys.stdout.write(r.stdout.decode("utf-8", "replace"))
    sys.stdout.write(r.stderr.decode("utf-8", "replace"))
    数 = r.stdout.decode("utf-8", "replace").count("読めない: ")
    if r.returncode == 1 and 数 > 0:
        print(f"赤: CI の Python {版} の文法で読めない .py が {数} 個在る（{py} で照らした）")
        return 1
    if r.returncode != 0:   # 読めない file を 1 つも挙げずに落ちた＝照らしの子が壊れた（結果ではない）
        print(f"赤: Python の版の照らしが壊れた（{py} の子が終わりの値 {r.returncode}・読めない file は挙げていない）＝結果ではない・道具を直す")
        return 2
    print(f"PYTHON={py}")
    print(f"Python の版の照らし: CI の Python {版} の文法で .py {len(file)} 個が読めた（{py} で照らした）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:  # 道具そのものが壊れた＝終わりの値 2（1 の「見つかった・赤」と混ぜない）
        import traceback
        traceback.print_exc()
        print(f"✗ 道具が壊れた（Python の版の照らし・終わりの値 2＝結果ではない）: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
