import ctypes
import os
import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QWidget, QProgressBar, QLineEdit, QFrame, QComboBox, QStackedWidget,
    QScrollArea, QSizePolicy
)
from PyQt6.QtGui import (
    QIntValidator, QDoubleValidator, QPainter, QPen, QColor, QFont,
    QLinearGradient, QRadialGradient, QPainterPath, QBrush, QPolygonF, QPixmap
)
from PyQt6.QtCore import Qt, QPointF, QRectF

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

gridflow_lib.getQueueChargeTypeAt.argtypes = [ctypes.c_void_p, ctypes.c_int]
gridflow_lib.getQueueChargeTypeAt.restype = ctypes.c_int

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

# The ONE place to choose how many charging sockets the station has. Every
# view (cards, statistics, isometric scene) derives its layout from this.
NUM_SOCKETS = 4

my_station_ptr = gridflow_lib.initStation(500.0, NUM_SOCKETS)


DARK_STYLESHEET = """
    QMainWindow, QWidget#Page { background-color: #121212; }
    QScrollArea { background-color: #121212; border: none; }
    QScrollArea > QWidget > QWidget { background-color: #121212; }
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
        self.setMinimumHeight(210)

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
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)
        layout.addSpacing(8)

        # Compact tile grid instead of five tall full-width rows - same
        # information, far less vertical space.
        tiles_grid = QGridLayout()
        tiles_grid.setSpacing(12)
        self.row_charge = self._build_tile(tiles_grid, 0, 0, "\u26A1 Charging Revenue", "\u20ba0.0")
        self.row_penalty = self._build_tile(tiles_grid, 0, 1, "\u23F3 Penalty Revenue", "\u20ba0.0")
        self.row_total = self._build_tile(tiles_grid, 0, 2, "\U0001F4B0 Total Lifetime Revenue", "\u20ba0.0")
        self.row_pending = self._build_tile(tiles_grid, 1, 0, "\U0001F50C Currently Pending", "\u20ba0.0")
        self.row_sessions = self._build_tile(tiles_grid, 1, 1, "\U0001F697 Vehicles Served", "0")
        layout.addLayout(tiles_grid)

        note = QLabel(
            "Note: Charging Revenue and Penalty Revenue are added to the lifetime "
            "totals when a vehicle is unplugged. Bills for vehicles still connected "
            "are shown separately in 'Currently Pending' and are not yet counted "
            "in the lifetime total above."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: #888888;")
        layout.addSpacing(4)
        layout.addWidget(note)
        layout.addSpacing(12)

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

    def _build_tile(self, grid_layout, row, col, title, initial_value):
        frame = QFrame()
        frame.setObjectName("StatCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 12px; color: #9e9e9e;")
        lbl_title.setWordWrap(True)
        lbl_value = QLabel(initial_value)
        lbl_value.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        frame.setLayout(layout)
        grid_layout.addWidget(frame, row, col)
        return lbl_value

    def refresh(self):
        charge_rev = gridflow_lib.getLifetimeChargeRevenue(self.station_ptr)
        penalty_rev = gridflow_lib.getLifetimePenaltyRevenue(self.station_ptr)
        sessions = gridflow_lib.getLifetimeSessionCount(self.station_ptr)

        pending = 0.0
        for i in range(NUM_SOCKETS):
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


class IsoCanvas(QWidget):
    """The isometric charging-yard drawing surface. Pure QPainter, same
    projection math as the HTML concept preview - no extra dependency
    (no Qt3D, no WebEngine). Reads only through the getters already used
    by SimulationPage.sync_ui(); it never touches ctypes/plugVehicle
    itself, so the simulation logic in C is completely untouched."""

    # ---- Scene layout (scene units, before ZOOM) ----
    # Bays fill a row left-to-right; once a row holds MAX_COLS bays the next
    # one starts a new row below. Canvas size, bay positions, asphalt and
    # lane stripes are all computed from NUM_SOCKETS in _compute_layout(),
    # so nothing here assumes there are 4 sockets.
    ZOOM = 1.2             # how big the scene is drawn (raise for a closer look)
    MAX_COLS = 6           # bays per row before wrapping to a new row
    CELL_W = 270           # horizontal space reserved per bay
    CELL_H = 260           # vertical space reserved per bay
    PAD = 40
    QUEUE_H = 100
    QUEUE_ENTRY_W = 150
    QUEUE_MAX_VISIBLE = 6
    TILE_W = 200
    TILE_H = 100
    STATUS_COLOR = {"CHARGING": "#4caf50", "FINISHED": "#ffeb3b", "PENALTY": "#f44336"}
    STATUS_TEXT = {"CHARGING": "CHARGING", "FINISHED": "FINISHED (GRACE)", "PENALTY": "IDLE PENALTY"}

    def __init__(self, station_ptr):
        super().__init__()
        self.station_ptr = station_ptr
        self.bays = [{"type": "AC", "status": "EMPTY"} for _ in range(NUM_SOCKETS)]
        self.queue = []
        self.queue_total = 0
        self.grid_load = 0.0
        self.max_cap = 500.0
        self.clock_str = "--:--"
        self.is_night = False
        self._compute_layout()
        self.setMinimumSize(int(self.CANVAS_W * self.ZOOM), int(self.CANVAS_H * self.ZOOM))

        # Optional car sprite: assets/car_icon.png next to this file. If it's
        # missing (or fails to load), _draw_car() below silently falls back
        # to the plain procedural box car - never a hard crash either way.
        asset_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "car_icon.png")
        pixmap = QPixmap(asset_path)
        self.car_pixmap = pixmap if not pixmap.isNull() else None

        self.refresh()

    def _compute_layout(self):
        n = NUM_SOCKETS
        cols = max(1, min(n, self.MAX_COLS))
        rows = (n + cols - 1) // cols
        queue_w = 40 + self.QUEUE_MAX_VISIBLE * self.QUEUE_ENTRY_W
        yard_w = cols * self.CELL_W
        yard_h = rows * self.CELL_H
        self.cols, self.rows = cols, rows
        # The queue box sits above the yard at a fixed spot with a fixed
        # inner layout; adding/removing sockets only changes the yard below.
        self.queue_rect = QRectF(self.PAD, self.PAD, queue_w, self.QUEUE_H)
        self.yard_rect = QRectF(self.PAD, self.PAD + self.QUEUE_H + 30, yard_w, yard_h)
        self.CANVAS_W = max(yard_w, queue_w) + 2 * self.PAD
        self.CANVAS_H = self.yard_rect.bottom() + self.PAD
        self.BAY_CENTERS = [
            (self.yard_rect.left() + self.CELL_W * ((i % cols) + 0.5),
             self.yard_rect.top() + self.CELL_H * (i // cols) + 125)
            for i in range(n)
        ]

    def refresh(self):
        bays = []
        for i in range(NUM_SOCKETS):
            socket_id = i + 1
            charge_type = gridflow_lib.getSocketChargeType(self.station_ptr, socket_id)
            type_name = "AC" if charge_type == AC_TYPE2 else "DC"
            full = gridflow_lib.isSocketFull(self.station_ptr, socket_id)
            if not full:
                bays.append({"type": type_name, "status": "EMPTY"})
                continue
            plate_raw = gridflow_lib.getPlateAt(self.station_ptr, socket_id)
            plate = plate_raw.decode('utf-8') if plate_raw else "?"
            soc = gridflow_lib.getSocketSOC(self.station_ptr, socket_id)
            target = gridflow_lib.getTargetSOC(self.station_ptr, socket_id)
            fee = gridflow_lib.getIdleFee(self.station_ptr, socket_id)
            if soc >= target:
                status = "PENALTY" if fee > 0 else "FINISHED"
            else:
                status = "CHARGING"
            bays.append({"type": type_name, "status": status, "plate": plate, "soc": soc})
        self.bays = bays

        qsize = gridflow_lib.getQueueSize(self.station_ptr)
        queue = []
        for idx in range(min(qsize, self.QUEUE_MAX_VISIBLE)):
            p = gridflow_lib.getQueuePlateAt(self.station_ptr, idx)
            plate = p.decode('utf-8') if p else "?"
            wait = gridflow_lib.getQueueEstimatedWaitMinutes(self.station_ptr, idx)
            
            ctype = gridflow_lib.getQueueChargeTypeAt(self.station_ptr, idx)
            queue.append((plate, wait, ctype))
        
        self.queue = queue
        self.queue_total = qsize

        self.grid_load = gridflow_lib.getTotalPower(self.station_ptr)
        self.max_cap = gridflow_lib.getMaxCapacity(self.station_ptr)
        clock_min = gridflow_lib.getStationClock(self.station_ptr)
        hour = (clock_min // 60) % 24
        self.clock_str = f"{hour:02d}:{clock_min % 60:02d}"
        # Night mode: darker asphalt + headlight beams, purely a function of
        # the simulated clock we already read - no extra state, no timer.
        self.is_night = hour >= 19 or hour < 6

        self.update()

    # ---------- drawing helpers ----------

    def _soc_color(self, soc):
        """Battery-style red -> amber -> green scale by charge level. Used
        for anything that represents 'how full is the battery' - never the
        fixed AC/DC identity color, so a full DC car doesn't read as if it
        still has teal-colored charge left, and a low AC car doesn't read
        as blue when it's actually nearly empty."""
        soc = max(0.0, min(100.0, soc))
        stops = [(0.0, QColor("#f44336")), (50.0, QColor("#ffca28")), (100.0, QColor("#4caf50"))]
        for (s0, c0), (s1, c1) in zip(stops, stops[1:]):
            if s0 <= soc <= s1:
                t = 0.0 if s1 == s0 else (soc - s0) / (s1 - s0)
                r = c0.red() + t * (c1.red() - c0.red())
                g = c0.green() + t * (c1.green() - c0.green())
                b = c0.blue() + t * (c1.blue() - c0.blue())
                return QColor(int(r), int(g), int(b))
        return stops[-1][1]

    def _iso_box(self, painter, cx, cy, hw, hd, h, base_color):
        top_c = base_color.lighter(130)
        left_c = base_color.darker(115)
        right_c = base_color.darker(145)

        b_right = QPointF(cx + hw, cy)
        b_bottom = QPointF(cx, cy + hd)
        b_left = QPointF(cx - hw, cy)
        t_top = QPointF(cx, cy - hd - h)
        t_right = QPointF(cx + hw, cy - h)
        t_bottom = QPointF(cx, cy + hd - h)
        t_left = QPointF(cx - hw, cy - h)

        painter.setPen(QPen(QColor(0, 0, 0, 90), 1))

        painter.setBrush(QBrush(right_c))
        painter.drawPolygon(QPolygonF([b_right, b_bottom, t_bottom, t_right]))

        painter.setBrush(QBrush(left_c))
        painter.drawPolygon(QPolygonF([b_left, b_bottom, t_bottom, t_left]))

        painter.setBrush(QBrush(top_c))
        painter.drawPolygon(QPolygonF([t_top, t_right, t_bottom, t_left]))

    def _floor_diamond(self, painter, cx, cy):
        pts = [
            QPointF(cx, cy - self.TILE_H / 2 + 6),
            QPointF(cx + self.TILE_W / 2 - 6, cy),
            QPointF(cx, cy + self.TILE_H / 2 - 6),
            QPointF(cx - self.TILE_W / 2 + 6, cy),
        ]
        # Green "EV bay" marking, like a real painted charging spot, instead
        # of a plain grey tile.
        border = QColor("#1b5e20") if self.is_night else QColor("#2e7d32")
        fill = QColor("#0f2e18") if self.is_night else QColor("#173d22")
        painter.setPen(QPen(border, 2))
        painter.setBrush(QBrush(fill))
        painter.drawPolygon(QPolygonF(pts))

    def _draw_socket_icon(self, painter, cx, cy):
        """A simple painted plug pictogram on the bay marking, like the
        stencilled EV symbol you see painted on real charging bay tarmac."""
        painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        body = QRectF(cx - 13, cy - 8, 26, 16)
        painter.drawRoundedRect(body, 4, 4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 150)))
        painter.drawEllipse(QPointF(cx - 6, cy), 2.2, 2.2)
        painter.drawEllipse(QPointF(cx + 6, cy), 2.2, 2.2)
        painter.drawEllipse(QPointF(cx, cy - 5), 2.2, 2.2)

    def _draw_asphalt(self, painter):
        """The parking-lot ground under all bays, sized from the layout, with
        dashed lane stripes between columns and rows."""
        r = self.yard_rect
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#0d0d10") if self.is_night else QColor("#232326")))
        painter.drawRoundedRect(r, 26, 26)
        painter.setPen(QPen(QColor(255, 255, 255, 16), 3, Qt.PenStyle.DashLine))
        for c in range(1, self.cols):
            x = r.left() + c * self.CELL_W
            painter.drawLine(QPointF(x, r.top() + 25), QPointF(x, r.bottom() - 25))
        for k in range(1, self.rows):
            y = r.top() + k * self.CELL_H
            painter.drawLine(QPointF(r.left() + 25, y), QPointF(r.right() - 25, y))

    def _text_center(self, painter, x, y, s, font, color):
        painter.setFont(font)
        painter.setPen(QColor(color))
        fm = painter.fontMetrics()
        w = fm.horizontalAdvance(s)
        painter.drawText(int(x - w / 2), int(y), s)

    def _draw_glow(self, painter, cx, cy, color):
        """Soft radial glow on the ground under a charging car. Static (no
        pulsing) on purpose - a blinking version needs a repaint timer,
        which we're deliberately leaving out for now to keep this robust."""
        gradient = QRadialGradient(QPointF(cx, cy), 65)
        near = QColor(color)
        near.setAlpha(150)
        far = QColor(color)
        far.setAlpha(0)
        gradient.setColorAt(0.0, near)
        gradient.setColorAt(1.0, far)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.save()
        painter.translate(cx, cy)
        painter.scale(1.0, 0.45)  # flatten the glow onto the "ground plane"
        painter.drawEllipse(QPointF(0, 0), 65, 65)
        painter.restore()

    def _draw_headlight(self, painter, cx, cy, direction=1):
        """A soft light cone spilling onto the ground, only used at night
        (simulated clock 19:00-06:00) - so it won't show at all if you test
        during the day. Made brighter/wider than the first pass so it's
        clearly visible against the dark asphalt."""
        gradient = QLinearGradient(cx, cy, cx + direction * 90, cy + 46)
        c1 = QColor(255, 248, 210, 160)
        c2 = QColor(255, 248, 210, 0)
        gradient.setColorAt(0.0, c1)
        gradient.setColorAt(1.0, c2)
        path = QPainterPath()
        path.moveTo(cx, cy)
        path.lineTo(cx + direction * 90, cy + 16)
        path.lineTo(cx + direction * 90, cy + 56)
        path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(path)

    def _draw_car(self, painter, cx, cy, status_color, scale=1.0, draw_shadow=True):
        """Draws assets/car_icon.png if it loaded; otherwise falls back to
        a flat vector car silhouette (body/roof/windshield/wheels/lights)
        instead of a plain box, so a missing asset still reads as a car.
        Used for both the bay cars (scale=1.0) and the small queue icons
        (scale<1, no ground shadow) - one drawing routine, one look.

        The sprite itself is a fixed color, so status (charging/finished/
        penalty) is carried by a flattened colored shadow underneath it
        instead of by tinting the car itself."""
        if draw_shadow:
            shadow_color = QColor(status_color)
            shadow_color.setAlpha(90)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(shadow_color))
            painter.save()
            painter.translate(cx, cy + 14 * scale)
            painter.scale(1.0, 0.4)
            painter.drawEllipse(QPointF(0, 0), 40 * scale, 40 * scale)
            painter.restore()

        if self.car_pixmap is not None:
            w = 78.0 * scale
            h = w * self.car_pixmap.height() / self.car_pixmap.width()
            bottom_y = cy + 12 * scale
            top_y = bottom_y - h
            painter.drawPixmap(QRectF(cx - w / 2, top_y, w, h), self.car_pixmap, QRectF(self.car_pixmap.rect()))
            return h + 4 * scale

        return self._draw_flat_car_fallback(painter, cx, cy, status_color, scale)

    def _draw_flat_car_fallback(self, painter, cx, cy, status_color, scale=1.0):
        """A simple flat side-view car silhouette (hood, roof, windshield,
        two wheels, head/tail light) built from one QPainterPath plus a
        few circles - only used if car_icon.png can't be loaded at all."""
        painter.save()
        painter.translate(cx, cy)
        painter.scale(scale, scale)

        body = QPainterPath()
        body.moveTo(-50, 10)
        body.lineTo(-50, 1)
        body.quadTo(-48, -13, -30, -17)
        body.lineTo(-22, -29)
        body.lineTo(15, -29)
        body.quadTo(28, -29, 32, -17)
        body.lineTo(45, -9)
        body.quadTo(50, -7, 50, 1)
        body.lineTo(50, 10)
        body.closeSubpath()

        painter.setPen(QPen(QColor("#0d0d0d"), 2))
        painter.setBrush(QBrush(status_color))
        painter.drawPath(body)

        windshield = QPainterPath()
        windshield.moveTo(-28, -18)
        windshield.lineTo(-21, -27)
        windshield.lineTo(13, -27)
        windshield.lineTo(9, -18)
        windshield.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(190, 225, 255, 160)))
        painter.drawPath(windshield)

        for wx in (-27, 27):
            painter.setBrush(QBrush(QColor("#161616")))
            painter.drawEllipse(QPointF(wx, 12), 12, 12)
            painter.setBrush(QBrush(QColor("#555555")))
            painter.drawEllipse(QPointF(wx, 12), 5, 5)

        painter.setBrush(QBrush(QColor("#fff6c9")))
        painter.drawEllipse(QPointF(-49, 3), 3.2, 3.2)
        painter.setBrush(QBrush(QColor("#e04b2f")))
        painter.drawRect(QRectF(46, -3, 4, 6))

        painter.restore()
        return 42 * scale  # visual height above cy, for anchoring things above it

    def _draw_holo_cylinder(self, painter, cx, top_y, soc):
        """Floating translucent 'holographic' battery cylinder above the
        car, colored by charge level (see _soc_color) rather than by AC/DC
        identity - a full DC car should read as green, not teal."""
        max_h, rw, rh = 46, 20, 7
        fill_h = max(6.0, max_h * (soc / 100.0))
        bottom_y = top_y
        shell_top_y = top_y - max_h
        fill_top_y = bottom_y - fill_h
        color = self._soc_color(soc)

        painter.setPen(QPen(QColor(255, 255, 255, 55), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
        painter.drawEllipse(QPointF(cx, shell_top_y), rw, rh)
        painter.drawLine(QPointF(cx - rw, shell_top_y), QPointF(cx - rw, bottom_y))
        painter.drawLine(QPointF(cx + rw, shell_top_y), QPointF(cx + rw, bottom_y))
        painter.drawEllipse(QPointF(cx, bottom_y), rw, rh)

        fill_color = QColor(color)
        fill_color.setAlpha(150)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(fill_color))
        body = QPainterPath()
        body.moveTo(cx - rw, fill_top_y)
        body.lineTo(cx + rw, fill_top_y)
        body.lineTo(cx + rw, bottom_y)
        body.lineTo(cx - rw, bottom_y)
        body.closeSubpath()
        painter.drawPath(body)
        painter.setBrush(QBrush(fill_color.lighter(125)))
        painter.drawEllipse(QPointF(cx, fill_top_y), rw, rh)

        self._text_center(painter, cx, shell_top_y - 8, f"{soc:.0f}%",
                           QFont("Segoe UI", 9, QFont.Weight.Bold), "#ffffff")

    def _draw_bay_geometry(self, painter, cx, cy, data):
        self._floor_diamond(painter, cx, cy)
        self._draw_socket_icon(painter, cx, cy)

        type_name = data["type"]
        status = data["status"]
        type_color = QColor(AC_COLOR if type_name == "AC" else DC_COLOR)

        pole_x, pole_y = cx, cy - self.TILE_H / 2 + 14
        pole_color = QColor("#3a3a3a") if status == "EMPTY" else type_color
        self._iso_box(painter, pole_x, pole_y, 6, 6, 46, pole_color)

        if status == "CHARGING":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(type_color))
            painter.drawEllipse(QPointF(pole_x, pole_y - 50), 5, 5)

        if status == "EMPTY":
            return

        car_x, car_y = cx + 18, cy + 6
        status_color = QColor(self.STATUS_COLOR.get(status, "#888888"))

        # The power cable is only drawn while actually CHARGING. Once the
        # target is reached the car stops drawing power immediately (that
        # part was already correct in the C simulation - getActivePower()
        # returns 0 the moment currBatLvl >= tgtBatLvl); what was misleading
        # was drawing the exact same "live" cable for FINISHED/PENALTY too,
        # which visually implied power was still flowing when it wasn't.
        if status == "CHARGING":
            self._draw_glow(painter, car_x, car_y + 4, self.STATUS_COLOR["CHARGING"])
            cable_pen = QPen(type_color, 2.5, Qt.PenStyle.DashLine)
            painter.setPen(cable_pen)
            painter.drawLine(QPointF(pole_x, pole_y - 40), QPointF(car_x - 10, car_y - 14))

        car_height = self._draw_car(painter, car_x, car_y, status_color)

        if self.is_night:
            # Anchored near the car's front-left corner (that's the "front"
            # in the icon image / fallback silhouette), beam pointing
            # further forward-left onto the ground - it was previously
            # anchored/pointed off the rear, looking like it shone backward.
            self._draw_headlight(painter, car_x - 32, car_y - 8, direction=-1)

        soc = data.get("soc", 0.0)
        self._draw_holo_cylinder(painter, car_x + 30, car_y - car_height - 6, soc)

    def _draw_bay_labels(self, painter, cx, cy, socket_id, data):
        type_name = data["type"]
        status = data["status"]

        label_y = cy + self.TILE_H / 2 + 26
        self._text_center(painter, cx, label_y, f"Socket {socket_id} | {type_name}",
                           QFont("Segoe UI", 11, QFont.Weight.Bold), "#ffffff")
        if status == "EMPTY":
            self._text_center(painter, cx, label_y + 16, "EMPTY", QFont("Segoe UI", 9), "#8a8a8a")
        else:
            plate = data.get("plate", "?")
            soc = data.get("soc", 0.0)
            self._text_center(painter, cx, label_y + 16, f"{plate}  |  SOC {soc:.0f}%",
                               QFont("Segoe UI", 9), "#8a8a8a")
            self._text_center(painter, cx, label_y + 32, self.STATUS_TEXT[status],
                               QFont("Segoe UI", 9, QFont.Weight.Bold), self.STATUS_COLOR[status])

    # Grid load and clock are no longer drawn inside the canvas - they're
    # real QLabel tiles in IsoPage's header now (top-left, outside the
    # scaled/painted scene) so they stay crisp and don't compete for space
    # with the yard itself.

    def _draw_queue(self, painter):
        """Waiting queue as a rounded box: title, then up to
        QUEUE_MAX_VISIBLE entries in a row (car icon, plate, est. wait)."""
        box = self.queue_rect
        painter.setPen(QPen(QColor("#2e2e34"), 1.5))
        painter.setBrush(QBrush(QColor("#1a1a1e")))
        painter.drawRoundedRect(box, 14, 14)

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#9e9e9e"))
        painter.drawText(int(box.left() + 20), int(box.top() + 26), f"WAITING QUEUE ({self.queue_total})")
        hidden = self.queue_total - len(self.queue)
        if hidden > 0:
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(int(box.right() - 90), int(box.top() + 26), f"+{hidden} more")
        if not self.queue:
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor("#666666"))
            painter.drawText(int(box.left() + 20), int(box.top() + 66), "Queue is empty.")
            return

        for idx, (plate, wait, ctype) in enumerate(self.queue):
            ex = box.left() + 20 + idx * self.QUEUE_ENTRY_W
            cy = box.top() + 68
            self._draw_car(painter, ex + 20, cy, QColor("#607d8b"), scale=0.42, draw_shadow=False)
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor("#e0e0e0"))
            painter.drawText(int(ex + 44), int(cy - 4), plate)
            wait_str = f"~{wait} min" if wait >= 0 else "..."
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#8a8a8a"))
            painter.drawText(int(ex + 44), int(cy + 11), wait_str)
            badge = QRectF(ex + 104, cy + 1, 28, 14)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(AC_COLOR if ctype == AC_TYPE2 else DC_COLOR)))
            painter.drawRoundedRect(badge, 5, 5)
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor("#ffffff"))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, "AC" if ctype == AC_TYPE2 else "DC")
            

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg_color = QColor("#0a0a0f") if self.is_night else QColor("#121212")
        painter.fillRect(self.rect(), bg_color)

        # Fixed zoom instead of "shrink everything to fit the window": the
        # scene keeps its size whatever the socket count, and the
        # QScrollArea around this widget (see IsoPage) scrolls horizontally
        # and vertically when the scene is bigger than the window.
        offset_x = max(0.0, (self.width() - self.CANVAS_W * self.ZOOM) / 2)
        painter.translate(offset_x, 0)
        painter.scale(self.ZOOM, self.ZOOM)

        self._draw_asphalt(painter)
        self._draw_queue(painter)

        # Two passes: all bay geometry first, then all labels on top, so a
        # label can never end up underneath a neighbouring bay's graphics.
        for i, bay in enumerate(self.bays):
            cx, cy = self.BAY_CENTERS[i]
            self._draw_bay_geometry(painter, cx, cy, bay)
        for i, bay in enumerate(self.bays):
            cx, cy = self.BAY_CENTERS[i]
            self._draw_bay_labels(painter, cx, cy, i + 1, bay)

        painter.end()


class IsoPage(QWidget):
    """Full-page wrapper around IsoCanvas: a small header (back button +
    Grid Load / Clock tiles top-left, title top-center) and the canvas
    filling the rest of the page."""

    def __init__(self, station_ptr, on_back):
        super().__init__()
        self.setObjectName("Page")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        btn_back = QPushButton("\u2190 Back to Simulation")
        btn_back.setStyleSheet("background-color: #455a64;")
        btn_back.clicked.connect(on_back)
        top_row.addWidget(btn_back)
        top_row.addSpacing(16)
        self.grid_load_label = self._build_mini_tile(top_row, "GRID LOAD", "0 / 0 kW")
        self.clock_label = self._build_mini_tile(top_row, "SIMULATED CLOCK", "--:--")
        top_row.addStretch()
        layout.addLayout(top_row)

        title = QLabel("Isometric Station View")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.canvas = IsoCanvas(station_ptr)
        canvas_scroll = QScrollArea()
        canvas_scroll.setWidgetResizable(True)
        canvas_scroll.setFrameShape(QFrame.Shape.NoFrame)
        canvas_scroll.setWidget(self.canvas)
        layout.addWidget(canvas_scroll, stretch=1)

        self.setLayout(layout)

    def _build_mini_tile(self, parent_layout, title, initial_value):
        frame = QFrame()
        frame.setObjectName("StatCard")
        box = QVBoxLayout()
        box.setContentsMargins(12, 6, 12, 6)
        box.setSpacing(0)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 10px; color: #9e9e9e;")
        lbl_value = QLabel(initial_value)
        lbl_value.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        box.addWidget(lbl_title)
        box.addWidget(lbl_value)
        frame.setLayout(box)
        parent_layout.addWidget(frame)
        return lbl_value

    def refresh(self):
        self.canvas.refresh()
        self.grid_load_label.setText(f"{self.canvas.grid_load:.0f} / {self.canvas.max_cap:.0f} kW")
        self.clock_label.setText(self.canvas.clock_str)


class SimulationPage(QWidget):
    """The main 2x2 charging-socket dashboard and controls."""

    def __init__(self, station_ptr, on_open_stats, on_open_iso=None, on_data_point=None):
        super().__init__()
        self.station_ptr = station_ptr
        self.total_sockets = NUM_SOCKETS
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

        if on_open_iso is not None:
            btn_iso = QPushButton("3D View")
            btn_iso.setStyleSheet("background-color: #00695c;")
            btn_iso.clicked.connect(on_open_iso)
            header_row.addWidget(btn_iso)

        btn_stats = QPushButton("Statistics")
        btn_stats.setStyleSheet("background-color: #6a1b9a;")
        btn_stats.clicked.connect(on_open_stats)
        header_row.addWidget(btn_stats)
        main_layout.addLayout(header_row)
        main_layout.addSpacing(10)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(15)
        self.clock_label = self._build_stat_card(stats_row, "\U0001F553 Simulated Clock", "--:--")
        self.grid_load_label = self._build_stat_card(stats_row, "\U0001F50C Grid Load", "0 / 0 kW")
        self.active_label = self._build_stat_card(stats_row, "\U0001F697 Active Sessions", f"0 / {NUM_SOCKETS}")
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

        self.ui_status_labels = []
        self.ui_content_stacks = []
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

            charge_type = gridflow_lib.getSocketChargeType(self.station_ptr, socket_id)
            type_icon = "\U0001F50C" if charge_type == AC_TYPE2 else "\u26A1"
            type_name = "AC (Type 2)" if charge_type == AC_TYPE2 else "DC (CCS)"
            type_color = AC_COLOR if charge_type == AC_TYPE2 else DC_COLOR

            # A socket's connector type never changes at runtime, so this is
            # set once here - and as two separate PLAIN labels (not one
            # label with an HTML <span> for the color) so there is nothing
            # for a rich-text parser to trip over.
            header_layout = QHBoxLayout()
            lbl_socket = QLabel(f"{type_icon} Socket {socket_id} |")
            lbl_socket.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
            lbl_type_name = QLabel(type_name)
            lbl_type_name.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {type_color};")

            lbl_status = QLabel("\u26AA EMPTY")
            lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #9e9e9e;")
            self.ui_status_labels.append(lbl_status)

            header_layout.addWidget(lbl_socket)
            header_layout.addWidget(lbl_type_name)
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

            # The "empty" vs "occupied" detail area is two separate pages of
            # a QStackedWidget, not the same labels toggled with
            # setVisible(). Repeatedly show/hide-ing several sibling labels
            # inside one QVBoxLayout was what caused the header/detail text
            # to visually overlap after a socket's first fill - QStackedWidget
            # is Qt's dedicated, well-tested tool for swapping a content
            # area and doesn't have that failure mode. It also keeps every
            # card the same height, whether empty or occupied.
            content_stack = QStackedWidget()
            content_stack.setMinimumHeight(100)

            empty_page = QWidget()
            empty_page_layout = QVBoxLayout()
            empty_page_layout.setContentsMargins(0, 0, 0, 0)
            lbl_waiting = QLabel("Waiting for connection...")
            lbl_waiting.setStyleSheet("font-size: 14px; color: #777777;")
            empty_page_layout.addWidget(lbl_waiting)
            empty_page_layout.addStretch()
            empty_page.setLayout(empty_page_layout)

            full_page = QWidget()
            full_page_layout = QVBoxLayout()
            full_page_layout.setContentsMargins(0, 0, 0, 0)
            full_page_layout.setSpacing(4)

            lbl_plate = QLabel()
            lbl_plate.setStyleSheet("font-size: 14px; color: #e0e0e0;")
            self.ui_plate_labels.append(lbl_plate)
            full_page_layout.addWidget(lbl_plate)

            lbl_soc = QLabel()
            lbl_soc.setStyleSheet("font-size: 14px; color: #e0e0e0;")
            self.ui_soc_labels.append(lbl_soc)
            full_page_layout.addWidget(lbl_soc)

            lbl_power = QLabel()
            lbl_power.setStyleSheet("font-size: 14px; color: #e0e0e0;")
            self.ui_power_labels.append(lbl_power)
            full_page_layout.addWidget(lbl_power)

            lbl_cost = QLabel()
            lbl_cost.setStyleSheet("font-size: 14px; color: #e0e0e0;")
            self.ui_cost_labels.append(lbl_cost)
            full_page_layout.addWidget(lbl_cost)
            full_page_layout.addStretch()
            full_page.setLayout(full_page_layout)

            content_stack.addWidget(empty_page)   # index 0
            content_stack.addWidget(full_page)    # index 1
            self.ui_content_stacks.append(content_stack)
            card_layout.addWidget(content_stack)

            btn_unplug = QPushButton("Unplug Vehicle")
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

        self.btn_add_ac = QPushButton("+ AC Vehicle (Type 2)")
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
        # Split across two shorter rows instead of one long one, so this
        # section never forces the window/cards wider than they need to be.
        manual_frame = QFrame()
        manual_frame.setObjectName("Card")
        manual_outer = QVBoxLayout()
        manual_title = QLabel("Manual Vehicle Entry")
        manual_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #90caf9;")
        manual_outer.addWidget(manual_title)

        manual_row1 = QHBoxLayout()

        self.manual_plate_input = QLineEdit()
        self.manual_plate_input.setPlaceholderText("Plate (optional)")
        self.manual_plate_input.setFixedWidth(130)

        self.manual_type_combo = QComboBox()
        self.manual_type_combo.addItems(["AC (Type 2)", "DC (CCS)"])
        self.manual_type_combo.setFixedWidth(120)

        self.manual_start_input = QLineEdit()
        self.manual_start_input.setPlaceholderText("Start SOC %")
        self.manual_start_input.setValidator(QDoubleValidator(0.0, 99.0, 1))
        self.manual_start_input.setFixedWidth(85)

        self.manual_target_input = QLineEdit()
        self.manual_target_input.setPlaceholderText("Target SOC %")
        self.manual_target_input.setValidator(QDoubleValidator(1.0, 100.0, 1))
        self.manual_target_input.setFixedWidth(85)

        manual_row1.addWidget(self.manual_plate_input)
        manual_row1.addWidget(self.manual_type_combo)
        manual_row1.addWidget(self.manual_start_input)
        manual_row1.addWidget(self.manual_target_input)
        manual_row1.addStretch()
        manual_outer.addLayout(manual_row1)

        manual_row2 = QHBoxLayout()

        self.manual_power_input = QLineEdit()
        self.manual_power_input.setPlaceholderText("Max Power kW")
        self.manual_power_input.setValidator(QDoubleValidator(0.1, 400.0, 1))
        self.manual_power_input.setFixedWidth(100)

        self.btn_add_manual = QPushButton("Add Custom Vehicle")
        self.btn_add_manual.setStyleSheet("background-color: #6a1b9a;")
        self.btn_add_manual.clicked.connect(self.add_manual_car)

        manual_hint = QLabel("Leave plate empty for an auto-generated one. Uses the Priority selected above.")
        manual_hint.setStyleSheet("font-size: 11px; color: #666666;")

        manual_row2.addWidget(self.manual_power_input)
        manual_row2.addWidget(self.btn_add_manual)
        manual_row2.addSpacing(10)
        manual_row2.addWidget(manual_hint)
        manual_row2.addStretch()
        manual_outer.addLayout(manual_row2)

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

    def update_bar_style(self, idx, is_empty=False, is_penalty=False, is_finished=False):
        bar = self.ui_progress_bars[idx]
        if is_empty:
            bar.setStyleSheet("QProgressBar { background-color: #262626; border-radius: 7px; } QProgressBar::chunk { background-color: transparent; }")
        elif is_penalty:
            bar.setStyleSheet("QProgressBar { background-color: #333333; border-radius: 7px; } QProgressBar::chunk { background-color: #f44336; border-radius: 7px; }")
        elif is_finished:
            # Distinct from the CHARGING (green) bar on purpose: a full
            # green bar here used to look identical to "still actively
            # charging", which is exactly the misleading impression this
            # was giving even though the vehicle was correctly drawing 0 kW.
            bar.setStyleSheet("QProgressBar { background-color: #333333; border-radius: 7px; } QProgressBar::chunk { background-color: #ffeb3b; border-radius: 7px; }")
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

        if not (0.0 <= start_soc < 100.0) or not (start_soc < target_soc <= 100.0) or not (0.0 < power <= 400.0):
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

            full = gridflow_lib.isSocketFull(self.station_ptr, socket_id)

            if not full:
                self.ui_status_labels[i].setText("\u26AA EMPTY")
                self.ui_status_labels[i].setStyleSheet("font-size: 14px; font-weight: bold; color: #9e9e9e;")
                self.ui_progress_bars[i].setValue(0)
                self.update_bar_style(i, is_empty=True)
                self.ui_content_stacks[i].setCurrentIndex(0)
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

            self.ui_unplug_btns[i].setText("Unplug Vehicle")
            self.ui_unplug_btns[i].setEnabled(True)
            self.ui_unplug_btns[i].setStyleSheet(
                "background-color: #d32f2f; color: white; font-weight: bold;"
            )
            self.ui_progress_bars[i].setValue(int(soc))

            self.ui_content_stacks[i].setCurrentIndex(1)

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
                    self.update_bar_style(i, is_finished=True)
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

        # Created before SimulationPage: SimulationPage's constructor calls
        # sync_ui() internally, which fires on_data_point -> record_history,
        # and record_history refreshes iso_page - so iso_page must already
        # exist by then.
        self.stats_page = StatsPage(
            station_ptr, on_back=self.show_simulation_page,
            history_load=self.history_load, history_revenue=self.history_revenue,
        )
        self.iso_page = IsoPage(station_ptr, on_back=self.show_simulation_page)

        self.simulation_page = SimulationPage(
            station_ptr, on_open_stats=self.show_stats_page, on_open_iso=self.show_iso_page,
            on_data_point=self.record_history,
        )

        # All pages are wrapped in a QScrollArea: if a window gets resized
        # small (or a page's content is simply taller than the available
        # space), it scrolls instead of squeezing/overlapping its widgets.
        sim_scroll = QScrollArea()
        sim_scroll.setWidgetResizable(True)
        sim_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sim_scroll.setWidget(self.simulation_page)

        stats_scroll = QScrollArea()
        stats_scroll.setWidgetResizable(True)
        stats_scroll.setFrameShape(QFrame.Shape.NoFrame)
        stats_scroll.setWidget(self.stats_page)

        iso_scroll = QScrollArea()
        iso_scroll.setWidgetResizable(True)
        iso_scroll.setFrameShape(QFrame.Shape.NoFrame)
        iso_scroll.setWidget(self.iso_page)

        self.stack.addWidget(sim_scroll)     # index 0
        self.stack.addWidget(stats_scroll)   # index 1
        self.stack.addWidget(iso_scroll)     # index 2
        self.stack.setCurrentIndex(0)

    def record_history(self, elapsed_minutes, grid_load_kw, lifetime_revenue):
        self.history_load.append((elapsed_minutes, grid_load_kw))
        self.history_revenue.append((elapsed_minutes, lifetime_revenue))
        if len(self.history_load) > self.history_cap:
            self.history_load.pop(0)
            self.history_revenue.pop(0)
        self.iso_page.refresh()

    def show_stats_page(self):
        self.stats_page.refresh()
        self.stack.setCurrentIndex(1)

    def show_iso_page(self):
        self.iso_page.refresh()
        self.stack.setCurrentIndex(2)

    def show_simulation_page(self):
        self.simulation_page.sync_ui()
        self.stack.setCurrentIndex(0)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GridFlowApp(my_station_ptr)
    window.show()
    sys.exit(app.exec())