"""Main application window — UI layout, tab construction, and event handling."""

from __future__ import annotations

import json
import logging
import subprocess
import threading
from collections.abc import Callable
from datetime import datetime
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk, Pango

from thinkcontrolcenter.config import (
    CONSOLE_MIN_HEIGHT,
    PANED_DEFAULT_POSITION,
    TELEMETRY_POLL_INTERVAL_MS,
    TEMP_CRITICAL_THRESHOLD,
    TEMP_WARNING_THRESHOLD,
    THINKLMI_ATTR_BASE,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
)
from thinkcontrolcenter.scanners.disk import DiskScanner
from thinkcontrolcenter.scanners.hardware import HardwareScanner
from thinkcontrolcenter.scanners.telemetry import TelemetryScanner
from thinkcontrolcenter.scanners.wakeup import WakeupScanner

logger = logging.getLogger(__name__)


class ThinkControlCenterWindow(Adw.ApplicationWindow):
    """Primary window containing all five application tabs and a console log."""

    def __init__(self, app: Adw.Application) -> None:
        super().__init__(
            application=app,
            title="ThinkControlCenter — Lenovo Power & Firmware Hub",
        )
        self.set_default_size(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        self._telemetry = TelemetryScanner()
        self._active_process: subprocess.Popen | None = None
        self._smart_cache: dict[str, Any] = {}

        self._build_ui()

        # Start telemetry polling
        GLib.timeout_add(TELEMETRY_POLL_INTERVAL_MS, self._on_telemetry_tick)
        self._on_telemetry_tick()

        # Initial scans
        self._rescan_hardware()
        self._refresh_wakeup()
        self._refresh_disks()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Assemble the top-level layout: header bar, view stack, and console."""
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(root_box)

        # Header bar with view switcher
        header = Adw.HeaderBar()
        self._view_switcher = Adw.ViewSwitcher()
        self._view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(self._view_switcher)
        root_box.append(header)

        # Vertical paned: top views + bottom console
        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        paned.set_vexpand(True)
        paned.set_hexpand(True)
        paned.set_position(PANED_DEFAULT_POSITION)
        root_box.append(paned)

        # View stack
        self._view_stack = Adw.ViewStack()
        self._view_switcher.set_stack(self._view_stack)

        self._view_stack.add_titled_with_icon(
            self._build_arch_tab(), "arch", "Architecture", "network-workgroup-symbolic",
        )
        self._view_stack.add_titled_with_icon(
            self._build_telemetry_tab(), "telemetry", "Telemetry",
            "utilities-system-monitor-symbolic",
        )
        self._view_stack.add_titled_with_icon(
            self._build_storage_tab(), "storage", "Storage & SMART",
            "drive-harddisk-symbolic",
        )
        self._view_stack.add_titled_with_icon(
            self._build_cooling_tab(), "cooling", "Cooling & ICE",
            "weather-snow-symbolic",
        )
        self._view_stack.add_titled_with_icon(
            self._build_wakeup_tab(), "wakeup", "ACPI Wakeup",
            "system-shutdown-symbolic",
        )
        paned.set_start_child(self._view_stack)

        # Console log
        paned.set_end_child(self._build_console())

        self._log("ThinkControlCenter started. Hardware, storage & WMI interfaces initialized.", "#60a5fa")

    # ------------------------------------------------------------------
    # Console log
    # ------------------------------------------------------------------

    def _build_console(self) -> Gtk.Box:
        """Create the bottom console log panel."""
        console_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        console_box.set_margin_start(12)
        console_box.set_margin_end(12)
        console_box.set_margin_bottom(10)
        console_box.set_margin_top(4)

        console_hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(
            label="<b>System Console &amp; Privilege Execution Log</b>",
            use_markup=True,
        )
        lbl.add_css_class("card-subtitle")
        lbl.set_xalign(0)
        console_hdr.append(lbl)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        console_hdr.append(spacer)

        btn_clear = Gtk.Button(label="Clear Console")
        btn_clear.connect("clicked", lambda _: self._console_buffer.set_text(""))
        console_hdr.append(btn_clear)
        console_box.append(console_hdr)

        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(CONSOLE_MIN_HEIGHT)
        self._console_view = Gtk.TextView()
        self._console_view.set_editable(False)
        self._console_view.set_cursor_visible(False)
        self._console_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._console_view.add_css_class("console-view")
        self._console_buffer = self._console_view.get_buffer()
        scroll.set_child(self._console_view)
        console_box.append(scroll)

        return console_box

    def _log(self, text: str, color: str | None = None) -> None:
        """Append a timestamped message to the console buffer."""
        timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] $ {text}\n"
        end_iter = self._console_buffer.get_end_iter()
        self._console_buffer.insert(end_iter, formatted)
        mark = self._console_buffer.create_mark(None, self._console_buffer.get_end_iter(), False)
        self._console_view.scroll_mark_onscreen(mark)

    # ------------------------------------------------------------------
    # Tab 1: Architecture View
    # ------------------------------------------------------------------

    def _build_arch_tab(self) -> Gtk.Box:
        """Build the hardware architecture tree-view tab."""
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        container.set_margin_start(16)
        container.set_margin_end(16)
        container.set_margin_top(14)
        container.set_margin_bottom(10)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text(
            "Search hardware (e.g. NVMe, Intel, USB, Audio, PCI, Display, SATA)...",
        )
        self._search_entry.set_hexpand(True)
        self._search_entry.connect("search-changed", self._on_search_changed)
        toolbar.append(self._search_entry)

        btn_rescan = Gtk.Button(label="Rescan Hardware")
        btn_rescan.add_css_class("suggested-action")
        btn_rescan.connect("clicked", lambda _: self._rescan_hardware())
        toolbar.append(btn_rescan)

        btn_expand = Gtk.Button(label="Expand All")
        btn_expand.connect("clicked", lambda _: self._arch_treeview.expand_all())
        toolbar.append(btn_expand)

        btn_collapse = Gtk.Button(label="Collapse")
        btn_collapse.connect("clicked", lambda _: self._arch_treeview.collapse_all())
        toolbar.append(btn_collapse)

        container.append(toolbar)

        # TreeView with filter
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self._tree_store = Gtk.TreeStore(str, str, bool)
        self._tree_filter = self._tree_store.filter_new()
        self._tree_filter.set_visible_column(2)

        self._arch_treeview = Gtk.TreeView(model=self._tree_filter)
        self._arch_treeview.set_headers_visible(False)
        self._arch_treeview.set_enable_search(False)

        col = Gtk.TreeViewColumn("Hardware")
        cell = Gtk.CellRendererText()
        cell.set_property("font", "Cantarell 10")
        col.pack_start(cell, True)
        col.add_attribute(cell, "text", 0)
        self._arch_treeview.append_column(col)

        scroll.set_child(self._arch_treeview)
        container.append(scroll)
        return container

    def _rescan_hardware(self) -> None:
        """Populate the architecture tree with fresh scan results."""
        self._log("Scanning system topology, PCI bridges, DRM displays and USB devices...")
        self._tree_store.clear()

        sections = [
            ("<b>Motherboard & Chipsets</b>", "motherboard chipsets pci", HardwareScanner.get_pci_tree),
            ("<b>Displays & Monitors</b>", "displays monitors screen drm dp hdmi", HardwareScanner.get_display_tree),
            ("<b>Input Devices (Keyboard / Mouse)</b>", "input keyboard mouse button", HardwareScanner.get_input_tree),
            ("<b>USB Controllers & Devices</b>", "usb hub controller", HardwareScanner.get_usb_tree),
            ("<b>Network Interfaces</b>", "network ethernet wifi wlan lan", HardwareScanner.get_network_tree),
        ]
        for title, search_text, scanner_fn in sections:
            root = self._tree_store.append(None, [title, search_text, True])
            for item in scanner_fn():
                self._add_tree_node(root, item)

        # Storage section
        storage_root = self._tree_store.append(
            None, ["<b>Storage & Block Devices</b>", "storage nvme disk ssd sata samsung", True],
        )
        for disk in DiskScanner.get_disks(self._smart_cache):
            node = {
                "title": f"Disk: {disk['model']} ({disk['path']}, {disk['size_gb']:.1f} GB, {disk['tran']})",
                "children": [
                    {"title": f"Serial Number: {disk['serial']}", "children": []},
                    {"title": f"Firmware Revision: {disk['firmware']}", "children": []},
                ],
            }
            if disk.get("temp_c") is not None:
                node["children"].append({"title": f"Temperature: {disk['temp_c']:.1f} °C", "children": []})
            for part in disk.get("partitions", []):
                desc = (
                    f"Partition: {part['name']} ({part['mount']}) — "
                    f"{part['fstype']}, {part['used_gb']:.1f} / {part['total_gb']:.1f} GB ({part['pct']:.1f}%)"
                )
                node["children"].append({"title": desc, "children": []})
            self._add_tree_node(storage_root, node)

        self._arch_treeview.expand_all()
        self._log("System architecture scan complete.", "#10b981")

    def _add_tree_node(self, parent_iter: Gtk.TreeIter, node: dict[str, Any]) -> None:
        """Recursively insert a tree-node dict into the TreeStore."""
        title = node.get("title", "")
        it = self._tree_store.append(parent_iter, [title, title.lower(), True])
        for child in node.get("children", []):
            self._add_tree_node(it, child)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        """Filter the architecture tree based on the search query."""
        query = entry.get_text().strip().lower()
        if not query:
            self._tree_store.foreach(lambda _model, _path, it: (
                self._tree_store.set_value(it, 2, True), False,
            )[-1])
            return

        def traverse(it: Gtk.TreeIter) -> None:
            child_it = self._tree_store.iter_children(it)
            any_child_visible = False
            while child_it:
                traverse(child_it)
                if self._tree_store.get_value(child_it, 2):
                    any_child_visible = True
                child_it = self._tree_store.iter_next(child_it)

            txt = self._tree_store.get_value(it, 1) or ""
            self._tree_store.set_value(it, 2, query in txt or any_child_visible)

        top_it = self._tree_store.get_iter_first()
        while top_it:
            traverse(top_it)
            top_it = self._tree_store.iter_next(top_it)

        self._arch_treeview.expand_all()

    # ------------------------------------------------------------------
    # Tab 2: Telemetry & Sensors
    # ------------------------------------------------------------------

    def _build_telemetry_tab(self) -> Gtk.ScrolledWindow:
        """Build the real-time CPU / RAM / temperature tab."""
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        scroll.set_child(main_box)

        # Card: System Utilization
        card_util = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_util.add_css_class("card-box")

        lbl_title = Gtk.Label(label="System Utilization", xalign=0)
        lbl_title.add_css_class("card-title")
        card_util.append(lbl_title)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(12)

        # CPU row
        lbl_cpu = Gtk.Label(label="CPU Load:", xalign=0)
        lbl_cpu.add_css_class("stat-label")
        grid.attach(lbl_cpu, 0, 0, 1, 1)

        self._cpu_bar = Gtk.ProgressBar()
        self._cpu_bar.set_hexpand(True)
        self._cpu_bar.set_show_text(False)
        grid.attach(self._cpu_bar, 1, 0, 1, 1)

        self._lbl_cpu_val = Gtk.Label(label="0.0%", xalign=1)
        self._lbl_cpu_val.add_css_class("stat-value")
        self._lbl_cpu_val.set_size_request(80, -1)
        grid.attach(self._lbl_cpu_val, 2, 0, 1, 1)

        # RAM row
        lbl_ram = Gtk.Label(label="RAM Usage:", xalign=0)
        lbl_ram.add_css_class("stat-label")
        grid.attach(lbl_ram, 0, 1, 1, 1)

        self._ram_bar = Gtk.ProgressBar()
        self._ram_bar.set_hexpand(True)
        self._ram_bar.set_show_text(False)
        grid.attach(self._ram_bar, 1, 1, 1, 1)

        self._lbl_ram_val = Gtk.Label(label="0 / 0 GB", xalign=1)
        self._lbl_ram_val.add_css_class("stat-value")
        self._lbl_ram_val.set_size_request(160, -1)
        grid.attach(self._lbl_ram_val, 2, 1, 1, 1)

        card_util.append(grid)
        main_box.append(card_util)

        # Card: Temperature sensors
        card_temp = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card_temp.add_css_class("card-box")

        lbl_temp_title = Gtk.Label(label="Hardware Temperature Sensors (/sys/class/hwmon)", xalign=0)
        lbl_temp_title.add_css_class("card-title")
        card_temp.append(lbl_temp_title)

        self._temp_store = Gtk.ListStore(str, str, float, str, str)
        self._temp_tree = Gtk.TreeView(model=self._temp_store)
        self._temp_tree.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

        col_drv = Gtk.TreeViewColumn("Device / Driver")
        cell_drv = Gtk.CellRendererText()
        col_drv.pack_start(cell_drv, True)
        col_drv.add_attribute(cell_drv, "text", 0)
        col_drv.set_min_width(180)
        self._temp_tree.append_column(col_drv)

        col_zone = Gtk.TreeViewColumn("Sensor Zone")
        cell_zone = Gtk.CellRendererText()
        col_zone.pack_start(cell_zone, True)
        col_zone.add_attribute(cell_zone, "text", 1)
        col_zone.set_expand(True)
        self._temp_tree.append_column(col_zone)

        col_temp = Gtk.TreeViewColumn("Temperature")
        cell_temp = Gtk.CellRendererText()
        cell_temp.set_property("xalign", 0.5)
        col_temp.pack_start(cell_temp, True)
        col_temp.add_attribute(cell_temp, "text", 3)
        col_temp.set_min_width(140)
        self._temp_tree.append_column(col_temp)

        temp_scroll = Gtk.ScrolledWindow()
        temp_scroll.set_min_content_height(240)
        temp_scroll.set_child(self._temp_tree)
        card_temp.append(temp_scroll)

        main_box.append(card_temp)
        return scroll

    def _on_telemetry_tick(self) -> bool:
        """Periodic callback to update CPU, RAM, and thermal readings."""
        cpu = self._telemetry.get_cpu_usage()
        self._cpu_bar.set_fraction(cpu / 100.0)
        self._lbl_cpu_val.set_label(f"{cpu:.1f}%")

        used, tot, pct = self._telemetry.get_memory_usage()
        self._ram_bar.set_fraction(pct / 100.0)
        self._lbl_ram_val.set_label(f"{used:.1f} / {tot:.1f} GB ({pct}%)")

        sensors = self._telemetry.get_thermals()
        self._temp_store.clear()
        for sensor in sensors:
            temp = sensor["temp"]
            if temp > TEMP_CRITICAL_THRESHOLD:
                badge = "temp-badge-critical"
            elif temp > TEMP_WARNING_THRESHOLD:
                badge = "temp-badge-warning"
            else:
                badge = "temp-badge-normal"
            self._temp_store.append([
                sensor["group"], sensor["label"], temp, f"{temp:.1f} °C", badge,
            ])
        return True  # keep the timer running

    # ------------------------------------------------------------------
    # Tab 3: Storage & SMART Health
    # ------------------------------------------------------------------

    def _build_storage_tab(self) -> Gtk.ScrolledWindow:
        """Build the disk storage and S.M.A.R.T. diagnostics tab."""
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self._storage_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self._storage_container.set_margin_start(16)
        self._storage_container.set_margin_end(16)
        self._storage_container.set_margin_top(16)
        self._storage_container.set_margin_bottom(16)
        scroll.set_child(self._storage_container)

        # Header actions
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        lbl = Gtk.Label(
            label=(
                "Real-time disk storage utilization, partition mounts, and "
                "<b>S.M.A.R.T. hardware diagnostics</b> via <tt>smartctl</tt>."
            ),
            use_markup=True, wrap=True, xalign=0,
        )
        lbl.set_hexpand(True)
        lbl.add_css_class("card-subtitle")
        top_bar.append(lbl)

        btn_refresh = Gtk.Button(label="Refresh Drives")
        btn_refresh.connect("clicked", lambda _: self._refresh_disks())
        top_bar.append(btn_refresh)

        btn_smart = Gtk.Button(label="🛡️ Run SMART Scan (smartctl)")
        btn_smart.add_css_class("suggested-action")
        btn_smart.connect("clicked", lambda _: self._run_smartctl_scan())
        top_bar.append(btn_smart)

        self._storage_container.append(top_bar)

        self._disks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self._storage_container.append(self._disks_box)

        return scroll

    def _refresh_disks(self) -> None:
        """Re-render all disk cards."""
        while child := self._disks_box.get_first_child():
            self._disks_box.remove(child)

        disks = DiskScanner.get_disks(self._smart_cache)
        if not disks:
            lbl = Gtk.Label(label="No physical block devices detected.")
            lbl.add_css_class("card-subtitle")
            self._disks_box.append(lbl)
            return

        for disk in disks:
            self._disks_box.append(self._build_disk_card(disk))

    def _build_disk_card(self, disk: dict[str, Any]) -> Gtk.Box:
        """Build a single disk information card widget."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("card-box")

        # Top row: icon, model, badges
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        icon_name = (
            "drive-solidstate-symbolic"
            if "SSD" in disk["model"] or "NVME" in disk["tran"]
            else "drive-harddisk-symbolic"
        )
        drive_icon = Gtk.Image.new_from_icon_name(icon_name)
        drive_icon.set_pixel_size(24)
        top_row.append(drive_icon)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_model = Gtk.Label(
            label=f"<b>{disk['model']}</b> ({disk['path']})",
            use_markup=True, xalign=0,
        )
        lbl_model.add_css_class("card-title")
        title_box.append(lbl_model)

        lbl_sub = Gtk.Label(
            label=(
                f"Capacity: <b>{disk['size_gb']:.1f} GB</b> | "
                f"Serial: <tt>{disk['serial']}</tt> | "
                f"Firmware: <tt>{disk['firmware']}</tt>"
            ),
            use_markup=True, xalign=0,
        )
        lbl_sub.add_css_class("card-subtitle")
        title_box.append(lbl_sub)
        top_row.append(title_box)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        top_row.append(spacer)

        # Transport badge
        tran_class = "badge-nvme" if disk["tran"] == "NVME" else "badge-sata"
        badge_tran = Gtk.Label(label=disk["tran"])
        badge_tran.add_css_class(tran_class)
        top_row.append(badge_tran)

        # Health badge
        top_row.append(self._build_health_badge(disk.get("health_status", "UNKNOWN")))
        card.append(top_row)

        # Metrics grid
        card.append(self._build_metrics_grid(disk))

        # Partitions
        self._append_partition_rows(card, disk.get("partitions", []))

        # Raw SMART attributes expander
        self._append_smart_expander(card, disk.get("attributes", []))

        return card

    @staticmethod
    def _build_health_badge(status: str) -> Gtk.Label:
        """Create a health status badge label."""
        badges = {
            "PASSED": ("🟢 HEALTH: PASSED", "health-badge-passed"),
            "WARNING": ("🟡 HEALTH: WARNING", "health-badge-warning"),
            "FAILING": ("🔴 HEALTH: FAILING", "health-badge-failing"),
        }
        text, css = badges.get(status, ("⚪ SMART: UNCHECKED", "health-badge-unknown"))
        label = Gtk.Label(label=text)
        label.add_css_class(css)
        return label

    @staticmethod
    def _build_metrics_grid(disk: dict[str, Any]) -> Gtk.Grid:
        """Build the SMART telemetry metrics tile grid."""
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)

        def _tile(title: str, value: str) -> Gtk.Box:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.add_css_class("metric-tile")
            lbl_t = Gtk.Label(label=title, xalign=0)
            lbl_t.add_css_class("metric-tile-title")
            box.append(lbl_t)
            lbl_v = Gtk.Label(label=value, xalign=0)
            lbl_v.add_css_class("metric-tile-value")
            box.append(lbl_v)
            return box

        temp_str = f"{disk['temp_c']:.1f} °C" if disk.get("temp_c") is not None else "-- °C"
        grid.attach(_tile("🌡️ Temperature", temp_str), 0, 0, 1, 1)

        if disk.get("wear_pct") is not None:
            health_pct = max(0, 100 - disk["wear_pct"])
            wear_str = f"{health_pct}% ({disk['wear_pct']}% Used)"
        else:
            wear_str = "Good (100%)" if disk.get("health_passed") else "--"
        grid.attach(_tile("📊 Drive Health / Life", wear_str), 1, 0, 1, 1)

        if disk.get("power_on_hours") is not None:
            hours = disk["power_on_hours"]
            poh_str = f"{hours:,} hrs ({hours / 24.0:.1f} days)"
        else:
            poh_str = "-- hrs"
        grid.attach(_tile("⏱️ Power-On Time", poh_str), 2, 0, 1, 1)

        tbw_str = f"{disk['tbw_written']:.2f} TB" if disk.get("tbw_written") is not None else "-- TB"
        grid.attach(_tile("✍️ Total Written (TBW)", tbw_str), 3, 0, 1, 1)

        tbr_str = f"{disk['tb_read']:.2f} TB" if disk.get("tb_read") is not None else "-- TB"
        grid.attach(_tile("📖 Total Data Read", tbr_str), 4, 0, 1, 1)

        err_str = "0 Errors"
        if disk.get("media_errors") is not None and disk["media_errors"] > 0:
            err_str = f"{disk['media_errors']} Media Errors"
        elif disk.get("reallocated_sectors") is not None:
            err_str = f"{disk['reallocated_sectors']} Reallocated Sectors"
        grid.attach(_tile("⚠️ Bad Blocks / Errors", err_str), 5, 0, 1, 1)

        return grid

    @staticmethod
    def _append_partition_rows(card: Gtk.Box, partitions: list[dict[str, Any]]) -> None:
        """Append partition usage rows and progress bars to a disk card."""
        if not partitions:
            return

        lbl = Gtk.Label(
            label="<b>Mounted Partitions &amp; Filesystem Usage:</b>",
            use_markup=True, xalign=0,
        )
        lbl.add_css_class("stat-label")
        card.append(lbl)

        for part in partitions:
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            row.set_margin_start(4)
            row.set_margin_end(4)

            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl_name = Gtk.Label(
                label=f"<b>{part['name']}</b> ({part['mount']})",
                use_markup=True, xalign=0,
            )
            lbl_name.add_css_class("stat-label")
            top.append(lbl_name)

            badge_fs = Gtk.Label(label=part["fstype"])
            badge_fs.add_css_class("badge-fs")
            top.append(badge_fs)

            spacer = Gtk.Box()
            spacer.set_hexpand(True)
            top.append(spacer)

            lbl_stats = Gtk.Label(
                label=(
                    f"<b>{part['used_gb']:.1f} GB</b> / {part['total_gb']:.1f} GB "
                    f"({part['pct']:.1f}%) — Free: {part['free_gb']:.1f} GB"
                ),
                use_markup=True, xalign=1,
            )
            lbl_stats.add_css_class("stat-value")
            top.append(lbl_stats)

            row.append(top)

            bar = Gtk.ProgressBar()
            bar.set_fraction(min(1.0, max(0.0, part["pct"] / 100.0)))
            row.append(bar)

            card.append(row)

    @staticmethod
    def _append_smart_expander(card: Gtk.Box, attributes: list[dict[str, Any]]) -> None:
        """Append a collapsible SMART attributes table to a disk card."""
        if not attributes:
            return

        expander = Gtk.Expander(label="Detailed S.M.A.R.T. Attributes Table")
        exp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        exp_box.set_margin_top(8)

        store = Gtk.ListStore(int, str, int, int, int, str)
        for attr in attributes:
            store.append([
                attr.get("id", 0),
                attr.get("name", ""),
                attr.get("value", 0),
                attr.get("worst", 0),
                attr.get("thresh", 0),
                attr.get("raw", ""),
            ])

        tree = Gtk.TreeView(model=store)
        tree.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

        columns = [
            ("ID", 50), ("Attribute Name", 220), ("Current", 80),
            ("Worst", 80), ("Threshold", 90), ("Raw Value", 120),
        ]
        for idx, (col_name, width) in enumerate(columns):
            col = Gtk.TreeViewColumn(col_name)
            cell = Gtk.CellRendererText()
            col.pack_start(cell, True)
            col.add_attribute(cell, "text", idx)
            col.set_min_width(width)
            tree.append_column(col)

        exp_scroll = Gtk.ScrolledWindow()
        exp_scroll.set_min_content_height(180)
        exp_scroll.set_child(tree)
        exp_box.append(exp_scroll)

        expander.set_child(exp_box)
        card.append(expander)

    def _run_smartctl_scan(self) -> None:
        """Launch a privileged smartctl scan across all physical drives."""
        disks = DiskScanner.get_disks(self._smart_cache)
        dev_paths = [d["path"] for d in disks if not d["path"].startswith("/dev/zram")]
        if not dev_paths:
            self._log("No physical storage devices to scan with smartctl.", "#ef4444")
            return

        dev_args = " ".join(dev_paths)
        scan_script = (
            f'python3 -c "\n'
            "import json, subprocess, sys\n"
            "res = {}\n"
            "for dev in sys.argv[1:]:\n"
            "    try:\n"
            "        out = subprocess.run(['smartctl', '-a', '-j', dev], capture_output=True, text=True).stdout\n"
            "        res[dev] = json.loads(out)\n"
            "    except Exception as e:\n"
            "        res[dev] = {'error': str(e)}\n"
            'print(json.dumps(res))\n'
            f'" {dev_args}'
        )

        self._log(f"Initiating privileged SMART scan for {dev_args} via smartctl...")

        def on_done(output: str) -> None:
            try:
                data = json.loads(output)
                self._smart_cache.update(data)
                self._refresh_disks()
                self._rescan_hardware()
                self._log("SMART diagnostics data successfully updated for all drives!", "#10b981")
            except json.JSONDecodeError as exc:
                self._log(f"Failed to parse smartctl diagnostic JSON: {exc}", "#ef4444")

        self._execute_privileged_with_stdout(
            "Execute SMART diagnostics via smartctl", scan_script, on_done,
        )

    # ------------------------------------------------------------------
    # Tab 4: Cooling & ICE
    # ------------------------------------------------------------------

    def _build_cooling_tab(self) -> Gtk.ScrolledWindow:
        """Build the Intelligent Cooling Engine control tab."""
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        scroll.set_child(main_box)

        # Card: ICE fan profile
        card_ice = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card_ice.add_css_class("card-box")

        lbl_title = Gtk.Label(label="Intelligent Cooling Engine (ICE) — Active Fan Profile", xalign=0)
        lbl_title.add_css_class("card-title")
        card_ice.append(lbl_title)

        lbl_desc = Gtk.Label(
            label=(
                "Lenovo ICE controls hardware fan curves at the BIOS/SMM firmware layer. "
                "Select a preset below to stage changes via <tt>think-lmi</tt>:"
            ),
            use_markup=True, xalign=0, wrap=True,
        )
        lbl_desc.add_css_class("card-subtitle")
        card_ice.append(lbl_desc)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        btn_box.set_homogeneous(True)

        ice_modes = [
            ("🍃 Acoustic Mode (Quiet)", "btn-acoustic", "Better Acoustic Performance", "Acoustic (Quiet)"),
            ("💨 Thermal Mode (Cooler)", "btn-thermal", "Better Thermal Performance", "Thermal (Performance)"),
            ("🚀 Full Speed (100% Fan)", "btn-fullspeed", "Full Speed", "Full Speed (100% Fan)"),
        ]
        for label, css, mode_val, mode_name in ice_modes:
            btn = Gtk.Button(label=label)
            btn.add_css_class(css)
            btn.connect("clicked", lambda _, v=mode_val, n=mode_name: self._set_ice_mode(v, n))
            btn_box.append(btn)

        card_ice.append(btn_box)
        main_box.append(card_ice)

        # Card: ThinkLMI firmware attributes
        card_lmi = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        card_lmi.add_css_class("card-box")

        lbl_lmi = Gtk.Label(label="Lenovo Firmware Attributes Management (ThinkLMI)", xalign=0)
        lbl_lmi.add_css_class("card-title")
        card_lmi.append(lbl_lmi)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(14)

        firmware_attrs = [
            ("ICE Thermal Alert (Hardware Overheat Alarm):", "ICE Thermal Alert"),
            ("Enhanced Power Saving Mode (ErP Standby Cut):", "Enhanced Power Saving Mode"),
            ("Smart Power On (Alt + P Wake from S5):", "Smart Power On"),
        ]
        for row_idx, (label_text, attr_name) in enumerate(firmware_attrs):
            lbl = Gtk.Label(label=label_text, xalign=0)
            lbl.add_css_class("stat-label")
            grid.attach(lbl, 0, row_idx, 1, 1)

            btn_on = Gtk.Button(label="Enable")
            btn_on.add_css_class("suggested-action")
            btn_on.connect("clicked", lambda _, a=attr_name: self._set_firmware_attr(a, "Enabled"))
            grid.attach(btn_on, 1, row_idx, 1, 1)

            btn_off = Gtk.Button(label="Disable")
            btn_off.connect("clicked", lambda _, a=attr_name: self._set_firmware_attr(a, "Disabled"))
            grid.attach(btn_off, 2, row_idx, 1, 1)

        card_lmi.append(grid)
        main_box.append(card_lmi)
        return scroll

    def _set_ice_mode(self, mode_val: str, mode_name: str) -> None:
        """Write a cooling profile to ThinkLMI."""
        cmd = f"echo '{mode_val}' > '{THINKLMI_ATTR_BASE}/ICE Performance Modes/current_value'"
        self._execute_privileged(f"Set Fan Profile to {mode_name}", cmd)

    def _set_firmware_attr(self, attr_name: str, value: str) -> None:
        """Write a firmware attribute value to ThinkLMI."""
        cmd = f"echo '{value}' > '{THINKLMI_ATTR_BASE}/{attr_name}/current_value'"
        self._execute_privileged(f"Set {attr_name} to {value}", cmd)

    # ------------------------------------------------------------------
    # Tab 5: ACPI Sleep & Wakeup
    # ------------------------------------------------------------------

    def _build_wakeup_tab(self) -> Gtk.Box:
        """Build the ACPI wakeup trigger management tab."""
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        container.set_margin_start(16)
        container.set_margin_end(16)
        container.set_margin_top(14)
        container.set_margin_bottom(10)

        # Top bar
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        lbl = Gtk.Label(
            label=(
                "Control which PCI and USB controllers are permitted to wake the machine "
                "from Suspend-to-RAM (S3). Disabling <b>XHC</b> stops accidental mouse "
                "nudges from waking the PC."
            ),
            use_markup=True, wrap=True, xalign=0,
        )
        lbl.set_hexpand(True)
        lbl.add_css_class("card-subtitle")
        top_bar.append(lbl)

        btn_refresh = Gtk.Button(label="Refresh List")
        btn_refresh.connect("clicked", lambda _: self._refresh_wakeup())
        top_bar.append(btn_refresh)

        btn_usb = Gtk.Button(label="Quick Toggle USB (XHC)")
        btn_usb.add_css_class("btn-purple")
        btn_usb.connect("clicked", lambda _: self._toggle_wakeup("XHC"))
        top_bar.append(btn_usb)

        container.append(top_bar)

        # Wakeup table
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self._wakeup_store = Gtk.ListStore(str, str, str, str, str, str)
        self._wakeup_tree = Gtk.TreeView(model=self._wakeup_store)
        self._wakeup_tree.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

        wakeup_cols = [
            ("ACPI Node", 110, {"weight": Pango.Weight.BOLD}),
            ("Sleep State", 100, {}),
            ("Status", 110, {}),
            ("Description", -1, {}),  # -1 = expand
            ("Action (Toggle)", 110, {
                "font": "Cantarell 9.5",
                "weight": Pango.Weight.BOLD,
                "foreground": "#60a5fa",
            }),
        ]
        for idx, (col_name, width, cell_props) in enumerate(wakeup_cols):
            col = Gtk.TreeViewColumn(col_name)
            cell = Gtk.CellRendererText()
            for prop, val in cell_props.items():
                cell.set_property(prop, val)
            col.pack_start(cell, True)
            col.add_attribute(cell, "text", idx)
            if width > 0:
                col.set_min_width(width)
            else:
                col.set_expand(True)
            self._wakeup_tree.append_column(col)

        self._wakeup_tree.connect("row-activated", self._on_wakeup_row_activated)

        scroll.set_child(self._wakeup_tree)
        container.append(scroll)
        return container

    def _refresh_wakeup(self) -> None:
        """Reload the ACPI wakeup device table."""
        devices = WakeupScanner.get_devices()
        self._wakeup_store.clear()
        for dev in devices:
            status = "ENABLED" if dev["enabled"] else "DISABLED"
            action = "[Click to Disable]" if dev["enabled"] else "[Click to Enable]"
            self._wakeup_store.append([
                dev["node"], dev["state"], status, dev["desc"], action, dev["node"],
            ])

    def _on_wakeup_row_activated(
        self,
        tree: Gtk.TreeView,
        path: Gtk.TreePath,
        column: Gtk.TreeViewColumn,
    ) -> None:
        """Handle a double-click on a wakeup table row."""
        it = self._wakeup_store.get_iter(path)
        if it:
            node = self._wakeup_store.get_value(it, 5)
            self._toggle_wakeup(node)

    def _toggle_wakeup(self, dev_node: str) -> None:
        """Toggle an ACPI wakeup source via privileged write."""
        cmd = f"echo '{dev_node}' > /proc/acpi/wakeup"
        self._execute_privileged(
            f"Toggle ACPI Wakeup State for {dev_node}", cmd,
            on_success=lambda: GLib.timeout_add(700, self._refresh_wakeup),
        )

    # ------------------------------------------------------------------
    # Privileged execution helpers
    # ------------------------------------------------------------------

    def _execute_privileged(
        self,
        action_desc: str,
        bash_cmd: str,
        on_success: Callable[[], None] | None = None,
    ) -> None:
        """Execute a privileged bash command, ignoring stdout."""
        self._execute_privileged_with_stdout(
            action_desc, bash_cmd,
            on_success_with_output=lambda _out: on_success() if on_success else None,
        )

    def _execute_privileged_with_stdout(
        self,
        action_desc: str,
        bash_cmd: str,
        on_success_with_output: Callable[[str], None] | None = None,
    ) -> None:
        """Execute a privileged bash command via ``pkexec``, capturing stdout."""
        if self._active_process is not None:
            self._log("Another command is currently executing. Please wait...", "#ef4444")
            return

        self._log(f"Invoking privileged operation: {action_desc}...")

        def worker() -> None:
            try:
                proc = subprocess.Popen(
                    ["pkexec", "sh", "-c", bash_cmd],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self._active_process = proc
                stdout, stderr = proc.communicate()
                exit_code = proc.returncode

                def on_done() -> None:
                    self._active_process = None
                    if stdout and stdout.strip():
                        display = (
                            stdout.strip()
                            if len(stdout.strip()) < 300
                            else f"{stdout.strip()[:200]}... [JSON data received]"
                        )
                        self._log(display)
                    if stderr and stderr.strip():
                        self._log(f"STDERR: {stderr.strip()}", "#ef4444")

                    if exit_code == 0:
                        self._log("Privileged command completed successfully!", "#10b981")
                        if on_success_with_output:
                            on_success_with_output(stdout)
                    else:
                        self._log(
                            f"Execution finished with code {exit_code}. "
                            "(Authorization dismissed or rejected)",
                            "#ef4444",
                        )

                GLib.idle_add(on_done)
            except (OSError, subprocess.SubprocessError) as exc:
                def on_err(err: str = str(exc)) -> None:
                    self._active_process = None
                    self._log(f"Execution error: {err}", "#ef4444")
                GLib.idle_add(on_err)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
