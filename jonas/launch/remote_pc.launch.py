from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='interface_pc',
            executable='interface_pc',
            name='interface_pc',
            output='screen',
        ),
    ])
