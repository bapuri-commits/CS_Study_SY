#!/usr/bin/env python3
"""
CS_Study Workspace Sync Tool

사용법:
    python sync.py              # 전체 상태 확인
    python sync.py pull         # 클린 레포만 pull (dirty 레포는 건너뜀)
    python sync.py setup        # 새 컴퓨터 세팅 (미설치 레포 clone)
    python sync.py add <local> <remote> [branch]   # 프로젝트 등록 + 클론
    python sync.py remove <local>                   # 프로젝트 등록 해제
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


def _check_startup_task():
    """startup sync가 등록되어 있는지 확인 (Task Scheduler 또는 Startup 폴더)."""
    if sys.platform != "win32":
        return False
    try:
        r = subprocess.run(
            ["schtasks", "/query", "/tn", "CS_Study Startup Sync"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if r.returncode == 0:
            return True
    except Exception:
        pass
    startup_dir = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"
    return (startup_dir / "CS_Study_Sync.vbs").exists()


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

    startup_registered = _check_startup_task()
    if startup_registered:
        print(f"  {C.G}부팅 자동 동기화: 등록됨{C.END}")
    else:
        print(f"\n  {C.Y}부팅 자동 동기화 미등록{C.END}")
        print(f"  {C.DIM}→ .workspace 폴더에서 실행:{C.END}")
        print(f"  {C.DIM}  powershell -ExecutionPolicy Bypass -File register_startup.ps1{C.END}")


# ──────────────────────────────────────────────────────────
#  add / remove helpers
# ──────────────────────────────────────────────────────────
def _save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)
        f.write("\n")


def _update_gitignore(local_name, action):
    gitignore = ROOT / ".gitignore"
    if not gitignore.exists():
        return False
    lines = gitignore.read_text(encoding="utf-8").splitlines()
    entry = f"{local_name}/"

    if action == "add":
        if entry in lines:
            return False
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and stripped.endswith("/") and not stripped.startswith("#") and not stripped.startswith("."):
                insert_idx = i + 1
        lines.insert(insert_idx, entry)
        gitignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True

    elif action == "remove":
        new_lines = [l for l in lines if l.strip() != entry]
        if len(new_lines) == len(lines):
            return False
        gitignore.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return True

    return False


def _update_workspace_file(cfg, local_name, action):
    ws_file = ROOT / cfg.get("workspace_file", "CS_Study_SY.code-workspace")
    if not ws_file.exists():
        return False
    lines = ws_file.read_text(encoding="utf-8").splitlines()

    if action == "add":
        if any(f'"path": "{local_name}"' in l for l in lines):
            return False
        folders_end = None
        for i, line in enumerate(lines):
            if '"folders"' in line:
                depth = 0
                for j in range(i, len(lines)):
                    depth += lines[j].count("[") - lines[j].count("]")
                    if depth == 0:
                        folders_end = j
                        break
                break
        if folders_end is None:
            return False
        last_brace = None
        for i in range(folders_end - 1, -1, -1):
            if lines[i].strip() in ("}", "},"):
                last_brace = i
                break
        if last_brace is None:
            return False
        if not lines[last_brace].strip().endswith(","):
            lines[last_brace] = lines[last_brace].rstrip() + ","
        new_lines = [
            "\t\t{",
            f'\t\t\t"path": "{local_name}"',
            "\t\t}",
        ]
        for idx, nl in enumerate(new_lines):
            lines.insert(last_brace + 1 + idx, nl)

    elif action == "remove":
        if not any(f'"path": "{local_name}"' in l for l in lines):
            return False
        block_start = block_end = None
        current_block = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "{":
                current_block = i
            elif current_block is not None and f'"path": "{local_name}"' in line:
                block_start = current_block
            elif current_block is not None and stripped in ("}", "},"):
                if block_start is not None:
                    block_end = i
                    break
                current_block = None
        if block_start is None or block_end is None:
            return False
        is_last_entry = not lines[block_end].strip().endswith(",")
        del lines[block_start : block_end + 1]
        if is_last_entry:
            for i in range(block_start - 1, -1, -1):
                if lines[i].strip().endswith("},"):
                    lines[i] = lines[i].rstrip()[:-1]
                    break

    ws_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


# ──────────────────────────────────────────────────────────
#  add
# ──────────────────────────────────────────────────────────
def cmd_add(cfg):
    args = sys.argv[2:]
    if len(args) < 2:
        print(f"사용법: python sync.py add <local_name> <github_remote> [branch]")
        print(f"  예:   python sync.py add my_project My_Project")
        print(f"        python sync.py add my_project My_Project master")
        sys.exit(1)

    local, remote = args[0], args[1]
    branch = args[2] if len(args) > 2 else "main"

    if any(r["local"] == local for r in cfg["repos"]):
        print(f"\n  {C.Y}⚠ '{local}'은 이미 등록되어 있습니다{C.END}")
        return

    header(f"프로젝트 등록: {local}")

    cfg["repos"].append({"local": local, "remote": remote, "branch": branch})
    _save_config(cfg)
    print(f"  {C.G}✓{C.END} config.json")

    if _update_gitignore(local, "add"):
        print(f"  {C.G}✓{C.END} .gitignore")
    else:
        print(f"  {C.DIM}● .gitignore (이미 존재){C.END}")

    if _update_workspace_file(cfg, local, "add"):
        print(f"  {C.G}✓{C.END} .code-workspace")
    else:
        print(f"  {C.DIM}● .code-workspace (이미 존재){C.END}")

    path = ROOT / local
    url = expected_url(cfg, cfg["repos"][-1])
    if (path / ".git").exists():
        print(f"  {C.DIM}● 레포 이미 존재{C.END}")
    elif path.exists() and any(path.iterdir()):
        print(f"  {C.Y}⚠ 폴더 존재하지만 git 아님 — 수동 처리 필요{C.END}")
    else:
        print(f"  {C.B}↓ 클론 중...{C.END}", end="", flush=True)
        if path.exists():
            path.rmdir()
        rc, _, err = git(ROOT, "clone", "-b", branch, url, local)
        if rc == 0:
            print(f"\r  {C.G}✓{C.END} 클론 완료                     ")
        else:
            print(f"\r  {C.R}✗{C.END} 클론 실패: {err[:60]}")

    handoff = ROOT / local / "docs" / "handoff"
    if (ROOT / local).exists():
        handoff.mkdir(parents=True, exist_ok=True)
        gitkeep = handoff / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()
        print(f"  {C.G}✓{C.END} docs/handoff/")

    print(f"\n  {C.G}등록 완료!{C.END} {local} → {cfg['github_user']}/{remote} ({branch})")


# ──────────────────────────────────────────────────────────
#  remove
# ──────────────────────────────────────────────────────────
def cmd_remove(cfg):
    args = sys.argv[2:]
    if not args:
        print(f"사용법: python sync.py remove <local_name>")
        sys.exit(1)

    local = args[0]

    if not any(r["local"] == local for r in cfg["repos"]):
        print(f"\n  {C.Y}⚠ '{local}'은 등록되어 있지 않습니다{C.END}")
        return

    header(f"프로젝트 해제: {local}")

    cfg["repos"] = [r for r in cfg["repos"] if r["local"] != local]
    _save_config(cfg)
    print(f"  {C.G}✓{C.END} config.json에서 제거")

    if _update_gitignore(local, "remove"):
        print(f"  {C.G}✓{C.END} .gitignore에서 제거")
    else:
        print(f"  {C.DIM}● .gitignore (항목 없음){C.END}")

    if _update_workspace_file(cfg, local, "remove"):
        print(f"  {C.G}✓{C.END} .code-workspace에서 제거")
    else:
        print(f"  {C.DIM}● .code-workspace (항목 없음){C.END}")

    path = ROOT / local
    if path.exists():
        print(f"\n  {C.Y}참고:{C.END} '{local}/' 폴더는 삭제하지 않았습니다.")
        print(f"  {C.DIM}필요 없으면 직접 삭제하세요.{C.END}")

    print(f"\n  {C.G}해제 완료!{C.END}")


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
    cmds = {
        "status": cmd_status, "pull": cmd_pull, "setup": cmd_setup,
        "add": cmd_add, "remove": cmd_remove,
    }

    if cmd in cmds:
        cmds[cmd](cfg)
    else:
        print(f"사용법: python sync.py [status | pull | setup | add | remove]")
        sys.exit(1)


if __name__ == "__main__":
    main()
