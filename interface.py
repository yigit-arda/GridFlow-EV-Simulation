import ctypes
import os
import sys
import random
import math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QWidget, QProgressBar, QLineEdit, QFrame, QComboBox, QStackedWidget,
    QScrollArea
)
from PyQt6.QtGui import (
    QIntValidator, QDoubleValidator, QPainter, QPen, QColor, QFont,
    QLinearGradient, QRadialGradient, QPainterPath, QBrush, QPolygonF
)
from PyQt6.QtCore import Qt, QPointF, QTimer

dll_path = os.path.abspath('./gridflow.dll')
gridflow_lib = ctypes.CDLL(dll_path)

# --- C Function Signatures ---
gridflow_lib.initStation.argtypes = [ctypes.c_float, ctypes.c_int]
gridflow_lib.initStation.restype = ctypes.c_void_p
gridflow_lib.createVehicle.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_int]
gridflow_lib.createVehicle.restype = ctypes.c_void_p
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

AC_POWER_CHOICES = [3.7, 7.4, 11.0, 22.0, 43.0]
DC_POWER_CHOICES = [50.0, 100.0, 120.0, 150.0, 180.0]
PRIORITY_LABELS = {"High (1)": 1, "Normal (3)": 3, "Low (5)": 5}
LOW_BATTERY_THRESHOLD = 20.0

AC_COLOR = "#0ea5e9" 
DC_COLOR = "#10b981" 

my_station_ptr = gridflow_lib.initStation(500.0, 4)

DARK_STYLESHEET = """
    QMainWindow, QWidget#Page { background-color: #0f172a; }
    QScrollArea { background-color: #0f172a; border: none; }
    QScrollArea > QWidget > QWidget { background-color: #0f172a; }
    QLabel { color: #f8fafc; font-family: 'Segoe UI'; }
    QPushButton {
        background-color: #3b82f6; color: white; padding: 10px;
        border-radius: 6px; font-weight: bold; font-family: 'Segoe UI'; border: none;
    }
    QPushButton:hover { background-color: #2563eb; }
    QPushButton:disabled { background-color: #334155; color: #94a3b8; }
    QLineEdit, QComboBox {
        background-color: #1e293b; color: #f8fafc; padding: 8px;
        border: 1px solid #334155; border-radius: 6px; font-size: 14px;
    }
    QFrame#Card, QFrame#StatRow {
        background-color: #1e293b; border: 1px solid #334155; border-radius: 10px;
    }
    QFrame#StatCard {
        background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px;
    }
"""

class LineChartWidget(QWidget):
    def __init__(self, title, color="#10b981", unit=""):
        super().__init__()
        self.title = title
        self.line_color = QColor(color)
        self.unit = unit
        self.points = []
        self.setMinimumHeight(210)

    def set_data(self, points):
        self.points = points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#0f172a"))

        painter.setPen(QColor("#f8fafc"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(12, 22, self.title)

        if len(self.points) < 2:
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(w // 2 - 70, h // 2, "Not enough data yet")
            painter.end()
            return

        margin_left, margin_right, margin_top, margin_bottom = 50, 15, 34, 22
        plot_w = max(1, w - margin_left - margin_right)
        plot_h = max(1, h - margin_top - margin_bottom)

        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(0.0, min(ys)), max(ys)
        if x_max == x_min: x_max = x_min + 1
        if y_max == y_min: y_max = y_min + 1

        def to_screen(px, py):
            sx = margin_left + (px - x_min) / (x_max - x_min) * plot_w
            sy = margin_top + (1 - (py - y_min) / (y_max - y_min)) * plot_h
            return QPointF(sx, sy)

        for i in range(4):
            frac = i / 3
            y_val = y_min + frac * (y_max - y_min)
            sy = margin_top + (1 - frac) * plot_h
            painter.setPen(QColor("#1e293b"))
            painter.drawLine(int(margin_left), int(sy), int(w - margin_right), int(sy))
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(4, int(sy) + 4, f"{y_val:.0f}")

        baseline_y = to_screen(x_min, y_min).y()
        area_path = QPainterPath()
        first_pt = to_screen(self.points[0][0], self.points[0][1])
        area_path.moveTo(first_pt.x(), baseline_y)
        area_path.lineTo(first_pt)
        for px, py in self.points[1:]: area_path.lineTo(to_screen(px, py))
        last_pt = to_screen(self.points[-1][0], self.points[-1][1])
        last_y = self.points[-1][1]
        area_path.lineTo(last_pt.x(), baseline_y)
        area_path.closeSubpath()

        gradient = QLinearGradient(0, margin_top, 0, margin_top + plot_h)
        top_color, bottom_color = QColor(self.line_color), QColor(self.line_color)
        top_color.setAlpha(130); bottom_color.setAlpha(0)
        gradient.setColorAt(0.0, top_color); gradient.setColorAt(1.0, bottom_color)
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QBrush(gradient)); painter.drawPath(area_path)

        line_path = QPainterPath(); line_path.moveTo(first_pt)
        for px, py in self.points[1:]: line_path.lineTo(to_screen(px, py))
        pen = QPen(self.line_color); pen.setWidth(3); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin); pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(pen); painter.drawPath(line_path)

        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor("#0f172a")); painter.drawEllipse(last_pt, 6, 6)
        painter.setBrush(self.line_color); painter.drawEllipse(last_pt, 4, 4)

        badge_text = f"{last_y:.1f} {self.unit}"
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        text_w = painter.fontMetrics().horizontalAdvance(badge_text)
        badge_x, badge_y = w - margin_right - text_w - 16, margin_top - 26
        painter.setBrush(QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 45))
        painter.drawRoundedRect(badge_x, badge_y, text_w + 16, 20, 8, 8)
        painter.setPen(QColor("#ffffff")); painter.drawText(badge_x + 8, badge_y + 14, badge_text)
        painter.end()


class StatsPage(QWidget):
    def __init__(self, station_ptr, on_back, history_load, history_revenue):
        super().__init__()
        self.station_ptr = station_ptr
        self.history_load = history_load
        self.history_revenue = history_revenue
        self.setObjectName("Page")

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30); layout.setSpacing(14)

        top_row = QHBoxLayout()
        btn_back = QPushButton("\u2190 Back to Simulation")
        btn_back.setStyleSheet("background-color: #334155; color: white;")
        btn_back.clicked.connect(on_back)
        top_row.addWidget(btn_back); top_row.addStretch(); layout.addLayout(top_row)

        title = QLabel("\U0001F4CA Station Revenue & Statistics")
        title.setStyleSheet("font-size: 24px; font-weight: bold;"); layout.addWidget(title)

        tiles_grid = QGridLayout(); tiles_grid.setSpacing(12)
        self.row_charge = self._build_tile(tiles_grid, 0, 0, "\u26A1 Charging Revenue", "\u20ba0.0")
        self.row_penalty = self._build_tile(tiles_grid, 0, 1, "\u23F3 Penalty Revenue", "\u20ba0.0")
        self.row_total = self._build_tile(tiles_grid, 0, 2, "\U0001F4B0 Total Lifetime Revenue", "\u20ba0.0")
        self.row_pending = self._build_tile(tiles_grid, 1, 0, "\U0001F50C Currently Pending", "\u20ba0.0")
        self.row_sessions = self._build_tile(tiles_grid, 1, 1, "\U0001F697 Vehicles Served", "0")
        layout.addLayout(tiles_grid)

        layout.addWidget(QLabel("\U0001F4C8 Over Time", styleSheet="font-size: 16px; font-weight: bold; margin-top: 10px;"))
        
        load_card = QFrame(); load_card.setObjectName("Card"); load_card_layout = QVBoxLayout()
        self.load_chart = LineChartWidget("Grid Load", color="#0ea5e9", unit="kW")
        load_card_layout.addWidget(self.load_chart); load_card.setLayout(load_card_layout); layout.addWidget(load_card)

        revenue_card = QFrame(); revenue_card.setObjectName("Card"); revenue_card_layout = QVBoxLayout()
        self.revenue_chart = LineChartWidget("Lifetime Revenue", color="#10b981", unit="\u20ba")
        revenue_card_layout.addWidget(self.revenue_chart); revenue_card.setLayout(revenue_card_layout); layout.addWidget(revenue_card)

        layout.addStretch(); self.setLayout(layout)

    def _build_tile(self, grid_layout, row, col, title, initial_value):
        frame = QFrame(); frame.setObjectName("StatCard")
        layout = QVBoxLayout(); layout.setContentsMargins(15, 10, 15, 10)
        lbl_title = QLabel(title); lbl_title.setStyleSheet("font-size: 12px; color: #94a3b8;")
        lbl_value = QLabel(initial_value); lbl_value.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8fafc;")
        layout.addWidget(lbl_title); layout.addWidget(lbl_value); frame.setLayout(layout); grid_layout.addWidget(frame, row, col)
        return lbl_value

    def refresh(self):
        charge_rev = gridflow_lib.getLifetimeChargeRevenue(self.station_ptr)
        penalty_rev = gridflow_lib.getLifetimePenaltyRevenue(self.station_ptr)
        self.row_charge.setText(f"\u20ba{charge_rev:.1f}")
        self.row_penalty.setText(f"\u20ba{penalty_rev:.1f}")
        self.row_total.setText(f"\u20ba{(charge_rev + penalty_rev):.1f}")
        self.row_sessions.setText(str(gridflow_lib.getLifetimeSessionCount(self.station_ptr)))
        
        pending = sum(gridflow_lib.getChargeCost(self.station_ptr, i + 1) + gridflow_lib.getIdleFee(self.station_ptr, i + 1) 
                      for i in range(4) if gridflow_lib.isSocketFull(self.station_ptr, i + 1))
        self.row_pending.setText(f"\u20ba{pending:.1f}")

        self.load_chart.set_data(self.history_load)
        self.revenue_chart.set_data(self.history_revenue)


class IsoCanvas(QWidget):
    CANVAS_W, CANVAS_H = 1200, 700
    ORIGIN_X, ORIGIN_Y = 560, 180 
    STATUS_COLOR = {"CHARGING": "#10b981", "FINISHED": "#eab308", "PENALTY": "#ef4444"}
    STATUS_TEXT = {"CHARGING": "CHARGING", "FINISHED": "FINISHED (100%)", "PENALTY": "IDLE PENALTY"}
    BAY_POSITIONS = [(0, 0), (1, 0), (0, 1), (1, 1)] 

    def __init__(self, station_ptr):
        super().__init__()
        self.station_ptr = station_ptr
        self.bays = [{"type": "AC", "status": "EMPTY"} for _ in range(4)]
        self.queue = []
        self.grid_load = 0.0
        self.max_cap = 500.0
        self.clock_str = "--:--"
        self.night_factor = 0.0 # 0.0: Gündüz, 1.0: Gece
        self.setMinimumHeight(550)
        
        # Animasyon Motoru
        self.anim_phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_frame)
        self.timer.start(35)
        self.refresh()

    def animate_frame(self):
        self.anim_phase += 1.5
        if self.anim_phase > 100:
            self.anim_phase -= 100
        self.update()

    def refresh(self):
        bays = []
        for i in range(4):
            socket_id = i + 1
            charge_type = gridflow_lib.getSocketChargeType(self.station_ptr, socket_id)
            type_name = "AC" if charge_type == AC_TYPE2 else "DC"
            if not gridflow_lib.isSocketFull(self.station_ptr, socket_id):
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
        for idx in range(min(qsize, 6)):
            p = gridflow_lib.getQueuePlateAt(self.station_ptr, idx)
            plate = p.decode('utf-8') if p else "?"
            wait = gridflow_lib.getQueueEstimatedWaitMinutes(self.station_ptr, idx)
            wait_str = f"ETA: ~{wait} min" if wait >= 0 else "ETA: unknown"
            queue.append({"plate": plate, "wait": wait_str})
        self.queue = queue

        self.grid_load = gridflow_lib.getTotalPower(self.station_ptr)
        self.max_cap = gridflow_lib.getMaxCapacity(self.station_ptr)
        clock_min = gridflow_lib.getStationClock(self.station_ptr)
        self.clock_str = f"{(clock_min // 60) % 24:02d}:{clock_min % 60:02d}"

        # Gece Gündüz Döngüsü Hesaplaması (Saat 14:00 tam gündüz, 02:00 tam gece)
        hour = (clock_min / 60.0) % 24
        self.night_factor = (math.cos((hour - 2) * math.pi / 12) + 1) / 2

    # --- 2.5D İzometrik Dönüşüm ---
    def _projected(self, painter, cx, cy, draw_func):
        painter.save()
        painter.translate(cx, cy)
        painter.scale(1.0, 0.5) 
        painter.rotate(45)      
        draw_func(painter)      
        painter.restore()

    def _tile_pos(self, col, row):
        spacing = 220 
        x = self.ORIGIN_X + (col - row) * spacing
        y = self.ORIGIN_Y + (col + row) * (spacing * 0.5)
        return x, y

    def _blend_colors(self, c1, c2, factor):
        r = int(c1.red() + (c2.red() - c1.red()) * factor)
        g = int(c1.green() + (c2.green() - c1.green()) * factor)
        b = int(c1.blue() + (c2.blue() - c1.blue()) * factor)
        return QColor(r, g, b)

    def _draw_asphalt(self, painter):
        # Asfalt Rengini Gece Moduna Göre Karart
        base_asphalt = QColor("#1e293b")
        night_asphalt = QColor("#020617")
        current_asphalt = self._blend_colors(base_asphalt, night_asphalt, self.night_factor)
        
        base_lines = QColor("#334155")
        night_lines = QColor("#0f172a")
        current_lines = self._blend_colors(base_lines, night_lines, self.night_factor)

        def draw_bg(p):
            p.setPen(QPen(QColor("#0f172a"), 6))
            p.setBrush(current_asphalt)
            p.drawRoundedRect(-400, -400, 800, 800, 40, 40)
            
            p.setPen(QPen(current_lines, 2, Qt.PenStyle.DashLine))
            for i in range(-300, 400, 200):
                p.drawLine(i, -350, i, 350)
                p.drawLine(-350, i, 350, i)
        self._projected(painter, self.ORIGIN_X, self.ORIGIN_Y + 110, draw_bg)

    def _floor_diamond(self, painter, cx, cy, is_empty):
        def draw_bay(p):
            p.setPen(QPen(QColor("#10b981") if not is_empty else QColor("#475569"), 3))
            p.setBrush(QColor(15, 23, 42, int(150 + 105 * self.night_factor))) # Gece platform daha karanlık olur
            p.drawRoundedRect(-90, -90, 180, 180, 16, 16)
        self._projected(painter, cx, cy, draw_bay)

    def _draw_glow(self, painter, cx, cy, color):
        # Araç şarj olurken altında yanıp sönen İzometrik LED Işığı (Glow)
        pulse = (math.sin(self.anim_phase / 5.0) + 1) / 2 # 0.0 to 1.0 arası nabız
        glow_radius = 80 + 20 * pulse
        
        grad = QRadialGradient(cx, cy, glow_radius)
        grad.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), int(60 + 40 * pulse)))
        grad.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        
        # İzometrik düzleme oturtmak için basık elips çiziyoruz
        painter.drawEllipse(QPointF(cx, cy), glow_radius, glow_radius * 0.5)

    def _draw_projected_car(self, painter, cx, cy, color, is_empty=False):
        def draw_car(p):
            # Araç Gölgesi
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, int(110 + 80 * self.night_factor))) # Gece gölge koyulaşır
            p.drawRoundedRect(-28, -48, 56, 96, 16, 16)
            
            # Farların Yere Vuran Işığı (Sadece gece ve araba varsa yanar)
            if not is_empty and self.night_factor > 0.2:
                beam_grad = QLinearGradient(0, -40, 0, -180)
                beam_grad.setColorAt(0.0, QColor(255, 255, 200, int(180 * self.night_factor)))
                beam_grad.setColorAt(1.0, QColor(255, 255, 200, 0))
                p.setBrush(beam_grad)
                p.drawPolygon(QPolygonF([QPointF(-16, -42), QPointF(16, -42), QPointF(50, -180), QPointF(-50, -180)]))
            
            # Tekerlekler
            p.setBrush(QColor("#020617"))
            p.drawRoundedRect(-28, -28, 8, 18, 4, 4) 
            p.drawRoundedRect(20, -28, 8, 18, 4, 4)  
            p.drawRoundedRect(-28, 18, 8, 18, 4, 4)  
            p.drawRoundedRect(20, 18, 8, 18, 4, 4)   
            
            # Ana Gövde 
            body_grad = QLinearGradient(-24, -44, 24, 44)
            base_c = QColor(color)
            body_grad.setColorAt(0.0, base_c.lighter(140)) 
            body_grad.setColorAt(1.0, base_c.darker(140))  
            p.setPen(QPen(QColor("#0f172a"), 2))
            p.setBrush(QBrush(body_grad))
            p.drawRoundedRect(-24, -44, 48, 88, 14, 14)
            
            # Tavan / Kabin
            roof_grad = QLinearGradient(-16, -20, 16, 20)
            roof_grad.setColorAt(0.0, QColor("#1e293b"))
            roof_grad.setColorAt(1.0, QColor("#0f172a"))
            p.setBrush(QBrush(roof_grad))
            p.drawRoundedRect(-18, -15, 36, 45, 10, 10)
            
            # Ön Cam
            p.setBrush(QColor("#38bdf8")) 
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(QPointF(-16, -15), QPointF(16, -15), QPointF(13, -28), QPointF(-13, -28))
            
            # Arka Cam
            p.drawPolygon(QPointF(-16, 30), QPointF(16, 30), QPointF(13, 38), QPointF(-13, 38))
            
            # Farlar 
            p.setBrush(QColor("#fef08a") if self.night_factor > 0.2 else QColor("#cbd5e1"))
            p.drawRoundedRect(-18, -42, 10, 6, 3, 3)
            p.drawRoundedRect(8, -42, 10, 6, 3, 3)
            
            # Ön Panjur
            p.setBrush(QColor("#020617"))
            p.drawRoundedRect(-6, -43, 12, 4, 2, 2)
            
            # Stop Lambaları
            p.setBrush(QColor("#ef4444"))
            p.drawRoundedRect(-18, 38, 12, 5, 2, 2)
            p.drawRoundedRect(6, 38, 12, 5, 2, 2)

        self._projected(painter, cx, cy - 14, draw_car)

    def _draw_hologram_battery(self, painter, cx, cy, soc, type_color):
        # Havada süzülen 3D Holografik Şarj Göstergesi
        # Hafifçe yukarı aşağı süzülme animasyonu
        float_offset = math.sin(self.anim_phase / 8.0) * 5
        base_y = cy - 80 + float_offset
        bar_w, bar_h = 16, 50
        
        # Dış Şeffaf Hologram Camı
        def draw_glass(p):
            p.setPen(QPen(type_color, 1.5))
            p.setBrush(QColor(type_color.red(), type_color.green(), type_color.blue(), 20))
            p.drawRoundedRect(-bar_w, -bar_h, bar_w*2, bar_h*2, 4, 4)
        
        # İç Doluluk Hacmi
        def draw_fill(p):
            p.setPen(Qt.PenStyle.NoPen)
            fill_color = QColor("#ef4444") if soc < LOW_BATTERY_THRESHOLD else type_color
            p.setBrush(fill_color)
            fill_height = max(2, (bar_h * 2) * (soc / 100.0))
            p.drawRoundedRect(-bar_w + 2, int(bar_h - fill_height + 2), bar_w*2 - 4, int(fill_height - 4), 2, 2)

        self._projected(painter, cx, base_y, draw_glass)
        self._projected(painter, cx, base_y, draw_fill)

    def _iso_box_pole(self, painter, cx, cy, hw, hd, h, base_color):
        top_c, left_c, right_c = base_color.lighter(130), base_color.darker(115), base_color.darker(145)
        b_right, b_bottom, b_left = QPointF(cx + hw, cy), QPointF(cx, cy + hd), QPointF(cx - hw, cy)
        t_top, t_right = QPointF(cx, cy - hd - h), QPointF(cx + hw, cy - h)
        t_bottom, t_left = QPointF(cx, cy + hd - h), QPointF(cx - hw, cy - h)

        painter.setPen(QPen(QColor(0, 0, 0, 90), 1))
        painter.setBrush(QBrush(right_c)); painter.drawPolygon(QPolygonF([b_right, b_bottom, t_bottom, t_right]))
        painter.setBrush(QBrush(left_c));  painter.drawPolygon(QPolygonF([b_left, b_bottom, t_bottom, t_left]))
        painter.setBrush(QBrush(top_c));   painter.drawPolygon(QPolygonF([t_top, t_right, t_bottom, t_left]))

    def _text_center(self, painter, x, y, s, font, color, bg=True):
        painter.setFont(font)
        fm = painter.fontMetrics()
        w, h = fm.horizontalAdvance(s), fm.height()
        if bg:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(15, 23, 42, 210)) 
            painter.drawRoundedRect(int(x - w / 2 - 8), int(y - h + 3), int(w + 16), int(h + 4), 6, 6)
        painter.setPen(QColor(color))
        painter.drawText(int(x - w / 2), int(y), s)

    def _draw_bay_objects(self, painter, col, row, socket_id, data):
        cx, cy = self._tile_pos(col, row)
        type_name, status = data["type"], data["status"]
        type_color = QColor(AC_COLOR if type_name == "AC" else DC_COLOR)
        
        pole_x, pole_y = cx, cy - 45
        
        # Dinamik Glow Efekti (Arabanın altına çizilir)
        if status == "CHARGING":
            self._draw_glow(painter, cx, cy, type_color)

        # Direk Çizimi
        pole_color = QColor("#334155") if status == "EMPTY" else type_color
        self._iso_box_pole(painter, pole_x, pole_y, 6, 6, 50, pole_color)

        if status != "EMPTY":
            status_color = QColor(self.STATUS_COLOR.get(status, "#888888"))
            
            # Hareketli Kablo Fiziği 
            cable_pen = QPen(type_color, 4, Qt.PenStyle.DashLine)
            if status == "CHARGING":
                cable_pen.setDashOffset(-self.anim_phase) 
            else:
                cable_pen.setStyle(Qt.PenStyle.SolidLine)
                cable_pen.setColor(QColor("#475569")) 
                
            painter.setPen(cable_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            p1 = QPointF(pole_x, pole_y - 60) 
            p2 = QPointF(cx, cy - 10)         
            
            path = QPainterPath()
            path.moveTo(p1)
            path.quadTo(QPointF((p1.x()+p2.x())/2, max(p1.y(), p2.y()) + 40), p2) 
            painter.drawPath(path)
            
            # Gelişmiş 3D SUV Araç
            self._draw_projected_car(painter, cx, cy, status_color)

            # Holografik 3D Batarya Barı
            soc = data.get("soc", 0.0)
            self._draw_hologram_battery(painter, cx, cy, soc, type_color)

    def _draw_bay_labels(self, painter, col, row, socket_id, data):
        cx, cy = self._tile_pos(col, row)
        type_name, status = data["type"], data["status"]
        label_y = cy + 50
        
        self._text_center(painter, cx, label_y, f"Socket {socket_id} | {type_name}", QFont("Segoe UI", 11, QFont.Weight.Bold), "#ffffff")
        if status == "EMPTY":
            self._text_center(painter, cx, label_y + 20, "EMPTY", QFont("Segoe UI", 9), "#94a3b8")
        else:
            self._text_center(painter, cx, label_y + 20, f"{data.get('plate', '?')}  |  SOC {data.get('soc', 0):.0f}%", QFont("Segoe UI", 9), "#cbd5e1")
            self._text_center(painter, cx, label_y + 40, self.STATUS_TEXT[status], QFont("Segoe UI", 9, QFont.Weight.Bold), self.STATUS_COLOR[status])

    def _draw_overlays(self, painter):
        # Saat Paneli 
        self._text_center(painter, 160, 100, "SIMULATED CLOCK", QFont("Segoe UI", 10, QFont.Weight.Bold), "#94a3b8", bg=False)
        self._text_center(painter, 160, 140, self.clock_str, QFont("Segoe UI", 34, QFont.Weight.Bold), "#f8fafc", bg=False)

        # Güç Paneli 
        cx, cy, r = 160, 480, 90
        bg_path = QPainterPath()
        bg_path.arcMoveTo(cx - r, cy - r, r * 2, r * 2, 180)
        bg_path.arcTo(cx - r, cy - r, r * 2, r * 2, 180, 180)
        bg_pen = QPen(QColor("#1e293b"), 18); bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen); painter.setBrush(Qt.BrushStyle.NoBrush); painter.drawPath(bg_path)

        frac = min(1.0, self.grid_load / self.max_cap) if self.max_cap > 0 else 0.0
        if frac > 0:
            fg_path = QPainterPath()
            fg_path.arcMoveTo(cx - r, cy - r, r * 2, r * 2, 180)
            fg_path.arcTo(cx - r, cy - r, r * 2, r * 2, 180, frac * 180)
            fg_color = "#ef4444" if frac > 0.85 else "#0ea5e9"
            fg_pen = QPen(QColor(fg_color), 18); fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(fg_pen); painter.drawPath(fg_path)
        
        self._text_center(painter, cx, cy - 10, "GRID LOAD", QFont("Segoe UI", 9, QFont.Weight.Bold), "#94a3b8", bg=False)
        self._text_center(painter, cx, cy + 24, f"{self.grid_load:.0f} / {self.max_cap:.0f} kW", QFont("Segoe UI", 14, QFont.Weight.Bold), "#f8fafc", bg=False)

        # Kuyruk Paneli 
        start_x, start_y = 1000, 140
        self._text_center(painter, start_x + 30, start_y - 40, f"WAITING QUEUE ({len(self.queue)})", QFont("Segoe UI", 10, QFont.Weight.Bold), "#94a3b8", bg=False)
        for idx, item in enumerate(self.queue):
            cx_q, cy_q = start_x - 30, start_y + idx * 85
            # Kuyruktaki arabalar gündüzleri görünür olması için far efekti pasif şekilde çizilir
            self._draw_projected_car(painter, cx_q, cy_q, "#64748b", is_empty=True) 
            
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            painter.setPen(QColor("#f8fafc")); painter.drawText(int(cx_q + 55), int(cy_q - 5), item["plate"])
            
            painter.setFont(QFont("Segoe UI", 10))
            painter.setPen(QColor("#eab308")); painter.drawText(int(cx_q + 55), int(cy_q + 15), item["wait"])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0f172a"))

        scale = min(self.width() / self.CANVAS_W, self.height() / self.CANVAS_H)
        if scale <= 0: return
        painter.translate((self.width() - self.CANVAS_W * scale) / 2, (self.height() - self.CANVAS_H * scale) / 2)
        painter.scale(scale, scale)

        # Z-INDEX DÜZELTMESİ (Arkadan Öne Çizim)
        self._draw_asphalt(painter) 
        for i, bay in enumerate(self.bays): 
            col, row = self.BAY_POSITIONS[i]
            self._floor_diamond(painter, *self._tile_pos(col, row), bay["status"] == "EMPTY")
            
        for i, bay in enumerate(self.bays): 
            col, row = self.BAY_POSITIONS[i]
            self._draw_bay_objects(painter, col, row, i + 1, bay)
            
        for i, bay in enumerate(self.bays): 
            col, row = self.BAY_POSITIONS[i]
            self._draw_bay_labels(painter, col, row, i + 1, bay)

        self._draw_overlays(painter) 
        painter.end()


class IsoPage(QWidget):
    def __init__(self, station_ptr, on_back):
        super().__init__()
        self.setObjectName("Page")
        layout = QVBoxLayout(); layout.setContentsMargins(30, 20, 30, 20); layout.setSpacing(10)

        top_row = QHBoxLayout()
        btn_back = QPushButton("\u2190 Back to Simulation")
        btn_back.setStyleSheet("background-color: #334155; color: white;")
        btn_back.clicked.connect(on_back)
        top_row.addWidget(btn_back)
        
        title = QLabel("Isometric Station View")
        title.setStyleSheet("font-size: 24px; font-weight: 900; color: #f8fafc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(title, 1) 
        
        dummy = QWidget(); dummy.setFixedWidth(180) 
        top_row.addWidget(dummy)
        
        layout.addLayout(top_row)
        
        self.canvas = IsoCanvas(station_ptr)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def refresh(self):
        self.canvas.refresh()


class SimulationPage(QWidget):
    def __init__(self, station_ptr, on_open_stats, on_open_iso=None, on_data_point=None):
        super().__init__()
        self.station_ptr = station_ptr
        self.total_sockets = 4
        self.on_data_point = on_data_point
        self.setObjectName("Page")

        main_layout = QVBoxLayout(); main_layout.setContentsMargins(20, 20, 20, 20)

        header_row = QHBoxLayout()
        title_label = QLabel("\u26A1 GridFlow Charging Station"); title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_row.addWidget(title_label); header_row.addStretch()

        if on_open_iso:
            btn_iso = QPushButton("\U0001F3D7\uFE0F 3D View"); btn_iso.setStyleSheet("background-color: #0d9488;")
            btn_iso.clicked.connect(on_open_iso); header_row.addWidget(btn_iso)

        btn_stats = QPushButton("\U0001F4CA Statistics"); btn_stats.setStyleSheet("background-color: #7c3aed;")
        btn_stats.clicked.connect(on_open_stats); header_row.addWidget(btn_stats)
        main_layout.addLayout(header_row); main_layout.addSpacing(10)

        stats_row = QHBoxLayout(); stats_row.setSpacing(15)
        self.clock_label = self._build_stat_card(stats_row, "\U0001F553 Simulated Clock", "--:--")
        self.grid_load_label = self._build_stat_card(stats_row, "\U0001F50C Grid Load", "0 / 0 kW")
        self.active_label = self._build_stat_card(stats_row, "\U0001F697 Active Sessions", "0 / 4")
        main_layout.addLayout(stats_row); main_layout.addSpacing(10)

        self.info_label = QLabel("Simulation ready. Add a vehicle to start.")
        self.info_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #10b981;"); self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.info_label); main_layout.addSpacing(10)

        self.cards_layout = QGridLayout(); self.cards_layout.setSpacing(20)
        self.ui_status_labels, self.ui_content_stacks, self.ui_plate_labels = [], [], []
        self.ui_soc_labels, self.ui_power_labels, self.ui_cost_labels = [], [], []
        self.ui_progress_bars, self.ui_unplug_btns = [], []

        for i in range(self.total_sockets):
            socket_id = i + 1
            card = QFrame(); card.setObjectName("Card")
            card_layout = QVBoxLayout(); card_layout.setContentsMargins(20, 20, 20, 20)

            charge_type = gridflow_lib.getSocketChargeType(self.station_ptr, socket_id)
            type_icon, type_name = ("\U0001F50C", "AC (Type 2)") if charge_type == AC_TYPE2 else ("\u26A1", "DC (CCS)")
            type_color = AC_COLOR if charge_type == AC_TYPE2 else DC_COLOR

            header_layout = QHBoxLayout()
            lbl_socket = QLabel(f"{type_icon} Socket {socket_id} |"); lbl_socket.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
            lbl_type_name = QLabel(type_name); lbl_type_name.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {type_color};")
            lbl_status = QLabel("\u26AA EMPTY"); lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #94a3b8;")
            self.ui_status_labels.append(lbl_status)
            header_layout.addWidget(lbl_socket); header_layout.addWidget(lbl_type_name); header_layout.addStretch(); header_layout.addWidget(lbl_status)
            card_layout.addLayout(header_layout)

            bar = QProgressBar(); bar.setRange(0, 100); bar.setValue(0); bar.setTextVisible(False); bar.setFixedHeight(12)
            self.ui_progress_bars.append(bar); card_layout.addWidget(bar); card_layout.addSpacing(10)

            content_stack = QStackedWidget(); content_stack.setMinimumHeight(100)
            empty_page = QWidget(); empty_page_layout = QVBoxLayout(); empty_page_layout.setContentsMargins(0, 0, 0, 0)
            lbl_waiting = QLabel("Waiting for connection..."); lbl_waiting.setStyleSheet("font-size: 14px; color: #64748b;")
            empty_page_layout.addWidget(lbl_waiting); empty_page_layout.addStretch(); empty_page.setLayout(empty_page_layout)

            full_page = QWidget(); full_page_layout = QVBoxLayout(); full_page_layout.setContentsMargins(0, 0, 0, 0); full_page_layout.setSpacing(4)
            lbl_plate = QLabel(); lbl_plate.setStyleSheet("font-size: 14px; color: #e2e8f0;"); self.ui_plate_labels.append(lbl_plate)
            lbl_soc = QLabel(); lbl_soc.setStyleSheet("font-size: 14px; color: #e2e8f0;"); self.ui_soc_labels.append(lbl_soc)
            lbl_power = QLabel(); lbl_power.setStyleSheet("font-size: 14px; color: #e2e8f0;"); self.ui_power_labels.append(lbl_power)
            lbl_cost = QLabel(); lbl_cost.setStyleSheet("font-size: 14px; color: #e2e8f0;"); self.ui_cost_labels.append(lbl_cost)
            full_page_layout.addWidget(lbl_plate); full_page_layout.addWidget(lbl_soc); full_page_layout.addWidget(lbl_power); full_page_layout.addWidget(lbl_cost)
            full_page_layout.addStretch(); full_page.setLayout(full_page_layout)

            content_stack.addWidget(empty_page); content_stack.addWidget(full_page)
            self.ui_content_stacks.append(content_stack); card_layout.addWidget(content_stack)

            btn_unplug = QPushButton("Unplug Vehicle"); btn_unplug.setEnabled(False)
            btn_unplug.clicked.connect(lambda checked, sid=socket_id: self.unplug_car(sid))
            self.ui_unplug_btns.append(btn_unplug); card_layout.addWidget(btn_unplug)

            card.setLayout(card_layout); self.cards_layout.addWidget(card, i // 2, i % 2)

        main_layout.addLayout(self.cards_layout); main_layout.addSpacing(15)

        control_layout = QHBoxLayout()
        self.btn_add_ac = QPushButton("+ AC Vehicle (Type 2)"); self.btn_add_ac.setStyleSheet(f"background-color: #0284c7;")
        self.btn_add_ac.clicked.connect(lambda: self.add_random_car(AC_TYPE2))
        self.btn_add_dc = QPushButton("\u26A1 + DC Fast Vehicle (CCS)"); self.btn_add_dc.setStyleSheet(f"background-color: #059669;")
        self.btn_add_dc.clicked.connect(lambda: self.add_random_car(DC_CCS))

        self.priority_combo = QComboBox(); self.priority_combo.addItems(list(PRIORITY_LABELS.keys())); self.priority_combo.setCurrentText("Normal (3)")
        self.time_input = QLineEdit(); self.time_input.setPlaceholderText("Minutes"); self.time_input.setValidator(QIntValidator(1, 1440)); self.time_input.setFixedWidth(80)
        
        self.btn_advance = QPushButton("\u23E9 Advance Time"); self.btn_advance.setStyleSheet("background-color: #475569;")
        self.btn_advance.clicked.connect(self.advance_system_time)

        control_layout.addWidget(self.btn_add_ac); control_layout.addWidget(self.btn_add_dc)
        control_layout.addWidget(QLabel("Priority:")); control_layout.addWidget(self.priority_combo); control_layout.addStretch()
        control_layout.addWidget(QLabel("Simulation Step (min):")); control_layout.addWidget(self.time_input); control_layout.addWidget(self.btn_advance)
        main_layout.addLayout(control_layout); main_layout.addSpacing(15)

        manual_frame = QFrame(); manual_frame.setObjectName("Card"); manual_outer = QVBoxLayout()
        manual_outer.addWidget(QLabel("Manual Vehicle Entry", styleSheet="font-size: 14px; font-weight: bold; color: #38bdf8;"))
        manual_row1 = QHBoxLayout()
        self.manual_plate_input = QLineEdit(); self.manual_plate_input.setPlaceholderText("Plate (optional)"); self.manual_plate_input.setFixedWidth(130)
        self.manual_type_combo = QComboBox(); self.manual_type_combo.addItems(["AC (Type 2)", "DC (CCS)"]); self.manual_type_combo.setFixedWidth(120)
        self.manual_start_input = QLineEdit(); self.manual_start_input.setPlaceholderText("Start SOC %"); self.manual_start_input.setValidator(QDoubleValidator(0.0, 99.0, 1)); self.manual_start_input.setFixedWidth(85)
        self.manual_target_input = QLineEdit(); self.manual_target_input.setPlaceholderText("Target SOC %"); self.manual_target_input.setValidator(QDoubleValidator(1.0, 100.0, 1)); self.manual_target_input.setFixedWidth(85)
        manual_row1.addWidget(self.manual_plate_input); manual_row1.addWidget(self.manual_type_combo); manual_row1.addWidget(self.manual_start_input); manual_row1.addWidget(self.manual_target_input); manual_row1.addStretch()
        manual_outer.addLayout(manual_row1)

        manual_row2 = QHBoxLayout()
        self.manual_power_input = QLineEdit(); self.manual_power_input.setPlaceholderText("Max Power kW"); self.manual_power_input.setValidator(QDoubleValidator(0.1, 400.0, 1)); self.manual_power_input.setFixedWidth(100)
        self.btn_add_manual = QPushButton("Add Custom Vehicle"); self.btn_add_manual.setStyleSheet("background-color: #7c3aed;"); self.btn_add_manual.clicked.connect(self.add_manual_car)
        manual_row2.addWidget(self.manual_power_input); manual_row2.addWidget(self.btn_add_manual); manual_row2.addSpacing(10)
        manual_row2.addWidget(QLabel("Leave plate empty for an auto-generated one.", styleSheet="font-size: 11px; color: #94a3b8;"))
        manual_row2.addStretch(); manual_outer.addLayout(manual_row2)

        manual_frame.setLayout(manual_outer); main_layout.addWidget(manual_frame)
        self.setLayout(main_layout)
        self.sync_ui()

    def _build_stat_card(self, parent_layout, title, initial_value):
        frame = QFrame(); frame.setObjectName("StatCard"); layout = QVBoxLayout(); layout.setContentsMargins(15, 10, 15, 10)
        lbl_title = QLabel(title); lbl_title.setStyleSheet("font-size: 12px; color: #94a3b8;")
        lbl_value = QLabel(initial_value); lbl_value.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8fafc;")
        layout.addWidget(lbl_title); layout.addWidget(lbl_value); frame.setLayout(layout); parent_layout.addWidget(frame)
        return lbl_value

    def update_bar_style(self, idx, is_empty=False, is_penalty=False):
        bar = self.ui_progress_bars[idx]
        if is_empty: bar.setStyleSheet("QProgressBar { background-color: #1e293b; border-radius: 6px; } QProgressBar::chunk { background-color: transparent; }")
        elif is_penalty: bar.setStyleSheet("QProgressBar { background-color: #1e293b; border-radius: 6px; } QProgressBar::chunk { background-color: #ef4444; border-radius: 6px; }")
        else: bar.setStyleSheet("QProgressBar { background-color: #1e293b; border-radius: 6px; } QProgressBar::chunk { background-color: #10b981; border-radius: 6px; }")

    def add_random_car(self, charge_type):
        plate_str = f"06 EV {random.randint(100, 999)}"
        start_soc = float(random.randint(5, 30))
        tgt_soc = float(random.randint(int(start_soc) + 30, 100))
        car_max_pwr = float(random.choice(AC_POWER_CHOICES if charge_type == AC_TYPE2 else DC_POWER_CHOICES))
        prio = PRIORITY_LABELS[self.priority_combo.currentText()]

        car_ptr = gridflow_lib.createVehicle(plate_str.encode('utf-8'), charge_type, start_soc, tgt_soc, car_max_pwr, prio)
        result = gridflow_lib.plugVehicle(self.station_ptr, car_ptr)

        type_name = "AC" if charge_type == AC_TYPE2 else "DC"
        if result > 0: self.info_label.setText(f"\u2705 {plate_str} ({type_name}, {car_max_pwr:.1f} kW) plugged into Socket {result}."); self.info_label.setStyleSheet("color: #10b981; font-size: 15px; font-weight: bold;")
        elif result == 0: self.info_label.setText(f"\u23F3 {plate_str} ({type_name}) added to the waiting queue."); self.info_label.setStyleSheet("color: #eab308; font-size: 15px; font-weight: bold;")
        else: self.info_label.setText("\u274C Error."); self.info_label.setStyleSheet("color: #ef4444; font-size: 15px; font-weight: bold;")
        self.sync_ui()

    def add_manual_car(self):
        plate = self.manual_plate_input.text().strip() or f"06 EV {random.randint(100, 999)}"
        charge_type = AC_TYPE2 if self.manual_type_combo.currentText().startswith("AC") else DC_CCS
        try:
            start_soc, target_soc, power = float(self.manual_start_input.text()), float(self.manual_target_input.text()), float(self.manual_power_input.text())
        except ValueError:
            self.info_label.setText("\u274C Invalid numbers."); self.info_label.setStyleSheet("color: #ef4444; font-size: 15px; font-weight: bold;")
            return
        if not (0.0 <= start_soc < target_soc <= 100.0) or not (0.0 < power <= 400.0):
            self.info_label.setText("\u274C 0 \u2264 Start < Target \u2264 100, Power > 0."); self.info_label.setStyleSheet("color: #ef4444; font-size: 15px; font-weight: bold;")
            return
        
        car_ptr = gridflow_lib.createVehicle(plate.encode('utf-8'), charge_type, start_soc, target_soc, power, PRIORITY_LABELS[self.priority_combo.currentText()])
        gridflow_lib.plugVehicle(self.station_ptr, car_ptr)
        self.sync_ui()

    def unplug_car(self, socket_id):
        gridflow_lib.unplugVehicle(self.station_ptr, socket_id); self.sync_ui()

    def advance_system_time(self):
        if not self.time_input.text(): return
        gridflow_lib.advanceTime(self.station_ptr, int(self.time_input.text()))
        self.sync_ui()

    def sync_ui(self):
        clock_min = gridflow_lib.getStationClock(self.station_ptr)
        self.clock_label.setText(f"{(clock_min // 60) % 24:02d}:{clock_min % 60:02d}")
        
        total_power, max_cap = gridflow_lib.getTotalPower(self.station_ptr), gridflow_lib.getMaxCapacity(self.station_ptr)
        self.grid_load_label.setText(f"{total_power:.1f} / {max_cap:.0f} kW")
        self.grid_load_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {'#ef4444' if max_cap > 0 and total_power / max_cap > 0.85 else '#f8fafc'};")

        active_count = 0
        for i in range(self.total_sockets):
            socket_id = i + 1
            if not gridflow_lib.isSocketFull(self.station_ptr, socket_id):
                self.ui_status_labels[i].setText("\u26AA EMPTY"); self.ui_status_labels[i].setStyleSheet("font-size: 14px; font-weight: bold; color: #64748b;")
                self.ui_progress_bars[i].setValue(0); self.update_bar_style(i, is_empty=True); self.ui_content_stacks[i].setCurrentIndex(0)
                self.ui_unplug_btns[i].setText("\u2014 Empty Socket \u2014"); self.ui_unplug_btns[i].setEnabled(False)
                self.ui_unplug_btns[i].setStyleSheet("background-color: #1e293b; color: #475569; border: 1px solid #334155;")
                continue

            active_count += 1
            plate = (gridflow_lib.getPlateAt(self.station_ptr, socket_id) or b"?").decode('utf-8')
            soc, target = gridflow_lib.getSocketSOC(self.station_ptr, socket_id), gridflow_lib.getTargetSOC(self.station_ptr, socket_id)
            cost, fee = gridflow_lib.getChargeCost(self.station_ptr, socket_id), gridflow_lib.getIdleFee(self.station_ptr, socket_id)
            
            self.ui_unplug_btns[i].setText("Unplug Vehicle"); self.ui_unplug_btns[i].setEnabled(True); self.ui_unplug_btns[i].setStyleSheet("background-color: #ef4444; color: white; font-weight: bold;")
            self.ui_progress_bars[i].setValue(int(soc)); self.ui_content_stacks[i].setCurrentIndex(1)
            self.ui_plate_labels[i].setText(f"\U0001F697 Plate: {plate}")
            self.ui_soc_labels[i].setStyleSheet(f"font-size: 14px; color: {'#ef4444' if soc < LOW_BATTERY_THRESHOLD else '#e2e8f0'};")

            if soc >= target:
                self.ui_soc_labels[i].setText(f"\U0001F50B SOC: {soc:.1f}% (Completed)")
                self.ui_power_labels[i].setText("\u26A1 Active Power: 0.0 kW") 
                if fee > 0:
                    self.ui_status_labels[i].setText("\u23F3 IDLE PENALTY"); self.ui_status_labels[i].setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
                    self.update_bar_style(i, is_penalty=True); self.ui_cost_labels[i].setText(f"\U0001F4B0 Total Bill: \u20ba{(cost + fee):.1f}")
                else:
                    self.ui_status_labels[i].setText("\u2705 FINISHED (Grace)"); self.ui_status_labels[i].setStyleSheet("font-size: 14px; font-weight: bold; color: #eab308;")
                    self.update_bar_style(i); self.ui_cost_labels[i].setText(f"\U0001F4B3 Cost: \u20ba{cost:.1f}")
            else:
                self.ui_status_labels[i].setText("\u26A1 CHARGING"); self.ui_status_labels[i].setStyleSheet("font-size: 14px; font-weight: bold; color: #10b981;")
                self.update_bar_style(i); self.ui_soc_labels[i].setText(f"\U0001F50B SOC: {soc:.1f}% \u2192 {target:.0f}%")
                self.ui_power_labels[i].setText(f"\u26A1 Active Power: {gridflow_lib.getActivePower(self.station_ptr, socket_id):.1f} kW")
                
                finish_min = gridflow_lib.getExpectedFinishReal(self.station_ptr, socket_id)
                self.ui_cost_labels[i].setText(f"\U0001F4B3 Cost: \u20ba{cost:.1f} | ETA: {f'{(finish_min // 60) % 24:02d}:{finish_min % 60:02d}' if finish_min >= 0 else '--:--'}")

        self.active_label.setText(f"{active_count} / {self.total_sockets}")
        if self.on_data_point: self.on_data_point(gridflow_lib.getElapsedMinutes(self.station_ptr), total_power, gridflow_lib.getLifetimeChargeRevenue(self.station_ptr) + gridflow_lib.getLifetimePenaltyRevenue(self.station_ptr))


class GridFlowApp(QMainWindow):
    def __init__(self, station_ptr):
        super().__init__()
        self.station_ptr = station_ptr
        self.history_load, self.history_revenue, self.history_cap = [], [], 300
        self.setWindowTitle("GridFlow - EV Charging Station Control Panel")
        self.setGeometry(100, 100, 1100, 800)
        self.setStyleSheet(DARK_STYLESHEET)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.stats_page = StatsPage(station_ptr, on_back=self.show_simulation_page, history_load=self.history_load, history_revenue=self.history_revenue)
        self.iso_page = IsoPage(station_ptr, on_back=self.show_simulation_page)
        self.simulation_page = SimulationPage(station_ptr, on_open_stats=self.show_stats_page, on_open_iso=self.show_iso_page, on_data_point=self.record_history)

        for p in (self.simulation_page, self.stats_page, self.iso_page):
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame); scroll.setWidget(p)
            self.stack.addWidget(scroll)

    def record_history(self, elapsed_minutes, grid_load_kw, lifetime_revenue):
        self.history_load.append((elapsed_minutes, grid_load_kw))
        self.history_revenue.append((elapsed_minutes, lifetime_revenue))
        if len(self.history_load) > self.history_cap: self.history_load.pop(0); self.history_revenue.pop(0)

    def show_stats_page(self): self.stats_page.refresh(); self.stack.setCurrentIndex(1)
    def show_iso_page(self): self.iso_page.refresh(); self.stack.setCurrentIndex(2)
    def show_simulation_page(self): self.simulation_page.sync_ui(); self.stack.setCurrentIndex(0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GridFlowApp(my_station_ptr)
    window.show()
    sys.exit(app.exec())