#!/usr/bin/env bash
# Foolproof MAVROS launch for ArduPilot SITL. Run: bash ~/start_mavros.sh
set -e
pkill -f mavros 2>/dev/null || true
sleep 1
source /opt/ros/jazzy/setup.bash
exec ros2 launch mavros apm.launch \
  fcu_url:="udp://:14551@127.0.0.1:14550" \
  gcs_url:="" \
  tgt_system:=1 tgt_component:=1
