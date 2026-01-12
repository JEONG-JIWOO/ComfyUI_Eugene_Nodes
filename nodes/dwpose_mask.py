from .helper import OpenPoseKeypointHelper, YoloPoseKeypointHelper, PoseMaskHelper

class DwposeMask:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pose_keypoint": ("POSE_KEYPOINT",),
                "original_image": ("IMAGE",),
                "points_a": (list(OpenPoseKeypointHelper.openpose_keypoints.keys()),),
                "points_b": (list(OpenPoseKeypointHelper.openpose_keypoints.keys()),),
                "points_c": (list(OpenPoseKeypointHelper.openpose_keypoints.keys()),),
                "points_d": (list(OpenPoseKeypointHelper.openpose_keypoints.keys()),),
                "radius_pixels": ("INT", {"default": 10, "min": 1, "max": 100}),
                "smooth_mask": ("INT", {"default": 0, "min": 0, "max": 100}),
            },
            "optional": {
                "input_mask": ("MASK",),
            }
        }

    RETURN_TYPES = ("MASK", "MASK", "MASK", "MASK", "MASK", "MASK", "IMAGE")
    RETURN_NAMES = ("mask_line_a", "mask_line_b", "mask_line_c", "mask_line_d", "mask_combined", "mask_with_input", "debug_image")
    FUNCTION = "process"
    CATEGORY = "mask"

    def process(self, pose_keypoint, original_image, points_a, points_b, points_c, points_d, radius_pixels, smooth_mask, input_mask=None):
        return PoseMaskHelper.process_pose_mask(
            OpenPoseKeypointHelper,
            original_image,
            pose_keypoint,
            [points_a], [points_b], [points_c], [points_d], # Make lists as the helper expects lists of keys
            radius_pixels,
            smooth_mask,
            input_mask
        )

class YoloPoseMask:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "yolo_pose_keypoint": ("YOLO_POSE_KEYPOINT",),
                "original_image": ("IMAGE",),
                "points_a": (list(YoloPoseKeypointHelper.yolo_keypoints.keys()),),
                "points_b": (list(YoloPoseKeypointHelper.yolo_keypoints.keys()),),
                "points_c": (list(YoloPoseKeypointHelper.yolo_keypoints.keys()),),
                "points_d": (list(YoloPoseKeypointHelper.yolo_keypoints.keys()),),
                "radius_pixels": ("INT", {"default": 10, "min": 1, "max": 100}),
                "smooth_mask": ("INT", {"default": 0, "min": 0, "max": 100}),
            },
            "optional": {
                "input_mask": ("MASK",),
            }
        }

    RETURN_TYPES = ("MASK", "MASK", "MASK", "MASK", "MASK", "MASK", "IMAGE")
    RETURN_NAMES = ("mask_line_a", "mask_line_b", "mask_line_c", "mask_line_d", "mask_combined", "mask_with_input", "debug_image")
    FUNCTION = "process"
    CATEGORY = "mask"

    def process(self, yolo_pose_keypoint, original_image, points_a, points_b, points_c, points_d, radius_pixels, smooth_mask, input_mask=None):
         return PoseMaskHelper.process_pose_mask(
            YoloPoseKeypointHelper,
            original_image,
            yolo_pose_keypoint,
            [points_a], [points_b], [points_c], [points_d], # Make lists as the helper expects lists of keys
            radius_pixels,
            smooth_mask,
            input_mask
        )