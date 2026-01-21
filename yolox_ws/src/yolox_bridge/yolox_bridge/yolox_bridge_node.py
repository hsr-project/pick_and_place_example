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
from yolox_bridge.coco_mapper import COCOClassMapper
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CameraInfo, CompressedImage
from bboxes_ex_msgs.msg import BoundingBoxes, BoundingBox as BoundingBoxEx
from instance_segmentation_msgs.msg import InstanceSegmentation, BBox
from cv_bridge import CvBridge
import numpy as np
import cv2
import json
from pathlib import Path
from typing import List


def img_and_bbox_to_segment(img: Image, bbox: list[BBox]) -> Image:
    bridge = CvBridge()

    # 1) First, use CvBridge to convert imgmsg to a NumPy array
    # By specifying img.encoding in desired_encoding,
    # you can maintain the original encoding and obtain a NumPy image
    cv_img = bridge.imgmsg_to_cv2(img, desired_encoding=img.encoding)

    # 2) Use np.full_like to create an array with the exact same shape and dtype as cv_img, and fill all elements with "filler"
    # For example, shape=(H,W) for grayscale, and shape=(H,W,3) or (H,W,4) for color
    shape = cv_img.shape[:2]
    segment_array = np.full(shape, 0, dtype=np.uint8)

    # 3) Convert the filled NumPy array back to an Image message
    # Keep the encoding the same as the original

    for i, box in enumerate(bbox):
        x, y, w, h = box.x, box.y, box.w, box.h
        segment_array[y:y+h, x:x+w] = i+1

    print(f'ENC:{img.encoding}')
    segment_msg = bridge.cv2_to_imgmsg(segment_array, encoding='8UC1')
    print("FILL!")

    # 4) Align the header (timestamp and frame_id) with the original image
    segment_msg.header = img.header

    return segment_msg


class YoloxBridgeNode(Node):
    def __init__(self):
        super().__init__('yolox_bridge_node')
        # The output topic name can be specified with a parameter
        self.declare_parameter('output_topic', '/yolox_bridge/result')
        output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        self.declare_parameter('blacklist_path', '')
        blacklist_path = self.get_parameter('blacklist_path').get_parameter_value().string_value
        # The topic name for depth differs between ignition and the actual machine.
        # ignition: /head_rgbd_sensor/image/compressedDepth
        # Actual machine: /head_rgbd_sensor/depth_registered/image_rect_raw/compressedDepth
        self.declare_parameter('depth_topic', '/head_rgbd_sensor/image/compressedDepth')
        depth_topic = self.get_parameter('depth_topic').get_parameter_value().string_value

        self.blacklist = []
        if blacklist_path:
            try:
                with open(blacklist_path, 'r') as f:
                    self.blacklist = json.load(f)
                self.get_logger().info(f"Blacklist loaded from {blacklist_path}")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.get_logger().error(f"Failed to load blacklist file: {e}")

        self.coco_class_mapper = COCOClassMapper()

        # Variable to hold the latest message
        self.camera_info = None
        self.rgb_image = None
        self.depth_image = None

        self.bridge = CvBridge()

        # Subscriber definition
        self.create_subscription(
            CameraInfo,
            '/head_rgbd_sensor/rgb/camera_info',
            self.camera_info_callback,
            10
        )
        self.create_subscription(
            Image,
            '/head_rgbd_sensor/rgb/image_rect_color',
            self.rgb_callback,
            10
        )
        self.create_subscription(
            CompressedImage,
            depth_topic,
            self.depth_callback,
            10
        )
        self.create_subscription(
            BoundingBoxes,
            '/yolox/bounding_boxes',
            self.bbox_callback,
            10
        )

        # Publisher definition
        self.pub = self.create_publisher(
            InstanceSegmentation,
            output_topic,
            qos_profile_sensor_data
        )
        self.tmp_pub_result_rgb = self.create_publisher(
            CompressedImage,
            '~/result_rgb',
            10
        )
        self.tmp_pub_result_depth = self.create_publisher(
            CompressedImage,
            '~/result_depth',
            10
        )
        self.tmp_pub_result_segment = self.create_publisher(
            Image,
            '~/result_segment',
            10
        )

    def filter_bboxes(self, bounding_boxes: List[BoundingBoxEx]) -> List[BoundingBoxEx]:
        if not self.blacklist:
            return bounding_boxes
        filtered_bounding_boxes = [box for box in bounding_boxes if box.class_id not in self.blacklist]
        filtered = len(bounding_boxes) - len(filtered_bounding_boxes)
        if filtered > 0:
            self.get_logger().info(f'{filtered} boxes are filtered.')
        return filtered_bounding_boxes

    def camera_info_callback(self, msg: CameraInfo):
        self.camera_info = msg

    def rgb_callback(self, msg: Image):
        self.rgb_image = msg

    def depth_callback(self, msg: Image):
        self.depth_image = msg

    def depth_to_compresseddepth2(self, depth_msg):
        try:
            # Convert 32FC1 DepthImage to OpenCV Mat
            depth_image = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding='32FC1')

            # Replace NaN and infinite values with 0
            # depth_image = np.nan_to_num(depth_image, nan=0.0, posinf=0.0, neginf=0.0)
            # Replace NaN and infinite values with 10000.0
            depth_image = np.nan_to_num(depth_image,
                                        nan=10000.0,
                                        posinf=10000.0,
                                        neginf=10000.0)

            # Convert 32FC1 to 16UC1 (convert to mm)
            depth_16u = (depth_image * 1000).clip(None, 65535).astype(np.uint16)

            compressed_msg = self.bridge.cv2_to_compressed_imgmsg(depth_16u, dst_format='png')

            header_12_bytes = np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.uint8)
            final_data = np.concatenate((header_12_bytes, np.array(compressed_msg.data))).tolist()

            final_msg = CompressedImage()
            final_msg.header.stamp = depth_msg.header.stamp
            final_msg.header.frame_id = depth_msg.header.frame_id
            final_msg.format = "16UC1; compressedDepth"
            final_msg.data = final_data

            return final_msg
        except Exception as e:
            self.get_logger().error(f'Error in depth_to_compresseddepth: {str(e)}')
            return None

    def depth_to_compresseddepth(self, depth_msg):
        try:
            # Convert 32FC1 DepthImage to OpenCV Mat
            depth_image = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding='32FC1')

            # Replace NaN and infinite values with 0
            # depth_image = np.nan_to_num(depth_image, nan=0.0, posinf=0.0, neginf=0.0)
            # Replace NaN and infinite values with 10000.0
            depth_image = np.nan_to_num(depth_image,
                                        nan=10000.0,
                                        posinf=10000.0,
                                        neginf=10000.0)

            # Convert 32FC1 to 16UC1 (convert to mm)
            depth_16u = (depth_image * 1000).clip(None, 65535).astype(np.uint16)

            # Create a 12-byte header
            header_data = bytearray()

            # Header structure (12-byte version)
            # 4 bytes: image height
            # 4 bytes: image width
            # 4 bytes: depth quantization (usually 1000 = mm unit)
            height, width = depth_16u.shape
            quantization = 1000  # in mm unit

            header_data.extend(height.to_bytes(4, byteorder='little'))
            header_data.extend(width.to_bytes(4, byteorder='little'))
            header_data.extend(quantization.to_bytes(4, byteorder='little'))

            # PNG compression
            success, png_data = cv2.imencode('.png', depth_16u,
                                             [cv2.IMWRITE_PNG_COMPRESSION, 9])

            if not success:
                raise Exception("Failed to encode depth image as PNG")

            # Create CompressedImage message
            compressed_msg = CompressedImage()
            compressed_msg.header = depth_msg.header
            compressed_msg.format = "16UC1;compressedDepth"

            # Combine 12-byte header + PNG data
            compressed_msg.data = bytes(header_data) + png_data.tobytes()

            return compressed_msg
        except Exception as e:
            self.get_logger().error(f'Error in depth_to_compresseddepth: {str(e)}')
            return None

    def bbox_callback(self, bbox_msg: BoundingBoxes):
        # Skip if necessary data is not available
        if self.camera_info is None or self.rgb_image is None or self.depth_image is None:
            self.get_logger().warn('Awaiting camera_info, rgb_image, or depth_image...')
            return

        inst_msg = InstanceSegmentation()
        inst_msg.header = bbox_msg.header

        filtered_bounding_boxes = self.filter_bboxes(bbox_msg.bounding_boxes)

        inst_msg.is_detected = len(filtered_bounding_boxes) > 0
        inst_msg.camera_info = self.camera_info

        # JPEG compression for RGB image
        cv_rgb = self.bridge.imgmsg_to_cv2(self.rgb_image, desired_encoding='bgr8')
        comp_rgb = self.bridge.cv2_to_compressed_imgmsg(cv_rgb, dst_format='jpg')
        comp_rgb.header = self.rgb_image.header
        inst_msg.rgb = comp_rgb

        # Set format for Depth image
        inst_msg.depth = self.depth_image
        inst_msg.depth.format = '16UC1; compressedDepth'

        # Map Bounding box to InstanceSegmentation.BBox
        for box in filtered_bounding_boxes:
            b = BBox()
            # b.id = box.id
            b.id = self.coco_class_mapper[box.class_id]
            b.name = box.class_id
            b.score = float(box.probability)
            b.x = box.xmin
            b.y = box.ymin
            b.w = box.xmax - box.xmin
            b.h = box.ymax - box.ymin
            # b.track_id = box.id  # Use box.id if track ID information is not available
            b.track_id = b.id  # Use box.id if track ID information is not available
            inst_msg.bbox.append(b)
            # Limit the output bbox to 1 or less.
            break
        segment_msg = img_and_bbox_to_segment(self.rgb_image, inst_msg.bbox)
        inst_msg.segment = segment_msg

        self.pub.publish(inst_msg)
        self.get_logger().info(f'Published InstanceSegmentation with {len(inst_msg.bbox)} boxes')
        inst_msg_rgb = inst_msg.rgb
        inst_msg_rgb.format = 'jpeg'
        self.tmp_pub_result_rgb.publish(inst_msg_rgb)
        inst_msg_depth = inst_msg.depth
        inst_msg_depth.format = '16UC1; png'
        self.tmp_pub_result_depth.publish(inst_msg_depth)
        self.tmp_pub_result_segment.publish(inst_msg.segment)


def main(args=None):
    rclpy.init(args=args)
    node = YoloxBridgeNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
