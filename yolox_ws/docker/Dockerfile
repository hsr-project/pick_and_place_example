ARG BASE_TAG=11.7.1-cudnn8-devel-ubuntu22.04
FROM nvcr.io/nvidia/cuda:${BASE_TAG} AS base
ENV	 DEBIAN_FRONTEND=noninteractive

ENV PATH /usr/local/nvidia/bin:/usr/local/cuda/bin:${PATH}
RUN apt update && \
    apt install -y python3-dev python3-pip ca-certificates g++ gcc make git aria2 && \
    apt -y clean && \
    rm -rf /var/lib/apt/lists/* && \
    aria2c -q -d /tmp -o cmake-3.21.0-linux-x86_64.tar.gz https://github.com/Kitware/CMake/releases/download/v3.21.0/cmake-3.21.0-linux-x86_64.tar.gz && \
    tar -zxf /tmp/cmake-3.21.0-linux-x86_64.tar.gz --strip=1 -C /usr
RUN python3 -m pip install -U pip && \
    python3 -m pip install -U numpy setuptools wheel && \
    python3 -m pip cache purge

WORKDIR /workdir
RUN git clone --depth 1 --recursive https://github.com/microsoft/onnxruntime -b v1.12.1 && \
    cd onnxruntime && \
    ./build.sh --cudnn_home /usr/lib/x86_64-linux-gnu/ \
    --cuda_home /usr/local/cuda \
    --use_cuda \
    --config RelWithDebInfo \
    --build_shared_lib \
    --skip_tests && \
    cd build/Linux/RelWithDebInfo && \
    make install && \
    rm -r /workdir/onnxruntime

# Install ROS2
RUN apt update && apt install locales && \
    locale-gen en_US en_US.UTF-8 && \
    update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 && \
    apt -y clean && \
    rm -rf /var/lib/apt/lists/*
ENV LANG=en_US.UTF-8

RUN apt update && \
    apt install -y git wget curl gnupg2 lsb-release && \
    curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null && \
    sed -i -e 's/ubuntu .* main/ubuntu jammy main/g' /etc/apt/sources.list.d/ros2.list && \
    apt update && \
    apt install -y ros-dev-tools \
    ros-humble-cv-bridge \
    ros-humble-generate-parameter-library \
    ros-humble-parameter-traits \
    ros-humble-ros-base \
    ros-humble-rqt-image-view \
    #                   ros-humble-v4l2-camera \
    ros-humble-rmw-cyclonedds-cpp && \
    apt -y clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install -U pip && \
    pip install catkin_pkg && \
    pip install empy && \
    pip install lark && \
    python3 -m pip cache purge


#===== Build yolox_ros ==== 
FROM base AS app
WORKDIR /workdir
COPY ../src/ src/
COPY ./docker/ros_entrypoint.sh /ros_entrypoint.sh
RUN echo "source /ros_entrypoint.sh" >> /root/.bashrc

# install torch
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 

# download weight
RUN echo $PWD
RUN bash src/YOLOX-ROS/weights/onnx/download.bash all 

# build 
RUN pip install setuptools==65.5.1
SHELL ["/bin/bash", "-c"]
RUN . "/opt/ros/humble/setup.bash" && \
    colcon build --packages-select yolox_param && \
    colcon build --packages-select bboxes_ex_msgs && \
    colcon build --cmake-args -DYOLOX_USE_ONNXRUNTIME=ON --packages-select yolox_cpp && \
    colcon build --packages-select yolox_ros_cpp && \
    colcon build --packages-select yolox_ros_launch

#==== Build yolox_bridge ====
RUN . "/opt/ros/humble/setup.bash" && \
    colcon build --packages-select instance_segmentation_msgs && \
    colcon build --packages-select yolox_bridge


#==== Build graspnet_ros

# Install additional python modules
RUN apt-get update && \
    apt-get remove -y python3-blinker
ENV TORCH_CUDA_ARCH_LIST="7.5;8.0;8.6;8.9;9.0"
RUN cd /workdir/src/graspnet-baseline && \
    pip3 install -r requirements.txt 

# Install pointnet2 operators
RUN . "/root/.bashrc" && cd /workdir/src/graspnet-baseline/pointnet2 && \
    python3 setup.py install

# Install knn operator
RUN . "/root/.bashrc" && cd /workdir/src/graspnet-baseline/knn && \
    python3 setup.py install


#==== Install graspnetAPI
# Down grade numpy under ver.2
RUN pip install --upgrade "numpy<2"

# Obtain graspnetAPI
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True
RUN . "/root/.bashrc" && cd src/graspnetAPI && \
    pip install .

# Build
RUN  . "/opt/ros/humble/setup.bash" && \
    colcon build --packages-select coordinate_transform_util_ros && \
    colcon build --packages-select cv_bridge_util && \
    colcon build --packages-select graspnet_ros_msgs && \
    colcon build --packages-select libgraspnet && \
    colcon build --packages-select graspnet_ros_node && \
    colcon build --packages-select graspnet_ros_launch


# Setup colcon install folder's pass
RUN echo "source /opt/ros/humble/setup.bash" > /etc/profile.d/ros_base_setup.sh && \
    echo "source /workspace/install/setup.bash" >> /etc/profile.d/ros_ws_setup.sh && \
    chmod +x /etc/profile.d/ros_base_setup.sh /etc/profile.d/ros_ws_setup.sh

#COPY ./ros_entrypoint.sh /ros_entrypoint.sh
COPY ./docker/ros_entrypoint.sh /ros_entrypoint.sh
RUN echo "source /ros_entrypoint.sh" >> /root/.bashrc
# ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
