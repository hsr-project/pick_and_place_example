#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
# colcon build --symlink-install
# source install/setup.bash
exec "$@"
