#!/usr/bin/env bash
# payroll-pack の検査の入口。CI も手元も同じこれを回す。
# 最後の行が「緑: …」なら通り、「赤: …」なら落ち。
set -u
cd "$(dirname "$0")/.."

python3 -m pytest -q tests/
rc=$?

if [ "$rc" -eq 0 ]; then
  echo "緑: 全部の検査が通った"
else
  echo "赤: pytest が落ちた（終了の値 $rc）"
fi
exit "$rc"
