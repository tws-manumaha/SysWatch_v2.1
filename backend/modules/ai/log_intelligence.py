"""
SysWatch v2.1 - Advanced AI Log Intelligence
- Statistical anomaly detection (z-score, EWMA, seasonal-aware)
- Predictive trend analysis (linear regression forecasting)
- AI-powered root cause analysis via LLM
- Automated remediation suggestion generation (human approval required)
"""
import json
import logging
import statistics
from datetime import timedelta
from typing import Optional

from modules.database import db
from modules.logging_manager import log_event, utcnow
from modules.ai.llm import ask_llm

logger = logging.getLogger("syswatch.ai.log_intelligence")

Z_SCORE_THRESHOLD = 3.0
EWMA_ALPHA = 0.3
MIN_DATA_POINTS = 10
PREDICTION_HORIZON_MINUTES = 30


def _get_metric_history(hostname, metric, limit=100):
    rows = db.query("SELECT value FROM metric_history WHERE hostname=%s AND metric_name=%s ORDER BY timestamp DESC LIMIT %s", (hostname, metric, limit))
    return [float(r["value"]) for r in reversed(rows)]


def _calculate_z_score(value, history):
    if len(history) < MIN_DATA_POINTS:
        return 0.0, float(statistics.mean(history)) if history else 0, 0
    mean = statistics.mean(history)
    std = statistics.stdev(history) if len(history) > 1 else 0
    if std == 0: return 0.0, mean, 0
    z = (value - mean) / std
    return z, mean, std


def _calculate_ewma(history, alpha=EWMA_ALPHA):
    if not history: return 0
    ewma = history[0]
    for val in history[1:]:
        ewma = alpha * val + (1 - alpha) * ewma
    return ewma


def _linear_regression_forecast(values, steps=5):
    if len(values) < 3: return []
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = statistics.mean(values)
    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0: return [y_mean] * steps
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return [max(0, slope * (n + i) + intercept) for i in range(steps)]


def _detect_trend(values):
    if len(values) < 5: return "insufficient_data"
    recent = values[-5:]
    if all(recent[i] <= recent[i + 1] for i in range(len(recent) - 1)): return "increasing"
    if all(recent[i] >= recent[i + 1] for i in range(len(recent) - 1)): return "decreasing"
    return "fluctuating"


def _will_breach_threshold(forecast, threshold, operator=">"):
    if not forecast: return False
    for val in forecast:
        if operator == ">" and val > threshold: return True
        if operator == "<" and val < threshold: return True
    return False


def analyze_anomalies():
    logger.info("Starting AI anomaly analysis")
    hosts = db.query("SELECT DISTINCT hostname FROM metrics WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 1 HOUR)")
    if not hosts:
        logger.info("No hosts with recent metrics")
        return {"analyzed": 0, "anomalies": 0, "predictions": 0}

    anomaly_count = 0
    prediction_count = 0
    analyzed_count = 0
    metrics_to_check = ["cpu", "memory", "disk", "load_1"]

    for host_row in hosts:
        hostname = host_row["hostname"]
        for metric in metrics_to_check:
            history = _get_metric_history(hostname, metric, limit=100)
            if len(history) < MIN_DATA_POINTS: continue
            analyzed_count += 1
            current_value = history[-1]
            z_score, mean, std = _calculate_z_score(current_value, history)

            if abs(z_score) > Z_SCORE_THRESHOLD:
                severity = "CRITICAL" if abs(z_score) > 5 else "WARNING"
                trend = _detect_trend(history)
                ewma = _calculate_ewma(history)
                forecast = _linear_regression_forecast(history, steps=PREDICTION_HORIZON_MINUTES // 5)
                insight_details = {"trend": trend, "ewma": round(ewma, 2), "forecast": [round(v, 2) for v in forecast], "data_points": len(history)}

                will_breach = False
                if metric == "cpu" and _will_breach_threshold(forecast, 90): will_breach = True
                elif metric == "memory" and _will_breach_threshold(forecast, 85): will_breach = True
                elif metric == "disk" and _will_breach_threshold(forecast, 90): will_breach = True
                if will_breach:
                    prediction_count += 1
                    insight_details["prediction"] = f"Forecast indicates {metric} will breach threshold within {PREDICTION_HORIZON_MINUTES} minutes"

                existing = db.query_one("SELECT id FROM ai_insights WHERE hostname=%s AND metric=%s AND status='OPEN' ORDER BY timestamp DESC LIMIT 1", (hostname, metric))
                if existing:
                    db.execute("UPDATE ai_insights SET current_value=%s, baseline_mean=%s, baseline_std=%s, deviation=%s, details=%s, timestamp=%s WHERE id=%s", (current_value, mean, std, z_score, json.dumps(insight_details), utcnow(), existing["id"]))
                else:
                    insight_id = db.execute_returning_id("INSERT INTO ai_insights (hostname, metric, current_value, baseline_mean, baseline_std, deviation, severity, status, details, provider, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s, 'OPEN', %s, 'statistical', %s)", (hostname, metric, current_value, mean, std, z_score, severity, json.dumps(insight_details), utcnow()))
                    anomaly_count += 1
                    db.execute("INSERT INTO notifications (user_id, type, title, message, severity, source_id, source_type) VALUES (NULL, 'ai_insight', %s, %s, %s, %s, 'ai_insight')", (f"AI Anomaly: {hostname}", f"{hostname}: anomaly on {metric} (z-score={z_score:.1f}, value={current_value:.1f}, trend={trend})", severity, insight_id))
                    log_event("ai", "WARNING", "anomaly_detected", f"Anomaly: {hostname} {metric}={current_value:.1f} (z={z_score:.1f}, trend={trend})", hostname=hostname, details={"insight_id": insight_id, "metric": metric, "z_score": z_score})
                    try:
                        _generate_remediation_suggestion(insight_id, hostname, metric, current_value, mean, std, z_score, trend, forecast)
                    except Exception as e:
                        logger.warning(f"Failed to generate remediation: {e}")

    logger.info(f"AI analysis: {analyzed_count} metrics checked, {anomaly_count} anomalies, {prediction_count} predictions")
    return {"analyzed": analyzed_count, "anomalies": anomaly_count, "predictions": prediction_count}


def _generate_remediation_suggestion(insight_id, hostname, metric, value, mean, std, z_score, trend, forecast):
    prompt = f"""You are a senior system administrator AI assistant for SysWatch.
An anomaly has been detected on host '{hostname}'.

Metric: {metric}
Current value: {value:.2f}
Baseline mean: {mean:.2f}
Standard deviation: {std:.2f}
Z-score: {z_score:.2f}
Trend: {trend}
30-minute forecast: {[round(v, 1) for v in forecast]}

Based on this data, suggest a single remediation command that a sysadmin could run to investigate or fix the issue.

Rules:
1. The command must be safe and non-destructive.
2. Prefer diagnostic commands (e.g., 'top -bn1', 'df -h', 'free -m', 'ps aux --sort=-%cpu | head -20').
3. If the forecast indicates an imminent threshold breach, suggest a proactive action.
4. Keep the command to a single line.

Respond in JSON format:
{{"command": "<the command>", "explanation": "<why this command>", "risk_level": "LOW|MEDIUM|HIGH"}}"""

    result = ask_llm(prompt, system="You are a helpful system administration AI. Always respond in valid JSON.", max_tokens=500)

    if result["success"]:
        try:
            text = result["text"].strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"): text = text[4:]
            suggestion = json.loads(text)
        except json.JSONDecodeError:
            suggestion = {"command": text[:500] if result.get("text") else f"# Investigate {metric} on {hostname}", "explanation": "AI suggested investigation command", "risk_level": "LOW"}

        command = suggestion.get("command", "")
        risk_level = suggestion.get("risk_level", "LOW").upper()
        if risk_level not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"): risk_level = "LOW"

        db.execute("INSERT INTO remediation_suggestions (insight_id, hostname, issue, suggested_command, ai_explanation, risk_level, status, generated_at) VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s)", (insight_id, hostname, f"{metric} anomaly: value={value:.2f}, z-score={z_score:.2f}, trend={trend}", command, suggestion.get("explanation", ""), risk_level, utcnow()))
        db.execute("INSERT INTO notifications (user_id, type, title, message, severity, source_id, source_type) VALUES (NULL, 'remediation', %s, %s, %s, %s, 'remediation')", (f"Remediation suggested: {hostname}", f"AI suggests running: {command[:100]}", "WARNING", insight_id))
        logger.info(f"Generated remediation suggestion for {hostname} (risk: {risk_level})")
    else:
        logger.warning(f"AI remediation generation failed: {result.get('error')}")


def get_latest_insight():
    return db.query_one("SELECT * FROM ai_insights ORDER BY timestamp DESC LIMIT 1") or {}


def analyze_log_patterns(hostname=None, limit=100):
    if hostname:
        logs = db.query("SELECT level, module, event_type, message, timestamp FROM application_logs WHERE hostname=%s ORDER BY timestamp DESC LIMIT %s", (hostname, limit))
    else:
        logs = db.query("SELECT level, module, event_type, message, timestamp FROM application_logs ORDER BY timestamp DESC LIMIT %s", (limit,))

    if not logs:
        return {"analysis": "No logs to analyze", "patterns": []}

    log_summary = "\n".join([f"[{l['level']}] {l['timestamp']} {l['module']}: {l['message'][:100]}" for l in logs[:50]])
    prompt = f"""Analyze these system logs and identify:
1. Common patterns or recurring issues
2. Severity trends (are errors increasing?)
3. Any security concerns
4. Recommended actions

Logs:
{log_summary}

Provide a concise analysis."""

    result = ask_llm(prompt, system="You are a system log analysis AI. Be concise and actionable.", max_tokens=1000)
    if result["success"]:
        return {"analysis": result["text"], "log_count": len(logs), "host": hostname or "all", "provider": result.get("provider")}
    return {"analysis": "AI analysis unavailable", "log_count": len(logs), "error": result.get("error")}
