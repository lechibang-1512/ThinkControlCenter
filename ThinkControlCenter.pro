TEMPLATE = app
TARGET = ThinkControlCenter
INCLUDEPATH += .
QT += core widgets

SOURCES += main.cpp \
           MainWindow.cpp \
           HardwareDiscovery.cpp \
           SystemMonitor.cpp \
           WakeupManager.cpp

HEADERS += MainWindow.h \
           HardwareDiscovery.h \
           SystemMonitor.h \
           WakeupManager.h
