#!/usr/bin/env python3
# ThinkControlCenter — Lenovo Power, Firmware, Hardware & Storage Hub for Linux
# Native GTK4 / Libadwaita application for ThinkPad, ThinkCentre & ThinkStation systems.

import sys
import os
import glob
import json
import subprocess
import threading
import shutil
from datetime import datetime

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Pango, Gio, Gdk

CSS_DATA = (
    "\n"
    "window {\n"
    "    background-color: #121214;\n"
    "}\n"
    "\n"
    ".view-container {\n"
    "    background-color: #18181b;\n"
    "    border-radius: 12px;\n"
    "    padding: 12px;\n"
    "}\n"
    "\n"
    ".card-box {\n"
    "    background-color: #1c1c20;\n"
    "    border: 1px solid #27272a;\n"
    "    border-radius: 10px;\n"
    "    padding: 16px;\n"
    "    margin-bottom: 14px;\n"
    "}\n"
    "\n"
    ".card-title {\n"
    "    font-size: 12.5pt;\n"
    "    font-weight: 700;\n"
    "    color: #60a5fa;\n"
    "    margin-bottom: 6px;\n"
    "}\n"
    "\n"
    ".card-subtitle {\n"
    "    font-size: 9pt;\n"
    "    color: #9ca3af;\n"
    "    margin-bottom: 12px;\n"
    "}\n"
    "\n"
    ".stat-label {\n"
    "    font-size: 10pt;\n"
    "    font-weight: 600;\n"
    "    color: #d1d5db;\n"
    "}\n"
    "\n"
    ".stat-value {\n"
    "    font-size: 10.5pt;\n"
    "    font-weight: 700;\n"
    "    color: #60a5fa;\n"
    "}\n"
    "\n"
    ".metric-tile {\n"
    "    background-color: #242429;\n"
    "    border: 1px solid #333338;\n"
    "    border-radius: 8px;\n"
    "    padding: 10px 14px;\n"
    "}\n"
    "\n"
    ".metric-tile-title {\n"
    "    font-size: 8.5pt;\n"
    "    font-weight: 600;\n"
    "    color: #9ca3af;\n"
    "}\n"
    "\n"
    ".metric-tile-value {\n"
    "    font-size: 11.5pt;\n"
    "    font-weight: 700;\n"
    "    color: #f3f4f6;\n"
    "}\n"
    "\n"
    ".badge-sata {\n"
    "    background-color: rgba(59, 130, 246, 0.2);\n"
    "    color: #60a5fa;\n"
    "    border: 1px solid rgba(59, 130, 246, 0.4);\n"
    "    border-radius: 6px;\n"
    "    padding: 2px 8px;\n"
    "    font-size: 8.5pt;\n"
    "    font-weight: 700;\n"
    "}\n"
    "\n"
    ".badge-nvme {\n"
    "    background-color: rgba(168, 85, 247, 0.2);\n"
    "    color: #c084fc;\n"
    "    border: 1px solid rgba(168, 85, 247, 0.4);\n"
    "    border-radius: 6px;\n"
    "    padding: 2px 8px;\n"
    "    font-size: 8.5pt;\n"
    "    font-weight: 700;\n"
    "}\n"
    "\n"
    ".badge-fs {\n"
    "    background-color: #27272a;\n"
    "    color: #e5e7eb;\n"
    "    border: 1px solid #3f3f46;\n"
    "    border-radius: 4px;\n"
    "    padding: 1px 6px;\n"
    "    font-size: 8pt;\n"
    "    font-weight: 600;\n"
    "}\n"
    "\n"
    ".health-badge-passed {\n"
    "    background-color: rgba(16, 185, 129, 0.2);\n"
    "    color: #34d399;\n"
    "    border: 1px solid rgba(16, 185, 129, 0.5);\n"
    "    border-radius: 6px;\n"
    "    padding: 4px 10px;\n"
    "    font-size: 9pt;\n"
    "    font-weight: 700;\n"
    "}\n"
    "\n"
    ".health-badge-warning {\n"
    "    background-color: rgba(245, 158, 11, 0.2);\n"
    "    color: #fbbf24;\n"
    "    border: 1px solid rgba(245, 158, 11, 0.5);\n"
    "    border-radius: 6px;\n"
    "    padding: 4px 10px;\n"
    "    font-size: 9pt;\n"
    "    font-weight: 700;\n"
    "}\n"
    "\n"
    ".health-badge-failing {\n"
    "    background-color: rgba(239, 68, 68, 0.2);\n"
    "    color: #f87171;\n"
    "    border: 1px solid rgba(239, 68, 68, 0.5);\n"
    "    border-radius: 6px;\n"
    "    padding: 4px 10px;\n"
    "    font-size: 9pt;\n"
    "    font-weight: 700;\n"
    "}\n"
    "\n"
    ".health-badge-unknown {\n"
    "    background-color: rgba(113, 113, 122, 0.2);\n"
    "    color: #a1a1aa;\n"
    "    border: 1px solid rgba(113, 113, 122, 0.4);\n"
    "    border-radius: 6px;\n"
    "    padding: 4px 10px;\n"
    "    font-size: 9pt;\n"
    "    font-weight: 600;\n"
    "}\n"
    "\n"
    ".temp-badge-normal {\n"
    "    background-color: rgba(16, 185, 129, 0.18);\n"
    "    color: #10b981;\n"
    "    border: 1px solid rgba(16, 185, 129, 0.4);\n"
    "    border-radius: 6px;\n"
    "    padding: 3px 8px;\n"
    "    font-weight: 700;\n"
    "}\n"
    "\n"
    ".temp-badge-warning {\n"
    "    background-color: rgba(245, 158, 11, 0.18);\n"
    "    color: #f59e0b;\n"
    "    border: 1px solid rgba(245, 158, 11, 0.4);\n"
    "    border-radius: 6px;\n"
    "    padding: 3px 8px;\n"
    "    font-weight: 700;\n"
    "}\n"
    "\n"
    ".temp-badge-critical {\n"
    "    background-color: rgba(239, 68, 68, 0.18);\n"
    "    color: #ef4444;\n"
    "    border: 1px solid rgba(239, 68, 68, 0.4);\n"
    "    border-radius: 6px;\n"
    "    padding: 3px 8px;\n"
    "    font-weight: 700;\n"
    "}\n"
    "\n"
    ".btn-acoustic {\n"
    "    background: linear-gradient(135deg, #059669 0%, #047857 100%);\n"
    "    color: #ffffff;\n"
    "    font-weight: 700;\n"
    "    border-radius: 8px;\n"
    "    padding: 10px 16px;\n"
    "}\n"
    ".btn-acoustic:hover {\n"
    "    background: linear-gradient(135deg, #10b981 0%, #059669 100%);\n"
    "}\n"
    "\n"
    ".btn-thermal {\n"
    "    background: linear-gradient(135deg, #d97706 0%, #b45309 100%);\n"
    "    color: #ffffff;\n"
    "    font-weight: 700;\n"
    "    border-radius: 8px;\n"
    "    padding: 10px 16px;\n"
    "}\n"
    ".btn-thermal:hover {\n"
    "    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);\n"
    "}\n"
    "\n"
    ".btn-fullspeed {\n"
    "    background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);\n"
    "    color: #ffffff;\n"
    "    font-weight: 700;\n"
    "    border-radius: 8px;\n"
    "    padding: 10px 16px;\n"
    "}\n"
    ".btn-fullspeed:hover {\n"
    "    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);\n"
    "}\n"
    "\n"
    ".btn-purple {\n"
    "    background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);\n"
    "    color: #ffffff;\n"
    "    font-weight: 600;\n"
    "    border-radius: 6px;\n"
    "}\n"
    ".btn-purple:hover {\n"
    "    background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);\n"
    "}\n"
    "\n"
    ".console-view {\n"
    "    background-color: #0c0c0e;\n"
    "    color: #10b981;\n"
    "    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;\n"
    "    font-size: 9pt;\n"
    "    border: 1px solid #27272a;\n"
    "    border-radius: 6px;\n"
    "    padding: 8px;\n"
    "}\n"
    "\n"
)

class HardwareScanner:
    @staticmethod
    def get_pci_tree():
        items = []
        try:
            res = subprocess.run(["lspci", "-nn"], capture_output=True, text=True, check=False)
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            
            root_host = {"title": "CPU / Host Bridge", "children": []}
            pch_node = {"title": "PCH (Platform Controller Hub)", "children": [
                {"title": "LPC Bus -> Nuvoton NCT6683D Embedded Controller", "children": []}
            ]}
            other_nodes = []

            for line in lines:
                if "Host bridge" in line:
                    root_host["children"].append({"title": line, "children": []})
                elif "ISA bridge" in line or "LPC Controller" in line:
                    pch_node["children"][0]["children"].append({"title": line, "children": []})
                elif "SMBus" in line:
                    pch_node["children"].append({"title": f"SMBus Controller: {line}", "children": []})
                else:
                    other_nodes.append({"title": line, "children": []})
            
            if root_host["children"]:
                items.append(root_host)
            if pch_node["children"]:
                items.append(pch_node)
            items.extend(other_nodes)
        except Exception as e:
            items.append({"title": f"PCI scan error: {e}", "children": []})
        return items

    @staticmethod
    def get_usb_tree():
        items = []
        try:
            res = subprocess.run(["lsusb"], capture_output=True, text=True, check=False)
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            hubs = {}
            for line in lines:
                bus_id = line[4:7] if len(line) >= 7 and line.startswith("Bus ") else "Generic"
                if bus_id not in hubs:
                    hubs[bus_id] = {"title": f"USB Bus {bus_id}", "children": []}
                hubs[bus_id]["children"].append({"title": line, "children": []})
            items.extend(hubs.values())
        except Exception as e:
            items.append({"title": f"USB scan error: {e}", "children": []})
        return items

    @staticmethod
    def get_network_tree():
        items = []
        try:
            res = subprocess.run(["ip", "-br", "link"], capture_output=True, text=True, check=False)
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    name, status, mac = parts[0], parts[1], parts[2]
                    items.append({
                        "title": f"{name} ({status})",
                        "children": [
                            {"title": f"State: {status}", "children": []},
                            {"title": f"MAC Address: {mac}", "children": []}
                        ]
                    })
        except Exception as e:
            items.append({"title": f"Network scan error: {e}", "children": []})
        return items

    @staticmethod
    def get_display_tree():
        active_displays = []
        inactive_displays = []
        drm_paths = glob.glob("/sys/class/drm/card*-*")
        
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
                    monitor_name = ""
                    edid_p = os.path.join(p, "edid")
                    if os.path.exists(edid_p):
                        with open(edid_p, "rb") as ef:
                            edid = ef.read()
                            if len(edid) >= 128:
                                for off in range(54, 109, 18):
                                    if off + 18 <= len(edid):
                                        blk = edid[off:off+18]
                                        if blk[0] == 0 and blk[1] == 0 and blk[2] == 0 and blk[3] == 0xfc and blk[4] == 0:
                                            monitor_name = blk[5:18].decode("ascii", errors="ignore").strip()
                                            break
                    title = f"{monitor_name} ({display_id})" if monitor_name else f"Display Port ({display_id})"
                    active_displays.append({"title": title, "children": [
                        {"title": f"Status: Connected", "children": []},
                        {"title": f"Sysfs Node: {p}", "children": []}
                    ]})
                else:
                    inactive_displays.append({"title": f"{display_id} (Disconnected)", "children": []})
            except Exception:
                pass

        res = []
        if active_displays:
            res.append({"title": "Active Displays", "children": active_displays})
        else:
            res.append({"title": "Active Displays (None detected)", "children": []})
        if inactive_displays:
            res.append({"title": "Inactive Ports", "children": inactive_displays})
        return res

    @staticmethod
    def get_input_tree():
        kbds = []
        mice = []
        sys_btns = []
        
        path = "/proc/bus/input/devices"
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
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

                    item = {"title": name, "children": [{"title": f"Handlers: {handlers}", "children": []}]}
                    if "mouse" in handlers:
                        mice.append(item)
                    elif "kbd" in handlers:
                        if any(x in name for x in ["Power Button", "Sleep Button", "Video Bus", "PC Speaker", "Mic", "Headphone", "HDMI"]):
                            sys_btns.append(item)
                        else:
                            kbds.append(item)
            except Exception:
                pass

        res = []
        if kbds:
            res.append({"title": "Keyboards", "children": kbds})
        if mice:
            res.append({"title": "Mice & Pointing Devices", "children": mice})
        if sys_btns:
            res.append({"title": "System Controls & Buttons", "children": sys_btns})
        return res


class DiskScanner:
    @staticmethod
    def get_disks(smart_cache=None):
        smart_cache = smart_cache or {}
        res = subprocess.run(
            ["lsblk", "--json", "-b", "-o", "NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,SERIAL,ROTA,TRAN,STATE,REV"],
            capture_output=True, text=True, check=False
        )
        try:
            raw_devices = json.loads(res.stdout).get("blockdevices", [])
        except Exception:
            raw_devices = []

        disks = []
        for dev in raw_devices:
            dev_type = dev.get("type")
            if dev_type not in ["disk", "loop", "rom"]:
                continue
            if dev.get("name", "").startswith("loop"):
                continue

            name = dev.get("name")
            path = dev.get("path") or f"/dev/{name}"
            size_bytes = dev.get("size", 0)
            size_gb = size_bytes / (1024**3)
            model = dev.get("model") or ("ZRAM Swap" if "zram" in name else "Generic Storage Device")
            serial = dev.get("serial") or "N/A"
            tran = (dev.get("tran") or ("NVME" if "nvme" in name else ("SWAP" if "zram" in name else "SATA"))).upper()
            firmware = dev.get("rev") or "N/A"

            partitions = []
            children = dev.get("children", [])
            if not children and dev.get("mountpoints"):
                children = [dev]

            for child in children:
                c_name = child.get("name")
                c_path = child.get("path") or f"/dev/{c_name}"
                c_fstype = child.get("fstype") or "unknown"
                c_size = child.get("size", 0) / (1024**3)
                mounts = child.get("mountpoints", [])
                
                for m in mounts:
                    if m:
                        used_gb = 0.0
                        total_gb = c_size
                        free_gb = 0.0
                        pct = 0.0
                        if os.path.exists(m) and not m.startswith("["):
                            try:
                                u = shutil.disk_usage(m)
                                total_gb = u.total / (1024**3)
                                used_gb = u.used / (1024**3)
                                free_gb = u.free / (1024**3)
                                pct = (u.used / u.total * 100) if u.total > 0 else 0.0
                            except Exception:
                                pass
                        partitions.append({
                            "name": c_name,
                            "path": c_path,
                            "mount": m,
                            "fstype": c_fstype,
                            "total_gb": total_gb,
                            "used_gb": used_gb,
                            "free_gb": free_gb,
                            "pct": pct
                        })

            # Check SMART cache or fallback sysfs
            smart_data = smart_cache.get(path, {})
            health_status = "UNKNOWN"
            health_passed = None
            temp_c = None
            power_on_hours = None
            power_cycles = None
            tbw_written = None
            tb_read = None
            wear_pct = None
            media_errors = None
            reallocated_sectors = None
            attributes_list = []

            if smart_data:
                # smartctl json parsing
                smart_status = smart_data.get("smart_status", {})
                if "passed" in smart_status:
                    health_passed = smart_status["passed"]
                    health_status = "PASSED" if health_passed else "FAILING"

                power_on = smart_data.get("power_on_time", {})
                if "hours" in power_on:
                    power_on_hours = power_on["hours"]
                power_cycles = smart_data.get("power_cycle_count")

                temp_obj = smart_data.get("temperature", {})
                if "current" in temp_obj:
                    temp_c = temp_obj["current"]

                # NVMe specific
                nvme_log = smart_data.get("nvme_smart_health_information_log", {})
                if nvme_log:
                    wear_pct = nvme_log.get("percentage_used")
                    if "temperature" in nvme_log and temp_c is None:
                        temp_c = nvme_log["temperature"]
                    data_written = nvme_log.get("data_units_written")
                    if data_written is not None:
                        tbw_written = (data_written * 512000) / (1024**4)
                    data_read = nvme_log.get("data_units_read")
                    if data_read is not None:
                        tb_read = (data_read * 512000) / (1024**4)
                    media_errors = nvme_log.get("media_errors", 0)
                    crit_warn = nvme_log.get("critical_warning", 0)
                    if crit_warn != 0:
                        health_status = "WARNING"

                # ATA specific
                ata_attrs = smart_data.get("ata_smart_attributes", {}).get("table", [])
                for attr in ata_attrs:
                    name_attr = attr.get("name")
                    raw_val = attr.get("raw", {}).get("value", 0)
                    raw_str = attr.get("raw", {}).get("string", str(raw_val))
                    attributes_list.append({
                        "id": attr.get("id"),
                        "name": name_attr,
                        "value": attr.get("value"),
                        "worst": attr.get("worst"),
                        "thresh": attr.get("thresh"),
                        "raw": raw_str
                    })
                    name_attr = attr.get("name", "")
                    attr_id = attr.get("id")
                    
                    if name_attr in ["Wear_Leveling_Count", "SSD_Life_Left", "Media_Wearout_Indicator"] or attr_id in [177, 231, 232, 169]:
                        wear_pct = 100 - attr.get("value", 100)
                    elif name_attr in ["Percent_Lifetime_Remain", "Remaining_Lifetime_Perc"] or attr_id in [202]:
                        wear_pct = 100 - attr.get("value", 100)
                    elif name_attr == "Percent_Lifetime_Used":
                        wear_pct = attr.get("value", 0)
                        
                    elif name_attr == "Reallocated_Sector_Ct" or attr_id == 5:
                        reallocated_sectors = raw_val
                        
                    elif name_attr in ["Total_LBAs_Written", "Host_Writes_32MiB", "Host_Writes_GiB", "Data_Units_Written"] or attr_id == 241:
                        if name_attr == "Host_Writes_32MiB":
                            tbw_written = (raw_val * 32 * 1024 * 1024) / (1024**4)
                        elif name_attr == "Host_Writes_GiB":
                            tbw_written = raw_val / 1024.0
                        else:
                            tbw_written = (raw_val * 512) / (1024**4)
                            
                    elif name_attr in ["Total_LBAs_Read", "Host_Reads_32MiB", "Host_Reads_GiB"] or attr_id == 242:
                        if name_attr == "Host_Reads_32MiB":
                            tb_read = (raw_val * 32 * 1024 * 1024) / (1024**4)
                        elif name_attr == "Host_Reads_GiB":
                            tb_read = raw_val / 1024.0
                        else:
                            tb_read = (raw_val * 512) / (1024**4)
                            
                    elif name_attr == "Temperature_Celsius" and temp_c is None:
                        temp_c = raw_val

            # Fallback for NVMe temperature from sysfs hwmon if not in smartctl
            if temp_c is None and "nvme" in name:
                for h in glob.glob("/sys/class/hwmon/hwmon*"):
                    try:
                        n_file = os.path.join(h, "name")
                        if os.path.exists(n_file) and "nvme" in open(n_file).read():
                            t_file = os.path.join(h, "temp1_input")
                            if os.path.exists(t_file):
                                temp_c = int(open(t_file).read().strip()) / 1000.0
                                break
                    except Exception:
                        pass

            disks.append({
                "name": name,
                "path": path,
                "model": model,
                "serial": serial,
                "firmware": firmware,
                "tran": tran,
                "size_gb": size_gb,
                "partitions": partitions,
                "health_status": health_status,
                "health_passed": health_passed,
                "temp_c": temp_c,
                "power_on_hours": power_on_hours,
                "power_cycles": power_cycles,
                "wear_pct": wear_pct,
                "tbw_written": tbw_written,
                "tb_read": tb_read,
                "media_errors": media_errors,
                "reallocated_sectors": reallocated_sectors,
                "attributes": attributes_list
            })
        return disks


class TelemetryScanner:
    def __init__(self):
        self.prev_idle = 0
        self.prev_total = 0
        self.has_prev = False

    def get_cpu_usage(self):
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            if not line.startswith("cpu "):
                return 0.0
            parts = [int(x) for x in line.split()[1:9]]
            user, nice, system, idle, iowait, irq, softirq, steal = parts
            idle_time = idle + iowait
            non_idle_time = user + nice + system + irq + softirq + steal
            total_time = idle_time + non_idle_time

            if not self.has_prev:
                self.prev_idle = idle_time
                self.prev_total = total_time
                self.has_prev = True
                return 0.0

            total_diff = total_time - self.prev_total
            idle_diff = idle_time - self.prev_idle
            self.prev_idle = idle_time
            self.prev_total = total_time

            if total_diff <= 0:
                return 0.0
            return max(0.0, min(100.0, 100.0 * (1.0 - (idle_diff / total_diff))))
        except Exception:
            return 0.0

    def get_memory_usage(self):
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            mem = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    mem[parts[0].strip()] = int(parts[1].split()[0])
            total_gb = mem.get("MemTotal", 0) / (1024.0 * 1024.0)
            avail_gb = mem.get("MemAvailable", 0) / (1024.0 * 1024.0)
            used_gb = max(0.0, total_gb - avail_gb)
            pct = int((used_gb / total_gb) * 100) if total_gb > 0 else 0
            return used_gb, total_gb, pct
        except Exception:
            return 0.0, 0.0, 0

    def get_thermals(self):
        sensors = []
        hwmons = sorted(glob.glob("/sys/class/hwmon/hwmon*"))
        for h in hwmons:
            name_p = os.path.join(h, "name")
            group_name = "Hardware Sensor"
            if os.path.exists(name_p):
                try:
                    with open(name_p, "r") as f:
                        group_name = f.read().strip()
                except Exception:
                    pass

            temp_inputs = sorted(glob.glob(os.path.join(h, "temp*_input")))
            for ti in temp_inputs:
                try:
                    with open(ti, "r") as f:
                        milli = int(f.read().strip())
                    val = milli / 1000.0
                    if val < -50 or val > 150:
                        continue
                    prefix = os.path.basename(ti).split("_")[0]
                    label_p = os.path.join(h, prefix + "_label")
                    label = prefix
                    if os.path.exists(label_p):
                        with open(label_p, "r") as lf:
                            label = lf.read().strip()
                    sensors.append({
                        "group": group_name,
                        "label": label,
                        "temp": val
                    })
                except Exception:
                    pass
        return sensors


class WakeupScanner:
    @staticmethod
    def get_devices():
        devices = []
        path = "/proc/acpi/wakeup"
        if not os.path.exists(path):
            return devices
        try:
            with open(path, "r") as f:
                lines = f.readlines()
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    node = parts[0]
                    state = parts[1]
                    status_str = parts[2]
                    enabled = "enabled" in status_str
                    sysfs_node = parts[3] if len(parts) >= 4 else ""

                    desc = "ACPI Wakeup Source"
                    if node == "XHC":
                        desc = "USB 3.0 Host Controller (Keyboard / Mouse wake)"
                    elif node == "GLAN":
                        desc = "Intel Gigabit LAN (Wake-on-LAN)"
                    elif node in ["RP06", "PXSX"]:
                        desc = "PCIe WLAN / Peripheral"
                    elif node == "HDAS":
                        desc = "Intel HD Audio"
                    elif node == "PS2K":
                        desc = "PS/2 Keyboard"
                    elif node == "PS2M":
                        desc = "PS/2 Mouse"
                    elif node.startswith("RP"):
                        desc = "PCIe Root Port"
                    elif node.startswith("PEG"):
                        desc = "PCI Express Graphics"

                    devices.append({
                        "node": node,
                        "state": state,
                        "enabled": enabled,
                        "sysfs": sysfs_node,
                        "desc": desc
                    })
        except Exception:
            pass
        return devices


class ThinkControlCenterWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="ThinkControlCenter — Lenovo Power & Firmware Hub")
        self.set_default_size(1180, 800)

        self.telemetry_scanner = TelemetryScanner()
        self.active_process = None
        self.smart_cache = {}

        # Build Main UI Layout
        self.setup_ui()

        # Start Telemetry Poller (every 1500 ms)
        GLib.timeout_add(1500, self.on_telemetry_tick)
        self.on_telemetry_tick()

        # Initial scans
        self.rescan_hardware()
        self.refresh_wakeup()
        self.refresh_disks()

    def setup_ui(self):
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(root_box)

        # Header Bar
        header = Adw.HeaderBar()
        self.view_switcher = Adw.ViewSwitcher()
        self.view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(self.view_switcher)
        root_box.append(header)

        # Vertical Paned: Top Views + Bottom Console
        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        paned.set_vexpand(True)
        paned.set_hexpand(True)
        paned.set_position(540)
        root_box.append(paned)

        # View Stack
        self.view_stack = Adw.ViewStack()
        self.view_switcher.set_stack(self.view_stack)

        # Add 5 Main Tabs
        self.tab_arch = self.create_arch_tab()
        self.view_stack.add_titled_with_icon(self.tab_arch, "arch", "Architecture", "network-workgroup-symbolic")

        self.tab_telemetry = self.create_telemetry_tab()
        self.view_stack.add_titled_with_icon(self.tab_telemetry, "telemetry", "Telemetry", "utilities-system-monitor-symbolic")

        self.tab_storage = self.create_storage_tab()
        self.view_stack.add_titled_with_icon(self.tab_storage, "storage", "Storage & SMART", "drive-harddisk-symbolic")

        self.tab_cooling = self.create_cooling_tab()
        self.view_stack.add_titled_with_icon(self.tab_cooling, "cooling", "Cooling & ICE", "weather-snow-symbolic")

        self.tab_wakeup = self.create_wakeup_tab()
        self.view_stack.add_titled_with_icon(self.tab_wakeup, "wakeup", "ACPI Wakeup", "system-shutdown-symbolic")

        paned.set_start_child(self.view_stack)

        # Bottom Console Log Frame
        console_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        console_box.set_margin_start(12)
        console_box.set_margin_end(12)
        console_box.set_margin_bottom(10)
        console_box.set_margin_top(4)

        console_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_console = Gtk.Label(label="<b>System Console &amp; Privilege Execution Log</b>", use_markup=True)
        lbl_console.add_css_class("card-subtitle")
        lbl_console.set_xalign(0)
        console_hdr.append(lbl_console)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        console_hdr.append(spacer)

        btn_clear = Gtk.Button(label="Clear Console")
        btn_clear.connect("clicked", lambda b: self.console_buffer.set_text(""))
        console_hdr.append(btn_clear)

        console_box.append(console_hdr)

        console_scroll = Gtk.ScrolledWindow()
        console_scroll.set_min_content_height(140)
        self.console_view = Gtk.TextView()
        self.console_view.set_editable(False)
        self.console_view.set_cursor_visible(False)
        self.console_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.console_view.add_css_class("console-view")
        self.console_buffer = self.console_view.get_buffer()
        console_scroll.set_child(self.console_view)
        console_box.append(console_scroll)

        paned.set_end_child(console_box)

        self.log_message("ThinkControlCenter started. Hardware, storage & WMI interfaces initialized.", "#60a5fa")

    # ==========================
    # Tab 1: Architecture View
    # ==========================
    def create_arch_tab(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        container.set_margin_start(16)
        container.set_margin_end(16)
        container.set_margin_top(14)
        container.set_margin_bottom(10)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search hardware (e.g. NVMe, Intel, USB, Audio, PCI, Display, SATA)...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        toolbar.append(self.search_entry)

        btn_rescan = Gtk.Button(label="Rescan Hardware")
        btn_rescan.add_css_class("suggested-action")
        btn_rescan.connect("clicked", lambda b: self.rescan_hardware())
        toolbar.append(btn_rescan)

        btn_expand = Gtk.Button(label="Expand All")
        btn_expand.connect("clicked", lambda b: self.arch_treeview.expand_all())
        toolbar.append(btn_expand)

        btn_collapse = Gtk.Button(label="Collapse")
        btn_collapse.connect("clicked", lambda b: self.arch_treeview.collapse_all())
        toolbar.append(btn_collapse)

        container.append(toolbar)

        # TreeView with Filter
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        
        self.tree_store = Gtk.TreeStore(str, str, bool)
        self.tree_filter = self.tree_store.filter_new()
        self.tree_filter.set_visible_column(2)

        self.arch_treeview = Gtk.TreeView(model=self.tree_filter)
        self.arch_treeview.set_headers_visible(False)
        self.arch_treeview.set_enable_search(False)

        col = Gtk.TreeViewColumn("Hardware")
        cell = Gtk.CellRendererText()
        cell.set_property("font", "Cantarell 10")
        col.pack_start(cell, True)
        col.add_attribute(cell, "text", 0)
        self.arch_treeview.append_column(col)

        scroll.set_child(self.arch_treeview)
        container.append(scroll)
        return container

    def rescan_hardware(self):
        self.log_message("Scanning system topology, PCI bridges, DRM displays and USB devices...")
        self.tree_store.clear()

        # 1. Motherboard & Chipsets
        pci_root = self.tree_store.append(None, ["<b>Motherboard & Chipsets</b>", "motherboard chipsets pci", True])
        for item in HardwareScanner.get_pci_tree():
            self._add_tree_node(pci_root, item)

        # 2. Displays & Monitors
        disp_root = self.tree_store.append(None, ["<b>Displays & Monitors</b>", "displays monitors screen drm dp hdmi", True])
        for item in HardwareScanner.get_display_tree():
            self._add_tree_node(disp_root, item)

        # 3. Input Devices
        input_root = self.tree_store.append(None, ["<b>Input Devices (Keyboard / Mouse)</b>", "input keyboard mouse button", True])
        for item in HardwareScanner.get_input_tree():
            self._add_tree_node(input_root, item)

        # 4. USB Controllers
        usb_root = self.tree_store.append(None, ["<b>USB Controllers & Devices</b>", "usb hub controller", True])
        for item in HardwareScanner.get_usb_tree():
            self._add_tree_node(usb_root, item)

        # 5. Network Interfaces
        net_root = self.tree_store.append(None, ["<b>Network Interfaces</b>", "network ethernet wifi wlan lan", True])
        for item in HardwareScanner.get_network_tree():
            self._add_tree_node(net_root, item)

        # 6. Storage & Block Devices
        storage_root = self.tree_store.append(None, ["<b>Storage & Block Devices</b>", "storage nvme disk ssd sata samsung", True])
        disks = DiskScanner.get_disks(self.smart_cache)
        for d in disks:
            d_node = {
                "title": f"Disk: {d['model']} ({d['path']}, {d['size_gb']:.1f} GB, {d['tran']})",
                "children": []
            }
            d_node["children"].append({"title": f"Serial Number: {d['serial']}", "children": []})
            d_node["children"].append({"title": f"Firmware Revision: {d['firmware']}", "children": []})
            if d.get("temp_c") is not None:
                d_node["children"].append({"title": f"Temperature: {d['temp_c']:.1f} °C", "children": []})
            for p in d.get("partitions", []):
                p_desc = f"Partition: {p['name']} ({p['mount']}) — {p['fstype']}, {p['used_gb']:.1f} / {p['total_gb']:.1f} GB ({p['pct']:.1f}%)"
                d_node["children"].append({"title": p_desc, "children": []})
            self._add_tree_node(storage_root, d_node)

        self.arch_treeview.expand_all()
        self.log_message("System architecture scan complete.", "#10b981")

    def _add_tree_node(self, parent_iter, node_dict):
        title = node_dict.get("title", "")
        children = node_dict.get("children", [])
        search_text = title.lower()
        it = self.tree_store.append(parent_iter, [title, search_text, True])
        for child in children:
            self._add_tree_node(it, child)

    def on_search_changed(self, entry):
        query = entry.get_text().strip().lower()
        if not query:
            def show_all(model, path, it):
                self.tree_store.set_value(it, 2, True)
                return False
            self.tree_store.foreach(show_all)
            return

        def traverse_and_mark(it):
            child_it = self.tree_store.iter_children(it)
            any_child_visible = False
            while child_it:
                traverse_and_mark(child_it)
                if self.tree_store.get_value(child_it, 2):
                    any_child_visible = True
                child_it = self.tree_store.iter_next(child_it)

            txt = self.tree_store.get_value(it, 1) or ""
            is_visible = (query in txt) or any_child_visible
            self.tree_store.set_value(it, 2, is_visible)

        top_it = self.tree_store.get_iter_first()
        while top_it:
            traverse_and_mark(top_it)
            top_it = self.tree_store.iter_next(top_it)

        self.arch_treeview.expand_all()

    # ==========================
    # Tab 2: Telemetry & Sensors
    # ==========================
    def create_telemetry_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        scroll.set_child(main_box)

        # Card 1: Utilization
        card_util = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_util.add_css_class("card-box")

        lbl_util_title = Gtk.Label(label="System Utilization", xalign=0)
        lbl_util_title.add_css_class("card-title")
        card_util.append(lbl_util_title)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(12)

        # CPU Row
        lbl_cpu = Gtk.Label(label="CPU Load:", xalign=0)
        lbl_cpu.add_css_class("stat-label")
        grid.attach(lbl_cpu, 0, 0, 1, 1)

        self.cpu_bar = Gtk.ProgressBar()
        self.cpu_bar.set_hexpand(True)
        self.cpu_bar.set_show_text(False)
        grid.attach(self.cpu_bar, 1, 0, 1, 1)

        self.lbl_cpu_val = Gtk.Label(label="0.0%", xalign=1)
        self.lbl_cpu_val.add_css_class("stat-value")
        self.lbl_cpu_val.set_size_request(80, -1)
        grid.attach(self.lbl_cpu_val, 2, 0, 1, 1)

        # RAM Row
        lbl_ram = Gtk.Label(label="RAM Usage:", xalign=0)
        lbl_ram.add_css_class("stat-label")
        grid.attach(lbl_ram, 0, 1, 1, 1)

        self.ram_bar = Gtk.ProgressBar()
        self.ram_bar.set_hexpand(True)
        self.ram_bar.set_show_text(False)
        grid.attach(self.ram_bar, 1, 1, 1, 1)

        self.lbl_ram_val = Gtk.Label(label="0 / 0 GB", xalign=1)
        self.lbl_ram_val.add_css_class("stat-value")
        self.lbl_ram_val.set_size_request(160, -1)
        grid.attach(self.lbl_ram_val, 2, 1, 1, 1)

        card_util.append(grid)
        main_box.append(card_util)

        # Card 2: Hardware Temperatures Table
        card_temp = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card_temp.add_css_class("card-box")

        lbl_temp_title = Gtk.Label(label="Hardware Temperature Sensors (/sys/class/hwmon)", xalign=0)
        lbl_temp_title.add_css_class("card-title")
        card_temp.append(lbl_temp_title)

        self.temp_store = Gtk.ListStore(str, str, float, str, str)
        self.temp_tree = Gtk.TreeView(model=self.temp_store)
        self.temp_tree.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

        col_drv = Gtk.TreeViewColumn("Device / Driver")
        cell_drv = Gtk.CellRendererText()
        col_drv.pack_start(cell_drv, True)
        col_drv.add_attribute(cell_drv, "text", 0)
        col_drv.set_min_width(180)
        self.temp_tree.append_column(col_drv)

        col_zone = Gtk.TreeViewColumn("Sensor Zone")
        cell_zone = Gtk.CellRendererText()
        col_zone.pack_start(cell_zone, True)
        col_zone.add_attribute(cell_zone, "text", 1)
        col_zone.set_expand(True)
        self.temp_tree.append_column(col_zone)

        col_temp = Gtk.TreeViewColumn("Temperature")
        cell_temp = Gtk.CellRendererText()
        cell_temp.set_property("xalign", 0.5)
        col_temp.pack_start(cell_temp, True)
        col_temp.add_attribute(cell_temp, "text", 3)
        col_temp.set_min_width(140)
        self.temp_tree.append_column(col_temp)

        temp_scroll = Gtk.ScrolledWindow()
        temp_scroll.set_min_content_height(240)
        temp_scroll.set_child(self.temp_tree)
        card_temp.append(temp_scroll)

        main_box.append(card_temp)
        return scroll

    def on_telemetry_tick(self):
        # 1. CPU
        cpu = self.telemetry_scanner.get_cpu_usage()
        self.cpu_bar.set_fraction(cpu / 100.0)
        self.lbl_cpu_val.set_label(f"{cpu:.1f}%")

        # 2. RAM
        used, tot, pct = self.telemetry_scanner.get_memory_usage()
        self.ram_bar.set_fraction(pct / 100.0)
        self.lbl_ram_val.set_label(f"{used:.1f} / {tot:.1f} GB ({pct}%)")

        # 3. Thermals
        sensors = self.telemetry_scanner.get_thermals()
        self.temp_store.clear()
        for s in sensors:
            t = s["temp"]
            badge_class = "temp-badge-normal"
            if t > 80:
                badge_class = "temp-badge-critical"
            elif t > 60:
                badge_class = "temp-badge-warning"

            self.temp_store.append([
                s["group"],
                s["label"],
                t,
                f"{t:.1f} °C",
                badge_class
            ])
        return True

    # ==========================
    # Tab 3: Storage & SMART Health View
    # ==========================
    def create_storage_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self.storage_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.storage_container.set_margin_start(16)
        self.storage_container.set_margin_end(16)
        self.storage_container.set_margin_top(16)
        self.storage_container.set_margin_bottom(16)
        scroll.set_child(self.storage_container)

        # Header Actions
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        lbl_hdr = Gtk.Label(
            label="Real-time disk storage utilization, partition mounts, and <b>S.M.A.R.T. hardware diagnostics</b> via <tt>smartctl</tt>.",
            use_markup=True,
            wrap=True,
            xalign=0
        )
        lbl_hdr.set_hexpand(True)
        lbl_hdr.add_css_class("card-subtitle")
        top_bar.append(lbl_hdr)

        btn_refresh_disks = Gtk.Button(label="Refresh Drives")
        btn_refresh_disks.connect("clicked", lambda b: self.refresh_disks())
        top_bar.append(btn_refresh_disks)

        btn_smart_scan = Gtk.Button(label="🛡️ Run SMART Scan (smartctl)")
        btn_smart_scan.add_css_class("suggested-action")
        btn_smart_scan.connect("clicked", lambda b: self.run_smartctl_scan())
        top_bar.append(btn_smart_scan)

        self.storage_container.append(top_bar)

        # Container for dynamic drive cards
        self.disks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.storage_container.append(self.disks_box)

        return scroll

    def refresh_disks(self):
        # Clear existing disk cards
        while child := self.disks_box.get_first_child():
            self.disks_box.remove(child)

        disks = DiskScanner.get_disks(self.smart_cache)
        if not disks:
            empty_lbl = Gtk.Label(label="No physical block devices detected.")
            empty_lbl.add_css_class("card-subtitle")
            self.disks_box.append(empty_lbl)
            return

        for d in disks:
            card = self._build_disk_card(d)
            self.disks_box.append(card)

    def _build_disk_card(self, d):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("card-box")

        # 1. Drive Top Row: Icon, Model, Interface, Size, Serial, Health Badge
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        icon_name = "drive-solidstate-symbolic" if "SSD" in d["model"] or "NVME" in d["tran"] else "drive-harddisk-symbolic"
        drive_icon = Gtk.Image.new_from_icon_name(icon_name)
        drive_icon.set_pixel_size(24)
        top_row.append(drive_icon)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_model = Gtk.Label(label=f"<b>{d['model']}</b> ({d['path']})", use_markup=True, xalign=0)
        lbl_model.add_css_class("card-title")
        title_box.append(lbl_model)

        lbl_sub = Gtk.Label(
            label=f"Capacity: <b>{d['size_gb']:.1f} GB</b> | Serial: <tt>{d['serial']}</tt> | Firmware: <tt>{d['firmware']}</tt>",
            use_markup=True,
            xalign=0
        )
        lbl_sub.add_css_class("card-subtitle")
        title_box.append(lbl_sub)
        top_row.append(title_box)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        top_row.append(spacer)

        # Transport Badge (NVMe / SATA / Swap)
        tran_class = "badge-nvme" if d["tran"] == "NVME" else "badge-sata"
        badge_tran = Gtk.Label(label=d["tran"])
        badge_tran.add_css_class(tran_class)
        top_row.append(badge_tran)

        # Health Badge
        health_status = d.get("health_status", "UNKNOWN")
        if health_status == "PASSED":
            badge_health = Gtk.Label(label="🟢 HEALTH: PASSED")
            badge_health.add_css_class("health-badge-passed")
        elif health_status == "WARNING":
            badge_health = Gtk.Label(label="🟡 HEALTH: WARNING")
            badge_health.add_css_class("health-badge-warning")
        elif health_status == "FAILING":
            badge_health = Gtk.Label(label="🔴 HEALTH: FAILING")
            badge_health.add_css_class("health-badge-failing")
        else:
            badge_health = Gtk.Label(label="⚪ SMART: UNCHECKED")
            badge_health.add_css_class("health-badge-unknown")
        top_row.append(badge_health)

        card.append(top_row)

        # 2. SMART Telemetry Metrics Tiles Grid
        grid_metrics = Gtk.Grid()
        grid_metrics.set_column_spacing(10)
        grid_metrics.set_row_spacing(10)
        grid_metrics.set_column_homogeneous(True)

        # Tile 1: Temperature
        temp_val_str = f"{d['temp_c']:.1f} °C" if d.get("temp_c") is not None else "-- °C"
        grid_metrics.attach(self._build_metric_tile("🌡️ Temperature", temp_val_str), 0, 0, 1, 1)

        # Tile 2: Health / Wear Level
        if d.get("wear_pct") is not None:
            health_pct = max(0, 100 - d["wear_pct"])
            wear_str = f"{health_pct}% ({d['wear_pct']}% Used)"
        else:
            wear_str = "Good (100%)" if d.get("health_passed") else "--"
        grid_metrics.attach(self._build_metric_tile("📊 Drive Health / Life", wear_str), 1, 0, 1, 1)

        # Tile 3: Power On Time
        if d.get("power_on_hours") is not None:
            hours = d["power_on_hours"]
            days = hours / 24.0
            poh_str = f"{hours:,} hrs ({days:.1f} days)"
        else:
            poh_str = "-- hrs"
        grid_metrics.attach(self._build_metric_tile("⏱️ Power-On Time", poh_str), 2, 0, 1, 1)

        # Tile 4: Total Data Written (TBW)
        if d.get("tbw_written") is not None:
            tbw_str = f"{d['tbw_written']:.2f} TB"
        else:
            tbw_str = "-- TB"
        grid_metrics.attach(self._build_metric_tile("✍️ Total Written (TBW)", tbw_str), 3, 0, 1, 1)

        # Tile 5: Total Read
        if d.get("tb_read") is not None:
            tbr_str = f"{d['tb_read']:.2f} TB"
        else:
            tbr_str = "-- TB"
        grid_metrics.attach(self._build_metric_tile("📖 Total Data Read", tbr_str), 4, 0, 1, 1)

        # Tile 6: Error Count / Reallocated Sectors
        err_str = "0 Errors"
        if d.get("media_errors") is not None and d["media_errors"] > 0:
            err_str = f"{d['media_errors']} Media Errors"
        elif d.get("reallocated_sectors") is not None:
            err_str = f"{d['reallocated_sectors']} Reallocated Sectors"
        grid_metrics.attach(self._build_metric_tile("⚠️ Bad Blocks / Errors", err_str), 5, 0, 1, 1)

        card.append(grid_metrics)

        # 3. Partitions & Filesystem Usage Rows
        parts = d.get("partitions", [])
        if parts:
            lbl_parts_title = Gtk.Label(label="<b>Mounted Partitions &amp; Filesystem Usage:</b>", use_markup=True, xalign=0)
            lbl_parts_title.add_css_class("stat-label")
            card.append(lbl_parts_title)

            for p in parts:
                part_row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                part_row.set_margin_start(4)
                part_row.set_margin_end(4)

                p_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                lbl_pname = Gtk.Label(label=f"<b>{p['name']}</b> ({p['mount']})", use_markup=True, xalign=0)
                lbl_pname.add_css_class("stat-label")
                p_top.append(lbl_pname)

                badge_fs = Gtk.Label(label=p["fstype"])
                badge_fs.add_css_class("badge-fs")
                p_top.append(badge_fs)

                p_spacer = Gtk.Box()
                p_spacer.set_hexpand(True)
                p_top.append(p_spacer)

                lbl_pstats = Gtk.Label(
                    label=f"<b>{p['used_gb']:.1f} GB</b> / {p['total_gb']:.1f} GB ({p['pct']:.1f}%) — Free: {p['free_gb']:.1f} GB",
                    use_markup=True,
                    xalign=1
                )
                lbl_pstats.add_css_class("stat-value")
                p_top.append(lbl_pstats)

                part_row.append(p_top)

                bar = Gtk.ProgressBar()
                bar.set_fraction(min(1.0, max(0.0, p["pct"] / 100.0)))
                part_row.append(bar)

                card.append(part_row)

        # 4. Raw SMART Attributes Expander (if available)
        attrs = d.get("attributes", [])
        if attrs:
            expander = Gtk.Expander(label="Detailed S.M.A.R.T. Attributes Table")
            exp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            exp_box.set_margin_top(8)

            store_attrs = Gtk.ListStore(int, str, int, int, int, str)
            for a in attrs:
                store_attrs.append([
                    a.get("id", 0),
                    a.get("name", ""),
                    a.get("value", 0),
                    a.get("worst", 0),
                    a.get("thresh", 0),
                    a.get("raw", "")
                ])

            tree_attrs = Gtk.TreeView(model=store_attrs)
            tree_attrs.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

            for idx, (col_name, width) in enumerate([("ID", 50), ("Attribute Name", 220), ("Current", 80), ("Worst", 80), ("Threshold", 90), ("Raw Value", 120)]):
                col = Gtk.TreeViewColumn(col_name)
                cell = Gtk.CellRendererText()
                col.pack_start(cell, True)
                col.add_attribute(cell, "text", idx)
                col.set_min_width(width)
                tree_attrs.append_column(col)

            exp_scroll = Gtk.ScrolledWindow()
            exp_scroll.set_min_content_height(180)
            exp_scroll.set_child(tree_attrs)
            exp_box.append(exp_scroll)

            expander.set_child(exp_box)
            card.append(expander)

        return card

    def _build_metric_tile(self, title, value):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("metric-tile")

        lbl_t = Gtk.Label(label=title, xalign=0)
        lbl_t.add_css_class("metric-tile-title")
        box.append(lbl_t)

        lbl_v = Gtk.Label(label=value, xalign=0)
        lbl_v.add_css_class("metric-tile-value")
        box.append(lbl_v)
        return box

    def run_smartctl_scan(self):
        disks = DiskScanner.get_disks(self.smart_cache)
        dev_paths = [d["path"] for d in disks if not d["path"].startswith("/dev/zram")]
        if not dev_paths:
            self.log_message("No physical storage devices to scan with smartctl.", "#ef4444")
            return

        dev_args = " ".join(dev_paths)
        scan_script = f"""python3 -c "
import json, subprocess, sys
res = {{}}
for dev in sys.argv[1:]:
    try:
        out = subprocess.run(['smartctl', '-a', '-j', dev], capture_output=True, text=True).stdout
        res[dev] = json.loads(out)
    except Exception as e:
        res[dev] = {{'error': str(e)}}
print(json.dumps(res))
" {dev_args}"""

        self.log_message(f"Initiating privileged SMART scan for {dev_args} via smartctl...")

        def on_scan_done(output_json_str):
            try:
                data = json.loads(output_json_str)
                self.smart_cache.update(data)
                self.refresh_disks()
                self.rescan_hardware()
                self.log_message("SMART diagnostics data successfully updated for all drives!", "#10b981")
            except Exception as e:
                self.log_message(f"Failed to parse smartctl diagnostic JSON: {e}", "#ef4444")

        self.execute_privileged_with_stdout(
            "Execute SMART diagnostics via smartctl",
            scan_script,
            on_success_with_output=on_scan_done
        )

    # ==========================
    # Tab 4: Cooling & ICE View
    # ==========================
    def create_cooling_tab(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        scroll.set_child(main_box)

        # Card 1: Intelligent Cooling Engine (ICE)
        card_ice = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_ice.add_css_class("card-box")

        lbl_ice_title = Gtk.Label(label="Intelligent Cooling Engine (ICE) — Active Fan Profile", xalign=0)
        lbl_ice_title.add_css_class("card-title")
        card_ice.append(lbl_ice_title)

        lbl_ice_desc = Gtk.Label(
            label="Lenovo ICE controls hardware fan curves at the BIOS/SMM firmware layer. Select a preset below to stage changes via <tt>think-lmi</tt>:",
            use_markup=True,
            xalign=0,
            wrap=True
        )
        lbl_ice_desc.add_css_class("card-subtitle")
        card_ice.append(lbl_ice_desc)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        btn_box.set_homogeneous(True)

        btn_acoustic = Gtk.Button(label="🍃 Acoustic Mode (Quiet)")
        btn_acoustic.add_css_class("btn-acoustic")
        btn_acoustic.connect("clicked", lambda b: self.set_ice_mode("Better Acoustic Performance", "Acoustic (Quiet)"))
        btn_box.append(btn_acoustic)

        btn_thermal = Gtk.Button(label="💨 Thermal Mode (Cooler)")
        btn_thermal.add_css_class("btn-thermal")
        btn_thermal.connect("clicked", lambda b: self.set_ice_mode("Better Thermal Performance", "Thermal (Performance)"))
        btn_box.append(btn_thermal)

        btn_full = Gtk.Button(label="🚀 Full Speed (100% Fan)")
        btn_full.add_css_class("btn-fullspeed")
        btn_full.connect("clicked", lambda b: self.set_ice_mode("Full Speed", "Full Speed (100% Fan)"))
        btn_box.append(btn_full)

        card_ice.append(btn_box)
        main_box.append(card_ice)

        # Card 2: ThinkLMI BIOS Firmware Attributes
        card_lmi = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        card_lmi.add_css_class("card-box")

        lbl_lmi_title = Gtk.Label(label="Lenovo Firmware Attributes Management (ThinkLMI)", xalign=0)
        lbl_lmi_title.add_css_class("card-title")
        card_lmi.append(lbl_lmi_title)

        grid_lmi = Gtk.Grid()
        grid_lmi.set_column_spacing(16)
        grid_lmi.set_row_spacing(14)

        # Row 1: ICE Thermal Alert
        lbl_a1 = Gtk.Label(label="ICE Thermal Alert (Hardware Overheat Alarm):", xalign=0)
        lbl_a1.add_css_class("stat-label")
        grid_lmi.attach(lbl_a1, 0, 0, 1, 1)

        btn_a1_on = Gtk.Button(label="Enable")
        btn_a1_on.add_css_class("suggested-action")
        btn_a1_on.connect("clicked", lambda b: self.set_firmware_attr("ICE Thermal Alert", "Enabled"))
        grid_lmi.attach(btn_a1_on, 1, 0, 1, 1)

        btn_a1_off = Gtk.Button(label="Disable")
        btn_a1_off.connect("clicked", lambda b: self.set_firmware_attr("ICE Thermal Alert", "Disabled"))
        grid_lmi.attach(btn_a1_off, 2, 0, 1, 1)

        # Row 2: Enhanced Power Saving Mode (ErP)
        lbl_a2 = Gtk.Label(label="Enhanced Power Saving Mode (ErP Standby Cut):", xalign=0)
        lbl_a2.add_css_class("stat-label")
        grid_lmi.attach(lbl_a2, 0, 1, 1, 1)

        btn_a2_on = Gtk.Button(label="Enable")
        btn_a2_on.add_css_class("suggested-action")
        btn_a2_on.connect("clicked", lambda b: self.set_firmware_attr("Enhanced Power Saving Mode", "Enabled"))
        grid_lmi.attach(btn_a2_on, 1, 1, 1, 1)

        btn_a2_off = Gtk.Button(label="Disable")
        btn_a2_off.connect("clicked", lambda b: self.set_firmware_attr("Enhanced Power Saving Mode", "Disabled"))
        grid_lmi.attach(btn_a2_off, 2, 1, 1, 1)

        # Row 3: Smart Power On
        lbl_a3 = Gtk.Label(label="Smart Power On (Alt + P Wake from S5):", xalign=0)
        lbl_a3.add_css_class("stat-label")
        grid_lmi.attach(lbl_a3, 0, 2, 1, 1)

        btn_a3_on = Gtk.Button(label="Enable")
        btn_a3_on.add_css_class("suggested-action")
        btn_a3_on.connect("clicked", lambda b: self.set_firmware_attr("Smart Power On", "Enabled"))
        grid_lmi.attach(btn_a3_on, 1, 2, 1, 1)

        btn_a3_off = Gtk.Button(label="Disable")
        btn_a3_off.connect("clicked", lambda b: self.set_firmware_attr("Smart Power On", "Disabled"))
        grid_lmi.attach(btn_a3_off, 2, 2, 1, 1)

        card_lmi.append(grid_lmi)
        main_box.append(card_lmi)
        return scroll

    def set_ice_mode(self, mode_val, mode_name):
        cmd = f"echo '{mode_val}' > '/sys/class/firmware-attributes/thinklmi/attributes/ICE Performance Modes/current_value'"
        self.execute_privileged(f"Set Fan Profile to {mode_name}", cmd)

    def set_firmware_attr(self, attr_name, val):
        cmd = f"echo '{val}' > '/sys/class/firmware-attributes/thinklmi/attributes/{attr_name}/current_value'"
        self.execute_privileged(f"Set {attr_name} to {val}", cmd)

    # ==========================
    # Tab 5: ACPI Sleep & Wakeup
    # ==========================
    def create_wakeup_tab(self):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        container.set_margin_start(16)
        container.set_margin_end(16)
        container.set_margin_top(14)
        container.set_margin_bottom(10)

        # Top banner & buttons
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        lbl_desc = Gtk.Label(
            label="Control which PCI and USB controllers are permitted to wake the machine from Suspend-to-RAM (S3). "
                  "Disabling <b>XHC</b> stops accidental mouse nudges from waking the PC.",
            use_markup=True,
            wrap=True,
            xalign=0
        )
        lbl_desc.set_hexpand(True)
        lbl_desc.add_css_class("card-subtitle")
        top_bar.append(lbl_desc)

        btn_refresh = Gtk.Button(label="Refresh List")
        btn_refresh.connect("clicked", lambda b: self.refresh_wakeup())
        top_bar.append(btn_refresh)

        btn_quick_usb = Gtk.Button(label="Quick Toggle USB (XHC)")
        btn_quick_usb.add_css_class("btn-purple")
        btn_quick_usb.connect("clicked", lambda b: self.toggle_wakeup_device("XHC"))
        top_bar.append(btn_quick_usb)

        container.append(top_bar)

        # Wakeup Table
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self.wakeup_store = Gtk.ListStore(str, str, str, str, str, str)
        self.wakeup_tree = Gtk.TreeView(model=self.wakeup_store)
        self.wakeup_tree.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

        col_node = Gtk.TreeViewColumn("ACPI Node")
        cell_node = Gtk.CellRendererText()
        cell_node.set_property("weight", Pango.Weight.BOLD)
        col_node.pack_start(cell_node, True)
        col_node.add_attribute(cell_node, "text", 0)
        col_node.set_min_width(110)
        self.wakeup_tree.append_column(col_node)

        col_state = Gtk.TreeViewColumn("Sleep State")
        cell_state = Gtk.CellRendererText()
        col_state.pack_start(cell_state, True)
        col_state.add_attribute(cell_state, "text", 1)
        col_state.set_min_width(100)
        self.wakeup_tree.append_column(col_state)

        col_status = Gtk.TreeViewColumn("Status")
        cell_status = Gtk.CellRendererText()
        col_status.pack_start(cell_status, True)
        col_status.add_attribute(cell_status, "text", 2)
        col_status.set_min_width(110)
        self.wakeup_tree.append_column(col_status)

        col_desc = Gtk.TreeViewColumn("Description")
        cell_desc = Gtk.CellRendererText()
        col_desc.pack_start(cell_desc, True)
        col_desc.add_attribute(cell_desc, "text", 3)
        col_desc.set_expand(True)
        self.wakeup_tree.append_column(col_desc)

        col_act = Gtk.TreeViewColumn("Action (Toggle)")
        cell_act = Gtk.CellRendererText()
        cell_act.set_property("font", "Cantarell 9.5")
        cell_act.set_property("weight", Pango.Weight.BOLD)
        cell_act.set_property("foreground", "#60a5fa")
        col_act.pack_start(cell_act, True)
        col_act.add_attribute(cell_act, "text", 4)
        col_act.set_min_width(110)
        self.wakeup_tree.append_column(col_act)

        self.wakeup_tree.connect("row-activated", self.on_wakeup_row_activated)

        scroll.set_child(self.wakeup_tree)
        container.append(scroll)
        return container

    def refresh_wakeup(self):
        devices = WakeupScanner.get_devices()
        self.wakeup_store.clear()
        for d in devices:
            status_text = "ENABLED" if d["enabled"] else "DISABLED"
            action_text = "[Click to Disable]" if d["enabled"] else "[Click to Enable]"
            self.wakeup_store.append([
                d["node"],
                d["state"],
                status_text,
                d["desc"],
                action_text,
                d["node"]
            ])

    def on_wakeup_row_activated(self, tree, path, column):
        it = self.wakeup_store.get_iter(path)
        if it:
            node = self.wakeup_store.get_value(it, 5)
            self.toggle_wakeup_device(node)

    def toggle_wakeup_device(self, dev_node):
        cmd = f"echo '{dev_node}' > /proc/acpi/wakeup"
        self.execute_privileged(f"Toggle ACPI Wakeup State for {dev_node}", cmd, on_success=lambda: GLib.timeout_add(700, self.refresh_wakeup))

    # ==========================
    # Console Log & Privileged Execution
    # ==========================
    def log_message(self, text, color=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] $ {text}\n"
        end_iter = self.console_buffer.get_end_iter()
        self.console_buffer.insert(end_iter, formatted)
        mark = self.console_buffer.create_mark(None, self.console_buffer.get_end_iter(), False)
        self.console_view.scroll_mark_onscreen(mark)

    def execute_privileged(self, action_desc, bash_cmd, on_success=None):
        self.execute_privileged_with_stdout(action_desc, bash_cmd, on_success_with_output=lambda out: on_success() if on_success else None)

    def execute_privileged_with_stdout(self, action_desc, bash_cmd, on_success_with_output=None):
        if self.active_process is not None:
            self.log_message("Another command is currently executing. Please wait...", "#ef4444")
            return

        self.log_message(f"Invoking privileged operation: {action_desc}...")

        def worker():
            try:
                proc = subprocess.Popen(
                    ["pkexec", "sh", "-c", bash_cmd],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.active_process = proc
                stdout, stderr = proc.communicate()
                exit_code = proc.returncode

                def on_done():
                    self.active_process = None
                    if stdout and stdout.strip():
                        # If stdout is massive JSON, truncate console display
                        display_out = stdout.strip() if len(stdout.strip()) < 300 else f"{stdout.strip()[:200]}... [JSON data received]"
                        self.log_message(display_out)
                    if stderr and stderr.strip():
                        self.log_message(f"STDERR: {stderr.strip()}", "#ef4444")
                    
                    if exit_code == 0:
                        self.log_message("Privileged command completed successfully!", "#10b981")
                        if on_success_with_output:
                            on_success_with_output(stdout)
                    else:
                        self.log_message(f"Execution finished with code {exit_code}. (Authorization dismissed or rejected)", "#ef4444")

                GLib.idle_add(on_done)
            except Exception as e:
                def on_err():
                    self.active_process = None
                    self.log_message(f"Execution error: {e}", "#ef4444")
                GLib.idle_add(on_err)

        t = threading.Thread(target=worker, daemon=True)
        t.start()


class ThinkControlCenterApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.lenovo.thinkcontrolcenter",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        style_mgr = Adw.StyleManager.get_default()
        style_mgr.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

        display = Gdk.Display.get_default()
        if display:
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS_DATA.encode("utf-8"))
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        self.win = ThinkControlCenterWindow(self)
        self.win.present()


def main():
    app = ThinkControlCenterApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
