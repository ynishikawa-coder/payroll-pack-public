# 直す人のための決まり

payroll-pack は、2 つのアカウント（Javis＝ynishikawa-coder・UTC＝sharekeiri-gif〔共同編集者〕）の窓が直し・試し・版を出す repo です。
枝・PR・レビュー・main へ入れる・版の印の決まりは、土台 [agent-foundation-public](https://github.com/ynishikawa-coder/agent-foundation-public) の CONTRIBUTING.md（読む版は `.github/workflows/土台の版.json` の 1 か所）に従います。ここには給与のパックだけの違いを書きます。

## 1. 枝と PR
- 枝・1 枝 = 1 PR = 1 窓・PR の型は土台 §1 のとおり。PR の本文はこの repo の `.github/pull_request_template.md` の型で書く。
- 使う側に関わる変わった事（`互換が切れる:` の行を含む）の正本は、その PR の `CHANGELOG.d/` の断片 1 つ（版を出す PR は `CHANGELOG.md` の版の節）。PR の本文は行の数と中身を写さず、断片の path も書かない（断片の名は枝の名で決まり〔`CHANGELOG.d/README.md`。`claude/<日付>-` の枝は `tests/test_骨.py` が名の違いを赤にする〕、PR の差分に在る＝本文に書くと枝の名の写しになり、打ち間違い・付け忘れを照らす所が要る。写すと断片とずれ、本文の数と実際の行が食い違う＝#359）。
- どちらのアカウントの窓も、この repo へ直に枝を push し PR を出す（fork しない）。

## 2. レビューと main へ入れる
- レビュー（誰が・何を確かめるか）と main へ入れる条件は、土台の核 §7 のとおり（ここに写さない）。判定の形は土台の skill `review-pr`（`plugins/checker/skills/review-pr`）。どちらのアカウントの PR も同じ。
- 給与のパックだけの足し: レビューは土台の skill `review-pr` で見る所に加えて、線の正本 `docs/設計/入れてよい物.md` に照らす（PR の「種類」が製品・顧客・移行なら赤）。

## 3. 置かない物
- 入れてよい物と入れない物の線は `docs/設計/入れてよい物.md` が正本（ここに写さない）。
- **顧客の物**: 顧客の名・語・マスタ・台帳・実の勤怠は repo に置かず、各事務所の Drive に置く。試験に顧客の値を写さない。秘密を置かないことは土台の核 §1-2 のとおり（顧客の Drive の ID も秘密に数える）。

## 4. 試験
- 入口は `bash scripts/check_all.sh`（土台の公開の検査のあと `python3 -m pytest -q`）。最後の行が `緑:` なら通り、`赤:` なら落ち。pytest が落ちた時は最後の行の手前に `落ちた試験: <名>`・`出力の全部: <file>` が出る（連絡に添える）。CI（`.github/workflows/ci.yml`）も同じ入口を回す。
- **試験は作り物の値だけで小さく置く**。試験は `tests/` に、直す物の dir と同じ名の束で置く（`tests/計算/` は `芯/計算/` の試験・`tests/入口/` は `入口/` の試験…。束の一覧と中身は `tests/README.md`）。置いてよい試験は次の 3 種:
  1. 規律・道具の自分の試験（`tests/` の直下。例 `tests/test_骨.py`・`tests/test_芯の境.py`）
  2. 部品ごとの試験（各束。作り物の値で、部品の決まりと、わざと誤りを入れて拒むかを見る。法の表を引いた値の例・回帰の見張りは `tests/作り物/`）
  3. 答え合わせの道具の試験（`tests/答え合わせ/`。照らしの道具そのものの試験で、芯から呼ばれないことも見る）
- 作り物の会社の一揃い（社員・マスタ・勤怠の束を丸ごと）は repo に置かない。各試験は要る行だけを作り物で持つ。会社ごとの確かめは各事務所の Drive の側で行う。
- **過去の正解に合わせる答え合わせは開発の道具に置き、芯に入れない**（`道具/` か `tests/`。`芯/` の計算は答えを見ない）。芯が標準の道具と芯の中の外を import しないことは `tests/test_芯の境.py` が見る。
- 確認ページの型と検査（土台の qa-html の `check.mjs`）は repo に写さず直に読む（窓は入った plugin docs-kit・CI は `QA_HTML_CHECK`）。試験は node と一緒に在れば当たる（手元で無ければ skip）。CI は ci.yml が土台の main の先端から取って渡し、無ければ赤（`tests/確認ページ/test_確認ページの検査の道具.py`）。

## 5. 版
- 版の出し方と印（タグ）は土台の決まりに従い、この repo の版の名と CHANGELOG の形は `docs/版の出し方.md` に書く。
- 記録は PR ごとに `CHANGELOG.d/<YYYYMMDD>-<話題>.txt` を 1 つ足して書く（`CHANGELOG.md` へは足さない・書き方は `CHANGELOG.d/README.md`）。殻が渡す形・呼び口・型の版が変わる PR は、その行の頭に `互換が切れる:` を書く（両側が latest を読むので、この印で気付く。見分け方は `docs/版の出し方.md`）。

## 6. 設計の目次
- `docs/設計/README.md` が設計書と部品の置き場の目次。file や dir を足したら、同じ PR で目次に行を足す（行の物が無いと骨の自己検査が赤になる）。
