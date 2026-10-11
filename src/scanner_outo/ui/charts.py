"""QtCharts view: one PID/unit at a time, separate ECU and gap segments."""

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis
from PySide6.QtCore import QDateTime, Qt, QMargins, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QComboBox

from scanner_outo.diagnostics.obd import PIDS


class ReadingChart(QWidget):
    def __init__(self, samples, parent=None):
        super().__init__(parent)
        self.samples = samples
        self.selector = QComboBox()
        self.chart = QChart()
        self.chart.setBackgroundBrush(QColor("#ffffff"))
        self.chart.setPlotAreaBackgroundBrush(QColor("#f5f7fa"))
        self.chart.setPlotAreaBackgroundVisible(True)
        self.chart.setBackgroundRoundness(0)
        self.chart.setMargins(QMargins(8, 4, 8, 4))
        self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chart.legend().setFont(QFont(self.font().family(), 9))
        self.time_axis = QDateTimeAxis()
        self.time_axis.setFormat("HH:mm:ss")
        self.time_axis.setTitleText("Hora local")
        self.time_axis.setTickCount(4)
        current = QDateTime.currentDateTime()
        self.time_axis.setRange(current.addSecs(-10), current)
        self.value_axis = QValueAxis()
        for axis in (self.time_axis, self.value_axis):
            axis.setLabelsFont(QFont(self.font().family(), 9))
            axis.setTitleFont(QFont(self.font().family(), 9))
        self.chart.addAxis(self.time_axis, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.value_axis, Qt.AlignmentFlag.AlignLeft)
        self.lines = {}
        self.view = QChartView(self.chart)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setMinimumHeight(170)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.selector)
        layout.addWidget(self.view)
        self.selector.currentIndexChanged.connect(self.refresh)

    def select_pids(self, pids):
        selected = self.selector.currentData()
        self.selector.blockSignals(True)
        self.selector.clear()
        for pid in pids:
            definition = PIDS[pid]
            self.selector.addItem(f"{pid:02X} | {definition.name} ({definition.unit})", pid)
        index = self.selector.findData(selected)
        self.selector.setCurrentIndex(max(0, index))
        self.selector.blockSignals(False)
        self.refresh()

    def refresh(self, *_):
        if not self.isVisible():
            return
        pid = self.selector.currentData()
        if pid is None:
            self.chart.removeAllSeries()
            self.lines.clear()
            self.chart.setTitle("Sem parâmetros seleccionados")
            return
        definition = PIDS[pid]
        self.chart.setTitle("")
        time_axis, value_axis = self.time_axis, self.value_axis
        value_axis.setTitleText(definition.unit)
        points = []
        active = set()
        colors = ("#00796b", "#bd3655", "#3265ad", "#8a6510")
        for index, (ecu, segments) in enumerate(self.samples.segments(f"{pid:02X}").items()):
            for segment_index, segment in enumerate(segments):
                key = (pid, ecu, segment_index)
                active.add(key)
                series = self.lines.get(key)
                if series is None:
                    series = QLineSeries()
                    series.setName(ecu)
                    series.setPen(QPen(QColor(colors[index % len(colors)]), 2))
                    series.setPointsVisible(True)
                    self.chart.addSeries(series)
                    series.attachAxis(time_axis)
                    series.attachAxis(value_axis)
                    self.lines[key] = series
                series.replace([QPointF(instant, value) for instant, value in segment])
                points.extend(segment)
                if segment_index:
                    for marker in self.chart.legend().markers(series):
                        marker.setVisible(False)
        for key in set(self.lines) - active:
            series = self.lines.pop(key)
            self.chart.removeSeries(series)
            series.deleteLater()
        if points:
            low, high = min(p[0] for p in points), max(p[0] for p in points)
            time_axis.setRange(QDateTime.fromMSecsSinceEpoch(int(low - 500)), QDateTime.fromMSecsSinceEpoch(int(max(high, low + 10000))))
            low, high = min(p[1] for p in points), max(p[1] for p in points)
            pad = max((high - low) * .1, 1)
            value_axis.setRange(low - pad, high + pad)
        else:
            self.chart.setTitle(definition.name + " | sem amostras válidas")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
