from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_xml.launch_description_sources import XMLLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    host = LaunchConfiguration('host')
    web_port = LaunchConfiguration('web_port')
    rosbridge_address = LaunchConfiguration('rosbridge_address')
    rosbridge_port = LaunchConfiguration('rosbridge_port')
    cmd_vel_raw_topic = LaunchConfiguration('cmd_vel_raw_topic')
    cmd_vel_output_topic = LaunchConfiguration('cmd_vel_output_topic')
    run_demo_status = LaunchConfiguration('run_demo_status')
    enable_safety_gateway = LaunchConfiguration('enable_safety_gateway')

    config_file = PathJoinSubstitution([
        FindPackageShare('interface_jonas_web'),
        'config',
        'jonas_web.yaml',
    ])

    rosbridge_launch = IncludeLaunchDescription(
        XMLLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('rosbridge_server'),
                'launch',
                'rosbridge_websocket_launch.xml',
            ])
        ),
        launch_arguments={
            'port': rosbridge_port,
            'address': rosbridge_address,
        }.items(),
    )

    web_server = Node(
        package='interface_jonas_web',
        executable='web_server_node',
        name='jonas_web_server',
        output='screen',
        parameters=[{
            'host': host,
            'port': web_port,
        }],
    )

    safety_gateway = Node(
        package='interface_jonas_web',
        executable='safety_gateway_node',
        name='safety_gateway_node',
        output='screen',
        condition=IfCondition(enable_safety_gateway),
        parameters=[
            config_file,
            {
                'input_topic': cmd_vel_raw_topic,
                'output_topic': cmd_vel_output_topic,
            },
        ],
    )

    demo_status = Node(
        package='interface_jonas_web',
        executable='demo_status_node',
        name='jonas_web_demo_status_node',
        output='screen',
        condition=IfCondition(run_demo_status),
    )

    return LaunchDescription([
        DeclareLaunchArgument('host', default_value='0.0.0.0'),
        DeclareLaunchArgument('web_port', default_value='8080'),
        DeclareLaunchArgument('rosbridge_address', default_value='0.0.0.0'),
        DeclareLaunchArgument('rosbridge_port', default_value='9090'),
        DeclareLaunchArgument(
            'cmd_vel_raw_topic',
            default_value='/jonas/web/cmd_vel_raw',
        ),
        DeclareLaunchArgument(
            'cmd_vel_output_topic',
            default_value='mov_coms_topic',
        ),
        DeclareLaunchArgument('run_demo_status', default_value='false'),
        DeclareLaunchArgument('enable_safety_gateway', default_value='true'),
        rosbridge_launch,
        web_server,
        safety_gateway,
        demo_status,
    ])
