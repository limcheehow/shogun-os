#!/usr/bin/env python3
"""
Modbus TCP Reader — connects to PLCs via Modbus TCP protocol.

Reads machine states, production counts, and status from industrial PLCs
that expose data via Modbus TCP. Common in manufacturing facilities.

Configure via env vars:
  MODBUS_HOST       — PLC IP address (default: 127.0.0.1)
  MODBUS_PORT       — Modbus TCP port (default: 502)
  MODBUS_TIMEOUT    — Connection timeout in seconds (default: 10)
  MODBUS_UNIT       — Modbus unit/slave ID (default: 1)

Usage:
    from mes_interface import get_adapter
    plc = get_adapter("modbus", host="192.168.1.100")
    plc.connect()
    states = plc.read_machine_states()
"""
import os
import struct
import json
from datetime import datetime, timezone
from typing import Optional
from mes_interface import MESAdapter

try:
    from pymodbus.client import ModbusTcpClient
    HAS_PYMODBUS = True
except ImportError:
    HAS_PYMODBUS = False

try:
    import minimalmodbus
    HAS_MINIMALMODBUS = True
except ImportError:
    HAS_MINIMALMODBUS = False


class ModbusAdapter(MESAdapter):
    """Modbus TCP adapter for PLC data reading."""

    def __init__(self, host: str = "", port: int = 502,
                 timeout: int = 10, unit: int = 1):
        self.host = host or os.environ.get("MODBUS_HOST", "127.0.0.1")
        self.port = int(os.environ.get("MODBUS_PORT", str(port)))
        self.timeout = int(os.environ.get("MODBUS_TIMEOUT", str(timeout)))
        self.unit = int(os.environ.get("MODBUS_UNIT", str(unit)))
        self._client = None

        # Register mapping — override via env vars
        # Format: MODBUS_REGISTER_MAP='{"state":0,"good_count":2,"reject_count":4}'
        self._register_map = self._parse_register_map(
            os.environ.get("MODBUS_REGISTER_MAP", "")
        )

    @staticmethod
    def _parse_register_map(map_str: str) -> dict:
        if not map_str:
            return {"state": 0, "good_count": 2, "reject_count": 4,
                    "cycle_time": 6, "speed": 8, "target_count": 10}
        try:
            return json.loads(map_str)
        except (json.JSONDecodeError, ValueError):
            return {}

    def connect(self) -> bool:
        if not HAS_PYMODBUS:
            raise ImportError(
                "pymodbus not installed. Run: pip install pymodbus"
            )
        self._client = ModbusTcpClient(
            self.host, port=self.port, timeout=self.timeout
        )
        connected = self._client.connect()
        if not connected:
            raise ConnectionError(
                f"Modbus TCP connection failed: {self.host}:{self.port}"
            )
        return True

    def _read_register(self, address: int, count: int = 1) -> list[int]:
        """Read holding registers from PLC."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
        result = self._client.read_holding_registers(address, count, unit=self.unit)
        if result.isError():
            raise RuntimeError(f"Modbus read error at {address}: {result}")
        return result.registers

    def _read_float(self, address: int) -> float:
        """Read a 32-bit float from two consecutive holding registers."""
        regs = self._read_register(address, 2)
        if len(regs) < 2:
            return 0.0
        # Modbus big-endian, two 16-bit registers → 32-bit float
        packed = struct.pack(">HH", regs[0], regs[1])
        return struct.unpack(">f", packed)[0]

    def _read_uint32(self, address: int) -> int:
        """Read a 32-bit unsigned int from two consecutive registers."""
        regs = self._read_register(address, 2)
        if len(regs) < 2:
            return 0
        return (regs[0] << 16) | regs[1]

    def read_machine_states(self) -> list[dict]:
        """Read machine state from PLC holding register."""
        state_addr = self._register_map.get("state", 0)
        try:
            regs = self._read_register(state_addr, 1)
            state_val = regs[0] if regs else 0
            speed = self._read_float(self._register_map.get("speed", 8))

            state_map = {0: "off", 1: "running", 2: "idle", 3: "down",
                         4: "maintenance", 5: "alarm"}
            state = state_map.get(state_val, "unknown")

            return [{
                "machine_id": "PLC_001",
                "name": f"PLC at {self.host}",
                "state": state,
                "state_since": "",
                "uptime_seconds": 0,
                "speed_percent": speed,
            }]
        except Exception as e:
            return [{
                "machine_id": "PLC_001",
                "name": f"PLC at {self.host}",
                "state": "unknown",
                "state_since": "",
                "uptime_seconds": 0,
                "speed_percent": 0,
                "error": str(e),
            }]

    def read_production_counts(self, since: Optional[str] = None,
                               machine_id: Optional[str] = None) -> list[dict]:
        """Read production counts from PLC holding registers."""
        try:
            good = self._read_uint32(self._register_map.get("good_count", 2))
            reject = self._read_uint32(self._register_map.get("reject_count", 4))
            cycle = self._read_float(self._register_map.get("cycle_time", 6))
            target = self._read_uint32(self._register_map.get("target_count", 10))

            return [{
                "machine_id": machine_id or "PLC_001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "good_count": good,
                "reject_count": reject,
                "cycle_time_avg": cycle,
                "target_count": target,
            }]
        except Exception as e:
            return [{"machine_id": machine_id or "PLC_001",
                     "timestamp": datetime.now(timezone.utc).isoformat(),
                     "good_count": 0, "reject_count": 0,
                     "cycle_time_avg": 0, "target_count": 0,
                     "error": str(e)}]

    def read_downtime_events(self, since: Optional[str] = None,
                             machine_id: Optional[str] = None) -> list[dict]:
        """Read downtime events — Modbus typically doesn't store history,
        so this returns current state with 0 duration."""
        return [{
            "machine_id": machine_id or "PLC_001",
            "start_time": "",
            "end_time": "",
            "duration_seconds": 0,
            "reason_code": "",
            "reason_text": "No downtime history from PLC (real-time only)",
            "shift": "",
        }]

    def read_quality_metrics(self, since: Optional[str] = None,
                             machine_id: Optional[str] = None) -> list[dict]:
        """Read quality metrics from PLC registers if mapped."""
        try:
            total = self._read_uint32(self._register_map.get("total_checked", 12))
            passed = self._read_uint32(self._register_map.get("passed", 14))
            failed = self._read_uint32(self._register_map.get("failed", 16))

            return [{
                "machine_id": machine_id or "PLC_001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_checked": total,
                "passed": passed,
                "failed": failed,
                "defect_codes": [],
            }]
        except Exception as e:
            return [{"machine_id": machine_id or "PLC_001",
                     "timestamp": datetime.now(timezone.utc).isoformat(),
                     "total_checked": 0, "passed": 0, "failed": 0,
                     "defect_codes": [], "error": str(e)}]

    def close(self):
        """Close Modbus TCP connection."""
        if self._client:
            self._client.close()
