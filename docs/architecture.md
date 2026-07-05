# Architecture

## Components

| Component        | Role                                                                 |
|------------------|----------------------------------------------------------------------|
| **Gazebo**       | Simulates the physical world: 3D scene, rigid-body dynamics, sensors (IMU, GPS), and the drone airframe. |
| **ArduPilot SITL** | The flight controller. Real ArduCopter firmware compiled for Linux; runs the same estimation and control loops as on a real drone. |
| **MAVProxy**     | Ground control station (GCS). Connects over MAVLink, offers a console + map, and fans the MAVLink stream out to other clients. |
| **MAVROS**       | Bridge node. Translates between MAVLink (autopilot side) and ROS 2 topics/services (autonomy side). |
| **drone_monitor** | Custom ROS 2 package. `drone_info` consumes telemetry; `fly_to` issues commands. |

## Data flow

```
 drone_monitor (ROS 2 nodes)
        │  topics: /mavros/state, /mavros/local_position/pose, ...
        │  services: /mavros/set_mode, /mavros/cmd/arming, /mavros/cmd/takeoff
        ▼
     MAVROS
        │  MAVLink over UDP
        ▼
   MAVProxy  ──MAVLink(TCP:5760)──  ArduPilot SITL
                                         │  JSON FDM over UDP (servo out / sensors in)
                                         ▼
                                      Gazebo
```

Two distinct links matter:

1. **ArduPilot ↔ Gazebo** — a lock-stepped UDP exchange using ArduPilot's *JSON*
   flight-dynamics-model (FDM) backend. Each physics step, SITL sends servo/motor
   commands to Gazebo and Gazebo returns IMU/GPS/pose. Selecting this backend
   (`--model JSON`) is required: the installed Gazebo plugin speaks the JSON protocol,
   not ArduPilot's older native-Gazebo one.

2. **ArduPilot ↔ ROS 2** — MAVLink from SITL, forwarded by MAVProxy, terminated by
   MAVROS, and re-published as ROS 2 interfaces.

## Port map

| Port          | Direction                | Purpose                                  |
|---------------|--------------------------|------------------------------------------|
| TCP 5760      | SITL ↔ MAVProxy          | Primary MAVLink master link              |
| UDP 14550     | MAVProxy → clients       | Default GCS output stream                |
| UDP 14551     | MAVProxy → MAVROS        | Dedicated stream feeding the ROS 2 bridge |
| UDP 9002/9003 | SITL ↔ Gazebo            | JSON FDM (servo out / sensor in)         |

## ROS 2 interfaces used

**Subscribed (telemetry, published by MAVROS):**

| Topic                            | Type                        | QoS          |
|----------------------------------|-----------------------------|--------------|
| `/mavros/state`                  | `mavros_msgs/State`         | reliable     |
| `/mavros/local_position/pose`    | `geometry_msgs/PoseStamped` | best-effort  |
| `/mavros/global_position/global` | `sensor_msgs/NavSatFix`     | best-effort  |
| `/mavros/battery`                | `sensor_msgs/BatteryState`  | best-effort  |

> **QoS note.** All MAVROS sensor/position topics are published **best-effort**. A
> subscription must use a compatible (sensor-data) QoS profile; the default reliable
> profile is incompatible and silently receives nothing. `/mavros/state` is the
> exception — it is reliable.

**Published / called (control):**

| Interface                        | Type                        | Use                    |
|----------------------------------|-----------------------------|------------------------|
| `/mavros/setpoint_position/local`| `geometry_msgs/PoseStamped` | Streamed target (≥2 Hz)|
| `/mavros/set_mode`               | `mavros_msgs/srv/SetMode`   | Switch to GUIDED       |
| `/mavros/cmd/arming`             | `mavros_msgs/srv/CommandBool`| Arm motors            |
| `/mavros/cmd/takeoff`            | `mavros_msgs/srv/CommandTOL`| Take off to altitude   |

## Autonomous flight sequence (`fly_to`)

The node is a state machine, one action per 1 Hz tick, gated on the *actual* state
reported by the autopilot:

1. Wait for `state.connected`.
2. Request **GUIDED**; retry until `state.mode == "GUIDED"`.
3. Request **arm**; retry every tick — this rides out the pre-arm period while the EKF
   and GPS converge (~30 s after connection).
4. Command **takeoff** to target altitude, exactly once (repeating it would reset the
   climb).
5. Wait until measured altitude exceeds a threshold, then mark *airborne*.
6. Only once airborne, stream the **position setpoint** at 10 Hz until the drone
   reaches and holds the target.

Streaming the setpoint *before* takeoff would override the climb, so the stream is
gated on the airborne flag. Coordinates are **ENU** metres from the home point
(x = East, y = North, z = Up); MAVROS converts to the autopilot's NED frame.
