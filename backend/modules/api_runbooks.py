"""SysWatch v2.1 - Runbooks API (FIXED: no more SyntaxError)"""
import json
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.logging_manager import log_event, utcnow
from modules.security import require_auth, get_current_user

logger = logging.getLogger("syswatch.api_runbooks")
runbooks_bp = Blueprint("runbooks", __name__)


@runbooks_bp.route("/runbooks", methods=["GET"])
@require_auth()
def list_runbooks():
    return jsonify(db.query("SELECT * FROM runbooks ORDER BY name"))


@runbooks_bp.route("/runbooks/<int:runbook_id>", methods=["GET"])
@require_auth()
def get_runbook(runbook_id):
    runbook = db.query_one("SELECT * FROM runbooks WHERE id=%s", (runbook_id,))
    if not runbook: return jsonify({"error": "Runbook not found"}), 404
    steps = db.query("SELECT * FROM runbook_steps WHERE runbook_id=%s ORDER BY step_number", (runbook_id,))
    runbook["steps"] = steps
    return jsonify(runbook)


@runbooks_bp.route("/runbooks", methods=["POST"])
@require_auth(roles=["admin"])
def create_runbook():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name: return jsonify({"error": "Runbook name is required"}), 400
    runbook_id = db.execute_returning_id("INSERT INTO runbooks (name, description, category, created_by, created_at) VALUES (%s, %s, %s, %s, %s)", (name, data.get("description", ""), data.get("category", "general"), get_current_user().get("email"), utcnow()))
    for i, step in enumerate(data.get("steps", [])):
        db.execute("INSERT INTO runbook_steps (runbook_id, step_number, action, command, expected_result) VALUES (%s, %s, %s, %s, %s)", (runbook_id, i + 1, step.get("action", ""), step.get("command", ""), step.get("expected_result", "")))
    log_event("runbooks", "INFO", "runbook_created", f"Runbook '{name}' created", user_id=get_current_user().get("email"))
    return jsonify({"id": runbook_id, "message": "Runbook created"}), 201


@runbooks_bp.route("/runbooks/<int:runbook_id>", methods=["PUT"])
@require_auth(roles=["admin"])
def update_runbook(runbook_id):
    data = request.get_json() or {}
    updates = {}
    for field in ["name", "description", "category"]:
        if field in data: updates[field] = data[field]
    if updates:
        set_clause = ", ".join(f"{k}=%s" for k in updates)
        db.execute(f"UPDATE runbooks SET {set_clause} WHERE id=%s", tuple(list(updates.values()) + [runbook_id]))
    if "steps" in data:
        db.execute("DELETE FROM runbook_steps WHERE runbook_id=%s", (runbook_id,))
        for i, step in enumerate(data["steps"]):
            db.execute("INSERT INTO runbook_steps (runbook_id, step_number, action, command, expected_result) VALUES (%s, %s, %s, %s, %s)", (runbook_id, i + 1, step.get("action", ""), step.get("command", ""), step.get("expected_result", "")))
    log_event("runbooks", "INFO", "runbook_updated", f"Runbook {runbook_id} updated", user_id=get_current_user().get("email"))
    return jsonify({"message": "Runbook updated"})


@runbooks_bp.route("/runbooks/<int:runbook_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_runbook(runbook_id):
    db.execute("DELETE FROM runbook_steps WHERE runbook_id=%s", (runbook_id,))
    db.execute("DELETE FROM runbooks WHERE id=%s", (runbook_id,))
    log_event("runbooks", "INFO", "runbook_deleted", f"Runbook {runbook_id} deleted", user_id=get_current_user().get("email"))
    return jsonify({"message": "Runbook deleted"})


@runbooks_bp.route("/runbooks/<int:runbook_id>/execute", methods=["POST"])
@require_auth(roles=["admin"])
def execute_runbook(runbook_id):
    runbook = db.query_one("SELECT * FROM runbooks WHERE id=%s", (runbook_id,))
    if not runbook: return jsonify({"error": "Runbook not found"}), 404
    steps = db.query("SELECT * FROM runbook_steps WHERE runbook_id=%s ORDER BY step_number", (runbook_id,))
    execution_id = db.execute_returning_id("INSERT INTO runbook_executions (runbook_id, executed_by, status, started_at) VALUES (%s, %s, 'running', %s)", (runbook_id, get_current_user().get("email"), utcnow()))
    first_step = steps[0] if steps else None
    return jsonify({"execution_id": execution_id, "runbook_id": runbook_id, "total_steps": len(steps), "current_step": first_step, "message": "Runbook execution started. Confirm each step to proceed."})