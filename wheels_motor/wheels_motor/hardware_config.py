#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Carga la configuracion central de hardware para wheels_motor."""

from dataclasses import dataclass
import json
import os
from pathlib import Path


HARDWARE_CONFIG_ENV = 'JONAS_HARDWARE_CONFIG'
HARDWARE_CONFIG_FILENAME = 'hardware_devices.json'
WHEEL_DEVICE_KEYS = ('arduino_1', 'arduino_2', 'arduino_3')

DEFAULT_PORTS = (
    '/dev/jonas_usb1',
    '/dev/jonas_usb2',
    '/dev/jonas_usb3',
)
DEFAULT_BAUDRATE = 9600
DEFAULT_BOOT_DELAY = 2.0
DEFAULT_RESPONSE_DELAY = 0.15


@dataclass(frozen=True)
class WheelsHardwareConfig:
    ports: tuple[str, ...]
    baudrate: int
    boot_delay: float
    response_delay: float
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


def _validate_ports(ports):
    normalized_ports = tuple(str(port).strip() for port in ports if str(port).strip())

    if len(normalized_ports) != len(WHEEL_DEVICE_KEYS):
        raise ValueError(
            'Se esperaban '
            f'{len(WHEEL_DEVICE_KEYS)} puertos de ruedas y se recibieron '
            f'{len(normalized_ports)}: {normalized_ports}'
        )

    return normalized_ports


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


def _wheels_data_to_config(wheels_data, source):
    ports = []

    for device_key in WHEEL_DEVICE_KEYS:
        device_data = wheels_data.get(device_key)

        if not isinstance(device_data, dict):
            raise ValueError(f'Falta devices.wheels.{device_key}.')

        ports.append(device_data.get('port', ''))

    return WheelsHardwareConfig(
        ports=_validate_ports(ports),
        baudrate=_positive_int(
            wheels_data.get('baudrate', DEFAULT_BAUDRATE),
            'wheels.baudrate',
        ),
        boot_delay=_non_negative_float(
            wheels_data.get('boot_delay', DEFAULT_BOOT_DELAY),
            'wheels.boot_delay',
        ),
        response_delay=_non_negative_float(
            wheels_data.get('response_delay', DEFAULT_RESPONSE_DELAY),
            'wheels.response_delay',
        ),
        source=source,
    )


def load_wheels_config():
    config_path = _find_config_path()

    if config_path is None:
        return WheelsHardwareConfig(
            ports=DEFAULT_PORTS,
            baudrate=DEFAULT_BAUDRATE,
            boot_delay=DEFAULT_BOOT_DELAY,
            response_delay=DEFAULT_RESPONSE_DELAY,
            source='defaults',
        )

    hardware_data = _read_json_config(config_path)
    wheels_data = hardware_data.get('devices', {}).get('wheels')

    if not isinstance(wheels_data, dict):
        raise ValueError(f'{config_path} no define devices.wheels correctamente.')

    return _wheels_data_to_config(wheels_data, str(config_path))
