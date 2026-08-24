"""
SysWatch v2.1 — Task Scheduler with Distributed Locking
Uses Redis-based locks when available, with a safe file-based fallback.
APScheduler BackgroundScheduler runs periodic jobs.
"""
import os
import time
import fcntl
import logging
from datetime import datetime
from functools import wraps
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from modules.config import Config
from modules.logging_manager import log_event, utcnow

logger = logging.getLogger("syswatch.scheduler")

# Try Redis for distributed locking
try:
    import redis
    _redis_client = None

    def _get_redis():
        global _redis_client
        if _redis_client is None:
            cfg = Config.get_redis_config()
            _redis_client = redis.Redis(
                host=cfg["host"], port=cfg["port"], db=cfg["db"],
                password=cfg["password"], decode_responses=True,
                socket_connect_timeout=3, socket_timeout=3,
            )
            _redis_client.ping()
        return _redis_client

    _HAS_REDIS = True
    logger.info("Redis available for distributed locking")
except Exception:
    _HAS_REDIS = False
    logger.info("Redis not available, using file-based locking fallback")


class DistributedLock:
    """
    Distributed lock using Redis SET NX EX or file-based flock fallback.
    """

    def __init__(self, name: str, timeout: int = 300):
        self.name = f"syswatch:lock:{name}"
        self.timeout = timeout
        self._redis_token = None
        self._lock_file = None
        self._lock_fd = None

    def __enter__(self):
        if _HAS_REDIS:
            try:
                r = _get_redis()
                self._redis_token = str(time.time())
                acquired = r.set(self.name, self._redis_token, nx=True, ex=self.timeout)
                if not acquired:
                    raise BlockingIOError(f"Lock '{self.name}' is held by another process")
                logger.debug(f"Acquired Redis lock: {self.name}")
                return self
            except Exception as e:
                logger.warning(f"Redis lock failed, falling back to file lock: {e}")

        # File-based fallback
        lock_dir = "/tmp/syswatch_locks"
        os.makedirs(lock_dir, exist_ok=True)
        safe_name = self.name.replace(":", "_").replace("/", "_")
        self._lock_file = os.path.join(lock_dir, f"{safe_name}.lock")
        self._lock_fd = open(self._lock_file, "w")
        try:
            fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            logger.debug(f"Acquired file lock: {self.name}")
        except BlockingIOError:
            self._lock_fd.close()
            raise BlockingIOError(f"Lock '{self.name}' is held by another process")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._redis_token and _HAS_REDIS:
            try:
                r = _get_redis()
                script = """
                if redis.call('get', KEYS[1]) == ARGV[1] then
                    return redis.call('del', KEYS[1])
                else
                    return 0
                end
                """
                r.eval(script, 1, self.name, self._redis_token)
                logger.debug(f"Released Redis lock: {self.name}")
            except Exception as e:
                logger.warning(f"Failed to release Redis lock: {e}")

        if self._lock_fd:
            try:
                fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
                self._lock_fd.close()
                logger.debug(f"Released file lock: {self.name}")
            except Exception as e:
                logger.warning(f"Failed to release file lock: {e}")


def with_lock(lock_name: str, timeout: int = 300):
    """Decorator that wraps a function in a DistributedLock."""
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                with DistributedLock(lock_name, timeout=timeout):
                    return fn(*args, **kwargs)
            except BlockingIOError:
                logger.info(f"Skipping '{lock_name}' — already running on another instance")
                return None
        return wrapper
    return decorator


class SysWatchScheduler:
    """Manages scheduled jobs with distributed locking."""

    def __init__(self):
        self._scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60}
        )
        self._jobs = {}

    def start(self):
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")
            log_event("scheduler", "INFO", "scheduler_started", "Background scheduler started")

    def shutdown(self):
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    def add_interval_job(self, func, job_id, seconds, lock_timeout=300, next_run_time=None):
        locked_func = with_lock(job_id, timeout=lock_timeout)(func)
        self._scheduler.add_job(
            locked_func, trigger=IntervalTrigger(seconds=seconds),
            id=job_id, next_run_time=next_run_time,
        )
        self._jobs[job_id] = {"type": "interval", "seconds": seconds}
        logger.info(f"Registered interval job '{job_id}' (every {seconds}s)")

    def add_cron_job(self, func, job_id, cron_expression, lock_timeout=600):
        locked_func = with_lock(job_id, timeout=lock_timeout)(func)
        parts = cron_expression.split()
        if len(parts) == 5:
            trigger = CronTrigger(
                minute=parts[0], hour=parts[1], day=parts[2],
                month=parts[3], day_of_week=parts[4],
            )
        else:
            logger.error(f"Invalid cron expression: {cron_expression}")
            return
        self._scheduler.add_job(locked_func, trigger=trigger, id=job_id)
        self._jobs[job_id] = {"type": "cron", "expression": cron_expression}
        logger.info(f"Registered cron job '{job_id}' ({cron_expression})")

    def remove_job(self, job_id):
        try:
            self._scheduler.remove_job(job_id)
            self._jobs.pop(job_id, None)
            logger.info(f"Removed job '{job_id}'")
        except Exception as e:
            logger.warning(f"Failed to remove job '{job_id}': {e}")

    def get_jobs(self):
        return [{"id": j.id, "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None, "trigger": str(j.trigger)} for j in self._scheduler.get_jobs()]

    def trigger_job(self, job_id):
        try:
            self._scheduler.modify_job(job_id, next_run_time=datetime.now())
            logger.info(f"Manually triggered job '{job_id}'")
            return True
        except Exception as e:
            logger.error(f"Failed to trigger job '{job_id}': {e}")
            return False


scheduler = SysWatchScheduler()


def register_default_jobs():
    """Register all default scheduled jobs."""
    from modules.logging_manager import cleanup_old_logs
    from modules.backup_manager import create_backup, cleanup_old_backups

    scheduler.add_cron_job(cleanup_old_logs, "log_cleanup", Config.LOG_CLEANUP_INTERVAL, lock_timeout=300)
    scheduler.add_cron_job(create_backup, "backup_create", Config.BACKUP_SCHEDULE, lock_timeout=600)
    scheduler.add_cron_job(cleanup_old_backups, "backup_cleanup", "30 2 * * *", lock_timeout=300)

    try:
        from modules.alert_engine import evaluate_alert_rules
        scheduler.add_interval_job(evaluate_alert_rules, "alert_evaluation", Config.ALERT_CHECK_INTERVAL, lock_timeout=120)
    except ImportError:
        logger.warning("Alert engine not yet available")

    try:
        from modules.host_checker import check_host_status
        scheduler.add_interval_job(check_host_status, "host_check", Config.HOST_CHECK_INTERVAL, lock_timeout=120)
    except ImportError:
        logger.warning("Host checker not yet available")

    try:
        from modules.ai.log_intelligence import analyze_anomalies
        scheduler.add_interval_job(analyze_anomalies, "ai_anomaly_analysis", Config.AI_ANALYSIS_INTERVAL, lock_timeout=600)
    except ImportError:
        logger.warning("AI log intelligence not yet available")

    try:
        from modules.api_snmp import poll_snmp_devices
        scheduler.add_interval_job(poll_snmp_devices, "snmp_poll", Config.SNMP_POLL_INTERVAL, lock_timeout=120)
    except ImportError:
        logger.warning("SNMP poller not yet available")

    logger.info(f"Registered {len(scheduler.get_jobs())} default jobs")
