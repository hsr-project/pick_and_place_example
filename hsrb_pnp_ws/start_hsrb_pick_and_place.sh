#! /bin/bash

# Run the pick and place system
cd /workdir; source ./install/setup.bash ; ros2 run hsrb_pick_and_place hsrb_pick_and_place --ros-args -p use_sim_time:=True
# cd /workdir; source ./install/setup.bash ; ros2 run hsrb_pick_and_place hsrb_pick_and_place --ros-args -p world_frame_id:=map -p use_sim_time:=False


