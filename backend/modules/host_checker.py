"""
SysWatch v2.1 — Host Status Checker
Periodically checks if hosts are reachable and updates their status.
Uses ICMP ping with TCP fallback for connectivity checks.
"""
import os
import platform
import subprocess
import socket
import json
import logging

from modules.database import db
from modules.logging_manager import log_event, utcnow

logger = logging.getLogger("syswatch.host_checker")


def _ping(host, timeout=5):
    """Ping a host. Works cross-platform (Linux, Windows, macOS)."""
    is_windows = platform.system().lower() == "windows"
    if is_windows:
        cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(timeout), host]
    try:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout + 5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return _tcp_check(host)
    except Exception:
        return False


def _tcp_check(host, ports=None):
    """Fallback: try TCP connect to common ports."""
    if ports is None:
        ports = [22, 80, 443, 5985, 3389]
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            if sock.connect_ex((host, port)) == 0:
                sock.close()
                return True
            sock.close()
        except Exception:
            continue
    return False


def check_host_status():
    """Check the status of all registered hosts."""
    logger.info("Starting host status check")
    hosts = db.query("SELECT id, hostname, ip, status FROM hosts")
    if not hosts:
        return {"checked": 0, "up": 0, "down": 0}

    up_count = down_count = 0
    for host in hosts:
        is_reachable = _ping(host["ip"])
        new_status = "UP" if is_reachable else "DOWN"
        if is_reachable:
            up_count += 1
        else:
            down_count += 1

        if new_status != host["status"]:
            db.execute("UPDATE hosts SET status=%s, last_seen=%s WHERE id=%s",
                (new_status, utcnow() if is_reachable else None, host["id"]))
            db.execute("INSERT INTO events (event_type, hostname, source, details, event_time) VALUES (%s, %s, %s, %s, %s)",
                ("host_down" if new_status == "DOWN" else "host_up", host["hostname"], "host_checker",
                 json.dumps({"old_status": host["status"], "new_status": new_status}), utcnow()))
            severity = "CRITICAL" if new_status == "DOWN" else "INFO"
            db.execute("INSERT INTO notifications (user_id, type, title, message, severity, source_id, source_type) VALUES (NULL, 'system', %s, %s, %s, %s, 'host')",
                (f"Host {new_status}: {host['hostname']}", f"Host {host['hostname']} ({host['ip']}) is now {new_status}", severity, host["id"]))
            log_event("host_checker", "WARNING" if new_status == "DOWN" else "INFO", "host_status_change",
                f"Host {host['hostname']} changed from {host['status']} to {new_status}", hostname=host["hostname"],
                details={"ip": host["ip"], "old_status": host["status"], "new_status": new_status})
        elif is_reachable:
            db.execute("UPDATE hosts SET last_seen=%s WHERE id=%s", (utcnow(), host["id"]))

    logger.info(f"Host check: {len(hosts)} hosts, {up_count} UP, {down_count} DOWN")
    return {"checked": len(hosts), "up": up_count, "down": down_count}
