"""SysWatch v2.1 - Security API"""
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.security import assess_security_posture, require_auth, get_current_user
from modules.logging_manager import log_event

logger = logging.getLogger("syswatch.api_security")
security_bp = Blueprint("security", __name__)


@security_bp.route("/security/posture", methods=["GET"])
@require_auth()
def security_posture():
    return jsonify(assess_security_posture())


@security_bp.route("/security/audit-log", methods=["GET"])
@require_auth(roles=["admin"])
def audit_log():
    limit = min(int(request.args.get("limit", 100)), 500)
    action = request.args.get("action")
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if action: query += " AND action=%s"; params.append(action)
    query += " ORDER BY timestamp DESC LIMIT %s"; params.append(limit)
    return jsonify(db.query(query, tuple(params)))


@security_bp.route("/security/api-keys", methods=["GET"])
@require_auth(roles=["admin"])
def list_api_keys():
    keys = db.query("SELECT ak.id, ak.name, ak.key_prefix, ak.last_used, ak.created_at, u.email FROM api_keys ak JOIN users u ON ak.user_id=u.id ORDER BY ak.created_at DESC")
    return jsonify(keys)


@security_bp.route("/security/api-keys/<int:key_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def revoke_api_key(key_id):
    db.execute("DELETE FROM api_keys WHERE id=%s", (key_id,))
    log_event("security", "INFO", "api_key_revoked", f"API key {key_id} revoked", user_id=get_current_user().get("email"))
    return jsonify({"message": "API key revoked"})