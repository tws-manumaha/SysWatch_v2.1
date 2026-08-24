"""
SysWatch v2.1 — Backup Manager
- Database-backed metadata with stable IDs (no more synthetic IDs from file listing)
- Secure mysqldump password handling (uses MYSQL_PWD env var, not command line)
- SHA-256 checksums for backup integrity
- Configurable retention and scheduling
"""
import os
import hashlib
import subprocess
import tarfile
import shutil
import logging
from datetime import datetime, timezone
from pathlib import Path

from modules.config import Config
from modules.database import db
from modules.logging_manager import log_event, utcnow

logger = logging.getLogger("syswatch.backup")


def _get_backup_dir():
    result = db.query_one("SELECT config_value FROM system_config WHERE config_key='backup_dir'")
    if result and result.get("config_value"):
        return result["config_value"]
    return Config.BACKUP_DIR


def _get_retention_days():
    result = db.query_one("SELECT config_value FROM system_config WHERE config_key='backup_retention_days'")
    if result and result.get("config_value"):
        try:
            return int(result["config_value"])
        except ValueError:
            pass
    return Config.BACKUP_RETENTION_DAYS


def create_backup(backup_type="scheduled"):
    backup_dir = _get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"syswatch_backup_{timestamp}.tar.gz"
    filepath = os.path.join(backup_dir, filename)
    temp_dir = os.path.join(backup_dir, f"tmp_{timestamp}")

    backup_id = db.execute_returning_id(
        "INSERT INTO backup_metadata (filename, size_bytes, status, backup_type, created_at) VALUES (%s, 0, 'in_progress', %s, %s)",
        (filename, backup_type, utcnow()),
    )

    try:
        os.makedirs(temp_dir, exist_ok=True)

        db_host = os.getenv("DB_HOST", "localhost")
        db_name = os.getenv("DB_NAME", "syswatch")
        db_user = os.getenv("DB_USER", "syswatch")
        db_password = os.getenv("DB_PASSWORD", "")

        dump_file = os.path.join(temp_dir, "db_dump.sql")
        dump_env = os.environ.copy()
        if db_password:
            dump_env["MYSQL_PWD"] = db_password

        dump_cmd = ["mysqldump", f"-h{db_host}", f"-u{db_user}", "--single-transaction", "--routines", "--triggers", db_name]

        try:
            with open(dump_file, "w") as f:
                subprocess.run(dump_cmd, stdout=f, check=True, timeout=300, env=dump_env)
        except FileNotFoundError:
            logger.warning("mysqldump not found, skipping DB dump")
            with open(dump_file, "w") as f:
                f.write("-- mysqldump not available\n")
        except subprocess.TimeoutExpired:
            logger.error("DB dump timed out")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"DB dump failed: {e}")
            with open(dump_file, "w") as f:
                f.write(f"-- DB dump failed: {e}\n")

        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        env_file = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_file):
            shutil.copy2(env_file, os.path.join(config_dir, ".env"))

        scripts_dir = os.path.join(os.getcwd(), "scripts")
        if os.path.exists(scripts_dir):
            shutil.copytree(scripts_dir, os.path.join(temp_dir, "scripts"), dirs_exist_ok=True)

        with tarfile.open(filepath, "w:gz") as tar:
            tar.add(temp_dir, arcname="backup")

        size = os.path.getsize(filepath)
        checksum = _calculate_checksum(filepath)

        db.execute("UPDATE backup_metadata SET size_bytes=%s, status='completed', checksum=%s WHERE id=%s", (size, checksum, backup_id))

        logger.info(f"Backup created: {filename} ({size} bytes)")
        log_event("backup", "INFO", "backup_completed", f"Backup {filename} created ({size} bytes)", details={"backup_id": backup_id, "checksum": checksum, "type": backup_type})

        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"id": backup_id, "filename": filename, "size_bytes": size, "status": "completed", "checksum": checksum, "type": backup_type}

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        db.execute("UPDATE backup_metadata SET status='failed' WHERE id=%s", (backup_id,))
        log_event("backup", "ERROR", "backup_failed", f"Backup failed: {e}", details={"backup_id": backup_id, "error": str(e)})
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"id": backup_id, "filename": filename, "size_bytes": 0, "status": "failed", "error": str(e), "type": backup_type}


def _calculate_checksum(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def list_backups():
    return db.query("SELECT id, filename, size_bytes, status, backup_type, checksum, created_at FROM backup_metadata ORDER BY created_at DESC")


def get_backup(backup_id):
    return db.query_one("SELECT id, filename, size_bytes, status, backup_type, checksum, created_at FROM backup_metadata WHERE id=%s", (backup_id,))


def delete_backup(backup_id):
    backup = get_backup(backup_id)
    if not backup:
        return False
    filepath = os.path.join(_get_backup_dir(), backup["filename"])
    if os.path.exists(filepath):
        os.remove(filepath)
    db.execute("DELETE FROM backup_metadata WHERE id=%s", (backup_id,))
    log_event("backup", "INFO", "backup_deleted", f"Deleted backup {backup['filename']}", details={"backup_id": backup_id})
    return True


def verify_backup(backup_id):
    backup = get_backup(backup_id)
    if not backup:
        return {"valid": False, "error": "Backup not found"}
    filepath = os.path.join(_get_backup_dir(), backup["filename"])
    if not os.path.exists(filepath):
        return {"valid": False, "error": "Backup file not found on disk"}
    current_checksum = _calculate_checksum(filepath)
    stored_checksum = backup.get("checksum")
    if not stored_checksum:
        db.execute("UPDATE backup_metadata SET checksum=%s WHERE id=%s", (current_checksum, backup_id))
        return {"valid": True, "checksum": current_checksum, "note": "Checksum calculated and stored"}
    return {"valid": current_checksum == stored_checksum, "stored_checksum": stored_checksum, "current_checksum": current_checksum}


def get_backup_filepath(backup_id):
    backup = get_backup(backup_id)
    if not backup:
        return None
    filepath = os.path.join(_get_backup_dir(), backup["filename"])
    return filepath if os.path.exists(filepath) else None


def cleanup_old_backups(retention_days=None):
    if retention_days is None:
        retention_days = _get_retention_days()
    backup_dir = _get_backup_dir()
    old_backups = db.query("SELECT id, filename FROM backup_metadata WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)", (retention_days,))
    deleted_count = 0
    for backup in old_backups:
        filepath = os.path.join(backup_dir, backup["filename"])
        if os.path.exists(filepath):
            os.remove(filepath)
        db.execute("DELETE FROM backup_metadata WHERE id=%s", (backup["id"],))
        deleted_count += 1
    if deleted_count > 0:
        log_event("backup", "INFO", "backups_cleaned", f"Deleted {deleted_count} backups older than {retention_days} days")
    return deleted_count


def get_backup_config():
    config_rows = db.query("SELECT config_key, config_value FROM system_config WHERE config_key IN ('backup_schedule', 'backup_retention_days', 'backup_dir')")
    config = {row["config_key"]: row["config_value"] for row in config_rows}
    return {
        "schedule": config.get("backup_schedule", Config.BACKUP_SCHEDULE),
        "retention_days": int(config.get("backup_retention_days", Config.BACKUP_RETENTION_DAYS)),
        "storage_path": config.get("backup_dir", Config.BACKUP_DIR),
        "remote_enabled": False,
    }


def update_backup_config(schedule=None, retention_days=None, backup_dir=None, updated_by="system"):
    if schedule:
        db.execute("INSERT INTO system_config (config_key, config_value, updated_by) VALUES ('backup_schedule', %s, %s) ON DUPLICATE KEY UPDATE config_value=VALUES(config_value), updated_by=VALUES(updated_by)", (schedule, updated_by))
    if retention_days is not None:
        db.execute("INSERT INTO system_config (config_key, config_value, updated_by) VALUES ('backup_retention_days', %s, %s) ON DUPLICATE KEY UPDATE config_value=VALUES(config_value), updated_by=VALUES(updated_by)", (str(retention_days), updated_by))
    if backup_dir:
        db.execute("INSERT INTO system_config (config_key, config_value, updated_by) VALUES ('backup_dir', %s, %s) ON DUPLICATE KEY UPDATE config_value=VALUES(config_value), updated_by=VALUES(updated_by)", (backup_dir, updated_by))
    log_event("backup", "INFO", "config_updated", "Backup configuration updated", user_id=updated_by, details={"schedule": schedule, "retention_days": retention_days, "backup_dir": backup_dir})
    return True
