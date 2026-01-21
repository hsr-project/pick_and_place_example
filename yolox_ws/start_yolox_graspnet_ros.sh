#! /bin/bash

source ./install/setup.bash
ros2 launch yolox_ros_launch yolox_onnxruntime_without_camera.launch.py src_image_topic_name:=/head_rgbd_sensor/rgb/image_rect_color &
ros2 launch yolox_bridge yolox_bridge.launch.py depth_topic:=/head_rgbd_sensor/image/compressedDepth &
# ros2 launch yolox_bridge yolox_bridge.launch.py depth_topic:=/head_rgbd_sensor/depth_registered/image_rect_raw/compressedDepth &
ros2 launch graspnet_ros_launch grasp_detector.launch.py input_topic:=/yolox_bridge/result &
