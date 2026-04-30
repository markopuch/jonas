from setuptools import find_packages, setup

package_name = 'interface_pc'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mpuchuri',
    maintainer_email='mpuchuri@utec.edu.pe',
    author='UTEC - Universidad de Ingenieria y Tecnologia, Lima, Peru',
    author_email='mpuchuri@utec.edu.pe',
    description=(
        'ROS 2 graphical interface for remote PC control of Jonas. '
        'Edited and maintained by mpuchuri@utec.edu.pe for UTEC, '
        'Lima, Peru.'
    ),
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'interface_pc = interface_pc.node_interface:main'
        ],
    },
)
