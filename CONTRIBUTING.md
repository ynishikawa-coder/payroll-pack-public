# 直す人のための決まり

payroll-pack は、2 つのアカウント（Javis＝ynishikawa-coder・UTC＝sharekeiri-gif〔共同編集者〕）の窓が直し・試し・版を出す repo です。
枝・PR・レビュー・main へ入れる・版の印の決まりは、土台 [agent-foundation-public](https://github.com/ynishikawa-coder/agent-foundation-public) の CONTRIBUTING.md（読む版は `.github/workflows/tag.yml` の `ref` の 1 か所）に従います。ここには給与のパックだけの違いを書きます。

## 1. 枝と PR
- 枝・1 枝 = 1 PR = 1 窓・PR の型は土台 §1 のとおり。PR の本文はこの repo の `.github/pull_request_template.md` の型で書く。
- どちらのアカウントの窓も、この repo へ直に枝を push し PR を出す（fork しない）。

## 2. レビューと main へ入れる
- レビューは書いた窓と別の窓がし、判定の形は土台の skill `review-pr`（`plugins/checker/skills/review-pr`）に従う。
- main へ入れるのは **Javis 側の親窓** だけ（土台 §3。どちらのアカウントの PR も同じ）。
- レビューは土台の skill `review-pr` で見る所に加えて、線の正本 `docs/設計/入れてよい物.md` に照らす（PR の「種類」が製品・顧客・移行なら赤）。
- 線の正本を変える PR と、Javis・UTC の窓で線の解釈が割れた PR は、green だけでは合流しない。オーナーの合意 1 つを待つ（オーナーは 1 人。Javis の窓・UTC の窓・連絡板〔ynishikawa-coder/agent-foundation の issue #2〕のどこで出した合意でもよい）。合意を得た PR は本文の頭に、合意の日と出した所（窓の session か連絡板）を書く ⟦鍵:給与計算/線が割れた時はオーナーの合意 1 つ⟧。この決まりの正本はここ（線の正本 §5 の 4 はここを指す）。

## 3. 置かない物
- 入れてよい物と入れない物の線は `docs/設計/入れてよい物.md` が正本（ここに写さない）。
- **顧客の物**: 顧客の名・語・マスタ・台帳・実の勤怠は repo に置かず、各事務所の Drive に置く。試験に顧客の値を写さない。秘密を置かないことは土台の核 §1-2 のとおり（顧客の Drive の ID も秘密に数える）。
- 顧客の語の検査（`tests/test_骨.py`）は、語の束を repo に持たない。CI や手元の環境から渡す:
  - `PAYROLL_NG_WORDS_FILE`（1 行 1 語の file の path）または `PAYROLL_NG_WORDS`（改行区切りの語）
  - どちらも無ければその検査は skip になる（落ちない）。語の束を repo に commit しない。

## 4. 試験
- 入口は `bash scripts/check_all.sh`（中で `python3 -m pytest -q tests/`）。最後の行が `緑:` なら通り、`赤:` なら落ち。CI（`.github/workflows/ci.yml`）も同じ入口を回す。
- **試験は小さく置く**。repo に置く試験は次の 3 つだけ:
  1. 規律・道具の自分の試験（`tests/` の直下。例 `tests/test_骨.py`）
  2. 作り物の **国の率や表の例**（`tests/作り物/`。法の表を引いた値が合うかの小さな例）
  3. 作り物の **回帰の見張り**（`tests/作り物/`。直した所の外の結果が変わらないことを見る）
- 作り物の会社の一揃い（社員・マスタ・勤怠の束）は repo に置かない。会社ごとの確かめは各事務所の Drive の側で行う。
- **過去の正解に合わせる答え合わせは開発の道具に置き、芯に入れない**（`道具/` か `tests/`。`芯/` の計算は答えを見ない）。

## 5. 版
- 版の出し方と印（タグ）は土台の決まりに従い、この repo の版の名と CHANGELOG の形は `docs/版の出し方.md` に書く。
- 殻が渡す形・呼び口・型の版が変わる PR は、CHANGELOG の行の頭に `互換が切れる:` を書く（両側が latest を読むので、この印で気付く。見分け方は `docs/版の出し方.md`）。

## 6. 設計の目次
- `docs/設計/README.md` が設計書と部品の置き場の目次。file や dir を足したら、同じ PR で目次に行を足す（行の物が無いと骨の自己検査が赤になる）。
