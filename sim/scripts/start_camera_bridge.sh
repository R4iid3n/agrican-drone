#!/usr/bin/env bash
# Bridge the drone's downward Gazebo camera to a ROS 2 topic.
# gz topic /camera (gz.msgs.Image)  -->  ROS 2 /camera (sensor_msgs/msg/Image)
# Run alongside the sim, then: ros2 run drone_monitor crop_scan
source /opt/ros/jazzy/setup.bash
exec ros2 run ros_gz_bridge parameter_bridge \
  "/camera@sensor_msgs/msg/Image[gz.msgs.Image"
