# Interface Jonas Web

`interface_jonas_web` provides a tablet-friendly web interface for controlling
the Jonas robot through ROS 2 Humble and `rosbridge_server`.

This package is intended to run on the Raspberry Pi. The tablet does not run ROS
2 directly; it opens a web page served by the Raspberry Pi and communicates with
ROS 2 through a WebSocket connection.

## Raspberry Pi Setup

Use Ubuntu 22.04 with ROS 2 Humble on the Raspberry Pi.

Install the required packages:

```bash
sudo apt update
sudo apt install ros-humble-rosbridge-server
sudo apt install python3-colcon-common-extensions python3-rosdep
sudo apt install ros-humble-std-msgs ros-humble-geometry-msgs
```

Package purpose:

- `ros-humble-rosbridge-server`: exposes ROS 2 to the tablet through WebSocket.
- `python3-colcon-common-extensions`: provides the `colcon` build tools.
- `python3-rosdep`: installs ROS package dependencies automatically.
- `ros-humble-std-msgs`: provides basic ROS message types.
- `ros-humble-geometry-msgs`: provides `geometry_msgs/msg/Twist`.

## Build On Raspberry Pi

From the workspace root:

```bash
cd ~/jonas_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install
source install/setup.bash
```

## Run On Raspberry Pi

Launch the web interface:

```bash
ros2 launch interface_jonas_web jonas_web_interface.launch.py
```

The launch file starts:

- `rosbridge_server` on `0.0.0.0:9090`.
- `web_server_node` on `0.0.0.0:8080`.
- `safety_gateway_node`.

The `0.0.0.0` address is required so another device on the same WiFi network can
connect to the Raspberry Pi.

## Open From Tablet

Get the Raspberry Pi IP address:

```bash
hostname -I
```

Open this URL from the tablet:

```text
http://IP_OF_THE_RASPBERRY_PI:8080
```

The WebApp connects to rosbridge automatically with:

```js
const ROSBRIDGE_URL = `ws://${window.location.hostname}:9090`;
```

For example, if the Raspberry Pi IP is `192.168.1.80`:

```text
http://192.168.1.80:8080
```

and the WebSocket connection will use:

```text
ws://192.168.1.80:9090
```

## Manual rosbridge Command

The launch file starts rosbridge automatically. To run rosbridge manually:

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml port:=9090 address:=0.0.0.0
```

## ROS Topic Mapping

The WebApp publishes raw velocity commands to:

```text
/jonas/web/cmd_vel_raw
```

Message type:

```text
geometry_msgs/msg/Twist
```

The safety gateway converts that `Twist` command into the legacy Jonas movement
topic used by `wheels_motor`:

```text
mov_coms_topic
```

Message type:

```text
std_msgs/msg/Int16MultiArray
```

Legacy payload format:

```text
[command, speed_percent]
```

The arm and face buttons use the same topics as `interface_pc`:

```text
face_coms_topic    std_msgs/msg/String
servos_coms_topic  std_msgs/msg/String
motors_status      std_msgs/msg/Bool
```

## Safety Behavior

- Movement starts disabled.
- The user must enable movement from the WebApp.
- STOP publishes zero velocity immediately.
- The joystick returns to center automatically.
- The browser publishes zero when the page loses focus or closes.
- `safety_gateway_node` limits linear and angular speed.
- `safety_gateway_node` publishes STOP if command messages stop arriving.
- The tablet does not publish directly to `mov_coms_topic`.

## Quick Checks

Check that the web server is running:

```bash
curl http://localhost:8080
```

Check the raw command topic:

```bash
ros2 topic echo /jonas/web/cmd_vel_raw
```

Check the legacy command sent to `wheels_motor`:

```bash
ros2 topic echo /mov_coms_topic
```

Publish a manual test command:

```bash
ros2 topic pub /jonas/web/cmd_vel_raw geometry_msgs/msg/Twist "{linear: {x: 0.1, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --once
```

Publish STOP:

```bash
ros2 topic pub /jonas/web/cmd_vel_raw geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --once
```

## Troubleshooting

If the tablet cannot open the page:

- Confirm the tablet and Raspberry Pi are on the same WiFi network.
- Confirm the URL uses the Raspberry Pi IP address and port `8080`.
- Confirm the launch file is running.

If the page opens but ROS does not connect:

- Confirm rosbridge is running on port `9090`.
- Confirm rosbridge is listening on `0.0.0.0`, not only `localhost`.
- Check that no firewall is blocking ports `8080` or `9090`.

If the joystick moves but the base does not:

- Enable movement in the WebApp.
- Check `/jonas/web/cmd_vel_raw`.
- Check `/mov_coms_topic`.
- Confirm `wheels_motor` is running and subscribed to `mov_coms_topic`.

If STOP does not stop the base:

- Check that `/mov_coms_topic` receives `[1, 0]`.
- Check that `wheels_motor` is running.
