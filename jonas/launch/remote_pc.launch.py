from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='jonas',
            executable='sequence_planner',
            name='sequence_planner',
            output='screen',
        ),
        Node(
            package='interface_pc',
            executable='interface_pc',
            name='interface_pc',
            output='screen',
        ),
    ])
