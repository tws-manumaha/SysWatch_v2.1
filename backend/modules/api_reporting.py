"""SysWatch v2.1 - Reporting API"""
import csv
import io
import logging
from flask import Blueprint, request, jsonify, Response
from modules.database import db
from modules.security import require_auth

logger = logging.getLogger("syswatch.api_reporting")
reporting_bp = Blueprint("reporting", __name__)


@reporting_bp.route("/reports/dashboard", methods=["GET"])
@require_auth()
def dashboard_summary():
    host_stats = db.query_one("SELECT COUNT(*) as total, SUM(CASE WHEN status='UP' THEN 1 ELSE 0 END) as up, SUM(CASE WHEN status='DOWN' THEN 1 ELSE 0 END) as down FROM hosts") or {}
    alert_stats = db.query_one("SELECT COUNT(*) as total, SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as open, SUM(CASE WHEN severity='CRITICAL' THEN 1 ELSE 0 END) as critical FROM alerts") or {}
    insight_stats = db.query_one("SELECT COUNT(*) as total, SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as open FROM ai_insights") or {}
    event_stats = db.query_one("SELECT COUNT(*) as total FROM events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)") or {}
    return jsonify({"hosts": {"total": host_stats.get("total", 0), "up": host_stats.get("up", 0), "down": host_stats.get("down", 0)}, "alerts": {"total": alert_stats.get("total", 0), "open": alert_stats.get("open", 0), "critical": alert_stats.get("critical", 0)}, "insights": {"total": insight_stats.get("total", 0), "open": insight_stats.get("open", 0)}, "events_24h": event_stats.get("total", 0)})


@reporting_bp.route("/reports/metrics/<hostname>", methods=["GET"])
@require_auth()
def metric_report(hostname):
    hours = int(request.args.get("hours", 24))
    metric = request.args.get("metric", "cpu")
    data = db.query("SELECT timestamp, value FROM metric_history WHERE hostname=%s AND metric_name=%s AND timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR) ORDER BY timestamp", (hostname, metric, hours))
    return jsonify({"hostname": hostname, "metric": metric, "hours": hours, "data": data})


@reporting_bp.route("/reports/export/csv", methods=["GET"])
@require_auth(roles=["admin", "operator"])
def export_csv():
    hosts = db.query("SELECT h.hostname, h.ip, h.os_type, h.status, h.last_seen, m.cpu, m.memory, m.disk, m.load_1 FROM hosts h LEFT JOIN (SELECT hostname, cpu, memory, disk, load_1, ROW_NUMBER() OVER (PARTITION BY hostname ORDER BY timestamp DESC) as rn FROM metrics) m ON h.hostname = m.hostname AND m.rn = 1 ORDER BY h.hostname")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Hostname", "IP", "OS", "Status", "Last Seen", "CPU%", "Memory%", "Disk%", "Load 1min"])
    for h in hosts:
        writer.writerow([h.get("hostname"), h.get("ip"), h.get("os_type"), h.get("status"), str(h.get("last_seen", "")), h.get("cpu"), h.get("memory"), h.get("disk"), h.get("load_1")])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=syswatch_hosts.csv"})


@reporting_bp.route("/reports/uptime", methods=["GET"])
@require_auth()
def uptime_report():
    hosts = db.query("SELECT hostname, status FROM hosts")
    result = []
    for host in hosts:
        events = db.query("SELECT event_type FROM events WHERE hostname=%s AND event_type IN ('host_up', 'host_down') AND event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)", (host["hostname"],))
        if not events:
            result.append({"hostname": host["hostname"], "uptime_pct": 100.0 if host["status"] == "UP" else 0.0, "incidents": 0})
            continue
        down_count = sum(1 for e in events if e["event_type"] == "host_down")
        uptime = ((len(events) - down_count) / len(events) * 100) if events else 100.0
        result.append({"hostname": host["hostname"], "uptime_pct": round(uptime, 2), "incidents": down_count})
    return jsonify(result)