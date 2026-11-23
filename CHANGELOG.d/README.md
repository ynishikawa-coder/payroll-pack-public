# 変更の記録の書き方（CHANGELOG.d/）

使う側に関係する変更は、PR ごとに **この dir へ自分の file を 1 つ足す**。全部の PR が `CHANGELOG.md` の「未リリース」の末尾へ行を足すと、1 本入るたびに残りの PR が全部ぶつかり、git の自動の取り込みが行を出した版の節へ紛れ込ませる事も起きた（#249・#252）。行を同じ file の同じ所に集めない。

- 名: `<YYYYMMDD>-<話題>.txt`。自分の枝 `claude/<YYYYMMDD>-<話題>` と同じにする（1 枝 = 1 file。他の枝の file は触らない）。枝の名は GitHub の上で 1 つに決まるので、2 本の PR が同じ file を作らない。AI の窓の枝（`claude/<YYYYMMDD>-<話題>`）で足す断片がこの名でなければ赤（`tests/test_骨.py`）。
- 中身: 1 項を 1 行で `- ` から書く（1 つの file に何行でもよい）。殻が渡す形・呼び口・型の版が変わる行は頭を `- 互換が切れる: ` にする（見分け方は `docs/版の出し方.md`）。
- 合流の後に直す時も、その file を直す（版を出すまでは断片のまま）。
- `CHANGELOG.md` の「未リリース」は決まった 1 行だけ（文の正本は `scripts/changelog.py` の `UNRELEASED_TEXT`）。行を足すと赤。
- 版を出す PR だけが `python3 scripts/changelog.py 版 vX.Y.Z YYYY-MM-DD` で断片を束ね（main に入った順・新しい物が上）、`CHANGELOG.md` に版の節を作り、断片を消す。版の節の形・印の打ち方（`tag.yml`）は今までと同じ。
- 断片が 1 つでも在る中身は版の印の中身でない（`出口/証明.py` の `パックの版` が `+未リリース` を付ける）。
- 形は `python3 scripts/changelog.py check` が照らす（終わりの値 0 緑・1 赤・2 道具が働けない＝結果ではない）（`tests/test_骨.py` が回す）。未リリースの行の全部は `python3 scripts/changelog.py` で読む。

## この形の前に枝を切った PR が main を取り込む時

`git merge origin/main` で `CHANGELOG.md` がぶつかったら、自分の行を自分の断片へ移す（`adopt` は「すでに在る行」を取り込む先〔既定 `origin/main`〕の `CHANGELOG.md` と断片から読む。ぶつかった途中の作業中の `CHANGELOG.md` は読まない）:

```
git fetch origin main
git show HEAD:CHANGELOG.md | python3 scripts/changelog.py adopt - CHANGELOG.d/<断片の名>.txt
git checkout origin/main -- CHANGELOG.md
python3 scripts/changelog.py check
```

- `adopt` は移した行を 1 行ずつ出す。自分の行の数と合うかを見る（0 行なら、自分の行が既に main の断片に在るか、取り込む先が違う）。
- 断片の名: 枝が `claude/<YYYYMMDD>-<話題>` なら `<YYYYMMDD>-<話題>.txt`。名に日付の無い枝（人の枝・前からの枝）は、取り込む日の日付と枝の名の最後の `/` の後を `-` でつないだ名にする（例 枝 `claude/作り物の話題` を 2099-01-02 に取り込むなら `20990102-作り物の話題.txt`。空白は `-` に替える）。
