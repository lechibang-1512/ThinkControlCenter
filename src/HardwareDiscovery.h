#ifndef HARDWAREDISCOVERY_H
#define HARDWAREDISCOVERY_H

#include <QTreeWidgetItem>

class HardwareDiscovery {
public:
    static void parsePci(QTreeWidgetItem* parentNode);
    static void parseUsb(QTreeWidgetItem* parentNode);
    static void parseNetwork(QTreeWidgetItem* parentNode);
    static void parseDisplays(QTreeWidgetItem* parentNode);
    static void parseInput(QTreeWidgetItem* parentNode);
};

#endif // HARDWAREDISCOVERY_H
