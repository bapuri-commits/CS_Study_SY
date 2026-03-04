#!/usr/bin/env python3
"""
CS_Study Workspace Sync Tool

사용법:
    python sync.py              # 전체 상태 확인
    python sync.py pull         # 클린 레포만 pull (dirty 레포는 건너뜀)
    python sync.py setup        # 새 컴퓨터 세팅 (미설치 레포 clone)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    os.system("")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
ROOT = SCRIPT_DIR.parent


class C:
    G = "\033[92m"
    Y = "\033[93m"
    R = "\033[91m"
    B = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def git(cwd, *args):
    r = subprocess.run(
        ["git", *args], cwd=str(cwd),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def status_of(path):
    info = dict(exists=False, git=False, branch="", dirty=0, ahead=0, behind=0,
                remote=False, remote_url="")
    if not path.exists():
        return info
    info["exists"] = True
    if not (path / ".git").exists():
        return info
    info["git"] = True

    rc, out, _ = git(path, "branch", "--show-current")
    info["branch"] = out if rc == 0 else "?"

    rc, out, _ = git(path, "remote")
    info["remote"] = bool(out)

    if info["remote"]:
        rc, out, _ = git(path, "remote", "get-url", "origin")
        info["remote_url"] = out if rc == 0 else ""

    rc, out, _ = git(path, "status", "--porcelain")
    info["dirty"] = len(out.splitlines()) if out else 0

    if info["remote"]:
        rc, out, _ = git(path, "rev-list", "--left-right", "--count", "HEAD...@{u}")
        if rc == 0 and len(out.split()) == 2:
            info["ahead"], info["behind"] = map(int, out.split())

    return info


def expected_url(cfg, repo_entry):
    return f"https://github.com/{cfg['github_user']}/{repo_entry['remote']}.git"


def scan_unknown_folders(cfg):
    """config에 없는 폴더 탐지."""
    known = {r["local"] for r in cfg["repos"]}
    known.update({".workspace", ".git", ".vscode", "test"})
    unknown = []
    for item in ROOT.iterdir():
        if item.is_dir() and item.name not in known and not item.name.startswith("."):
            unknown.append(item.name)
    return sorted(unknown)


def header(text):
    print(f"\n{C.BOLD}{C.B}{'=' * 56}")
    print(f"  {text}")
    print(f"{'=' * 56}{C.END}\n")


# ──────────────────────────────────────────────────────────
#  status
# ──────────────────────────────────────────────────────────
def cmd_status(cfg):
    header("CS_Study 워크스페이스 상태")
    missing, dirty, behind_repos = [], [], []

    for r in cfg["repos"]:
        path = ROOT / r["local"]
        s = status_of(path)
        name = r["local"]

        if not s["exists"]:
            print(f"  {C.R}✗ {name:<28} 미설치{C.END}")
            missing.append(name)
            continue
        if not s["git"]:
            print(f"  {C.R}? {name:<28} git 아님{C.END}")
            continue

        tags = []
        if s["dirty"]:
            tags.append(f"{C.Y}변경 {s['dirty']}개{C.END}")
            dirty.append(name)
        if s["ahead"]:
            tags.append(f"{C.B}↑{s['ahead']}{C.END}")
        if s["behind"]:
            tags.append(f"{C.R}↓{s['behind']}{C.END}")
            behind_repos.append(name)
        if not tags:
            tags.append(f"{C.G}동기화됨{C.END}")

        print(f"  {C.G}●{C.END} {C.BOLD}{name:<28}{C.END} [{s['branch']}]  {'  '.join(tags)}")

    print(f"\n{C.DIM}{'─' * 56}{C.END}")
    total = len(cfg["repos"])
    print(
        f"  총 {total}개 | "
        f"{C.G}설치 {total - len(missing)}{C.END} | "
        f"{C.Y}변경 {len(dirty)}{C.END} | "
        f"{C.R}업데이트 {len(behind_repos)}{C.END}"
    )
    if missing:
        print(f"\n  {C.DIM}→ python sync.py setup 으로 미설치 레포 클론{C.END}")
    if behind_repos:
        print(f"  {C.DIM}→ python sync.py pull 으로 업데이트{C.END}")

    unknown = scan_unknown_folders(cfg)
    if unknown:
        print(f"\n  {C.Y}미관리 폴더:{C.END} {C.DIM}{', '.join(unknown)}{C.END}")


# ──────────────────────────────────────────────────────────
#  pull
# ──────────────────────────────────────────────────────────
def cmd_pull(cfg):
    header("Pull (클린 레포만)")
    pulled, skipped, uptodate = 0, 0, 0

    for r in cfg["repos"]:
        path = ROOT / r["local"]
        s = status_of(path)
        name = r["local"]

        if not s["git"] or not s["remote"]:
            skipped += 1
            continue
        if s["dirty"]:
            print(f"  {C.Y}⏭ {name:<28} 로컬 변경 있음 — 건너뜀{C.END}")
            skipped += 1
            continue

        rc, _, _ = git(path, "fetch", "--quiet")
        if rc != 0:
            print(f"  {C.R}✗ {name:<28} fetch 실패{C.END}")
            continue

        rc, out, _ = git(path, "rev-list", "--left-right", "--count", "HEAD...@{u}")
        b = 0
        if rc == 0 and len(out.split()) == 2:
            b = int(out.split()[1])
        if b == 0:
            uptodate += 1
            continue

        rc, _, _ = git(path, "pull", "--ff-only")
        if rc == 0:
            print(f"  {C.G}↓ {name:<28} {b}개 커밋 업데이트{C.END}")
            pulled += 1
        else:
            print(f"  {C.R}✗ {name:<28} pull 실패 (수동 처리 필요){C.END}")

    print(f"\n{C.DIM}{'─' * 56}{C.END}")
    print(f"  업데이트 {C.G}{pulled}{C.END} | 최신 {uptodate} | 건너뜀 {C.Y}{skipped}{C.END}")


# ──────────────────────────────────────────────────────────
#  setup
# ──────────────────────────────────────────────────────────
def cmd_setup(cfg):
    header("새 컴퓨터 세팅")
    user = cfg["github_user"]
    cloned, existed, failed, warned = 0, 0, 0, 0

    for r in cfg["repos"]:
        path = ROOT / r["local"]
        name = r["local"]
        url = expected_url(cfg, r)

        if (path / ".git").exists():
            actual_url = ""
            rc, out, _ = git(path, "remote", "get-url", "origin")
            if rc == 0:
                actual_url = out

            if actual_url and actual_url != url:
                print(f"  {C.Y}⚠ {name:<28} remote 불일치{C.END}")
                print(f"    {C.DIM}예상: {url}{C.END}")
                print(f"    {C.DIM}실제: {actual_url}{C.END}")
                warned += 1
            else:
                print(f"  {C.G}● {name:<28} 이미 설치됨{C.END}")
            existed += 1
            continue

        if path.exists():
            items = list(path.iterdir())
            if items:
                print(f"  {C.Y}⚠ {name:<28} 폴더 존재하지만 git 아님 ({len(items)}개 파일){C.END}")
                print(f"    {C.DIM}→ 삭제 또는 이름 변경 후 다시 실행하세요{C.END}")
                print(f"    {C.DIM}  ren \"{name}\" \"{name}_backup\"{C.END}")
                warned += 1
                failed += 1
                continue
            else:
                path.rmdir()

        print(f"  {C.B}↓ {name} 클론 중...{C.END}", end="", flush=True)
        rc, _, err = git(ROOT, "clone", "-b", r["branch"], url, r["local"])

        if rc == 0:
            print(f"\r  {C.G}✓ {name:<28} 클론 완료          {C.END}")
            cloned += 1
        else:
            print(f"\r  {C.R}✗ {name:<28} 실패: {err[:50]}{C.END}")
            failed += 1

    print(f"\n{C.DIM}{'─' * 56}{C.END}")
    print(
        f"  클론 {C.G}{cloned}{C.END} | 기존 {existed} | "
        f"경고 {C.Y}{warned}{C.END} | 실패 {C.R}{failed}{C.END}"
    )

    unknown = scan_unknown_folders(cfg)
    if unknown:
        print(f"\n  {C.Y}관리 대상 아닌 폴더 발견:{C.END}")
        for u in unknown:
            has_git = (ROOT / u / ".git").exists()
            tag = "git 레포" if has_git else "일반 폴더"
            print(f"    {C.DIM}· {u}/ ({tag}){C.END}")
        print(f"  {C.DIM}→ 필요 없으면 삭제, 필요하면 config.json에 추가{C.END}")

    ws = cfg.get("workspace_file", "CS_Study_SY.code-workspace")
    if (ROOT / ws).exists():
        print(f"\n  {C.G}Cursor에서 {ws} 를 열면 전체 워크스페이스 로드{C.END}")


# ──────────────────────────────────────────────────────────
#  main
# ──────────────────────────────────────────────────────────
def main():
    if not CONFIG_PATH.exists():
        print(f"{C.R}config.json 없음: {CONFIG_PATH}{C.END}")
        print(f"{C.DIM}bootstrap.ps1을 먼저 실행하세요{C.END}")
        sys.exit(1)

    cfg = load_config()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    cmds = {"status": cmd_status, "pull": cmd_pull, "setup": cmd_setup}

    if cmd in cmds:
        cmds[cmd](cfg)
    else:
        print(f"사용법: python sync.py [status | pull | setup]")
        sys.exit(1)


if __name__ == "__main__":
    main()
