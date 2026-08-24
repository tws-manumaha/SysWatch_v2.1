"""SysWatch v2.1 - Notifications API"""
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.logging_manager import utcnow
from modules.security import require_auth, get_current_user

logger = logging.getLogger("syswatch.api_notifications")
notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/notifications", methods=["GET"])
@require_auth()
def list_notifications():
    user = get_current_user()
    limit = min(int(request.args.get("limit", 50)), 500)
    unread_only = request.args.get("unread", "false").lower() == "true"
    query = "SELECT * FROM notifications WHERE user_id IS NULL OR user_id=%s"
    params = [user.get("user_id")]
    if unread_only: query += " AND read_at IS NULL"
    query += " ORDER BY created_at DESC LIMIT %s"; params.append(limit)
    return jsonify(db.query(query, tuple(params)))


@notifications_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@require_auth()
def mark_read(notification_id):
    db.execute("UPDATE notifications SET read_at=%s WHERE id=%s", (utcnow(), notification_id))
    return jsonify({"message": "Notification marked as read"})


@notifications_bp.route("/notifications/read-all", methods=["POST"])
@require_auth()
def mark_all_read():
    user = get_current_user()
    db.execute("UPDATE notifications SET read_at=%s WHERE (user_id IS NULL OR user_id=%s) AND read_at IS NULL", (utcnow(), user.get("user_id")))
    return jsonify({"message": "All notifications marked as read"})


@notifications_bp.route("/notifications/unread-count", methods=["GET"])
@require_auth()
def unread_count():
    user = get_current_user()
    result = db.query_one("SELECT COUNT(*) as count FROM notifications WHERE (user_id IS NULL OR user_id=%s) AND read_at IS NULL", (user.get("user_id"),))
    return jsonify({"count": result.get("count", 0) if result else 0})