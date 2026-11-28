# payroll-agent — 給与エージェントの部分（plugin）

計算のパック（この repo の残りの全部）を使って給与の仕事をするエージェントの、手順と決まりと照らし。両側の窓が同じ物を窓を開く前に入れて使い、片方だけが育たないようにする。各社の側に残すのは環境の設定と、`口の一覧.md` の口だけ。パックは Drive の口を持ち、鍵と置き場の根の id は給与の窓が環境から渡す（repo に置かない）。出す物と管理表はパックの 1 命令（出口/出す.py）で書く。

## 置く物

| 物 | 中身 | 窓に届く道 |
|---|---|---|
| `決まり.md` | 給与の窓が常に守る線 | `scripts/差し込む.py inject` を SessionStart の hook が呼んで差し込む（hook の登録は同じ plugin の hooks の dir に置く） |
| `skills/payroll-steps/SKILL.md` | 毎月の手順（0 初期設定・1 材料をそろえる・2 給与計算・3 突き合わせと納品の 4 段と 済み） | skill（呼び名 `payroll-agent:payroll-steps`） |
| `口の一覧.md` | 各社の側が満たす口（名・渡す物・返す物・守る事） | 手順と決まりが口の名で指す |
| `hooks/` | 起動時の差し込みの登録（SessionStart だけ） | hook |
| `scripts/差し込む.py` | 決まりを差し込む口 | hook が呼ぶ |

## 届け方と版
- marketplace はこの repo の根の `.claude-plugin/marketplace.json`（名 `payroll-pack`）。土台の plugin と同じ届け方で、窓の環境の setup script が版の印を決めて user scope に入れる（手順は `docs/版の出し方.md` の「給与エージェントの plugin」）。
- 版はパックの版の印そのもの。`.claude-plugin/plugin.json` と根の `.claude-plugin/marketplace.json` に版を書かない（2 か所に版を持たない・書くと試験が赤）。
- 公開版へはこの dir も `.claude-plugin/` もそのまま載る（公開版へ出す道具の持っていかない物に入れない・試験 tests/test_公開版へ出す.py が見る。その道具と試験は公開版へ載らないので、ここでは path を引かない）。

## 線
- 中に製品の名・側の名・環境の道具の名・置き場の在り処を書かない。線の正本は `docs/設計/入れてよい物.md`（レビューで照らす）。
- 計算の設計を写さない。手順は計算のパックの docs と部品の README を指すだけ。
