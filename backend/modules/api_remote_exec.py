"""SysWatch v2.1 - Remote Execution API
- Real SSH command execution via paramiko
- Encrypted credential storage (AES-256-GCM)
- Command allowlist/denylist for safety
- Full audit trail of every command executed
- Human-in-the-loop: AI suggestions must be approved before execution
"""
import json
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.logging_manager import log_event, utcnow
from modules.security import validate_input, require_auth, get_current_user, decrypt_secret

logger = logging.getLogger("syswatch.api_remote_exec")
remote_exec_bp = Blueprint("remote_exec", __name__)

try:
    import paramiko
    _HAS_PARAMIKO = True
except ImportError:
    _HAS_PARAMIKO = False
    logger.warning("paramiko not installed - remote execution unavailable")

BLOCKED_COMMANDS = ["rm -rf /", "mkfs", "dd if=", "shutdown", "reboot", "halt", ":(){:|:&};:", "> /dev/sda", "chmod -R 777 /", "iptables -F", "iptables -P", "systemctl stop sshd", "systemctl stop ssh", "userdel", "groupdel"]


def _is_command_safe(command):
    if not command or not command.strip(): return False, "Empty command"
    cmd_lower = command.lower().strip()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower: return False, f"Blocked command pattern: {blocked}"
    return True, "OK"


def _get_ssh_credentials(hostname):
    host = db.query_one("SELECT hostname, ip, ssh_port, ssh_user, ssh_password_enc, ssh_key_enc, ssh_key_iv, ssh_password_iv FROM hosts WHERE hostname=%s", (hostname,))
    if not host: return None
    creds = {"hostname": host["hostname"], "ip": host["ip"], "port": host.get("ssh_port") or 22, "username": host.get("ssh_user") or "root", "password": None, "key_filename": None}
    if host.get("ssh_password_enc") and host.get("ssh_password_iv"):
        try: creds["password"] = decrypt_secret(host["ssh_password_enc"], host["ssh_password_iv"])
        except Exception as e: logger.error(f"Failed to decrypt SSH password for {hostname}: {e}")
    if host.get("ssh_key_enc") and host.get("ssh_key_iv"):
        try:
            import tempfile, os
            key_text = decrypt_secret(host["ssh_key_enc"], host["ssh_key_iv"])
            key_file = tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False)
            key_file.write(key_text); key_file.close(); os.chmod(key_file.name, 0o600)
            creds["key_filename"] = key_file.name
        except Exception as e: logger.error(f"Failed to decrypt SSH key for {hostname}: {e}")
    return creds


def execute_command_on_host(hostname, command, timeout=30):
    if not _HAS_PARAMIKO: return {"success": False, "error": "paramiko not installed", "exit_code": -1}
    if not validate_input(hostname, "hostname"): return {"success": False, "error": "Invalid hostname", "exit_code": -1}
    safe, reason = _is_command_safe(command)
    if not safe: return {"success": False, "error": f"Command rejected: {reason}", "exit_code": -1}
    creds = _get_ssh_credentials(hostname)
    if not creds: return {"success": False, "error": f"Host '{hostname}' not found", "exit_code": -1}
    if not creds["password"] and not creds["key_filename"]: return {"success": False, "error": "No SSH credentials configured", "exit_code": -1}
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(creds["ip"], port=creds["port"], username=creds["username"], password=creds["password"], key_filename=creds["key_filename"], timeout=10)
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="replace")
        error_output = stderr.read().decode("utf-8", errors="replace")
        if error_output and not output: output = error_output
        ssh.close()
        if creds.get("key_filename"):
            import os
            try: os.unlink(creds["key_filename"])
            except: pass
        return {"success": True, "output": output, "exit_code": exit_code}
    except paramiko.AuthenticationException: return {"success": False, "error": "SSH authentication failed", "exit_code": -1}
    except paramiko.SSHException as e: return {"success": False, "error": f"SSH error: {e}", "exit_code": -1}
    except Exception as e: return {"success": False, "error": f"Connection error: {e}", "exit_code": -1}
    finally:
        try: ssh.close()
        except: pass


@remote_exec_bp.route("/remote/exec", methods=["POST"])
@require_auth(roles=["admin"])
def execute_remote_command():
    data = request.get_json() or {}
    hostname = data.get("hostname", "").strip()
    command = data.get("command", "").strip()
    if not hostname or not command: return jsonify({"error": "hostname and command are required"}), 400
    if not validate_input(hostname, "hostname"): return jsonify({"error": "Invalid hostname"}), 400
    if not validate_input(command, "command"): return jsonify({"error": "Invalid command characters"}), 400
    safe, reason = _is_command_safe(command)
    if not safe: return jsonify({"error": reason}), 403
    user = get_current_user()
    timeout = min(int(data.get("timeout", 30)), 120)
    exec_id = db.execute_returning_id("INSERT INTO remote_executions (hostname, command, requested_by, status, requested_at) VALUES (%s, %s, %s, 'running', %s)", (hostname, command, user.get("email"), utcnow()))
    result = execute_command_on_host(hostname, command, timeout=timeout)
    if result["success"]:
        db.execute("UPDATE remote_executions SET status='completed', exit_code=%s, output=%s, completed_at=%s WHERE id=%s", (result["exit_code"], result["output"][:10000], utcnow(), exec_id))
        log_event("remote_exec", "INFO", "command_executed", f"Command executed on {hostname}: {command[:80]}", user_id=user.get("email"), hostname=hostname, details={"exec_id": exec_id, "exit_code": result["exit_code"]})
        return jsonify({"exec_id": exec_id, "output": result["output"], "exit_code": result["exit_code"], "status": "completed"})
    else:
        db.execute("UPDATE remote_executions SET status='failed', error=%s, completed_at=%s WHERE id=%s", (result.get("error", "Unknown"), utcnow(), exec_id))
        log_event("remote_exec", "ERROR", "command_failed", f"Command failed on {hostname}: {command[:80]}", user_id=user.get("email"), hostname=hostname, details={"exec_id": exec_id, "error": result.get("error")})
        return jsonify({"exec_id": exec_id, "error": result.get("error"), "status": "failed"}), 500


@remote_exec_bp.route("/remote/executions", methods=["GET"])
@require_auth(roles=["admin", "operator"])
def list_executions():
    limit = min(int(request.args.get("limit", 50)), 500)
    hostname = request.args.get("hostname")
    if hostname: return jsonify(db.query("SELECT * FROM remote_executions WHERE hostname=%s ORDER BY requested_at DESC LIMIT %s", (hostname, limit)))
    return jsonify(db.query("SELECT * FROM remote_executions ORDER BY requested_at DESC LIMIT %s", (limit,)))


@remote_exec_bp.route("/remote/executions/<int:exec_id>", methods=["GET"])
@require_auth(roles=["admin", "operator"])
def get_execution(exec_id):
    execution = db.query_one("SELECT * FROM remote_executions WHERE id=%s", (exec_id,))
    if not execution: return jsonify({"error": "Execution not found"}), 404
    return jsonify(execution)


@remote_exec_bp.route("/remote/remediations", methods=["GET"])
@require_auth(roles=["admin", "operator"])
def list_remediations():
    status = request.args.get("status", "pending")
    limit = min(int(request.args.get("limit", 50)), 500)
    return jsonify(db.query("SELECT * FROM remediation_suggestions WHERE status=%s ORDER BY generated_at DESC LIMIT %s", (status, limit)))


@remote_exec_bp.route("/remote/remediations/<int:suggestion_id>/approve", methods=["POST"])
@require_auth(roles=["admin"])
def approve_remediation(suggestion_id):
    from modules.ai.assistant import approve_suggestion
    data = request.get_json() or {}
    result = approve_suggestion(suggestion_id, get_current_user().get("email"), data.get("modified_command"))
    if not result["success"]: return jsonify(result), 400
    return jsonify(result)


@remote_exec_bp.route("/remote/remediations/<int:suggestion_id>/reject", methods=["POST"])
@require_auth(roles=["admin"])
def reject_remediation(suggestion_id):
    from modules.ai.assistant import reject_suggestion
    data = request.get_json() or {}
    result = reject_suggestion(suggestion_id, get_current_user().get("email"), data.get("reason"))
    if not result["success"]: return jsonify(result), 400
    return jsonify(result)


@remote_exec_bp.route("/remote/remediations/<int:suggestion_id>/execute", methods=["POST"])
@require_auth(roles=["admin"])
def execute_remediation(suggestion_id):
    from modules.ai.assistant import execute_suggestion
    data = request.get_json() or {}
    hostname = data.get("hostname", "")
    if not hostname:
        suggestion = db.query_one("SELECT hostname FROM remediation_suggestions WHERE id=%s", (suggestion_id,))
        if suggestion: hostname = suggestion["hostname"]
    if not hostname: return jsonify({"error": "hostname is required"}), 400
    result = execute_suggestion(suggestion_id, get_current_user().get("email"), hostname)
    if not result["success"]: return jsonify(result), 500
    return jsonify(result)