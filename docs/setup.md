# Setup & Run Guide

Target platform: **Ubuntu 24.04 LTS**. The version pairing below is deliberate —
ROS 2 Jazzy, Gazebo Harmonic, and the ArduPilot JSON backend are the combination that
works together on 24.04.

## 1. Prerequisites

Install, in order:

1. **ROS 2 Jazzy** (`ros-jazzy-desktop`) + `ros-dev-tools`.
2. **Gazebo Harmonic** (`gz sim`) — pulled in with the ROS 2 `ros_gz` integration.
3. **MAVROS** for Jazzy (`ros-jazzy-mavros`).
4. **ArduPilot** source, built for SITL (provides `sim_vehicle.py`).
5. **ardupilot_gazebo** plugin, built against Harmonic (provides
   `libArduPilotPlugin.so` and the `iris` models/worlds).
6. **MAVProxy** (`pip install MAVProxy`).

Environment (in `~/.bashrc`):

```bash
source /opt/ros/jazzy/setup.bash
export PATH=$PATH:$HOME/ardupilot/Tools/autotest
export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/ardupilot_gazebo/build:$GZ_SIM_SYSTEM_PLUGIN_PATH
export GZ_SIM_RESOURCE_PATH=$HOME/ardupilot_gazebo/models:$HOME/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH
```

## 2. Build the ROS 2 package

```bash
mkdir -p ~/ros2_ws/src
cp -r ros2/drone_monitor ~/ros2_ws/src/
cd ~/ros2_ws
colcon build --packages-select drone_monitor
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
source ~/ros2_ws/install/setup.bash
```

## 3. Install the helper scripts

```bash
cp sim/scripts/start_mavros.sh ~/start_mavros.sh
cp sim/scripts/sim-quiet ~/.local/bin/sim-quiet
chmod +x ~/.local/bin/sim-quiet
```

`sim-quiet` runs Gazebo **headless** (`gz sim -s`, no 3D window) to save CPU; run
`sim-quiet view` to open the 3D view on demand.

## 4. Run — four terminals

Start them in order and wait for each to be ready before the next.

**Terminal 1 — Gazebo (physics running):**
```bash
sim-quiet -v4 -r iris_runway.sdf
```
The world must be *playing* (the `-r` flag). If Gazebo is paused, the SITL JSON
backend stalls waiting for sensor data.

**Terminal 2 — ArduPilot SITL:**
```bash
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --console --out=127.0.0.1:14551
```
- `--model JSON` selects the FDM protocol the Gazebo plugin expects (mandatory).
- `--out=127.0.0.1:14551` adds a dedicated MAVLink stream for MAVROS.

Wait until the console prints `Received N parameters` and the SITL window scrolls
`JSON received:` — that confirms the ArduPilot ↔ Gazebo link is live.

**Terminal 3 — MAVROS bridge:**
```bash
bash ~/start_mavros.sh
```
Wait for `CON: Got HEARTBEAT, connected. FCU: ArduPilot`.

**Terminal 4 — a ROS 2 node.** Telemetry:
```bash
ros2 run drone_monitor drone_info
# -> connected=True armed=False mode=STABILIZE
```
Or an autonomous flight (allow ~30 s after connection for the EKF/GPS to be arm-ready):
```bash
ros2 run drone_monitor fly_to
# -> requesting GUIDED... -> ARM... -> takeoff... -> climbing... -> airborne - flying to target
```

## 5. Verify the flight

```bash
ros2 topic echo /mavros/local_position/pose --once
# position x/y/z should approach the target (10, 5, 10)
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Gazebo floods `Incorrect protocol magic 0 should be 18458` | SITL using the legacy Gazebo backend | Launch SITL with `--model JSON` |
| SITL stuck at `Waiting for heartbeat`, Gazebo shows nothing | Gazebo paused / not stepping | Launch Gazebo with `-r`; confirm the clock advances |
| MAVROS stays `connected: false` | No MAVLink reaching it | Ensure SITL has `--out=127.0.0.1:14551`; check the `fcu_url` in `start_mavros.sh` |
| ROS node gets no position data | Wrong QoS on a best-effort topic | Subscribe with `qos_profile_sensor_data` |
| Drone arms then disarms in a loop, never climbs | Position setpoint streamed during takeoff, or altitude never read | Gate the setpoint stream on the airborne flag; use sensor QoS on `/mavros/local_position/pose` |
| `Package 'drone_monitor' not found` | Workspace not sourced | `source ~/ros2_ws/install/setup.bash` |
