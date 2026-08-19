#include "WakeupManager.h"
#include <QFile>
#include <QTextStream>
#include <QStringList>

QVector<WakeupDevice> WakeupManager::getWakeupDevices() {
    QVector<WakeupDevice> list;
    QFile file("/proc/acpi/wakeup");
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return list;

    QTextStream stream(&file);
    bool firstLine = true;
    while (!stream.atEnd()) {
        QString line = stream.readLine();
        if (firstLine) {
            firstLine = false;
            continue; // Skip header
        }

        QStringList parts = line.split(QRegExp("\\s+"), Qt::SkipEmptyParts);
        if (parts.size() >= 3) {
            WakeupDevice dev;
            dev.device = parts[0];
            dev.sleepState = parts[1];
            dev.enabled = parts[2].contains("enabled");
            if (parts.size() >= 4) {
                dev.sysfsNode = parts[3];
            }

            if (dev.device == "XHC") dev.description = "USB 3.0 Host Controller (Keyboard/Mouse wake)";
            else if (dev.device == "GLAN") dev.description = "Intel Gigabit LAN (Wake-on-LAN)";
            else if (dev.device == "RP06" || dev.device == "PXSX") dev.description = "PCIe WLAN / Peripheral";
            else if (dev.device == "HDAS") dev.description = "Intel HD Audio";
            else if (dev.device == "PS2K") dev.description = "PS/2 Keyboard";
            else if (dev.device == "PS2M") dev.description = "PS/2 Mouse";
            else if (dev.device.startsWith("RP")) dev.description = "PCIe Root Port";
            else if (dev.device.startsWith("PEG")) dev.description = "PCI Express Graphics";
            else dev.description = "ACPI Wakeup Source";

            list.append(dev);
        }
    }
    file.close();
    return list;
}

QString WakeupManager::getToggleCommand(const QString& device) {
    return QString("echo '%1' > /proc/acpi/wakeup").arg(device);
}
