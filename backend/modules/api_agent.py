"""
SysWatch v2.1 — Agent Ingestion API
Accepts metric reports from SysWatch agents running on monitored hosts.
Provides registration, heartbeat, and metric ingestion endpoints.
"""
import json
import hashlib
import secrets
import logging
from flask import Blueprint, request, jsonify

from modules.database import db
from modules.logging_manager import log_event, utcnow
from modules.security import validate_input, require_auth

logger = logging.getLogger("syswatch.api_agent")
agent_bp = Blueprint("agent", __name__)


@agent_bp.route("/agent/register", methods=["POST"])
def register_agent():
    """Register a new agent and return an agent key."""
    data = request.get_json() or {}
    hostname = data.get("hostname", "").strip()
    ip = data.get("ip", "").strip()
    os_type = data.get("os_type", "linux")

    if not hostname or not ip:
        return jsonify({"error": "hostname and ip are required"}), 400
    if not validate_input(hostname, "hostname"):
        return jsonify({"error": "Invalid hostname"}), 400

    agent_key = secrets.token_urlsafe(32)
    agent_key_hash = hashlib.sha256(agent_key.encode()).hexdigest()

    existing = db.query_one("SELECT id FROM hosts WHERE hostname=%s", (hostname,))
    if existing:
        db.execute(
            "UPDATE hosts SET ip=%s, os_type=%s, agent_key_hash=%s, agent_installed=TRUE, status='UP', last_seen=%s, agent_version=%s WHERE id=%s",
            (ip, os_type, agent_key_hash, utcnow(), data.get("agent_version", "2.1"), existing["id"]))
        host_id = existing["id"]
    else:
        host_id = db.execute_returning_id(
            "INSERT INTO hosts (hostname, ip, os_type, status, agent_installed, agent_key_hash, agent_version, last_seen, discovered_by, discovery_time) VALUES (%s, %s, %s, 'UP', TRUE, %s, %s, %s, 'agent', %s)",
            (hostname, ip, os_type, agent_key_hash, data.get("agent_version", "2.1"), utcnow(), utcnow()))

    db.execute("INSERT INTO events (event_type, hostname, source, details, event_time) VALUES (%s, %s, %s, %s, %s)",
        ("agent_registered", hostname, "agent_api", json.dumps({"host_id": host_id, "ip": ip}), utcnow()))
    log_event("agent", "INFO", "agent_registered", f"Agent registered: {hostname} ({ip})", hostname=hostname, details={"host_id": host_id})

    return jsonify({"host_id": host_id, "agent_key": agent_key, "report_interval": 60, "server_version": "2.1"}), 201


@agent_bp.route("/agent/report", methods=["POST"])
def report_metrics():
    """Receive metrics from an agent. Header: X-Agent-Key: <agent_key>"""
    agent_key = request.headers.get("X-Agent-Key", "")
    if not agent_key:
        return jsonify({"error": "X-Agent-Key header required"}), 401

    key_hash = hashlib.sha256(agent_key.encode()).hexdigest()
    host = db.query_one("SELECT id, hostname, ip, status FROM hosts WHERE agent_key_hash=%s", (key_hash,))
    if not host:
        return jsonify({"error": "Invalid agent key"}), 403

    data = request.get_json() or {}
    hostname = host["hostname"]
    metrics = data.get("metrics", {})

    cpu = float(metrics.get("cpu", 0))
    memory = float(metrics.get("memory", 0))
    disk = float(metrics.get("disk", 0))
    net_in = int(metrics.get("net_in", 0))
    net_out = int(metrics.get("net_out", 0))
    load_1 = float(metrics.get("load_1", 0))
    load_5 = float(metrics.get("load_5", 0))
    load_15 = float(metrics.get("load_15", 0))
    processes = int(metrics.get("processes", 0))
    uptime_seconds = int(metrics.get("uptime_seconds", 0))
    swap_used = float(metrics.get("swap_used", 0))
    temperature = metrics.get("temperature")
    custom_metrics = metrics.get("custom_metrics")

    db.execute(
        "INSERT INTO metrics (hostname, cpu, memory, disk, net_in, net_out, load_1, load_5, load_15, processes, uptime_seconds, swap_used, temperature, custom_metrics, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (hostname, cpu, memory, disk, net_in, net_out, load_1, load_5, load_15, processes, uptime_seconds, swap_used, temperature, json.dumps(custom_metrics) if custom_metrics else None, utcnow()))

    db.execute("UPDATE hosts SET last_seen=%s, status='UP' WHERE id=%s", (utcnow(), host["id"]))

    for metric_name, value in [("cpu", cpu), ("memory", memory), ("disk", disk), ("load_1", load_1), ("load_5", load_5), ("load_15", load_15)]:
        db.execute("INSERT INTO metric_history (hostname, metric_name, value, timestamp) VALUES (%s, %s, %s, %s)", (hostname, metric_name, value, utcnow()))

    return jsonify({"status": "received", "timestamp": utcnow().isoformat()}), 200


@agent_bp.route("/agent/heartbeat", methods=["POST"])
def heartbeat():
    """Lightweight heartbeat from agent."""
    agent_key = request.headers.get("X-Agent-Key", "")
    if not agent_key:
        return jsonify({"error": "X-Agent-Key header required"}), 401
    key_hash = hashlib.sha256(agent_key.encode()).hexdigest()
    host = db.query_one("SELECT id, hostname FROM hosts WHERE agent_key_hash=%s", (key_hash,))
    if not host:
        return jsonify({"error": "Invalid agent key"}), 403
    db.execute("UPDATE hosts SET last_seen=%s, status='UP' WHERE id=%s", (utcnow(), host["id"]))
    return jsonify({"status": "ok", "timestamp": utcnow().isoformat()}), 200


@agent_bp.route("/agent/config/<hostname>", methods=["GET"])
@require_auth(roles=["admin", "operator"])
def get_agent_config(hostname):
    """Get the agent configuration for a specific host."""
    if not validate_input(hostname, "hostname"):
        return jsonify({"error": "Invalid hostname"}), 400
    host = db.query_one("SELECT hostname, ip, os_type, agent_version, ssh_port, ssh_user FROM hosts WHERE hostname=%s", (hostname,))
    if not host:
        return jsonify({"error": "Host not found"}), 404
    return jsonify({"hostname": host["hostname"], "ip": host["ip"], "os_type": host["os_type"], "agent_version": host.get("agent_version", "2.1"), "report_interval": 60,
        "metrics": ["cpu", "memory", "disk", "net_in", "net_out", "load_1", "load_5", "load_15", "processes", "uptime_seconds", "swap_used"], "ssh_port": host.get("ssh_port", 22)})
