"""SysWatch v2.1 - Backups API"""
import logging
from flask import Blueprint, request, jsonify, send_file
from modules.logging_manager import log_event
from modules.security import require_auth, get_current_user
from modules.backup_manager import create_backup, list_backups, delete_backup, verify_backup, get_backup_filepath, get_backup_config, update_backup_config

logger = logging.getLogger("syswatch.api_backups")
backups_bp = Blueprint("backups", __name__)


@backups_bp.route("/backups", methods=["GET"])
@require_auth(roles=["admin"])
def list_all():
    return jsonify(list_backups())


@backups_bp.route("/backups", methods=["POST"])
@require_auth(roles=["admin"])
def create():
    result = create_backup(backup_type="manual")
    log_event("backup", "INFO", "backup_manual", f"Manual backup created: {result.get('filename')}", user_id=get_current_user().get("email"))
    if result["status"] == "completed": return jsonify(result), 201
    return jsonify(result), 500


@backups_bp.route("/backups/<int:backup_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete(backup_id):
    if delete_backup(backup_id): return jsonify({"message": "Backup deleted"})
    return jsonify({"error": "Backup not found"}), 404


@backups_bp.route("/backups/<int:backup_id>/verify", methods=["POST"])
@require_auth(roles=["admin"])
def verify(backup_id):
    return jsonify(verify_backup(backup_id))


@backups_bp.route("/backups/<int:backup_id>/download", methods=["GET"])
@require_auth(roles=["admin"])
def download(backup_id):
    filepath = get_backup_filepath(backup_id)
    if not filepath: return jsonify({"error": "Backup file not found"}), 404
    return send_file(filepath, as_attachment=True)


@backups_bp.route("/backups/config", methods=["GET"])
@require_auth(roles=["admin"])
def get_config():
    return jsonify(get_backup_config())


@backups_bp.route("/backups/config", methods=["PUT"])
@require_auth(roles=["admin"])
def update_config():
    data = request.get_json() or {}
    update_backup_config(schedule=data.get("schedule"), retention_days=data.get("retention_days"), backup_dir=data.get("storage_path"), updated_by=get_current_user().get("email"))
    return jsonify({"message": "Backup configuration updated"})