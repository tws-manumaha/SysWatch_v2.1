"""SysWatch v2.1 - Network Discovery API"""
import ipaddress
import subprocess
import socket
import json
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.logging_manager import log_event, utcnow
from modules.security import validate_input, require_auth, get_current_user

logger = logging.getLogger("syswatch.api_discovery")
discovery_bp = Blueprint("discovery", __name__)


def _ping_sweep(subnet, timeout=1):
    live_hosts = []
    try:
        network = ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        return []
    for host in network.hosts():
        ip = str(host)
        try:
            result = subprocess.run(["ping", "-c", "1", "-W", str(timeout), ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout + 2)
            if result.returncode == 0: live_hosts.append(ip)
        except Exception:
            continue
    return live_hosts


def _reverse_dns(ip):
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except Exception:
        return ip


def _detect_os(ip):
    try:
        result = subprocess.run(["ping", "-c", "1", "-W", "2", ip], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split("\n"):
            if "ttl=" in line.lower():
                ttl = int(line.split("ttl=")[1].split()[0])
                if ttl <= 64: return "linux"
                elif ttl <= 128: return "windows"
                elif ttl <= 255: return "network_device"
    except Exception:
        pass
    return "unknown"


@discovery_bp.route("/discovery/scan", methods=["POST"])
@require_auth(roles=["admin", "operator"])
def scan_network():
    data = request.get_json() or {}
    subnet = data.get("subnet", "").strip()
    if not subnet or not validate_input(subnet, "subnet"):
        return jsonify({"error": "Valid subnet required (e.g., 192.168.1.0/24)"}), 400
    log_event("discovery", "INFO", "scan_started", f"Network scan started for {subnet}", user_id=get_current_user().get("email"))
    live_hosts = _ping_sweep(subnet, timeout=1)
    discovered = []
    for ip in live_hosts:
        hostname = _reverse_dns(ip)
        os_type = _detect_os(ip)
        existing = db.query_one("SELECT id FROM hosts WHERE ip=%s", (ip,))
        if not existing:
            host_id = db.execute_returning_id("INSERT INTO hosts (hostname, ip, os_type, status, discovered_by, discovery_time) VALUES (%s, %s, %s, 'UP', 'discovery', %s)", (hostname, ip, os_type, utcnow()))
        else:
            host_id = existing["id"]
            db.execute("UPDATE hosts SET status='UP', last_seen=%s WHERE id=%s", (utcnow(), host_id))
        discovered.append({"ip": ip, "hostname": hostname, "os_type": os_type, "host_id": host_id})
    db.execute("INSERT INTO events (event_type, hostname, source, details, event_time) VALUES (%s, %s, %s, %s, %s)", ("discovery_completed", subnet, "discovery_api", json.dumps({"hosts_found": len(discovered)}), utcnow()))
    log_event("discovery", "INFO", "scan_completed", f"Scan of {subnet} found {len(discovered)} hosts", user_id=get_current_user().get("email"), details={"subnet": subnet, "hosts": len(discovered)})
    return jsonify({"subnet": subnet, "hosts_found": len(discovered), "hosts": discovered})