"""SysWatch v2.1 - AI Insights API"""
import logging
from flask import Blueprint, request, jsonify
from modules.database import db
from modules.security import require_auth, get_current_user
from modules.ai.assistant import generate_suggestion, interactive_analysis
from modules.ai.llm import get_provider_status, test_provider
from modules.ai.log_intelligence import analyze_log_patterns, analyze_anomalies

logger = logging.getLogger("syswatch.api_ai")
ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/ai/insights", methods=["GET"])
@require_auth()
def list_insights():
    status = request.args.get("status", "OPEN")
    limit = min(int(request.args.get("limit", 50)), 500)
    insights = db.query("SELECT * FROM ai_insights WHERE status=%s ORDER BY timestamp DESC LIMIT %s", (status, limit))
    return jsonify(insights)


@ai_bp.route("/ai/insights/<int:insight_id>", methods=["GET"])
@require_auth()
def get_insight(insight_id):
    insight = db.query_one("SELECT * FROM ai_insights WHERE id=%s", (insight_id,))
    if not insight: return jsonify({"error": "Insight not found"}), 404
    return jsonify(insight)


@ai_bp.route("/ai/insights/<int:insight_id>/resolve", methods=["POST"])
@require_auth(roles=["admin", "operator"])
def resolve_insight(insight_id):
    db.execute("UPDATE ai_insights SET status='RESOLVED' WHERE id=%s", (insight_id,))
    return jsonify({"message": "Insight resolved"})


@ai_bp.route("/ai/ask", methods=["POST"])
@require_auth()
def ask_ai():
    data = request.get_json() or {}
    hostname = data.get("hostname", "").strip()
    question = data.get("question", "").strip()
    if not hostname or not question:
        return jsonify({"error": "hostname and question are required"}), 400
    result = interactive_analysis(hostname, question)
    if not result["success"]:
        return jsonify(result), 500
    return jsonify(result)


@ai_bp.route("/ai/suggest", methods=["POST"])
@require_auth(roles=["admin", "operator"])
def suggest_remediation():
    data = request.get_json() or {}
    hostname = data.get("hostname", "").strip()
    issue = data.get("issue", "").strip()
    context = data.get("context", {})
    if not hostname or not issue:
        return jsonify({"error": "hostname and issue are required"}), 400
    result = generate_suggestion(hostname, issue, context)
    if not result["success"]:
        return jsonify(result), 500
    return jsonify(result), 201


@ai_bp.route("/ai/analyze-logs", methods=["POST"])
@require_auth(roles=["admin", "operator"])
def analyze_logs():
    data = request.get_json() or {}
    hostname = data.get("hostname")
    limit = int(data.get("limit", 100))
    result = analyze_log_patterns(hostname, limit)
    return jsonify(result)


@ai_bp.route("/ai/run-analysis", methods=["POST"])
@require_auth(roles=["admin"])
def run_analysis():
    result = analyze_anomalies()
    return jsonify(result)


@ai_bp.route("/ai/providers", methods=["GET"])
@require_auth()
def list_providers():
    return jsonify(get_provider_status())


@ai_bp.route("/ai/providers/<provider>/test", methods=["POST"])
@require_auth(roles=["admin"])
def test_ai_provider(provider):
    result = test_provider(provider)
    return jsonify(result)