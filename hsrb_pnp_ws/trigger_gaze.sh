#! /bin/bash

cd /workdir
source ./install/setup.bash

# Trigger the gaze at the object
ros2 service call /gaze_trigger hsrb_pnp_msgs/srv/PnpTrigger "{pos: [0.5, 0.12, 0.75]}"

