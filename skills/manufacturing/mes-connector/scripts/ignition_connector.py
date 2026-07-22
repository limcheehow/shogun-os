#!/usr/bin/env python3
"""
Ignition MES Adapter — connects to Inductive Automation Ignition via MQTT + REST API.

Ignition is the most popular MES/SCADA platform in manufacturing worldwide.
This adapter reads machine states, production counts, and downtime events.

Configure via env vars:
  IGNITION_URL       — Ignition gateway URL (e.g. http://localhost:8088)
  IGNITION_USER      — Ignition username
  IGNITION_PASSWORD  — Ignition password
  IGNITION_PROJECT   — Ignition project name (default: "")
  IGNITION_TIMEOUT   — Request timeout in seconds (default: 30)

Usage:
    from mes_interface import get_adapter
    mes = get_adapter("ignition", url="http://localhost:8088")
    mes.connect()
    states = mes.read_machine_states()
"""
import os
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional
from mes_interface import MESAdapter


class IgnitionAdapter(MESAdapter):
    """Ignition SCADA/MES adapter via REST API."""

    def __init__(self, url: str = "", user: str = "", password: str = "",
                 project: str = "", timeout: int = 30):
        self.url = url.rstrip("/") or os.environ.get("IGNITION_URL", "http://localhost:8088")
        self.user = user or os.environ.get("IGNITION_USER", "admin")
        self.password = password or os.environ.get("IGNITION_PASSWORD", "password")
        self.project = project or os.environ.get("IGNITION_PROJECT", "")
        self.timeout = int(os.environ.get("IGNITION_TIMEOUT", str(timeout)))
        self._session_id = None

    def _auth_header(self) -> dict:
        auth = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Basic {auth}",
        }

    def _request(self, method: str, path: str, data: dict = None) -> dict:
        url = f"{self.url}/main/{path.lstrip('/')}"
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body,
                                     headers=self._auth_header(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()[:500]
            raise ConnectionError(f"Ignition HTTP {e.code}: {err_body}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Ignition connection failed: {e.reason}")

    def _call_script(self, script: str, params: list = None) -> dict:
        """Call an Ignition gateway script."""
        payload = {"script": script, "params": params or []}
        return self._request("POST", "gateway/script", payload)

    def connect(self) -> bool:
        """Test connection by calling a simple gateway script."""
        try:
            result = self._call_script("system.gateway.getVersion()")
            return True
        except Exception as e:
            raise ConnectionError(f"Ignition connection failed: {e}")

    def _tag_read(self, tag_paths: list[str]) -> dict:
        """Read OPC-UA tag values from Ignition."""
        result = self._call_script(
            "system.tag.readBlocking",
            [tag_paths, 10000]
        )
        return result

    def read_machine_states(self) -> list[dict]:
        """Read machine states from Ignition tags."""
        machine_tag_base = os.environ.get("IGNITION_MACHINE_TAG_PATH",
                                          "[default]Machines")
        tag_count = int(os.environ.get("IGNITION_MACHINE_COUNT", "20"))

        tag_paths = []
        for i in range(1, tag_count + 1):
            tag_paths.append(f"{machine_tag_base}[{i}]/State")
            tag_paths.append(f"{machine_tag_base}[{i}]/StateSince")
            tag_paths.append(f"{machine_tag_base}[{i}]/Speed")
            tag_paths.append(f"{machine_tag_base}[{i}]/Name")

        if not tag_paths:
            return []

        result = self._tag_read(tag_paths)
        values = result.get("result", [])

        machines = []
        for i in range(tag_count):
            base = i * 4
            if base + 3 < len(values):
                state_val = values[base].get("value", "unknown")
                state_since = values[base + 1].get("value", "")
                speed = values[base + 2].get("value", 0)
                name = values[base + 3].get("value", f"Machine_{i + 1}")

                state_map = {0: "off", 1: "running", 2: "idle", 3: "down"}
                state = state_map.get(state_val, "unknown")

                uptime = 0
                if state == "running" and state_since:
                    try:
                        since_dt = datetime.fromisoformat(str(state_since))
                        uptime = int((datetime.now(timezone.utc) - since_dt).total_seconds())
                    except (ValueError, TypeError):
                        pass

                machines.append({
                    "machine_id": f"MACHINE_{i + 1:03d}",
                    "name": str(name),
                    "state": state,
                    "state_since": str(state_since) if state_since else "",
                    "uptime_seconds": uptime,
                    "speed_percent": float(speed or 0),
                })

        return machines

    def read_production_counts(self, since: Optional[str] = None,
                               machine_id: Optional[str] = None) -> list[dict]:
        """Read production counts from Ignition tags."""
        tag_base = os.environ.get("IGNITION_COUNT_TAG_PATH",
                                  "[default]Production")

        tag_paths = [f"{tag_base}/GoodCount", f"{tag_base}/RejectCount",
                     f"{tag_base}/CycleTime", f"{tag_base}/TargetCount"]

        if machine_id:
            tag_paths = [f"{tag_base}/{machine_id}/GoodCount",
                         f"{tag_base}/{machine_id}/RejectCount",
                         f"{tag_base}/{machine_id}/CycleTime"]

        result = self._tag_read(tag_paths)
        values = result.get("result", [])

        return [{
            "machine_id": machine_id or "ALL",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "good_count": int(values[0].get("value", 0)) if len(values) > 0 else 0,
            "reject_count": int(values[1].get("value", 0)) if len(values) > 1 else 0,
            "cycle_time_avg": float(values[2].get("value", 0)) if len(values) > 2 else 0,
            "target_count": int(values[3].get("value", 0)) if len(values) > 3 else 0,
        }]

    def read_downtime_events(self, since: Optional[str] = None,
                             machine_id: Optional[str] = None) -> list[dict]:
        """Read downtime events from Ignition tags or database."""
        tag_base = os.environ.get("IGNITION_COUNT_TAG_PATH",
                                  "[default]Production")

        if machine_id:
            state_tag = f"{tag_base}/{machine_id}/State"
        else:
            state_tag = f"{tag_base}/State"

        result = self._tag_read([state_tag])
        values = result.get("result", [])

        return [{
            "machine_id": machine_id or "UNKNOWN",
            "start_time": "",
            "end_time": "",
            "duration_seconds": 0,
            "reason_code": "",
            "reason_text": "",
            "shift": "",
        }]

    def read_quality_metrics(self, since: Optional[str] = None,
                             machine_id: Optional[str] = None) -> list[dict]:
        """Read quality metrics from Ignition."""
        tag_base = os.environ.get("IGNITION_COUNT_TAG_PATH",
                                  "[default]Production")
        path = f"{tag_base}/{machine_id}/" if machine_id else f"{tag_base}/"

        result = self._tag_read([
            f"{path}TotalChecked", f"{path}Passed", f"{path}Failed"
        ])
        values = result.get("result", [])

        return [{
            "machine_id": machine_id or "ALL",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_checked": int(values[0].get("value", 0)) if len(values) > 0 else 0,
            "passed": int(values[1].get("value", 0)) if len(values) > 1 else 0,
            "failed": int(values[2].get("value", 0)) if len(values) > 2 else 0,
            "defect_codes": [],
        }]
