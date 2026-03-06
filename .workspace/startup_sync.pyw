"""
CS_Study Startup Sync — 부팅 시 양방향 자동 동기화

Windows 로그인 시 Task Scheduler에 의해 실행됨.
콘솔 없이 백그라운드로 동작하며, 결과를 토스트 알림 + 로그로 표시.

동작 순서: 네트워크 대기 → push(미푸시 커밋) → pull(원격 변경) → 알림
"""

import json
import subprocess
import socket
import time
import logging
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
LOG_PATH = SCRIPT_DIR / "sync.log"
ROOT = SCRIPT_DIR.parent

logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)
log = logging.getLogger("startup_sync")


def wait_for_network(timeout=60, interval=5):
    """인터넷 연결될 때까지 대기."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            socket.create_connection(("github.com", 443), timeout=3).close()
            return True
        except OSError:
            time.sleep(interval)
    return False


def git(cwd, *args):
    r = subprocess.run(
        ["git", *args], cwd=str(cwd),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def _xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def toast(title, body):
    """Windows 토스트 알림 (PowerShell, 의존성 없음)."""
    safe_title = _xml_escape(title)
    safe_body = _xml_escape(body)
    ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] > $null

$template = @"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>{safe_title}</text>
      <text>{safe_body}</text>
    </binding>
  </visual>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("CS_Study Sync")
$notifier.Show([Windows.UI.Notifications.ToastNotification]::new($xml))
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_repo_info(path):
    """레포의 dirty/ahead/behind 상태를 빠르게 확인."""
    info = {"dirty": False, "ahead": 0, "behind": 0}
    rc, out, _ = git(path, "status", "--porcelain")
    info["dirty"] = bool(out)
    rc, out, _ = git(path, "rev-list", "--left-right", "--count", "HEAD...@{u}")
    if rc == 0 and len(out.split()) == 2:
        info["ahead"], info["behind"] = map(int, out.split())
    return info


def sync_repos(cfg):
    """모든 레포 push + pull. 결과 dict 반환."""
    result = {
        "pushed": [], "pulled": [], "uptodate": 0,
        "skipped": [], "dirty": [], "failed": [],
    }

    all_repos = list(cfg["repos"])

    for r in all_repos:
        path = ROOT / r["local"]
        name = r["local"]

        if not (path / ".git").exists():
            result["skipped"].append(f"{name} (미설치)")
            continue

        rc, out, _ = git(path, "remote")
        if not out:
            result["skipped"].append(f"{name} (remote 없음)")
            continue

        info = _get_repo_info(path)

        if info["dirty"]:
            result["dirty"].append(name)
            result["skipped"].append(f"{name} (로컬 변경)")
            continue

        # Phase 1: Push ahead commits
        if info["ahead"] > 0:
            rc, _, err = git(path, "push")
            if rc == 0:
                result["pushed"].append(f"{name} ({info['ahead']})")
                log.info(f"  pushed: {name} — {info['ahead']} commits")
            else:
                result["failed"].append(f"{name} (push)")
                log.warning(f"  push failed: {name} — {err[:60]}")
                continue

        # Phase 2: Fetch + Pull
        rc, _, _ = git(path, "fetch", "--quiet")
        if rc != 0:
            result["failed"].append(f"{name} (fetch)")
            continue

        rc, out, _ = git(path, "rev-list", "--left-right", "--count", "HEAD...@{u}")
        behind = 0
        if rc == 0 and len(out.split()) == 2:
            behind = int(out.split()[1])

        if behind == 0:
            result["uptodate"] += 1
            continue

        rc, _, _ = git(path, "pull", "--ff-only")
        if rc == 0:
            result["pulled"].append(f"{name} ({behind})")
            log.info(f"  pulled: {name} — {behind} commits")
        else:
            result["failed"].append(f"{name} (pull)")
            log.warning(f"  pull failed: {name}")

    # 워크스페이스 레포 자체도 동기화
    if (ROOT / ".git").exists():
        ws_info = _get_repo_info(ROOT)
        if ws_info["dirty"]:
            result["dirty"].append("(workspace)")
        else:
            if ws_info["ahead"] > 0:
                rc, _, err = git(ROOT, "push")
                if rc == 0:
                    result["pushed"].append(f"(workspace) ({ws_info['ahead']})")
                    log.info(f"  pushed: workspace — {ws_info['ahead']} commits")
                else:
                    result["failed"].append("(workspace) (push)")
                    log.warning(f"  push failed: workspace — {err[:60]}")
            rc, _, _ = git(ROOT, "fetch", "--quiet")
            if rc == 0:
                rc, out, _ = git(ROOT, "rev-list", "--left-right", "--count", "HEAD...@{u}")
                behind = 0
                if rc == 0 and len(out.split()) == 2:
                    behind = int(out.split()[1])
                if behind > 0:
                    rc, _, _ = git(ROOT, "pull", "--ff-only")
                    if rc == 0:
                        result["pulled"].append(f"(workspace) ({behind})")
                        log.info(f"  pulled: workspace — {behind} commits")
                    else:
                        result["failed"].append("(workspace) (pull)")
                        log.warning("  pull failed: workspace")

    return result


def main():
    start = time.time()
    log.info("=" * 40)
    log.info("Startup sync 시작")

    if not CONFIG_PATH.exists():
        log.error("config.json 없음")
        return

    if not wait_for_network():
        log.warning("네트워크 연결 실패 — 동기화 건너뜀")
        toast("CS_Study Sync", "네트워크 연결 실패 — 동기화 건너뜀")
        return

    cfg = load_config()
    result = sync_repos(cfg)
    elapsed = time.time() - start

    pushed_count = len(result["pushed"])
    pulled_count = len(result["pulled"])
    skipped_count = len(result["skipped"])
    dirty_count = len(result["dirty"])
    failed_count = len(result["failed"])

    log.info(
        f"완료: push {pushed_count} | pull {pulled_count} | "
        f"최신 {result['uptodate']} | "
        f"건너뜀 {skipped_count} | "
        f"실패 {failed_count} | "
        f"{elapsed:.1f}초"
    )
    if result["dirty"]:
        log.info(f"  미커밋: {', '.join(result['dirty'])}")

    lines = []
    if pushed_count:
        lines.append(f"↑ {pushed_count}개 push")
    if pulled_count:
        lines.append(f"↓ {pulled_count}개 pull")
    lines.append(f"✓ {result['uptodate']}개 최신")
    if dirty_count:
        lines.append(f"⚠ {dirty_count}개 미커밋: {', '.join(result['dirty'])}")
    if failed_count:
        lines.append(f"✗ {failed_count}개 실패")
    lines.append(f"{elapsed:.1f}초 소요")

    toast("CS_Study Sync", "\n".join(lines))


if __name__ == "__main__":
    main()
