#!/usr/bin/env python3
# Copyright (c) 2025 TOYOTA MOTOR CORPORATION
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted (subject to the limitations in the disclaimer
# below) provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of the copyright holder nor the names of its contributors may be used
#   to endorse or promote products derived from this software without specific
#   prior written permission.
# NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY THIS
# LICENSE. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
# GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState
from geometry_msgs.msg import TransformStamped
from std_srvs.srv import Trigger, SetBool
from tf2_ros import TransformBroadcaster

from graspnet_ros_msgs.msg import GraspDetection
from hsrb_pnp_msgs.srv import PnpTrigger

import numpy as np
import math
import time
import sys
from scipy.spatial.transform import Rotation as R

from hsrb_interface import geometry  # noqa : F401
from hsrb_interface import Robot

class HsrbPickAndPlace(Node):
    """
    ROS2 node for HSR robot pick and place operations.
    """

    def __init__(self) -> None:
        """
        Initialize the HsrbPickAndPlace node.
        """
        super().__init__('hsrb_pick_and_place')

        # Parameters
        self.declare_parameter('pick_approach_offset', 0.2)
        self.declare_parameter('pick_lift_offset', 0.05)
        self.declare_parameter('place_approach_offset', 0.1)
        self.declare_parameter('place_retract_offset', 0.1)
        self.declare_parameter('use_grasp_pose_adjust', True)
        self.declare_parameter('world_frame_id', "world")  # for real robot set this to 'map'

        # Set params
        self.pick_approach_offset = self.get_parameter('pick_approach_offset').get_parameter_value().double_value
        self.pick_lift_offset = self.get_parameter('pick_lift_offset').get_parameter_value().double_value
        self.place_approach_offset = self.get_parameter('place_approach_offset').get_parameter_value().double_value
        self.place_retract_offset = self.get_parameter('place_retract_offset').get_parameter_value().double_value
        self.use_grasp_pose_adjust = self.get_parameter('use_grasp_pose_adjust').get_parameter_value().bool_value
        self.world_frame_id = self.get_parameter('world_frame_id').get_parameter_value().string_value

        # Listen to graspnet results
        qos = rclpy.qos.QoSProfile(depth=10, reliability=rclpy.qos.ReliabilityPolicy.BEST_EFFORT)
        self.sub_graspnet_result = self.create_subscription(
            GraspDetection,
            '/grasp_detector_node/result',
            self.graspnet_result_callback,
            qos
        )

        # Transform broadcaster
        self.tf_broadcaster = TransformBroadcaster(self)

        # Service trigger
        self.srv_pnp_trigger = self.create_service(PnpTrigger, 'pnp_trigger', self.pnp_trigger_callback)

        # Gaze service trigger
        self.srv_gaze_trigger = self.create_service(PnpTrigger, 'gaze_trigger', self.gaze_trigger_callback)

        # Reset trigger
        self.srv_arm_reset_trigger = self.create_service(Trigger, 'arm_reset_trigger', self.arm_reset_trigger_callback)

        # Graspnet Pose result adjustment
        self.srv_graspnet_pose_adjust = self.create_service(SetBool, 'graspnet_pose_adjust', self.graspnet_pose_adjust_callback)

        # Grasp Pose
        self.grasp_detection = None

        # Initialize the robot
        self.robot = Robot()
        self.whole_body = self.robot.try_get('whole_body')  # noqa : F841
        self.get_logger().info('Hsrb whole body initialized')

        # Gripper
        self.gripper = self.robot.try_get('gripper')  # noqa : F841
        self.get_logger().info('Hsrb gripper initialized')

        self.get_logger().info('HSR Pick and Place node initialized')

    def graspnet_pose_adjust_callback(self, request: SetBool.Request, response:SetBool.Response) -> SetBool.Response:
        self.get_logger().info(f"Received Graspnet Pose Adjust request: {request.data}")
        self.use_grasp_pose_adjust = request.data
        response.success = True
        response.message = f"Graspnet Pose Adjust: {self.use_grasp_pose_adjust}"
        return response

    def arm_reset_trigger_callback(self, request: Trigger.Request, response: Trigger.Response) -> Trigger.Response:
        self.get_logger().info('Trigger arm reset')
        try:
            self.move_arm_to_go()
            response.message = 'Arm reset succeded.'
            response.success = True
        except Exception as e:
            self.get_logger().error(f'Arm reset failed: {e}')
            response.message = 'Arm reset failed.'
            response.success = False

        return response

    def pnp_trigger_callback(self, request: PnpTrigger.Request, response: PnpTrigger.Response) -> PnpTrigger.Response:
        """
        @brief Callback function for the trigger service.
        @param request The request.
        @param response The response.
        @return The response.
        """
        self.get_logger().info('Trigger pick and place')

        # Guard
        # Position must only contain 3 values, position and orientation must contain 6 values
        data_len = len(request.pos)
        if  data_len != 3 and data_len != 6:
            self.get_logger().error(f'Place request pos has a length not equal to 3 or 6. Cannot execute pick and place, len:{len(request.pos)}')
            self.get_logger().error(f'request.pos = {request.pos}')
            response.message = f'Place request pos has a length not equal to 3 or 6. Cannot execute pick and place, len:{len(request.pos)}'
            response.success = False
            return response

        self.get_logger().info('Get pick pose...')
        # Get pick and place pose
        pick_pose = self.get_pick_pose()

        self.get_logger().info('Get place pose...')
        # Get place pose.
        # Position = from PnpTrigger request,
        # Orientation = from pick_pose (default), or add rot_offset relative to pick pose orientation(rx,ry,rz)
        place_position = request.pos[:3]
        place_rot_offset = request.pos[3:] if data_len==6 else [0.0,0.0,0.0]
        place_pose = self.get_place_pose(place_position, place_rot_offset, pick_pose)

        self.get_logger().info('Check guard...')
        # Guard
        if pick_pose is None or place_pose is None:
            self.get_logger().error('Pick or place pose is None')
            response.message = 'Pick or place pose is None'
            response.success = False
            return response

        # Perform pick and place
        self.get_logger().info('Performing pick and place...')
        try:
            self.perform_pick_and_place(pick_pose, place_pose)
            response.message = 'Pick and place succeded.'
            response.success = True
        except Exception as e:
            self.get_logger().error(f'Pick and place failed: {e}')
            response.message = 'Pick and place failed.'
            response.success = False

        self.get_logger().info(f'Pick and place success: {response.success}')
        return response

    def gaze_trigger_callback(self, request: PnpTrigger.Request, response: PnpTrigger.Response) -> PnpTrigger.Response:
        """
        @brief Callback function for the gaze trigger service.
        @param request The request.
        @param response The response.
        @return The response.
        """
        self.get_logger().info('Trigger gaze')

        # Guard
        # Position must only contain 3 values
        if len(request.pos) != 3:
            self.get_logger().error(f'Gaze request pos has a length not equal to 3. Cannot execute gaze, len:{len(request.pos)}')
            self.get_logger().error(f'request.pos = {request.pos}')
            response.message = f'Gaze request pos has a length not equal to 3. Cannot execute gaze, len:{len(request.pos)}'
            response.success = False
            return response

        # Move to go arm config
        self.move_arm_to_go()

        # Search for the object, this could be a routine for the robot to look around
        # looking for the object
        # For now, we just look at a fixed point
        pos = request.pos
        self.whole_body.gaze_point(pos, 'base_link')

        response.message = 'Gaze triggered'
        response.success = True
        return response

    def graspnet_result_callback(self, msg: GraspDetection) -> None:
        """
        @brief Callback function for the GraspDetection message.
        @param msg The GraspDetection message.
        """
        # graspnet_ros_msgs/msg/GraspDetection
        # std_msgs/Header header
        # bool is_not_framed_out
        # geometry_msgs/Pose[] pose
        # float32[] width
        # float32[] height
        # float32[] depth
        # float32[] score
        # float32[] robustness

        # Set grasp detection
        self.grasp_detection = msg

        for i in range(len(msg.pose)):
            # Get the pose
            pose = msg.pose[i]

            # Create a TransformStamped message
            graspnet_pose = TransformStamped()

            # Set the header
            graspnet_pose.header.stamp = self.get_clock().now().to_msg()
            graspnet_pose.header.frame_id = msg.header.frame_id
            graspnet_pose.child_frame_id = f"graspnet_pose_{i}"

            # Pose: translation (x, y, z)
            graspnet_pose.transform.translation.x = pose.position.x
            graspnet_pose.transform.translation.y = pose.position.y
            graspnet_pose.transform.translation.z = pose.position.z

            # Pose: rotation as quaternion (x, y, z, w)
            graspnet_pose.transform.rotation.x = pose.orientation.x
            graspnet_pose.transform.rotation.y = pose.orientation.y
            graspnet_pose.transform.rotation.z = pose.orientation.z
            graspnet_pose.transform.rotation.w = pose.orientation.w

            # Send the transform
            self.tf_broadcaster.sendTransform(graspnet_pose)

    def perform_pick_and_place(self, pick_pose: PoseStamped, place_pose: PoseStamped) -> None:
        """
        @brief Perform the pick and place operation.
        @param pick_pose PoseStamped object representing the target pose
        @param place_pose PoseStamped object representing the target pose
        """
        # Move arm to neutral pose
        # self.get_logger().info('Moving to neutral pose...')
        # self.move_arm_to_neutral()

        # Close the gripper
        self.get_logger().info('Closing the gripper...')
        self.gripper_close()

        # Perform pick
        self.get_logger().info('Performing pick...')
        self.get_logger().info(f"Pick Header Frame ID: {pick_pose.header.frame_id}")
        self.get_logger().info(f"Pick Pose: {pick_pose.pose}")
        self.perform_pick(pick_pose)

        # Perform place
        self.get_logger().info('Performing place...')
        self.perform_place(place_pose)

    def perform_pick(self, pick_pose: PoseStamped) -> None:
        """
        @brief Perform the pick operation.
        @param pick_pose PoseStamped object representing the target pose
        """

        # Move arm to offset pick pose, approach pose
        self.get_logger().info('Moving to pick approach pose...')

        # Get base to pick pose transform matrix
        head_T_ee_pose = self.whole_body.get_end_effector_pose(pick_pose.header.frame_id)
        base_T_ee_pose = self.whole_body.get_end_effector_pose("base_link")
        head_T_ee_posestamped = self.hsr_pose_to_ros_pose(head_T_ee_pose)
        base_T_ee_posestamped = self.hsr_pose_to_ros_pose(base_T_ee_pose)

        # Compute base_frame to pick_pose transform
        head_T_ee = self.pose_to_transform_matrix(head_T_ee_posestamped)
        base_T_ee = self.pose_to_transform_matrix(base_T_ee_posestamped)
        head_T_pick = self.pose_to_transform_matrix(pick_pose)
        base_T_pick = base_T_ee @ np.linalg.inv(head_T_ee) @ head_T_pick
        base_T_pick_pose = self.transform_matrix_to_pose(base_T_pick)

        # Get approach pose, and move to it
        self.get_logger().info('Get approach pose, and move to it')
        approach_pose = self.get_linear_local_offset_pose(base_T_pick_pose, [0.0, 0.0, -self.pick_approach_offset])
        self.move_arm_to_pose(approach_pose)
        time.sleep(0.1)

        # Open the gripper
        self.get_logger().info('Opening the gripper...')
        self.gripper_open()
        time.sleep(0.1)

        # Move arm to pick pose
        self.get_logger().info('Moving to pick pose...')
        self.move_ee_by_line([0,0,1], self.pick_approach_offset)
        time.sleep(0.1)

        # Wait for a bit
        self.get_logger().info('Waiting for a bit...')
        time.sleep(0.1)

        # Log pick position
        ee_current_pose = self.whole_body.get_end_effector_pose("base_link")
        ee_current_posestamped = self.hsr_pose_to_ros_pose(ee_current_pose)
        self.get_logger().info(f'Pick position:{ee_current_posestamped.pose.position}')

        # Grab the object
        self.get_logger().info('Closing the gripper...')
        self.gripper_close()
        time.sleep(0.1)

        # Retract to pick approach pose
        self.get_logger().info('Retracting to pick approach pose...')
        base_R_ee = self.pose_to_rotation_matrix(base_T_pick_pose)
        base_Z_axis = [0,0,1]
        ee_T_eez = np.linalg.inv(base_R_ee) @ base_Z_axis
        self.move_ee_by_line(ee_T_eez.tolist(), self.pick_lift_offset)
        self.move_ee_by_line([0,0,1], -self.pick_approach_offset)
        time.sleep(0.1)

        # Move arm to neutral pose
        self.get_logger().info('Moving to neutral pose...')
        self.move_arm_to_neutral()

    def perform_place(self, place_pose: PoseStamped) -> None:
        """
        @brief Perform the pick operation.
        @param pick_pose PoseStamped object representing the target pose
        """

        # Get approach pose
        world_T_base = self.get_world_to_base_transform()
        world_T_placepose = self.pose_to_transform_matrix(place_pose)
        base_T_ee = np.linalg.inv(world_T_base) @ world_T_placepose

        # Move arm place pose, approach pose
        self.get_logger().info('Moving to place approach pose...')
        world_z_offset = self.build_transform_matrix(np.array([0.0, 0.0, self.place_approach_offset]), np.eye(3))
        base_T_ee_approach = world_z_offset @ base_T_ee
        approach_pose = self.transform_matrix_to_pose(base_T_ee_approach)
        self.move_arm_to_pose(approach_pose)

        # Move arm to place pose
        self.get_logger().info('Moving to place pose...')
        base_R_ee = self.pose_to_rotation_matrix(place_pose)
        base_Z_axis = [0,0,1]
        ee_T_eez = np.linalg.inv(base_R_ee) @ base_Z_axis
        self.move_ee_by_line(ee_T_eez.tolist(), -self.place_approach_offset)
        time.sleep(0.1)

        # Wait for a bit
        self.get_logger().info('Waiting for a bit...')
        time.sleep(0.1)

        # Release the object
        self.get_logger().info('Opening the gripper...')
        self.gripper_open()
        time.sleep(0.1)

        # Wait for a bit
        self.get_logger().info('Waiting for a bit...')
        time.sleep(0.1)

        # Move to approach pose
        # Always go up/down Z-axis with respect to base axis
        self.get_logger().info('Retracting to place approach pose...')
        self.move_ee_by_line(ee_T_eez.tolist(), self.place_retract_offset)
        time.sleep(0.1)

        # Retract
        self.move_ee_by_line([0,0,1], -self.place_retract_offset)

        # Close gripper
        self.get_logger().info('Closing the gripper...')
        self.gripper_close()

        # Move arm to go pose
        self.get_logger().info('Moving to go pose...')
        self.move_arm_to_go()

    def move_arm_to_pose(self, pose: PoseStamped) -> None:
        """
        @brief Move the arm to the target pose.
        @param pose PoseStamped object representing the target pose
        """
        pos = (pose.pose.position.x, pose.pose.position.y, pose.pose.position.z)
        quat = (pose.pose.orientation.x, pose.pose.orientation.y, pose.pose.orientation.z, pose.pose.orientation.w)
        self.whole_body.move_end_effector_pose((pos, quat), pose.header.frame_id)

    def move_ee_by_line(self, axis: list, distance: float, ref_frame: str = "hand_palm_link") -> None:
        """
        @brief Move the end effector by a line in the given axis.
        @param axis Axis to move the end effector in [x, y, z]
        @param distance Distance to move the end effector
        @param ref_frame Reference frame to move the end effector in
        """
        self.whole_body.move_end_effector_by_line(axis, distance, ref_frame)

    def move_arm_to_neutral(self) -> None:
        """
        @brief Move the arm to the neutral pose.
        """
        self.whole_body.move_to_neutral()

    def move_arm_to_go(self) -> None:
        """
        @brief Move the arm to the go pose.
        """
        self.whole_body.move_to_go()

    def adjust_pick_pose(self, pick_pose: PoseStamped) -> PoseStamped:
        """
        @brief Adjust the pick pose so that it always give the best pose for the HSR robot
        @param pick_pose The original pick_pose from graspnet
        @return PoseStamped object representing the target pose
        """
        # Adjusted pose
        adjusted_pose = pick_pose

        # Perform adjustment
        pp_mat = self.pose_to_transform_matrix(pick_pose) # 4x4
        pose_y_axis = pp_mat[:3, 1]
        pose_z_axis = pp_mat[:3, 2]
        up_axis = np.array([0.0, 0.0, 1.0])

        # Determine right
        right_axis = np.cross(pose_z_axis, up_axis)
        self.get_logger().info(f'right_axis:{right_axis}')

        # Project pose_y_axis to zero plane
        pose_y_axis_proj = pose_y_axis.copy()
        pose_y_axis_proj[2] = 0.0
        self.get_logger().info(f'pose_y_axis_proj:{pose_y_axis_proj}')

        # Get the Dot product
        dot_p = np.dot(pose_y_axis_proj, right_axis)
        self.get_logger().info(f'Dot:{dot_p}')

        if dot_p < 0:
            self.get_logger().info('Rotating target pose. . .')
            # y-axis is on the other side of HSRB
            # Rotate 180-degrees on the local z-axis of pose
            rot = R.from_euler('xyz', [0.0, 0.0, math.pi]).as_matrix()
            rot_mat = self.build_transform_matrix(np.array([0.0, 0.0, 0.0]), rot)
            adjusted_mat = pp_mat * rot_mat
            adjusted_pose =  self.transform_matrix_to_pose(adjusted_mat, pick_pose.header.frame_id)

        return adjusted_pose

    def get_pick_pose(self) -> PoseStamped:
        """
        @brief Get the target pose from the target name.
        @return PoseStamped object representing the target pose
        """
        if(self.grasp_detection == None):
            return None
        if(len(self.grasp_detection.pose) == 0):
            return None

        # Grasp Pose
        grasp_pose = self.grasp_detection.pose[0]
        pick_pose = PoseStamped()
        pick_pose.header.stamp = self.get_clock().now().to_msg()
        pick_pose.header.frame_id = self.grasp_detection.header.frame_id
        pick_pose.pose.position.x = grasp_pose.position.x
        pick_pose.pose.position.y = grasp_pose.position.y
        pick_pose.pose.position.z = grasp_pose.position.z
        pick_pose.pose.orientation.x = grasp_pose.orientation.x
        pick_pose.pose.orientation.y = grasp_pose.orientation.y
        pick_pose.pose.orientation.z = grasp_pose.orientation.z
        pick_pose.pose.orientation.w = grasp_pose.orientation.w

        if self.use_grasp_pose_adjust:
            adjusted_pick_pose = self.adjust_pick_pose(pick_pose)
            return adjusted_pick_pose

        return pick_pose

    def get_place_pose(self, pos:list[float], rot_offset:list[float], pick_pose: PoseStamped) -> PoseStamped:
        """
        @brief Get the place_pose
        @param pos Position x,y,z from a static world frame (meters)
        @param rot_offset Rotation offset from the pick pose orientation, used for adjustments (radians)
        @param pick_pose Extracts the orientation of the pick_pose and used as the orientation of the place_pose
        @return PoseStamped object representing the target pose
        """
        # Vars
        place_pose = PoseStamped()
        rot_matrix = R.from_euler('xyz', rot_offset).as_matrix()
        rot_T_offset = self.build_transform_matrix(np.array([0.0, 0.0, 0.0]), rot_matrix)

        # Position based on world
        place_pose.header.frame_id = self.world_frame_id
        place_pose.header.stamp = self.get_clock().now().to_msg()

        # Set position
        place_pose.pose.position.x = pos[0]
        place_pose.pose.position.y = pos[1]
        place_pose.pose.position.z = pos[2]

        # Rotation based on world
        world_T_base = self.get_world_to_base_transform()
        head_T_ee_pose = self.whole_body.get_end_effector_pose(pick_pose.header.frame_id)
        base_T_ee_pose = self.whole_body.get_end_effector_pose("base_link")
        head_T_ee_posestamped = self.hsr_pose_to_ros_pose(head_T_ee_pose)
        base_T_ee_posestamped = self.hsr_pose_to_ros_pose(base_T_ee_pose)
        head_T_ee = self.pose_to_transform_matrix(head_T_ee_posestamped)
        base_T_ee = self.pose_to_transform_matrix(base_T_ee_posestamped)
        head_T_pick = self.pose_to_transform_matrix(pick_pose)
        base_T_pick = base_T_ee @ np.linalg.inv(head_T_ee) @ head_T_pick
        world_T_pick = world_T_base @ base_T_pick

        # Apply offset
        world_T_place_offset = world_T_pick @ rot_T_offset
        world_T_place_pose = self.transform_matrix_to_pose(world_T_place_offset)

        # Set rotation
        quat = world_T_place_pose.pose.orientation
        place_pose.pose.orientation.x = quat.x
        place_pose.pose.orientation.y = quat.y
        place_pose.pose.orientation.z = quat.z
        place_pose.pose.orientation.w = quat.w

        return place_pose

    def gripper_open(self, command: float = 0.9) -> None:
        """
        @brief Open the gripper.
        """
        self.gripper.command(command)

    def gripper_close(self, force: float = 2.0) -> None:
        """
        @brief Close the gripper.
        """
        self.gripper.apply_force(force)

    def get_linear_local_offset_pose(self, pose: PoseStamped, offset: list) -> PoseStamped:
        """
        @brief Get the linear local offset pose.
        @param pose PoseStamped object representing the target pose
        @return PoseStamped object representing linear local offset pose
        """
        # Get the transformation matrix from the base to the end effector
        base_T_ee = self.pose_to_transform_matrix(pose)
        ee_T_app = self.build_transform_matrix(np.array(offset), np.eye(3))
        base_T_app = base_T_ee @ ee_T_app
        return self.transform_matrix_to_pose(base_T_app)

    def get_world_to_base_transform(self) -> np.ndarray:
        """
        @brief Get the transformation matrix from the world to the base.
        @return Transformation matrix
        """
        base_T_ee_hsrpose = self.whole_body.get_end_effector_pose("base_link")
        world_T_ee_hsrpose = self.whole_body.get_end_effector_pose(self.world_frame_id)
        base_T_ee_ros = self.hsr_pose_to_ros_pose(base_T_ee_hsrpose)
        world_T_ee_ros = self.hsr_pose_to_ros_pose(world_T_ee_hsrpose)
        base_T_ee = self.pose_to_transform_matrix(base_T_ee_ros)
        world_T_ee = self.pose_to_transform_matrix(world_T_ee_ros)
        world_T_base = world_T_ee @ np.linalg.inv(base_T_ee)
        return world_T_base

    def build_transform_matrix(self, pos: np.ndarray, rot: np.ndarray) -> np.ndarray:
        """
        @brief Build a transformation matrix from a position and rotation matrix.
        @param pos Position vector [3x1]
        @param rot Rotation matrix [3x3]
        @return Spatial transformation matrix
        """
        T = np.eye(4)
        T[:3, :3] = rot
        T[:3, 3] = pos
        return T

    def pose_to_rotation_matrix(self, pose: PoseStamped) -> np.ndarray:
        """
        @brief Convert a pose message to a rotation matrix.
        @param pose PoseStamped object representing the pose
        @return Rotation matrix
        """
        # Extract orientation
        ori = pose.pose.orientation
        quat = [ori.x, ori.y, ori.z, ori.w]
        rot = R.from_quat(quat)
        R_mat = rot.as_matrix()  # 3x3 rotation matrix
        return R_mat

    def pose_to_transform_matrix(self, pose: PoseStamped) -> np.ndarray:
        """
        @brief Convert a pose message to a transformation matrix.
        @param pose PoseStamped object representing the pose
        @return Spatial transformation matrix
        """
        # Extract position
        pos = pose.pose.position
        p = np.array([pos.x, pos.y, pos.z])

        # Extract orientation
        r = self.pose_to_rotation_matrix(pose)

        # Build 4x4 matrix
        T = np.eye(4)
        T[:3, :3] = r
        T[:3, 3] = p

        return T

    def hsr_pose_to_ros_pose(self, pose) -> PoseStamped:
        """
        @brief Convert a pose message from HSR's frame to ROS's frame.
        @param pose PoseStamped object representing the pose in HSR's frame
        @return PoseStamped object representing the pose in ROS's frame
        """
        ros_pose = PoseStamped()
        ros_pose.pose.position.x = pose.pos.x
        ros_pose.pose.position.y = pose.pos.y
        ros_pose.pose.position.z = pose.pos.z
        ros_pose.pose.orientation.x = pose.ori.x
        ros_pose.pose.orientation.y = pose.ori.y
        ros_pose.pose.orientation.z = pose.ori.z
        ros_pose.pose.orientation.w = pose.ori.w
        return ros_pose

    def transform_matrix_to_pose(self, T: np.ndarray, frame_id: str = "base_link") -> PoseStamped:
        """
        @brief Convert a transformation matrix to a pose message.
        @param T Transformation matrix
        @return PoseStamped object representing the pose
        """
        # Extract position
        p = T[:3, 3]

        # Extract orientation
        r = T[:3, :3]
        quat = R.from_matrix(r).as_quat()

        # Create pose message
        pose = PoseStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = frame_id
        pose.pose.position.x = p[0]
        pose.pose.position.y = p[1]
        pose.pose.position.z = p[2]
        pose.pose.orientation.x = quat[0]
        pose.pose.orientation.y = quat[1]
        pose.pose.orientation.z = quat[2]
        pose.pose.orientation.w = quat[3]

        return pose

def main(args=None):
    """
    Main function for HSR Pick and Place node.
    """
    rclpy.init(args=args)
    node = HsrbPickAndPlace()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
