#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itertools

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Bool, String


class DemoStatusNode(Node):
    def __init__(self):
        super().__init__('jonas_web_demo_status_node')
        self.face_publisher = self.create_publisher(String, '/jonas/web/face_status', 10)
        self.sequence_publisher = self.create_publisher(
            String,
            '/jonas/web/sequence_status',
            10,
        )
        self.dynamixel_publisher = self.create_publisher(
            String,
            '/jonas/web/dynamixel_status',
            10,
        )
        self.motors_publisher = self.create_publisher(Bool, 'motors_status', 10)
        self.states = itertools.cycle([
            ('WAIT', 'WAIT', 'OK', False),
            ('ACTIVE', 'RUNNING', 'OK', True),
            ('WAIT', 'DONE', 'OK', False),
        ])
        self.create_timer(2.0, self.publish_status)

    def publish_status(self):
        face, sequence, dynamixel, moving = next(self.states)

        face_msg = String()
        face_msg.data = face
        self.face_publisher.publish(face_msg)

        sequence_msg = String()
        sequence_msg.data = sequence
        self.sequence_publisher.publish(sequence_msg)

        dynamixel_msg = String()
        dynamixel_msg.data = dynamixel
        self.dynamixel_publisher.publish(dynamixel_msg)

        motors_msg = Bool()
        motors_msg.data = moving
        self.motors_publisher.publish(motors_msg)


def main(args=None):
    rclpy.init(args=args)
    node = DemoStatusNode()

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
