FROM nvidia/cuda:13.0.0-cudnn-devel-ubuntu24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive

ENV PATH=/usr/local/nvidia/bin:/usr/local/cuda/bin:${PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}

ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      wget curl ca-certificates gnupg2 lsb-release \
      python3 python3-dev python3-pip \
      python3-setuptools \
      g++ gcc make git aria2 \
      locales \
      cmake \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US en_US.UTF-8 && \
    update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
ENV LANG=en_US.UTF-8

RUN python3 -m pip install "numpy==1.26.4" && \
    python3 -m pip cache purge

WORKDIR /workdir

ARG ONNXRUNTIME_VERSION=1.27.1

RUN aria2c -q -d /tmp -o onnxruntime-linux-x64-gpu_cuda13-${ONNXRUNTIME_VERSION}.tgz \
      https://github.com/microsoft/onnxruntime/releases/download/v${ONNXRUNTIME_VERSION}/onnxruntime-linux-x64-gpu_cuda13-${ONNXRUNTIME_VERSION}.tgz && \
    mkdir -p /tmp/onnxruntime && \
    tar -zxf /tmp/onnxruntime-linux-x64-gpu_cuda13-${ONNXRUNTIME_VERSION}.tgz \
      -C /tmp/onnxruntime --strip-components=1 && \
    cp -r /tmp/onnxruntime/include/* /usr/local/include/ && \
    cp -r /tmp/onnxruntime/lib/*     /usr/local/lib/ && \
    mkdir -p /usr/local/include/onnxruntime && \
    hdr_path=$(find /usr/local/include -name onnxruntime_cxx_api.h | head -n 1) && \
    cp "${hdr_path}" /usr/local/include/onnxruntime/onnxruntime_cxx_api.h && \
    rm -rf /tmp/onnxruntime /tmp/onnxruntime-linux-x64-gpu_cuda13-${ONNXRUNTIME_VERSION}.tgz && \
    ldconfig

ENV CPATH=/usr/local/include:${CPATH}
ENV LIBRARY_PATH=/usr/local/lib:${LIBRARY_PATH}
ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/local/cuda/lib64:${LD_LIBRARY_PATH}

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      git wget curl gnupg2 lsb-release && \
    curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
      -o /usr/share/keyrings/ros-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
          http://packages.ros.org/ros2/ubuntu noble main" \
      | tee /etc/apt/sources.list.d/ros2.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      ros-dev-tools \
      ros-jazzy-cv-bridge \
      ros-jazzy-generate-parameter-library \
      ros-jazzy-parameter-traits \
      ros-jazzy-ros-base \
      ros-jazzy-rqt-image-view \
      ros-jazzy-rmw-cyclonedds-cpp \
      ros-jazzy-vision-msgs \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install catkin_pkg empy lark && \
    python3 -m pip cache purge

#===== Build yolox_ros ====
FROM base AS app
WORKDIR /workdir

COPY ../src/ src/
COPY ./docker/ros_entrypoint.sh /ros_entrypoint.sh
RUN echo "source /ros_entrypoint.sh" >> /root/.bashrc

RUN python3 -m pip install torch torchvision torchaudio \
      --index-url https://download.pytorch.org/whl/cu130

RUN bash src/YOLOX-ROS/weights/onnx/download.bash all

SHELL ["/bin/bash", "-c"]

RUN source "/opt/ros/jazzy/setup.bash" && \
    colcon build --packages-select yolox_param && \
    colcon build --packages-select bboxes_ex_msgs && \
    colcon build --cmake-args -DYOLOX_USE_ONNXRUNTIME=ON --packages-select yolox_cpp && \
    colcon build --packages-select yolox_ros_cpp && \
    colcon build --packages-select yolox_ros_launch

#==== Build yolox_bridge ====
RUN source "/opt/ros/jazzy/setup.bash" && \
    colcon build --packages-select instance_segmentation_msgs && \
    colcon build --packages-select yolox_bridge

#==== Build graspnet_ros ====
RUN apt-get update && \
    apt-get remove -y python3-blinker || true && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN apt-get update && \
    apt-get remove -y python3-numpy python3-scipy python3-sklearn || true && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV TORCH_CUDA_ARCH_LIST="7.5;8.0;8.6;8.9;9.0"

RUN cd /workdir/src/graspnet-baseline && \
    python3 -m pip install --ignore-installed -r requirements.txt

RUN source "/root/.bashrc" && \
    cd /workdir/src/graspnet-baseline/pointnet2 && \
    python3 setup.py install

RUN source "/root/.bashrc" && \
    cd /workdir/src/graspnet-baseline/knn && \
    python3 setup.py install

#==== Install graspnetAPI ====
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True
RUN source "/root/.bashrc" && \
    cd src/graspnetAPI && \
    python3 -m pip install .

RUN python3 -m pip install --force-reinstall \
      "numpy==1.26.4" \
      "scipy==1.11.4" \
      "scikit-learn==1.4.2"

RUN source "/opt/ros/jazzy/setup.bash" && \
    colcon build --packages-select coordinate_transform_util_ros && \
    colcon build --packages-select cv_bridge_util && \
    colcon build --packages-select graspnet_ros_msgs && \
    colcon build --packages-select libgraspnet && \
    colcon build --packages-select graspnet_ros_node && \
    colcon build --packages-select graspnet_ros_launch

RUN echo "source /opt/ros/jazzy/setup.bash" > /etc/profile.d/ros_base_setup.sh && \
    echo "source /workspace/install/setup.bash" >> /etc/profile.d/ros_ws_setup.sh && \
    chmod +x /etc/profile.d/ros_base_setup.sh /etc/profile.d/ros_ws_setup.sh

COPY ./docker/ros_entrypoint.sh /ros_entrypoint.sh
RUN echo "source /ros_entrypoint.sh" >> /root/.bashrc

CMD ["bash"]
