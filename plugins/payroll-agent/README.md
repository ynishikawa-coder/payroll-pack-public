# payroll-agent — 給与エージェントの部分（plugin）

計算のパック（この repo の残りの全部）を使って給与の仕事をするエージェントの、手順と決まりと照らし。両側の窓が同じ物を窓を開く前に入れて使い、片方だけが育たないようにする。各社の側に残すのは環境の設定と、`口の一覧.md` の口だけ。

## 置く物

| 物 | 中身 | 窓に届く道 |
|---|---|---|
| `決まり.md` | 給与の窓が常に守る線 | `scripts/差し込む.py inject` を SessionStart の hook が呼んで差し込む（hook の登録は同じ plugin の hooks の dir に置く） |
| `skills/payroll-steps/SKILL.md` | 毎月の手順（0 初期設定・1 材料をそろえる・2 給与計算） | skill（呼び名 `payroll-agent:payroll-steps`） |
| `口の一覧.md` | 各社の側が満たす口（名・渡す物・返す物・守る事） | 手順と決まりが口の名で指す |
| `hooks/`・`bin/` | 照らし（出す前の照らし・止める見張り・問いの照らし） | hook と道具 |
| `scripts/差し込む.py` | 決まりを差し込む口と、量の上限の照らし | hook が呼ぶ |

## 届け方と版
- marketplace はこの repo の根の `.claude-plugin/marketplace.json`（名 `payroll-pack`）。土台の plugin と同じ届け方で、窓の環境の setup script が版の印を決めて user scope に入れる（手順は `docs/版の出し方.md` の「給与エージェントの plugin」）。
- 版はパックの版の印そのもの。`.claude-plugin/plugin.json` と根の `.claude-plugin/marketplace.json` に版を書かない（2 か所に版を持たない・書くと試験が赤）。
- 公開版へはこの dir も `.claude-plugin/` もそのまま載る（`scripts/public_mirror.py` の持っていかない物に入れない・試験が見る）。

## 線
- 中に製品の名・側の名・環境の道具の名・置き場の在り処を書かない（`tests/test_給与エージェントの器.py` が赤。束は `tests/data/`）。線の正本は `docs/設計/入れてよい物.md`。
- 計算の設計を写さない。手順は計算のパックの docs と部品の README を指すだけ。
