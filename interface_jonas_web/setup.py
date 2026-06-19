import os
from glob import glob

from setuptools import find_packages, setup


package_name = 'interface_jonas_web'


def package_files(destination, source):
    entries = []
    for root, _, files in os.walk(source):
        selected = [os.path.join(root, file_name) for file_name in files]
        if selected:
            relative_root = os.path.relpath(root, source)
            install_root = destination
            if relative_root != '.':
                install_root = os.path.join(destination, relative_root)
            entries.append((install_root, selected))
    return entries


data_files = [
    ('share/ament_index/resource_index/packages',
        ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
]
data_files.extend(package_files(os.path.join('share', package_name, 'web'), 'web'))


setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=data_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mpuchuri',
    maintainer_email='mpuchuri@utec.edu.pe',
    author='UTEC - Universidad de Ingenieria y Tecnologia, Lima, Peru',
    author_email='mpuchuri@utec.edu.pe',
    description=(
        'Web interface for tablet control of Jonas through ROS 2 Humble '
        'and rosbridge.'
    ),
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'web_server_node = interface_jonas_web.web_server_node:main',
            'safety_gateway_node = interface_jonas_web.safety_gateway_node:main',
            'demo_status_node = interface_jonas_web.demo_status_node:main',
            'test_cmd_vel_node = interface_jonas_web.test_cmd_vel_node:main',
        ],
    },
)
