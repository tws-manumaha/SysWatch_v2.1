"""
SysWatch v2.1 - AI Assistant with Human-in-the-Loop
- AI generates remediation suggestions for detected anomalies
- ALL suggestions require human approval before execution
- Risk-level assessment for each suggestion
- Interactive prompt: user must explicitly approve, modify, or reject
- Full audit trail of who approved what and when
- Execution results captured and stored
"""
import json
import logging
from typing import Optional

from modules.database import db
from modules.logging_manager import log_event, utcnow
from modules.ai.llm import ask_llm

logger = logging.getLogger("syswatch.ai.assistant")

RISK_POLICIES = {
    "LOW": {"auto_execute": False, "requires_approval": True, "roles": ["operator", "admin"]},
    "MEDIUM": {"auto_execute": False, "requires_approval": True, "roles": ["admin"]},
    "HIGH": {"auto_execute": False, "requires_approval": True, "roles": ["admin"], "requires_confirmation": True},
    "CRITICAL": {"auto_execute": False, "requires_approval": True, "roles": ["admin"], "requires_confirmation": True},
}


def generate_suggestion(hostname, issue, context=None):
    """Generate an AI remediation suggestion. ALWAYS stored as 'pending' - never auto-executed."""
    context = context or {}
    prompt = f"""You are SysWatch AI, a senior system administrator assistant.

Host: {hostname}
Issue: {issue}
Context: {json.dumps(context, default=str)}

Generate a remediation plan. You must provide:
1. A safe, non-destructive command to investigate or fix the issue
2. A clear explanation of why this command is recommended
3. A risk assessment (LOW/MEDIUM/HIGH/CRITICAL)
4. Alternative approaches if the first command doesn't work

IMPORTANT: The command will NOT be executed automatically. A human operator must review and approve it.

Respond in JSON:
{{
  "command": "<single-line command>",
  "explanation": "<why this command>",
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "alternatives": ["<alternative 1>", "<alternative 2>"],
  "rollback": "<how to undo if something goes wrong>"
}}"""

    result = ask_llm(prompt, system="You are a cautious system administration AI. Always prioritize safety. Never suggest destructive commands.", max_tokens=800)

    if not result["success"]:
        return {"success": False, "error": result.get("error", "AI request failed")}

    try:
        text = result["text"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        suggestion = json.loads(text)
    except json.JSONDecodeError:
        suggestion = {"command": result["text"][:500], "explanation": "AI-generated suggestion (non-JSON response)", "risk_level": "MEDIUM", "alternatives": [], "rollback": "N/A"}

    risk_level = suggestion.get("risk_level", "MEDIUM").upper()
    if risk_level not in RISK_POLICIES: risk_level = "MEDIUM"

    suggestion_id = db.execute_returning_id("INSERT INTO remediation_suggestions (hostname, issue, suggested_command, ai_explanation, risk_level, status, generated_at) VALUES (%s, %s, %s, %s, %s, 'pending', %s)", (hostname, issue, suggestion.get("command", ""), suggestion.get("explanation", ""), risk_level, utcnow()))

    if suggestion.get("alternatives") or suggestion.get("rollback"):
        db.execute("INSERT INTO events (event_type, hostname, source, details, event_time) VALUES (%s, %s, %s, %s, %s)", ("ai_suggestion_generated", hostname, "ai_assistant", json.dumps({"suggestion_id": suggestion_id, "alternatives": suggestion.get("alternatives", []), "rollback": suggestion.get("rollback", ""), "risk_level": risk_level, "provider": result.get("provider")}), utcnow()))

    log_event("ai_assistant", "INFO", "suggestion_generated", f"AI suggestion generated for {hostname} (risk: {risk_level}, id: {suggestion_id})", hostname=hostname, details={"suggestion_id": suggestion_id, "risk_level": risk_level, "command": suggestion.get("command", "")[:100]})

    return {"success": True, "suggestion_id": suggestion_id, "command": suggestion.get("command"), "explanation": suggestion.get("explanation"), "risk_level": risk_level, "alternatives": suggestion.get("alternatives", []), "rollback": suggestion.get("rollback", "N/A"), "provider": result.get("provider"), "requires_approval": True, "message": "Suggestion generated. Human approval required before execution."}


def approve_suggestion(suggestion_id, approver, modified_command=None):
    """Approve a remediation suggestion for execution. Human must explicitly approve."""
    suggestion = db.query_one("SELECT id, hostname, issue, suggested_command, risk_level, status FROM remediation_suggestions WHERE id=%s", (suggestion_id,))
    if not suggestion: return {"success": False, "error": "Suggestion not found"}
    if suggestion["status"] != "pending": return {"success": False, "error": f"Suggestion is already {suggestion['status']}"}

    command = modified_command if modified_command else suggestion["suggested_command"]
    db.execute("UPDATE remediation_suggestions SET status='approved', approved_by=%s, approved_at=%s, suggested_command=%s WHERE id=%s", (approver, utcnow(), command, suggestion_id))
    log_event("ai_assistant", "INFO", "suggestion_approved", f"Remediation {suggestion_id} approved by {approver}", user_id=approver, hostname=suggestion["hostname"], details={"suggestion_id": suggestion_id, "command": command[:100], "modified": modified_command is not None})
    return {"success": True, "suggestion_id": suggestion_id, "status": "approved", "command": command, "message": "Suggestion approved. Execute when ready.", "next_step": f"POST /api/remediations/{suggestion_id}/execute"}


def reject_suggestion(suggestion_id, rejecter, reason=None):
    """Reject a remediation suggestion."""
    suggestion = db.query_one("SELECT id, hostname, status FROM remediation_suggestions WHERE id=%s", (suggestion_id,))
    if not suggestion: return {"success": False, "error": "Suggestion not found"}
    if suggestion["status"] != "pending": return {"success": False, "error": f"Suggestion is already {suggestion['status']}"}
    db.execute("UPDATE remediation_suggestions SET status='rejected', rejected_by=%s, rejected_at=%s WHERE id=%s", (rejecter, utcnow(), suggestion_id))
    log_event("ai_assistant", "INFO", "suggestion_rejected", f"Remediation {suggestion_id} rejected by {rejecter}", user_id=rejecter, hostname=suggestion["hostname"], details={"suggestion_id": suggestion_id, "reason": reason or "No reason provided"})
    return {"success": True, "status": "rejected", "message": "Suggestion rejected"}


def execute_suggestion(suggestion_id, executor, hostname):
    """Execute an approved remediation suggestion on a remote host."""
    suggestion = db.query_one("SELECT id, hostname, issue, suggested_command, risk_level, status, approved_by FROM remediation_suggestions WHERE id=%s", (suggestion_id,))
    if not suggestion: return {"success": False, "error": "Suggestion not found"}
    if suggestion["status"] != "approved": return {"success": False, "error": f"Suggestion must be approved first (current: {suggestion['status']})"}

    command = suggestion["suggested_command"]
    try:
        from modules.api_remote_exec import execute_command_on_host
        result = execute_command_on_host(hostname, command, timeout=30)
        if result["success"]:
            db.execute("UPDATE remediation_suggestions SET status='completed', executed_at=%s, output=%s, exit_code=%s WHERE id=%s", (utcnow(), result["output"], result["exit_code"], suggestion_id))
            log_event("ai_assistant", "INFO", "suggestion_executed", f"Remediation {suggestion_id} executed on {hostname}", user_id=executor, hostname=hostname, details={"suggestion_id": suggestion_id, "exit_code": result["exit_code"]})
            return {"success": True, "suggestion_id": suggestion_id, "output": result["output"], "exit_code": result["exit_code"], "status": "completed"}
        else:
            db.execute("UPDATE remediation_suggestions SET status='failed', executed_at=%s, output=%s, exit_code=%s WHERE id=%s", (utcnow(), result.get("error", "Unknown error"), result.get("exit_code", -1), suggestion_id))
            log_event("ai_assistant", "ERROR", "suggestion_failed", f"Remediation {suggestion_id} failed on {hostname}: {result.get('error')}", user_id=executor, hostname=hostname, details={"suggestion_id": suggestion_id, "error": result.get("error")})
            return {"success": False, "error": result.get("error", "Execution failed"), "status": "failed"}
    except ImportError:
        logger.warning("Remote execution module not available - recording command for manual execution")
        db.execute("UPDATE remediation_suggestions SET status='completed', executed_at=%s, output=%s, exit_code=0 WHERE id=%s", (utcnow(), "Command recorded for manual execution (remote exec module not available)", suggestion_id))
        return {"success": True, "status": "completed", "note": "Manual execution required"}


def interactive_analysis(hostname, question):
    """Interactive AI analysis - user asks a question about a host."""
    host = db.query_one("SELECT * FROM hosts WHERE hostname=%s", (hostname,))
    if not host: return {"success": False, "error": "Host not found"}

    latest_metrics = db.query("SELECT * FROM metrics WHERE hostname=%s ORDER BY timestamp DESC LIMIT 10", (hostname,))
    recent_alerts = db.query("SELECT * FROM alerts WHERE hostname=%s ORDER BY triggered_at DESC LIMIT 5", (hostname,))
    recent_insights = db.query("SELECT * FROM ai_insights WHERE hostname=%s ORDER BY timestamp DESC LIMIT 5", (hostname,))

    context = {"host": {"hostname": host["hostname"], "ip": host["ip"], "os_type": host["os_type"], "status": host["status"]},
        "latest_metrics": [{"cpu": m["cpu"], "memory": m["memory"], "disk": m["disk"], "load_1": m["load_1"], "timestamp": m["timestamp"].isoformat() if m.get("timestamp") else None} for m in latest_metrics],
        "recent_alerts": [{"metric": a["metric"], "severity": a["severity"], "status": a["status"], "cause": a.get("cause", "")} for a in recent_alerts],
        "recent_insights": [{"metric": i["metric"], "severity": i["severity"], "deviation": float(i["deviation"])} for i in recent_insights]}

    prompt = f"""You are SysWatch AI, analyzing host '{hostname}'.

Host context:
{json.dumps(context, indent=2, default=str)}

User question: {question}

Provide a detailed, actionable analysis. If you suggest any commands, note that they will require human approval before execution."""

    result = ask_llm(prompt, system="You are an expert system administrator AI. Be thorough, specific, and always recommend safe actions.", max_tokens=1500)
    if result["success"]:
        return {"success": True, "analysis": result["text"], "provider": result.get("provider"), "host": hostname}
    return {"success": False, "error": result.get("error", "AI analysis failed")}
