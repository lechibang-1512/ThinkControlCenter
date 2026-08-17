#include "HardwareDiscovery.h"
#include <QProcess>
#include <QStringList>
#include <QDir>
#include <QFile>
#include <QMap>

void HardwareDiscovery::parsePci(QTreeWidgetItem* parentNode) {
    QProcess p;
    p.start("lspci", QStringList() << "-nn");
    p.waitForFinished();
    
    QString output = p.readAllStandardOutput();
    QStringList lines = output.split('\n', Qt::SkipEmptyParts);
    
    QTreeWidgetItem* rootHost = nullptr;
    QTreeWidgetItem* pchNode = nullptr;

    for (const QString& line : lines) {
        if (line.contains("Host bridge")) {
            rootHost = new QTreeWidgetItem(parentNode);
            rootHost->setText(0, "CPU / Host Bridge");
            QTreeWidgetItem* detail = new QTreeWidgetItem(rootHost);
            detail->setText(0, line.trimmed());
        } 
        else if (line.contains("ISA bridge") || line.contains("LPC Controller")) {
            if (!rootHost) {
                rootHost = new QTreeWidgetItem(parentNode);
                rootHost->setText(0, "System Bus");
            }
            pchNode = new QTreeWidgetItem(rootHost);
            pchNode->setText(0, "PCH (Platform Controller Hub)");
            QTreeWidgetItem* lpc = new QTreeWidgetItem(pchNode);
            lpc->setText(0, "LPC Bus -> Nuvoton NCT6683D Embedded Controller");
            QTreeWidgetItem* detail = new QTreeWidgetItem(lpc);
            detail->setText(0, line.trimmed());
        }
        else if (line.contains("SMBus")) {
            if (pchNode) {
                QTreeWidgetItem* smbus = new QTreeWidgetItem(pchNode);
                smbus->setText(0, "SMBus Controller");
                QTreeWidgetItem* detail = new QTreeWidgetItem(smbus);
                detail->setText(0, line.trimmed());
            }
        }
        else {
            QTreeWidgetItem* item = new QTreeWidgetItem(parentNode);
            item->setText(0, line.trimmed());
        }
    }
}

void HardwareDiscovery::parseUsb(QTreeWidgetItem* parentNode) {
    QProcess p;
    p.start("lsusb", QStringList());
    p.waitForFinished();
    
    QString output = p.readAllStandardOutput();
    QStringList lines = output.split('\n', Qt::SkipEmptyParts);
    
    QMap<QString, QTreeWidgetItem*> hubs;

    for (const QString& line : lines) {
        QString busMatch = line.mid(4, 3);
        
        QTreeWidgetItem* hubNode = nullptr;
        if (hubs.contains(busMatch)) {
            hubNode = hubs[busMatch];
        } else {
            hubNode = new QTreeWidgetItem(parentNode);
            hubNode->setText(0, QString("USB Bus %1").arg(busMatch));
            hubs.insert(busMatch, hubNode);
        }

        QTreeWidgetItem* deviceNode = new QTreeWidgetItem(hubNode);
        deviceNode->setText(0, line.trimmed());
    }
}

void HardwareDiscovery::parseNetwork(QTreeWidgetItem* parentNode) {
    QProcess p;
    p.start("ip", QStringList() << "-br" << "link");
    p.waitForFinished();
    
    QString output = p.readAllStandardOutput();
    QStringList lines = output.split('\n', Qt::SkipEmptyParts);

    for (const QString& line : lines) {
        QStringList parts = line.split(' ', Qt::SkipEmptyParts);
        if (parts.size() >= 3) {
            QString name = parts[0];
            QString status = parts[1];
            QString mac = parts[2];
            
            QTreeWidgetItem* ifaceNode = new QTreeWidgetItem(parentNode);
            ifaceNode->setText(0, QString("%1 (%2)").arg(name, status));
            
            QTreeWidgetItem* detailStatus = new QTreeWidgetItem(ifaceNode);
            detailStatus->setText(0, QString("State: %1").arg(status));
            
            QTreeWidgetItem* detailMac = new QTreeWidgetItem(ifaceNode);
            detailMac->setText(0, QString("MAC: %1").arg(mac));
        }
    }
}

void HardwareDiscovery::parseDisplays(QTreeWidgetItem* parentNode) {
    QDir drmDir("/sys/class/drm");
    if (!drmDir.exists()) {
        QTreeWidgetItem* errNode = new QTreeWidgetItem(parentNode);
        errNode->setText(0, "DRM subsystem not found");
        return;
    }
    
    QStringList connectors = drmDir.entryList(QStringList() << "card*-*", QDir::Dirs | QDir::NoDotAndDotDot | QDir::System);
    
    QTreeWidgetItem* activeNode = new QTreeWidgetItem(parentNode);
    activeNode->setText(0, "Active Displays");
    
    QTreeWidgetItem* inactiveNode = new QTreeWidgetItem(parentNode);
    inactiveNode->setText(0, "Inactive Ports");
    
    int activeCount = 0;
    int inactiveCount = 0;
    
    for (const QString& conn : connectors) {
        QString path = "/sys/class/drm/" + conn;
        QFile statusFile(path + "/status");
        if (statusFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
            QString status = statusFile.readAll().trimmed();
            statusFile.close();
            
            QString displayId = conn;
            if (conn.startsWith("card")) {
                int dashIdx = conn.indexOf('-');
                if (dashIdx != -1) {
                    displayId = conn.mid(dashIdx + 1);
                }
            }
            
            if (status == "connected") {
                QString monitorName = "";
                QFile edidFile(path + "/edid");
                if (edidFile.open(QIODevice::ReadOnly)) {
                    QByteArray edidData = edidFile.readAll();
                    edidFile.close();
                    
                    if (edidData.size() >= 128) {
                        for (int offset = 54; offset <= 108; offset += 18) {
                            if (offset + 18 <= edidData.size()) {
                                const char* block = edidData.constData() + offset;
                                if (block[0] == 0 && block[1] == 0 && block[2] == 0 && 
                                    static_cast<unsigned char>(block[3]) == 0xfc && block[4] == 0) {
                                    
                                    QString nameStr = "";
                                    for (int k = 5; k < 18; ++k) {
                                        char ch = block[k];
                                        if (ch == 0x0a || ch == 0x00) break;
                                        if (ch >= 32 && ch <= 126) {
                                            nameStr.append(ch);
                                        }
                                    }
                                    nameStr = nameStr.trimmed();
                                    if (!nameStr.isEmpty()) {
                                        monitorName = nameStr;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
                
                QTreeWidgetItem* connNode = new QTreeWidgetItem(activeNode);
                if (!monitorName.isEmpty()) {
                    connNode->setText(0, QString("%1 (%2)").arg(monitorName, displayId));
                } else {
                    connNode->setText(0, QString("Display Port (%2)").arg(displayId));
                }
                activeCount++;
            } else {
                QTreeWidgetItem* connNode = new QTreeWidgetItem(inactiveNode);
                connNode->setText(0, QString("%1 (Disconnected)").arg(displayId));
                inactiveCount++;
            }
        }
    }
    
    if (activeCount == 0) {
        QTreeWidgetItem* noneNode = new QTreeWidgetItem(activeNode);
        noneNode->setText(0, "No active displays detected");
    }
    if (inactiveCount == 0) {
        delete inactiveNode;
    }
}

void HardwareDiscovery::parseInput(QTreeWidgetItem* parentNode) {
    QFile file("/proc/bus/input/devices");
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        QTreeWidgetItem* errNode = new QTreeWidgetItem(parentNode);
        errNode->setText(0, "Unable to read input devices");
        return;
    }
    
    QTreeWidgetItem* kbdsNode = new QTreeWidgetItem(parentNode);
    kbdsNode->setText(0, "Keyboards");
    
    QTreeWidgetItem* miceNode = new QTreeWidgetItem(parentNode);
    miceNode->setText(0, "Mice & Pointing Devices");
    
    QTreeWidgetItem* sysNode = new QTreeWidgetItem(parentNode);
    sysNode->setText(0, "System Buttons & Controls");
    
    QString content = file.readAll();
    file.close();
    
    QStringList devices;
    QString currentBlock = "";
    QStringList lines = content.split('\n');
    for (const QString& line : lines) {
        if (line.trimmed().isEmpty()) {
            if (!currentBlock.isEmpty()) {
                devices.append(currentBlock);
                currentBlock = "";
            }
        } else {
            if (!currentBlock.isEmpty()) {
                currentBlock.append("\n");
            }
            currentBlock.append(line);
        }
    }
    if (!currentBlock.isEmpty()) {
        devices.append(currentBlock);
    }
    
    int kbdCount = 0;
    int mouseCount = 0;
    int sysCount = 0;
    
    for (const QString& deviceBlock : devices) {
        QString name = "";
        QString handlers = "";
        
        QStringList devLines = deviceBlock.split('\n', Qt::SkipEmptyParts);
        for (const QString& line : devLines) {
            QString trimmed = line.trimmed();
            if (trimmed.startsWith("N: Name=")) {
                int firstQuote = trimmed.indexOf('"');
                int lastQuote = trimmed.lastIndexOf('"');
                if (firstQuote != -1 && lastQuote != -1 && lastQuote > firstQuote) {
                    name = trimmed.mid(firstQuote + 1, lastQuote - firstQuote - 1);
                } else {
                    name = trimmed.mid(8);
                }
            } else if (trimmed.startsWith("H: Handlers=")) {
                handlers = trimmed.mid(12);
            }
        }
        
        if (name.isEmpty() || handlers.isEmpty()) continue;
        
        if (handlers.contains("mouse")) {
            QTreeWidgetItem* item = new QTreeWidgetItem(miceNode);
            item->setText(0, name);
            QTreeWidgetItem* detail = new QTreeWidgetItem(item);
            detail->setText(0, QString("Handlers: %1").arg(handlers));
            mouseCount++;
        } else if (handlers.contains("kbd")) {
            bool isSystem = name.contains("Power Button") || name.contains("Sleep Button") || 
                             name.contains("Video Bus") || name.contains("PC Speaker") ||
                             name.contains("Mic") || name.contains("Headphone") ||
                             name.contains("HDMI");
                             
            if (isSystem) {
                QTreeWidgetItem* item = new QTreeWidgetItem(sysNode);
                item->setText(0, name);
                QTreeWidgetItem* detail = new QTreeWidgetItem(item);
                detail->setText(0, QString("Handlers: %1").arg(handlers));
                sysCount++;
            } else {
                QTreeWidgetItem* item = new QTreeWidgetItem(kbdsNode);
                item->setText(0, name);
                QTreeWidgetItem* detail = new QTreeWidgetItem(item);
                detail->setText(0, QString("Handlers: %1").arg(handlers));
                kbdCount++;
            }
        }
    }
    
    if (kbdCount == 0) {
        QTreeWidgetItem* none = new QTreeWidgetItem(kbdsNode);
        none->setText(0, "No keyboards detected");
    }
    if (mouseCount == 0) {
        QTreeWidgetItem* none = new QTreeWidgetItem(miceNode);
        none->setText(0, "No mice detected");
    }
    if (sysCount == 0) {
        delete sysNode;
    }
}
