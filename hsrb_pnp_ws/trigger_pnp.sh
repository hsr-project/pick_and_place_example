#! /bin/bash

cd /workdir
source ./install/setup.bash

# Trigger the pick and place routine
ros2 service call /pnp_trigger hsrb_pnp_msgs/srv/PnpTrigger "{pos: [0.6, -0.28, 0.608]}"


