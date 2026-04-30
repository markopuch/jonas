#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import signal

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow
from std_msgs.msg import Int16MultiArray, String

from .UI_design import setupUi


class UI_MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setupUi(self)

        self.node = Node('pyqt_gui')

        self.pub_mov = self.node.create_publisher(Int16MultiArray, 'mov_coms_topic', 10)
        self.pub_face = self.node.create_publisher(String, 'face_coms_topic', 10)
        self.pub_servos_commands = self.node.create_publisher(String, 'servos_coms_topic', 10)

        self.slider.valueChanged.connect(self.changeValue)

        self.direction = ''
        self.current_value = 0
        self.mov_msg = Int16MultiArray()
        self.mov_dic = {
            'UP': 1,
            'DOWN': 2,
            'LEFT': 3,
            'RIGHT': 4,
            'UP-RIGHT': 5,
            'DOWN-RIGHT': 6,
            'DOWN-LEFT': 7,
            'UP-LEFT': 8,
            'ROT-LEFT': 9,
            'ROT-RIGHT': 10,
        }

    def set_face(self, expression):
        msg = String()
        msg.data = expression
        self.pub_face.publish(msg)

    def set_servos(self, gesture):
        msg = String()
        msg.data = gesture
        self.pub_servos_commands.publish(msg)

    def button_pressed(self, direction):
        if direction == 'STOP':
            self.direction = 'UP'
            value_msg = 0
        else:
            self.direction = direction
            value_msg = self.current_value

        self.mov_msg.data = [self.mov_dic[self.direction], value_msg]
        print(self.direction)
        print(value_msg)
        self.pub_mov.publish(self.mov_msg)

    def changeValue(self, value):
        self.my_label.setText('num: ' + str(value))
        self.current_value = value


def main(args=None):
    rclpy.init(args=args)
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    ui = UI_MainWindow()
    ui.show()

    ros_timer = QTimer()
    shutdown_requested = False

    def request_shutdown(*_):
        nonlocal shutdown_requested
        if shutdown_requested:
            return

        shutdown_requested = True
        ros_timer.stop()
        app.quit()

    def spin_ros_once():
        if shutdown_requested or not rclpy.ok():
            request_shutdown()
            return

        try:
            rclpy.spin_once(ui.node, timeout_sec=0.01)
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
        ui.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
