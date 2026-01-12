from .helper import OpenPoseKeypointHelper, YoloPoseKeypointHelper, GeometryHelper

class KeypointExtractor:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pose_keypoint": ("POSE_KEYPOINT",),
                "keypoint_name1": (list(OpenPoseKeypointHelper.openpose_keypoints.keys()),),
                "keypoint_name2": (list(OpenPoseKeypointHelper.openpose_keypoints.keys()),),
                "keypoint_name3": (list(OpenPoseKeypointHelper.openpose_keypoints.keys()),),
                "keypoint_name4": (list(OpenPoseKeypointHelper.openpose_keypoints.keys()),),
            },
             "optional": {
                "reference_image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("INT", "INT", "INT", "INT", "INT", "INT", "INT", "INT", "STRING")
    RETURN_NAMES = ("x1", "y1", "x2", "y2", "x3", "y3", "x4", "y4", "info_string")
    FUNCTION = "extract_keypoints"
    CATEGORY = "attributes"

    def extract_keypoints(self, pose_keypoint, keypoint_name1, keypoint_name2, keypoint_name3, keypoint_name4, reference_image=None):
        target_size = None
        if reference_image is not None:
            target_size = reference_image.shape[1:3]

        keypoint_names = [keypoint_name1, keypoint_name2, keypoint_name3, keypoint_name4]
        coords = OpenPoseKeypointHelper.get_multiple_keypoint_coordinates(pose_keypoint, keypoint_names, target_size)

        flattened_coords = []
        info_parts = []

        for name, coord in zip(keypoint_names, coords):
            if coord:
                flattened_coords.extend(coord)
                info_parts.append(f"{name}=({coord[0]}, {coord[1]})")
            else:
                flattened_coords.extend([0, 0])
                info_parts.append(f"{name}=(Not found)")

        info_string = ", ".join(info_parts)
        
        return tuple(flattened_coords + [info_string])

class BaseKeypointDivider:
    CATEGORY = "attributes"
    
    def process_division(self, keypoint_helper, pose_data, keypoint_name_a, keypoint_name_b, division_ratio, offset, reference_image=None):
        target_size = None
        canvas_height = 0
        canvas_width = 0
        
        # Handle canvas size extraction based on input type
        if hasattr(pose_data, 'orig_shape'): # Yolo
             canvas_height, canvas_width = pose_data.orig_shape
        elif isinstance(pose_data, list) and len(pose_data) > 0 and isinstance(pose_data[0], dict): # OpenPose
             canvas_height = pose_data[0].get("canvas_height", 0)
             canvas_width = pose_data[0].get("canvas_width", 0)

        if reference_image is not None:
             target_size = reference_image.shape[1:3]
             canvas_height, canvas_width = target_size

        coord_a = keypoint_helper.get_keypoint_coordinate(pose_data, keypoint_name_a, target_size)
        coord_b = keypoint_helper.get_keypoint_coordinate(pose_data, keypoint_name_b, target_size)

        if coord_a and coord_b:
            mx, my, angle, length = GeometryHelper.calculate_middle_point(
                coord_a[0], coord_a[1], coord_b[0], coord_b[1]
            )
            
            # Apply division ratio
            # ratio 0 is point A, 1 is point B. 0.5 is midpoint.
            # Using vector interpolation
            dx = coord_b[0] - coord_a[0]
            dy = coord_b[1] - coord_a[1]
            
            division_x = coord_a[0] + dx * division_ratio
            division_y = coord_a[1] + dy * division_ratio
            
            # Apply offset if needed
            if offset != 0:
                 # Recalculate based on the division point as center? 
                 # Or just shift the division point perpendicular to the line?
                 # GeometryHelper.apply_offset logic seems to assume mx, my is midpoint.
                 # Let's reuse it but pass the division point.
                 final_x, final_y = GeometryHelper.apply_offset(division_x, division_y, angle, length, offset)
            else:
                 final_x, final_y = division_x, division_y

            final_x = int(final_x)
            final_y = int(final_y)
            
            info_string = f"{keypoint_name_a}:({coord_a[0]},{coord_a[1]}), {keypoint_name_b}:({coord_b[0]},{coord_b[1]}) -> ({final_x},{final_y})"
            return (final_x, final_y, info_string)
            
        return (0, 0, "Keypoints not found")


class KeypointDivider(BaseKeypointDivider):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "pose_keypoint": ("POSE_KEYPOINT",),
                "keypoint_name_a": (list(OpenPoseKeypointHelper.openpose_keypoints.keys()),),
                "keypoint_name_b": (list(OpenPoseKeypointHelper.openpose_keypoints.keys()),),
                "division_ratio": ("FLOAT", {"default": 0.5, "min": -2.0, "max": 3.0, "step": 0.01}),
                "offset": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.01}),
            },
            "optional": {
                "reference_image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("x", "y", "info_string")
    FUNCTION = "divide_keypoints"

    def divide_keypoints(self, pose_keypoint, keypoint_name_a, keypoint_name_b, division_ratio, offset, reference_image=None):
        return self.process_division(OpenPoseKeypointHelper, pose_keypoint, keypoint_name_a, keypoint_name_b, division_ratio, offset, reference_image)


class YoloPoseKeypointDivider(BaseKeypointDivider):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "yolo_pose_keypoint": ("YOLO_POSE_KEYPOINT",),
                "keypoint_name_a": (list(YoloPoseKeypointHelper.yolo_keypoints.keys()),),
                "keypoint_name_b": (list(YoloPoseKeypointHelper.yolo_keypoints.keys()),),
                "division_ratio": ("FLOAT", {"default": 0.5, "min": -2.0, "max": 3.0, "step": 0.01}),
                "offset": ("FLOAT", {"default": 0.0, "min": -10.0, "max": 10.0, "step": 0.01}),
            },
            "optional": {
                "reference_image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("INT", "INT", "STRING")
    RETURN_NAMES = ("x", "y", "info_string")
    FUNCTION = "divide_keypoints"

    def divide_keypoints(self, yolo_pose_keypoint, keypoint_name_a, keypoint_name_b, division_ratio, offset, reference_image=None):
        return self.process_division(YoloPoseKeypointHelper, yolo_pose_keypoint, keypoint_name_a, keypoint_name_b, division_ratio, offset, reference_image)