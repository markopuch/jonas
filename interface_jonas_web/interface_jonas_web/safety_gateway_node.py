#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Bool, Int16MultiArray, String


STOP_COMMAND = 1
MAX_SPEED_PERCENT = 99

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


class SafetyGatewayNode(Node):
    def __init__(self):
        super().__init__('safety_gateway_node')

        self.declare_parameter('input_topic', '/jonas/web/cmd_vel_raw')
        self.declare_parameter('output_topic', 'mov_coms_topic')
        self.declare_parameter('enable_topic', '/jonas/web/enable')
        self.declare_parameter('base_status_topic', '/jonas/web/base_status')
        self.declare_parameter('max_linear_x', 0.30)
        self.declare_parameter('max_linear_y', 0.30)
        self.declare_parameter('max_angular_z', 0.80)
        self.declare_parameter('command_timeout_sec', 0.5)
        self.declare_parameter('publish_rate_hz', 10.0)
        self.declare_parameter('require_enable', True)
        self.declare_parameter('deadzone', 0.03)
        self.declare_parameter('keepalive_sec', 0.5)

        self.input_topic = self.get_parameter('input_topic').value
        self.output_topic = self.get_parameter('output_topic').value
        self.enable_topic = self.get_parameter('enable_topic').value
        self.base_status_topic = self.get_parameter('base_status_topic').value
        self.max_linear_x = float(self.get_parameter('max_linear_x').value)
        self.max_linear_y = float(self.get_parameter('max_linear_y').value)
        self.max_angular_z = float(self.get_parameter('max_angular_z').value)
        self.command_timeout_sec = float(
            self.get_parameter('command_timeout_sec').value
        )
        self.publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
        self.require_enable = bool(self.get_parameter('require_enable').value)
        self.deadzone = float(self.get_parameter('deadzone').value)
        self.keepalive_sec = float(self.get_parameter('keepalive_sec').value)

        self.enabled = not self.require_enable
        self.last_cmd_time = 0.0
        self.last_publish_time = 0.0
        self.last_payload = None
        self.last_status = ''
        self.current_twist = Twist()

        self.create_subscription(Twist, self.input_topic, self.cmd_callback, 10)
        self.create_subscription(Bool, self.enable_topic, self.enable_callback, 10)
        self.motion_publisher = self.create_publisher(
            Int16MultiArray,
            self.output_topic,
            10,
        )
        self.status_publisher = self.create_publisher(
            String,
            self.base_status_topic,
            10,
        )

        timer_period = 1.0 / max(self.publish_rate_hz, 1.0)
        self.create_timer(timer_period, self.publish_safe_command)

        self.get_logger().info(
            f'Gateway listening on {self.input_topic}, publishing legacy '
            f'commands on {self.output_topic}'
        )

    def cmd_callback(self, msg):
        self.current_twist = self.limited_twist(msg)
        self.last_cmd_time = time.monotonic()

    def enable_callback(self, msg):
        was_enabled = self.enabled
        self.enabled = bool(msg.data) or not self.require_enable
        if was_enabled and not self.enabled:
            self.publish_payload((STOP_COMMAND, 0), force=True)
            self.publish_status('DISABLED')
        elif self.enabled:
            self.publish_status('ENABLED')

    def limited_twist(self, msg):
        limited = Twist()
        limited.linear.x = clamp(msg.linear.x, -self.max_linear_x, self.max_linear_x)
        limited.linear.y = clamp(msg.linear.y, -self.max_linear_y, self.max_linear_y)
        limited.angular.z = clamp(
            msg.angular.z,
            -self.max_angular_z,
            self.max_angular_z,
        )
        return limited

    def publish_safe_command(self):
        now = time.monotonic()

        if not self.enabled:
            self.publish_payload((STOP_COMMAND, 0))
            self.publish_status('DISABLED')
            return

        if now - self.last_cmd_time > self.command_timeout_sec:
            self.publish_payload((STOP_COMMAND, 0))
            self.publish_status('TIMEOUT')
            return

        payload = self.twist_to_legacy_payload(self.current_twist)
        self.publish_payload(payload)

        command, speed = payload
        if speed == 0:
            self.publish_status('STOP')
        else:
            label = MOVEMENT_LABELS.get(command, f'UNKNOWN {command}')
            self.publish_status(f'MOVING {label} {speed}%')

    def twist_to_legacy_payload(self, twist):
        linear_x_ratio = safe_ratio(twist.linear.x, self.max_linear_x)
        linear_y_ratio = safe_ratio(twist.linear.y, self.max_linear_y)
        angular_ratio = safe_ratio(twist.angular.z, self.max_angular_z)

        linear_level = min(1.0, math.hypot(linear_x_ratio, linear_y_ratio))
        angular_level = min(1.0, abs(angular_ratio))

        if max(linear_level, angular_level) <= self.deadzone:
            return (STOP_COMMAND, 0)

        if angular_level >= max(linear_level, self.deadzone):
            command = 9 if angular_ratio > 0.0 else 10
            speed = round(MAX_SPEED_PERCENT * angular_level)
            return (command, speed)

        angle = math.degrees(math.atan2(linear_y_ratio, linear_x_ratio))
        command = code_for_angle(angle)
        speed = round(MAX_SPEED_PERCENT * linear_level)
        return (command, speed)

    def publish_payload(self, payload, force=False):
        now = time.monotonic()
        if (
            not force
            and payload == self.last_payload
            and now - self.last_publish_time < self.keepalive_sec
        ):
            return

        msg = Int16MultiArray()
        msg.data = [int(payload[0]), int(clamp(payload[1], 0, MAX_SPEED_PERCENT))]
        self.motion_publisher.publish(msg)
        self.last_payload = payload
        self.last_publish_time = now

    def publish_status(self, status):
        if status == self.last_status:
            return

        msg = String()
        msg.data = status
        self.status_publisher.publish(msg)
        self.last_status = status


def code_for_angle(angle):
    if -22.5 <= angle < 22.5:
        return 1
    if 22.5 <= angle < 67.5:
        return 8
    if 67.5 <= angle < 112.5:
        return 3
    if 112.5 <= angle < 157.5:
        return 7
    if angle >= 157.5 or angle < -157.5:
        return 2
    if -157.5 <= angle < -112.5:
        return 6
    if -112.5 <= angle < -67.5:
        return 4
    if -67.5 <= angle < -22.5:
        return 5
    return STOP_COMMAND


def safe_ratio(value, maximum):
    if abs(maximum) < 1e-9:
        return 0.0
    return clamp(value / maximum, -1.0, 1.0)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def main(args=None):
    rclpy.init(args=args)
    node = SafetyGatewayNode()

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.publish_payload((STOP_COMMAND, 0), force=True)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
