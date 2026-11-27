"""給与の見張りの hook（plugins/payroll-agent/hooks/見張り.py）が止めるのは 1 つだけ:
GitHub の道具と add_repo を、引数の repo の名が payroll-pack / payroll-pack-public の時。
表: 道具の名 × repo の名 × owner の有無 × 大文字小文字。ほかの repo は通る・Drive とシートの書き込みは止めない・命令の文は読まない。"""
import json
import subprocess
import sys

import pytest

from 手伝い import PLUGIN

HOOK = PLUGIN / "hooks" / "見張り.py"
道具たち = ("mcp__github__create_pull_request", "mcp__github__push_files", "mcp__github__get_file_contents",
          "mcp__github__merge_pull_request", "mcp__claude-code-remote__add_repo")
止める名 = ("payroll-pack", "payroll-pack-public")
通す名 = ("pixel-office", "agent-foundation-public", "payroll-pack-x", "my-payroll-pack", "payroll")


def _引数(名: str, owner: str | None, 形: str) -> dict:
    if 形 == "別の引数":
        return {"owner": owner or "", "repo": 名} if owner else {"repo": 名}
    return {"repo": f"{owner}/{名}" if owner else 名}


def _回す(tool: str, args) -> subprocess.CompletedProcess:
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"tool_name": tool, "tool_input": args}),
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, (r.returncode, r.stderr)
    return r


def _止めたか(r) -> bool:
    return bool(r.stdout.strip()) and json.loads(r.stdout)["hookSpecificOutput"].get("permissionDecision") == "deny"


_表 = [(t, 名, owner, 形, 字)
      for t in 道具たち for 名 in 止める名 + 通す名
      for owner in (None, "some-owner", "Some-Org") for 形 in ("1 つの引数", "別の引数")
      for 字 in ("小", "大", "混")]


@pytest.mark.parametrize("tool,名,owner,形,字", _表)
def test_表_パックのrepoだけ止まる(tool, 名, owner, 形, 字):
    書く名 = {"小": 名, "大": 名.upper(), "混": 名.title()}[字]
    r = _回す(tool, _引数(書く名, owner, 形))
    assert _止めたか(r) == (名 in 止める名), (tool, 書く名, owner, 形, r.stdout)
    if 名 in 止める名:
        assert 名 in json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize("args", [{"repo": "some-owner/payroll-pack.git"}, {"repo": " payroll-pack-public/ "},
                                  {"repository": "some-owner/Payroll-Pack"}, {"full_name": "x/payroll-pack"}])
def test_書き方の揺れも止まる(args):
    assert _止めたか(_回す("mcp__github__list_commits", args))


@pytest.mark.parametrize("tool,args", [
    ("mcp__c999fcee-566f-4b40-849e-d762560fa1cd__update_file", {"fileId": "作り物", "name": "取り込み_作り物"}),
    ("mcp__c999fcee-566f-4b40-849e-d762560fa1cd__create_file", {"title": "支給控除一覧_作り物", "parents": ["作り物"]}),
    ("mcp__befd6e03-1ca7-4b10-8334-d8dd007c3791__update_values", {"spreadsheetId": "作り物", "range": "出した物!A1"}),
    ("mcp__befd6e03-1ca7-4b10-8334-d8dd007c3791__append_values", {"spreadsheetId": "作り物", "range": "月の状況!A1"}),
    ("Bash", {"command": "python3 出口/出す.py --根 作り物"}),
    ("Bash", {"command": "git push origin main  # payroll-pack"}),   # 命令の文は読まない
    ("Write", {"file_path": "/tmp/payroll-pack/x", "content": "x"}),
])
def test_Driveとシートの書き込みと命令の文は止めない(tool, args):
    r = _回す(tool, args)
    assert r.stdout == "", r.stdout


def test_repoの無い引数とほかの道具は通る():
    for tool, args in (("mcp__github__get_me", {}), ("mcp__claude-code-remote__add_repo", {"owner": "payroll-pack", "repo": "x"}),
                       ("mcp__github__search_code", {"query": "payroll-pack"})):
        assert _回す(tool, args).stdout == "", (tool, args)


def test_引数が読めない時は止める():
    assert _止めたか(_回す("mcp__github__create_pull_request", "文の引数"))
