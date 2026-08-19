"""Application constants, sysfs paths, and UI configuration values."""

# ---------------------------------------------------------------------------
# Window geometry
# ---------------------------------------------------------------------------
WINDOW_DEFAULT_WIDTH: int = 1180
WINDOW_DEFAULT_HEIGHT: int = 800

# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------
TELEMETRY_POLL_INTERVAL_MS: int = 1500
PANED_DEFAULT_POSITION: int = 540
CONSOLE_MIN_HEIGHT: int = 140

# ---------------------------------------------------------------------------
# Temperature thresholds (°C)
# ---------------------------------------------------------------------------
TEMP_WARNING_THRESHOLD: float = 60.0
TEMP_CRITICAL_THRESHOLD: float = 80.0

# ---------------------------------------------------------------------------
# Sysfs / procfs paths
# ---------------------------------------------------------------------------
THINKLMI_ATTR_BASE: str = "/sys/class/firmware-attributes/thinklmi/attributes"
PROC_ACPI_WAKEUP: str = "/proc/acpi/wakeup"
PROC_STAT: str = "/proc/stat"
PROC_MEMINFO: str = "/proc/meminfo"
PROC_INPUT_DEVICES: str = "/proc/bus/input/devices"
SYS_DRM_BASE: str = "/sys/class/drm"
SYS_HWMON_BASE: str = "/sys/class/hwmon"

# ---------------------------------------------------------------------------
# ACPI wakeup node descriptions
# ---------------------------------------------------------------------------
WAKEUP_NODE_DESCRIPTIONS: dict[str, str] = {
    "XHC": "USB 3.0 Host Controller (Keyboard / Mouse wake)",
    "GLAN": "Intel Gigabit LAN (Wake-on-LAN)",
    "RP06": "PCIe WLAN / Peripheral",
    "PXSX": "PCIe WLAN / Peripheral",
    "HDAS": "Intel HD Audio",
    "PS2K": "PS/2 Keyboard",
    "PS2M": "PS/2 Mouse",
}

# ---------------------------------------------------------------------------
# System button / control input device name fragments
# ---------------------------------------------------------------------------
SYSTEM_INPUT_KEYWORDS: list[str] = [
    "Power Button", "Sleep Button", "Video Bus",
    "PC Speaker", "Mic", "Headphone", "HDMI",
]

# ---------------------------------------------------------------------------
# SMART attribute names for wear / lifetime
# ---------------------------------------------------------------------------
WEAR_LEVEL_ATTRS: set[str] = {
    "Wear_Leveling_Count", "SSD_Life_Left", "Media_Wearout_Indicator",
    "Percent_Lifetime_Remain", "Remaining_Lifetime_Perc",
}
WEAR_LEVEL_IDS: set[int] = {177, 231, 232, 169, 202}

WRITE_TOTAL_ATTRS: set[str] = {
    "Total_LBAs_Written", "Host_Writes_32MiB", "Host_Writes_GiB", "Data_Units_Written",
}
READ_TOTAL_ATTRS: set[str] = {
    "Total_LBAs_Read", "Host_Reads_32MiB", "Host_Reads_GiB",
}

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_ID: str = "org.lenovo.thinkcontrolcenter"
APP_TITLE: str = "ThinkControlCenter — Lenovo Power & Firmware Hub"
