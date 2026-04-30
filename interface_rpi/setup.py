from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'interface_rpi'

face_files = []
for face_file in glob(os.path.join(package_name, 'faces', '*', '*.png')):
    install_dir = os.path.join(
        'share',
        package_name,
        os.path.dirname(os.path.relpath(face_file, package_name)),
    )
    face_files.append((install_dir, [face_file]))

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ] + face_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mpuchuri',
    maintainer_email='mpuchuri@utec.edu.pe',
    author='UTEC - Universidad de Ingenieria y Tecnologia, Lima, Peru',
    author_email='mpuchuri@utec.edu.pe',
    description=(
        'ROS 2 graphical interface for the Jonas robot face display. '
        'Edited and maintained by mpuchuri@utec.edu.pe for UTEC, '
        'Lima, Peru.'
    ),
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'interface_rpi = interface_rpi.node_interface:main'
        ],
    },
)
