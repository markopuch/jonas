#!/usr/bin/env bash
set -euo pipefail

# rpi4_jonas.sh
# Minimal Raspberry Pi 4 setup for Jonas on Ubuntu Server 22.04 / ROS 2 Humble.
#
# Run from the workspace root:
#   cd ~/jonas_ws
#   bash src/jonas/rpi4_jonas.sh
#
# Optional desktop installation:
#   bash src/jonas/rpi4_jonas.sh --with-mate

ROS_DISTRO="${ROS_DISTRO:-humble}"
INSTALL_MATE=0

usage() {
  cat <<'USAGE'
Usage:
  bash src/jonas/rpi4_jonas.sh [options]

Options:
  --with-mate   Install ubuntu-mate-desktop after the ROS/runtime packages.
  -h, --help    Show this help message.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-mate)
      INSTALL_MATE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unrecognized option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -d src/jonas ]]; then
  echo "ERROR: run this script from the workspace root, for example ~/jonas_ws." >&2
  exit 1
fi

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
else
  echo "ERROR: could not read /etc/os-release." >&2
  exit 1
fi

if [[ "${UBUNTU_CODENAME:-}" != "jammy" ]]; then
  echo "WARNING: this script is intended for Ubuntu 22.04 jammy." >&2
  echo "Detected system: ${PRETTY_NAME:-unknown}" >&2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UDEV_SOURCE="${SCRIPT_DIR}/udev/99-jonas-serial.rules"
UDEV_TARGET="/etc/udev/rules.d/99-jonas-serial.rules"

if [[ ! -f "${UDEV_SOURCE}" ]]; then
  echo "ERROR: missing udev rules file: ${UDEV_SOURCE}" >&2
  exit 1
fi

echo "== Jonas RPi4 setup =="
echo "ROS_DISTRO=${ROS_DISTRO}"
echo

echo "== Base apt tools and ROS 2 repository =="
sudo apt update
sudo apt install -y \
  curl \
  gnupg \
  lsb-release \
  locales \
  software-properties-common

sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
sudo add-apt-repository -y universe

if [[ ! -f /etc/apt/sources.list.d/ros2.list ]]; then
  sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu ${UBUNTU_CODENAME:-jammy} main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
else
  echo "ROS 2 repository already exists."
fi

echo
echo "== ROS 2 Humble base and Jonas runtime packages =="
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  python3-numpy \
  python3-rosdep \
  python3-serial \
  python3-setuptools \
  python3-pyqt5 \
  python3-tk \
  ros-"${ROS_DISTRO}"-ros-base \
  ros-"${ROS_DISTRO}"-ament-cmake \
  ros-"${ROS_DISTRO}"-ament-index-python \
  ros-"${ROS_DISTRO}"-rosidl-default-generators \
  ros-"${ROS_DISTRO}"-rosidl-default-runtime \
  ros-"${ROS_DISTRO}"-action-msgs \
  ros-"${ROS_DISTRO}"-builtin-interfaces \
  ros-"${ROS_DISTRO}"-rclpy \
  ros-"${ROS_DISTRO}"-std-msgs \
  ros-"${ROS_DISTRO}"-launch \
  ros-"${ROS_DISTRO}"-launch-ros \
  ros-"${ROS_DISTRO}"-dynamixel-sdk

if [[ "${INSTALL_MATE}" -eq 1 ]]; then
  echo
  echo "== Ubuntu MATE desktop =="
  sudo apt install -y ubuntu-mate-desktop
fi

echo
echo "== rosdep =="
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
else
  echo "rosdep is already initialized."
fi
rosdep update
rosdep install --from-paths src --ignore-src -r -y

echo
echo "== Serial permissions and udev =="
sudo usermod -aG dialout "${USER}"
sudo install -m 0644 "${UDEV_SOURCE}" "${UDEV_TARGET}"
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=tty || true

if systemctl list-unit-files brltty.service >/dev/null 2>&1; then
  sudo systemctl disable --now brltty.service brltty-udev.service 2>/dev/null || true
fi

if dpkg -s brltty >/dev/null 2>&1; then
  sudo apt-get purge -y brltty
fi

echo
echo "== Shell environment =="
if ! grep -qxF "source /opt/ros/${ROS_DISTRO}/setup.bash" "${HOME}/.bashrc"; then
  echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> "${HOME}/.bashrc"
fi

if ! grep -qxF "export ROS_DISTRO=${ROS_DISTRO}" "${HOME}/.bashrc"; then
  echo "export ROS_DISTRO=${ROS_DISTRO}" >> "${HOME}/.bashrc"
fi

WORKSPACE_SOURCE='if [ -f ~/jonas_ws/install/setup.bash ]; then source ~/jonas_ws/install/setup.bash; fi'
if ! grep -qxF "${WORKSPACE_SOURCE}" "${HOME}/.bashrc"; then
  echo "${WORKSPACE_SOURCE}" >> "${HOME}/.bashrc"
fi

cat <<NOTE

Done.

Important next steps:
1. Reboot so dialout permissions and udev aliases are active:
     sudo reboot

2. Verify serial aliases after reconnecting the USB devices:
     ls -l /dev/jonas_usb*

3. Build on the Raspberry Pi:
     cd ~/jonas_ws
     source /opt/ros/${ROS_DISTRO}/setup.bash
     export MAKEFLAGS="-j1"
     colcon build --symlink-install --merge-install --executor sequential \\
       --parallel-workers 1 --cmake-args -DBUILD_TESTING=OFF
     source install/setup.bash

4. Run the robot:
     ros2 launch jonas jonas.launch.py
NOTE
