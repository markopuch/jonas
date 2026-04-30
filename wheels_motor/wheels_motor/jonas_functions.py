#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import time

import numpy as np
import serial

# Dimensiones del robot
l = 0.18  # Distancia del centro a cada rueda
r = 0.1524  # Radio de las ruedas

# Velocidad maxima de las ruedas (rad/s)
vw_max = 8.5

# Configuracion serial de los arduinos
SERIAL_PORTS = (
    '/dev/jonas_usb1',
    '/dev/jonas_usb2',
    '/dev/jonas_usb3',
)
SERIAL_BAUDRATE = 9600
SERIAL_BOOT_DELAY = 2.0
SERIAL_RESPONSE_DELAY = 0.15

arduino1 = None
arduino2 = None
arduino3 = None


def initialize_serial_ports():
    global arduino1, arduino2, arduino3

    if all(port is not None and port.is_open for port in (arduino1, arduino2, arduino3)):
        return

    close_serial_ports()

    arduino1 = serial.Serial(SERIAL_PORTS[0], SERIAL_BAUDRATE, timeout=1)
    arduino2 = serial.Serial(SERIAL_PORTS[1], SERIAL_BAUDRATE, timeout=1)
    arduino3 = serial.Serial(SERIAL_PORTS[2], SERIAL_BAUDRATE, timeout=1)
    time.sleep(SERIAL_BOOT_DELAY)
    clear_serial_input_buffers()


def close_serial_ports():
    global arduino1, arduino2, arduino3

    for port in (arduino1, arduino2, arduino3):
        if port is not None and port.is_open:
            port.close()

    arduino1 = None
    arduino2 = None
    arduino3 = None


def get_serial_ports():
    return (arduino1, arduino2, arduino3)


def clear_serial_input_buffers():
    for port in get_serial_ports():
        if port is not None and port.is_open:
            port.reset_input_buffer()


def _format_serial_payload(speed):
    """Formatear la trama serial esperada por cada controlador."""
    numeric_speed = float(speed)

    if abs(numeric_speed) < 1e-9:
        numeric_speed = 0.0

    return f'{numeric_speed:.4f}\n'.encode('ascii')


def _read_serial_port(port):
    waiting = port.in_waiting

    if waiting <= 0:
        return b''

    return port.read(waiting)


def _build_serial_debug_entry(port, tx_payload, rx_payload):
    tx_text = tx_payload.decode('ascii', errors='replace').rstrip('\r\n')
    rx_text = rx_payload.decode('utf-8', errors='replace').strip()

    return {
        'port': port.port,
        'tx_payload': tx_payload,
        'tx_text': tx_text,
        'rx_payload': rx_payload,
        'rx_text': rx_text,
    }


def read_serial_feedback():
    """Leer la trama actualmente disponible en cada puerto serial."""
    initialize_serial_ports()

    feedback = []

    for port in get_serial_ports():
        rx_payload = _read_serial_port(port)
        feedback.append(_build_serial_debug_entry(port, b'', rx_payload))

    return feedback


def lim_wheels_speed(wheels_des_speed):
    """Limitar la velocidad angular deseada de cada rueda."""
    w_lim = np.array([-vw_max, vw_max])

    for i in range(3):
        if wheels_des_speed[i] < w_lim[0]:
            wheels_des_speed[i] = w_lim[0]
        elif wheels_des_speed[i] > w_lim[1]:
            wheels_des_speed[i] = w_lim[1]

    return wheels_des_speed


def fkine(vel_wheels):
    """Cinematica directa."""
    vx = (math.sqrt(3) * r * (-vel_wheels[0] + vel_wheels[1])) / 3
    vy = (r * (-vel_wheels[0] - vel_wheels[1] + 2 * vel_wheels[2])) / 3
    w = -(r * (vel_wheels[0] + vel_wheels[1] + vel_wheels[2])) / (3 * l)

    vel_robot = np.array([vx, vy, w])

    return vel_robot


def ikine(vel_robot):
    """Cinematica inversa."""
    vw1 = -(math.sqrt(3) * vel_robot[0] + vel_robot[1] + 2 * vel_robot[2] * l) / (2 * r)
    vw2 = (math.sqrt(3) * vel_robot[0] - vel_robot[1] - 2 * vel_robot[2] * l) / (2 * r)
    vw3 = (vel_robot[1] - vel_robot[2] * l) / r

    vel_wheels = np.array([vw1, vw2, vw3])

    return vel_wheels


def send_vel_robot(vx, vy, w, return_debug=False):
    """Enviar velocidades angulares deseadas a los arduinos."""
    vel_robot = np.array([vx, vy, w])
    vel_wheels = ikine(vel_robot)
    return send_vel_wheels(*vel_wheels, return_debug=return_debug)


def send_vel_wheels(w1, w2, w3, return_debug=False):
    """Enviar velocidades angulares deseadas directamente a cada rueda."""
    initialize_serial_ports()

    vel_wheels = np.array([w1, w2, w3], dtype=float)
    vel_wheels = lim_wheels_speed(vel_wheels)
    vel_wheels = np.round(vel_wheels, 4)
    vel_wheels[np.isclose(vel_wheels, 0.0, atol=1e-4)] = 0.0

    clear_serial_input_buffers()

    serial_debug = []

    for port, wheel_speed in zip(get_serial_ports(), vel_wheels):
        payload = _format_serial_payload(wheel_speed)
        port.write(payload)
        port.flush()
        serial_debug.append(
            {
                'port': port.port,
                'tx_payload': payload,
                'tx_text': payload.decode('ascii').rstrip('\r\n'),
                'rx_payload': b'',
                'rx_text': '',
            }
        )

    time.sleep(SERIAL_RESPONSE_DELAY)

    for index, port in enumerate(get_serial_ports()):
        rx_payload = _read_serial_port(port)
        serial_debug[index] = _build_serial_debug_entry(
            port,
            serial_debug[index]['tx_payload'],
            rx_payload,
        )

    if return_debug:
        return vel_wheels, serial_debug

    return vel_wheels


# Velocidades maximas del robot
vx_max = fkine(np.array([-vw_max, vw_max, 0]))[0]  # m/s
vy_max = fkine(np.array([-vw_max / 2, -vw_max / 2, vw_max]))[1]  # m/s
w_max = fkine(np.array([-vw_max, -vw_max, -vw_max]))[2]  # rad/s
vxy_max = (vw_max * 2 * r) / (1 + math.sqrt(3))
