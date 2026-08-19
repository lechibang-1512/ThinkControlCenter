"""ACPI wakeup source scanner and toggler."""

from __future__ import annotations

import logging
import os
from typing import Any

from thinkcontrolcenter.config import PROC_ACPI_WAKEUP, WAKEUP_NODE_DESCRIPTIONS

logger = logging.getLogger(__name__)

# Type alias for a wakeup device dictionary.
WakeupDevice = dict[str, Any]


class WakeupScanner:
    """Reads and parses ``/proc/acpi/wakeup`` for suspend trigger management."""

    @staticmethod
    def get_devices() -> list[WakeupDevice]:
        """Return a list of ACPI wakeup device dictionaries.

        Each dict contains: ``node``, ``state``, ``enabled``, ``sysfs``, ``desc``.
        """
        devices: list[WakeupDevice] = []
        if not os.path.exists(PROC_ACPI_WAKEUP):
            return devices

        try:
            with open(PROC_ACPI_WAKEUP, "r") as f:
                lines = f.readlines()
            for line in lines[1:]:
                parts = line.split()
                if len(parts) < 3:
                    continue

                node = parts[0]
                state = parts[1]
                status_str = parts[2]
                enabled = "enabled" in status_str
                sysfs_node = parts[3] if len(parts) >= 4 else ""

                desc = _get_node_description(node)

                devices.append({
                    "node": node,
                    "state": state,
                    "enabled": enabled,
                    "sysfs": sysfs_node,
                    "desc": desc,
                })
        except OSError as exc:
            logger.warning("Failed to read ACPI wakeup devices: %s", exc)
        return devices


def _get_node_description(node: str) -> str:
    """Map an ACPI node name to a human-readable description."""
    if node in WAKEUP_NODE_DESCRIPTIONS:
        return WAKEUP_NODE_DESCRIPTIONS[node]
    if node.startswith("RP"):
        return "PCIe Root Port"
    if node.startswith("PEG"):
        return "PCI Express Graphics"
    return "ACPI Wakeup Source"
