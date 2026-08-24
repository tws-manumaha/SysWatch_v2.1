"""SysWatch v2.1 - Application Logs API"""
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.security import require_auth

logger = logging.getLogger("syswatch.api_system_logs")
system_logs_bp = Blueprint("system_logs", __name__)


@system_logs_bp.route("/logs", methods=["GET"])
@require_auth()
def list_logs():
    limit = min(int(request.args.get("limit", 100)), 1000)
    level = request.args.get("level")
    module = request.args.get("module")
    hostname = request.args.get("hostname")
    query = "SELECT * FROM application_logs WHERE 1=1"
    params = []
    if level: query += " AND level=%s"; params.append(level)
    if module: query += " AND module=%s"; params.append(module)
    if hostname: query += " AND hostname=%s"; params.append(hostname)
    query += " ORDER BY timestamp DESC LIMIT %s"; params.append(limit)
    return jsonify(db.query(query, tuple(params)))


@system_logs_bp.route("/logs/<int:log_id>", methods=["GET"])
@require_auth()
def get_log(log_id):
    log = db.query_one("SELECT * FROM application_logs WHERE id=%s", (log_id,))
    if not log: return jsonify({"error": "Log not found"}), 404
    return jsonify(log)