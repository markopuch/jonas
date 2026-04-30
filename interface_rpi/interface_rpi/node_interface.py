#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import signal
from pathlib import Path

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
from PyQt5 import QtCore, QtGui, QtWidgets
from std_msgs.msg import String


IMAGE_COUNTS = {
    'blink': 5,
    'heart': 25,
    'fire': 23,
    'music': 33,
    'smile': 7,
}


class App(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.title = 'My Screen'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.image_label = 'blink'
        self.current_image = 1
        self.images_counts = 0
        self.flag_loop = False
        self.image_base_path = None
        try:
            self.main_path = Path(get_package_share_directory('interface_rpi')) / 'faces'
        except PackageNotFoundError:
            self.main_path = Path(__file__).resolve().parent / 'faces'

        self.node = Node('node_interface')
        self.node.create_subscription(String, 'face_coms_topic', self.callback_face, 10)

        self.init_ui()

    def callback_face(self, msg):
        print(msg.data)
        self.image_label = msg.data
        self.current_image = 1
        self.flag_loop = False

    def init_ui(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.label = QtWidgets.QLabel(self)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_image)
        self.timer.start(100)
        self.showFullScreen()
        self.update_image()

    def refresh_image_sequence(self):
        if self.image_label not in IMAGE_COUNTS:
            self.image_label = 'blink'

        self.images_counts = IMAGE_COUNTS[self.image_label]
        self.image_base_path = self.main_path / self.image_label / self.image_label
        self.flag_loop = True

    def update_image(self):
        if not self.flag_loop:
            self.refresh_image_sequence()

        if self.current_image > self.images_counts:
            if self.image_label != 'blink':
                self.image_label = 'blink'
                self.current_image = 1
                self.flag_loop = False
                self.refresh_image_sequence()
            else:
                self.current_image = 1

        final_path = Path(f'{self.image_base_path}_{self.current_image}.png')
        pixmap = QtGui.QPixmap(str(final_path))
        if not pixmap.isNull():
            self.label.setPixmap(pixmap)
            self.label.adjustSize()
            self.resize(pixmap.size())
            self.current_image += 1


def main(args=None):
    rclpy.init(args=args)
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    ex.show()

    ros_timer = QtCore.QTimer()
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
            rclpy.spin_once(ex.node, timeout_sec=0.01)
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
        ex.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
