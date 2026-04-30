from glob import glob

from setuptools import find_packages, setup

package_name = 'jonas'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=[
        'setuptools',
        'numpy',
        'dynamixel-sdk',
    ],
    zip_safe=True,
    maintainer='mpuchuri',
    maintainer_email='mpuchuri@utec.edu.pe',
    author='UTEC - Universidad de Ingenieria y Tecnologia, Lima, Peru',
    author_email='mpuchuri@utec.edu.pe',
    description=(
        'ROS 2 nodes for Jonas joint motion and sequence control. '
        'Edited and maintained by mpuchuri@utec.edu.pe for UTEC, '
        'Lima, Peru.'
    ),
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'motor_movement = jonas.motor_movement:main',
            'sequence_planner = jonas.sequence_planner:main',
        ],
    },
)
