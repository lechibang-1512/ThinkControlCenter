TEMPLATE = app
TARGET = ThinkControlCenter
INCLUDEPATH += .
QT += core widgets

SOURCES += src/main.cpp \
           src/MainWindow.cpp \
           src/HardwareDiscovery.cpp \
           src/SystemMonitor.cpp \
           src/WakeupManager.cpp

HEADERS += src/MainWindow.h \
           src/HardwareDiscovery.h \
           src/SystemMonitor.h \
           src/WakeupManager.h
