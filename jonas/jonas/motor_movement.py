#!/usr/bin/env python3

import time

import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Bool, Int16MultiArray

from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler
from jonas_interfaces.srv import Sequence


class Robot(Node):
    def __init__(self):
        super().__init__('joint_node')

        # Joint variables
        self.q_des = np.array([2048, 2048, 2048, 2048, 2048, 2048], dtype=int)
        self.q_act = np.array([2048, 2048, 2048, 2048, 2048, 2048], dtype=int)

        # General variables
        self.dxl_id = np.array([1, 2, 3, 4, 5, 6], dtype=int)
        self.dxl_status = np.array([0, 0, 0, 0, 0, 0], dtype=int)
        self.dxl_speed = 175

        # Server variables
        self.sequence_active = False
        self.motors_moving = False
        self.order_sent = False
        self.sequence_start_time = 0.0
        self.sequence_time = 0.0
        self.msg_motor = Bool()

        # Addresses
        self.addr_torque_en = 24
        self.addr_led_en = 25
        self.addr_goal_position = 30
        self.addr_mov_speed = 32
        self.addr_mov_status = 46

        # General settings
        self.protocol_version = 1.0
        self.baudrate = 1000000
        self.device = '/dev/jonas_usb0'

        self.port_handler = PortHandler(self.device)
        self.packet_handler = PacketHandler(self.protocol_version)

        self._open_port()

        self.create_subscription(Int16MultiArray, 'joint_value', self.update_goal, 10)
        self.motor_publisher = self.create_publisher(Bool, 'motors_status', 10)
        self.create_service(Sequence, 'sequence_service', self.start_sequence)

        self.setup_servomotors()

    def _now_seconds(self):
        return self.get_clock().now().nanoseconds / 1e9

    def _open_port(self):
        if not self.port_handler.openPort():
            raise RuntimeError('Failed to open the Dynamixel port.')

        self.get_logger().info('Succeeded to open the port.')

        if not self.port_handler.setBaudRate(self.baudrate):
            self.port_handler.closePort()
            raise RuntimeError(f'Failed to change baudrate to {self.baudrate}.')

        self.get_logger().info(f'Baudrate changed to {self.baudrate}.')

    def setup_servomotors(self):
        for motor_id in self.dxl_id:
            dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
                self.port_handler, int(motor_id), self.addr_led_en, True
            )
            self._verify_result(dxl_comm_result, dxl_error, motor_id, 'LED setup')

            dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
                self.port_handler, int(motor_id), self.addr_torque_en, True
            )
            self._verify_result(dxl_comm_result, dxl_error, motor_id, 'torque enable')

            dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(
                self.port_handler, int(motor_id), self.addr_mov_speed, self.dxl_speed
            )
            self._verify_result(dxl_comm_result, dxl_error, motor_id, 'speed setup')

            self.get_logger().info(f'Motor ID {motor_id} ready to use.')

    def _verify_result(self, dxl_comm_result, dxl_error, motor_id, context):
        if dxl_comm_result != COMM_SUCCESS:
            raise RuntimeError(
                f'{context} failed for motor {motor_id}: '
                f'{self.packet_handler.getTxRxResult(dxl_comm_result)}'
            )

        if dxl_error != 0:
            raise RuntimeError(
                f'{context} failed for motor {motor_id}: '
                f'{self.packet_handler.getRxPacketError(dxl_error)}'
            )

    def start_sequence(self, request, response):
        if not self.sequence_active:
            self.sequence_active = request.sequence_active
            self.sequence_start_time = self._now_seconds()
            self.order_sent = True
        else:
            self.order_sent = False

        response.order_received = self.order_sent
        return response

    def update_goal(self, msg):
        data_array = msg.data

        if len(data_array) == len(self.dxl_id):
            self.q_des = np.array(data_array, dtype=int)
        else:
            self.get_logger().warning('Invalid joint array, try again.')

    def set_position(self):
        for motor_id in self.dxl_id:
            dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(
                self.port_handler,
                int(motor_id),
                self.addr_goal_position,
                int(self.q_des[motor_id - 1]),
            )
            self._verify_result(dxl_comm_result, dxl_error, motor_id, 'goal position')

        time.sleep(0.1)

    def update_status(self):
        mask = 0

        for motor_id in self.dxl_id:
            status, dxl_comm_result, dxl_error = self.packet_handler.read1ByteTxRx(
                self.port_handler, int(motor_id), self.addr_mov_status
            )
            self._verify_result(dxl_comm_result, dxl_error, motor_id, 'status read')

            self.dxl_status[motor_id - 1] = status
            mask += status

        if mask == 0:
            self.sequence_active = False
            self.motors_moving = False
            self.sequence_time = self._now_seconds() - self.sequence_start_time
        else:
            self.motors_moving = True

        self.msg_motor.data = self.motors_moving
        self.motor_publisher.publish(self.msg_motor)

    def step(self):
        if self.sequence_active:
            if not self.motors_moving:
                self.set_position()

            self.update_status()

    def shutdown(self):
        for motor_id in self.dxl_id:
            try:
                self.packet_handler.write1ByteTxRx(
                    self.port_handler, int(motor_id), self.addr_led_en, False
                )
                self.packet_handler.write1ByteTxRx(
                    self.port_handler, int(motor_id), self.addr_torque_en, False
                )
                self.get_logger().info(f'Shutting down motor ID {motor_id}.')
            except Exception:
                pass

        self.port_handler.closePort()


def main(args=None):
    rclpy.init(args=args)
    robot = None
    loop_period = 0.1

    try:
        robot = Robot()

        while rclpy.ok():
            rclpy.spin_once(robot, timeout_sec=0.01)
            robot.step()
            time.sleep(loop_period)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if robot is not None:
            robot.shutdown()
            robot.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
