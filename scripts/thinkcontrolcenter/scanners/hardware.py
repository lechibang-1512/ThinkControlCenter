"""Hardware topology scanners for PCI, USB, displays, input devices, and network."""

from __future__ import annotations

import glob
import logging
import os
import subprocess
from typing import Any

from thinkcontrolcenter.config import (
    PROC_INPUT_DEVICES,
    SYS_DRM_BASE,
    SYSTEM_INPUT_KEYWORDS,
)

logger = logging.getLogger(__name__)

# Type alias for the tree-node dicts used by the architecture viewer.
TreeNode = dict[str, Any]


def _make_node(title: str, children: list[TreeNode] | None = None) -> TreeNode:
    """Create a tree-node dictionary."""
    return {"title": title, "children": children or []}


class HardwareScanner:
    """Scans system topology via CLI tools and sysfs."""

    @staticmethod
    def get_pci_tree() -> list[TreeNode]:
        """Build a PCI device tree from ``lspci -nn``."""
        items: list[TreeNode] = []
        try:
            res = subprocess.run(
                ["lspci", "-nn"], capture_output=True, text=True, check=False,
            )
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]

            root_host = _make_node("CPU / Host Bridge")
            pch_node = _make_node("PCH (Platform Controller Hub)", [
                _make_node("LPC Bus -> Nuvoton NCT6683D Embedded Controller"),
            ])
            other_nodes: list[TreeNode] = []

            for line in lines:
                if "Host bridge" in line:
                    root_host["children"].append(_make_node(line))
                elif "ISA bridge" in line or "LPC Controller" in line:
                    pch_node["children"][0]["children"].append(_make_node(line))
                elif "SMBus" in line:
                    pch_node["children"].append(_make_node(f"SMBus Controller: {line}"))
                else:
                    other_nodes.append(_make_node(line))

            if root_host["children"]:
                items.append(root_host)
            if pch_node["children"]:
                items.append(pch_node)
            items.extend(other_nodes)
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("PCI scan failed: %s", exc)
            items.append(_make_node(f"PCI scan error: {exc}"))
        return items

    @staticmethod
    def get_usb_tree() -> list[TreeNode]:
        """Build a USB device tree from ``lsusb``."""
        items: list[TreeNode] = []
        try:
            res = subprocess.run(
                ["lsusb"], capture_output=True, text=True, check=False,
            )
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            hubs: dict[str, TreeNode] = {}
            for line in lines:
                bus_id = line[4:7] if len(line) >= 7 and line.startswith("Bus ") else "Generic"
                if bus_id not in hubs:
                    hubs[bus_id] = _make_node(f"USB Bus {bus_id}")
                hubs[bus_id]["children"].append(_make_node(line))
            items.extend(hubs.values())
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("USB scan failed: %s", exc)
            items.append(_make_node(f"USB scan error: {exc}"))
        return items

    @staticmethod
    def get_network_tree() -> list[TreeNode]:
        """Build a network interface tree from ``ip -br link``."""
        items: list[TreeNode] = []
        try:
            res = subprocess.run(
                ["ip", "-br", "link"], capture_output=True, text=True, check=False,
            )
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    name, status, mac = parts[0], parts[1], parts[2]
                    items.append(_make_node(f"{name} ({status})", [
                        _make_node(f"State: {status}"),
                        _make_node(f"MAC Address: {mac}"),
                    ]))
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("Network scan failed: %s", exc)
            items.append(_make_node(f"Network scan error: {exc}"))
        return items

    @staticmethod
    def get_display_tree() -> list[TreeNode]:
        """Discover connected displays via ``/sys/class/drm``."""
        active_displays: list[TreeNode] = []
        inactive_displays: list[TreeNode] = []
        drm_paths = glob.glob(os.path.join(SYS_DRM_BASE, "card*-*"))

        for p in sorted(drm_paths):
            status_p = os.path.join(p, "status")
            if not os.path.exists(status_p):
                continue
            try:
                with open(status_p, "r") as f:
                    status = f.read().strip()
                display_id = os.path.basename(p)
                if "-" in display_id:
                    display_id = display_id.split("-", 1)[1]

                if status == "connected":
                    monitor_name = _parse_edid_monitor_name(os.path.join(p, "edid"))
                    title = (
                        f"{monitor_name} ({display_id})"
                        if monitor_name
                        else f"Display Port ({display_id})"
                    )
                    active_displays.append(_make_node(title, [
                        _make_node("Status: Connected"),
                        _make_node(f"Sysfs Node: {p}"),
                    ]))
                else:
                    inactive_displays.append(_make_node(f"{display_id} (Disconnected)"))
            except OSError as exc:
                logger.debug("Could not read display %s: %s", p, exc)

        result: list[TreeNode] = []
        if active_displays:
            result.append(_make_node("Active Displays", active_displays))
        else:
            result.append(_make_node("Active Displays (None detected)"))
        if inactive_displays:
            result.append(_make_node("Inactive Ports", inactive_displays))
        return result

    @staticmethod
    def get_input_tree() -> list[TreeNode]:
        """Discover input devices from ``/proc/bus/input/devices``."""
        kbds: list[TreeNode] = []
        mice: list[TreeNode] = []
        sys_btns: list[TreeNode] = []

        if not os.path.exists(PROC_INPUT_DEVICES):
            return []

        try:
            with open(PROC_INPUT_DEVICES, "r") as f:
                content = f.read()
            blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
            for block in blocks:
                name = ""
                handlers = ""
                for line in block.splitlines():
                    line = line.strip()
                    if line.startswith("N: Name="):
                        name = line.split("=", 1)[1].strip('"')
                    elif line.startswith("H: Handlers="):
                        handlers = line.split("=", 1)[1].strip()

                if not name or not handlers:
                    continue

                item = _make_node(name, [_make_node(f"Handlers: {handlers}")])
                if "mouse" in handlers:
                    mice.append(item)
                elif "kbd" in handlers:
                    if any(kw in name for kw in SYSTEM_INPUT_KEYWORDS):
                        sys_btns.append(item)
                    else:
                        kbds.append(item)
        except OSError as exc:
            logger.debug("Could not read input devices: %s", exc)

        result: list[TreeNode] = []
        if kbds:
            result.append(_make_node("Keyboards", kbds))
        if mice:
            result.append(_make_node("Mice & Pointing Devices", mice))
        if sys_btns:
            result.append(_make_node("System Controls & Buttons", sys_btns))
        return result


def _parse_edid_monitor_name(edid_path: str) -> str:
    """Extract the monitor name from a raw EDID binary file.

    Returns an empty string if the EDID is missing or unparseable.
    """
    if not os.path.exists(edid_path):
        return ""
    try:
        with open(edid_path, "rb") as ef:
            edid = ef.read()
            if len(edid) >= 128:
                for off in range(54, 109, 18):
                    if off + 18 <= len(edid):
                        blk = edid[off : off + 18]
                        if (
                            blk[0] == 0
                            and blk[1] == 0
                            and blk[2] == 0
                            and blk[3] == 0xFC
                            and blk[4] == 0
                        ):
                            return blk[5:18].decode("ascii", errors="ignore").strip()
    except OSError as exc:
        logger.debug("Could not parse EDID at %s: %s", edid_path, exc)
    return ""
