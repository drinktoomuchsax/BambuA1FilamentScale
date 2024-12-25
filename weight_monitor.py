import sys
import serial
import serial.tools.list_ports
import time
from collections import deque

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import pyqtgraph as pg


class SerialReader(QThread):
    data_received = pyqtSignal(float)

    def __init__(self, port, baudrate=9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.ser = None

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Opened serial port: {self.port} at {self.baudrate} baud.")
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            return

        while self.running:
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8').strip()
                    # 假设每行数据格式为 "Weight: 123.45"
                    if line.startswith("Weight:"):
                        try:
                            weight_str = line.split(":")[1].strip()
                            weight = float(weight_str)
                            self.data_received.emit(weight)
                        except (IndexError, ValueError) as e:
                            print(f"Error parsing line: '{line}' - {e}")
                else:
                    time.sleep(0.01)
            except serial.SerialException as e:
                print(f"Serial exception: {e}")
                break

        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"Closed serial port: {self.port}")

    def stop(self):
        self.running = False
        self.wait()


class WeightMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("重量监测系统")
        self.resize(800, 600)

        # 初始化UI组件
        self.init_ui()

        # 数据存储
        self.weight_data = deque(maxlen=6000)  # 存储最近100分钟的数据，假设每秒采样一次
        self.time_data = deque(maxlen=6000)
        self.start_time = time.time()
        self.last_time = self.start_time
        self.interval_times = deque(maxlen=100)  # 用于计算采样频率

        # 串口线程
        self.serial_thread = None

        # 定时器用于更新采样频率
        self.freq_timer = QTimer()
        self.freq_timer.timeout.connect(self.update_frequency)
        self.freq_timer.start(1000)  # 每秒更新一次采样频率

    def init_ui(self):
        layout = QVBoxLayout()

        # 串口选择和连接按钮
        port_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.refresh_ports()
        self.refresh_button = QPushButton("刷新串口")
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.connect_button = QPushButton("连接")
        self.connect_button.clicked.connect(self.connect_serial)

        port_layout.addWidget(QLabel("串口:"))
        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(self.refresh_button)
        port_layout.addWidget(self.connect_button)

        layout.addLayout(port_layout)

        # 显示当前重量和采样频率
        display_layout = QHBoxLayout()
        self.weight_label = QLabel("当前重量: -- g")
        self.freq_label = QLabel("采样频率: -- Hz")
        display_layout.addWidget(self.weight_label)
        display_layout.addWidget(self.freq_label)
        layout.addLayout(display_layout)

        # 绘图区域
        self.plot_widget = pg.PlotWidget(title="重量随时间变化")
        self.plot_widget.setLabel('left', '重量 (g)')
        self.plot_widget.setLabel('bottom', '时间 (分钟)')
        self.plot_curve = self.plot_widget.plot([], [], pen=pg.mkPen('b', width=2))
        layout.addWidget(self.plot_widget)

        self.setLayout(layout)

    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)

    def connect_serial(self):
        if self.serial_thread and self.serial_thread.isRunning():
            # 断开连接
            self.serial_thread.stop()
            self.serial_thread = None
            self.connect_button.setText("连接")
            QMessageBox.information(self, "信息", "已断开串口连接。")
        else:
            # 连接串口
            selected_port = self.port_combo.currentText()
            if not selected_port:
                QMessageBox.warning(self, "警告", "请选择一个串口。")
                return
            self.serial_thread = SerialReader(selected_port)
            self.serial_thread.data_received.connect(self.handle_data)
            self.serial_thread.start()
            self.connect_button.setText("断开")
            QMessageBox.information(self, "信息", f"已连接到串口 {selected_port}。")

    def handle_data(self, weight):
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        elapsed_minutes = elapsed_time / 60.0
        self.weight_data.append(weight)
        self.time_data.append(elapsed_minutes)
        self.interval_times.append(current_time - self.last_time)
        self.last_time = current_time

        # 更新重量显示
        self.weight_label.setText(f"当前重量: {weight:.2f} g")

        # 更新绘图
        self.update_plot()

    def update_plot(self):
        if not self.time_data:
            return
        times = list(self.time_data)
        weights = list(self.weight_data)
        self.plot_curve.setData(times, weights)
        self.plot_widget.enableAutoRange()

    def update_frequency(self):
        if not self.interval_times:
            self.freq_label.setText("采样频率: -- Hz")
            return
        avg_interval = sum(self.interval_times) / len(self.interval_times)
        if avg_interval > 0:
            frequency = 1.0 / avg_interval
            self.freq_label.setText(f"采样频率: {frequency:.2f} Hz")
        else:
            self.freq_label.setText("采样频率: -- Hz")

    def closeEvent(self, event):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    monitor = WeightMonitor()
    monitor.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
