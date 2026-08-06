# HSR/ROS2でのPick&Placeのサンプルソフトウェアの開発

---
## 1. 概要

本資料では、以下の手順を説明します。

* HSR/ROS2でのPick&Placeのサンプルソフトウェアのdocker環境での構築をします。
* 別途構築したyolox_rosとgraspnet_rosを統合したソフトウェアとの組み合わせで、以下のシミュレーション動作を行います。
  * yolox_rosを用いて画像シーケンス中から把持対象物を検出します。
    * この際、圧縮画像(topic)を入力として取得することでデータ伝送高速化を図りました。
    * yolox_rosの検出結果をgraspnet_rosに供給して、把持対象物の位置と姿勢を出力します。
  * 上記把持推定結果をHSR/ROS2ソフトウェアで受信することで、対象物のPick & Placeを実施します。

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
| OS                     | Ubuntu 24.04                                              |
| ROS                    | ROS2 Jazzy                                               |
| 構成環境               | Docker version 29.6.1, build 8900f1d                      |
| 動作部分               | hsrb_interfaceを利用                                                               |
| 物体認識用モジュール   | yolox ROS2 実装: https://github.com/Ar-Ray-code/YOLOX-ROS                          |
| 把持姿勢推論モジュール | graspnet ROS2 ノード(トヨタ提供)                                                  |
| シミュレータ           | Ignition Gazeboを利用                                                              |
<br>

<div style="page-break-before:always"></div>

### 2.2. 本Pick&Place ソフトウェアのパッケージ構成

```
pick_and_place_example/
:
├── hsrb_pnp_ws
│   ├── Doc
│   │   ├── Gazebo.png
│   │   ├── README-EN.md
│   │   ├── README.md
│   │   ├── RViz.png
│   │   ├── accessing_opening_gripper.png
│   │   ├── grip_object.png
│   │   ├── place_object.png
│   │   └── trigar_gaze.png
│   ├── docker
│   │   ├── Dockerfile
│   │   ├── cyclonedds_profile.xml
│   │   └── docker-compose.yaml
│   ├── launch_hsrb_pnp_ignition_gz.sh
│   ├── src
│   │   ├── hsr_repos_ignition_jazzy
│   │   │   ├── csm
│   │   │   ├── dynpick_driver
│   │   │   ├── exxx_control_table
│   │   │   ├── graspnet_ros
│   │   │   ├── hsr_common
│   │   │   ├── hsrb_common
│   │   │   ├── hsrb_control
│   │   │   ├── hsrb_controllers
│   │   │   ├── hsrb_drivers
│   │   │   ├── hsrb_interfaces
│   │   │   ├── hsrb_launch
│   │   │   ├── hsrb_manipulation
│   │   │   ├── hsrb_monitor
│   │   │   ├── hsrb_moveit
│   │   │   ├── hsrb_robot
│   │   │   ├── hsrb_rosnav
│   │   │   ├── hsrb_simulator
│   │   │   ├── hsrb_teleop
│   │   │   ├── ros2_laser_scan_matcher
│   │   │   ├── tmc_common
│   │   │   ├── tmc_common_msgs
│   │   │   ├── tmc_database
│   │   │   ├── tmc_drivers
│   │   │   ├── tmc_gazebo
│   │   │   ├── tmc_manipulation
│   │   │   ├── tmc_manipulation_base
│   │   │   ├── tmc_manipulation_planner
│   │   │   ├── tmc_navigation
│   │   │   ├── tmc_realtime_control
│   │   │   ├── tmc_teleop
│   │   │   └── tmc_voice
│   │   └── hsrb_pnp_pkgs
│   │       ├── hsrb_pick_and_place
│   │       └── hsrb_pnp_msgs
│   ├── start_hsrb_pick_and_place.sh
│   ├── trigger_gaze.sh
│   └── trigger_pnp.sh
:
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

端末2で、以下を実行してください。

``` bash
$ docker exec -it yolox_ros_onnx_graspnet bash
root@computer:~/ros2_ws# cd /workdir
root@computer:/workdir# ~/ros2_ws/start_yolox_graspnet_ros.sh
```


### 4.3. HSRB Pick and Place 制御システム起動

端末3で、以下を実行してください。
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

まずHSR体内PCで、 `/etc/opt/tmc/robot/cyclonedds_profile.xml` のPeer Addressに開発PCのIPアドレスを設定してください。

例: **\<Peer Address="192.168.123.456"\/\>**

次に開発PCで、ワークスペース内のCycloneDDS設定をします。
各設定ファイルを変更してください。

* yolox_ws/docker/cyclonedds_profile.xml
* hsrb_pnp_ws/docker/cyclonedds_profile.xml

  **\<Peer Address="XXX.XXX.XXX.XXX"\/\>** をHSR体内PCのIPアドレスに書き換えてください。

  * 例: **\<Peer Address="192.168.456.789"\/\>**

* yolox_ws/docker/docker-compose.yaml
* hsrb_pnp_ws/docker/docker-compose.yaml

  ROS_DOMAIN_IDをご自身の環境に合わせて設定してください。

実機用に、実行コマンドの変更を行ってください。

* hsrb_pnp_ws/start_hsrb_pick_and_place.sh

  ```bash
  #! /bin/bash

  # Run the pick and place system
  # cd /workdir; source ./install/setup.bash ; ros2 run hsrb_pick_and_place hsrb_pick_and_place --ros-args -p use_sim_time:=True
  cd /workdir; source ./install/setup.bash ; ros2 run hsrb_pick_and_place hsrb_pick_and_place --ros-args -p world_frame_id:=map -p use_sim_time:=False
  ```


ここまで設定が出来たら、コンテナを再起動してください。

```bash
$ cd /path/to/pick_and_place_example/hsrb_pnp_ws/docker
$ docker compose up -d

$ cd /path/to/pick_and_place_example/yolox_ws/docker
$ docker compose up -d
```

HSRを起動し、開発PCで以下を実行してください。

```bash
$ xhost +
$ docker exec -it yolox_ros_onnx_graspnet bash
$ cd /workdir
$ ~/ros2_ws/start_yolox_graspnet_ros.sh
```

開発PCの別の端末で以下を実行してください。

```bash
$ docker exec -it hsrb_pick_and_place bash
$ ./start_hsrb_pick_and_place.sh
```

開発PCの別の端末で以下を実行してください。

```bash
$ docker exec -it hsrb_pick_and_place bash
$ ./trigger_gaze.sh
```

hsrb_pnp_ws/trigger_gaze.sh の "{pos: [0.5, 0.12, 0.75]}" で与えるパラメータはHSRのbase_linkのworld座標系での3次元座標で、単位はmeterです。
必要に応じて変更して、対象物を視界に捉えるよう変更してください。

開発PCの別の端末で以下を実行してください。

```bash
$ docker exec -it hsrb_pick_and_place bash
$ ./trigger_pnp.sh
```

"{pos: [0.6, -0.28, 0.608]}" で与えるパラメータはPlace positionのworld座標系での3次元座標で、単位はmeterです。
必要に応じて変更し、対象物を置く場所を指定してください。

またPlace positionのorientationはデフォルトでPick positionのorientationと同一です。
しかし、そのパラメータに続けて3次元のパラメータをラジアン単位で指定することでPick positionのorientationをデフォルトから変位させることができます。

例: "{pos: [0.6, -0.28, 0.608, 0.175, 0.0, 0.0]}"

⚠️WARNING⚠️: ここでは、HSRが対象物をGraspnetで認識して把持できるように、HSRの視野に対象物が入っていることを想定しています。
対象物が複数視野に入っていたり、対象物が小さすぎると正常に動作しません。

動作しない場合は、以下のファイルからパラメータや対象物の位置を調整してください。

* /path/to/pick_and_place_example/hsrb_pnp_ws/src/hsr_repos_ignition_jazzy/graspnet_ros/graspnet_ros_node/graspnet_ros_node/parameters.yaml

  調整するパラメータ

  * robustness_th　：　- 把持候補の安全度（頑丈さ）スコアの閾値。高めにすると、安定した位置の候補だけが残る。
  * workspace_outlier　：　- 対象物の位置がワークスペース外かどうかの判定閾値。許容範囲を厳しくすれば、候補が少なくなる。


<div style="text-align: right;">
以上
</div>