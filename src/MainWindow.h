#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QTreeWidget>
#include <QTableWidget>
#include <QProgressBar>
#include <QLabel>
#include <QLineEdit>
#include <QTabWidget>
#include <QProcess>
#include <QTimer>
#include "SystemMonitor.h"
#include "WakeupManager.h"

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void setFanModeAcoustic();
    void setFanModeThermal();
    void setFanModeFullSpeed();
    void setFirmwareSetting(const QString& attributeName, const QString& value);
    void toggleWakeupDevice(const QString& deviceName);
    void rescanHardware();
    void filterHardwareTree(const QString& query);
    void updateTelemetry();
    void onProcessOutput();
    void onProcessError();
    void onProcessFinished(int exitCode, QProcess::ExitStatus exitStatus);

private:
    void setupUi();
    QWidget* createArchitectureTab();
    QWidget* createTelemetryTab();
    QWidget* createCoolingTab();
    QWidget* createWakeupTab();
    void addLog(const QString& text, const QString& color = "#10b981");
    void executeRootCommand(const QString& actionDesc, const QString& bashCmd);
    void refreshWakeupTable();

    // UI Widgets
    QTabWidget* tabWidget;
    QPlainTextEdit* terminalOutput;
    
    // Architecture Tab
    QTreeWidget* hardwareTree;
    QLineEdit* searchBox;
    
    // Telemetry Tab
    QProgressBar* cpuBar;
    QLabel* cpuLabel;
    QProgressBar* memBar;
    QLabel* memLabel;
    QTableWidget* thermalsTable;
    
    // Cooling Tab
    QPushButton* btnAcoustic;
    QPushButton* btnThermal;
    QPushButton* btnFullSpeed;
    
    // Wakeup Tab
    QTableWidget* wakeupTable;
    
    // Core systems
    SystemMonitor monitor;
    QTimer* telemetryTimer;
    QProcess* executionProcess;
};

#endif // MAINWINDOW_H
