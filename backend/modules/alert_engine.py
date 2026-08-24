"""
SysWatch v2.1 — Alert Engine
Evaluates alert rules against live metrics and creates/triggers alerts.
Supports: >, <, >=, <=, =, != operators
Implements cooldown and duration (consecutive breach count) logic.
Creates notification entries for triggered alerts.
"""
import json
import logging
from datetime import timedelta
from typing import Optional

from modules.database import db
from modules.logging_manager import log_event, utcnow

logger = logging.getLogger("syswatch.alert_engine")


def _compare(value: float, operator: str, threshold: float) -> bool:
    """Compare a value against a threshold using the given operator."""
    ops = {
        ">": lambda v, t: v > t,
        "<": lambda v, t: v < t,
        ">=": lambda v, t: v >= t,
        "<=": lambda v, t: v <= t,
        "=": lambda v, t: v == t,
        "!=": lambda v, t: v != t,
    }
    return ops.get(operator, lambda v, t: False)(value, threshold)


def _get_all_hosts_latest_metrics() -> dict:
    """Get the latest metric for each host. Returns dict[hostname -> metric_dict]."""
    metrics = db.query(
        """SELECT m.* FROM metrics m
           INNER JOIN (
             SELECT hostname, MAX(timestamp) as max_ts
             FROM metrics GROUP BY hostname
           ) latest ON m.hostname = latest.hostname AND m.timestamp = latest.max_ts"""
    )
    return {m["hostname"]: m for m in metrics}


def _check_cooldown(rule_id: int, cooldown_seconds: int) -> bool:
    """Returns True if still in cooldown (should NOT trigger), False if OK to trigger."""
    result = db.query_one(
        "SELECT last_triggered FROM alerts WHERE rule_id=%s AND last_triggered IS NOT NULL ORDER BY last_triggered DESC LIMIT 1",
        (rule_id,),
    )
    if not result or not result.get("last_triggered"):
        return False
    last_triggered = result["last_triggered"]
    if hasattr(last_triggered, "tzinfo") and last_triggered.tzinfo is None:
        last_triggered = last_triggered.replace(tzinfo=utcnow().tzinfo)
    elapsed = (utcnow() - last_triggered).total_seconds()
    return elapsed < cooldown_seconds


def _check_duration_breach(hostname: str, metric: str, operator: str,
                           threshold: float, duration_checks: int) -> bool:
    """Check if the condition has been breached for N consecutive checks."""
    if duration_checks <= 1:
        return True
    recent = db.query(
        "SELECT * FROM metrics WHERE hostname=%s ORDER BY timestamp DESC LIMIT %s",
        (hostname, duration_checks),
    )
    if len(recent) < duration_checks:
        return False
    for m in recent:
        value = m.get(metric)
        if value is None:
            return False
        if not _compare(float(value), operator, float(threshold)):
            return False
    return True


def evaluate_alert_rules():
    """Main alert evaluation function. Called by the scheduler."""
    logger.info("Starting alert rule evaluation")
    rules = db.query("SELECT * FROM alert_rules WHERE enabled=TRUE")
    if not rules:
        logger.info("No enabled alert rules found")
        return {"evaluated": 0, "triggered": 0, "skipped": 0}

    latest_metrics = _get_all_hosts_latest_metrics()
    triggered_count = 0
    skipped_count = 0

    for rule in rules:
        hostname = rule["hostname"]
        metric = rule["metric"]
        operator = rule["operator"]
        threshold = float(rule["threshold"])
        cooldown = int(rule["cooldown"])
        duration = int(rule["duration"])

        if hostname == "%":
            hosts_to_check = list(latest_metrics.keys())
        else:
            hosts_to_check = [hostname] if hostname in latest_metrics else []

        for host in hosts_to_check:
            metric_row = latest_metrics.get(host)
            if not metric_row:
                continue
            value = metric_row.get(metric)
            if value is None:
                if metric == "status":
                    host_info = db.query_one("SELECT status FROM hosts WHERE hostname=%s", (host,))
                    if host_info:
                        value = 1 if host_info["status"] == "UP" else 0
                    else:
                        continue
                else:
                    continue
            value = float(value)

            if not _compare(value, operator, threshold):
                continue
            if not _check_duration_breach(host, metric, operator, threshold, duration):
                continue
            if _check_cooldown(rule["id"], cooldown):
                skipped_count += 1
                continue
            _trigger_alert(rule, host, value)
            triggered_count += 1

    logger.info(f"Alert evaluation: {len(rules)} rules, {triggered_count} triggered, {skipped_count} skipped")
    return {"evaluated": len(rules), "triggered": triggered_count, "skipped": skipped_count}


def _trigger_alert(rule: dict, hostname: str, value: float):
    """Create a new alert, event, and notification."""
    rule_id = rule["id"]
    existing = db.query_one(
        "SELECT id FROM alerts WHERE rule_id=%s AND hostname=%s AND status='OPEN'",
        (rule_id, hostname),
    )
    if existing:
        db.execute("UPDATE alerts SET last_triggered=%s, value=%s WHERE id=%s", (utcnow(), value, existing["id"]))
        logger.info(f"Updated existing alert {existing['id']} for {hostname}")
    else:
        alert_id = db.execute_returning_id(
            "INSERT INTO alerts (rule_id, hostname, metric, value, threshold, operator, severity, status, cause, action, triggered_at, last_triggered) VALUES (%s, %s, %s, %s, %s, %s, %s, 'OPEN', %s, %s, %s, %s)",
            (rule_id, hostname, rule["metric"], value, rule["threshold"], rule["operator"], rule["severity"], rule.get("cause", ""), rule.get("action", ""), utcnow(), utcnow()),
        )
        db.execute("INSERT INTO events (event_type, hostname, source, details, event_time) VALUES (%s, %s, %s, %s, %s)",
            ("alert_triggered", hostname, "alert_engine", json.dumps({"alert_id": alert_id, "metric": rule["metric"], "value": str(value)}), utcnow()))
        db.execute("INSERT INTO notifications (user_id, type, title, message, severity, source_id, source_type) VALUES (NULL, 'alert', %s, %s, %s, %s, 'alert')",
            (f"Alert: {hostname}", f"{hostname}: {rule.get('cause', rule['metric'])} — {rule['metric']}={value}", rule["severity"], alert_id))
        log_event("alerts", "WARNING" if rule["severity"] != "CRITICAL" else "ERROR", "alert_triggered",
            f"Alert: {hostname} {rule['metric']}={value} (rule: {rule['name']})", hostname=hostname,
            details={"alert_id": alert_id, "rule_id": rule_id})
