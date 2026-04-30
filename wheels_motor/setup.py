from setuptools import find_packages, setup

package_name = 'wheels_motor'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools',
        'numpy',
        'pyserial',
        'PyQt5',
    ],
    zip_safe=True,
    maintainer='mpuchuri',
    maintainer_email='mpuchuri@utec.edu.pe',
    author='UTEC - Universidad de Ingenieria y Tecnologia, Lima, Peru',
    author_email='mpuchuri@utec.edu.pe',
    description=(
        'ROS 2 control package for the Jonas mobile base. '
        'Edited and maintained by mpuchuri@utec.edu.pe for UTEC, '
        'Lima, Peru.'
    ),
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'jonas_control = wheels_motor.jonas_control:main',
            'jonas_wheels_interface = '
            'wheels_motor.jonas_wheels_interface:main',
            'jonas_pc_style_interface = '
            'wheels_motor.jonas_pc_style_interface:main',
        ],
    },
)
