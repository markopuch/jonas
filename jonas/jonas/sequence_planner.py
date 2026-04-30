#!/usr/bin/env python3

import time

import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Bool, Int16MultiArray, String

from jonas_interfaces.srv import Sequence


class Planner(Node):
    def __init__(self):
        super().__init__('planner_node')

        self.sequence_active = True
        self.motors_moving = False
        self.action_string = 'Rest'
        self.action_active = False

        self.poses = {
            'Rest': np.array([180, 100, 170, 180, 100, 170]),
            'Serve': np.array([90, 90, 180, 270, 90, 180]),
            'Show': np.array([0, 90, 180, 360, 90, 180]),
            'Salute 1': np.array([45, 100, 155, 180, 100, 170]),
            'Salute 2': np.array([45, 90, 155, 180, 100, 170]),
            'Walking 1': np.array([135, 100, 170, 135, 100, 170]),
            'Walking 2': np.array([225, 100, 170, 225, 100, 170]),
            'Dance 1': np.array([0, 105, 255, 180, 105, 255]),
            'Dance 2': np.array([0, 125, 235, 180, 125, 235]),
            'Hug 1': np.array([90, 135, 180, 270, 135, 180]),
            'Hug 2': np.array([90, 90, 135, 270, 90, 135]),
            'Curl 1': np.array([180, 125, 160, 180, 125, 160]),
            'Curl 2': np.array([0, 160, 90, 360, 160, 90]),
        }

        self.sequences = {
            'Salute': np.array(
                ['Rest', 'Salute 1', 'Salute 2', 'Salute 1', 'Salute 2', 'Salute 1', 'Salute 2', 'Rest']
            ),
            'Walking': np.array(
                ['Rest', 'Walking 1', 'Walking 2', 'Walking 1', 'Walking 2', 'Walking 1', 'Walking 2', 'Rest']
            ),
            'Dance': np.array(
                ['Rest', 'Dance 1', 'Dance 2', 'Dance 1', 'Dance 2', 'Dance 1', 'Dance 2', 'Dance 1', 'Dance 2', 'Rest']
            ),
            'Hug': np.array(
                ['Rest', 'Hug 1', 'Hug 2', 'Hug 1', 'Hug 2', 'Hug 1', 'Hug 2', 'Rest']
            ),
            'Curl': np.array(
                ['Rest', 'Curl 1', 'Curl 2', 'Curl 1', 'Curl 2', 'Curl 1', 'Rest']
            ),
        }

        self.joint_publisher = self.create_publisher(Int16MultiArray, 'joint_value', 10)
        self.create_subscription(Bool, 'motors_status', self.update_status, 10)
        self.create_subscription(String, 'servos_coms_topic', self.send_action, 10)
        self.client = self.create_client(Sequence, 'sequence_service')

    def send_action(self, msg):
        self.action_string = msg.data
        self.action_active = True

    def update_status(self, msg):
        self.motors_moving = msg.data

    def sequence_client(self, joint_values):
        msg = Int16MultiArray()
        msg.data = joint_values.tolist()
        self.joint_publisher.publish(msg)

        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for service activation.')

        request = Sequence.Request()
        request.sequence_active = self.sequence_active

        future = self.client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        response = future.result()
        if response is None:
            raise RuntimeError('Sequence service call failed.')

        return response.order_received

    def wait_until_motors_stop(self):
        while rclpy.ok() and self.motors_moving:
            rclpy.spin_once(self, timeout_sec=0.1)

    def execute_action(self):
        request = self.action_string

        if request in self.sequences:
            order = self.sequences[request]
            self.get_logger().info(f'Sent activation for {request} sequence.')

            for pose_name in order:
                self.wait_until_motors_stop()
                self.sequence_client((self.poses[pose_name] / 0.088).astype(int))
                time.sleep(0.5)

        elif request in self.poses:
            self.sequence_client((self.poses[request] / 0.088).astype(int))
            self.get_logger().info(f'Sent activation for {request} pose.')
            time.sleep(0.5)

        else:
            self.get_logger().warning(
                f'Neither pose nor sequence exists with name {request}, try again.'
            )

        self.action_active = False


def main(args=None):
    rclpy.init(args=args)
    planner = Planner()
    planner.get_logger().info('Jonas sequence planner active.')

    try:
        while rclpy.ok():
            rclpy.spin_once(planner, timeout_sec=0.1)

            if not planner.motors_moving and planner.action_active:
                planner.execute_action()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        planner.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
