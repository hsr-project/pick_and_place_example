# HSRB pick and placeサンプルコード

- Author: 矢口裕明 (クシナダ機巧株式会社)

本リポジトリには2つのdcoker構成用ファイル群が含まれています。
それぞれの使用法は以下を参照してください。

- hsrb_pnp_ws/Docs/README.md

- yolox_ws/Docs/README.md

## submoduleについて

関連するリポジトリが多いためsubmoduleでの管理をしています。

## 構築手順

このリポジトリをクローンする際は git clone のオプション、"--recursive" をつけて任意の場所にて実行してください。
``` bash
$ git clone --recursive git@github.com:hsr-project/pick_and_place_example.git
```

以下の順番で構築を行ってください。

#### 1. hsrb_pnp_wsとyolox_wsのDockerコンテナ作成＆起動

端末から以下を実行してビルドしてください。
yolox_wsのビルドには１時間程度必要です。

``` bash
$ cd /path/to/pick_and_place_example/yolox_ws/docker
$ docker compose build
```

``` bash
$ cd /path/to/pick_and_place_example/hsrb_pnp_ws/docker
$ docker compose build
```

#### 2. yolox_ws/Docs/README.mdの構築、確認
yolox_ws/Docs/README.mdを参照してください。
#### 3. hsrb_pnp_ws/Docs/README.mdの構築、確認
hsrb_pnp_ws/Docs/README.mdを参照してください。
