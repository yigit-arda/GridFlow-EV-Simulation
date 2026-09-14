import ctypes
import os
import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QWidget, QProgressBar, QLineEdit, QFrame, QComboBox, QStackedWidget
)
from PyQt6.QtGui import (
    QIntValidator, QDoubleValidator, QPainter, QPen, QColor, QFont,
    QLinearGradient, QPainterPath, QBrush
)
from PyQt6.QtCore import Qt, QPointF

dll_path = os.path.abspath('./gridflow.dll')
gridflow_lib = ctypes.CDLL(dll_path)

# --- C Function Signatures ---
gridflow_lib.initStation.argtypes = [ctypes.c_float, ctypes.c_int]
gridflow_lib.initStation.restype = ctypes.c_void_p

gridflow_lib.createVehicle.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_int]
gridflow_lib.createVehicle.restype = ctypes.c_void_p

# plugVehicle returns the real socketID it used (0 = queued, -1 = error)
# instead of a bare bool, so the UI never has to guess where a car landed.
gridflow_lib.plugVehicle.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gridflow_lib.plugVehicle.restype = ctypes.c_int

gridflow_lib.advanceTime.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.advanceTime.restype = None

gridflow_lib.unplugVehicle.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.unplugVehicle.restype = None

gridflow_lib.isSocketFull.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.isSocketFull.restype = ctypes.c_bool

gridflow_lib.getSocketChargeType.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.getSocketChargeType.restype = ctypes.c_int

gridflow_lib.getPlateAt.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.getPlateAt.restype = ctypes.c_char_p

gridflow_lib.getSocketSOC.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.getSocketSOC.restype = ctypes.c_float

gridflow_lib.getTargetSOC.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.getTargetSOC.restype = ctypes.c_float

gridflow_lib.getChargeCost.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.getChargeCost.restype = ctypes.c_float

gridflow_lib.getIdleFee.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.getIdleFee.restype = ctypes.c_float

gridflow_lib.getActivePower.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.getActivePower.restype = ctypes.c_float

gridflow_lib.getExpectedFinishReal.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.getExpectedFinishReal.restype = ctypes.c_int

gridflow_lib.getQueueSize.argtypes = [ctypes.c_void_p]
gridflow_lib.getQueueSize.restype = ctypes.c_int

gridflow_lib.getQueuePlateAt.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.getQueuePlateAt.restype = ctypes.c_char_p

gridflow_lib.getQueueEstimatedWaitMinutes.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.getQueueEstimatedWaitMinutes.restype = ctypes.c_int

gridflow_lib.getTotalPower.argtypes = [ctypes.c_void_p]
gridflow_lib.getTotalPower.restype = ctypes.c_float

gridflow_lib.getMaxCapacity.argtypes = [ctypes.c_void_p]
gridflow_lib.getMaxCapacity.restype = ctypes.c_float

gridflow_lib.getStationClock.argtypes = [ctypes.c_void_p]
gridflow_lib.getStationClock.restype = ctypes.c_int

gridflow_lib.getElapsedMinutes.argtypes = [ctypes.c_void_p]
gridflow_lib.getElapsedMinutes.restype = ctypes.c_int

gridflow_lib.getLifetimeChargeRevenue.argtypes = [ctypes.c_void_p]
gridflow_lib.getLifetimeChargeRevenue.restype = ctypes.c_float

gridflow_lib.getLifetimePenaltyRevenue.argtypes = [ctypes.c_void_p]
gridflow_lib.getLifetimePenaltyRevenue.restype = ctypes.c_float

gridflow_lib.getLifetimeSessionCount.argtypes = [ctypes.c_void_p]
gridflow_lib.getLifetimeSessionCount.restype = ctypes.c_int

AC_TYPE2 = 0
DC_CCS = 1

# AC list includes a value above the 22 kW socket cap on purpose, so the
# capping / dynamic load balancing logic is visible in the UI, not just in C.
AC_POWER_CHOICES = [3.7, 7.4, 11.0, 22.0, 43.0]
DC_POWER_CHOICES = [50.0, 100.0, 120.0, 150.0, 180.0]

PRIORITY_LABELS = {"High (1)": 1, "Normal (3)": 3, "Low (5)": 5}

LOW_BATTERY_THRESHOLD = 20.0

# DC accent color: a teal that keeps white text and the lightning-bolt emoji
# clearly legible (the previous orange washed the emoji out).
AC_COLOR = "#42a5f5"
DC_COLOR = "#26a69a"

my_station_ptr = gridflow_lib.initStation(500.0, 4)


DARK_STYLESHEET = """
    QMainWindow, QWidget#Page { background-color: #121212; }
    QLabel { color: #ffffff; font-family: 'Segoe UI'; }
    QPushButton {
        background-color: #2e7d32; color: white; padding: 10px;
        border-radius: 5px; font-weight: bold; font-family: 'Segoe UI';
    }
    QPushButton:hover { background-color: #388e3c; }
    QPushButton:disabled { background-color: #424242; color: #757575; }
    QLineEdit, QComboBox {
        background-color: #1e1e1e; color: white; padding: 8px;
        border: 1px solid #424242; border-radius: 4px; font-size: 14px;
    }
    QFrame#Card {
        background-color: #1e1e1e; border: 1px solid #333333; border-radius: 8px;
    }
    QFrame#StatCard {
        background-color: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px;
    }
    QFrame#StatRow {
        background-color: #1e1e1e; border: 1px solid #333333; border-radius: 8px;
    }
"""


class LineChartWidget(QWidget):
    """A minimal dependency-free line chart (no matplotlib/QtCharts needed -
    just QPainter) for showing a metric over simulated time."""

    def __init__(self, title, color="#4caf50", unit=""):
        super().__init__()
        self.title = title
        self.line_color = QColor(color)
        self.unit = unit
        self.points = []  # list of (x, y)
        self.setMinimumHeight(190)

    def set_data(self, points):
        self.points = points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#1a1a1a"))

        painter.setPen(QColor("#e0e0e0"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(12, 22, self.title)

        if len(self.points) < 2:
            painter.setPen(QColor("#666666"))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(w // 2 - 70, h // 2, "Not enough data yet")
            painter.end()
            return

        margin_left, margin_right = 50, 15
        margin_top, margin_bottom = 34, 22
        plot_w = max(1, w - margin_left - margin_right)
        plot_h = max(1, h - margin_top - margin_bottom)

        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(0.0, min(ys)), max(ys)
        if x_max == x_min:
            x_max = x_min + 1
        if y_max == y_min:
            y_max = y_min + 1

        def to_screen(px, py):
            sx = margin_left + (px - x_min) / (x_max - x_min) * plot_w
            sy = margin_top + (1 - (py - y_min) / (y_max - y_min)) * plot_h
            return QPointF(sx, sy)

        for i in range(4):
            frac = i / 3
            y_val = y_min + frac * (y_max - y_min)
            sy = margin_top + (1 - frac) * plot_h
            painter.setPen(QColor("#2a2a2a"))
            painter.drawLine(int(margin_left), int(sy), int(w - margin_right), int(sy))
            painter.setPen(QColor("#888888"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(4, int(sy) + 4, f"{y_val:.0f}")

        # Soft gradient area fill under the curve, down to the baseline
        # (y_min, usually 0) - gives the chart a lot more visual weight
        # than a bare line.
        baseline_y = to_screen(x_min, y_min).y()
        area_path = QPainterPath()
        first_pt = to_screen(self.points[0][0], self.points[0][1])
        area_path.moveTo(first_pt.x(), baseline_y)
        area_path.lineTo(first_pt)
        for px, py in self.points[1:]:
            area_path.lineTo(to_screen(px, py))
        last_pt = to_screen(self.points[-1][0], self.points[-1][1])
        last_y = self.points[-1][1]
        area_path.lineTo(last_pt.x(), baseline_y)
        area_path.closeSubpath()

        gradient = QLinearGradient(0, margin_top, 0, margin_top + plot_h)
        top_color = QColor(self.line_color)
        top_color.setAlpha(130)
        bottom_color = QColor(self.line_color)
        bottom_color.setAlpha(0)
        gradient.setColorAt(0.0, top_color)
        gradient.setColorAt(1.0, bottom_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(area_path)

        # The line itself, drawn as one smooth path with rounded joins.
        line_path = QPainterPath()
        line_path.moveTo(first_pt)
        for px, py in self.points[1:]:
            line_path.lineTo(to_screen(px, py))
        pen = QPen(self.line_color)
        pen.setWidth(3)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
        painter.drawPath(line_path)

        # Last-value marker: a filled dot with a dark ring, plus a small
        # rounded "chip" showing the current value instead of bare text.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#121212"))
        painter.drawEllipse(last_pt, 6, 6)
        painter.setBrush(self.line_color)
        painter.drawEllipse(last_pt, 4, 4)

        badge_text = f"{last_y:.1f} {self.unit}"
        badge_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(badge_font)
        text_w = painter.fontMetrics().horizontalAdvance(badge_text)
        badge_x = w - margin_right - text_w - 16
        badge_y = margin_top - 26
        painter.setBrush(QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 45))
        painter.drawRoundedRect(badge_x, badge_y, text_w + 16, 20, 8, 8)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(badge_x + 8, badge_y + 14, badge_text)
        painter.end()


class StatsPage(QWidget):
    """Full-page (not a popup) view of the station's persistent revenue
    and session statistics, reached from - and returning to - the
    simulation page via the buttons in the top bar."""

    def __init__(self, station_ptr, on_back, history_load, history_revenue):
        super().__init__()
        self.station_ptr = station_ptr
        # These are the SAME list objects GridFlowApp keeps appending to -
        # holding a reference here means refresh() always sees the latest
        # data with no extra syncing needed.
        self.history_load = history_load
        self.history_revenue = history_revenue
        self.setObjectName("Page")

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        btn_back = QPushButton("\u2190 Back to Simulation")
        btn_back.setStyleSheet("background-color: #455a64;")
        btn_back.clicked.connect(on_back)
        top_row.addWidget(btn_back)
        top_row.addStretch()
        layout.addLayout(top_row)

        title = QLabel("\U0001F4CA Station Revenue & Statistics")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        layout.addSpacing(10)

        self.row_charge = self._build_row(layout, "\u26A1 Charging Revenue (energy)", "\u20ba0.0")
        self.row_penalty = self._build_row(layout, "\u23F3 Penalty Revenue (idle fees)", "\u20ba0.0")
        self.row_total = self._build_row(layout, "\U0001F4B0 Total Lifetime Revenue", "\u20ba0.0")
        self.row_pending = self._build_row(layout, "\U0001F50C Currently Pending (not yet unplugged)", "\u20ba0.0")
        self.row_sessions = self._build_row(layout, "\U0001F697 Vehicles Served So Far", "0")

        note = QLabel(
            "Note: Charging Revenue and Penalty Revenue are added to the lifetime "
            "totals when a vehicle is unplugged. Bills for vehicles still connected "
            "are shown separately in 'Currently Pending' and are not yet counted "
            "in the lifetime total above."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 12px; color: #888888;")
        layout.addSpacing(6)
        layout.addWidget(note)
        layout.addSpacing(16)

        charts_title = QLabel("\U0001F4C8 Over Time")
        charts_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(charts_title)

        load_card = QFrame()
        load_card.setObjectName("Card")
        load_card_layout = QVBoxLayout()
        load_card_layout.setContentsMargins(4, 4, 4, 4)
        self.load_chart = LineChartWidget("Grid Load", color="#42a5f5", unit="kW")
        load_card_layout.addWidget(self.load_chart)
        load_card.setLayout(load_card_layout)
        layout.addWidget(load_card)

        revenue_card = QFrame()
        revenue_card.setObjectName("Card")
        revenue_card_layout = QVBoxLayout()
        revenue_card_layout.setContentsMargins(4, 4, 4, 4)
        self.revenue_chart = LineChartWidget("Lifetime Revenue", color="#4caf50", unit="\u20ba")
        revenue_card_layout.addWidget(self.revenue_chart)
        revenue_card.setLayout(revenue_card_layout)
        layout.addWidget(revenue_card)

        chart_hint = QLabel("X axis: simulated minutes elapsed since the station started.")
        chart_hint.setStyleSheet("font-size: 11px; color: #666666;")
        layout.addWidget(chart_hint)

        layout.addStretch()
        self.setLayout(layout)

    def _build_row(self, parent_layout, title, initial_value):
        frame = QFrame()
        frame.setObjectName("StatRow")
        row = QHBoxLayout()
        row.setContentsMargins(18, 14, 18, 14)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 14px; color: #bdbdbd;")
        lbl_value = QLabel(initial_value)
        lbl_value.setStyleSheet("font-size: 18px; font-weight: bold;")
        row.addWidget(lbl_title)
        row.addStretch()
        row.addWidget(lbl_value)
        frame.setLayout(row)
        parent_layout.addWidget(frame)
        return lbl_value

    def refresh(self):
        charge_rev = gridflow_lib.getLifetimeChargeRevenue(self.station_ptr)
        penalty_rev = gridflow_lib.getLifetimePenaltyRevenue(self.station_ptr)
        sessions = gridflow_lib.getLifetimeSessionCount(self.station_ptr)

        pending = 0.0
        for i in range(4):
            socket_id = i + 1
            if gridflow_lib.isSocketFull(self.station_ptr, socket_id):
                pending += gridflow_lib.getChargeCost(self.station_ptr, socket_id)
                pending += gridflow_lib.getIdleFee(self.station_ptr, socket_id)

        self.row_charge.setText(f"\u20ba{charge_rev:.1f}")
        self.row_penalty.setText(f"\u20ba{penalty_rev:.1f}")
        self.row_total.setText(f"\u20ba{(charge_rev + penalty_rev):.1f}")
        self.row_pending.setText(f"\u20ba{pending:.1f}")
        self.row_sessions.setText(str(sessions))

        self.load_chart.set_data(self.history_load)
        self.revenue_chart.set_data(self.history_revenue)


class SimulationPage(QWidget):
    """The main 2x2 charging-socket dashboard and controls."""

    def __init__(self, station_ptr, on_open_stats, on_data_point=None):
        super().__init__()
        self.station_ptr = station_ptr
        self.total_sockets = 4
        self.on_data_point = on_data_point
        self.setObjectName("Page")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ---------- HEADER / DASHBOARD STATS ----------
        header_row = QHBoxLayout()
        title_label = QLabel("\u26A1 GridFlow Charging Station")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_row.addWidget(title_label)
        header_row.addStretch()

        btn_stats = QPushButton("\U0001F4CA Statistics")
        btn_stats.setStyleSheet("background-color: #6a1b9a;")
        btn_stats.clicked.connect(on_open_stats)
        header_row.addWidget(btn_stats)
        main_layout.addLayout(header_row)
        main_layout.addSpacing(10)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(15)
        self.clock_label = self._build_stat_card(stats_row, "\U0001F553 Simulated Clock", "--:--")
        self.grid_load_label = self._build_stat_card(stats_row, "\U0001F50C Grid Load", "0 / 0 kW")
        self.active_label = self._build_stat_card(stats_row, "\U0001F697 Active Sessions", "0 / 4")
        main_layout.addLayout(stats_row)
        main_layout.addSpacing(10)

        self.info_label = QLabel("Simulation ready. Add a vehicle to start.")
        self.info_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #4caf50;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.info_label)
        main_layout.addSpacing(10)

        # ---------- 2x2 SOCKET CARDS ----------
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(20)

        self.ui_type_labels = []
        self.ui_status_labels = []
        self.ui_waiting_labels = []
        self.ui_plate_labels = []
        self.ui_soc_labels = []
        self.ui_power_labels = []
        self.ui_cost_labels = []
        self.ui_progress_bars = []
        self.ui_unplug_btns = []

        for i in range(self.total_sockets):
            socket_id = i + 1
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(20, 20, 20, 20)

            header_layout = QHBoxLayout()
            lbl_type = QLabel()
            lbl_type.setStyleSheet("font-size: 16px; font-weight: bold;")
            self.ui_type_labels.append(lbl_type)

            lbl_status = QLabel("\u26AA EMPTY")
            lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #9e9e9e;")
            self.ui_status_labels.append(lbl_status)

            header_layout.addWidget(lbl_type)
            header_layout.addStretch()
            header_layout.addWidget(lbl_status)
            card_layout.addLayout(header_layout)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(15)
            self.ui_progress_bars.append(bar)
            card_layout.addWidget(bar)
            card_layout.addSpacing(10)

            # Each data row is its own plain-text QLabel rather than one
            # combined rich-text block with manual <br> line breaks - a
            # single HTML blob is fragile (a parsing hiccup can silently
            # drop everything after the first line). Separate widgets can't
            # do that: each line is guaranteed its own space in the layout.
            lbl_waiting = QLabel("Waiting for connection...")
            lbl_waiting.setStyleSheet("font-size: 14px; color: #777777;")
            self.ui_waiting_labels.append(lbl_waiting)
            card_layout.addWidget(lbl_waiting)

            lbl_plate = QLabel()
            lbl_plate.setStyleSheet("font-size: 14px; color: #e0e0e0;")
            lbl_plate.setVisible(False)
            self.ui_plate_labels.append(lbl_plate)
            card_layout.addWidget(lbl_plate)

            lbl_soc = QLabel()
            lbl_soc.setStyleSheet("font-size: 14px; color: #e0e0e0;")
            lbl_soc.setVisible(False)
            self.ui_soc_labels.append(lbl_soc)
            card_layout.addWidget(lbl_soc)

            lbl_power = QLabel()
            lbl_power.setStyleSheet("font-size: 14px; color: #e0e0e0;")
            lbl_power.setVisible(False)
            self.ui_power_labels.append(lbl_power)
            card_layout.addWidget(lbl_power)

            lbl_cost = QLabel()
            lbl_cost.setStyleSheet("font-size: 14px; color: #e0e0e0;")
            lbl_cost.setVisible(False)
            self.ui_cost_labels.append(lbl_cost)
            card_layout.addWidget(lbl_cost)

            card_layout.addStretch()

            btn_unplug = QPushButton("\U0001F50C Unplug Vehicle")
            btn_unplug.setEnabled(False)
            btn_unplug.clicked.connect(lambda checked, sid=socket_id: self.unplug_car(sid))
            self.ui_unplug_btns.append(btn_unplug)
            card_layout.addWidget(btn_unplug)

            card.setLayout(card_layout)
            self.cards_layout.addWidget(card, i // 2, i % 2)

        main_layout.addLayout(self.cards_layout)
        main_layout.addSpacing(15)

        # ---------- WAIT QUEUE PANEL ----------
        queue_frame = QFrame()
        queue_frame.setObjectName("Card")
        queue_layout = QVBoxLayout()
        queue_title = QLabel("\u23F3 Waiting Queue")
        queue_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #90caf9;")
        self.queue_content_label = QLabel("Queue is empty.")
        self.queue_content_label.setStyleSheet("font-size: 13px; color: #bdbdbd;")
        self.queue_content_label.setWordWrap(True)
        queue_layout.addWidget(queue_title)
        queue_layout.addWidget(self.queue_content_label)
        queue_frame.setLayout(queue_layout)
        main_layout.addWidget(queue_frame)
        main_layout.addSpacing(15)

        # ---------- CONTROL PANEL ----------
        control_layout = QHBoxLayout()

        self.btn_add_ac = QPushButton("\U0001F50C + AC Vehicle (Type 2)")
        self.btn_add_ac.setStyleSheet(f"background-color: #1976d2;")
        self.btn_add_ac.clicked.connect(lambda: self.add_random_car(AC_TYPE2))

        self.btn_add_dc = QPushButton("\u26A1 + DC Fast Vehicle (CCS)")
        self.btn_add_dc.setStyleSheet(f"background-color: {DC_COLOR};")
        self.btn_add_dc.clicked.connect(lambda: self.add_random_car(DC_CCS))

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(list(PRIORITY_LABELS.keys()))
        self.priority_combo.setCurrentText("Normal (3)")

        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("Minutes")
        self.time_input.setValidator(QIntValidator(1, 1440))
        self.time_input.setFixedWidth(80)

        self.btn_advance = QPushButton("\u23E9 Advance Time")
        self.btn_advance.setStyleSheet("background-color: #455a64;")
        self.btn_advance.clicked.connect(self.advance_system_time)

        control_layout.addWidget(self.btn_add_ac)
        control_layout.addWidget(self.btn_add_dc)
        control_layout.addWidget(QLabel("Priority:"))
        control_layout.addWidget(self.priority_combo)
        control_layout.addStretch()
        control_layout.addWidget(QLabel("Simulation Step (min):"))
        control_layout.addWidget(self.time_input)
        control_layout.addWidget(self.btn_advance)

        main_layout.addLayout(control_layout)
        main_layout.addSpacing(15)

        # ---------- MANUAL VEHICLE ENTRY ----------
        manual_frame = QFrame()
        manual_frame.setObjectName("Card")
        manual_outer = QVBoxLayout()
        manual_title = QLabel("\u270D\uFE0F Manual Vehicle Entry")
        manual_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #90caf9;")
        manual_outer.addWidget(manual_title)

        manual_row = QHBoxLayout()

        self.manual_plate_input = QLineEdit()
        self.manual_plate_input.setPlaceholderText("Plate (optional)")
        self.manual_plate_input.setFixedWidth(140)

        self.manual_type_combo = QComboBox()
        self.manual_type_combo.addItems(["AC (Type 2)", "DC (CCS)"])

        self.manual_start_input = QLineEdit()
        self.manual_start_input.setPlaceholderText("Start SOC %")
        self.manual_start_input.setValidator(QDoubleValidator(0.0, 99.0, 1))
        self.manual_start_input.setFixedWidth(90)

        self.manual_target_input = QLineEdit()
        self.manual_target_input.setPlaceholderText("Target SOC %")
        self.manual_target_input.setValidator(QDoubleValidator(1.0, 100.0, 1))
        self.manual_target_input.setFixedWidth(90)

        self.manual_power_input = QLineEdit()
        self.manual_power_input.setPlaceholderText("Max Power kW")
        self.manual_power_input.setValidator(QDoubleValidator(0.1, 400.0, 1))
        self.manual_power_input.setFixedWidth(100)

        self.btn_add_manual = QPushButton("\u2795 Add Custom Vehicle")
        self.btn_add_manual.setStyleSheet("background-color: #6a1b9a;")
        self.btn_add_manual.clicked.connect(self.add_manual_car)

        manual_row.addWidget(self.manual_plate_input)
        manual_row.addWidget(self.manual_type_combo)
        manual_row.addWidget(self.manual_start_input)
        manual_row.addWidget(self.manual_target_input)
        manual_row.addWidget(self.manual_power_input)
        manual_row.addWidget(self.btn_add_manual)
        manual_row.addStretch()

        manual_outer.addLayout(manual_row)
        manual_hint = QLabel("Leave plate empty for an auto-generated one. Uses the Priority selected above.")
        manual_hint.setStyleSheet("font-size: 11px; color: #666666;")
        manual_outer.addWidget(manual_hint)
        manual_frame.setLayout(manual_outer)
        main_layout.addWidget(manual_frame)

        self.setLayout(main_layout)

        self.sync_ui()

    def _build_stat_card(self, parent_layout, title, initial_value):
        frame = QFrame()
        frame.setObjectName("StatCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 12px; color: #9e9e9e;")
        lbl_value = QLabel(initial_value)
        lbl_value.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        frame.setLayout(layout)
        parent_layout.addWidget(frame)
        return lbl_value

    def update_bar_style(self, idx, is_empty=False, is_penalty=False):
        bar = self.ui_progress_bars[idx]
        if is_empty:
            bar.setStyleSheet("QProgressBar { background-color: #262626; border-radius: 7px; } QProgressBar::chunk { background-color: transparent; }")
        elif is_penalty:
            bar.setStyleSheet("QProgressBar { background-color: #333333; border-radius: 7px; } QProgressBar::chunk { background-color: #f44336; border-radius: 7px; }")
        else:
            bar.setStyleSheet("QProgressBar { background-color: #333333; border-radius: 7px; } QProgressBar::chunk { background-color: #4caf50; border-radius: 7px; }")

    # ---------- Actions ----------

    def add_random_car(self, charge_type):
        plate_str = f"06 EV {random.randint(100, 999)}"
        start_soc = float(random.randint(5, 30))
        tgt_soc = float(random.randint(int(start_soc) + 30, 100))

        power_choices = AC_POWER_CHOICES if charge_type == AC_TYPE2 else DC_POWER_CHOICES
        car_max_pwr = float(random.choice(power_choices))

        prio = PRIORITY_LABELS[self.priority_combo.currentText()]

        car_ptr = gridflow_lib.createVehicle(plate_str.encode('utf-8'), charge_type, start_soc, tgt_soc, car_max_pwr, prio)
        result = gridflow_lib.plugVehicle(self.station_ptr, car_ptr)

        type_name = "AC" if charge_type == AC_TYPE2 else "DC"

        if result > 0:
            self.info_label.setText(f"\u2705 {plate_str} ({type_name}, {car_max_pwr:.1f} kW) plugged into Socket {result}.")
            self.info_label.setStyleSheet("color: #4caf50; font-size: 15px; font-weight: bold;")
        elif result == 0:
            self.info_label.setText(f"\u23F3 {plate_str} ({type_name}) added to the waiting queue - no eligible socket free right now.")
            self.info_label.setStyleSheet("color: #ffb300; font-size: 15px; font-weight: bold;")
        else:
            self.info_label.setText("\u274C Could not create/plug the vehicle.")
            self.info_label.setStyleSheet("color: #f44336; font-size: 15px; font-weight: bold;")

        self.sync_ui()

    def add_manual_car(self):
        plate = self.manual_plate_input.text().strip()
        if not plate:
            plate = f"06 EV {random.randint(100, 999)}"

        charge_type = AC_TYPE2 if self.manual_type_combo.currentText().startswith("AC") else DC_CCS

        try:
            start_soc = float(self.manual_start_input.text())
            target_soc = float(self.manual_target_input.text())
            power = float(self.manual_power_input.text())
        except ValueError:
            self.info_label.setText("\u274C Fill in Start SOC, Target SOC and Max Power with valid numbers.")
            self.info_label.setStyleSheet("color: #f44336; font-size: 15px; font-weight: bold;")
            return

        if not (0.0 <= start_soc < 100.0) or not (start_soc < target_soc <= 100.0) or power <= 0.0:
            self.info_label.setText("\u274C Check your values: 0 \u2264 Start < Target \u2264 100, and Power > 0.")
            self.info_label.setStyleSheet("color: #f44336; font-size: 15px; font-weight: bold;")
            return

        prio = PRIORITY_LABELS[self.priority_combo.currentText()]
        car_ptr = gridflow_lib.createVehicle(plate.encode('utf-8'), charge_type, start_soc, target_soc, power, prio)
        result = gridflow_lib.plugVehicle(self.station_ptr, car_ptr)

        type_name = "AC" if charge_type == AC_TYPE2 else "DC"

        if result > 0:
            self.info_label.setText(f"\u2705 {plate} ({type_name}, {power:.1f} kW) plugged into Socket {result}.")
            self.info_label.setStyleSheet("color: #4caf50; font-size: 15px; font-weight: bold;")
        elif result == 0:
            self.info_label.setText(f"\u23F3 {plate} ({type_name}) added to the waiting queue - no eligible socket free right now.")
            self.info_label.setStyleSheet("color: #ffb300; font-size: 15px; font-weight: bold;")
        else:
            self.info_label.setText("\u274C Could not create/plug the vehicle.")
            self.info_label.setStyleSheet("color: #f44336; font-size: 15px; font-weight: bold;")

        self.sync_ui()

    def unplug_car(self, socket_id):
        plate = gridflow_lib.getPlateAt(self.station_ptr, socket_id)
        plate_str = plate.decode('utf-8') if plate else "Vehicle"

        gridflow_lib.unplugVehicle(self.station_ptr, socket_id)

        self.info_label.setText(f"\U0001F44B {plate_str} removed from Socket {socket_id}.")
        self.info_label.setStyleSheet("color: #4caf50; font-size: 15px; font-weight: bold;")

        # Autopilot inside unplugVehicle may have already pulled the next
        # queued car into a socket (possibly this one) - sync_ui() re-reads
        # every socket from C, so that shows up correctly with no extra work.
        self.sync_ui()

    def advance_system_time(self):
        input_text = self.time_input.text()
        if not input_text:
            return

        minutes = int(input_text)
        gridflow_lib.advanceTime(self.station_ptr, minutes)
        self.sync_ui()
        self.info_label.setText(f"\u23E9 Time advanced by {minutes} minutes.")
        self.info_label.setStyleSheet("color: #90caf9; font-size: 15px; font-weight: bold;")

    # ---------- Single source of truth: redraw everything from C ----------

    def sync_ui(self):
        clock_min = gridflow_lib.getStationClock(self.station_ptr)
        self.clock_label.setText(f"{(clock_min // 60) % 24:02d}:{clock_min % 60:02d}")

        total_power = gridflow_lib.getTotalPower(self.station_ptr)
        max_cap = gridflow_lib.getMaxCapacity(self.station_ptr)
        self.grid_load_label.setText(f"{total_power:.1f} / {max_cap:.0f} kW")
        if max_cap > 0 and total_power / max_cap > 0.85:
            self.grid_load_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #f44336;")
        else:
            self.grid_load_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")

        active_count = 0

        for i in range(self.total_sockets):
            socket_id = i + 1
            charge_type = gridflow_lib.getSocketChargeType(self.station_ptr, socket_id)
            type_icon = "\U0001F50C" if charge_type == AC_TYPE2 else "\u26A1"
            type_name = "AC (Type 2)" if charge_type == AC_TYPE2 else "DC (CCS)"
            type_color = AC_COLOR if charge_type == AC_TYPE2 else DC_COLOR
            self.ui_type_labels[i].setText(f"{type_icon} Socket {socket_id} | <span style='color:{type_color}'>{type_name}</span>")

            full = gridflow_lib.isSocketFull(self.station_ptr, socket_id)

            if not full:
                self.ui_status_labels[i].setText("\u26AA EMPTY")
                self.ui_status_labels[i].setStyleSheet("font-size: 14px; font-weight: bold; color: #9e9e9e;")
                self.ui_progress_bars[i].setValue(0)
                self.update_bar_style(i, is_empty=True)
                self.ui_waiting_labels[i].setVisible(True)
                self.ui_plate_labels[i].setVisible(False)
                self.ui_soc_labels[i].setVisible(False)
                self.ui_power_labels[i].setVisible(False)
                self.ui_cost_labels[i].setVisible(False)
                self.ui_unplug_btns[i].setText("\u2014 Empty Socket \u2014")
                self.ui_unplug_btns[i].setEnabled(False)
                # Dimmed look: an empty socket's button shouldn't draw the eye.
                self.ui_unplug_btns[i].setStyleSheet(
                    "background-color: #1c1c1c; color: #4a4a4a; border: 1px solid #262626; font-weight: normal;"
                )
                continue

            active_count += 1
            plate_raw = gridflow_lib.getPlateAt(self.station_ptr, socket_id)
            plate = plate_raw.decode('utf-8') if plate_raw else "?"
            soc = gridflow_lib.getSocketSOC(self.station_ptr, socket_id)
            target = gridflow_lib.getTargetSOC(self.station_ptr, socket_id)
            cost = gridflow_lib.getChargeCost(self.station_ptr, socket_id)
            fee = gridflow_lib.getIdleFee(self.station_ptr, socket_id)
            active_kw = gridflow_lib.getActivePower(self.station_ptr, socket_id)
            finish_min = gridflow_lib.getExpectedFinishReal(self.station_ptr, socket_id)
            finish_str = f"{(finish_min // 60) % 24:02d}:{finish_min % 60:02d}" if finish_min >= 0 else "--:--"

            self.ui_unplug_btns[i].setText("\U0001F50C Unplug Vehicle")
            self.ui_unplug_btns[i].setEnabled(True)
            self.ui_unplug_btns[i].setStyleSheet(
                "background-color: #d32f2f; color: white; font-weight: bold;"
            )
            self.ui_progress_bars[i].setValue(int(soc))

            self.ui_waiting_labels[i].setVisible(False)
            self.ui_plate_labels[i].setVisible(True)
            self.ui_soc_labels[i].setVisible(True)
            self.ui_power_labels[i].setVisible(True)
            self.ui_cost_labels[i].setVisible(True)

            self.ui_plate_labels[i].setText(f"\U0001F697 Plate: {plate}")

            soc_color = "#f44336" if soc < LOW_BATTERY_THRESHOLD else "#e0e0e0"
            self.ui_soc_labels[i].setStyleSheet(f"font-size: 14px; color: {soc_color};")

            if soc >= target:
                self.ui_soc_labels[i].setText(f"\U0001F50B SOC: {soc:.1f}% (Completed)")
                self.ui_power_labels[i].setText("\u26A1 Active Power: 0.0 kW (not drawing from grid)")
                if fee > 0:
                    self.ui_status_labels[i].setText("\u23F3 IDLE PENALTY")
                    self.ui_status_labels[i].setStyleSheet("font-size: 14px; font-weight: bold; color: #f44336;")
                    self.update_bar_style(i, is_penalty=True)
                    self.ui_cost_labels[i].setText(
                        f"\U0001F4B0 Total Bill: \u20ba{(cost + fee):.1f} (Energy \u20ba{cost:.1f} + Idle \u20ba{fee:.1f})"
                    )
                else:
                    self.ui_status_labels[i].setText("\u2705 FINISHED (Grace Period)")
                    self.ui_status_labels[i].setStyleSheet("font-size: 14px; font-weight: bold; color: #ffeb3b;")
                    self.update_bar_style(i)
                    self.ui_cost_labels[i].setText(f"\U0001F4B3 Cost: \u20ba{cost:.1f}")
            else:
                self.ui_status_labels[i].setText("\u26A1 CHARGING")
                self.ui_status_labels[i].setStyleSheet("font-size: 14px; font-weight: bold; color: #4caf50;")
                self.update_bar_style(i)
                self.ui_soc_labels[i].setText(f"\U0001F50B SOC: {soc:.1f}% \u2192 {target:.0f}%")
                self.ui_power_labels[i].setText(f"\u26A1 Active Power: {active_kw:.1f} kW")
                self.ui_cost_labels[i].setText(f"\U0001F4B3 Cost so far: \u20ba{cost:.1f} | ETA: {finish_str}")

        self.active_label.setText(f"{active_count} / {self.total_sockets}")

        # Waiting queue panel, with a rough estimated wait time per vehicle.
        qsize = gridflow_lib.getQueueSize(self.station_ptr)
        if qsize == 0:
            self.queue_content_label.setText("Queue is empty.")
        else:
            entries = []
            for idx in range(qsize):
                p = gridflow_lib.getQueuePlateAt(self.station_ptr, idx)
                plate = p.decode('utf-8') if p else "?"
                wait = gridflow_lib.getQueueEstimatedWaitMinutes(self.station_ptr, idx)
                wait_str = f"~{wait} min" if wait >= 0 else "unknown"
                entries.append(f"{plate} (est. wait: {wait_str})")
            self.queue_content_label.setText(f"{qsize} vehicle(s) waiting: " + " | ".join(entries))

        if self.on_data_point is not None:
            elapsed = gridflow_lib.getElapsedMinutes(self.station_ptr)
            lifetime_revenue = (
                gridflow_lib.getLifetimeChargeRevenue(self.station_ptr)
                + gridflow_lib.getLifetimePenaltyRevenue(self.station_ptr)
            )
            self.on_data_point(elapsed, total_power, lifetime_revenue)


class GridFlowApp(QMainWindow):
    def __init__(self, station_ptr):
        super().__init__()
        self.station_ptr = station_ptr

        # Shared, ever-growing (capped) time-series data for the charts on
        # the Statistics page. Both pages just hold a reference to these
        # same list objects, so there is nothing to keep in sync manually.
        self.history_load = []
        self.history_revenue = []
        self.history_cap = 300

        self.setWindowTitle("GridFlow - EV Charging Station Control Panel")
        self.setGeometry(100, 100, 1100, 800)
        self.setStyleSheet(DARK_STYLESHEET)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.simulation_page = SimulationPage(
            station_ptr, on_open_stats=self.show_stats_page, on_data_point=self.record_history
        )
        self.stats_page = StatsPage(
            station_ptr, on_back=self.show_simulation_page,
            history_load=self.history_load, history_revenue=self.history_revenue,
        )

        self.stack.addWidget(self.simulation_page)   # index 0
        self.stack.addWidget(self.stats_page)         # index 1
        self.stack.setCurrentIndex(0)

    def record_history(self, elapsed_minutes, grid_load_kw, lifetime_revenue):
        self.history_load.append((elapsed_minutes, grid_load_kw))
        self.history_revenue.append((elapsed_minutes, lifetime_revenue))
        if len(self.history_load) > self.history_cap:
            self.history_load.pop(0)
            self.history_revenue.pop(0)

    def show_stats_page(self):
        self.stats_page.refresh()
        self.stack.setCurrentIndex(1)

    def show_simulation_page(self):
        self.simulation_page.sync_ui()
        self.stack.setCurrentIndex(0)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GridFlowApp(my_station_ptr)
    window.show()
    sys.exit(app.exec())