# HSR/ROS2でのPick&Placeのサンプルソフトウェアの開発

---
## 1. 概要

本資料では、以下の手順を説明します。

* HSR/ROS2でのPick&Placeのサンプルソフトウェアのdocker環境での構築をします。
* 別途構築したyolox_rosとgraspnet_rosを統合したソフトウェアとの組み合わせで、以下のシミュレーション動作を行います。
  * yolox_rosを用いて画像シーケンス中から把持対象物を検出すします。
    * この際、圧縮画像(topic)を入力として取得することでデータ伝送高速化を図りました。
    * yolox_rosの検出結果をgraspnet_rosに供給して、把持対象物の位置と姿勢とを出力します。
  * 上記把持推定結果をHSR/ROS2ソフトウェアで受信することで、対象物のPick&Placeを実施します。

---

<div style="page-break-before:always"></div>


## 2. 本ワークスペースの構成概要
本資料の示す成果物は、以下となります。

### 2.1. ソフトウェア構成要件
構成に用いる基本ソフトウェアの構成は以下となります。

<div style="text-align: center;">
<h5>表-1 ソフトウェア構成要件</h5>
</div>

| 項目                   | 内容                                                                               |
| ---------------------- | ---------------------------------------------------------------------------------- |
| OS                     | ![Ubuntu](https://img.shields.io/badge/Ubuntu-22.04-orange.svg)Ubuntu 22.04        |
| ROS                    | ![ROS Version](https://img.shields.io/badge/ROS-Humble-brightgreen.svg)ROS2 Humble |
| 構成環境               | Docker version 28.3.2, build 578ccf6                                               |
| 動作部分               | hsrb_interfaceを利用                                                               |
| 物体認識用モジュール   | yolox ROS2 実装: https://github.com/Ar-Ray-code/YOLOX-ROS                          |
| 把持姿勢推論モジュール | grasp net ROS2 ノード(トヨタ提供)                                                  |
| シミュレータ           | Ignition Gazeboを利用                                                              |
<br>

<div style="page-break-before:always"></div>

### 2.2. 本Pick&Place ソフトウェアのパッケージ構成


```
~/pick_and_place_example
|
hsrb_pnp_ws/
|   ├── docker
|   |   ├── docker-compose.yaml
|   |   └──  Dockerfile
|   ├── src/
|       ├── hsr_repos_ignition_humble/      # Main HSR-B packages
|       │   ├── csm/                        # Scan matching library
|       │   ├── dynpick_driver/             # Force sensor driver
|       │   ├── exxx_control_table/         # Control table
|       │   ├── gazebo_ros2_control/        # Gazebo ROS 2 control
|       │   ├── graspnet_ros/               # Graspnet
|       │   ├── gz_ros2_control/            # Gazebo ignition ros2 control
|       │   ├── hsrb_common/                # Common HSR-B packages
|       │   ├── hsrb_control/               # Control packages
|       │   ├── hsrb_controllers/           # Robot controllers
|       │   ├── hsrb_drivers/               # Hardware drivers
|       │   ├── hsrb_interfaces/            # Interface definitions
|       │   ├── hsrb_launch/                # Launch files
|       │   ├── hsrb_manipulation/          # Manipulation packages
|       │   ├── hsrb_monitor/               # System monitoring
|       │   ├── hsrb_moveit/                # MoveIt integration
|       │   ├── hsrb_robot/                 # Robot description
|       │   ├── hsrb_rosnav/                # Navigation integration
|       │   ├── hsrb_simulator/             # Simulation environment
|       │   ├── hsrb_teleop/                # Teleoperation packages
|       │   ├── hsr_common/                 # Common HSR packages
|       │   ├── ros2_laser_scan_matcher/    # Laser scan matching
|       │   ├── tmc_common/                 # Common TMC packages
|       │   ├── tmc_common_msgs/            # Common message definitions
|       │   ├── tmc_database/               # Database integration
|       │   ├── tmc_dev_tools/              # Development tools
|       │   ├── tmc_drivers/                # Hardware drivers
|       │   ├── tmc_gazebo/                 # Gazebo integration
|       │   ├── tmc_manipulation/           # Manipulation libraries
|       │   ├── tmc_manipulation_base/      # Base manipulation
|       │   ├── tmc_manipulation_planner/   # Motion planning
|       │   ├── tmc_navigation/             # Navigation stack
|       │   ├── tmc_realtime_control/       # Real-time control
|       │   ├── tmc_teleop/                 # Teleoperation libraries
|       │   └── tmc_voice/                  # Voice recognition/synthesis
|       └── hsrb_pnp_okgs
|            ├── hsrb_pick_and_place/        # Pick and place functionality
|            └── hsrb_pnp_msgs/              # Pick and place msgs
```

<div style="page-break-before:always"></div>
<br>

```
~/pick_and_place_example
|
|  -------- 以下は別資料(yolox_ws/doc/README.md)参照 -------------------------------------------------
└── yolox_ws
|   ├── check_grasp_result.sh           # Check script for graspnet's results
|   ├── play_movie.sh                   # Sample image scequence playing script for test
|   ├── start_yolox_graspnet_ros.sh     # Start script for yolox and graspnet
|   ├── docker
|   │   ├── docker-compose.yaml
|   │   ├── Dockerfile
|   │   └── ros_entrypoint.sh
|   ├── Images
|   │   └── rosbag2_one_phone_standing_up.zip
|   ├── Doc
|   │   ├── README.md
|   │   └── result_yolox_graspnet.jpg
|   ├── src
|       ├── compressed_rgbd_msgs
|       ├── coordinate_transform_util_ros
|       ├── cv_bridge_util
|       ├── graspnetAPI
|       ├── graspnet-baseline
|       ├── graspnet_ros
|       ├── instance_segmentation_msgs
|       ├── yolox_bridge
|       ├── yolox_graspnet_meta
|       └── YOLOX-ROS
```


<br><br>

## 3. 環境構築手順

以下を実行し、dockerコンテナを起動させてください。

* HSR/ROS2 pick & Place用コンテナの起動

``` bash
$ cd /path/to/pick_and_place_example/hsrb_pnp_ws/docker
$ docker compose up -d
```

* yolox+ graspnet用コンテナの起動

``` bash
$ cd /path/to/pick_and_place_example/yolox_ws/docker
$ docker compose up -d
```

## 4. シミュレーションでの検出物体のpick&place動作手順

### 4.1. Base HSRB system とシミュレーション用worldの生成

端末1で、以下を実施してください。

```bash
$ xhost +
$ docker exec -it hsrb_pick_and_place bash
hsrb@computer:~/ros2_ws$ ./launch_hsrb_pnp_ignition_gz.sh
```


この結果以下のignition gazobo, rvizが起動します。

<div style="display: flex;">
  <img src="Gazebo.png" width="100">
  <img src="RViz.png" width="100">
</div>
<br> 

### 4.2. 物体検出+把持姿勢推定(yolox+graspnet)用コンテナ起動

端末2で、以下を実施してください。

``` bash
$ docker exec -it yolox_ros_onnx_graspnet bash
root@computer:~/ros2_ws# cd /workdir
root@computer:/workdir# source ./install/setup.bash
root@computer:/workdir# ~/ros2_ws/start_yolox_graspnet_ros.sh
```


### 4.3. HSRB Pick and Place 制御システム起動

端末3で、以下を実施してください。
```bash
$ docker exec -it hsrb_pick_and_place bash
hsrb@computer:~/ros2_ws# ./start_hsrb_pick_and_place.sh
```


### 4.4. 対象物にRobotのカメラを向けるコマンドの起動

端末4で、以下を実施してください。
ここで"{pos: [0.5, 0.12, 0.75]}"で与えるパラメータはロボットのbase_linkのworld座標系での3次元座標で、単位はmeterです。

```bash
$ docker exec -it hsrb_pick_and_place bash
hsrb@computer:~/ros2_ws$ ./trigger_gaze.sh
```

この結果、HSRは以下のように対象物を視野に捉えます。

![trigger_gaze](trigar_gaze.png)



### 4.5. RobotにPick and Place を実行させるコマンドの起動

端末4で、以下を実施してください。
ここで"{pos: [0.6, -0.28, 0.608]}"で与えるパラメータはPlace positionのworld座標系での3次元座標で、単位はmeterです。
またPlace positionのorientationはdefaultではPick positionのorientationと同一ですが、前述のpositionパラメータに続けて3次元のparameterをradian単位で指定することでPick positionのorientationをdefaultから変位させることができます。
例 "{pos: [0.6, -0.28, 0.608, 0.175, 0.0, 0.0]}"

⚠️WARNING⚠️: ここでは、対象物がgraspnetで認識して把持ができるように、Robotの視野に入っていることを想定しています。


```bash
$ docker exec -it hsrb_pick_and_place bash
hsrb@computer:~/ros2_ws$ ./trigger_pnp.sh
```

上記の結果に従って、HSRは以下の動作を行います。

* 対象物に接近し、グリップを開き、グリップを閉じて対象物を掴みにいきます。
![accessing_opening_gripper](./accessing_opening_gripper.png)
<br><br>


* 右に移動して、対象物を置き、
![place_object](./place_object.png)

<br><br>

* グリップを開いてハンドをあげます。
![grip_object](./grip_object.png)


## 5. 補助コマンドの起動
### 5.1. Robotのアームをホームポジションに戻すコマンドの起動

``` bash
$ docker exec -it hsrb_pick_and_place bash
hsrb@computer:~/ros2_ws$ cd /workdir
# In a new Terminal 5
hsrb@computer:~/workdir$ source install/setup.bash
# Arm Reset trigger
hsrb@computer:~/workdir$ ros2 service call /arm_reset_trigger std_srvs/srv/Trigger "{}"
```

### 5.2. アームを対象物に近い面から掴ませる自動設定のON/OFF
graspnetの出力が、robotの現在位置に対して必ずしも正対に近い姿勢を提案しない場合もあります。
その場合にrobotから近い、提案とは対称な姿勢で把持を行うように設定する機能を本アプリで実装していますが、以下ではその機能のon/offを切り替えます。

* 機能のON (default)

``` bash
# In a new Terminal 6
$ docker exec -it hsrb_pick_and_place bash
hsrb@computer:~/ros2_ws$ cd /workdir
hsrb@computer:~/workdir$ source install/setup.bash
hsrb@computer:~/workdir$ ros2 service call /graspnet_pose_adjust std_srvs/srv/SetBool "{data: true}"
```

* 機能のOFF

``` bash
# In a new Terminal 6
$ docker exec -it hsrb_pick_and_place bash
hsrb@computer:~/ros2_ws$ cd /workdir
hsrb@computer:~/workdir$ source install/setup.bash
hsrb@computer:~/workdir$ ros2 service call /graspnet_pose_adjust std_srvs/srv/SetBool "{data: false}"
```

## 6. 実機での動作方法

ロボットと通信を行うために、cycloneddsの設定を行います。

HSR体内PCで、`/etc/opt/tmc/robot/cyclonedds_profile.xml`の設定を行います。

ファイルの雛形は以下のとおりです。

* 4行目のNetworkInterfaceAddressは，HSR-Cでは削除してください
* Peer Addressには、ロボットと通信を行うPC（以降、リモートPC）のIPアドレスを設定してください

```bash
<CycloneDDS>
  <Domain>
    <General>
      <NetworkInterfaceAddress>wlp3s0</NetworkInterfaceAddress>
      <AllowMulticast>false</AllowMulticast>
      <EnableMulticastLoopback>false</EnableMulticastLoopback>
      <MaxMessageSize>65500B</MaxMessageSize>
    </General>
    <Discovery>
      <ParticipantIndex>auto</ParticipantIndex>
      <MaxAutoParticipantIndex>100</MaxAutoParticipantIndex>
      <Peers>
        <Peer Address="xxx.xxx.xxx.xxx"/>
        <Peer Address="localhost"/>
      </Peers>
    </Discovery>
  </Domain>
</CycloneDDS>
```

続いて、リモートPCのcycloneddsの設定を行います。

まずは、以下2ファイルの設定を行います。

* yolox_ws/docker/cyclonedds_profile.xml
* hsrb_pnp_ws/docker/cyclonedds_profile.xml

ファイルの雛形は以下のとおりです。

* Peer Addressには、通信を行うHSRのIPアドレスを設定してください

```bash
<CycloneDDS>
  <Domain>
    <General>
      <AllowMulticast>false</AllowMulticast>
      <EnableMulticastLoopback>false</EnableMulticastLoopback>
      <MaxMessageSize>65500B</MaxMessageSize>
    </General>
    <Discovery>
      <ParticipantIndex>auto</ParticipantIndex>
      <MaxAutoParticipantIndex>100</MaxAutoParticipantIndex>
      <Peers>
        <Peer Address="xxx.xxx.xxx.xxx"/>
        <Peer Address="localhost"/>
      </Peers>
    </Discovery>
  </Domain>
</CycloneDDS>
```

続けて、以下ファイルの設定を行います。

* yolox_ws/docker/docker-compose.yaml

以下のように変更してください。ROS_DOMAIN_IDはご自身の環境に合わせて設定してください。

```bash
#version: '3.4'
services:
    yolox_ros_onnx_graspnet:
        container_name: yolox_ros_onnx_graspnet
        privileged: true
        build:
            # context: .
            context: ..
            dockerfile: docker/Dockerfile
            args:
                - BASE_TAG=11.8.0-cudnn8-devel-ubuntu22.04
        image: yolox_ros_onnx_graspnet:latest
        network_mode: host
        runtime: nvidia
        environment:
            - DISPLAY=$DISPLAY
            - RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
            - CYCLONEDDS_URI=file:///root/ros2_ws/docker/cyclonedds_profile.xml
            - ROS_DOMAIN_ID=XXX
            - TZ=Asia/Tokyo
        volumes:
            - ../:/root/ros2_ws
            - /tmp/.X11-unix:/tmp/.X11-unix
        devices:
            - "/dev/video0:/dev/video0"
        working_dir: /root/ros2_ws
        tty: true
        command: bash
```

* hsrb_pnp_ws/docker/docker-compose.yaml

こちらも同様に、ROS_DOMAIN_IDはご自身の環境に合わせて設定してください。

```bash
services:
    hsrb_pick_and_place:
        container_name: hsrb_pick_and_place
        privileged: true
        build:
            context: ..
            dockerfile: docker/Dockerfile   # added
        image: hsrb_pick_and_place:latest
        network_mode: host
        runtime: nvidia
        environment:
            - DISPLAY=$DISPLAY
            - RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
            - CYCLONEDDS_URI=file:///home/hsrb/ros2_ws/docker/cyclonedds_profile.xml
            - ROS_DOMAIN_ID=XXX
            - IGN_GAZEBO_RESOURCE_PATH=/workdir/src/hsrb_pnp_pkgs/hsrb_pick_and_place/models/
        volumes:
            - ../:/home/hsrb/ros2_ws
            - /tmp/.X11-unix:/tmp/.X11-unix
        devices:
            - "/dev/video0:/dev/video0"
        working_dir: /home/hsrb/ros2_ws
        tty: true
        command: bash
```

実機用に、パラメータ、トピック名の変更を行います。

* yolox_ws/start_yolox_graspnet_ros.sh

```bash
#! /bin/bash

source ./install/setup.bash
ros2 launch yolox_ros_launch yolox_onnxruntime_without_camera.launch.py src_image_topic_name:=/head_rgbd_sensor/rgb/image_rect_color &
# ros2 launch yolox_bridge yolox_bridge.launch.py depth_topic:=/head_rgbd_sensor/image/compressedDepth  &
ros2 launch yolox_bridge yolox_bridge.launch.py depth_topic:=/head_rgbd_sensor/depth_registered/image_rect_raw/compressedDepth &
ros2 launch graspnet_ros_launch grasp_detector.launch.py input_topic:=/yolox_bridge/result &
```

* hsrb_pnp_ws/start_hsrb_pick_and_place.sh

```bash
#! /bin/bash

# Run the pick and place system
# cd /workdir; source ./install/setup.bash ; ros2 run hsrb_pick_and_place hsrb_pick_and_place --ros-args -p use_sim_time:=True
cd /workdir; source ./install/setup.bash ; ros2 run hsrb_pick_and_place hsrb_pick_and_place --ros-args -p world_frame_id:=map -p use_sim_time:=False
```

ここまで設定が出来たら、コンテナを再度作成します。

以下を実行してビルドしてください。

```bash
$ cd /path/to/pick_and_place_example/yolox_ws/docker
$ docker compose build

$ cd /path/to/pick_and_place_example/hsrb_pnp_ws/docker
$ docker compose build
```

ビルドが完了したら、コンテナを起動します。

```bash
$ cd /path/to/pick_and_place_example/hsrb_pnp_ws/docker
$ docker compose up -d

$ cd /path/to/pick_and_place_example/yolox_ws/docker
$ docker compose up -d
```


非常停止を解除してHSRが起動したことを確認したら、端末1で以下を実行してください（リモートPC）

```bash
$ xhost +
$ docker exec -it yolox_ros_onnx_graspnet bash
$ cd /workdir
$ source ./install/setup.bash
$ ~/ros2_ws/start_yolox_graspnet_ros.sh
```

端末2で以下を実行してください（リモートPC）

```bash
$ docker exec -it hsrb_pick_and_place bash
$ ./start_hsrb_pick_and_place.sh
```

端末3で以下を実行してください（リモートPC）

```bash
$ docker exec -it hsrb_pick_and_place bash
$ ./trigger_gaze.sh
```

`hsrb_pnp_ws/trigger_gaze.sh`の`pos`は必要に応じて変更して、対象物を視界に捉えるよう変更してください

`"{pos: [0.5, 0.12, 0.75]}"`で与えるパラメータはロボットのbase_linkのworld座標系での3次元座標で、単位はmeterです。


端末4で、以下を実施してください。（リモートPC）

```bash
$ docker exec -it hsrb_pick_and_place bash
$ ./trigger_pnp.sh
```

`hsrb_pnp_ws/trigger_pnp.sh`の`pos`は必要に応じてを変更して、対象物を把持後、対象物を置く場所を指定してください。

`"{pos: [0.6, -0.28, 0.608]}"`で与えるパラメータはPlace positionのworld座標系での3次元座標で、単位はmeterです。

またPlace positionのorientationはdefaultではPick positionのorientationと同一ですが、前述のpositionパラメータに続けて3次元のparameterをradian単位で指定することでPick positionのorientationをdefaultから変位させることができます。

例 `"{pos: [0.6, -0.28, 0.608, 0.175, 0.0, 0.0]}"`

⚠️WARNING⚠️: ここでは、対象物がgraspnetで認識して把持ができるように、Robotの視野に入っていることを想定しています。対象物が複数視野に入っていたり、対象物が小さすぎると正常に動作しません。



動作しない場合は、以下のファイルからのパラメータの調整や、対象物の位置の調整などを行ってください。

* /path/to/pick_and_place_example/hsrb_pnp_ws/src/hsr_repos_ignition_humble/graspnet_ros/graspnet_ros_node/graspnet_ros_node/parameters.yaml

調整するパラメータ

* robustness_th　：　- 把持候補の安全度（頑丈さ）スコアの閾値。高めにすると、安定した位置の候補だけが残る
* workspace_outlier　：　- 対象物の位置がワークスペース外かどうかの判定閾値。許容範囲を厳しくすれば、候補が少なくなる


<div style="text-align: right;">
以上
</div>