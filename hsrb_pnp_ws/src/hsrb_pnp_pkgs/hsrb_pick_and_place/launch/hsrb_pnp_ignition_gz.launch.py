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

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Get the launch directory
    pkg_dir_share = get_package_share_directory('hsrb_pick_and_place')
    pp_demo_path = os.path.join(pkg_dir_share, 'worlds', 'pp_demo_one_phone_standing.sdf')

    # Declare the launch arguments
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Ignition Gazebo) clock if true'
    )
        
    declare_world = DeclareLaunchArgument(
        'world',
        default_value=pp_demo_path,
        description='SDF world file'
    )
    
    # Launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Launch hsrb_gazebo_bringup
    hsrb_gazebo_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('hsrb_gazebo_bringup'), 'launch', 'hsrb_gazebo_bringup.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'world_file_name': LaunchConfiguration('world')
        }.items()
    )

    # Launch hsrb moveit 
    hsrb_moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('hsrb_moveit_config'), 'launch', 'hsrb_demo.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items()
    )

    # Moveit wait
    moveit_wait = TimerAction(
        period=5.0,
        actions=[
            hsrb_moveit
        ]
    )

    # Launch hsrb common
    hsrb_common = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('hsrb_common_launch'), 'launch', 'hsrb_common.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items()
    )

    # hsrb_common wait
    hsrb_common_wait = TimerAction(
        period=10.0,
        actions=[
            hsrb_common
        ]
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_world,
        hsrb_gazebo_bringup,
        moveit_wait,
        hsrb_common_wait
    ])
