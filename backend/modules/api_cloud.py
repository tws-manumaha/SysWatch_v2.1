"""SysWatch v2.1 - Cloud & Templates API"""
import json
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.logging_manager import log_event, utcnow
from modules.security import require_auth, get_current_user, encrypt_secret

logger = logging.getLogger("syswatch.api_cloud")
cloud_bp = Blueprint("cloud", __name__)


@cloud_bp.route("/cloud/credentials", methods=["GET"])
@require_auth(roles=["admin"])
def list_credentials():
    return jsonify(db.query("SELECT id, provider, name, account_id, region, created_at FROM cloud_credentials ORDER BY provider, name"))


@cloud_bp.route("/cloud/credentials", methods=["POST"])
@require_auth(roles=["admin"])
def add_credentials():
    data = request.get_json() or {}
    provider = data.get("provider", "").strip()
    name = data.get("name", "").strip()
    access_key = data.get("access_key", "").strip()
    secret_key = data.get("secret_key", "").strip()
    if not provider or not name or not access_key or not secret_key:
        return jsonify({"error": "provider, name, access_key, and secret_key are required"}), 400
    enc_access, iv_access = encrypt_secret(access_key)
    enc_secret, iv_secret = encrypt_secret(secret_key)
    cred_id = db.execute_returning_id("INSERT INTO cloud_credentials (provider, name, account_id, access_key_enc, access_key_iv, secret_key_enc, secret_key_iv, region, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (provider, name, data.get("account_id", ""), enc_access, iv_access, enc_secret, iv_secret, data.get("region", ""), utcnow()))
    log_event("cloud", "INFO", "credentials_added", f"Cloud credentials for {provider}/{name} added", user_id=get_current_user().get("email"))
    return jsonify({"id": cred_id, "provider": provider, "name": name}), 201


@cloud_bp.route("/cloud/credentials/<int:cred_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_credentials(cred_id):
    db.execute("DELETE FROM cloud_credentials WHERE id=%s", (cred_id,))
    log_event("cloud", "INFO", "credentials_deleted", f"Cloud credentials {cred_id} deleted", user_id=get_current_user().get("email"))
    return jsonify({"message": "Credentials deleted"})


@cloud_bp.route("/templates", methods=["GET"])
@require_auth()
def list_templates():
    return jsonify(db.query("SELECT id, name, provider, instance_type, region, created_at FROM launch_templates ORDER BY name"))


@cloud_bp.route("/templates", methods=["POST"])
@require_auth(roles=["admin"])
def create_template():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name: return jsonify({"error": "Template name is required"}), 400
    template_id = db.execute_returning_id("INSERT INTO launch_templates (name, provider, instance_type, region, ami_image, security_groups, created_by, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (name, data.get("provider", "aws"), data.get("instance_type", "t3.micro"), data.get("region", "us-east-1"), data.get("ami_image", ""), json.dumps(data.get("security_groups", [])), get_current_user().get("email"), utcnow()))
    log_event("cloud", "INFO", "template_created", f"Launch template '{name}' created", user_id=get_current_user().get("email"))
    return jsonify({"id": template_id, "name": name}), 201


@cloud_bp.route("/templates/<int:template_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_template(template_id):
    db.execute("DELETE FROM launch_templates WHERE id=%s", (template_id,))
    return jsonify({"message": "Template deleted"})