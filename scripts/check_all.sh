#!/usr/bin/env bash
# payroll-pack の検査の入口。CI も手元も同じこれを回す。
# 最後の行が「緑: …」なら通り、「赤: …」なら落ち。落ちた時は手前に「落ちた試験: <名>」を 1 行ずつ出す。
# 引数を渡せばその試験だけを回す（既定は tests/ の全部）。bash の変数の名は英字（bash は日本語の名を受けない）。
set -u
cd "$(dirname "$0")/.."

# 公開の検査（土台 agent-foundation-public の public-guard/guard.py）を repo の中身の全部に当てる。
# 版の印は .github/workflows/土台の版.json の「土台」（1 か所）。本体は repo の外へ版ごとに取る。
# 顧客の語の照合は版を運ぶ時（鍵を持つ workflow）が受け持つ＝ここでは GITHUB_ACTIONS を外して回す。
af_ref=$(python3 -c 'import json; print(json.load(open(".github/workflows/土台の版.json", encoding="utf-8"))["土台"])') \
  || { echo "赤: 土台の版の印（.github/workflows/土台の版.json）が読めない"; exit 1; }
af_dir="${XDG_CACHE_HOME:-$HOME/.cache}/payroll-pack/agent-foundation-public-$af_ref"
if [ ! -f "$af_dir/public-guard/guard.py" ]; then
  rm -rf "$af_dir"; mkdir -p "$(dirname "$af_dir")"
  git clone -q --depth 1 --branch "$af_ref" https://github.com/ynishikawa-coder/agent-foundation-public "$af_dir" \
    || { echo "赤: 公開の検査の本体（土台 $af_ref）を取れない"; exit 1; }
fi
if ! env -u GITHUB_ACTIONS -u GITHUB_EVENT_PATH python3 "$af_dir/public-guard/guard.py" --repo . --files-only; then
  echo "赤: 公開の検査が通らない（上の出力を見る）"
  exit 1
fi
echo "公開の検査（土台 $af_ref・中身の全部）: 当たり 0"

log=$(mktemp "${TMPDIR:-/tmp}/payroll-pack-check_all.XXXXXX")
if [ "$#" -eq 0 ]; then set -- tests/; fi
python3 -m pytest -q -rfE "$@" 2>&1 | tee "$log"
rc=${PIPESTATUS[0]}
if [ "$rc" -eq 0 ]; then
  rm -f "$log"
  echo "緑: 全部の検査が通った"
else
  grep -E '^(FAILED|ERROR) ' "$log" | sed -E 's/^(FAILED|ERROR) ([^ ]+).*/落ちた試験: \2/'
  echo "出力の全部: $log"
  echo "赤: pytest が落ちた（終了の値 $rc）"
fi
exit "$rc"
