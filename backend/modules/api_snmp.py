"""SysWatch v2.1 - SNMP Polling API"""
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.logging_manager import log_event, utcnow
from modules.security import require_auth, get_current_user, decrypt_secret, encrypt_secret

logger = logging.getLogger("syswatch.api_snmp")
snmp_bp = Blueprint("snmp", __name__)

try:
    from pysnmp.hlapi import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
    _HAS_PYSNMP = True
except ImportError:
    _HAS_PYSNMP = False
    logger.warning("pysnmp not installed - SNMP polling unavailable")


def _snmp_get(ip, community, oid, port=161, timeout=5):
    if not _HAS_PYSNMP: return None
    try:
        iterator = getCmd(SnmpEngine(), CommunityData(community), UdpTransportTarget((ip, port), timeout=timeout, retries=1), ContextData(), ObjectType(ObjectIdentity(oid)))
        error_indication, error_status, error_index, var_binds = next(iterator)
        if error_indication or error_status: return None
        for var_bind in var_binds: return str(var_bind[1])
    except Exception: return None
    return None


@snmp_bp.route("/snmp/devices", methods=["GET"])
@require_auth()
def list_snmp_devices():
    return jsonify(db.query("SELECT id, hostname, ip, community, snmp_port, enabled FROM snmp_devices ORDER BY hostname"))


@snmp_bp.route("/snmp/devices", methods=["POST"])
@require_auth(roles=["admin"])
def add_snmp_device():
    data = request.get_json() or {}
    hostname = data.get("hostname", "").strip()
    ip = data.get("ip", "").strip()
    community = data.get("community", "public")
    port = int(data.get("port", 161))
    if not hostname or not ip: return jsonify({"error": "hostname and ip are required"}), 400
    enc_community, iv = encrypt_secret(community) if community else (None, None)
    device_id = db.execute_returning_id("INSERT INTO snmp_devices (hostname, ip, community, community_enc, community_iv, snmp_port, enabled, created_at) VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s)", (hostname, ip, community, enc_community, iv, port, utcnow()))
    log_event("snmp", "INFO", "device_added", f"SNMP device {hostname} added", user_id=get_current_user().get("email"))
    return jsonify({"id": device_id, "hostname": hostname, "ip": ip}), 201


@snmp_bp.route("/snmp/devices/<int:device_id>", methods=["DELETE"])
@require_auth(roles=["admin"])
def delete_snmp_device(device_id):
    db.execute("DELETE FROM snmp_devices WHERE id=%s", (device_id,))
    return jsonify({"message": "SNMP device deleted"})


@snmp_bp.route("/snmp/devices/<int:device_id>/poll", methods=["POST"])
@require_auth()
def poll_device(device_id):
    device = db.query_one("SELECT * FROM snmp_devices WHERE id=%s", (device_id,))
    if not device: return jsonify({"error": "Device not found"}), 404
    community = "public"
    if device.get("community_enc") and device.get("community_iv"):
        try: community = decrypt_secret(device["community_enc"], device["community_iv"])
        except Exception: community = device.get("community", "public")
    oids = {"sysDescr": "1.3.6.1.2.1.1.1.0", "sysUpTime": "1.3.6.1.2.1.1.3.0", "sysName": "1.3.6.1.2.1.1.5.0", "sysLocation": "1.3.6.1.2.1.1.6.0"}
    results = {}
    for name, oid in oids.items():
        results[name] = _snmp_get(device["ip"], community, oid, port=device.get("snmp_port", 161))
    if not any(results.values()): return jsonify({"error": "SNMP polling failed", "results": results}), 503
    return jsonify({"device_id": device_id, "hostname": device["hostname"], "results": results})


def poll_snmp_devices():
    if not _HAS_PYSNMP:
        logger.warning("pysnmp not available - skipping SNMP poll")
        return {"polled": 0, "success": 0, "failed": 0}
    devices = db.query("SELECT * FROM snmp_devices WHERE enabled=TRUE")
    success = 0; failed = 0
    for device in devices:
        community = "public"
        if device.get("community_enc") and device.get("community_iv"):
            try: community = decrypt_secret(device["community_enc"], device["community_iv"])
            except Exception: community = device.get("community", "public")
        sysname = _snmp_get(device["ip"], community, "1.3.6.1.2.1.1.5.0", port=device.get("snmp_port", 161))
        if sysname:
            db.execute("UPDATE snmp_devices SET last_polled=%s, last_response=%s WHERE id=%s", (utcnow(), sysname, device["id"]))
            success += 1
        else:
            db.execute("UPDATE snmp_devices SET last_polled=%s WHERE id=%s", (utcnow(), device["id"]))
            failed += 1
    logger.info(f"SNMP poll: {len(devices)} devices, {success} success, {failed} failed")
    return {"polled": len(devices), "success": success, "failed": failed}