"""SysWatch v2.1 - Alerts API"""
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.logging_manager import log_event, utcnow
from modules.security import validate_input, require_auth, get_current_user

logger = logging.getLogger("syswatch.api_alerts")
alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/alerts", methods=["GET"])
@require_auth()
def list_alerts():
    status = request.args.get("status")
    severity = request.args.get("severity")
    hostname = request.args.get("hostname")
    limit = min(int(request.args.get("limit", 50)), 500)
    query = "SELECT * FROM alerts WHERE 1=1"
    params = []
    if status: query += " AND status=%s"; params.append(status)
    if severity: query += " AND severity=%s"; params.append(severity)
    if hostname: query += " AND hostname=%s"; params.append(hostname)
    query += " ORDER BY triggered_at DESC LIMIT %s"; params.append(limit)
    return jsonify(db.query(query, tuple(params)))


@alerts_bp.route("/alerts/<int:alert_id>", methods=["GET"])
@require_auth()
def get_alert(alert_id):
    alert = db.query_one("SELECT * FROM alerts WHERE id=%s", (alert_id,))
    if not alert: return jsonify({"error": "Alert not found"}), 404
    return jsonify(alert)


@alerts_bp.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
@require_auth(roles=["admin", "operator"])
def acknowledge_alert(alert_id):
    alert = db.query_one("SELECT id FROM alerts WHERE id=%s", (alert_id,))
    if not alert: return jsonify({"error": "Alert not found"}), 404
    user = get_current_user()
    db.execute("UPDATE alerts SET status='ACKNOWLEDGED', acknowledged_by=%s, acknowledged_at=%s WHERE id=%s", (user.get("email"), utcnow(), alert_id))
    log_event("alerts", "INFO", "alert_acknowledged", f"Alert {alert_id} acknowledged", user_id=user.get("email"))
    return jsonify({"message": "Alert acknowledged", "alert_id": alert_id, "status": "ACKNOWLEDGED"})


@alerts_bp.route("/alerts/<int:alert_id>/resolve", methods=["POST"])
@require_auth(roles=["admin", "operator"])
def resolve_alert(alert_id):
    alert = db.query_one("SELECT id FROM alerts WHERE id=%s", (alert_id,))
    if not alert: return jsonify({"error": "Alert not found"}), 404
    user = get_current_user()
    db.execute("UPDATE alerts SET status='RESOLVED', resolved_by=%s, resolved_at=%s WHERE id=%s", (user.get("email"), utcnow(), alert_id))
    log_event("alerts", "INFO", "alert_resolved", f"Alert {alert_id} resolved", user_id=user.get("email"))
    return jsonify({"message": "Alert resolved", "alert_id": alert_id, "status": "RESOLVED"})


@alerts_bp.route("/alerts/<int:alert_id>/notes", methods=["POST"])
@require_auth(roles=["admin", "operator"])
def add_alert_note(alert_id):
    data = request.get_json() or {}
    note = data.get("note", "").strip()
    if not note: return jsonify({"error": "Note text required"}), 400
    alert = db.query_one("SELECT id, notes FROM alerts WHERE id=%s", (alert_id,))
    if not alert: return jsonify({"error": "Alert not found"}), 404
    import json
    existing_notes = json.loads(alert.get("notes") or "[]")
    existing_notes.append({"user": get_current_user().get("email"), "note": note, "timestamp": utcnow().isoformat()})
    db.execute("UPDATE alerts SET notes=%s WHERE id=%s", (json.dumps(existing_notes), alert_id))
    return jsonify({"message": "Note added", "notes": existing_notes})


@alerts_bp.route("/alert-rules", methods=["GET"])
@require_auth()
def list_alert_rules():
    return jsonify(db.query("SELECT * FROM alert_rules ORDER BY hostname, metric"))


@alerts_bp.route("/alert-rules", methods=["POST"])
@require_auth(roles=["admin"])
def create_alert_rule():
    data = request.get_json() or {}
    for field in ["name", "hostname", "metric", "operator", "threshold", "severity"]:
        if field not in data: return jsonify({"error": f"Field '{field}' is required"}), 400
    if data["operator"] not in [">", "<", ">=", "<=", "=", "!="]: return jsonify({"error": "Invalid operator"}), 400
    if data["severity"] not in ["INFO", "WARNING", "CRITICAL"]: return jsonify({"error": "Invalid severity"}), 400
    rule_id = db.execute_returning_id("INSERT INTO alert_rules (name, hostname, metric, operator, threshold, severity, cooldown, duration, enabled, cause, action, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s)", (data["name"], data["hostname"], data["metric"], data["operator"], float(data["threshold"]), data["severity"], int(data.get("cooldown", 300)), int(data.get("duration", 1)), data.get("cause", ""), data.get("action", ""), utcnow()))
    log_event("alerts", "INFO", "rule_created", f"Alert rule '{data['name']}' created", user_id=get_current_user().get("email"))
    return jsonify({"id": rule_id, "message": "Alert rule created"}), 201


@alerts_bp.route("/alert-rules/<int:rule_id>", methods=["PUT"])
@require_auth(roles=["admin"])
def update_alert_rule(rule_id):
    data = request.get_json() or {}
    fields = ["name", "hostname", "metric", "operator", "threshold", "severity", "cooldown", "duration", "enabled", "cause", "action"]
    updates = {k: data[k] for k in fields if k in data}
    if not updates: return jsonify({"error": "No fields to update"}), 400
    set_clause = ", ".join(f"{k}=%s" for k in updates)
    values = list(updates.values()) + [rule_id]
    db.execute(f"UPDATE alert_rules SET {set_clause} WHERE id=%s", tuple(values))
    log_event("alerts", "INFO", "rule_updated", f"Alert rule {rule_id} updated", user_id=get_current_user().get("email"))
    return jsonify({"message": "Rule updated", "rule_id": rule_id})


@alerts_bp.route("/alert-rules/<int:rule_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_alert_rule(rule_id):
    db.execute("DELETE FROM alert_rules WHERE id=%s", (rule_id,))
    log_event("alerts", "INFO", "rule_deleted", f"Alert rule {rule_id} deleted", user_id=get_current_user().get("email"))
    return jsonify({"message": "Rule deleted"})