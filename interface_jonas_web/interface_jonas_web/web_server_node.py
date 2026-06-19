#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import functools
import http.server
import socketserver
import threading

import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class ReusableTcpServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class WebServerNode(Node):
    def __init__(self):
        super().__init__('jonas_web_server')

        self.declare_parameter('host', '0.0.0.0')
        self.declare_parameter('port', 8080)
        self.declare_parameter(
            'web_root',
            get_package_share_directory('interface_jonas_web') + '/web',
        )

        self.host = self.get_parameter('host').value
        self.port = int(self.get_parameter('port').value)
        self.web_root = self.get_parameter('web_root').value

        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler,
            directory=self.web_root,
        )
        self.httpd = ReusableTcpServer((self.host, self.port), handler)
        self.server_thread = threading.Thread(
            target=self.httpd.serve_forever,
            daemon=True,
        )
        self.server_thread.start()

        self.get_logger().info(
            f'Serving Jonas web interface from {self.web_root} '
            f'on http://{self.host}:{self.port}'
        )

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.server_thread.join(timeout=2.0)


def main(args=None):
    rclpy.init(args=args)
    node = WebServerNode()

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
