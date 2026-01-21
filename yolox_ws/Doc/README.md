# 物体認識 + 把持姿勢推論シミュレーションサンプルの構成方法


## 1. 概要
本資料では、以下の手順を説明します。

* yolox_rosとgraspnet_rosをDocker環境内で統合するサンプルソフトウェアを構築します。
* 上記Docker環境内で以下のシミュレーション動作を行います。
  * yolox_rosを用いて画像シーケンス中から把持対象物を検出します。
    * この際、圧縮画像(topic)を入力として取得することでデータ伝送高速化を図りました。
  * yolox_rosの検出結果をgraspnet_rosに供給して、把持対象物の位置と姿勢とを出力します。

---

## 2. 本ワークスペースの構成概要
本資料の示す成果物は、以下となります。

### 2.1. ソフトウェア構成要件
構成に用いる基本ソフトウェアの構成は以下となります。

<div style="text-align: center;">
<h5>表-1 ソフトウェア構成要件</h5>
</div>

| 項目                   | 内容                                                      |
| ---------------------- | --------------------------------------------------------- |
| OS                     | Ubuntu 22.04                                              |
| ROS                    | ROS2 Humble                                               |
| 構成環境               | Docker version 28.3.2, build 578ccf6                      |
| 物体認識用モジュール   | yolox ROS2 実装: https://github.com/Ar-Ray-code/YOLOX-ROS |
| 把持姿勢推論モジュール | grasp net ROS2 ノード(トヨタ提供)                         |

<br><br>

### 2.2. ディレクトリ構成
本ソフトウェアは以下ディレクトリ構成からなり、Docker環境内での実行を想定しています。

```
/path/to/workspace
├── Additional_src
│   ├── Dependent_package_src.zip
│   └── Graspnet_ros_src.zip
└── yolox_ws
    ├── check_grasp_result.sh
    ├── play_movie.sh
    ├── test_yolox_graspnet_ros.sh
    ├── docker
    │   ├── docker-compose.yaml
    │   ├── Dockerfile
    │   └── ros_entrypoint.sh
    ├── doc
    │   ├── README.md
    │   └── result_yolox_graspnet.jpg
    ├── src
        ├── compressed_rgbd_msgs
        ├── coordinate_transform_util_ros
        ├── cv_bridge_util
        ├── graspnetAPI
        ├── graspnet-baseline
        ├── graspnet_ros
        ├── instance_segmentation_msgs
        ├── yolox_bridge
        ├── yolox_graspnet_meta
        └── YOLOX-ROS

```


## 3. ホスト側での環境構築手順
以下の手順でホスト側の環境となるdockerコンテナの構築を行ってください。

### 3.1. dockerコンテナ内からのGUIウィンドウ表示の許容設定

``` bash
$ xhost +
```

### 3.2. コンテナの起動

``` bash
$ cd /path/to/pick_and_place_example/yolox_ws/docker
$ docker compose up -d
```

<br><br>

---
<div style="page-break-before:always"></div>

## 4. graspnet_rosによる把持姿勢推論の実行

### 4.1. hsrb_pick_and_placeでシミュレータの起動
本節以下で行うros2コマンドのなかに、シミュレータを起動していないと正常に動作しないものがあるため、それぞれ別端末で、hsrb_pick_and_placeでシミュレータの起動を行います。

HSR/ROS2 pick & Place用コンテナの起動

``` bash
$ cd /path/to/pick_and_place_example/hsrb_pnp_ws/docker
$ docker compose up -d

#端末１
$ docker exec -it hsrb_pick_and_place bash
root@computer:~/ros2_ws# ./launch_hsrb_pnp_ignition_gz.sh

#端末２
$ docker exec -it hsrb_pick_and_place bash
hsrb@computer:~/ros2_ws# ./start_hsrb_pick_and_place.sh

#端末３
$ docker exec -it hsrb_pick_and_place bash
root@computer:~/ros2_ws# ./trigger_gaze.sh
```

### 4.3. yolox_ros、graspnet_rosの起動
以下を別端末から起動することで、yolox_rosによる画像中からの対象物検出プロセス、およびgraspnet_rosによる把持姿勢推定プロセスを起動することができます。停止コマンドを実行しなければ停止させることができません。

- 起動コマンド

``` bash
$ docker exec -it yolox_ros_onnx_graspnet bash
root@computer:~/ros2_ws# cd /workdir
root@computer:~/workdir# ~/ros2_ws/start_yolox_graspnet_ros.sh
```
上記を実行したタイミングで下図のどちらかが表示されていなければ、失敗しています。「3. ホスト側での環境構築手順」から実行し直してください。

- 停止コマンド

``` bash
$ docker exec -it yolox_ros_onnx_graspnet bash
root@computer:~/ros2_ws# cd /workdir
root@computer:~/ros2_ws# ~/ros2_ws/stop_yolox_graspnet_ros.sh
```
<div style="display: flex;">
  <img src="yolox_ros_before.png" width="100">
  <img src="yolox_ros_after.png" width="100">
</div>

## 5. 実機での動作について

hsrb_pnp_ws/Docs/README.mdを参照してください。

# 6. 補足
## rosbagによる映像入力
HSRのトピックが入ったrosbagをplayできます。
以下では、サンプルのrosbagデータ(rosbag2_one_phone_standing_up)が~/Images/以下に保存されていると仮定しています。ファイルがない状態で実行すると、エラーが出ます。

``` bash
$ docker exec -it yolox_ros_onnx_graspnet bash
root@computer:~/ros2_ws# ros2 bag play ./Images/rosbag2_one_phone_standing_up
```

<div style="text-align: right;">
以上
</div>
