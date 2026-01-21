# HSRB Pick and Place Sample Code

- Author: Hiroaki Yaguchi (クシナダ機巧株式会社)

This repository contains two sets of files for Docker configuration.
Please refer to the following for the usage of each.

- hsrb_pnp_ws/Docs/README-EN.md

- yolox_ws/Docs/README-EN.md

## About the submodule

Since there are many related repositories, they are managed as submodules.

## Build Procedure

When cloning this repository, execute git clone with the --recursive option in any desired location.
``` bash
$ git clone --recursive git@github.com:hsr-project/pick_and_place_example.git
```

Please build in the following order.

#### 1. Create and start the Docker containers for hsrb_pnp_ws and yolox_ws.

From the terminal, execute the following to build.
Building yolox_ws takes approximately one hour.

``` bash
$ cd /path/to/pick_and_place_example/yolox_ws/docker
$ docker compose build
```

``` bash
$ cd /path/to/pick_and_place_example/hsrb_pnp_ws/docker
$ docker compose build
```

#### 2. Build and verify according to yolox_ws/Docs/README-EN.md.
Please refer to yolox_ws/Docs/README-EN.md.
#### 3. Build and verify according to hsrb_pnp_ws/Docs/README-EN.md.
Please refer to hsrb_pnp_ws/Docs/README-EN.md.
