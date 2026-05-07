from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='jonas',
            executable='motor_movement',
            name='motor_movement',
            output='screen',
        ),
        Node(
            package='wheels_motor',
            executable='jonas_control',
            name='wheels',
            output='screen',
        ),
        Node(
            package='jonas',
            executable='sequence_planner',
            name='sequence_planner',
            output='screen',
        ),
        Node(
            package='interface_rpi',
            executable='interface_rpi',
            name='interface_rpi',
            output='screen',
        ),
    ])
