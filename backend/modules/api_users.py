"""SysWatch v2.1 - Users & Authentication API"""
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.logging_manager import log_event, utcnow
from modules.security import (validate_input, require_auth, get_current_user, hash_password, verify_password,
    generate_token, generate_refresh_token, verify_refresh_token, revoke_refresh_token,
    check_brute_force, record_failed_attempt, record_successful_login, generate_api_key)

logger = logging.getLogger("syswatch.api_users")
users_bp = Blueprint("users", __name__)


@users_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not email or not password: return jsonify({"error": "Email and password are required"}), 400
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    user_agent = request.headers.get("User-Agent", "")
    if check_brute_force(ip, email): return jsonify({"error": "Too many failed login attempts. Please try again later."}), 429
    user = db.query_one("SELECT id, email, password_hash, role, active FROM users WHERE email=%s", (email,))
    if not user or not verify_password(password, user.get("password_hash", "")):
        record_failed_attempt(ip, email, user_agent)
        return jsonify({"error": "Invalid email or password"}), 401
    if not user.get("active"): return jsonify({"error": "Account is disabled. Contact administrator."}), 403
    access_token = generate_token(user["id"], user["email"], user["role"])
    refresh_token = generate_refresh_token(user["id"])
    record_successful_login(ip, email, user_agent)
    db.execute("UPDATE users SET last_login=NOW() WHERE id=%s", (user["id"],))
    return jsonify({"token": access_token, "refresh_token": refresh_token, "user": {"id": user["id"], "email": user["email"], "role": user["role"]}}), 200


@users_bp.route("/auth/refresh", methods=["POST"])
def refresh_token():
    data = request.get_json() or {}
    refresh = data.get("refresh_token", "")
    if not refresh: return jsonify({"error": "refresh_token is required"}), 400
    user_id = verify_refresh_token(refresh)
    if not user_id: return jsonify({"error": "Invalid or expired refresh token"}), 401
    user = db.query_one("SELECT id, email, role, active FROM users WHERE id=%s", (user_id,))
    if not user or not user.get("active"): return jsonify({"error": "User not found or inactive"}), 401
    revoke_refresh_token(refresh)
    new_access = generate_token(user["id"], user["email"], user["role"])
    new_refresh = generate_refresh_token(user["id"])
    return jsonify({"token": new_access, "refresh_token": new_refresh}), 200


@users_bp.route("/auth/logout", methods=["POST"])
@require_auth()
def logout():
    data = request.get_json() or {}
    refresh = data.get("refresh_token", "")
    if refresh: revoke_refresh_token(refresh)
    log_event("users", "INFO", "logout", "User logged out", user_id=get_current_user().get("email"))
    return jsonify({"message": "Logged out successfully"}), 200


@users_bp.route("/users", methods=["GET"])
@require_auth(roles=["admin"])
def list_users():
    return jsonify(db.query("SELECT id, email, name, role, active, last_login, created_at FROM users ORDER BY email"))


@users_bp.route("/users", methods=["POST"])
@require_auth(roles=["admin"])
def create_user():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    role = data.get("role", "viewer")
    if not email or not password: return jsonify({"error": "Email and password are required"}), 400
    if not validate_input(email, "email"): return jsonify({"error": "Invalid email format"}), 400
    if role not in ["admin", "operator", "viewer"]: return jsonify({"error": "Invalid role"}), 400
    if len(password) < 8: return jsonify({"error": "Password must be at least 8 characters"}), 400
    existing = db.query_one("SELECT id FROM users WHERE email=%s", (email,))
    if existing: return jsonify({"error": "Email already registered"}), 409
    password_hash = hash_password(password)
    user_id = db.execute_returning_id("INSERT INTO users (email, name, password_hash, role, active, created_at) VALUES (%s, %s, %s, %s, TRUE, %s)", (email, name, password_hash, role, utcnow()))
    log_event("users", "INFO", "user_created", f"User {email} created with role {role}", user_id=get_current_user().get("email"))
    return jsonify({"id": user_id, "email": email, "role": role, "name": name}), 201


@users_bp.route("/users/<int:user_id>", methods=["PUT"])
@require_auth(roles=["admin"])
def update_user(user_id):
    data = request.get_json() or {}
    updates = {}
    if "name" in data: updates["name"] = data["name"]
    if "role" in data:
        if data["role"] not in ["admin", "operator", "viewer"]: return jsonify({"error": "Invalid role"}), 400
        updates["role"] = data["role"]
    if "active" in data: updates["active"] = data["active"]
    if "password" in data:
        if len(data["password"]) < 8: return jsonify({"error": "Password must be at least 8 characters"}), 400
        updates["password_hash"] = hash_password(data["password"])
    if not updates: return jsonify({"error": "No fields to update"}), 400
    set_clause = ", ".join(f"{k}=%s" for k in updates)
    db.execute(f"UPDATE users SET {set_clause} WHERE id=%s", tuple(list(updates.values()) + [user_id]))
    log_event("users", "INFO", "user_updated", f"User {user_id} updated", user_id=get_current_user().get("email"))
    return jsonify({"message": "User updated"})


@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_user(user_id):
    current = get_current_user()
    if current.get("user_id") == user_id: return jsonify({"error": "Cannot delete your own account"}), 400
    user = db.query_one("SELECT email FROM users WHERE id=%s", (user_id,))
    if not user: return jsonify({"error": "User not found"}), 404
    db.execute("DELETE FROM users WHERE id=%s", (user_id,))
    log_event("users", "INFO", "user_deleted", f"User {user['email']} deleted", user_id=current.get("email"))
    return jsonify({"message": "User deleted"})


@users_bp.route("/users/me", methods=["GET"])
@require_auth()
def get_current_profile():
    user = get_current_user()
    profile = db.query_one("SELECT id, email, name, role, active, last_login, created_at FROM users WHERE id=%s", (user.get("user_id"),))
    if not profile: return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile)


@users_bp.route("/users/me/password", methods=["PUT"])
@require_auth()
def change_password():
    data = request.get_json() or {}
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")
    if not current_password or not new_password: return jsonify({"error": "current_password and new_password are required"}), 400
    if len(new_password) < 8: return jsonify({"error": "Password must be at least 8 characters"}), 400
    user = get_current_user()
    user_row = db.query_one("SELECT password_hash FROM users WHERE id=%s", (user.get("user_id"),))
    if not user_row or not verify_password(current_password, user_row["password_hash"]): return jsonify({"error": "Current password is incorrect"}), 401
    db.execute("UPDATE users SET password_hash=%s WHERE id=%s", (hash_password(new_password), user.get("user_id")))
    log_event("users", "INFO", "password_changed", "Password changed", user_id=user.get("email"))
    return jsonify({"message": "Password changed successfully"})


@users_bp.route("/users/<int:user_id>/api-keys", methods=["POST"])
@require_auth(roles=["admin"])
def create_api_key(user_id):
    raw_key, key_hash = generate_api_key()
    key_prefix = raw_key[:12]
    db.execute("INSERT INTO api_keys (user_id, key_hash, key_prefix, name, created_at) VALUES (%s, %s, %s, %s, NOW())", (user_id, key_hash, key_prefix, request.get_json().get("name", "API Key")))
    log_event("users", "INFO", "api_key_created", f"API key created for user {user_id}", user_id=get_current_user().get("email"))
    return jsonify({"api_key": raw_key, "prefix": key_prefix, "message": "Store this key securely - it will not be shown again"}), 201