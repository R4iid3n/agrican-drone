"""crop_scan - estimates crop coverage from the downward camera during a survey.

Subscribes to the drone's downward camera (bridged from Gazebo) and, for each frame,
computes a vegetation index: the fraction of pixels that read as green plant matter
(Excess Green > threshold). Combined with the drone's position, it reports how much
crop cover was seen over each field row - the kind of output a real crop-scanning
drone would produce.

Pipeline:  Gazebo camera --ros_gz_bridge--> /camera (sensor_msgs/Image) --> this node
Run the bridge first:
    ros2 run ros_gz_bridge parameter_bridge /camera@sensor_msgs/msg/Image[gz.msgs.Image
"""
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float32


class CropScan(Node):
    def __init__(self):
        super().__init__("crop_scan")

        self.veg_threshold = 20      # Excess-Green value above which a pixel is "plant"
        self.y = 0.0                 # current North position, to bucket by field row
        self.row_spacing = 4.0       # crop rows are spaced 4 m in Y
        self.row_cover = {}          # row index -> [sum coverage, sample count]

        self.create_subscription(
            PoseStamped, "/mavros/local_position/pose",
            self.cb_pose, qos_profile_sensor_data)
        self.create_subscription(Image, "/camera", self.cb_image, 10)

        # publish the live coverage so it can be plotted / echoed
        self.cover_pub = self.create_publisher(Float32, "/crop_coverage", 10)

        self.create_timer(10.0, self.report)   # periodic per-row summary
        self.get_logger().info("crop_scan: waiting for /camera frames...")

    def cb_pose(self, msg):
        self.y = msg.pose.position.y

    def cb_image(self, msg):
        # decode the raw image into an (H, W, 3) uint8 array
        buf = np.frombuffer(bytes(msg.data), dtype=np.uint8)
        try:
            img = buf.reshape(msg.height, msg.width, 3).astype(np.int16)
        except ValueError:
            return  # unexpected size / encoding
        if msg.encoding == "bgr8":
            b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
        else:  # rgb8 (Gazebo default)
            r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]

        # Excess Green index: highlights living plant matter vs soil
        exg = 2 * g - r - b
        coverage = float((exg > self.veg_threshold).mean() * 100.0)

        # bucket the reading by nearest field row (in Y)
        row = int(round(self.y / self.row_spacing))
        s = self.row_cover.setdefault(row, [0.0, 0])
        s[0] += coverage
        s[1] += 1

        self.cover_pub.publish(Float32(data=coverage))
        self.get_logger().info(
            f"y={self.y:+5.1f}  crop cover={coverage:5.1f} %")

    def report(self):
        if not self.row_cover:
            return
        self.get_logger().info("--- crop coverage by row (Y) ---")
        for row in sorted(self.row_cover):
            total, n = self.row_cover[row]
            avg = total / n if n else 0.0
            bar = "#" * int(avg / 5)
            self.get_logger().info(f"  y={row * self.row_spacing:+5.1f} m : {avg:5.1f} % {bar}")


def main():
    rclpy.init()
    node = CropScan()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
