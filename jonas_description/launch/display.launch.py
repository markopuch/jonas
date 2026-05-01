from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_share = FindPackageShare('jonas_description')

    default_model_path = PathJoinSubstitution([
        package_share,
        'urdf',
        'jonas_omni_base.urdf.xacro',
    ])
    default_rviz_config_path = PathJoinSubstitution([
        package_share,
        'rviz',
        'display.rviz',
    ])

    model = LaunchConfiguration('model')
    rviz_config = LaunchConfiguration('rviz_config')

    robot_description = {
        'robot_description': ParameterValue(
            Command(['xacro', ' ', model]),
            value_type=str,
        )
    }

    return LaunchDescription([
        DeclareLaunchArgument(
            'model',
            default_value=default_model_path,
            description='Absolute path to the Jonas URDF/Xacro model.',
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=default_rviz_config_path,
            description='Absolute path to the RViz configuration file.',
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[robot_description],
            output='screen',
        ),
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            parameters=[robot_description],
            output='screen',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_config],
            output='screen',
        ),
    ])
