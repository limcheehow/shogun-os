#!/usr/bin/env python3
"""
MES Connector Interface — abstract base for MES/SCADA adapters.
Each adapter (Ignition, Modbus, OPC-UA, etc.) implements this interface.

Usage:
    from mes_interface import get_adapter
    mes = get_adapter("ignition", url="http://localhost:8088")
    states = mes.read_machine_states()
    counts = mes.read_production_counts()
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class MESAdapter(ABC):
    """Abstract interface for MES/SCADA system connectors."""

    @abstractmethod
    def connect(self) -> bool:
        """Test connection. Returns True on success."""
        ...

    @abstractmethod
    def read_machine_states(self) -> list[dict]:
        """
        Read current state of all machines/work centers.
        Returns list of: {machine_id, name, state (running/idle/down/off),
                         state_since, uptime_seconds, speed_percent}
        """
        ...

    @abstractmethod
    def read_production_counts(self, since: Optional[str] = None,
                               machine_id: Optional[str] = None) -> list[dict]:
        """
        Read production counts (good parts, rejected, cycle time).
        Returns list of: {machine_id, timestamp, good_count, reject_count,
                         cycle_time_avg, target_count}
        """
        ...

    @abstractmethod
    def read_downtime_events(self, since: Optional[str] = None,
                             machine_id: Optional[str] = None) -> list[dict]:
        """
        Read downtime events.
        Returns list of: {machine_id, start_time, end_time, duration_seconds,
                         reason_code, reason_text, shift}
        """
        ...

    @abstractmethod
    def read_quality_metrics(self, since: Optional[str] = None,
                             machine_id: Optional[str] = None) -> list[dict]:
        """
        Read quality metrics from MES.
        Returns list of: {machine_id, timestamp, total_checked, passed,
                         failed, defect_codes: [{code, count}]}
        """
        ...

    def test_connection(self) -> dict:
        try:
            ok = self.connect()
            if ok:
                states = self.read_machine_states()
                return {"status": "ok",
                        "message": f"Connected. {len(states)} machines found"}
            return {"status": "error", "message": "Connection failed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


def get_adapter(system: str, **kwargs) -> MESAdapter:
    """Factory: returns the appropriate MES adapter."""
    if system == "ignition":
        from ignition_connector import IgnitionAdapter
        return IgnitionAdapter(**kwargs)
    elif system == "modbus":
        from modbus_reader import ModbusAdapter
        return ModbusAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown MES system: {system}. Supported: ignition, modbus")
