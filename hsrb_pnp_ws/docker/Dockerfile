FROM osrf/ros:humble-desktop-full

# Add ubuntu user with same UID and GID as your host system, if it doesn't already exist
# Since Ubuntu 24.04, a non-root user is created by default with the name vscode and UID=1000
#ARG USERNAME=ubuntu
ARG USERNAME=hsrb
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN if ! id -u $USER_UID >/dev/null 2>&1; then \
        groupadd --gid $USER_GID $USERNAME && \
        useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME; \
    fi
# Add sudo support for the non-root user
RUN apt-get update && \
    apt-get install -y sudo && \
    echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME

# Switch from root to user
USER $USERNAME

# Add user to video group to allow access to webcam
RUN sudo usermod --append --groups video $USERNAME

# Update all packages
RUN sudo apt-get update && sudo apt upgrade -y

# Install Git
RUN sudo apt-get install -y git

# Rosdep update
RUN rosdep update

# Source the ROS setup file
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc

################################
## Building ros2 commands
################################
WORKDIR /workdir
COPY ../src/ src/

USER root
RUN chmod a+w src/hsr_repos_ignition_humble/tmc_gazebo/tmc_gazebo_worlds/worlds/
USER $USERNAME

# Build Dependencies
RUN sudo apt-get update &&\
    sudo apt-get install -y ros-humble-ros-gz && \
    sudo apt-get install -y ros-humble-gz-ros2-control && \
    sudo apt-get install -y ros-humble-twist-mux && \
    sudo apt-get install -y ros-humble-twist-stamper && \
    sudo apt-get install -y ros-humble-ros2-control && \
    sudo apt-get install -y ros-humble-ros2-controllers && \
    sudo apt-get install -y ros-humble-ign-ros2-control && \
    sudo apt-get install -y ros-humble-filters && \
    sudo apt-get install -y ros-humble-rmw-cyclonedds-cpp


#====  Install runtime Dependencies ====
RUN sudo apt-get update && sudo apt-get install -y python3-pip
RUN sudo pip install numpy-stl
RUN sudo apt-get update && \
    sudo apt-get install -y ros-humble-joint-state-publisher && \
    sudo apt-get install -y ros-humble-depth-image-proc && \
    sudo apt-get install -y ros-humble-pointcloud-to-laserscan && \
    sudo apt-get install -y ros-humble-tf-transformations && \
    sudo apt-get install -y ros-humble-topic-tools && \
    sudo apt-get install -y ros-humble-nav2-common && \
    sudo apt-get install -y ros-humble-octomap-ros && \
    sudo apt-get install -y ros-humble-nav2-bringup && \
    sudo apt-get install -y ros-humble-omni-base-controller-configuration && \
    sudo apt-get install -y ros-humble-joy && \
    sudo apt-get install -y ros-humble-joy-linux && \
    sudo apt-get install -y ros-humble-joint-state-broadcaster

RUN sudo apt-get update && \
    # Moveit2
    sudo apt-get install -y ros-humble-moveit && \
    # Pinochio
    sudo apt-get install -y ros-humble-pinocchio && \
    # Lib
    sudo apt install -y libsdl1.2-dev libsdl-image1.2-dev


#====  Build the necessary packages ====
SHELL ["/bin/bash", "-c"]
RUN . "/opt/ros/humble/setup.bash" && \
    # Build Base controllers
    colcon build --packages-up-to hsrb_base_controllers --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    # Hsrb moveit
    colcon build --packages-up-to hsrb_moveit_config --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    # Hsrb common launch
    colcon build --packages-up-to hsrb_common_launch --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    # Downloaded with 'git clone https://github.com/ros-controls/gz_ros2_control.git'
    # Branch, 0.7.12
    # IGN, located locally in hsrb_pnp_ws/others/gz_ros2_control
    colcon build --packages-select ign_ros2_control --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    # Build Gazebo Bringup
    colcon build --packages-up-to hsrb_gazebo_bringup --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    # Build Gazebo Launch
    colcon build --packages-up-to hsrb_gazebo_launch --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    # Build Hsrb Interface
    colcon build --packages-up-to hsrb_interface_py --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    # Graspnet messages
    colcon build --packages-select graspnet_ros_msgs --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    # Build pick and place package for hsrb
    colcon build --packages-select hsrb_pick_and_place --cmake-args -DCMAKE_BUILD_TYPE=Release --symlink-install && \
    # Build pick and place messages for hsrb, especially for specify place pose
    colcon build --packages-select hsrb_pnp_msgs --cmake-args -DCMAKE_BUILD_TYPE=Release


# Setup colcon install folder's pass
RUN echo "source /opt/ros/humble/setup.bash" | sudo tee /etc/profile.d/ros_base_setup.sh && \
    echo "source /workspace/install/setup.bash" | sudo tee /etc/profile.d/ros_ws_setup.sh && \
    sudo chmod +x /etc/profile.d/ros_base_setup.sh /etc/profile.d/ros_ws_setup.sh

RUN echo "source /opt/ros/humble/setup.bash" >> /home/hsrb/.bashrc
RUN echo "source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash" >> /home/hsrb/.bashrc

CMD ["bash"]
