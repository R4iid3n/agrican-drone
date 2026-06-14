# Project Specification — Agrican Drone

*Cahier des charges — v1, June 2026*

## 1. Context and motivation

Precision agriculture increasingly relies on unmanned aerial vehicles (UAVs) to
monitor crops, map fields, and apply inputs selectively. The *Agrican* brief asks for
a drone tailored to agricultural operation.

Developing and testing autonomy directly on a physical drone is slow, expensive, and
risky. The industry-standard alternative is **software-in-the-loop (SITL)
simulation**: the real flight-control firmware runs on a computer, coupled to a
physics simulator that supplies fake but realistic sensor data. Control software
developed against the simulator transfers to real hardware with minimal change.

This project builds that simulation platform and the first layer of autonomous control
on top of it.

## 2. Objectives

**Primary objective:** have a working, controllable drone simulation that can execute
an autonomous flight commanded from custom software.

Broken down:

1. Simulate a multirotor with realistic flight dynamics in a 3D world.
2. Run the actual flight-control firmware (not a toy controller) against that
   simulation.
3. Control the drone from a ground station, as an operator would.
4. Control the drone programmatically from custom ROS 2 nodes, as an autonomy stack
   would.

## 3. Functional requirements

| ID   | Requirement                                                                 | Status |
|------|-----------------------------------------------------------------------------|--------|
| FR-1 | The simulator shall render a 3D world and simulate multirotor flight physics. | Done   |
| FR-2 | The flight controller shall be ArduPilot (the same firmware used on real drones), running in SITL. | Done |
| FR-3 | The simulator and flight controller shall exchange sensor and actuator data in real time. | Done |
| FR-4 | A ground control station (GCS) shall connect to the drone and allow manual commands (mode, arm, takeoff, go-to). | Done |
| FR-5 | The system shall expose drone telemetry and commands to ROS 2. | Done |
| FR-6 | A ROS 2 node shall read and display live drone state (link, arm, mode, position, GPS, battery). | Done |
| FR-7 | A ROS 2 node shall autonomously arm the drone, take off, and fly to a specified waypoint. | Done |
| FR-8 | The world shall support adding static props (obstacles, field features) for mission scenarios. | In progress |

## 4. Non-functional requirements

- **NFR-1 — Reproducibility.** The full stack runs on a single Linux laptop from
  documented steps; no proprietary or cloud dependency.
- **NFR-2 — Hardware transfer.** Control logic targets standard ArduPilot interfaces
  (MAVLink / MAVROS) so it can drive a real drone unchanged.
- **NFR-3 — Real-time behaviour.** The simulation runs at (or near) wall-clock speed
  so control timing reflects reality.
- **NFR-4 — Modularity.** Simulation, flight control, and autonomy are separate
  processes communicating over standard protocols, each replaceable independently.

## 5. Scope

**In scope (this phase)**
- Multirotor SITL simulation and its bring-up.
- Manual control through a GCS.
- ROS 2 telemetry and single-waypoint autonomous flight.
- Basic world authoring (props).

**Out of scope (later phases)**
- Field-coverage mission planning.
- Camera / multispectral payload simulation and image processing.
- Spray / actuation payload modelling.
- Real-hardware deployment.

## 6. Constraints

- **Platform:** Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic (the versions that
  pair correctly; earlier Gazebo/ROS combinations are incompatible with this stack).
- **Flight controller:** ArduPilot ArduCopter, SITL build.
- **Autopilot ↔ simulator link:** ArduPilot "JSON" FDM backend (the protocol the
  installed Gazebo plugin speaks).
- **Single-operator, single-drone** for this phase.

## 7. Deliverables

1. A reproducible SITL simulation stack (documented in `docs/setup.md`).
2. A ROS 2 package (`drone_monitor`) with the telemetry and control nodes.
3. Documentation: this specification, an architecture description, a setup guide, and
   a development logbook.

## 8. Success criteria

The phase is complete when, from a clean machine following `docs/setup.md`, an operator
can:

1. Launch the simulation and see the drone in a 3D world.
2. Run `ros2 run drone_monitor drone_info` and observe live telemetry with
   `connected: true`.
3. Run `ros2 run drone_monitor fly_to` and watch the drone arm, take off, and fly to
   the target coordinate, holding position on arrival.

All three are demonstrated as of September 2026.
