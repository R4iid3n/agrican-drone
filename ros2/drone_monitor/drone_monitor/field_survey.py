"""field_survey - autonomous field-coverage mission.

Flies a boustrophedon ("lawnmower") pattern over the crop field: passes back and
forth along X, stepping over in Y between passes, at a fixed survey altitude. On
completion it switches to RTL so the autopilot returns home and lands.

This extends the single-waypoint fly_to node into a full coverage mission - the basis
for crop scanning or spraying, where the drone must cover every row of the field.

Frame: ENU metres from home (x=East, y=North, z=Up). MAVROS converts to the
autopilot's NED internally.
"""
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import SetMode, CommandBool, CommandTOL


def build_lawnmower(y_min, y_max, y_step, x_min, x_max, alt):
    """Return a list of (x, y, z) waypoints covering the field row by row.

    Each Y pass runs the full X span; the X direction flips every pass so the drone
    snakes across the field instead of flying back to the same side each time.
    """
    waypoints = []
    y = y_min
    flip = False
    while y <= y_max + 1e-6:
        if flip:
            waypoints.append((x_max, y, alt))
            waypoints.append((x_min, y, alt))
        else:
            waypoints.append((x_min, y, alt))
            waypoints.append((x_max, y, alt))
        flip = not flip
        y += y_step
    return waypoints


class FieldSurvey(Node):
    def __init__(self):
        super().__init__("field_survey")

        # --- mission parameters (field: rows Y -14..14, length X ~20, barn at X=-15) ---
        self.alt = 12.0            # survey altitude, well above the 0.5 m crop rows
        self.reach = 1.5           # waypoint reached when within this radius (m)
        self.waypoints = build_lawnmower(
            y_min=-14.0, y_max=14.0, y_step=4.0,   # one pass per crop row
            x_min=-8.0, x_max=8.0,                 # stay inside the field, clear of the barn
            alt=self.alt,
        )
        self.wp_i = 0              # index of the current target waypoint

        # --- state ---
        self.state = State()
        self.x = self.y = self.z = 0.0
        self.took_off_sent = False
        self.airborne = False
        self.mission_done = False

        # telemetry in (pose is best-effort -> sensor QoS, or we get nothing)
        self.create_subscription(State, "/mavros/state", self.cb_state, 10)
        self.create_subscription(
            PoseStamped, "/mavros/local_position/pose",
            self.cb_pose, qos_profile_sensor_data)

        # command out
        self.sp_pub = self.create_publisher(
            PoseStamped, "/mavros/setpoint_position/local", 10)
        self.cli_mode = self.create_client(SetMode, "/mavros/set_mode")
        self.cli_arm = self.create_client(CommandBool, "/mavros/cmd/arming")
        self.cli_takeoff = self.create_client(CommandTOL, "/mavros/cmd/takeoff")

        self.create_timer(1.0, self.sequence)          # mission logic @ 1 Hz
        self.create_timer(0.1, self.stream_setpoint)   # setpoint stream @ 10 Hz
        self.get_logger().info(
            f"field_survey: {len(self.waypoints)} waypoints, alt {self.alt} m")

    # --- callbacks ---
    def cb_state(self, msg):
        self.state = msg

    def cb_pose(self, msg):
        p = msg.pose.position
        self.x, self.y, self.z = p.x, p.y, p.z

    # --- helpers ---
    def call(self, client, req):
        if client.service_is_ready():
            client.call_async(req)

    def dist_to(self, wp):
        """Horizontal distance to a waypoint (altitude held by the setpoint)."""
        return math.hypot(wp[0] - self.x, wp[1] - self.y)

    # --- mission state machine (one action per tick) ---
    def sequence(self):
        if not self.state.connected:
            self.get_logger().info("waiting for FCU connection..."); return
        if self.state.mode != "GUIDED" and not self.mission_done:
            self.call(self.cli_mode, SetMode.Request(custom_mode="GUIDED"))
            self.get_logger().info("requesting GUIDED..."); return
        if not self.state.armed and not self.mission_done:
            self.call(self.cli_arm, CommandBool.Request(value=True))
            self.get_logger().info("requesting ARM (waits for EKF/GPS)..."); return
        if not self.took_off_sent:
            self.call(self.cli_takeoff, CommandTOL.Request(altitude=self.alt))
            self.took_off_sent = True
            self.get_logger().info(f"takeoff to {self.alt} m commanded"); return
        if not self.airborne:
            if self.z < 2.0:
                self.get_logger().info(f"climbing... alt={self.z:.1f} m"); return
            self.airborne = True
            self.get_logger().info("airborne - starting field survey")
            return

        # --- survey: advance through the waypoint list ---
        if self.wp_i < len(self.waypoints):
            wp = self.waypoints[self.wp_i]
            d = self.dist_to(wp)
            if d < self.reach:
                self.get_logger().info(
                    f"reached wp {self.wp_i + 1}/{len(self.waypoints)} "
                    f"({wp[0]:+.0f},{wp[1]:+.0f})")
                self.wp_i += 1
            else:
                self.get_logger().info(
                    f"-> wp {self.wp_i + 1}/{len(self.waypoints)} "
                    f"({wp[0]:+.0f},{wp[1]:+.0f})  dist={d:4.1f} m")
            return

        # --- done: return to launch and land ---
        if not self.mission_done:
            self.call(self.cli_mode, SetMode.Request(custom_mode="RTL"))
            self.mission_done = True
            self.get_logger().info("survey complete - RTL (returning home to land)")

    def stream_setpoint(self):
        # stream only while flying the survey; not during takeoff (blocks climb) or RTL
        if not self.airborne or self.mission_done:
            return
        if self.wp_i >= len(self.waypoints):
            return
        wp = self.waypoints[self.wp_i]
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.pose.position.x = wp[0]
        msg.pose.position.y = wp[1]
        msg.pose.position.z = wp[2]
        self.sp_pub.publish(msg)


def main():
    rclpy.init()
    node = FieldSurvey()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
