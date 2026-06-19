#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Carga la configuracion central de hardware para el paquete ROS jonas."""

from dataclasses import dataclass
import json
import os
from pathlib import Path


HARDWARE_CONFIG_ENV = 'JONAS_HARDWARE_CONFIG'
HARDWARE_CONFIG_FILENAME = 'hardware_devices.json'

DEFAULT_DYNAMIXEL_PORT = '/dev/jonas_usb0'
DEFAULT_DYNAMIXEL_BAUDRATE = 1000000
DEFAULT_PROTOCOL_VERSION = 1.0
DEFAULT_MOTOR_IDS = (1, 2, 3, 4, 5, 6)
DEFAULT_MOVING_SPEED = 175
DEFAULT_STEP_DELAY = 0.5
DEFAULT_SETTLE_TIMEOUT = 8.0
DEFAULT_POLL_INTERVAL = 0.1


@dataclass(frozen=True)
class DynamixelHardwareConfig:
    port: str
    baudrate: int
    protocol_version: float
    motor_ids: tuple[int, ...]
    moving_speed: int
    step_delay: float
    settle_timeout: float
    poll_interval: float
    source: str


def _candidate_paths():
    candidates = []
    env_path = os.environ.get(HARDWARE_CONFIG_ENV)

    if env_path:
        candidates.append(Path(env_path).expanduser())

    anchors = (Path(__file__).resolve(), Path.cwd())

    for anchor in anchors:
        anchor_dir = anchor if anchor.is_dir() else anchor.parent

        for parent in (anchor_dir, *anchor_dir.parents):
            candidates.extend(
                (
                    parent / 'config' / HARDWARE_CONFIG_FILENAME,
                    parent / 'jonas' / 'config' / HARDWARE_CONFIG_FILENAME,
                    parent / 'src' / 'jonas' / 'config' / HARDWARE_CONFIG_FILENAME,
                )
            )

    seen = set()

    for candidate in candidates:
        key = str(candidate)

        if key in seen:
            continue

        seen.add(key)
        yield candidate


def _find_config_path():
    env_path = os.environ.get(HARDWARE_CONFIG_ENV)

    if env_path:
        config_path = Path(env_path).expanduser()

        if not config_path.exists():
            raise FileNotFoundError(
                f'{HARDWARE_CONFIG_ENV} apunta a un archivo inexistente: '
                f'{config_path}'
            )

        return config_path

    for candidate in _candidate_paths():
        if candidate.exists():
            return candidate

    return None


def _read_json_config(config_path):
    with config_path.open('r', encoding='utf-8') as config_file:
        data = json.load(config_file)

    if not isinstance(data, dict):
        raise ValueError('El archivo central de hardware debe contener un JSON.')

    return data


def _positive_int(value, field_name):
    parsed_value = int(value)

    if parsed_value <= 0:
        raise ValueError(f'{field_name} debe ser mayor que cero.')

    return parsed_value


def _non_negative_float(value, field_name):
    parsed_value = float(value)

    if parsed_value < 0:
        raise ValueError(f'{field_name} no puede ser negativo.')

    return parsed_value


def _motor_ids(value):
    if not isinstance(value, (list, tuple)):
        raise ValueError('motor_ids debe ser una lista.')

    ids = tuple(int(motor_id) for motor_id in value)

    if not ids:
        raise ValueError('motor_ids no puede estar vacio.')

    if any(motor_id <= 0 for motor_id in ids):
        raise ValueError('Los IDs de motores deben ser positivos.')

    return ids


def _build_config(config, source):
    port = str(config['port']).strip()

    if not port:
        raise ValueError('devices.dynamixel.port no puede estar vacio.')

    return DynamixelHardwareConfig(
        port=port,
        baudrate=_positive_int(config['baudrate'], 'dynamixel.baudrate'),
        protocol_version=float(config['protocol_version']),
        motor_ids=_motor_ids(config['motor_ids']),
        moving_speed=_positive_int(config['moving_speed'], 'moving_speed'),
        step_delay=_non_negative_float(config['step_delay'], 'step_delay'),
        settle_timeout=_non_negative_float(
            config['settle_timeout'],
            'settle_timeout',
        ),
        poll_interval=_non_negative_float(
            config['poll_interval'],
            'poll_interval',
        ),
        source=source,
    )


def load_dynamixel_config():
    config = {
        'port': DEFAULT_DYNAMIXEL_PORT,
        'baudrate': DEFAULT_DYNAMIXEL_BAUDRATE,
        'protocol_version': DEFAULT_PROTOCOL_VERSION,
        'motor_ids': DEFAULT_MOTOR_IDS,
        'moving_speed': DEFAULT_MOVING_SPEED,
        'step_delay': DEFAULT_STEP_DELAY,
        'settle_timeout': DEFAULT_SETTLE_TIMEOUT,
        'poll_interval': DEFAULT_POLL_INTERVAL,
    }
    source = 'defaults'
    config_path = _find_config_path()

    if config_path is not None:
        hardware_data = _read_json_config(config_path)
        dynamixel_data = hardware_data.get('devices', {}).get('dynamixel')

        if not isinstance(dynamixel_data, dict):
            raise ValueError(
                f'{config_path} no define devices.dynamixel correctamente.'
            )

        config.update(dynamixel_data)
        source = str(config_path)

    return _build_config(config, source)

