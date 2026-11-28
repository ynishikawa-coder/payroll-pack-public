"""置き場を引く — 事務所の根から、事務所の物（名で引く）と会社の物（事務所の設定「置き場」の表で引く）の id を引く。

正本は docs/設計/Drive の型.md §8: 会社の物の id は事務所の設定「3_置き場」タブだけが持つ（列 顧客ID・会社・組・物・ID）。
事務所の物（マスタ・事務所の設定・管理表・質問と回答 など・型 39）は事務所の根の直下に在り「置き場」に行を持たず、根から木の名で引く。
マスタは事務所に 1 冊で全社の行を持つ＝マスタを読む が 顧客ID で絞り、Drive の列（顧客ID・社員ID）を道具の内の列（会社・NO）へ読み替える。
フォルダ・シート・タブの名は直に書かず 初期設定/型の口.py から引く。表の照らし（重なり・空・一覧との違い）は
型の口.置き場の登録の赤 の 1 か所に任せ、赤が 1 つでも在れば選ばずに止める。
"""
from __future__ import annotations

import os

from drive口 import Drive口, 根の変数名の既定
from 初期設定 import 型の口

設定の役 = "事務所の設定"


class 引けない(LookupError):
    """置き場が引けない（無い・重なる・表が型の決まりに合わない）。訳に id の値を入れない。"""


def 根を受け取る(根: str | None = None, *, 根の変数名: str = 根の変数名の既定) -> str:
    """事務所の根の id を、引数（--根）か環境の変数（既定 PAYROLL_OFFICE_ROOT_ID）から受け取る。無ければ止める。"""
    v = (根 or os.environ.get(根の変数名, "")).strip()
    if not v:
        raise 引けない(f"事務所の根の id が無い（引数 --根 か環境の変数 {根の変数名} で渡す）")
    return v


def _ちょうど1つ(口: Drive口, 親id: str, 名: str, どこ: str) -> dict:
    hits = [x for x in 口.子を並べる(親id) if x["name"] == 名]
    if not hits:
        raise 引けない(f"{どこ} に「{名}」が無い")
    if len(hits) > 1:
        raise 引けない(f"{どこ} に「{名}」が {len(hits)} つ在る（どれかを選ばずに止める）")
    return hits[0]


def 事務所の物(口: Drive口, 根id: str) -> dict[str, str]:
    """事務所の根 → {Drive の名: id}。根の直下に在る事務所の物（型の口.物たち("事務所の物")・型 39 は 00_事務所 を挟まない）。
    事務所の設定 は必ず要る（無ければ止める）。ほかの物は在る物だけ返す（同じ名が 2 つ以上なら止める）。"""
    子 = 口.子を並べる(根id)
    out = {}
    for 名 in 型の口.物たち("事務所の物"):
        hits = [x for x in 子 if x["name"] == 名]
        if len(hits) > 1:
            raise 引けない(f"事務所の根 に「{名}」が {len(hits)} つ在る（どれかを選ばずに止める）")
        if hits:
            out[名] = hits[0]["id"]
    if 型の口.Driveの名(設定の役) not in out:
        raise 引けない(f"事務所の根 に「{型の口.Driveの名(設定の役)}」が無い")
    return out


def タブを読む(口: Drive口, シートid: str, シート: str, タブ: str, タブたち: list[str] | None = None) -> list[list]:
    """型のシート（型の口.名 の名・例 台帳_<支給年>）とタブ（役の名）→ Drive のタブの名（型の口.タブの名）で格子を読む。
    タブが無ければ止める。Drive のタブの名を呼ぶ側で組まない（役の名のまま読むと型 39 の 1_社員 などに当たらない）。"""
    名 = 型の口.タブの名(シート, タブ)
    タブたち = 口.タブを並べる(シートid) if タブたち is None else タブたち
    if 名 not in タブたち:
        raise 引けない(f"{型の口.タブの本(シート, タブ)} に「{名}」タブが無い")
    return 口.表を読む(シートid, f"'{名}'!A1:ZZ")


def _登録を読む(口: Drive口, 根id: str) -> tuple[dict[str, str], list[dict], list[dict]]:
    """→ (事務所の物, 置き場の行たち, 会社の一覧の行たち)。表が型の決まりに合わなければ止める。"""
    物 = 事務所の物(口, 根id)
    シートid = 物[型の口.Driveの名(設定の役)]
    タブたち = 口.タブを並べる(シートid)
    格子 = {タブ: タブを読む(口, シートid, 型の口.名(設定の役), タブ, タブたち) for タブ in ("置き場", "会社の一覧")}
    赤 = 型の口.置き場の登録の赤(格子["置き場"], 格子["会社の一覧"])
    if 赤:
        raise 引けない("置き場の表が決まり（Drive の型 §8）に合わない: " + "／".join(f"{t}: {m}" for t, m in 赤))
    置き場, _ = 型の口.登録の表を読む(格子["置き場"], "置き場")
    一覧, _ = 型の口.登録の表を読む(格子["会社の一覧"], "会社の一覧")
    return 物, 置き場, 一覧


def 置き場を引く(口: Drive口, 根id: str) -> dict[str, str]:
    """事務所の設定「置き場」の表の全部 → {"<顧客ID>/<物>": id}（1 つの (顧客ID, 物) に 1 行＝鍵は 1 つに決まる）。"""
    鍵 = 型の口.顧客IDの列()
    _, 置き場, _ = _登録を読む(口, 根id)
    return {f"{r[鍵]}/{r['物']}": r["ID"] for r in 置き場}


def _顧客IDを決める(一覧: list[dict], 会社: str) -> str:
    """会社（顧客ID か会社の呼び名）→ 会社の一覧の顧客ID 1 つ。決まらなければ止める（AI は顧客ID を付けない・Drive の型 §1）。"""
    鍵 = 型の口.顧客IDの列()
    会社 = (会社 or "").strip()
    by_id = [r for r in 一覧 if r[鍵] == 会社]
    if by_id:
        return by_id[0][鍵]
    by_name = [r for r in 一覧 if r["会社"] == 会社]
    if len(by_name) == 1:
        return by_name[0][鍵]
    if not by_name:
        raise 引けない(f"会社「{会社}」が事務所の設定「会社の一覧」に無い（{鍵} か呼び名で渡す）")
    raise 引けない(f"会社「{会社}」が会社の一覧に {len(by_name)} 行在る（{鍵} で渡す）")


def 会社の置き場(口: Drive口, 根id: str, 会社: str) -> dict[str, str]:
    """会社（顧客ID か呼び名）→ {物: id}。
    鍵は「置き場」の列「物」の字（会社の根・1_決まり・台帳_<YYYY>・3_月ごと・8_確認事項・9_履歴・受け取り口 のうち
    登録の在る物）と、事務所の物の名（マスタ・事務所の設定・管理表 など在る物）。両方に同じ名は出ない（9_履歴 は会社の物を返す）。
    "顧客ID"・"会社"・"組" の 3 つの鍵も返す（値は字）。月のフォルダの中（届いた物・出す物）は 月の置き場 で引く。"""
    鍵 = 型の口.顧客IDの列()
    物, 置き場, 一覧 = _登録を読む(口, 根id)
    顧客ID = _顧客IDを決める(一覧, 会社)
    行 = next(r for r in 一覧 if r[鍵] == 顧客ID)
    会社の物 = {r["物"]: r["ID"] for r in 置き場 if r[鍵] == 顧客ID}
    if not 会社の物:
        raise 引けない(f"{鍵}「{顧客ID}」の行が事務所の設定「置き場」に無い")
    out = {k: v for k, v in 物.items() if k not in 会社の物}
    out.update(会社の物)
    out.update({"顧客ID": 顧客ID, "会社": 行["会社"], "組": 行["組"]})
    return out


def 月の置き場(口: Drive口, 月ごとid: str, 月の名: str, *, 作る: bool = False) -> dict[str, str]:
    """3_月ごと の id と月のフォルダの名（`YYYY.MM支給（M月分）`）
    → {月の名: id, 1_届いた物: id, 2_出す物: id}。作る=True なら無い物を作る（同じ名が 2 つ以上なら止める）。"""
    def 引く(親: str, 名: str, どこ: str) -> str:
        hits = [x for x in 口.子を並べる(親) if x["name"] == 名]
        if len(hits) > 1:
            raise 引けない(f"{どこ} に「{名}」が {len(hits)} つ在る（どれかを選ばずに止める）")
        if hits:
            return hits[0]["id"]
        if not 作る:
            raise 引けない(f"{どこ} に「{名}」が無い")
        return 口.フォルダを作る(親, 名)

    月 = 引く(月ごとid, 月の名, 型の口.名("月ごと"))
    out = {月の名: 月}
    for 名 in 型の口.物たち("月の物"):
        out[名] = 引く(月, 名, 月の名)
    return out


def マスタを読む(口: Drive口, 置き場: dict[str, str], タブ: str) -> list[dict]:
    """会社の置き場（会社の置き場 の戻り）とマスタのタブ（役の名・例 社員）→ その会社の行だけ [{道具の内の列: 値}]。
    マスタは事務所に 1 冊（変更の記録 だけは別の本 マスタの変更の記録）。Drive の列（顧客ID・社員ID）で読み、顧客ID で絞り、
    道具の内の列（会社＝会社の呼び名・NO）へ読み替える。見出しに型の列が無ければ止める（足りない列で黙って読まない）。"""
    シート = 型の口.名("マスタ")
    本 = 型の口.タブの本(シート, タブ)
    if 本 not in 置き場:
        raise 引けない(f"事務所の根 に「{本}」が無い")
    格子 = タブを読む(口, 置き場[本], シート, タブ)
    if not 格子:
        return []
    換 = 型の口.Driveの列の読み替え(シート)
    戻し = {v: k for k, v in 換.items()}
    h = [str(x if x is not None else "").strip() for x in 格子[0]]
    欠け = [c for c in 型の口.Driveの見出し(シート, タブ) if c not in h]
    if 欠け:
        raise 引けない(f"{本} の「{型の口.タブの名(シート, タブ)}」の見出しに {'・'.join(欠け)} が無い")
    鍵 = 換.get("会社", "会社")
    out = []
    for r in 格子[1:]:
        行 = {c: (r[i] if i < len(r) else "") for i, c in enumerate(h) if c}
        if str(行.get(鍵, "")).strip() != 置き場["顧客ID"]:
            continue
        行 = {戻し.get(c, c): v for c, v in 行.items()}
        行["会社"] = 置き場["会社"]
        out.append(行)
    return out
