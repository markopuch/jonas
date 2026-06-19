#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class TestCmdVelNode(Node):
    def __init__(self):
        super().__init__('jonas_web_test_cmd_vel_node')
        self.declare_parameter('topic', '/jonas/web/cmd_vel_raw')
        self.declare_parameter('linear_x', 0.10)
        self.declare_parameter('linear_y', 0.0)
        self.declare_parameter('angular_z', 0.0)
        self.declare_parameter('duration_sec', 1.0)

        self.topic = self.get_parameter('topic').value
        self.linear_x = float(self.get_parameter('linear_x').value)
        self.linear_y = float(self.get_parameter('linear_y').value)
        self.angular_z = float(self.get_parameter('angular_z').value)
        self.duration_sec = float(self.get_parameter('duration_sec').value)
        self.publisher = self.create_publisher(Twist, self.topic, 10)

    def run(self):
        end_time = time.monotonic() + self.duration_sec
        msg = Twist()
        msg.linear.x = self.linear_x
        msg.linear.y = self.linear_y
        msg.angular.z = self.angular_z

        while rclpy.ok() and time.monotonic() < end_time:
            self.publisher.publish(msg)
            rclpy.spin_once(self, timeout_sec=0.05)

        self.publisher.publish(Twist())
        self.get_logger().info(f'Published test command on {self.topic} and STOP.')


def main(args=None):
    rclpy.init(args=args)
    node = TestCmdVelNode()

    try:
        node.run()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
