# Agrican Drone — Simulation & Autonomous Control

A software-in-the-loop (SITL) platform for developing an **agricultural drone**: a
simulated multirotor that flies autonomously over a virtual field, controlled from
custom ROS 2 nodes. Built as a summer project (June–September 2026) to prototype the
autonomy stack for the *Agrican* use case — crop monitoring and field coverage —
without any physical hardware.

> Everything runs on a single Linux laptop. The same ArduPilot flight code that would
> run on a real drone runs here in simulation, so the control logic developed against
> the simulator transfers to real hardware.

---

## What it does

- Simulates a quadrotor with realistic flight physics in **Gazebo** (3D world, fake
  sensors, wind, GPS).
- Runs **ArduPilot SITL** as the flight controller — the real autopilot firmware,
  compiled for Linux.
- Bridges the autopilot to **ROS 2** via **MAVROS**, exposing telemetry and commands
  as ROS topics/services.
- Provides two custom ROS 2 nodes:
  - `drone_info` — subscribes to MAVROS and prints live drone state (link, arm status,
    flight mode, GPS, local position, battery).
  - `fly_to` — commands a full autonomous sortie: switch to GUIDED, arm, take off, and
    fly to a target waypoint, holding position on arrival.
  - `field_survey` — flies a full field-coverage mission: a boustrophedon ("lawnmower")
    pattern over the crop rows, advancing waypoint by waypoint, then returns home (RTL)
    and lands.

## Architecture

```
        ROS 2 graph
   ┌───────────────────┐
   │  fly_to (control) │        commands (services + setpoints)
   │  drone_info (HUD) │◄──────────────────┐
   └─────────┬─────────┘                   │
             │ ROS 2 topics/services       │ telemetry
             ▼                             │
        ┌─────────┐   MAVLink    ┌─────────────────┐
        │  MAVROS │◄────────────►│  ArduPilot SITL │
        └─────────┘   UDP        │  (flight code)  │
                                 └────────┬────────┘
                                          │ JSON FDM (UDP)
                                          ▼
                                   ┌──────────────┐
                                   │    Gazebo    │  physics + sensors + 3D world
                                   └──────────────┘
```

MAVROS translates between the ROS 2 world (topics/services) and the MAVLink protocol
the autopilot speaks. Gazebo and ArduPilot exchange servo commands and sensor data
over a lock-stepped UDP link (the ArduPilot "JSON" backend).

## Tech stack

| Layer            | Tool                              |
|------------------|-----------------------------------|
| OS               | Ubuntu 24.04 LTS (Noble)          |
| Middleware       | ROS 2 Jazzy                       |
| Simulator        | Gazebo Harmonic (`gz sim`)        |
| Flight control   | ArduPilot SITL (ArduCopter)       |
| ROS↔MAVLink      | MAVROS                            |
| Ground station   | MAVProxy                          |
| Language         | Python (ROS 2 nodes), SDF (worlds)|

## Repository layout

```
agrican-drone/
├── docs/
│   ├── requirements.md   # project specification (cahier des charges)
│   ├── architecture.md   # components, data flow, ports
│   ├── setup.md          # install + run guide
│   └── logbook.md        # development logbook (carnet de bord)
├── ros2/
│   └── drone_monitor/    # ROS 2 Python package (drone_info, fly_to)
├── sim/
│   ├── scripts/          # helper scripts (headless Gazebo, MAVROS launch)
│   └── worlds/           # Gazebo SDF worlds (field, props)
├── LICENSE
└── README.md
```

## Quickstart

Full instructions in [`docs/setup.md`](docs/setup.md). In short, four terminals:

```bash
# 1 — Gazebo (headless, physics running)
sim-quiet -v4 -r iris_runway.sdf

# 2 — ArduPilot SITL (JSON backend, feeds MAVROS on 14551)
sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --console --out=127.0.0.1:14551

# 3 — MAVROS bridge
bash sim/scripts/start_mavros.sh

# 4 — an autonomous flight from a ROS 2 node
ros2 run drone_monitor fly_to
```

## Roadmap

- [x] Working drone simulation (Gazebo + ArduPilot SITL)
- [x] Manual control via a ground station (MAVProxy)
- [x] ROS 2 telemetry node (`drone_info`)
- [x] Autonomous waypoint flight from a ROS 2 node (`fly_to`)
- [x] Farm world with crop rows and obstacles (`farm_field.sdf`)
- [x] Multi-waypoint field-coverage mission — boustrophedon / lawnmower pattern (`field_survey`)
- [ ] Downward camera payload → crop imaging over ROS 2
- [ ] Spray / payload actuation model

## Context

This project originates from an *Agrican* brief proposed through the DeVinci Hive
association at ESILV: build a drone for agricultural use. It is developed here
independently as a personal engineering project.

## License

MIT — see [`LICENSE`](LICENSE).
