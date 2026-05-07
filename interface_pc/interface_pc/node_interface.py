#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import signal
import sys
import time
from typing import Dict

import rclpy
from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Bool, Int16MultiArray, String


MAX_SPEED_PERCENT = 99
STATUS_TIMEOUT = 2.0
AXIS_DEADZONE = 0.12
STOP_COMMAND = 1

MOVEMENT_LABELS = {
    1: 'UP',
    2: 'DOWN',
    3: 'LEFT',
    4: 'RIGHT',
    5: 'UP-RIGHT',
    6: 'DOWN-RIGHT',
    7: 'DOWN-LEFT',
    8: 'UP-LEFT',
    9: 'ROT-LEFT',
    10: 'ROT-RIGHT',
}


class JonasGuiNode(Node):
    def __init__(self):
        super().__init__('pyqt_gui')

        self.move_publisher = self.create_publisher(
            Int16MultiArray,
            'mov_coms_topic',
            10,
        )
        self.face_publisher = self.create_publisher(String, 'face_coms_topic', 10)
        self.servo_publisher = self.create_publisher(String, 'servos_coms_topic', 10)
        self.create_subscription(Bool, 'motors_status', self.motors_status_callback, 10)

        self.last_motion_payload = None
        self.last_motion_sent = 0.0
        self.last_face_sent = 0.0
        self.last_servo_sent = 0.0
        self.last_motors_status_seen = 0.0
        self.motors_moving = False

        self.motion_text = 'mov_coms_topic: waiting'
        self.face_text = 'face_coms_topic: waiting'
        self.servo_text = 'servos_coms_topic: waiting'
        self.arm_text = 'motors_status: waiting'

    def motors_status_callback(self, msg):
        self.last_motors_status_seen = time.monotonic()
        self.motors_moving = bool(msg.data)
        state = 'moving' if self.motors_moving else 'idle'
        self.arm_text = f'motors_status: {state}'

    def send_motion(self, command, speed_percent, force=False):
        command = int(command)
        speed_percent = int(clamp(speed_percent, 0, MAX_SPEED_PERCENT))
        payload = (command, speed_percent)
        now = time.monotonic()

        if (
            not force
            and payload == self.last_motion_payload
            and now - self.last_motion_sent < 0.08
        ):
            return

        msg = Int16MultiArray()
        msg.data = [command, speed_percent]
        self.move_publisher.publish(msg)

        self.last_motion_payload = payload
        self.last_motion_sent = now
        label = MOVEMENT_LABELS.get(command, f'UNKNOWN {command}')
        self.motion_text = (
            f'mov_coms_topic: {label} ({command}), speed={speed_percent}%'
        )

    def send_face(self, expression):
        msg = String()
        msg.data = expression
        self.face_publisher.publish(msg)
        self.last_face_sent = time.monotonic()
        self.face_text = f'face_coms_topic: {expression}'

    def send_arm_sequence(self, name):
        face_expression = {
            'Salute': 'blink',
            'Curl': 'fire',
            'Hug': 'heart',
            'Dance': 'music',
            'Serve': 'smile',
            'Walking': 'blink',
            'Rest': 'blink',
        }.get(name, 'blink')

        self.send_face(face_expression)

        msg = String()
        msg.data = name
        self.servo_publisher.publish(msg)
        self.last_servo_sent = time.monotonic()
        self.servo_text = f'servos_coms_topic: {name}'


class AnalogPad(QWidget):
    valueChanged = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self._x_axis = 0.0
        self._y_axis = 0.0
        self.setMinimumSize(270, 270)
        self.setMouseTracking(True)

    def reset(self, emit_signal=True):
        self._x_axis = 0.0
        self._y_axis = 0.0
        if emit_signal:
            self.valueChanged.emit(0.0, 0.0)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._update_from_position(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._update_from_position(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.reset()

    def paintEvent(self, _event):
        size = min(self.width(), self.height()) - 24
        radius = size / 2.0
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        rect = QRectF(center.x() - radius, center.y() - radius, size, size)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor('#f7f8fa'))

        painter.setPen(QPen(QColor('#c8ced8'), 2))
        painter.setBrush(QColor('#ffffff'))
        painter.drawEllipse(rect)

        painter.setPen(QPen(QColor('#dde2ea'), 1))
        painter.drawEllipse(
            QRectF(
                center.x() - radius * 0.55,
                center.y() - radius * 0.55,
                radius * 1.1,
                radius * 1.1,
            )
        )
        painter.drawLine(
            QPointF(center.x() - radius, center.y()),
            QPointF(center.x() + radius, center.y()),
        )
        painter.drawLine(
            QPointF(center.x(), center.y() - radius),
            QPointF(center.x(), center.y() + radius),
        )

        painter.setPen(QPen(QColor('#4c566a'), 1))
        painter.setFont(QFont('Sans Serif', 9))
        painter.drawText(
            QRectF(center.x() - 30, center.y() - radius - 8, 60, 18),
            Qt.AlignCenter,
            '+X',
        )
        painter.drawText(
            QRectF(center.x() - 30, center.y() + radius - 10, 60, 18),
            Qt.AlignCenter,
            '-X',
        )
        painter.drawText(
            QRectF(center.x() - radius - 8, center.y() - 9, 45, 18),
            Qt.AlignCenter,
            '+Y',
        )
        painter.drawText(
            QRectF(center.x() + radius - 38, center.y() - 9, 45, 18),
            Qt.AlignCenter,
            '-Y',
        )

        knob_x = center.x() - self._y_axis * radius
        knob_y = center.y() - self._x_axis * radius
        knob_radius = max(18.0, radius * 0.16)
        painter.setPen(QPen(QColor('#1d4ed8'), 2))
        painter.setBrush(QColor('#3b82f6'))
        painter.drawEllipse(QPointF(knob_x, knob_y), knob_radius, knob_radius)

    def _update_from_position(self, position):
        size = min(self.width(), self.height()) - 24
        radius = max(size / 2.0, 1.0)
        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        dx = position.x() - center_x
        dy = position.y() - center_y
        distance = math.hypot(dx, dy)
        if distance > radius:
            scale = radius / distance
            dx *= scale
            dy *= scale

        self._x_axis = clamp(-dy / radius, -1.0, 1.0)
        self._y_axis = clamp(-dx / radius, -1.0, 1.0)
        self.valueChanged.emit(self._x_axis, self._y_axis)
        self.update()


class JonasGui(QMainWindow):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.linear_x_axis = 0.0
        self.linear_y_axis = 0.0
        self.angular_axis = 0.0

        self.setWindowTitle('Jonas Control')
        self.setMinimumSize(880, 650)
        self.setStyleSheet("""
            QMainWindow { background: #eef1f5; }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #d7dce5;
                border-radius: 8px;
                margin-top: 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QPushButton {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 7px;
                padding: 9px 12px;
                font-weight: 600;
            }
            QPushButton:pressed {
                background: #dbeafe;
                border-color: #3b82f6;
            }
            QLabel { color: #1f2937; }
        """)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(MAX_SPEED_PERCENT)
        self.speed_slider.setValue(30)
        self.speed_slider.valueChanged.connect(self.update_speed_limit)

        self.speed_label = QLabel()
        self.limit_label = QLabel()
        self.update_speed_limit(self.speed_slider.value())

        root_layout = QVBoxLayout()
        root_layout.addWidget(self.build_base_controls())
        root_layout.addWidget(self.build_arm_controls())
        root_layout.addWidget(self.build_status_panel())

        root = QWidget()
        root.setLayout(root_layout)
        self.setCentralWidget(root)

        self.command_timer = QTimer()
        self.command_timer.timeout.connect(self.publish_active_motion)
        self.command_timer.start(100)

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(200)

    def build_base_controls(self):
        base_box = QGroupBox('Base')
        base_layout = QVBoxLayout()

        motion_layout = QHBoxLayout()
        motion_layout.addWidget(self.build_rotation_controls(), 0)
        motion_layout.addWidget(self.build_analog_controls(), 1)
        base_layout.addLayout(motion_layout)

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.speed_label)
        slider_layout.addWidget(self.speed_slider, 1)
        slider_layout.addWidget(self.limit_label)
        base_layout.addLayout(slider_layout)

        base_box.setLayout(base_layout)
        return base_box

    def build_rotation_controls(self):
        rotation_box = QGroupBox('Rotacion')
        rotation_box.setFixedWidth(230)
        layout = QVBoxLayout()

        rot_left = QPushButton('Rotar izq')
        rot_right = QPushButton('Rotar der')
        stop = QPushButton('STOP')
        for button in (rot_left, rot_right, stop):
            button.setMinimumHeight(58)

        rot_left.pressed.connect(lambda: self.set_rotation(1.0))
        rot_left.released.connect(lambda: self.set_rotation(0.0))
        rot_right.pressed.connect(lambda: self.set_rotation(-1.0))
        rot_right.released.connect(lambda: self.set_rotation(0.0))
        stop.clicked.connect(self.stop_motion)

        layout.addWidget(rot_left)
        layout.addWidget(stop)
        layout.addWidget(rot_right)
        layout.addStretch(1)
        rotation_box.setLayout(layout)
        return rotation_box

    def build_analog_controls(self):
        analog_box = QGroupBox('Analogo lineal X/Y')
        layout = QHBoxLayout()

        self.analog_pad = AnalogPad()
        self.analog_pad.valueChanged.connect(self.set_linear_axes)

        readout_layout = QVBoxLayout()
        self.analog_label = QLabel('Entrada: x=+0.00, y=+0.00')
        self.command_label = QLabel(self.node.motion_text)
        self.face_label = QLabel(self.node.face_text)
        self.servo_label = QLabel(self.node.servo_text)
        self.arm_label = QLabel(self.node.arm_text)
        self.max_speed_label = QLabel()
        self.max_speed_label.setText(self.limit_label.text())
        for label in (
            self.analog_label,
            self.command_label,
            self.face_label,
            self.servo_label,
            self.arm_label,
            self.max_speed_label,
        ):
            label.setWordWrap(True)
            label.setMinimumHeight(28)

        readout_layout.addWidget(self.analog_label)
        readout_layout.addWidget(self.command_label)
        readout_layout.addWidget(self.face_label)
        readout_layout.addWidget(self.servo_label)
        readout_layout.addWidget(self.arm_label)
        readout_layout.addWidget(self.max_speed_label)
        readout_layout.addStretch(1)

        layout.addWidget(self.analog_pad, 0)
        layout.addLayout(readout_layout, 1)
        analog_box.setLayout(layout)
        return analog_box

    def build_arm_controls(self):
        sequence_box = QGroupBox('Brazo')
        sequence_layout = QGridLayout()
        sequences = ['Salute', 'Curl', 'Hug', 'Dance', 'Serve', 'Walking', 'Rest']

        for index, name in enumerate(sequences):
            button = QPushButton(name)
            button.setMinimumHeight(42)
            button.clicked.connect(lambda _=False, seq=name: self.node.send_arm_sequence(seq))
            sequence_layout.addWidget(button, index // 4, index % 4)

        sequence_box.setLayout(sequence_layout)
        return sequence_box

    def build_status_panel(self):
        status_box = QGroupBox('Estado')
        status_layout = QGridLayout()

        self.status_badges: Dict[str, QLabel] = {
            'motion': self.make_badge(),
            'face': self.make_badge(),
            'servos': self.make_badge(),
            'motors': self.make_badge(),
        }
        status_layout.addWidget(QLabel('Base'), 0, 0)
        status_layout.addWidget(self.status_badges['motion'], 0, 1)
        status_layout.addWidget(QLabel('Cara'), 0, 2)
        status_layout.addWidget(self.status_badges['face'], 0, 3)
        status_layout.addWidget(QLabel('Secuencia'), 1, 0)
        status_layout.addWidget(self.status_badges['servos'], 1, 1)
        status_layout.addWidget(QLabel('Dynamixel'), 1, 2)
        status_layout.addWidget(self.status_badges['motors'], 1, 3)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        status_layout.addWidget(separator, 2, 0, 1, 4)

        self.motion_status_label = QLabel(self.node.motion_text)
        self.face_status_label = QLabel(self.node.face_text)
        self.servo_status_label = QLabel(self.node.servo_text)
        self.motor_status_label = QLabel(self.node.arm_text)
        for label in (
            self.motion_status_label,
            self.face_status_label,
            self.servo_status_label,
            self.motor_status_label,
        ):
            label.setWordWrap(True)

        status_layout.addWidget(self.motion_status_label, 3, 0, 1, 4)
        status_layout.addWidget(self.face_status_label, 4, 0, 1, 4)
        status_layout.addWidget(self.servo_status_label, 5, 0, 1, 4)
        status_layout.addWidget(self.motor_status_label, 6, 0, 1, 4)

        status_box.setLayout(status_layout)
        return status_box

    def make_badge(self):
        label = QLabel('waiting')
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumHeight(28)
        label.setMinimumWidth(150)
        return label

    def update_speed_limit(self, value):
        self.speed_label.setText(f'Limite de velocidad: {value}%')
        self.limit_label.setText(f'max legado={value}%')
        if hasattr(self, 'max_speed_label'):
            self.max_speed_label.setText(self.limit_label.text())
        self.send_current_motion(force=True)

    def set_linear_axes(self, x_axis, y_axis):
        self.linear_x_axis = float(x_axis)
        self.linear_y_axis = float(y_axis)
        self.analog_label.setText(
            f'Entrada: x={self.linear_x_axis:+.2f}, y={self.linear_y_axis:+.2f}'
        )
        self.send_current_motion(force=True)

    def set_rotation(self, angular_axis):
        self.angular_axis = float(angular_axis)
        self.send_current_motion(force=True)

    def publish_active_motion(self):
        if self.motion_is_active():
            self.send_current_motion()

    def send_current_motion(self, force=False):
        if not self.motion_is_active():
            if force:
                self.node.send_motion(STOP_COMMAND, 0, force=True)
            return

        command = self.legacy_code_for_motion()
        speed_percent = round(self.speed_slider.value() * self.motion_level())
        self.node.send_motion(command, speed_percent, force=force)

    def stop_motion(self):
        self.linear_x_axis = 0.0
        self.linear_y_axis = 0.0
        self.angular_axis = 0.0
        self.analog_pad.reset(emit_signal=False)
        self.analog_label.setText('Entrada: x=+0.00, y=+0.00')
        self.node.send_motion(STOP_COMMAND, 0, force=True)

    def motion_is_active(self):
        return self.motion_level() > AXIS_DEADZONE

    def motion_level(self):
        return min(
            1.0,
            max(
                abs(self.linear_x_axis),
                abs(self.linear_y_axis),
                abs(self.angular_axis),
            ),
        )

    def legacy_code_for_motion(self):
        x_axis = self.linear_x_axis
        y_axis = self.linear_y_axis
        angular_axis = self.angular_axis

        if abs(angular_axis) >= max(abs(x_axis), abs(y_axis), AXIS_DEADZONE):
            return 9 if angular_axis > 0.0 else 10

        x_active = abs(x_axis) > AXIS_DEADZONE
        y_active = abs(y_axis) > AXIS_DEADZONE

        if x_active and y_active:
            if x_axis > 0.0 and y_axis > 0.0:
                return 8
            if x_axis > 0.0 and y_axis < 0.0:
                return 5
            if x_axis < 0.0 and y_axis < 0.0:
                return 6
            return 7

        if x_active:
            return 1 if x_axis > 0.0 else 2

        if y_active:
            return 3 if y_axis > 0.0 else 4

        return STOP_COMMAND

    def refresh_status(self):
        now = time.monotonic()

        self.command_label.setText(self.node.motion_text)
        self.face_label.setText(self.node.face_text)
        self.servo_label.setText(self.node.servo_text)
        self.arm_label.setText(self.node.arm_text)
        self.motion_status_label.setText(self.node.motion_text)
        self.face_status_label.setText(self.node.face_text)
        self.servo_status_label.setText(self.node.servo_text)
        self.motor_status_label.setText(self.node.arm_text)

        motion_fresh = now - self.node.last_motion_sent <= 1.0
        if self.motion_is_active():
            self.set_badge(
                self.status_badges['motion'],
                'ok' if motion_fresh else 'error',
                'TX' if motion_fresh else 'TIMEOUT',
            )
        elif self.node.last_motion_sent:
            self.set_badge(self.status_badges['motion'], 'ok', 'STOP')
        else:
            self.set_badge(self.status_badges['motion'], 'wait', 'WAIT')

        self.set_badge(
            self.status_badges['face'],
            'ok' if self.node.last_face_sent else 'wait',
            'SENT' if self.node.last_face_sent else 'WAIT',
        )
        self.set_badge(
            self.status_badges['servos'],
            'ok' if self.node.last_servo_sent else 'wait',
            'SENT' if self.node.last_servo_sent else 'WAIT',
        )

        motors_fresh = now - self.node.last_motors_status_seen <= STATUS_TIMEOUT
        if motors_fresh:
            self.set_badge(
                self.status_badges['motors'],
                'warn' if self.node.motors_moving else 'ok',
                'MOVING' if self.node.motors_moving else 'IDLE',
            )
        else:
            self.set_badge(self.status_badges['motors'], 'wait', 'WAIT')

    @staticmethod
    def set_badge(label, state, text):
        styles = {
            'ok': ('#15803d', '#dcfce7'),
            'warn': ('#92400e', '#fef3c7'),
            'error': ('#b91c1c', '#fee2e2'),
            'wait': ('#475569', '#e2e8f0'),
        }
        color, background = styles[state]
        label.setText(text)
        label.setStyleSheet(
            f'background: {background}; color: {color}; '
            f'border: 1px solid {color}; border-radius: 7px; '
            'font-weight: 700; padding: 4px 8px;'
        )


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def main(args=None):
    rclpy.init(args=args)
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    node = JonasGuiNode()
    window = JonasGui(node)
    window.show()

    ros_timer = QTimer()
    shutdown_requested = False

    def request_shutdown(*_):
        nonlocal shutdown_requested
        if shutdown_requested:
            return

        shutdown_requested = True
        if rclpy.ok():
            node.send_motion(STOP_COMMAND, 0, force=True)
        ros_timer.stop()
        app.quit()

    def spin_ros_once():
        if shutdown_requested or not rclpy.ok():
            request_shutdown()
            return

        try:
            rclpy.spin_once(node, timeout_sec=0.01)
        except (KeyboardInterrupt, ExternalShutdownException):
            request_shutdown()
        except RuntimeError:
            if rclpy.ok():
                raise
            request_shutdown()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    ros_timer.timeout.connect(spin_ros_once)
    ros_timer.start(10)

    try:
        return app.exec_()
    finally:
        ros_timer.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
