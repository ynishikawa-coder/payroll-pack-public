#!/usr/bin/env bash
# payroll-pack の検査の入口。CI も手元も同じこれを回す。
# 最後の行が「緑: …」なら通り、「赤: …」なら落ち。
# 落ちた時は、最後の行の手前に「落ちた試験: <名>」を 1 行ずつと「回した環境: …」「出力の全部: <file>」を出す
# （1 回目だけ落ちて打ち直すと通った時も、名と環境が出力の終わりに残る）。
# 引数を渡せばその試験だけを回す（既定は tests/ の全部）。bash の変数の名は英字（bash は日本語の名を受けない）。
set -u
cd "$(dirname "$0")/.."

# 回す前の様子（1 回目か＝前に回した時の __pycache__ が在るか・浅い clone か・確認ページの検査の道具を当てるか）
if find tests -type d -name __pycache__ -print -quit 2>/dev/null | grep -q .; then prev="在る"; else prev="無い（1 回目）"; fi
shallow=$(git rev-parse --is-shallow-repository 2>/dev/null || echo 不明)
qa=$([ -n "${QA_HTML_CHECK:-}" ] && echo 在る || echo 無い)

# 最初の段: CI と同じ版の Python の文法で repo の全部の .py が読めるか（版の正本は .github/workflows/ci.yml・写さない）。
# 手元の Python の版が CI と違うと、手元の緑が CI の緑を約束しないため（例 名の「・」は 3.13 で通り 3.12 で SyntaxError）。
ver_out=$(python3 scripts/check_python_version.py 2>&1); ver_rc=$?
ci_py=$(printf '%s\n' "$ver_out" | sed -n 's/^PYTHON=//p')
# 試験も CI の版の python で回す（標準の道具の違いも手元で出る）。その python に pytest が無い時だけ python3 で回し、そう出す
if [ -n "$ci_py" ] && "$ci_py" -c 'import pytest' >/dev/null 2>&1; then py="$ci_py"; else py=python3; fi
env_line="python $("$py" -c 'import sys; print(sys.version.split()[0])' 2>/dev/null)・pytest $("$py" -c 'import pytest; print(pytest.__version__)' 2>/dev/null)・浅い clone=${shallow}・前の回の __pycache__=${prev}・QA_HTML_CHECK=${qa}・時刻 $(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M') 日本時間"
# 照らしの終わりの値: 0 通り／1 読めない .py が在る（赤）／2 照らしが働けない・壊れた（結果ではない＝道具か環境を直す）。
# 2 は 1 と混ぜずに「道具が働けない」と出し、入口も 2 で抜ける（どちらも通さない）。
if [ "$ver_rc" -ne 0 ]; then
  printf '%s\n' "$ver_out" | sed '$d'
  echo "回した環境: $env_line"
  if [ "$ver_rc" -eq 1 ]; then
    printf '%s\n' "$ver_out" | tail -n 1
    exit 1
  fi
  echo "赤: Python の版の照らしが働けない・壊れた（終わりの値 ${ver_rc}＝読めない .py の結果ではない。上の訳で道具か環境を直す）: $(printf '%s\n' "$ver_out" | tail -n 1)"
  exit 2
fi
printf '%s\n' "$ver_out" | grep -v '^PYTHON='
if [ "$py" != "$ci_py" ]; then
  echo "知らせ: 試験は $(python3 -c 'import sys; print(sys.version.split()[0])') で回す（CI の版の python $ci_py に pytest が無い＝標準の道具の違いは CI で出る。入れれば同じ版で回す）"
fi

# 次の段: 公開の検査（土台 agent-foundation-public の public-guard/guard.py）を repo の中身の全部に当てる。
# 公開の写し（payroll-pack-public）へ版を運ぶ時に同じ検査が当たる＝当たる字は手元と CI でここで赤にし、main に入れない。
# 版の印は .github/workflows/土台の版.json の「土台」を直に読む（ci.yml・public-mirror.yml と同じ 1 か所。ここに印を書かない）。
# 本体は repo に写さず、版ごとに repo の外の置き場へ取る（PAYROLL_PUBLIC_GUARD に guard.py の path を渡せば取らずにそれを使う）。
# 取れない・読めない時は黙って通さず赤。顧客の語の照合は版を運ぶ時（鍵を持つ workflow）が受け持つ＝ここでは
# GITHUB_ACTIONS を外して回す（CI でも顧客の語が無いことで止めない。AF_DENY_BUNDLE・AF_DENY_WORDS が環境に在れば照らす）。
# 終わりの値は分ける: 当たりがある（guard.py の 1）は 1。版の印が読めない・本体を取れない・guard.py が働けない（2）・
# 照らしていない（3）・そのほかの値は「当たり」ではない＝2（道具が働けない。1 に寄せると落ちた回を当たりと読む・決定 420a40dc）。
guard_red() {
  [ -n "${1:-}" ] && printf '%s\n' "$1"
  echo "回した環境: $env_line"
  echo "赤: 公開の検査に当たりがある（公開の写しへ版を運べない。当たる字を当たらない形に直す）"
  exit 1
}
guard_broken() {
  [ -n "${1:-}" ] && printf '%s\n' "$1"
  echo "回した環境: $env_line"
  echo "赤: 公開の検査が働けない・照らしていない（${2:-回せない}＝当たりの結果ではない。上の訳で道具か環境を直す）"
  exit 2
}
af_ref=$("$py" - <<'PY' 2>&1
import json, re, sys
from pathlib import Path
p = Path(".github/workflows/土台の版.json")
v = json.loads(p.read_text(encoding="utf-8")).get("土台", "") if p.exists() else ""
if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", str(v)):
    sys.exit(f"✗ 土台の版の印が読めない（.github/workflows/土台の版.json の「土台」）: {v!r}")
print(v)
PY
) || guard_broken "$af_ref" "土台の版の印が読めない"
guard_py="${PAYROLL_PUBLIC_GUARD:-}"
if [ -z "$guard_py" ]; then
  af_dir="${PAYROLL_GUARD_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/payroll-pack}/agent-foundation-public-$af_ref"
  if [ ! -f "$af_dir/public-guard/guard.py" ]; then
    mkdir -p "$(dirname "$af_dir")"
    af_tmp=$(mktemp -d "$af_dir.XXXXXX")
    if git clone -q --depth 1 --branch "$af_ref" https://github.com/ynishikawa-coder/agent-foundation-public "$af_tmp" 2>/dev/null \
       && [ -f "$af_tmp/public-guard/guard.py" ]; then
      rm -rf "$af_dir"; mv "$af_tmp" "$af_dir" 2>/dev/null || rm -rf "$af_tmp"
    else
      rm -rf "$af_tmp"
      guard_broken "✗ 公開の検査の本体（土台 agent-foundation-public $af_ref の public-guard/guard.py）を取れない（網・印を見る。PAYROLL_PUBLIC_GUARD で path を渡してもよい）" "本体を取れない"
    fi
  fi
  guard_py="$af_dir/public-guard/guard.py"
fi
guard_out=$(env -u GITHUB_ACTIONS -u GITHUB_EVENT_PATH "$py" "$guard_py" --repo . --files-only 2>&1); guard_rc=$?
if [ "$guard_rc" -eq 1 ]; then guard_red "$guard_out"; fi
if [ "$guard_rc" -ne 0 ]; then guard_broken "$guard_out" "guard.py の終わりの値 ${guard_rc}"; fi
echo "公開の検査（土台 $af_ref・中身の全部）: 当たり 0"

log=$(mktemp "${TMPDIR:-/tmp}/payroll-pack-check_all.XXXXXX")
if [ "$#" -eq 0 ]; then set -- tests/; fi
"$py" -m pytest -q -rfE "$@" 2>&1 | tee "$log"
rc=${PIPESTATUS[0]}

if [ "$rc" -eq 0 ]; then
  rm -f "$log"
  echo "緑: 全部の検査が通った"
else
  # 試験の名の \uXXXX（pytest が引数の字を逃がした形）は字に戻す
  names=$(grep -E '^(FAILED|ERROR) ' "$log" | sed -E 's/^(FAILED|ERROR) ([^ ]+).*/\2/' \
          | "$py" -c 'import re, sys; [print(re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), l.rstrip("\n"))) for l in sys.stdin]')
  if [ -n "$names" ]; then
    while IFS= read -r n; do echo "落ちた試験: $n"; done <<< "$names"
    count=$(printf '%s\n' "$names" | grep -c .)
  else
    echo "落ちた試験: 名が取れない（pytest が試験を集める前か途中で止まった＝出力の全部を見る）"
    count=0
  fi
  echo "回した環境: $env_line"
  echo "出力の全部: $log"
  # pytest の終わりの値: 1＝落ちた試験が在る／2＝止められた／3＝pytest の中の故障／4＝使い方の誤り／5＝試験が 1 つも無い。
  # 1 のほかは試験の結果でなく道具が働けない＝そう出す（落ちた試験と混ぜない）
  if [ "$rc" -eq 1 ]; then
    echo "赤: pytest が落ちた（終了の値 $rc・落ちた試験 $count 個）"
  else
    echo "赤: pytest が働けない（終了の値 $rc＝試験の結果ではない・2 止められた／3 中の故障／4 使い方の誤り／5 試験が無い。出力の全部を見る）"
  fi
fi
exit "$rc"
