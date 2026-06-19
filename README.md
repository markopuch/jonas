# Jonas ROS 2

This repository contains the ROS 2 Humble software stack for Jonas, a robotics
project of UTEC - Universidad de Ingenieria y Tecnologia, Lima, Peru.

Repository editor and maintainer contact: `mpuchuri@utec.edu.pe`.

## Overview

Jonas is operated through a distributed ROS 2 setup:

- A remote PC runs the operator interface.
- A Raspberry Pi 4 with 8 GB of RAM runs the robot-side nodes for the mobile
  base, face display, Dynamixel servos, and arm sequence planner.

The workspace is intended to be placed directly at:

```text
~/jonas_ws/src/jonas
```

Keep only this repository inside `~/jonas_ws/src` for Jonas.

## Packages

- `jonas_interfaces`: custom service and action definitions.
- `jonas`: arm motion, Dynamixel control, launch files, and sequence planning.
- `wheels_motor`: mobile base control and wheel serial communication.
- `interface_rpi`: robot-side face display interface.
- `interface_pc`: remote PC PyQt control interface adapted to the legacy Jonas
  topics.
- `interface_jonas_web`: tablet-oriented web interface for ROS 2 Humble using
  rosbridge and a safety gateway.

Additional files:

- `NODE_ARCHITECTURE.md`: node, topic, service, and hardware architecture.
- `config/hardware_devices.json`: central device map for Dynamixel and the
  three wheel Arduinos.
- `docs/jonas_node_architecture.svg`: architecture diagram.
- `rpi4_jonas.sh`: Raspberry Pi setup helper for ROS 2 Humble, runtime
  packages, serial permissions, and udev rules.
- `udev/99-jonas-serial.rules`: stable serial aliases for Jonas hardware.

## Interface Jonas Web

The `interface_jonas_web` package provides a tablet web interface for Jonas
using ROS 2 Humble and `rosbridge_server`. It serves the WebApp on port `8080`,
connects the browser to rosbridge on port `9090`, and routes base movement
through a safety gateway before publishing legacy Jonas movement commands to
`mov_coms_topic`.

Install the main Raspberry Pi dependency with:

```bash
sudo apt update
sudo apt install ros-humble-rosbridge-server
```

See full instructions in `interface_jonas_web/README.md`.

## PC Control Interface

The `interface_pc` package provides the newer PyQt operator GUI adapted to the
legacy Jonas topic architecture. It starts a ROS 2 node named `pyqt_gui`, does
not depend on `jonas_interfaces_v2`, and publishes commands to three topics:

![Jonas PC control interface](docs/interface_pc_gui.png)

- `mov_coms_topic` (`std_msgs/Int16MultiArray`): mobile base movement command
  and speed percentage.
- `face_coms_topic` (`std_msgs/String`): face expression command for the
  Raspberry Pi display.
- `servos_coms_topic` (`std_msgs/String`): gesture or sequence command for the
  arm sequence planner.

It also subscribes to `motors_status` (`std_msgs/Bool`) to show whether the
Dynamixel controller is still moving.

The analog pad maps X/Y input to the legacy movement codes used by
`wheels_motor`. The horizontal slider sets the maximum speed from `0` to `99`;
the analog displacement scales the sent percentage below that limit. The `STOP`
button sends `[1, 0]`.

| Code | Direction |
| --- | --- |
| `1` | `UP` |
| `2` | `DOWN` |
| `3` | `LEFT` |
| `4` | `RIGHT` |
| `5` | `UP-RIGHT` |
| `6` | `DOWN-RIGHT` |
| `7` | `DOWN-LEFT` |
| `8` | `UP-LEFT` |
| `9` | `ROT-LEFT` |
| `10` | `ROT-RIGHT` |

The sequence buttons publish both a face expression and an arm gesture:

| Button | Face expression | Arm command |
| --- | --- | --- |
| `Salute` | `blink` | `Salute` |
| `Curl` | `fire` | `Curl` |
| `Hug` | `heart` | `Hug` |
| `Dance` | `music` | `Dance` |
| `Serve` | `smile` | `Serve` |
| `Walking` | `blink` | `Walking` |
| `Rest` | `blink` | `Rest` |

The PC interface is normally launched with:

```bash
ros2 launch jonas remote_pc.launch.py
```

It can also be run directly after building and sourcing the workspace:

```bash
ros2 run interface_pc interface_pc
```

## Robot Computer Setup

The Jonas robot uses a Raspberry Pi 4 with 8 GB of RAM as its onboard computer.
The base operating system installed on the Raspberry Pi is Ubuntu Server 22.04
LTS. A lightweight graphical desktop was then added with Ubuntu MATE so the
robot-side display tools can run when needed.

Install Ubuntu MATE on top of Ubuntu Server with:

```bash
sudo apt update
sudo apt install -y ubuntu-mate-desktop
sudo reboot
```

During installation, Ubuntu may ask for a display manager. The default option is
usually acceptable. After rebooting, the Raspberry Pi can still be used over SSH,
but it also has a graphical desktop available for local display work.

The same desktop can be installed together with the Jonas setup script by using
the optional `--with-mate` flag.

## Requirements

These instructions target Ubuntu 22.04 with ROS 2 Humble.

On the Raspberry Pi, the recommended setup path is the consolidated helper
script:

```bash
cd ~/jonas_ws
bash src/jonas/rpi4_jonas.sh
```

This installs ROS 2 Humble base, the Python and ROS packages needed by Jonas,
adds the user to the `dialout` group, copies the udev rules from
`src/jonas/udev/99-jonas-serial.rules`, reloads udev, and prepares the shell
environment. The script installs dependencies for the robot-side packages used
on the Raspberry Pi. The `interface_pc` GUI is launched from the operator PC.

To also install Ubuntu MATE:

```bash
bash src/jonas/rpi4_jonas.sh --with-mate
```

The manual commands below are useful when setting up a PC or when installing
dependencies step by step.

Load ROS 2 in the current terminal:

```bash
source /opt/ros/humble/setup.bash
export ROS_DISTRO=humble
```

Install base tools:

```bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-setuptools
```

Initialize `rosdep` if needed:

```bash
sudo rosdep init
rosdep update
```

If `sudo rosdep init` reports that it was already initialized, run only:

```bash
rosdep update
```

Install ROS 2 and Python dependencies used by all packages on a PC or laptop:

```bash
sudo apt update
sudo apt install -y \
  python3-numpy \
  python3-serial \
  python3-pyqt5 \
  python3-tk \
  ros-${ROS_DISTRO}-ament-cmake \
  ros-${ROS_DISTRO}-rosidl-default-generators \
  ros-${ROS_DISTRO}-rosidl-default-runtime \
  ros-${ROS_DISTRO}-action-msgs \
  ros-${ROS_DISTRO}-builtin-interfaces \
  ros-${ROS_DISTRO}-rclpy \
  ros-${ROS_DISTRO}-std-msgs \
  ros-${ROS_DISTRO}-launch \
  ros-${ROS_DISTRO}-launch-ros \
  ros-${ROS_DISTRO}-ament-index-python \
  ros-${ROS_DISTRO}-dynamixel-sdk
```

From the workspace root, install dependencies declared by the local packages:

```bash
cd ~/jonas_ws
rosdep install --from-paths src --ignore-src -r -y
```

On the Raspberry Pi, install only robot-side package dependencies:

```bash
cd ~/jonas_ws
rosdep install --from-paths \
  src/jonas/jonas_interfaces \
  src/jonas/wheels_motor \
  src/jonas/interface_rpi \
  src/jonas/jonas \
  --ignore-src -r -y
```

## Build

For a normal PC or laptop build:

```bash
cd ~/jonas_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

If package locations were recently moved, clean generated directories first:

```bash
cd ~/jonas_ws
rm -rf build install log
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## Raspberry Pi Build

On a Raspberry Pi 4, build only robot-side packages and use a sequential build
to reduce memory pressure:

```bash
cd ~/jonas_ws
source /opt/ros/humble/setup.bash
export MAKEFLAGS="-j1"
COLCON_RPI_ARGS="--symlink-install --merge-install --executor sequential --parallel-workers 1"

colcon build $COLCON_RPI_ARGS \
  --packages-select jonas_interfaces wheels_motor interface_rpi jonas \
  --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash
```

Recommended package-by-package order:

```bash
colcon build $COLCON_RPI_ARGS --packages-select jonas_interfaces --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash

colcon build $COLCON_RPI_ARGS --packages-select wheels_motor --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash

colcon build $COLCON_RPI_ARGS --packages-select interface_rpi --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash

colcon build $COLCON_RPI_ARGS --packages-select jonas --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash
```

The PC-only package `interface_pc` is not required on the robot if the
Raspberry Pi only runs `jonas.launch.py`. The `jonas` package is still built on
the Raspberry Pi because it runs both `motor_movement` and `sequence_planner`
there.

## Launch

Robot-side launch on the Raspberry Pi:

```bash
ros2 launch jonas jonas.launch.py
```

This starts `motor_movement`, `wheels_motor`, `interface_rpi`, and
`sequence_planner`. Keeping `sequence_planner` on the Raspberry Pi keeps
`joint_value`, `motors_status`, and `sequence_service` local to the robot; only
high-level GUI topics cross the network.

Remote PC launch:

```bash
ros2 launch jonas remote_pc.launch.py
```

This starts only the `interface_pc` GUI.

For a distributed setup, both machines should share the same ROS 2 domain:

```bash
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
```

Source ROS 2 and the workspace on each machine before launching:

```bash
source /opt/ros/humble/setup.bash
source ~/jonas_ws/install/setup.bash
```

## Serial Ports

The current code reads device paths from the central hardware file:

```text
src/jonas/config/hardware_devices.json
```

That file is outside the ROS package directory `src/jonas/jonas`, so it can be
shared by the ROS packages and by the standalone scripts in
`src/config_python_codes`. Change the ports there when the hardware layout
changes. The environment variable `JONAS_HARDWARE_CONFIG` can point all loaders
to another file without editing code.

By default the central file uses stable udev aliases:

| Hardware | Alias |
| --- | --- |
| Dynamixel / FTDI | `/dev/jonas_usb0` |
| Wheel Arduino 1 | `/dev/jonas_usb1` |
| Wheel Arduino 2 | `/dev/jonas_usb2` |
| Wheel Arduino 3 | `/dev/jonas_usb3` |

The aliases are created by `udev/99-jonas-serial.rules`, which is copied by the
setup script to `/etc/udev/rules.d/99-jonas-serial.rules`. The same rules assign
the devices to the `dialout` group with `0660` permissions.

To manually install the rule:

```bash
sudo install -m 0644 src/jonas/udev/99-jonas-serial.rules /etc/udev/rules.d/99-jonas-serial.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=tty
sudo usermod -aG dialout $USER
```

Log out and back in, or reboot, so the group change takes effect.

## Repository Origin

This repository is an updated and improved version of the repository from which
it was forked: <https://github.com/dumdumrobots/jonas>, by Joaquin Cornejo,
master's student at TUM.
