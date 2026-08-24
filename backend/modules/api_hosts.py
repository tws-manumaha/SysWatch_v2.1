"""SysWatch v2.1 - Host Management API"""
import json
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.logging_manager import log_event, utcnow
from modules.security import validate_input, require_auth, get_current_user

logger = logging.getLogger("syswatch.api_hosts")
hosts_bp = Blueprint("hosts", __name__)


@hosts_bp.route("/hosts", methods=["GET"])
@require_auth()
def list_hosts():
    hosts = db.query("""SELECT h.id, h.hostname, h.ip, h.os_type, h.status, h.last_seen, h.agent_installed, h.agent_version, h.ssh_port, h.ssh_user, h.discovered_by, h.discovery_time, m.cpu, m.memory, m.disk, m.load_1, m.load_5, m.load_15, m.processes, m.uptime_seconds, m.timestamp as metric_timestamp FROM hosts h LEFT JOIN (SELECT hostname, cpu, memory, disk, load_1, load_5, load_15, processes, uptime_seconds, timestamp, ROW_NUMBER() OVER (PARTITION BY hostname ORDER BY timestamp DESC) as rn FROM metrics) m ON h.hostname = m.hostname AND m.rn = 1 ORDER BY h.hostname""")
    return jsonify(hosts)


@hosts_bp.route("/hosts", methods=["POST"])
@require_auth(roles=["admin", "operator"])
def add_host():
    data = request.get_json() or {}
    hostname = data.get("hostname", "").strip()
    ip = data.get("ip", "").strip()
    if not hostname or not ip: return jsonify({"error": "hostname and ip are required"}), 400
    if not validate_input(hostname, "hostname"): return jsonify({"error": "Invalid hostname"}), 400
    if not validate_input(ip, "ip"): return jsonify({"error": "Invalid IP address"}), 400
    existing = db.query_one("SELECT id FROM hosts WHERE hostname=%s OR ip=%s", (hostname, ip))
    if existing: return jsonify({"error": "Host with this hostname or IP already exists"}), 409
    host_id = db.execute_returning_id("INSERT INTO hosts (hostname, ip, os_type, status, ssh_port, ssh_user, discovered_by, discovery_time) VALUES (%s, %s, %s, 'UNKNOWN', %s, %s, 'manual', %s)", (hostname, ip, data.get("os_type", "linux"), data.get("ssh_port", 22), data.get("ssh_user", ""), utcnow()))
    db.execute("INSERT INTO events (event_type, hostname, source, details, event_time) VALUES (%s, %s, %s, %s, %s)", ("host_added", hostname, "api", json.dumps({"ip": ip}), utcnow()))
    log_event("hosts", "INFO", "host_added", f"Host {hostname} ({ip}) added", user_id=get_current_user().get("email"), hostname=hostname)
    return jsonify({"id": host_id, "hostname": hostname, "ip": ip, "status": "UNKNOWN"}), 201


@hosts_bp.route("/hosts/<int:host_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_host(host_id):
    host = db.query_one("SELECT hostname FROM hosts WHERE id=%s", (host_id,))
    if not host: return jsonify({"error": "Host not found"}), 404
    db.execute("DELETE FROM metrics WHERE hostname=%s", (host["hostname"],))
    db.execute("DELETE FROM metric_history WHERE hostname=%s", (host["hostname"],))
    db.execute("DELETE FROM hosts WHERE id=%s", (host_id,))
    db.execute("INSERT INTO events (event_type, hostname, source, details, event_time) VALUES (%s, %s, %s, %s, %s)", ("host_deleted", host["hostname"], "api", json.dumps({"host_id": host_id}), utcnow()))
    log_event("hosts", "INFO", "host_deleted", f"Host {host['hostname']} deleted", user_id=get_current_user().get("email"), hostname=host["hostname"])
    return jsonify({"message": "Host deleted"}), 200


@hosts_bp.route("/hosts/<hostname>/metrics", methods=["GET"])
@require_auth()
def get_host_metrics(hostname):
    if not validate_input(hostname, "hostname"): return jsonify({"error": "Invalid hostname"}), 400
    limit = min(int(request.args.get("limit", 100)), 1000)
    return jsonify(db.query("SELECT * FROM metrics WHERE hostname=%s ORDER BY timestamp DESC LIMIT %s", (hostname, limit)))


@hosts_bp.route("/hosts/<hostname>/events", methods=["GET"])
@require_auth()
def get_host_events(hostname):
    if not validate_input(hostname, "hostname"): return jsonify({"error": "Invalid hostname"}), 400
    limit = min(int(request.args.get("limit", 50)), 500)
    return jsonify(db.query("SELECT * FROM events WHERE hostname=%s ORDER BY event_time DESC LIMIT %s", (hostname, limit)))


@hosts_bp.route("/hosts/<hostname>/alerts", methods=["GET"])
@require_auth()
def get_host_alerts(hostname):
    if not validate_input(hostname, "hostname"): return jsonify({"error": "Invalid hostname"}), 400
    limit = min(int(request.args.get("limit", 50)), 500)
    return jsonify(db.query("SELECT * FROM alerts WHERE hostname=%s ORDER BY triggered_at DESC LIMIT %s", (hostname, limit)))


@hosts_bp.route("/hosts/<hostname>", methods=["PUT"])
@require_auth(roles=["admin", "operator"])
def update_host(hostname):
    if not validate_input(hostname, "hostname"): return jsonify({"error": "Invalid hostname"}), 400
    data = request.get_json() or {}
    updates = {}
    if "ssh_port" in data: updates["ssh_port"] = data["ssh_port"]
    if "ssh_user" in data: updates["ssh_user"] = data["ssh_user"]
    if "os_type" in data: updates["os_type"] = data["os_type"]
    if "ip" in data:
        if not validate_input(data["ip"], "ip"): return jsonify({"error": "Invalid IP"}), 400
        updates["ip"] = data["ip"]
    if not updates: return jsonify({"error": "No fields to update"}), 400
    set_clause = ", ".join(f"{k}=%s" for k in updates)
    values = list(updates.values()) + [hostname]
    db.execute(f"UPDATE hosts SET {set_clause} WHERE hostname=%s", tuple(values))
    log_event("hosts", "INFO", "host_updated", f"Host {hostname} updated", user_id=get_current_user().get("email"), hostname=hostname, details=updates)
    return jsonify({"message": "Host updated", "updated_fields": list(updates.keys())})