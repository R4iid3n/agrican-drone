import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State #to READ current mode/armed
from mavros_msgs.srv import SetMode, CommandBool, CommandTOL


class FlyTo(Node):
    def __init__(self):
        super().__init__("fly_to")
        self.took_off_sent = False
        # target (ENU metres from home): 10m East, 5m North, 10m up
        self.tx, self.ty, self.tz = 10.0, 5.0, 10.0
        # altitude tracking + flags 
        self.cur_z = 0.0
        self.airborne = False
        self.create_subscription(PoseStamped,'mavros/local_position/pose',self.cb_pose,qos_profile_sensor_data)
        #latest FCU state 
        self.state = State()
        self.create_subscription(State,'/mavros/state',self.cb_state,10)
        # Publisher: streams position setpoints to MAVROS
        self.sp_pub = self.create_publisher(
            PoseStamped, "/mavros/setpoint_position/local", 10
        )
        # service clients (talk to MAVROS services)
        self.cli_mode = self.create_client(SetMode, "/mavros/set_mode")
        self.cli_arm = self.create_client(CommandBool, "/mavros/cmd/arming")
        self.cli_takeoff = self.create_client(CommandTOL, "/mavros/cmd/takeoff")

        self.create_timer(1.0, self.sequence)  # run sequence once/sec
        self.create_timer(0.1, self.stream_setpoint)  # stream target @10Hz
        self.get_logger().info("fly_to starting...")
        
    def cb_state(self,msg):
        self.state = msg #remember mode + armed
        
    def cb_pose(self,msg):
        self.cur_z = msg.pose.position.z

    def sequence(self):
        if not self.state.connected: 
            self.get_logger().info('waiting for FCU connection...');return
        #1 force GUIDED (retry until it sticks)
        if self.state.mode != 'GUIDED':
            self.call(self.cli_mode,SetMode.Request(custom_mode='GUIDED'))
            self.get_logger().info('requesting GUIDED...'); return 
        #2 arm (retry every sec until armed - rides out PreArm-not-ready)
        if not self.state.armed:
            self.call(self.cli_arm,CommandBool.Request(value=True))
            self.get_logger().info('requesting ARM (waits for EKF/GPS)...');return
        #3 takeoff once (not every tick - repeat resets the climb)
        if not self.took_off_sent:
            self.call(self.cli_takeoff,CommandTOL.Request(altitude=self.tz))
            self.took_off_sent=True
            self.get_logger().info(f'takeoff to {self.tz}m commanded');return
        #3b wait until actually climbing (needs Fix 1 or cur_z stays 0)
        if self.cur_z < 2.0:
            self.get_logger().info(f'climbing... alt={self.cur_z:.1f}m');return
        #4 airborne - now allow streaming to fly to target
        if not self.airborne:
            self.airborne = True
            self.get_logger().info('airborne - flying to target')
            
    def stream_setpoint(self):
        if not self.airborne: # dont stream during takeoff, it blocks climb 
            return
        # MUST publish continuously or ArduPilot ignores guided target
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.pose.position.x = self.tx
        msg.pose.position.y = self.ty
        msg.pose.position.z = self.tz
        self.sp_pub.publish(msg)

    def call(self,client,req):
        if client.service_is_ready():
            client.call_async(req)


def main():
    rclpy.init()
    node = FlyTo()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
