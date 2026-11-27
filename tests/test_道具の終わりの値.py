"""道具の終わりの値: 道具そのものが壊れた時は 2、意味のある「見つかった・赤・止めた」は 1（混ぜない）。

なぜ（根治・2026-11-22・決定 420a40dc-f638-8162-84f4-d1181128d83d）: 7 つの道具が、壊れて止まった時（捕まえない例外＝Python は 1 で抜ける）も
「見つかった物がある」と同じ 1 を返していた。呼び手は落ちた回を「差がある・赤・改定が近い」と読みうる。そこで各道具の入口が
捕まえない例外を受けて「道具が壊れた（…・終わりの値 2＝結果ではない）」を標準エラーに出し 2 で抜ける形にそろえた。

ここは道具ごとに、わざと壊して（例外を注入するか、形の違う入力を渡して）本当の入口（`__main__`）を回し、2 と知らせを見る。
意味のある 1 が 1 のままなことも同じ道具で見る（2 に寄せて 1 を消していない）。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

根 = Path(__file__).resolve().parents[1]
壊れた = "道具が壊れた"


def _回す(前置き: str, 入口: str, argv: list[str], *, 入力: str = "", cwd: Path = 根, env: dict | None = None):
    """前置き（壊す注入）を当ててから、道具の本当の入口を __main__ として回す。入口は file の path か `-m 名`。"""
    if 入口.startswith("-m "):
        走る = f"import runpy, sys; sys.argv = [{入口[3:]!r}] + {argv!r}; runpy.run_module({入口[3:]!r}, run_name='__main__', alter_sys=True)"
    else:
        走る = (f"import runpy, sys; sys.path.insert(0, {str(Path(入口).parent)!r}); sys.argv = [{入口!r}] + {argv!r}; "
              f"runpy.run_path({入口!r}, run_name='__main__')")
    code = textwrap.dedent(前置き) + "\n" + 走る
    e = dict(os.environ, PYTHONPATH=str(根))
    e.update(env or {})
    return subprocess.run([sys.executable, "-c", code], input=入力, capture_output=True, text=True, cwd=cwd, env=e, timeout=120)


# 注入: file を読む手を壊す（OSError でない＝道具が想定して捕まえる「読めない」ではない故障）
読む手を壊す = """
import pathlib
def _壊す(*a, **k):
    raise RuntimeError("注入した故障")
pathlib.Path.read_text = _壊す
"""


def _壊れた2(r) -> None:
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert 壊れた in r.stderr and "終わりの値 2" in r.stderr, r.stderr


# 1. 版の記録の道具 scripts/changelog.py
def test_版の記録の道具_壊れたら2_赤は1(tmp_path):
    道具 = str(根 / "scripts" / "changelog.py")
    _壊れた2(_回す(読む手を壊す, 道具, ["check"]))
    # 使い方の誤り・形の違う版の名は 2（赤・止めたの 1 と混ぜない）
    assert _回す("", 道具, ["知らない口"]).returncode == 2
    r = _回す("", 道具, ["版", "v1", "2099-01-01"])
    assert r.returncode == 2 and "vX.Y.Z" in r.stderr, r.stderr
    # 意味のある赤は 1 のまま: 形の違う断片の名を置いた複製で check
    複製 = tmp_path / "r"
    (複製 / "scripts").mkdir(parents=True)
    shutil.copy(道具, 複製 / "scripts" / "changelog.py")
    shutil.copytree(根 / "CHANGELOG.d", 複製 / "CHANGELOG.d")
    shutil.copy(根 / "CHANGELOG.md", 複製 / "CHANGELOG.md")
    (複製 / "CHANGELOG.d" / "名の形が違う.txt").write_text("- x\n", encoding="utf-8")
    r = _回す("", str(複製 / "scripts" / "changelog.py"), ["check"])
    assert r.returncode == 1 and "changelog: 赤" in r.stdout, (r.stdout, r.stderr)


# 2. 決まりを差し込む口 plugins/payroll-agent/scripts/差し込む.py
def test_決まりを差し込む口_checkは壊れたら2_injectは0():
    道具 = str(根 / "plugins" / "payroll-agent" / "scripts" / "差し込む.py")
    _壊れた2(_回す(読む手を壊す, 道具, ["check"]))
    r = _回す(読む手を壊す, 道具, ["inject"])   # 窓の起動を止めない（hook）＝0 で抜け、壊れたと知らせる
    assert r.returncode == 0 and "壊れた" in r.stderr, r.stderr
    assert _回す("", 道具, ["check"]).returncode == 0


# 3. 答え合わせの道具 道具/答え合わせ（`python3 -m 道具.答え合わせ`）
def test_答え合わせの道具_壊れたら2_差は1(tmp_path):
    (tmp_path / "芯.json").write_text("5", encoding="utf-8")   # 形の違う JSON（行の並びでも dict でもない）
    (tmp_path / "答え.json").write_text(json.dumps({"行": []}), encoding="utf-8")
    (tmp_path / "つなぎ.json").write_text("[]", encoding="utf-8")
    引数 = ["照らす", "--芯", str(tmp_path / "芯.json"), "--答え", str(tmp_path / "答え.json"),
          "--つなぎ", str(tmp_path / "つなぎ.json"), "--出す", str(tmp_path / "差.json")]
    _壊れた2(_回す("", "-m 道具.答え合わせ", 引数))
    assert not (tmp_path / "差.json").exists()   # 出す file は書かれない
    # 意味のある 1（要確認がある）は 1 のまま
    (tmp_path / "芯.json").write_text(json.dumps({"行": [], "人の状態": []}), encoding="utf-8")
    (tmp_path / "答え.json").write_text(json.dumps({"行": [], "要確認": ["作り物の要確認"]}), encoding="utf-8")
    r = _回す("", "-m 道具.答え合わせ", 引数)
    assert r.returncode == 1 and 壊れた not in r.stderr, (r.returncode, r.stderr)


# 4. 公開の写しの道具 scripts/public_mirror.py は公開の写しへ持っていかない＝その試験も持っていかない tests/test_公開版へ出す.py に置く


# 5. 法の表の見張り 道具/法の表の見張り.py（呼び口は引数を受けない＝置き場は引く口の既定を注入で差し替える）
def _置き場を替える(置き場: Path) -> str:
    return f"import 芯.計算.引く口 as _引く口\nfrom pathlib import Path as _P\n_引く口.既定の置き場 = _P({str(置き場)!r})\n"


def test_法の表の見張り_壊れたら2_知らせは1(tmp_path):
    道具 = str(根 / "道具" / "法の表の見張り.py")
    壊れ = tmp_path / "壊れ"
    壊れ.mkdir()
    (壊れ / "壊れた表.json").write_text("{ここは JSON でない", encoding="utf-8")
    _壊れた2(_回す(_置き場を替える(壊れ), 道具, []))
    # 意味のある 1（挙げた物が在る）: 次の改定の欄が無い表
    良い = tmp_path / "良い"
    良い.mkdir()
    元 = next(p for p in sorted((根 / "法の表").glob("*.json")))
    表 = json.loads(元.read_text(encoding="utf-8"))
    表.pop("次の改定", None)
    (良い / 元.name).write_text(json.dumps(表, ensure_ascii=False), encoding="utf-8")
    r = _回す(_置き場を替える(良い), 道具, [])
    assert r.returncode == 1 and 壊れた not in r.stderr, (r.returncode, r.stdout, r.stderr)
    # 引数を渡すのは使い方の誤り＝2（argparse）。結果の 1 と混ぜない
    assert _回す("", 道具, ["--日", "2026-11-18"]).returncode == 2


# 6. Python の版の照らし scripts/check_python_version.py
def test_Pythonの版の照らし_壊れたら2():
    道具 = str(根 / "scripts" / "check_python_version.py")
    _壊れた2(_回す(読む手を壊す, 道具, [__file__]))
    # 子が読めない file を挙げずに落ちた（子の故障）も 2＝「読めない .py が在る」の 1 と混ぜない
    子を壊す = """
import subprocess
_元 = subprocess.run
def _子だけ壊す(cmd, *a, **k):
    if "-c" in cmd and k.get("input") is not None:
        return subprocess.CompletedProcess(cmd, 1, b"", b"Traceback: \\xe6\\xb3\\xa8\\xe5\\x85\\xa5")
    return _元(cmd, *a, **k)
subprocess.run = _子だけ壊す
"""
    r = _回す(子を壊す, 道具, [__file__])
    assert r.returncode == 2 and "照らしが壊れた" in r.stdout, (r.returncode, r.stdout, r.stderr)


def test_検査の入口は版の照らしの2を道具が働けないと出す(tmp_path):
    複製 = tmp_path / "r"
    (複製 / "scripts").mkdir(parents=True)
    (複製 / "tests").mkdir()
    shutil.copy(根 / "scripts" / "check_all.sh", 複製 / "scripts" / "check_all.sh")
    (複製 / "scripts" / "check_python_version.py").write_text(
        "import sys\nprint('赤: 作り物の故障')\nsys.exit(2)\n", encoding="utf-8")
    r = subprocess.run(["bash", str(複製 / "scripts" / "check_all.sh")], capture_output=True, text=True, timeout=120)
    最後 = r.stdout.strip().splitlines()[-1]
    assert r.returncode == 2 and 最後.startswith("赤:") and "働けない" in 最後, (r.returncode, r.stdout)
    (複製 / "scripts" / "check_python_version.py").write_text(
        "import sys\nprint('赤: 作り物の読めない .py')\nsys.exit(1)\n", encoding="utf-8")
    r = subprocess.run(["bash", str(複製 / "scripts" / "check_all.sh")], capture_output=True, text=True, timeout=120)
    assert r.returncode == 1 and r.stdout.strip().splitlines()[-1] == "赤: 作り物の読めない .py", r.stdout


# 7. オーナーへの文の照らし plugins/payroll-agent/bin/オーナーへの文の照らし.py
def test_オーナーへの文の照らし_壊れたら2_当たりは数でなく1():
    道具 = str(根 / "plugins" / "payroll-agent" / "bin" / "オーナーへの文の照らし.py")
    注入 = """
import sys
class _壊れた入力:
    def read(self, *a):
        raise RuntimeError("注入した故障")
sys.stdin = _壊れた入力()
"""
    _壊れた2(_回す(注入, 道具, ["--パック", str(根)]))
    r = _回す("", 道具, ["--パック", str(根)], 入力="検算が合っているか見て。原本の読み方も教えて")
    assert r.returncode == 1 and len([l for l in r.stdout.splitlines() if l.strip()]) >= 1, (r.returncode, r.stdout)
    assert _回す("", 道具, ["--パック", str(根)], 入力="").returncode == 0


# 8. 給与の見張りの hook plugins/payroll-agent/hooks/見張り.py（決定の 7 つの外・同じ原因の台帳の行）
# PreToolUse の hook は終わりの値 1 を「止めない誤り」として道具の呼び出しを通す＝落ちた回が黙って通る。
# 見る道具（GitHub の道具と add_repo）で入力が読めなければ止める（deny）・選択肢の画面の照らしが落ちた時は止めずに「壊れた」と知らせる。
def _部品を壊す(名: str, 読めない: bool = False) -> str:
    if 読めない:   # import そのものが落ちる
        return f"import sys\nsys.modules[{名!r}] = None\n"
    return (f"import sys, types\n_m = types.ModuleType({名!r})\n"
            "def _壊す(*a, **k):\n    raise RuntimeError('注入した故障')\n"
            "_m.__getattr__ = lambda n: _壊す\n"
            f"sys.modules[{名!r}] = _m\n")


def test_見張りのhook_落ちても1で通さない():
    道具 = str(根 / "plugins" / "payroll-agent" / "hooks" / "見張り.py")
    書く = json.dumps({"tool_name": "mcp__github__push_files", "tool_input": {"repo": "payroll-pack"}})
    問い = json.dumps({"tool_name": "AskUserQuestion", "tool_input": {"questions": []}})
    読む = json.dumps({"tool_name": "Read", "tool_input": {}})
    env = {"PAYROLL_PACK_DIR": str(根)}
    for 前置き in (_部品を壊す("パックの場所"), _部品を壊す("パックの場所", 読めない=True)):
        # repo の見張りはパックの場所に頼らない: 部品が落ちてもパックの repo は止める
        r = _回す(前置き, 道具, [], 入力=書く, env=env)
        assert r.returncode == 0 and '"deny"' in r.stdout, (r.returncode, r.stdout, r.stderr)
        # 選択肢の画面の照らしが落ちた: 止めずに、照らしていないと知らせる
        r = _回す(前置き, 道具, [], 入力=問い, env=env)
        assert r.returncode == 0 and "additionalContext" in r.stdout and "見張りが壊れた" in r.stdout, (r.returncode, r.stdout, r.stderr)
        # 見ない道具は今どおり何もしない
        r = _回す(前置き, 道具, [], 入力=読む, env=env)
        assert r.returncode == 0 and r.stdout == "", (r.returncode, r.stdout, r.stderr)
    # 捕まえ残し（知らせる手そのものが落ちる）は 2＝Claude Code が止める
    r = _回す("import json\n_元 = json.dumps\ndef _壊す(*a, **k):\n    raise RuntimeError('注入した故障')\njson.dumps = _壊す\n",
            道具, [], 入力="JSON でない入力", env=env)   # 読めない入力＝止める道（_拒む）で知らせる手が落ちる
    _壊れた2(r)
