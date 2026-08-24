"""SysWatch v2.1 - Events API"""
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.security import require_auth

logger = logging.getLogger("syswatch.api_events")
events_bp = Blueprint("events", __name__)


@events_bp.route("/events", methods=["GET"])
@require_auth()
def list_events():
    limit = min(int(request.args.get("limit", 50)), 500)
    hostname = request.args.get("hostname")
    event_type = request.args.get("event_type")
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    if hostname: query += " AND hostname=%s"; params.append(hostname)
    if event_type: query += " AND event_type=%s"; params.append(event_type)
    query += " ORDER BY event_time DESC LIMIT %s"; params.append(limit)
    return jsonify(db.query(query, tuple(params)))


@events_bp.route("/events/<int:event_id>", methods=["GET"])
@require_auth()
def get_event(event_id):
    event = db.query_one("SELECT * FROM events WHERE id=%s", (event_id,))
    if not event: return jsonify({"error": "Event not found"}), 404
    return jsonify(event)