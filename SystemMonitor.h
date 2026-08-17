#ifndef SYSTEMMONITOR_H
#define SYSTEMMONITOR_H

#include <QString>
#include <QVector>

struct ThermalSensor {
    QString sensorGroup; // e.g. "coretemp", "nvme", "iwlwifi"
    QString label;       // e.g. "Package id 0", "Core 0", "Composite"
    double temperature;  // e.g. 48.5
};

struct MemoryStats {
    double totalGb;
    double usedGb;
    double freeGb;
    int percentage;
};

class SystemMonitor {
public:
    SystemMonitor();
    
    QVector<ThermalSensor> getThermalSensors();
    double getCpuUsage();
    MemoryStats getMemoryUsage();

private:
    unsigned long long prevUser = 0;
    unsigned long long prevNice = 0;
    unsigned long long prevSystem = 0;
    unsigned long long prevIdle = 0;
    unsigned long long prevIowait = 0;
    unsigned long long prevIrq = 0;
    unsigned long long prevSoftirq = 0;
    unsigned long long prevSteal = 0;
    bool hasPreviousCpuSample = false;
};

#endif // SYSTEMMONITOR_H
