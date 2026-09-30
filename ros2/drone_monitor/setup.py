from setuptools import find_packages, setup

package_name = 'drone_monitor'

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
    maintainer='r4iid3n',
    maintainer_email='r4iid3n@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'drone_info = drone_monitor.drone_info:main',
            'fly_to = drone_monitor.fly_to:main',
            'field_survey = drone_monitor.field_survey:main',
            'crop_scan = drone_monitor.crop_scan:main'
        ],
    },
)
