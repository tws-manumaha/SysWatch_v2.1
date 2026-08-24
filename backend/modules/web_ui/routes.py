"""SysWatch v2.1 - Web UI Routes
Serves all Jinja2 template pages. Auth via session token or API key.
"""
import os
from flask import Blueprint, render_template, redirect, url_for, request, session, jsonify
from datetime import datetime, timezone

from modules.config import Config
from modules.database import db
from modules.security import verify_token, verify_api_key, hash_password, verify_password
from modules.logging_manager import log_event, utcnow

web_ui_bp = Blueprint("web_ui", __name__)


def _check_auth():
    """Check if the current request is authenticated.
    Returns the user dict if authenticated, None otherwise.
    """
    # Check session first
    token = session.get("token")
    if token:
        user = verify_token(token)
        if user:
            return user

    # Check Authorization header (Bearer token or API key)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user = verify_token(token)
        if user:
            return user
    elif auth_header.startswith("ApiKey "):
        raw_key = auth_header[7:]
        user = verify_api_key(raw_key)
        if user:
            return user

    return None


@web_ui_bp.route("/")
def dashboard():
    user = _check_auth()
    if not user:
        return redirect("/login")

    # Get summary stats for dashboard
    stats = {}
    try:
        host_count = db.query_one("SELECT COUNT(*) as cnt FROM hosts")
        stats["total_hosts"] = host_count["cnt"] if host_count else 0

        up_count = db.query_one("SELECT COUNT(*) as cnt FROM hosts WHERE status = 'UP'")
        stats["hosts_up"] = up_count["cnt"] if up_count else 0

        down_count = db.query_one("SELECT COUNT(*) as cnt FROM hosts WHERE status = 'DOWN'")
        stats["hosts_down"] = down_count["cnt"] if down_count else 0

        warning_count = db.query_one("SELECT COUNT(*) as cnt FROM hosts WHERE status = 'WARNING'")
        stats["hosts_warning"] = warning_count["cnt"] if warning_count else 0

        open_alerts = db.query_one("SELECT COUNT(*) as cnt FROM alerts WHERE status = 'OPEN'")
        stats["open_alerts"] = open_alerts["cnt"] if open_alerts else 0

        recent_hosts = db.query("SELECT hostname, ip, os_type, status, cpu_count, memory_total_mb, last_seen FROM hosts ORDER BY updated_at DESC LIMIT 10")
        stats["recent_hosts"] = recent_hosts if recent_hosts else []

        recent_alerts = db.query("SELECT a.id, a.hostname, a.metric, a.severity, a.status, a.triggered_at FROM alerts a WHERE a.status = 'OPEN' ORDER BY a.triggered_at DESC LIMIT 5")
        stats["recent_alerts"] = recent_alerts if recent_alerts else []
    except Exception:
        stats["total_hosts"] = 0
        stats["hosts_up"] = 0
        stats["hosts_down"] = 0
        stats["hosts_warning"] = 0
        stats["open_alerts"] = 0
        stats["recent_hosts"] = []
        stats["recent_alerts"] = []

    return render_template("dashboard.html", active_page="dashboard", user=user, stats=stats)


@web_ui_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="Email and password are required")

        try:
            user = db.query_one("SELECT * FROM users WHERE email = %s AND active = TRUE", (email,))
            if user and verify_password(password, user["password_hash"]):
                session["token"] = _generate_session_token(user)
                session["user_email"] = user["email"]
                session["user_role"] = user["role"]
                log_event("security", "INFO", "login_success",
                         f"Web UI login for '{email}'", user_id=user["email"])
                return redirect("/")
            else:
                return render_template("login.html", error="Invalid credentials")
        except Exception as e:
            return render_template("login.html", error=f"Login error: {e}")

    return render_template("login.html")


@web_ui_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


def _generate_session_token(user):
    """Generate a JWT token for the web UI session."""
    from modules.security import generate_token
    return generate_token(user["id"], user["email"], user["role"])


@web_ui_bp.route("/hosts")
def hosts():
    user = _check_auth()
    if not user:
        return redirect("/login")

    hosts_list = db.query("SELECT * FROM hosts ORDER BY hostname") or []
    groups = db.query("SELECT * FROM host_groups ORDER BY name") or []
    return render_template("hosts.html", active_page="hosts", user=user, hosts=hosts_list, groups=groups)


@web_ui_bp.route("/hosts/<hostname>")
def host_detail(hostname):
    user = _check_auth()
    if not user:
        return redirect("/login")

    host = db.query_one("SELECT * FROM hosts WHERE hostname = %s", (hostname,))
    if not host:
        return render_template("host_detail.html", active_page="hosts", user=user, host=None, hostname=hostname, metrics=None, history=None), 404

    metrics = db.query("SELECT * FROM metrics WHERE hostname = %s ORDER BY timestamp DESC LIMIT 1", (hostname,))
    history = db.query("SELECT * FROM metric_history WHERE hostname = %s ORDER BY timestamp DESC LIMIT 50", (hostname,))
    return render_template("host_detail.html", active_page="hosts", user=user, host=host, hostname=hostname, metrics=metrics[0] if metrics else None, history=history or [])


@web_ui_bp.route("/alerts")
def alerts():
    user = _check_auth()
    if not user:
        return redirect("/login")

    alerts_list = db.query("SELECT * FROM alerts ORDER BY triggered_at DESC LIMIT 100") or []
    rules = db.query("SELECT * FROM alert_rules ORDER BY name") or []
    return render_template("alerts.html", active_page="alerts", user=user, alerts=alerts_list, rules=rules)


@web_ui_bp.route("/events")
def events():
    user = _check_auth()
    if not user:
        return redirect("/login")

    events_list = db.query("SELECT * FROM events ORDER BY event_time DESC LIMIT 200") or []
    return render_template("events.html", active_page="events", user=user, events=events_list)


@web_ui_bp.route("/ai")
def ai_insights():
    user = _check_auth()
    if not user:
        return redirect("/login")

    insights = db.query("SELECT * FROM ai_insights ORDER BY timestamp DESC LIMIT 50") or []
    suggestions = db.query("SELECT * FROM remediation_suggestions ORDER BY generated_at DESC LIMIT 50") or []
    return render_template("ai_insights.html", active_page="ai", user=user, insights=insights, suggestions=suggestions)


@web_ui_bp.route("/reports")
def reports():
    user = _check_auth()
    if not user:
        return redirect("/login")

    reports_list = db.query("SELECT * FROM reports ORDER BY generated_at DESC LIMIT 50") or []
    return render_template("reports.html", active_page="reports", user=user, reports=reports_list)


@web_ui_bp.route("/remote")
def remote_exec():
    user = _check_auth()
    if not user:
        return redirect("/login")

    execs = db.query("SELECT * FROM remote_executions ORDER BY requested_at DESC LIMIT 50") or []
    return render_template("remote_exec.html", active_page="remote", user=user, executions=execs)


@web_ui_bp.route("/settings")
def settings():
    user = _check_auth()
    if not user:
        return redirect("/login")

    config_items = db.query("SELECT * FROM system_config ORDER BY config_key") or []
    return render_template("settings.html", active_page="settings", user=user, config_items=config_items)