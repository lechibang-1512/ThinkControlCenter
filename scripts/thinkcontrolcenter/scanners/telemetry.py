"""Real-time system telemetry: CPU usage, memory utilization, and temperature sensors."""

from __future__ import annotations

import glob
import logging
import os
from typing import Any

from thinkcontrolcenter.config import PROC_MEMINFO, PROC_STAT, SYS_HWMON_BASE

logger = logging.getLogger(__name__)


class TelemetryScanner:
    """Provides polling-based CPU, RAM, and thermal sensor readings."""

    def __init__(self) -> None:
        self._prev_idle: int = 0
        self._prev_total: int = 0
        self._has_prev: bool = False

    def get_cpu_usage(self) -> float:
        """Return current CPU usage as a percentage (0.0–100.0).

        Uses the delta between two consecutive reads of ``/proc/stat``.
        Returns 0.0 on the first call or on any read error.
        """
        try:
            with open(PROC_STAT, "r") as f:
                line = f.readline()
            if not line.startswith("cpu "):
                return 0.0

            parts = [int(x) for x in line.split()[1:9]]
            user, nice, system, idle, iowait, irq, softirq, steal = parts
            idle_time = idle + iowait
            total_time = idle_time + user + nice + system + irq + softirq + steal

            if not self._has_prev:
                self._prev_idle = idle_time
                self._prev_total = total_time
                self._has_prev = True
                return 0.0

            total_diff = total_time - self._prev_total
            idle_diff = idle_time - self._prev_idle
            self._prev_idle = idle_time
            self._prev_total = total_time

            if total_diff <= 0:
                return 0.0
            return max(0.0, min(100.0, 100.0 * (1.0 - (idle_diff / total_diff))))
        except (OSError, ValueError) as exc:
            logger.debug("CPU usage read failed: %s", exc)
            return 0.0

    @staticmethod
    def get_memory_usage() -> tuple[float, float, int]:
        """Return ``(used_gb, total_gb, percent)`` from ``/proc/meminfo``."""
        try:
            with open(PROC_MEMINFO, "r") as f:
                lines = f.readlines()
            mem: dict[str, int] = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    mem[parts[0].strip()] = int(parts[1].split()[0])
            total_gb = mem.get("MemTotal", 0) / (1024.0 * 1024.0)
            avail_gb = mem.get("MemAvailable", 0) / (1024.0 * 1024.0)
            used_gb = max(0.0, total_gb - avail_gb)
            pct = int((used_gb / total_gb) * 100) if total_gb > 0 else 0
            return used_gb, total_gb, pct
        except (OSError, ValueError) as exc:
            logger.debug("Memory usage read failed: %s", exc)
            return 0.0, 0.0, 0

    @staticmethod
    def get_thermals() -> list[dict[str, Any]]:
        """Read all hardware temperature sensors from ``/sys/class/hwmon``."""
        sensors: list[dict[str, Any]] = []
        hwmons = sorted(glob.glob(os.path.join(SYS_HWMON_BASE, "hwmon*")))

        for hwmon_dir in hwmons:
            group_name = _read_hwmon_name(hwmon_dir)
            temp_inputs = sorted(glob.glob(os.path.join(hwmon_dir, "temp*_input")))

            for temp_input in temp_inputs:
                try:
                    with open(temp_input, "r") as f:
                        millideg = int(f.read().strip())
                    temp_c = millideg / 1000.0
                    if temp_c < -50 or temp_c > 150:
                        continue

                    prefix = os.path.basename(temp_input).split("_")[0]
                    label = _read_sensor_label(hwmon_dir, prefix)

                    sensors.append({
                        "group": group_name,
                        "label": label,
                        "temp": temp_c,
                    })
                except (OSError, ValueError) as exc:
                    logger.debug("Sensor read failed for %s: %s", temp_input, exc)
        return sensors


def _read_hwmon_name(hwmon_dir: str) -> str:
    """Read the ``name`` file inside a hwmon directory."""
    name_path = os.path.join(hwmon_dir, "name")
    if os.path.exists(name_path):
        try:
            with open(name_path, "r") as f:
                return f.read().strip()
        except OSError:
            pass
    return "Hardware Sensor"


def _read_sensor_label(hwmon_dir: str, prefix: str) -> str:
    """Read the label file for a specific temperature sensor, falling back to its prefix."""
    label_path = os.path.join(hwmon_dir, f"{prefix}_label")
    if os.path.exists(label_path):
        try:
            with open(label_path, "r") as f:
                return f.read().strip()
        except OSError:
            pass
    return prefix
