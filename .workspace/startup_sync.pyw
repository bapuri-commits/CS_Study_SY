"""
CS_Study Startup Sync — 부팅 시 자동 동기화

Windows 로그인 시 Task Scheduler에 의해 실행됨.
콘솔 없이 백그라운드로 동작하며, 결과를 토스트 알림 + 로그로 표시.
"""

import json
import subprocess
import socket
import time
import logging
from pathlib import Path
from datetime import datetime

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


def toast(title, body):
    """Windows 토스트 알림 (PowerShell, 의존성 없음)."""
    ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] > $null

$template = @"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>{title}</text>
      <text>{body}</text>
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


def sync_repos(cfg):
    """모든 레포 fetch + pull. 결과 dict 반환."""
    result = {"pulled": [], "uptodate": 0, "skipped": [], "failed": []}

    for r in cfg["repos"]:
        path = ROOT / r["local"]
        name = r["local"]

        if not (path / ".git").exists():
            result["skipped"].append(f"{name} (미설치)")
            continue

        rc, out, _ = git(path, "remote")
        if not out:
            result["skipped"].append(f"{name} (remote 없음)")
            continue

        rc, out, _ = git(path, "status", "--porcelain")
        if out:
            result["skipped"].append(f"{name} (로컬 변경)")
            continue

        rc, _, _ = git(path, "fetch", "--quiet")
        if rc != 0:
            result["failed"].append(name)
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
            result["failed"].append(name)
            log.warning(f"  pull failed: {name}")

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

    pulled_count = len(result["pulled"])
    skipped_count = len(result["skipped"])
    failed_count = len(result["failed"])

    log.info(
        f"완료: 업데이트 {pulled_count} | "
        f"최신 {result['uptodate']} | "
        f"건너뜀 {skipped_count} | "
        f"실패 {failed_count} | "
        f"{elapsed:.1f}초"
    )

    lines = []
    if pulled_count:
        lines.append(f"↓ {pulled_count}개 업데이트")
    lines.append(f"✓ {result['uptodate']}개 최신")
    if skipped_count:
        lines.append(f"⏭ {skipped_count}개 건너뜀")
    if failed_count:
        lines.append(f"✗ {failed_count}개 실패")
    lines.append(f"{elapsed:.1f}초 소요")

    toast("CS_Study Sync", "\n".join(lines))


if __name__ == "__main__":
    main()
