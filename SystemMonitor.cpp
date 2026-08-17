#include "SystemMonitor.h"
#include <QDir>
#include <QFile>
#include <QTextStream>
#include <QStringList>

SystemMonitor::SystemMonitor() {}

QVector<ThermalSensor> SystemMonitor::getThermalSensors() {
    QVector<ThermalSensor> sensors;
    QDir hwmonDir("/sys/class/hwmon");
    if (!hwmonDir.exists()) return sensors;

    QStringList entries = hwmonDir.entryList(QStringList() << "hwmon*", QDir::Dirs | QDir::NoDotAndDotDot);
    for (const QString& hwmonName : entries) {
        QString hwmonPath = "/sys/class/hwmon/" + hwmonName;
        QString groupName = "Unknown";

        // Read sensor chip name
        QFile nameFile(hwmonPath + "/name");
        if (nameFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
            groupName = QString::fromUtf8(nameFile.readAll()).trimmed();
            nameFile.close();
        }

        // Find all temp*_input files
        QDir singleHwmon(hwmonPath);
        QStringList tempInputs = singleHwmon.entryList(QStringList() << "temp*_input", QDir::Files);
        for (const QString& inputFile : tempInputs) {
            QString prefix = inputFile.section('_', 0, 0); // e.g. "temp1"
            QString label = prefix;

            // Check if label file exists (e.g. temp1_label)
            QFile labelFile(hwmonPath + "/" + prefix + "_label");
            if (labelFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
                label = QString::fromUtf8(labelFile.readAll()).trimmed();
                labelFile.close();
            }

            // Read temp value
            QFile valFile(hwmonPath + "/" + inputFile);
            if (valFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
                bool ok = false;
                long long milliDeg = QString::fromUtf8(valFile.readAll()).trimmed().toLongLong(&ok);
                valFile.close();
                if (ok && milliDeg > -50000 && milliDeg < 150000) {
                    ThermalSensor sensor;
                    sensor.sensorGroup = groupName;
                    sensor.label = label;
                    sensor.temperature = milliDeg / 1000.0;
                    sensors.append(sensor);
                }
            }
        }
    }
    return sensors;
}

double SystemMonitor::getCpuUsage() {
    QFile file("/proc/stat");
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return 0.0;

    QTextStream stream(&file);
    QString line = stream.readLine();
    file.close();

    if (!line.startsWith("cpu ")) return 0.0;

    QStringList parts = line.split(' ', Qt::SkipEmptyParts);
    if (parts.size() < 9) return 0.0;

    unsigned long long user = parts[1].toULongLong();
    unsigned long long nice = parts[2].toULongLong();
    unsigned long long system = parts[3].toULongLong();
    unsigned long long idle = parts[4].toULongLong();
    unsigned long long iowait = parts[5].toULongLong();
    unsigned long long irq = parts[6].toULongLong();
    unsigned long long softirq = parts[7].toULongLong();
    unsigned long long steal = parts[8].toULongLong();

    if (!hasPreviousCpuSample) {
        prevUser = user; prevNice = nice; prevSystem = system; prevIdle = idle;
        prevIowait = iowait; prevIrq = irq; prevSoftirq = softirq; prevSteal = steal;
        hasPreviousCpuSample = true;
        return 0.0;
    }

    unsigned long long prevNonIdle = prevUser + prevNice + prevSystem + prevIrq + prevSoftirq + prevSteal;
    unsigned long long nonIdle = user + nice + system + irq + softirq + steal;

    unsigned long long prevTotal = prevNonIdle + prevIdle + prevIowait;
    unsigned long long total = nonIdle + idle + iowait;

    unsigned long long totald = total - prevTotal;
    unsigned long long idled = (idle + iowait) - (prevIdle + prevIowait);

    prevUser = user; prevNice = nice; prevSystem = system; prevIdle = idle;
    prevIowait = iowait; prevIrq = irq; prevSoftirq = softirq; prevSteal = steal;

    if (totald == 0) return 0.0;

    double cpuPercent = (double)(totald - idled) / (double)totald * 100.0;
    return qBound(0.0, cpuPercent, 100.0);
}

MemoryStats SystemMonitor::getMemoryUsage() {
    MemoryStats stats = {0.0, 0.0, 0.0, 0};
    QFile file("/proc/meminfo");
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return stats;

    QTextStream stream(&file);
    unsigned long long totalKb = 0;
    unsigned long long availKb = 0;

    while (!stream.atEnd()) {
        QString line = stream.readLine();
        if (line.startsWith("MemTotal:")) {
            QStringList parts = line.split(' ', Qt::SkipEmptyParts);
            if (parts.size() >= 2) totalKb = parts[1].toULongLong();
        } else if (line.startsWith("MemAvailable:")) {
            QStringList parts = line.split(' ', Qt::SkipEmptyParts);
            if (parts.size() >= 2) availKb = parts[1].toULongLong();
        }
    }
    file.close();

    if (totalKb > 0) {
        unsigned long long usedKb = totalKb - availKb;
        stats.totalGb = totalKb / (1024.0 * 1024.0);
        stats.usedGb = usedKb / (1024.0 * 1024.0);
        stats.freeGb = availKb / (1024.0 * 1024.0);
        stats.percentage = (int)((double)usedKb / (double)totalKb * 100.0);
    }
    return stats;
}
