# Jonas ROS 2 - instalacion de dependencias

Este directorio contiene los paquetes ROS 2 locales del robot Jonas:

- `jonas_interfaces`: servicios y acciones personalizados.
- `jonas`: nodos para movimiento de articulaciones y secuencias.
- `wheels_motor`: nodos e interfaces para control de ruedas.
- `interface_rpi`: interfaz grafica para la pantalla del robot.
- `interface_pc`: interfaz grafica para control remoto desde PC.

Las instrucciones estan pensadas para Ubuntu 22.04 con ROS 2 Humble.

## 1. Cargar ROS 2

```bash
source /opt/ros/humble/setup.bash
export ROS_DISTRO=humble
```

Si se quiere dejar cargado automaticamente en cada terminal:

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "export ROS_DISTRO=humble" >> ~/.bashrc
```

## 2. Instalar herramientas base

```bash
sudo apt update
sudo apt install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-setuptools
```

Si `rosdep` nunca fue inicializado en la maquina:

```bash
sudo rosdep init
rosdep update
```

Si `sudo rosdep init` indica que ya existe, solo ejecutar:

```bash
rosdep update
```

## 3. Instalar dependencias ROS 2 y Python

Estos paquetes cubren las dependencias declaradas en los `package.xml`, los imports Python usados por los nodos y las interfaces graficas:

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

Dependencias principales que cubre cada grupo:

- `rclpy`, `std_msgs`, `launch`, `launch_ros`: nodos y archivos launch.
- `ament_cmake`, `rosidl_default_generators`, `rosidl_default_runtime`, `action_msgs`, `builtin_interfaces`: generacion y uso de `jonas_interfaces`.
- `python3-numpy`: calculos numericos en movimiento y ruedas.
- `python3-serial`: comunicacion serial con Arduinos mediante `pyserial`.
- `python3-pyqt5`: interfaces graficas de PC y RPi.
- `python3-tk`: interfaz alternativa de ruedas basada en Tkinter.
- `ros-${ROS_DISTRO}-dynamixel-sdk`: comunicacion con servomotores Dynamixel.

## 4. Dependencias para tests

Solo son necesarias si se van a correr pruebas con `colcon test`:

```bash
sudo apt install -y \
  python3-pytest \
  ros-${ROS_DISTRO}-ament-copyright \
  ros-${ROS_DISTRO}-ament-flake8 \
  ros-${ROS_DISTRO}-ament-pep257
```

## 5. Permisos para puertos seriales

Los nodos usan puertos como `/dev/ttyUSB0`, `/dev/ttyUSB1` y `/dev/ttyUSB2`. Para acceder sin ejecutar ROS con `sudo`:

```bash
sudo usermod -aG dialout $USER
```

Despues de este comando, cerrar sesion y volver a entrar. Tambien se puede reiniciar la maquina.

Para revisar si el usuario ya pertenece al grupo:

```bash
groups
```

## 6. Instalar dependencias con rosdep

Desde la raiz del workspace:

```bash
cd ~/jonas_ws
rosdep install --from-paths src --ignore-src -r -y
```

Nota: `rosdep` instala dependencias declaradas en los `package.xml`. En este workspace tambien conviene ejecutar el comando completo de la seccion 3, porque algunas dependencias Python usadas por los nodos aparecen en los imports o en `setup.py`.

## 7. Compilar el workspace

Los paquetes `jonas_interfaces`, `jonas`, `wheels_motor`, `interface_rpi` e `interface_pc` son paquetes locales del workspace. No se instalan con `apt`; se compilan con `colcon`:

### Opcion normal

En una PC o laptop:

```bash
cd ~/jonas_ws
colcon build --symlink-install
source install/setup.bash
```

### Opcion recomendada para Raspberry Pi 4

En una RPi4 conviene limitar `colcon` a un solo proceso para evitar quedarse sin RAM:

```bash
cd ~/jonas_ws
export MAKEFLAGS="-j1"
COLCON_RPI_ARGS="--symlink-install --merge-install --executor sequential --parallel-workers 1"

colcon build \
  $COLCON_RPI_ARGS \
  --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash
```

Que hace cada opcion:

- `--parallel-workers 1`: compila un paquete a la vez.
- `--executor sequential`: evita ejecucion paralela entre paquetes.
- `MAKEFLAGS="-j1"`: evita compilacion paralela dentro de paquetes CMake.
- `--merge-install`: reduce cantidad de archivos de entorno en `install`.
- `--symlink-install`: evita copiar archivos Python innecesariamente.
- `-DBUILD_TESTING=OFF`: evita preparar objetivos de test durante el build.

### Opcion paquete por paquete

Si la RPi4 sigue muy cargada, compilar de forma incremental:

```bash
cd ~/jonas_ws
export MAKEFLAGS="-j1"
COLCON_RPI_ARGS="--symlink-install --merge-install --executor sequential --parallel-workers 1"

colcon build $COLCON_RPI_ARGS --packages-select jonas_interfaces --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash

colcon build $COLCON_RPI_ARGS --packages-select wheels_motor --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash

colcon build $COLCON_RPI_ARGS --packages-select interface_rpi --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash

colcon build $COLCON_RPI_ARGS --packages-select interface_pc --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash

colcon build $COLCON_RPI_ARGS --packages-select jonas --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash
```

Orden recomendado:

- Primero `jonas_interfaces`, porque genera los servicios y acciones.
- Luego paquetes independientes: `wheels_motor`, `interface_rpi`, `interface_pc`.
- Al final `jonas`, porque depende de `jonas_interfaces`.

Si en la RPi4 solo se usara el launch principal del robot, normalmente bastan:

```bash
cd ~/jonas_ws
export MAKEFLAGS="-j1"
COLCON_RPI_ARGS="--symlink-install --merge-install --executor sequential --parallel-workers 1"

colcon build $COLCON_RPI_ARGS --packages-select jonas_interfaces --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash

colcon build $COLCON_RPI_ARGS --packages-select wheels_motor --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash

colcon build $COLCON_RPI_ARGS --packages-select interface_rpi --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash

colcon build $COLCON_RPI_ARGS --packages-select jonas --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash
```

Si se cambia entre la opcion normal y la opcion con `--merge-install`, limpiar primero los directorios generados:

```bash
cd ~/jonas_ws
rm -rf build install log
```

### Si la RPi4 se queda sin memoria

Revisar memoria disponible:

```bash
free -h
```

Crear swap temporal de 2 GB:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
swapon --show
```

Al terminar la compilacion, se puede apagar y borrar esa swap:

```bash
sudo swapoff /swapfile
sudo rm /swapfile
```

Recomendaciones practicas para la RPi4:

- Compilar por SSH, sin entorno grafico pesado abierto.
- Usar fuente de poder estable y buena ventilacion.
- Instalar dependencias por `apt`, no compilar librerias externas con `pip`.
- No ejecutar `colcon test` en la RPi4 salvo que sea necesario.

Para cargar automaticamente este workspace en cada terminal:

```bash
echo "source ~/jonas_ws/install/setup.bash" >> ~/.bashrc
```

## 8. Comandos de launch

Launch principal del robot:

```bash
ros2 launch jonas jonas.launch.py
```

Launch para PC remoto:

```bash
ros2 launch jonas remote_pc.launch.py
```

## 9. Verificacion rapida

Despues de instalar dependencias y compilar:

```bash
source /opt/ros/humble/setup.bash
source ~/jonas_ws/install/setup.bash
ros2 pkg list | grep jonas
```

Tambien se puede verificar que Python encuentre los modulos externos:

```bash
python3 - <<'PY'
import numpy
import serial
import PyQt5
import dynamixel_sdk
import rclpy
print("Dependencias Python OK")
PY
```
