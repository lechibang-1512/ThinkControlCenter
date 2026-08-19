#include "MainWindow.h"
#include "HardwareDiscovery.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QGroupBox>
#include <QHeaderView>
#include <QLabel>
#include <QSplitter>
#include <QTime>
#include <QScrollBar>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
{
    executionProcess = new QProcess(this);
    connect(executionProcess, &QProcess::readyReadStandardOutput, this, &MainWindow::onProcessOutput);
    connect(executionProcess, &QProcess::readyReadStandardError, this, &MainWindow::onProcessError);
    connect(executionProcess, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished), this, &MainWindow::onProcessFinished);

    setupUi();
    rescanHardware();
    refreshWakeupTable();

    // Start Live Telemetry Poller (1.5s interval)
    telemetryTimer = new QTimer(this);
    connect(telemetryTimer, &QTimer::timeout, this, &MainWindow::updateTelemetry);
    telemetryTimer->start(1500);
    updateTelemetry();
}

MainWindow::~MainWindow() {
    if (telemetryTimer->isActive()) {
        telemetryTimer->stop();
    }
}

void MainWindow::setupUi() {
    this->setWindowTitle("ThinkControlCenter — Lenovo Power & Firmware Hub");
    this->resize(1150, 750);

    // Modern High-Contrast Dark Theme
    this->setStyleSheet(R"(
        QMainWindow {
            background-color: #141416;
        }
        QWidget {
            color: #d1d5db;
            font-family: 'Segoe UI', 'Cantarell', 'Ubuntu', sans-serif;
            font-size: 10pt;
        }
        QTabWidget::pane {
            border: 1px solid #27272a;
            border-radius: 6px;
            background-color: #18181b;
            padding: 10px;
        }
        QTabBar::tab {
            background: #27272a;
            color: #9ca3af;
            font-size: 8.5pt;
            padding: 6px 14px;
            margin-right: 4px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            font-weight: 600;
        }
        QTabBar::tab:selected {
            background: #3b82f6;
            color: #ffffff;
        }
        QTabBar::tab:hover:!selected {
            background: #3f3f46;
            color: #e5e7eb;
        }
        QGroupBox {
            font-weight: 700;
            font-size: 11pt;
            border: 1px solid #27272a;
            border-radius: 8px;
            margin-top: 14px;
            padding-top: 18px;
            background-color: #1c1c20;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 14px;
            padding: 0 6px;
            color: #60a5fa;
        }
        QPushButton {
            background-color: #2563eb;
            color: #ffffff;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #3b82f6;
        }
        QPushButton:pressed {
            background-color: #1d4ed8;
        }
        QPushButton:disabled {
            background-color: #3f3f46;
            color: #71717a;
        }
        QLineEdit {
            background-color: #27272a;
            border: 1px solid #3f3f46;
            border-radius: 6px;
            padding: 6px 12px;
            color: #ffffff;
        }
        QLineEdit:focus {
            border: 1px solid #3b82f6;
        }
        QTreeWidget, QTableWidget {
            background-color: #18181b;
            border: 1px solid #27272a;
            border-radius: 6px;
            alternate-background-color: #1f1f23;
            gridline-color: #27272a;
        }
        QHeaderView::section {
            background-color: #27272a;
            color: #9ca3af;
            padding: 6px;
            border: none;
            font-weight: 600;
        }
        QProgressBar {
            border: 1px solid #3f3f46;
            border-radius: 6px;
            text-align: center;
            background-color: #27272a;
            color: #ffffff;
            font-weight: 600;
        }
        QProgressBar::chunk {
            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #60a5fa);
            border-radius: 5px;
        }
        QPlainTextEdit {
            background-color: #0c0c0e;
            color: #10b981;
            font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
            font-size: 9.5pt;
            border: 1px solid #27272a;
            border-radius: 6px;
            padding: 8px;
        }
    )");

    QWidget* centralWidget = new QWidget(this);
    setCentralWidget(centralWidget);
    QVBoxLayout* rootLayout = new QVBoxLayout(centralWidget);
    rootLayout->setContentsMargins(14, 14, 14, 14);
    rootLayout->setSpacing(12);

    // Splitter between Tabs and Live Terminal Output
    QSplitter* splitter = new QSplitter(Qt::Vertical);

    tabWidget = new QTabWidget();
    tabWidget->addTab(createArchitectureTab(), "Architecture Map");
    tabWidget->addTab(createTelemetryTab(), "Sensors & Telemetry");
    tabWidget->addTab(createCoolingTab(), "Cooling & Firmware (ICE)");
    tabWidget->addTab(createWakeupTab(), "ACPI Sleep & Wakeup");

    splitter->addWidget(tabWidget);

    // Bottom Console Frame
    QWidget* consoleContainer = new QWidget();
    QVBoxLayout* consoleLayout = new QVBoxLayout(consoleContainer);
    consoleLayout->setContentsMargins(0, 4, 0, 0);
    consoleLayout->setSpacing(6);

    QHBoxLayout* consoleHeader = new QHBoxLayout();
    QLabel* logTitle = new QLabel("System Console & Privilege Execution Log");
    logTitle->setTextFormat(Qt::PlainText);
    logTitle->setStyleSheet("font-weight: 700; color: #9ca3af; font-size: 9.5pt;");
    
    QPushButton* btnClearLog = new QPushButton("Clear Console");
    btnClearLog->setStyleSheet("padding: 4px 10px; font-size: 8.5pt; background-color: #3f3f46;");
    connect(btnClearLog, &QPushButton::clicked, this, [this]() {
        terminalOutput->clear();
    });

    consoleHeader->addWidget(logTitle);
    consoleHeader->addStretch();
    consoleHeader->addWidget(btnClearLog);

    terminalOutput = new QPlainTextEdit();
    terminalOutput->setReadOnly(true);
    terminalOutput->setMaximumHeight(160);

    consoleLayout->addLayout(consoleHeader);
    consoleLayout->addWidget(terminalOutput);

    splitter->addWidget(consoleContainer);
    splitter->setStretchFactor(0, 4);
    splitter->setStretchFactor(1, 1);

    rootLayout->addWidget(splitter);

    addLog("ThinkControlCenter started. Hardware interfaces initialized.", "#60a5fa");
}

QWidget* MainWindow::createArchitectureTab() {
    QWidget* tab = new QWidget();
    QVBoxLayout* layout = new QVBoxLayout(tab);
    layout->setContentsMargins(8, 8, 8, 8);
    layout->setSpacing(10);

    QHBoxLayout* toolBar = new QHBoxLayout();
    searchBox = new QLineEdit();
    searchBox->setPlaceholderText("Search hardware components (e.g. NVMe, Audio, Intel, USB)...");
    connect(searchBox, &QLineEdit::textChanged, this, &MainWindow::filterHardwareTree);

    QPushButton* btnRescan = new QPushButton("Rescan Hardware");
    connect(btnRescan, &QPushButton::clicked, this, &MainWindow::rescanHardware);

    QPushButton* btnExpand = new QPushButton("Expand All");
    btnExpand->setStyleSheet("background-color: #3f3f46;");
    connect(btnExpand, &QPushButton::clicked, this, [this]() { hardwareTree->expandAll(); });

    QPushButton* btnCollapse = new QPushButton("Collapse");
    btnCollapse->setStyleSheet("background-color: #3f3f46;");
    connect(btnCollapse, &QPushButton::clicked, this, [this]() { hardwareTree->collapseAll(); });

    toolBar->addWidget(searchBox, 3);
    toolBar->addWidget(btnRescan);
    toolBar->addWidget(btnExpand);
    toolBar->addWidget(btnCollapse);

    hardwareTree = new QTreeWidget();
    hardwareTree->setHeaderHidden(true);
    hardwareTree->setAnimated(true);
    hardwareTree->setIndentation(18);

    layout->addLayout(toolBar);
    layout->addWidget(hardwareTree);
    return tab;
}

QWidget* MainWindow::createTelemetryTab() {
    QWidget* tab = new QWidget();
    QVBoxLayout* layout = new QVBoxLayout(tab);
    layout->setContentsMargins(10, 10, 10, 10);
    layout->setSpacing(14);

    // Top Overview Stats (CPU & RAM Usage)
    QGroupBox* statsGroup = new QGroupBox("System Utilization");
    QGridLayout* statsGrid = new QGridLayout(statsGroup);
    statsGrid->setContentsMargins(16, 16, 16, 16);
    statsGrid->setSpacing(12);

    QLabel* cpuTitle = new QLabel("CPU Load:");
    cpuTitle->setTextFormat(Qt::PlainText);
    cpuTitle->setStyleSheet("font-weight: 600; font-size: 11pt;");
    cpuBar = new QProgressBar();
    cpuBar->setRange(0, 100);
    cpuBar->setFixedHeight(22);
    cpuLabel = new QLabel("0%");
    cpuLabel->setTextFormat(Qt::PlainText);
    cpuLabel->setFixedWidth(60);
    cpuLabel->setStyleSheet("font-weight: 700; color: #60a5fa;");

    QLabel* memTitle = new QLabel("RAM Usage:");
    memTitle->setTextFormat(Qt::PlainText);
    memTitle->setStyleSheet("font-weight: 600; font-size: 11pt;");
    memBar = new QProgressBar();
    memBar->setRange(0, 100);
    memBar->setFixedHeight(22);
    memLabel = new QLabel("0 GB / 0 GB");
    memLabel->setTextFormat(Qt::PlainText);
    memLabel->setFixedWidth(120);
    memLabel->setStyleSheet("font-weight: 700; color: #60a5fa;");

    statsGrid->addWidget(cpuTitle, 0, 0);
    statsGrid->addWidget(cpuBar, 0, 1);
    statsGrid->addWidget(cpuLabel, 0, 2);

    statsGrid->addWidget(memTitle, 1, 0);
    statsGrid->addWidget(memBar, 1, 1);
    statsGrid->addWidget(memLabel, 1, 2);

    // Thermal Sensors Table
    QGroupBox* thermGroup = new QGroupBox("Hardware Temperature Sensors (/sys/class/hwmon)");
    QVBoxLayout* thermLayout = new QVBoxLayout(thermGroup);
    thermLayout->setContentsMargins(14, 14, 14, 14);

    thermalsTable = new QTableWidget();
    thermalsTable->setColumnCount(3);
    thermalsTable->setHorizontalHeaderLabels(QStringList() << "Device / Driver" << "Sensor Zone" << "Temperature (°C)");
    thermalsTable->horizontalHeader()->setSectionResizeMode(0, QHeaderView::ResizeToContents);
    thermalsTable->horizontalHeader()->setSectionResizeMode(1, QHeaderView::Stretch);
    thermalsTable->horizontalHeader()->setSectionResizeMode(2, QHeaderView::ResizeToContents);
    thermalsTable->setAlternatingRowColors(true);
    thermalsTable->setEditTriggers(QAbstractItemView::NoEditTriggers);

    thermLayout->addWidget(thermalsTable);

    layout->addWidget(statsGroup);
    layout->addWidget(thermGroup, 1);
    return tab;
}

QWidget* MainWindow::createCoolingTab() {
    QWidget* tab = new QWidget();
    QVBoxLayout* layout = new QVBoxLayout(tab);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(16);

    // 1. ICE Performance Modes
    QGroupBox* iceGroup = new QGroupBox("Intelligent Cooling Engine (ICE) — Active Fan Profile");
    QVBoxLayout* iceLayout = new QVBoxLayout(iceGroup);
    iceLayout->setContentsMargins(16, 16, 16, 16);
    iceLayout->setSpacing(12);

    QLabel* iceDesc = new QLabel(
        "Lenovo ICE controls the fan curves at the BIOS/SMM firmware layer. Select a preset below to stage changes via think-lmi:"
    );
    iceDesc->setTextFormat(Qt::PlainText);
    iceDesc->setWordWrap(true);
    iceDesc->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
    iceDesc->setStyleSheet("color: #9ca3af; margin-bottom: 4px; line-height: 1.4;");

    QHBoxLayout* btnLayout = new QHBoxLayout();
    btnLayout->setSpacing(12);

    btnAcoustic = new QPushButton("Acoustic Mode (Quiet)");
    btnAcoustic->setStyleSheet("padding: 12px; font-size: 10.5pt; background-color: #059669;");
    btnAcoustic->setCursor(Qt::PointingHandCursor);
    connect(btnAcoustic, &QPushButton::clicked, this, &MainWindow::setFanModeAcoustic);

    btnThermal = new QPushButton("Thermal Mode (Cooler)");
    btnThermal->setStyleSheet("padding: 12px; font-size: 10.5pt; background-color: #d97706;");
    btnThermal->setCursor(Qt::PointingHandCursor);
    connect(btnThermal, &QPushButton::clicked, this, &MainWindow::setFanModeThermal);

    btnFullSpeed = new QPushButton("Full Speed (100% Fan)");
    btnFullSpeed->setStyleSheet("padding: 12px; font-size: 10.5pt; background-color: #dc2626;");
    btnFullSpeed->setCursor(Qt::PointingHandCursor);
    connect(btnFullSpeed, &QPushButton::clicked, this, &MainWindow::setFanModeFullSpeed);

    btnLayout->addWidget(btnAcoustic);
    btnLayout->addWidget(btnThermal);
    btnLayout->addWidget(btnFullSpeed);

    iceLayout->addWidget(iceDesc);
    iceLayout->addLayout(btnLayout);

    // 2. Extra BIOS Firmware Features
    QGroupBox* fwGroup = new QGroupBox("Lenovo Firmware Attributes Management (ThinkLMI)");
    QGridLayout* fwGrid = new QGridLayout(fwGroup);
    fwGrid->setContentsMargins(16, 16, 16, 16);
    fwGrid->setSpacing(12);

    // ICE Thermal Alert
    QLabel* alertLbl = new QLabel("ICE Thermal Alert (Hardware Alarm):");
    alertLbl->setTextFormat(Qt::PlainText);
    QPushButton* btnAlertOn = new QPushButton("Enable");
    QPushButton* btnAlertOff = new QPushButton("Disable");
    btnAlertOff->setStyleSheet("background-color: #3f3f46;");
    connect(btnAlertOn, &QPushButton::clicked, this, [this]() { setFirmwareSetting("ICE Thermal Alert", "Enabled"); });
    connect(btnAlertOff, &QPushButton::clicked, this, [this]() { setFirmwareSetting("ICE Thermal Alert", "Disabled"); });

    // Enhanced Power Saving Mode (ErP)
    QLabel* erpLbl = new QLabel("Enhanced Power Saving Mode (ErP):");
    erpLbl->setTextFormat(Qt::PlainText);
    QPushButton* btnErpOn = new QPushButton("Enable");
    QPushButton* btnErpOff = new QPushButton("Disable");
    btnErpOff->setStyleSheet("background-color: #3f3f46;");
    connect(btnErpOn, &QPushButton::clicked, this, [this]() { setFirmwareSetting("Enhanced Power Saving Mode", "Enabled"); });
    connect(btnErpOff, &QPushButton::clicked, this, [this]() { setFirmwareSetting("Enhanced Power Saving Mode", "Disabled"); });

    // Smart Power On (Alt+P)
    QLabel* spoLbl = new QLabel("Smart Power On (Alt+P wake from S5):");
    spoLbl->setTextFormat(Qt::PlainText);
    QPushButton* btnSpoOn = new QPushButton("Enable");
    QPushButton* btnSpoOff = new QPushButton("Disable");
    btnSpoOff->setStyleSheet("background-color: #3f3f46;");
    connect(btnSpoOn, &QPushButton::clicked, this, [this]() { setFirmwareSetting("Smart Power On", "Enabled"); });
    connect(btnSpoOff, &QPushButton::clicked, this, [this]() { setFirmwareSetting("Smart Power On", "Disabled"); });

    fwGrid->addWidget(alertLbl, 0, 0);
    fwGrid->addWidget(btnAlertOn, 0, 1);
    fwGrid->addWidget(btnAlertOff, 0, 2);

    fwGrid->addWidget(erpLbl, 1, 0);
    fwGrid->addWidget(btnErpOn, 1, 1);
    fwGrid->addWidget(btnErpOff, 1, 2);

    fwGrid->addWidget(spoLbl, 2, 0);
    fwGrid->addWidget(btnSpoOn, 2, 1);
    fwGrid->addWidget(btnSpoOff, 2, 2);

    layout->addWidget(iceGroup);
    layout->addWidget(fwGroup);
    layout->addStretch();
    return tab;
}

QWidget* MainWindow::createWakeupTab() {
    QWidget* tab = new QWidget();
    QVBoxLayout* layout = new QVBoxLayout(tab);
    layout->setContentsMargins(10, 10, 10, 10);
    layout->setSpacing(12);

    QLabel* desc = new QLabel(
        "Control which PCI and USB controllers are permitted to wake the machine from Suspend-to-RAM (S3). "
        "Disabling 'XHC' stops accidental keyboard/mouse nudges from waking the PC."
    );
    desc->setTextFormat(Qt::PlainText);
    desc->setWordWrap(true);
    desc->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
    desc->setStyleSheet("color: #9ca3af; margin-bottom: 6px; line-height: 1.4;");

    QHBoxLayout* topBar = new QHBoxLayout();
    QPushButton* btnRefresh = new QPushButton("Refresh Wakeup List");
    connect(btnRefresh, &QPushButton::clicked, this, &MainWindow::refreshWakeupTable);

    QPushButton* btnQuickDisableUsb = new QPushButton("Quick Toggle USB (XHC)");
    btnQuickDisableUsb->setStyleSheet("background-color: #7c3aed;");
    connect(btnQuickDisableUsb, &QPushButton::clicked, this, [this]() {
        toggleWakeupDevice("XHC");
    });

    topBar->addWidget(btnRefresh);
    topBar->addWidget(btnQuickDisableUsb);
    topBar->addStretch();

    wakeupTable = new QTableWidget();
    wakeupTable->setColumnCount(5);
    wakeupTable->setHorizontalHeaderLabels(QStringList() << "ACPI Node" << "Sleep State" << "Status" << "Description" << "Action");
    wakeupTable->horizontalHeader()->setSectionResizeMode(0, QHeaderView::ResizeToContents);
    wakeupTable->horizontalHeader()->setSectionResizeMode(1, QHeaderView::ResizeToContents);
    wakeupTable->horizontalHeader()->setSectionResizeMode(2, QHeaderView::ResizeToContents);
    wakeupTable->horizontalHeader()->setSectionResizeMode(3, QHeaderView::Stretch);
    wakeupTable->horizontalHeader()->setSectionResizeMode(4, QHeaderView::ResizeToContents);
    wakeupTable->setAlternatingRowColors(true);
    wakeupTable->setEditTriggers(QAbstractItemView::NoEditTriggers);

    layout->addWidget(desc);
    layout->addLayout(topBar);
    layout->addWidget(wakeupTable);
    return tab;
}

void MainWindow::addLog(const QString& text, const QString& color) {
    Q_UNUSED(color);
    QString timestamp = QTime::currentTime().toString("HH:mm:ss");
    terminalOutput->appendPlainText(QString("[%1] $ %2").arg(timestamp, text));
    terminalOutput->verticalScrollBar()->setValue(terminalOutput->verticalScrollBar()->maximum());
}

void MainWindow::executeRootCommand(const QString& actionDesc, const QString& bashCmd) {
    if (executionProcess->state() != QProcess::NotRunning) {
        addLog("A command is currently running. Please wait...", "#ef4444");
        return;
    }

    addLog(QString("Invoking privileged operation: %1").arg(actionDesc), "#fcd34d");
    executionProcess->start("pkexec", QStringList() << "sh" << "-c" << bashCmd);
}

void MainWindow::setFanModeAcoustic() {
    executeRootCommand(
        "Set Fan Mode to Acoustic (Quiet)",
        "echo 'Better Acoustic Performance' > '/sys/class/firmware-attributes/thinklmi/attributes/ICE Performance Modes/current_value'"
    );
}

void MainWindow::setFanModeThermal() {
    executeRootCommand(
        "Set Fan Mode to Thermal (Performance)",
        "echo 'Better Thermal Performance' > '/sys/class/firmware-attributes/thinklmi/attributes/ICE Performance Modes/current_value'"
    );
}

void MainWindow::setFanModeFullSpeed() {
    executeRootCommand(
        "Set Fan Mode to Full Speed (100%)",
        "echo 'Full Speed' > '/sys/class/firmware-attributes/thinklmi/attributes/ICE Performance Modes/current_value'"
    );
}

void MainWindow::setFirmwareSetting(const QString& attributeName, const QString& value) {
    QString cmd = QString("echo '%1' > '/sys/class/firmware-attributes/thinklmi/attributes/%2/current_value'")
                  .arg(value, attributeName);
    executeRootCommand(QString("Set %1 to %2").arg(attributeName, value), cmd);
}

void MainWindow::toggleWakeupDevice(const QString& deviceName) {
    executeRootCommand(
        QString("Toggle ACPI Wakeup State for %1").arg(deviceName),
        WakeupManager::getToggleCommand(deviceName)
    );
    // Refresh table shortly after
    QTimer::singleShot(800, this, &MainWindow::refreshWakeupTable);
}

void MainWindow::rescanHardware() {
    hardwareTree->clear();
    addLog("Scanning system topology and buses...", "#60a5fa");

    QTreeWidgetItem* pciRoot = new QTreeWidgetItem(hardwareTree);
    pciRoot->setText(0, "Motherboard & Chipsets");
    HardwareDiscovery::parsePci(pciRoot);

    QTreeWidgetItem* displayRoot = new QTreeWidgetItem(hardwareTree);
    displayRoot->setText(0, "Displays & Monitors");
    HardwareDiscovery::parseDisplays(displayRoot);

    QTreeWidgetItem* inputRoot = new QTreeWidgetItem(hardwareTree);
    inputRoot->setText(0, "Input Devices (Keyboard/Mouse)");
    HardwareDiscovery::parseInput(inputRoot);

    QTreeWidgetItem* usbRoot = new QTreeWidgetItem(hardwareTree);
    usbRoot->setText(0, "USB Controllers & Devices");
    HardwareDiscovery::parseUsb(usbRoot);

    QTreeWidgetItem* netRoot = new QTreeWidgetItem(hardwareTree);
    netRoot->setText(0, "Network Interfaces");
    HardwareDiscovery::parseNetwork(netRoot);

    hardwareTree->expandAll();
    addLog("System architecture scan complete.", "#10b981");
}

void MainWindow::filterHardwareTree(const QString& query) {
    QString cleanQuery = query.trimmed().toLower();
    if (cleanQuery.isEmpty()) {
        for (int i = 0; i < hardwareTree->topLevelItemCount(); ++i) {
            QTreeWidgetItem* top = hardwareTree->topLevelItem(i);
            top->setHidden(false);
            for (int j = 0; j < top->childCount(); ++j) {
                top->child(j)->setHidden(false);
            }
        }
        return;
    }

    for (int i = 0; i < hardwareTree->topLevelItemCount(); ++i) {
        QTreeWidgetItem* top = hardwareTree->topLevelItem(i);
        bool anyChildMatch = false;

        for (int j = 0; j < top->childCount(); ++j) {
            QTreeWidgetItem* child = top->child(j);
            bool match = child->text(0).toLower().contains(cleanQuery);
            child->setHidden(!match);
            if (match) anyChildMatch = true;
        }

        bool topMatch = top->text(0).toLower().contains(cleanQuery);
        top->setHidden(!topMatch && !anyChildMatch);
        if (anyChildMatch) top->setExpanded(true);
    }
}

void MainWindow::updateTelemetry() {
    // 1. CPU
    double cpu = monitor.getCpuUsage();
    cpuBar->setValue((int)cpu);
    cpuLabel->setText(QString("%1%").arg(cpu, 0, 'f', 1));

    // 2. RAM
    MemoryStats mem = monitor.getMemoryUsage();
    memBar->setValue(mem.percentage);
    memLabel->setText(QString("%1 / %2 GB (%3%)")
        .arg(mem.usedGb, 0, 'f', 1)
        .arg(mem.totalGb, 0, 'f', 1)
        .arg(mem.percentage));

    // 3. Thermals Table
    QVector<ThermalSensor> sensors = monitor.getThermalSensors();
    thermalsTable->setRowCount(sensors.size());
    for (int i = 0; i < sensors.size(); ++i) {
        const ThermalSensor& s = sensors[i];

        QTableWidgetItem* groupItem = new QTableWidgetItem(s.sensorGroup);
        QTableWidgetItem* labelItem = new QTableWidgetItem(s.label);
        QTableWidgetItem* tempItem = new QTableWidgetItem(QString("%1 °C").arg(s.temperature, 0, 'f', 1));
        tempItem->setTextAlignment(Qt::AlignCenter);

        // Color coding: Green < 60°C, Orange 60-80°C, Red > 80°C
        if (s.temperature > 80.0) {
            tempItem->setForeground(QBrush(QColor("#ef4444")));
        } else if (s.temperature > 60.0) {
            tempItem->setForeground(QBrush(QColor("#f59e0b")));
        } else {
            tempItem->setForeground(QBrush(QColor("#10b981")));
        }

        thermalsTable->setItem(i, 0, groupItem);
        thermalsTable->setItem(i, 1, labelItem);
        thermalsTable->setItem(i, 2, tempItem);
    }
}

void MainWindow::refreshWakeupTable() {
    QVector<WakeupDevice> devices = WakeupManager::getWakeupDevices();
    wakeupTable->setRowCount(devices.size());

    for (int i = 0; i < devices.size(); ++i) {
        const WakeupDevice& dev = devices[i];

        QTableWidgetItem* nodeItem = new QTableWidgetItem(dev.device);
        QTableWidgetItem* stateItem = new QTableWidgetItem(dev.sleepState);
        QTableWidgetItem* statusItem = new QTableWidgetItem(dev.enabled ? "ENABLED" : "DISABLED");
        statusItem->setTextAlignment(Qt::AlignCenter);

        if (dev.enabled) {
            statusItem->setForeground(QBrush(QColor("#10b981")));
        } else {
            statusItem->setForeground(QBrush(QColor("#71717a")));
        }

        QTableWidgetItem* descItem = new QTableWidgetItem(dev.description);

        QPushButton* btnToggle = new QPushButton(dev.enabled ? "Disable" : "Enable");
        btnToggle->setStyleSheet(dev.enabled ? "background-color: #dc2626; padding: 4px;" : "background-color: #059669; padding: 4px;");
        QString devName = dev.device;
        connect(btnToggle, &QPushButton::clicked, this, [this, devName]() {
            toggleWakeupDevice(devName);
        });

        wakeupTable->setItem(i, 0, nodeItem);
        wakeupTable->setItem(i, 1, stateItem);
        wakeupTable->setItem(i, 2, statusItem);
        wakeupTable->setItem(i, 3, descItem);
        wakeupTable->setCellWidget(i, 4, btnToggle);
    }
}

void MainWindow::onProcessOutput() {
    QString out = executionProcess->readAllStandardOutput();
    if (!out.trimmed().isEmpty()) {
        addLog(out.trimmed(), "#e2e8f0");
    }
}

void MainWindow::onProcessError() {
    QString err = executionProcess->readAllStandardError();
    if (!err.trimmed().isEmpty()) {
        addLog("ERROR: " + err.trimmed(), "#ef4444");
    }
}

void MainWindow::onProcessFinished(int exitCode, QProcess::ExitStatus exitStatus) {
    if (exitStatus == QProcess::CrashExit) {
        addLog("Process execution crashed.", "#ef4444");
    } else if (exitCode != 0) {
        addLog(QString("Execution failed (Exit Code: %1). Authorization canceled or rejected.").arg(exitCode), "#ef4444");
    } else {
        addLog("Firmware / Kernel state successfully updated!", "#10b981");
    }
}
