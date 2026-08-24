"""SysWatch v2.1 - Flask Application
Wires all blueprints together, initializes database, starts scheduler.
Run with Gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 'app:app'
"""
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from modules.config import Config
from modules.database import db, init_db
from modules.logging_manager import setup_logging, log_event, utcnow

setup_logging()
logger = logging.getLogger("syswatch.app")


def create_app():
    app = Flask(__name__,
                template_folder="modules/web_ui/templates",
                static_folder="modules/web_ui/static")
    app.config["SECRET_KEY"] = Config.JWT_SECRET
    app.config["JSON_SORT_KEYS"] = False
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    if Config.CORS_ORIGINS:
        CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)
    else:
        CORS(app, supports_credentials=True)
        logger.warning("CORS is open - configure CORS_ORIGINS in production")

    try:
        init_db()
        logger.info("Database schema initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    from modules.api_hosts import hosts_bp
    from modules.api_alerts import alerts_bp
    from modules.api_events import events_bp
    from modules.api_ai import ai_bp
    from modules.api_users import users_bp
    from modules.api_agent import agent_bp
    from modules.api_discovery import discovery_bp
    from modules.api_runbooks import runbooks_bp
    from modules.api_snmp import snmp_bp
    from modules.api_reporting import reporting_bp
    from modules.api_notifications import notifications_bp
    from modules.api_backups import backups_bp
    from modules.api_security import security_bp
    from modules.api_system_logs import system_logs_bp
    from modules.api_cloud import cloud_bp
    from modules.api_remote_exec import remote_exec_bp

    app.register_blueprint(hosts_bp, url_prefix="/api")
    app.register_blueprint(alerts_bp, url_prefix="/api")
    app.register_blueprint(events_bp, url_prefix="/api")
    app.register_blueprint(ai_bp, url_prefix="/api")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(agent_bp, url_prefix="/api")
    app.register_blueprint(discovery_bp, url_prefix="/api")
    app.register_blueprint(runbooks_bp, url_prefix="/api")
    app.register_blueprint(snmp_bp, url_prefix="/api")
    app.register_blueprint(reporting_bp, url_prefix="/api")
    app.register_blueprint(notifications_bp, url_prefix="/api")
    app.register_blueprint(backups_bp, url_prefix="/api")
    app.register_blueprint(security_bp, url_prefix="/api")
    app.register_blueprint(system_logs_bp, url_prefix="/api")
    app.register_blueprint(cloud_bp, url_prefix="/api")
    app.register_blueprint(remote_exec_bp, url_prefix="/api")

    # Register the web UI blueprint (Jinja2 templates served at root)
    from modules.web_ui.routes import web_ui_bp
    app.register_blueprint(web_ui_bp)

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "healthy", "version": "2.1", "timestamp": utcnow().isoformat()})

    @app.errorhandler(404)
    def not_found(e): return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({"error": "Internal server error"}), 500

    @app.errorhandler(403)
    def forbidden(e): return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(401)
    def unauthorized(e): return jsonify({"error": "Unauthorized"}), 401

    @app.before_request
    def log_request():
        from flask import request
        logger.debug(f"{request.method} {request.path} from {request.remote_addr}")

    return app


app = create_app()

try:
    from modules.scheduler import scheduler, register_default_jobs
    register_default_jobs()
    scheduler.start()
    logger.info("Scheduler started with default jobs")
except Exception as e:
    logger.error(f"Failed to start scheduler: {e}")

log_event("system", "INFO", "app_started", "SysWatch v2.1 application started")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)