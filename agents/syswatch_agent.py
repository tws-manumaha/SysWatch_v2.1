#!/usr/bin/env python3
"""
SysWatch v2.1 Agent - Cross-Platform Monitoring Client
Collects system metrics via psutil and reports to the SysWatch server.

Works on Linux, Windows, and macOS.
Install as service: python syswatch_agent.py --install
Run in foreground:  python syswatch_agent.py
Test connection:    python syswatch_agent.py --test
"""
import os
import sys
import time
import json
import socket
import platform
import argparse
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:5000").rstrip("/")
API_KEY = os.getenv("AGENT_API_KEY", "")
REPORT_INTERVAL = int(os.getenv("REPORT_INTERVAL", "30"))
AGENT_ID_FILE = str(Path(__file__).parent / "agent_id")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(str(Path(__file__).parent / "agent.log"))],
)
logger = logging.getLogger("syswatch.agent")

# Try to import psutil
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.error("psutil not installed. Install with: pip install psutil")


def get_hostname():
    return socket.gethostname()


def collect_metrics():
    """Collect all system metrics using psutil."""
    if not HAS_PSUTIL:
        return None

    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
    net = psutil.net_io_counters()
    swap = psutil.swap_memory()
    boot_time = psutil.boot_time()
    uptime = int(time.time() - boot_time)
    processes = len(psutil.pids())

    # Disk partitions
    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent,
            })
        except PermissionError:
            continue

    # Network interfaces
    net_if = {}
    try:
        for name, addrs in psutil.net_if_addrs().items():
            net_if[name] = [a.address for a in addrs if a.family in (socket.AF_INET, socket.AF_INET6)]
    except Exception:
        pass

    return {
        "hostname": get_hostname(),
        "os_type": _detect_os(),
        "cpu": cpu_percent,
        "memory": memory.percent,
        "disk": disk.percent,
        "net_in": net.bytes_recv,
        "net_out": net.bytes_sent,
        "load_1": load_avg[0],
        "load_5": load_avg[1],
        "load_15": load_avg[2],
        "processes": processes,
        "uptime_seconds": uptime,
        "swap_used": swap.percent,
        "cpu_count": psutil.cpu_count(logical=True),
        "memory_total_mb": round(memory.total / (1024**2)),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "partitions": partitions,
        "network_interfaces": net_if,
        "agent_version": "2.1.0",
    }


def _detect_os():
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    elif "freebsd" in system:
        return "freebsd"
    return "other"


def register_agent():
    """Register this agent with the SysWatch server."""
    hostname = get_hostname()
    payload = {
        "hostname": hostname,
        "ip": _get_local_ip(),
        "os_type": _detect_os(),
        "agent_version": "2.1.0",
    }
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"ApiKey {API_KEY}"

    try:
        resp = requests.post(f"{SERVER_URL}/api/agent/register", json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 201):
            data = resp.json()
            agent_id = data.get("agent_id") or data.get("id")
            if agent_id:
                with open(AGENT_ID_FILE, "w") as f:
                    f.write(str(agent_id))
            logger.info(f"Agent registered successfully (ID: {agent_id})")
            return True
        else:
            logger.error(f"Registration failed: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return False


def send_metrics(metrics):
    """Send metrics to the SysWatch server."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"ApiKey {API_KEY}"

    try:
        resp = requests.post(
            f"{SERVER_URL}/api/agent/metrics",
            json=metrics,
            headers=headers,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            logger.debug("Metrics sent successfully")
            return True
        else:
            logger.warning(f"Metrics send failed: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Metrics send error: {e}")
        return False


def send_heartbeat():
    """Send a heartbeat to the server."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"ApiKey {API_KEY}"
    try:
        resp = requests.post(
            f"{SERVER_URL}/api/agent/heartbeat",
            json={"hostname": get_hostname(), "status": "UP"},
            headers=headers,
            timeout=10,
        )
        return resp.status_code in (200, 201)
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")
        return False


def _get_local_ip():
    """Get the local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run_agent():
    """Main agent loop."""
    logger.info(f"SysWatch Agent v2.1 starting (server: {SERVER_URL})")

    if not HAS_PSUTIL:
        logger.error("psutil is required. Install with: pip install psutil")
        sys.exit(1)

    # Register
    if not register_agent():
        logger.warning("Registration failed, will retry on next cycle")

    # Collect and send metrics
    heartbeat_counter = 0
    while True:
        try:
            metrics = collect_metrics()
            if metrics:
                if send_metrics(metrics):
                    logger.info(f"Metrics sent: CPU={metrics['cpu']}% MEM={metrics['memory']}% DISK={metrics['disk']}%")
                else:
                    logger.warning("Failed to send metrics")

            heartbeat_counter += 1
            if heartbeat_counter >= 5:
                send_heartbeat()
                heartbeat_counter = 0

        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        time.sleep(REPORT_INTERVAL)


def install_service():
    """Install the agent as a system service."""
    os_type = _detect_os()
    script_path = str(Path(__file__).resolve())

    if os_type == "linux":
        _install_systemd(script_path)
    elif os_type == "windows":
        _install_windows_service(script_path)
    elif os_type == "macos":
        _install_launchd(script_path)
    else:
        logger.error(f"Service installation not supported on {os_type}")


def _install_systemd(script_path):
    service_content = f"""[Unit]
Description=SysWatch Monitoring Agent v2.1
After=network.target

[Service]
Type=simple
ExecStart={sys.executable} {script_path}
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
    service_path = "/etc/systemd/system/syswatch-agent.service"
    try:
        with open(service_path, "w") as f:
            f.write(service_content)
        os.system("systemctl daemon-reload")
        os.system("systemctl enable syswatch-agent")
        os.system("systemctl start syswatch-agent")
        logger.info("SysWatch agent installed and started as systemd service")
        logger.info("Manage with: systemctl status|stop|start|restart syswatch-agent")
    except PermissionError:
        logger.error("Run as root/sudo to install system service")
        sys.exit(1)


def _install_windows_service(script_path):
    try:
        import win32serviceutil
        import win32service
        import win32event
    except ImportError:
        logger.error("pywin32 not installed. Install with: pip install pywin32")
        sys.exit(1)

    class SysWatchAgentService(win32serviceutil.ServiceFramework):
        _svc_name_ = "SysWatchAgent"
        _svc_display_name_ = "SysWatch Monitoring Agent v2.1"
        _svc_description_ = "Collects system metrics and reports to SysWatch server"

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):
            run_agent()

    win32serviceutil.HandleCommandLine(SysWatchAgentService, argv=[sys.argv[0], "install"])
    os.system("net start SysWatchAgent")
    logger.info("SysWatch agent installed as Windows service")


def _install_launchd(script_path):
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.syswatch.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/syswatch-agent.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/syswatch-agent.error.log</string>
</dict>
</plist>
"""
    plist_path = os.path.expanduser("~/Library/LaunchAgents/com.syswatch.agent.plist")
    os.makedirs(os.path.dirname(plist_path), exist_ok=True)
    with open(plist_path, "w") as f:
        f.write(plist_content)
    os.system(f"launchctl load {plist_path}")
    logger.info("SysWatch agent installed as launchd service")


def test_connection():
    """Test connection to the SysWatch server."""
    logger.info(f"Testing connection to {SERVER_URL}...")
    try:
        resp = requests.get(f"{SERVER_URL}/api/health", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"Connection successful! Server version: {data.get('version', '?')}")
            logger.info(f"Server status: {data.get('status', '?')}")
            return True
        else:
            logger.error(f"Server responded with status {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="SysWatch v2.1 Monitoring Agent")
    parser.add_argument("--install", action="store_true", help="Install as system service")
    parser.add_argument("--test", action="store_true", help="Test connection to server")
    parser.add_argument("--metrics", action="store_true", help="Print current metrics and exit")
    args = parser.parse_args()

    if args.test:
        test_connection()
        return

    if args.metrics:
        metrics = collect_metrics()
        if metrics:
            print(json.dumps(metrics, indent=2))
        return

    if args.install:
        install_service()
        return

    run_agent()


if __name__ == "__main__":
    main()
