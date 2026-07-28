import rclpy
from rclpy.node import Node
from mavros_msgs.msg import State


class DroneInfo(Node):
    def __init__(self):
        super().__init__("drone_info")
        self.create_subscription(State, "/mavros/state", self.cb_state, 10)
        self.get_logger().info("drone_info listening...")

    def cb_state(self, msg):
        self.get_logger().info(
            f"connected={msg.connected} armed={msg.armed} mode={msg.mode}"
        )


def main():
    rclpy.init()
    node = DroneInfo()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
