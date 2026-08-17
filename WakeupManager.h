#ifndef WAKEUPMANAGER_H
#define WAKEUPMANAGER_H

#include <QString>
#include <QVector>

struct WakeupDevice {
    QString device;
    QString sleepState;
    bool enabled;
    QString sysfsNode;
    QString description;
};

class WakeupManager {
public:
    static QVector<WakeupDevice> getWakeupDevices();
    static QString getToggleCommand(const QString& device);
};

#endif // WAKEUPMANAGER_H
