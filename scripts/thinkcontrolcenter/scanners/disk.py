"""Disk and S.M.A.R.T. health scanner using lsblk and smartctl JSON data."""

from __future__ import annotations

import glob
import json
import logging
import os
import shutil
import subprocess
from typing import Any

from thinkcontrolcenter.config import (
    READ_TOTAL_ATTRS,
    SYS_HWMON_BASE,
    WEAR_LEVEL_ATTRS,
    WEAR_LEVEL_IDS,
    WRITE_TOTAL_ATTRS,
)
from thinkcontrolcenter.utils import read_file

logger = logging.getLogger(__name__)

# Type alias for a disk info dictionary.
DiskInfo = dict[str, Any]


class DiskScanner:
    """Discovers block devices and parses S.M.A.R.T. data."""

    @staticmethod
    def get_disks(smart_cache: dict[str, Any] | None = None) -> list[DiskInfo]:
        """Return a list of disk info dictionaries.

        Args:
            smart_cache: Optional mapping of device path → smartctl JSON data.
        """
        smart_cache = smart_cache or {}
        raw_devices = _fetch_block_devices()
        disks: list[DiskInfo] = []

        for dev in raw_devices:
            dev_type = dev.get("type")
            if dev_type not in ("disk", "loop", "rom"):
                continue
            if dev.get("name", "").startswith("loop"):
                continue

            name = dev.get("name")
            path = dev.get("path") or f"/dev/{name}"
            size_bytes = dev.get("size", 0)
            size_gb = size_bytes / (1024**3)
            model = dev.get("model") or (
                "ZRAM Swap" if "zram" in name else "Generic Storage Device"
            )
            serial = dev.get("serial") or "N/A"
            tran = (
                dev.get("tran")
                or ("NVME" if "nvme" in name else ("SWAP" if "zram" in name else "SATA"))
            ).upper()
            firmware = dev.get("rev") or "N/A"

            partitions = _collect_partitions(dev)
            smart_data = smart_cache.get(path, {})
            smart_info = _parse_smart_data(smart_data, name)

            disks.append({
                "name": name,
                "path": path,
                "model": model,
                "serial": serial,
                "firmware": firmware,
                "tran": tran,
                "size_gb": size_gb,
                "partitions": partitions,
                **smart_info,
            })
        return disks


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_block_devices() -> list[dict[str, Any]]:
    """Run ``lsblk --json`` and return the list of block devices."""
    res = subprocess.run(
        [
            "lsblk", "--json", "-b", "-o",
            "NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,SERIAL,ROTA,TRAN,STATE,REV",
        ],
        capture_output=True, text=True, check=False,
    )
    try:
        return json.loads(res.stdout).get("blockdevices", [])
    except (json.JSONDecodeError, TypeError) as exc:
        logger.debug("lsblk JSON parse error: %s", exc)
        return []


def _collect_partitions(dev: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract partition and mount-point data from an lsblk device entry."""
    partitions: list[dict[str, Any]] = []
    children = dev.get("children", [])
    if not children and dev.get("mountpoints"):
        children = [dev]

    for child in children:
        c_name = child.get("name")
        c_path = child.get("path") or f"/dev/{c_name}"
        c_fstype = child.get("fstype") or "unknown"
        c_size = child.get("size", 0) / (1024**3)
        mounts = child.get("mountpoints", [])

        for mount in mounts:
            if not mount:
                continue
            used_gb = 0.0
            total_gb = c_size
            free_gb = 0.0
            pct = 0.0
            if os.path.exists(mount) and not mount.startswith("["):
                try:
                    usage = shutil.disk_usage(mount)
                    total_gb = usage.total / (1024**3)
                    used_gb = usage.used / (1024**3)
                    free_gb = usage.free / (1024**3)
                    pct = (usage.used / usage.total * 100) if usage.total > 0 else 0.0
                except OSError as exc:
                    logger.debug("disk_usage(%s) failed: %s", mount, exc)

            partitions.append({
                "name": c_name,
                "path": c_path,
                "mount": mount,
                "fstype": c_fstype,
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "pct": pct,
            })
    return partitions


def _parse_smart_data(
    smart_data: dict[str, Any],
    dev_name: str,
) -> dict[str, Any]:
    """Parse a smartctl JSON blob into a flat dictionary of health metrics."""
    info: dict[str, Any] = {
        "health_status": "UNKNOWN",
        "health_passed": None,
        "temp_c": None,
        "power_on_hours": None,
        "power_cycles": None,
        "wear_pct": None,
        "tbw_written": None,
        "tb_read": None,
        "media_errors": None,
        "reallocated_sectors": None,
        "attributes": [],
    }

    if not smart_data:
        # Attempt sysfs fallback for NVMe temperature
        if "nvme" in dev_name:
            info["temp_c"] = _nvme_sysfs_temp()
        return info

    # Overall health
    smart_status = smart_data.get("smart_status", {})
    if "passed" in smart_status:
        info["health_passed"] = smart_status["passed"]
        info["health_status"] = "PASSED" if smart_status["passed"] else "FAILING"

    # Power-on time & cycles
    power_on = smart_data.get("power_on_time", {})
    if "hours" in power_on:
        info["power_on_hours"] = power_on["hours"]
    info["power_cycles"] = smart_data.get("power_cycle_count")

    # Temperature
    temp_obj = smart_data.get("temperature", {})
    if "current" in temp_obj:
        info["temp_c"] = temp_obj["current"]

    # NVMe-specific log
    _parse_nvme_log(smart_data, info)

    # ATA-specific attributes
    _parse_ata_attributes(smart_data, info)

    # Sysfs fallback if no temp found
    if info["temp_c"] is None and "nvme" in dev_name:
        info["temp_c"] = _nvme_sysfs_temp()

    return info


def _parse_nvme_log(smart_data: dict[str, Any], info: dict[str, Any]) -> None:
    """Extract health data from the NVMe SMART log if present."""
    nvme_log = smart_data.get("nvme_smart_health_information_log", {})
    if not nvme_log:
        return

    info["wear_pct"] = nvme_log.get("percentage_used")
    if "temperature" in nvme_log and info["temp_c"] is None:
        info["temp_c"] = nvme_log["temperature"]

    data_written = nvme_log.get("data_units_written")
    if data_written is not None:
        info["tbw_written"] = (data_written * 512_000) / (1024**4)

    data_read = nvme_log.get("data_units_read")
    if data_read is not None:
        info["tb_read"] = (data_read * 512_000) / (1024**4)

    info["media_errors"] = nvme_log.get("media_errors", 0)

    crit_warn = nvme_log.get("critical_warning", 0)
    if crit_warn != 0:
        info["health_status"] = "WARNING"


def _parse_ata_attributes(smart_data: dict[str, Any], info: dict[str, Any]) -> None:
    """Extract health data from ATA S.M.A.R.T. attribute tables."""
    ata_attrs = smart_data.get("ata_smart_attributes", {}).get("table", [])
    attributes_list: list[dict[str, Any]] = []

    for attr in ata_attrs:
        name_attr = attr.get("name", "")
        attr_id = attr.get("id")
        raw_val = attr.get("raw", {}).get("value", 0)
        raw_str = attr.get("raw", {}).get("string", str(raw_val))

        attributes_list.append({
            "id": attr_id,
            "name": name_attr,
            "value": attr.get("value"),
            "worst": attr.get("worst"),
            "thresh": attr.get("thresh"),
            "raw": raw_str,
        })

        # Wear / lifetime
        if name_attr in WEAR_LEVEL_ATTRS or attr_id in WEAR_LEVEL_IDS:
            info["wear_pct"] = 100 - attr.get("value", 100)
        elif name_attr == "Percent_Lifetime_Used":
            info["wear_pct"] = attr.get("value", 0)

        # Reallocated sectors
        elif name_attr == "Reallocated_Sector_Ct" or attr_id == 5:
            info["reallocated_sectors"] = raw_val

        # Total data written
        elif name_attr in WRITE_TOTAL_ATTRS or attr_id == 241:
            info["tbw_written"] = _convert_write_units(name_attr, raw_val)

        # Total data read
        elif name_attr in READ_TOTAL_ATTRS or attr_id == 242:
            info["tb_read"] = _convert_read_units(name_attr, raw_val)

        # Temperature fallback
        elif name_attr == "Temperature_Celsius" and info["temp_c"] is None:
            info["temp_c"] = raw_val

    info["attributes"] = attributes_list


def _convert_write_units(name: str, raw_val: int) -> float:
    """Convert a raw write-total value to terabytes."""
    if name == "Host_Writes_32MiB":
        return (raw_val * 32 * 1024 * 1024) / (1024**4)
    if name == "Host_Writes_GiB":
        return raw_val / 1024.0
    return (raw_val * 512) / (1024**4)


def _convert_read_units(name: str, raw_val: int) -> float:
    """Convert a raw read-total value to terabytes."""
    if name == "Host_Reads_32MiB":
        return (raw_val * 32 * 1024 * 1024) / (1024**4)
    if name == "Host_Reads_GiB":
        return raw_val / 1024.0
    return (raw_val * 512) / (1024**4)


def _nvme_sysfs_temp() -> float | None:
    """Attempt to read NVMe temperature from sysfs hwmon."""
    for hwmon in glob.glob(os.path.join(SYS_HWMON_BASE, "hwmon*")):
        try:
            name = read_file(os.path.join(hwmon, "name"))
            if "nvme" not in name:
                continue
            temp_path = os.path.join(hwmon, "temp1_input")
            if os.path.exists(temp_path):
                return int(read_file(temp_path).strip()) / 1000.0
        except (OSError, ValueError) as exc:
            logger.debug("NVMe sysfs temp read failed for %s: %s", hwmon, exc)
    return None
