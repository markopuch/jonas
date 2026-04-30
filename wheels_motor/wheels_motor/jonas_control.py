#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Int16MultiArray

from .jonas_functions import (
    close_serial_ports,
    send_vel_robot,
    vx_max,
    vxy_max,
    vy_max,
    w_max,
)


class JonasControl(Node):
    def __init__(self):
        super().__init__('jonas_control')
        self.create_subscription(
            Int16MultiArray,
            'mov_coms_topic',
            self.callback_base,
            10,
        )

    def callback_base(self, data):
        vx = 0.0
        vy = 0.0
        w = 0.0

        if len(data.data) < 2:
            self.get_logger().warning('Comando de movimiento invalido recibido.')
            return

        command = data.data[0]
        speed_ratio = data.data[1] / 100.0

        if command == 1:
            vx = speed_ratio * vx_max
        elif command == 2:
            vx = -speed_ratio * vx_max
        elif command == 3:
            vy = speed_ratio * vy_max
        elif command == 4:
            vy = -speed_ratio * vy_max
        elif command == 5:
            vx = speed_ratio * vxy_max
            vy = -speed_ratio * vxy_max
        elif command == 6:
            vx = -speed_ratio * vxy_max
            vy = -speed_ratio * vxy_max
        elif command == 7:
            vx = -speed_ratio * vxy_max
            vy = speed_ratio * vxy_max
        elif command == 8:
            vx = speed_ratio * vxy_max
            vy = speed_ratio * vxy_max
        elif command == 9:
            w = speed_ratio * w_max
        elif command == 10:
            w = -speed_ratio * w_max

        self.get_logger().info(
            f'Comando base -> vx: {vx:.4f}, vy: {vy:.4f}, w: {w:.4f}'
        )

        try:
            send_vel_robot(vx, vy, w)
        except Exception as exc:  # pragma: no cover - depende del hardware
            self.get_logger().error(f'No se pudo enviar velocidad a la base: {exc}')


def main(args=None):
    rclpy.init(args=args)
    node = JonasControl()

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        close_serial_ports()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
