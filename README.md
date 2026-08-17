# ThinkControlCenter

**ThinkControlCenter** is a native Linux management hub and graphical control center designed for Lenovo Think-series hardware (ThinkCentre Tiny, ThinkPad, and ThinkStation). It provides direct control over Lenovo's **Intelligent Cooling Engine (ICE)**, BIOS firmware attributes via `think-lmi`, ACPI S3 sleep wakeup triggers, and real-time hardware telemetry.

---

## 1. Key Features & Capabilities

* **Intelligent Cooling Engine (ICE):** Configure high-level BIOS cooling profiles (`Better Acoustic Performance`, `Better Thermal Performance`, and `Full Speed 100%`) without rebooting into UEFI setup.
* **Firmware Attributes Management (`think-lmi`):** Directly query and modify Lenovo BIOS settings from Linux (Thermal Alerts, ErP Power Saving, Smart Power On, Wake on LAN).
* **Live Hardware Telemetry:** Real-time monitoring of CPU usage, RAM utilization, and temperatures for CPU cores, NVMe SSD, and Wi-Fi modules via `/sys/class/hwmon`.
* **ACPI Sleep & Wakeup Control:** Manage Suspend-to-RAM (S3) wake triggers in `/proc/acpi/wakeup` (such as disabling `XHC` to prevent accidental mouse/keyboard movement from waking the system).
* **Motherboard Topology Viewer:** Inspect host bridges, LPC controllers, PCIe devices, USB hubs, and connected displays with real-time filtering and search.

---

## 2. Firmware Control Interface (ThinkLMI)

Lenovo exposes BIOS/UEFI settings to the Linux kernel via WMI (`think-lmi` driver). These can be queried and modified at runtime via the `sysfs` firmware-attributes class.

### Location of Attributes
```bash
/sys/class/firmware-attributes/thinklmi/attributes/
```

### Key Cooling & Power Settings
| Attribute | Active Value | Possible Values | Description |
| :--- | :--- | :--- | :--- |
| `ICE Performance Modes` | `Better Acoustic Performance` | `Better Acoustic Performance`<br>`Better Thermal Performance`<br>`Full Speed` | Dictates the active fan speed curve preset. |
| `ICE Thermal Alert` | `Enabled` | `Enabled`<br>`Disabled` | System alarm on critical temperatures. |
| `Enhanced Power Saving Mode` | *(Configurable)* | `Enabled`<br>`Disabled` | ErP mode: cuts standby power, disables USB/LAN wakeups. |
| `Smart Power On` | *(Configurable)* | `Enabled`<br>`Disabled` | Allows powering on from G3/S5 by pressing `Alt + P` on a USB keyboard. |
| `C State Support` | *(Configurable)* | `C1`, `C1C3`, `C1C3C6`, `C1C3C6C7`, `C1C3C6C7C8` | CPU idle power states. |
| `Wake on LAN` | *(Configurable)* | `Primary`<br>`Automatic`<br>`Disabled` | Enables waking up the PC via network commands. |

### CLI Management Commands

* **Query all attributes:**
  ```bash
  for attr in "ICE Performance Modes" "ICE Thermal Alert" "Enhanced Power Saving Mode" "C State Support" "Smart Power On" "Wake on LAN" "Wake Up on Alarm" "After Power Loss"; do
    echo -n "$attr: "
    sudo cat "/sys/class/firmware-attributes/thinklmi/attributes/$attr/current_value"
  done
  ```

* **Switch cooling to "Better Thermal Performance" (cooler CPU, earlier fan ramp):**
  ```bash
  echo "Better Thermal Performance" | sudo tee "/sys/class/firmware-attributes/thinklmi/attributes/ICE Performance Modes/current_value"
  ```

* **Force maximum fan speed (100% duty cycle):**
  ```bash
  echo "Full Speed" | sudo tee "/sys/class/firmware-attributes/thinklmi/attributes/ICE Performance Modes/current_value"
  ```

* **Return to default quiet mode:**
  ```bash
  echo "Better Acoustic Performance" | sudo tee "/sys/class/firmware-attributes/thinklmi/attributes/ICE Performance Modes/current_value"
  ```

---

## 3. OS-Level Sleep & Wake Configuration

### Sleep States
* **File:** `/sys/power/mem_sleep`
* **Configuration:** `s2idle [deep]`
* **Behavior:** Traditional S3 Suspend-to-RAM (`deep`) powers down the CPU and PCIe devices while maintaining memory context.

### ACPI Wakeup Triggers
* **File:** `/proc/acpi/wakeup`
* **Common Triggers:**
  * `GLAN` (Intel Gigabit Ethernet): Wake-on-LAN.
  * `XHC` (USB 3.0 Host Controller): USB keyboard/mouse events.
* **Toggle USB Wakeup via CLI:**
  ```bash
  echo "XHC" | sudo tee /proc/acpi/wakeup
  ```

---

## 4. ACPI DSDT Firmware Analysis

Decompiling the system DSDT (Differentiated System Description Table) reveals the lower-level implementation details of Lenovo's cooling engine.

### A. WMI Setup Mapping Package
The BIOS defines a named array (`ITEM`) exposing settings to WMI. The mapping block for cooling settings:

```asl
Package (0x03)
{
    0x1B,                    // Option Index (27 in decimal)
    "ICE Performance Modes", // Display Name
    0x47                     // WMI ID (71 in decimal)
}
```

### B. Value Translation Package (`VSEL`)
The configuration index `0x1B` maps to the 27th index of `VSEL`:

```asl
Package (0x03)
{
    "Better Acoustic Performance", // Value Index 0
    "Better Thermal Performance",  // Value Index 1
    "Full Speed"                   // Value Index 2
}
```

### C. System Management Interrupt (SMI) Execution
When modifying attributes from Linux, the ACPI driver invokes the `SMI` method, writing to port `APMC = 0x2F` to trigger **System Management Mode (SMM)**:

```asl
Method (SMI, 5, NotSerialized)
{
    Acquire (MSMI, 0xFFFF)
    CMD = Arg0
    PAR0 = Arg1
    PAR1 = Arg2
    PAR2 = Arg3
    PAR3 = Arg4
    APMC = 0x2F             // Transition CPU to System Management Mode (SMM)
    While ((ERR == One))
    {
        Sleep (0x64)
        APMC = 0x2F
    }

    Local0 = PAR0 
    Release (MSMI)
    Return (Local0)
}
```

### D. Fan Controller Hardware Ports
The Nuvoton NCT6683D eSIO chip registers are declared in the DSDT address spaces:
```asl
NCTC,   8,  // Nuvoton Control Register
NCTI,   8,  // Nuvoton Index Register
NCTH,   8,  // Nuvoton Data Register
```
All closed-loop fan RPM calculations and thermal triggers are handled by the controller firmware and BIOS SMM handler.

---

## 5. Hardware & Kernel Compatibility

* **Kernel Driver:** The `think-lmi` driver was merged into mainline Linux in version **5.17** (`drivers/platform/x86/think-lmi.c`).
* **Intel Core Ultra (Meteor Lake) & Modern Platforms:** Newer Lenovo ThinkPad and ThinkCentre models utilize an expanded WMI payload format. Support for this schema is available in **Linux Kernel 6.8 or newer**.
* **Intelligent Cooling vs Dynamic Profiles:**
  * `think-lmi` manages static, persistent BIOS thermal policies and firmware attributes.
  * Laptops with active dynamic profiles utilize `/sys/firmware/acpi/platform_profile` (handled by `power-profiles-daemon`).
  * Direct fan tachometer overrides on supported mobile platforms utilize `thinkpad_acpi`.

---

## 6. Building & Running

### Dependencies
* Qt 5 (Widgets, Core)
* CMake (3.10+) or qmake
* `pciutils`, `usbutils`, `iproute2` (for hardware discovery)

### Build with CMake
```bash
cmake -B build -S .
cmake --build build
./build/ThinkArchitectureViewer
```

### Build with qmake
```bash
qmake ThinkControlCenter.pro
make
./ThinkControlCenter
```
