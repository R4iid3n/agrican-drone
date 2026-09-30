# Development Logbook

*Carnet de bord — a running record of the work, decisions, and problems solved.*

Newest entries at the bottom. Dates reflect when each milestone was reached.

---

### 2026-06-14 — Project framing

Started from the Agrican brief: build a drone for agriculture. Decided to work in
simulation first — a physical drone is slow and risky to iterate on, and SITL is the
standard way to develop autonomy. Wrote the specification (`requirements.md`): the goal
for this phase is a working, controllable drone simulation that can fly an autonomous
sortie commanded from custom software.

Chose the stack: ArduPilot as the flight controller (real firmware, transfers to
hardware), Gazebo as the simulator, ROS 2 for the autonomy layer, MAVProxy as the
ground station.

### 2026-06-22 — Simulation stack up

Settled the version pairing: Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic. Earlier
Gazebo/ROS combinations don't work together on 24.04, which cost some time to pin down.

Built the `ardupilot_gazebo` plugin against Harmonic (`libArduPilotPlugin.so`) and
wired up the environment (`GZ_SIM_SYSTEM_PLUGIN_PATH`, `GZ_SIM_RESOURCE_PATH`). Added a
`sim-quiet` helper to run Gazebo headless — the 3D view costs a few CPU threads, and on
a laptop that margin matters for keeping the simulation real-time.

### 2026-07-05 — ArduPilot ↔ Gazebo talking

Getting SITL and Gazebo to exchange data was the first real obstacle. Gazebo kept
printing `Incorrect protocol magic 0 should be 18458` and the drone wouldn't respond.

Root cause: the frame `-f gazebo-iris` selects ArduPilot's *legacy* Gazebo backend,
which sends a bare servo packet with no protocol header. The installed plugin, however,
speaks the newer *JSON* FDM protocol (magic `18458`). The fix is `--model JSON`, which
switches SITL to the matching protocol. Also learned the hard way that Gazebo must be
launched with `-r` (running); if it starts paused, SITL stalls waiting for sensor data
and never emits a heartbeat.

Once both were aligned, the SITL console started scrolling `JSON received:` — sensor
data flowing from Gazebo into the flight controller.

### 2026-07-14 — Manual control via GCS

Connected MAVProxy to SITL. Can now put the drone in GUIDED, arm, take off, and send
"fly to here" from the map — the drone responds correctly in the 3D world. That closes
the first half of the objective: a working, manually controllable simulated drone.

Documented the port map (TCP 5760 master, UDP 14550/14551 outputs) since routing
between SITL, MAVProxy, and later MAVROS would clearly need to be exact.

### 2026-07-28 — ROS 2 telemetry node

Created the `drone_monitor` ROS 2 package and the first node, `drone_info`. It
subscribes to `/mavros/state` and prints the drone's link status, arm state, and flight
mode. This is the node-to-node pattern that matters: MAVROS publishes, my node
subscribes — they never call each other directly, they meet on a topic.

### 2026-08-12 — MAVROS bridge nailed down

Bringing MAVROS up reliably took several iterations. Symptoms were always
`connected: false` despite the stack looking correct. Causes found and documented:

- The `fcu_url` string is unforgiving — `udp://:14551@127.0.0.1:14550` exactly. A
  missing colon makes MAVROS read the port as a hostname; a typo makes it fall back to
  a serial device that doesn't exist. Moved the launch into `start_mavros.sh` so it's
  never hand-typed.
- MAVProxy has to actually forward to 14551 (`--out=127.0.0.1:14551`).
- Stale processes from earlier attempts stack up and confuse routing — kill hard and
  confirm before relaunching.

With those fixed: `CON: Got HEARTBEAT, connected. FCU: ArduPilot`.

### 2026-08-30 — Autonomous waypoint flight

Wrote `fly_to`: a ROS 2 node that flies the drone autonomously to a target. This was
the hardest node to get right. Two bugs stood out:

1. **QoS mismatch.** `/mavros/local_position/pose` is published *best-effort*. My
   subscription used the default *reliable* QoS, which is incompatible — so it silently
   received zero messages and my altitude reading stayed at 0. That made the node
   re-command takeoff every tick, which reset the climb, and the drone looped
   arm→disarm on the ground. Fix: subscribe with `qos_profile_sensor_data`.
2. **Setpoint timing.** Streaming the position setpoint during takeoff overrides the
   climb. Fix: gate the stream on an "airborne" flag set only after the measured
   altitude clears a threshold.

Final logic is a state machine, one action per tick, gated on the autopilot's actual
reported state, with the arm step retried to ride out the pre-arm EKF/GPS convergence.
Result: the drone reliably switches to GUIDED, arms, takes off, and flies to
`(10, 5, 10)`, holding position on arrival. The objective for this phase is met.

### 2026-09-15 — World props

Started authoring the simulated environment. Added a field world with static props
(crop rows, obstacles) as a base for mission scenarios — this is where the
agriculture-specific work begins: something for the drone to fly *over* and, later,
sense.

### 2026-09-30 — Documentation & cleanup

Consolidated the project into a presentable repository: specification, architecture,
setup guide, and this logbook. Cleaned up the ROS 2 package and helper scripts.

### 2026-09-30 — Field-coverage mission

Turned the single waypoint into a full coverage mission (`field_survey`). The node
generates a boustrophedon ("lawnmower") waypoint list programmatically — one pass per
crop row, alternating X direction so the drone snakes across the field — then flies it,
advancing to the next waypoint when within a reach radius, and finally switches to RTL
to return home and land.

Bringing it up on the new `farm_field` world surfaced a chain of bugs, each of which
blocked everything downstream until fixed:

- **World missing sensor system plugins.** My hand-written `farm_field.sdf` omitted the
  `Imu` and `NavSat` system plugins (and `spherical_coordinates`) that the stock world
  has. Without them the iris IMU/GPS produced nothing, SITL stalled waiting for a valid
  FDM, and no heartbeat ever came. Fix: mirror the proven world header.
- **MAVROS launch script self-terminating.** `start_mavros.sh` began with
  `pkill -f mavros` — which matched the script's *own* command line (`start_mavros.sh`
  contains "mavros") and killed itself before launching. This had been silently
  sabotaging the bridge step for a while. Fix: match `mavros_node` specifically.
- **Empty launch argument.** A `gcs_url:=""` expanded to an empty value that
  `ros2 launch` rejects. Fix: drop the optional argument.
- **Pre-arm failures under a slow sim.** With the 3D GUI rendering in software (no GPU
  driver), the simulation ran at ~2 Hz; the two simulated IMUs then diverged and the
  autopilot refused to arm ("Accels inconsistent"), and GPS needed time to lock.
  Running the Gazebo *server* headless (viewing through a separate client) keeps the
  simulation fast enough to arm cleanly.

With all four resolved, the drone arms, climbs to 12 m, flies the 16-waypoint survey
covering all eight crop rows, and returns home to land. First genuinely agricultural
capability: autonomous field coverage.

Next phase: add a downward camera payload and stream its imagery over ROS 2, turning
the coverage pattern into an actual crop scan.
