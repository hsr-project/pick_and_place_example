#! /bin/bash

# Launch pick and place system
cd /workdir ; source ./install/setup.bash; ros2 launch hsrb_pick_and_place hsrb_pnp_ignition_gz.launch.py use_sim_time:=true


