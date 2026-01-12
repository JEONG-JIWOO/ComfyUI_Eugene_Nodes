import numpy as np
import torch
import cv2
import scipy.ndimage
from scipy.ndimage import gaussian_filter, binary_dilation
import torchvision.transforms as T

# Constants
MAX_RESOLUTION = 8192

"""

1. comfyui의 커스텀 노드를 만드는중이야. 현재 보여주는 기능은 왠만하면 다 동작하며 이 구조를 개선하는게 목적이야

2. IO에있어서 comfyui의 표준을 준수하고자해
a. 이미지
- 입력 : [B,H,W,C] : 채널은 3(RGB)또는 RGBA야
- 노드 내부 : [B,H,W,4] : 무조건 RGBA로 변환해서 프로세싱을 진행해
ALPHA는
우선순위 1. 마스크가 따로 입력됬으면 그걸 알파로 사용
우선순위 2. 마스크가 없고 알파채널이 있으면 그걸사용
우선순위 3. 마스크도 없고 알파채널이 없으면 기본값을 생성해서 사용
이 변환은 반드시 노드 내부에서 제일 처음에 데이터를 받고서 수행될거야. 그리고 내부처리에는 모두 [B,H,W,4]를 사용해

- 리턴 : [B,H,W,4] 로 리턴할거야.

b. 마스크
- 입력 [B,H,W]
- 노드내부 : [B,H,W,1] 연산의 용이성을 위해서 4차원으로 변환해서 사용할거야.
- 노드 외부 리턴 : 다시 [B,H,W]로 변환해서 리턴해


"""

class OpenPoseKeypointHelper:
    openpose_keypoints = {
        "None": None,
        "Nose": 0, "Neck": 1, "RightShoulder": 2, "RightElbow": 3, "RightWrist": 4,
        "LeftShoulder": 5, "LeftElbow": 6, "LeftWrist": 7, "RightHip": 8, "RightKnee": 9,
        "RightAnkle": 10, "LeftHip": 11, "LeftKnee": 12, "LeftAnkle": 13, "RightEye": 14,
        "LeftEye": 15, "RightEar": 16, "LeftEar": 17
    }

    @staticmethod
    def get_largest_person(pose_keypoint):
        people = pose_keypoint[0]['people']
        if not people:
            return None

        largest_area = 0
        largest_person = None

        for person in people:
            keypoints = np.array(person['pose_keypoints_2d']).reshape(-1, 3)
            valid_keypoints = keypoints[keypoints[:, 2] > 0]  # confidence > 0
            if len(valid_keypoints) < 2:
                continue
            x_min, y_min = valid_keypoints[:, :2].min(axis=0)
            x_max, y_max = valid_keypoints[:, :2].max(axis=0)
            area = (x_max - x_min) * (y_max - y_min)
            if area > largest_area:
                largest_area = area
                largest_person = person

        return largest_person

    @staticmethod
    def get_keypoint_coordinate(pose_keypoint, keypoint_name, target_size=None):
        if keypoint_name == "None":
            return None
        largest_person = OpenPoseKeypointHelper.get_largest_person(pose_keypoint)
        if not largest_person:
            return None

        pose = largest_person['pose_keypoints_2d']
        pose_size = (pose_keypoint[0]["canvas_height"], pose_keypoint[0]["canvas_width"])

        index = OpenPoseKeypointHelper.openpose_keypoints[keypoint_name]
        x = pose[index * 3]
        y = pose[index * 3 + 1]
        confidence = pose[index * 3 + 2]

        if confidence == 0:
            return None

        if target_size:
            scale_x = target_size[1] / pose_size[1]
            scale_y = target_size[0] / pose_size[0]
            x = int(x * scale_x)
            y = int(y * scale_y)

        return (x, y)

    @staticmethod
    def get_multiple_keypoint_coordinates(pose_keypoint, keypoint_names, target_size=None):
        return [OpenPoseKeypointHelper.get_keypoint_coordinate(pose_keypoint, name, target_size)
                for name in keypoint_names if name != "None"]

class YoloPoseKeypointHelper:
    # COCO 포맷 기준 keypoint 이름과 인덱스 매핑 (YoloPose는 COCO 순서 사용)
    yolo_keypoints = {
        "None": None,
        "Nose": 0, "LeftEye": 1, "RightEye": 2, "LeftEar": 3, "RightEar": 4,
        "LeftShoulder": 5, "RightShoulder": 6, "LeftElbow": 7, "RightElbow": 8,
        "LeftWrist": 9, "RightWrist": 10, "LeftHip": 11, "RightHip": 12,
        "LeftKnee": 13, "RightKnee": 14, "LeftAnkle": 15, "RightAnkle": 16
    }

    @staticmethod
    def get_largest_person(keypoints):
        # keypoints.xy: (N, 17, 2)
        # keypoints.conf: (N, 17)
        if keypoints.xy.shape[0] == 0:
            return None

        largest_area = 0
        largest_idx = None

        for idx in range(keypoints.xy.shape[0]):
            xy = keypoints.xy[idx].cpu().numpy()  # (17, 2)
            conf = keypoints.conf[idx].cpu().numpy()  # (17,)
            valid = conf > 0
            if valid.sum() < 2:
                continue
            valid_xy = xy[valid]
            x_min, y_min = valid_xy.min(axis=0)
            x_max, y_max = valid_xy.max(axis=0)
            area = (x_max - x_min) * (y_max - y_min)
            if area > largest_area:
                largest_area = area
                largest_idx = idx

        return largest_idx

    @staticmethod
    def get_keypoint_coordinate(keypoints, keypoint_name, target_size=None):
        if keypoint_name == "None":
            return None
        idx = YoloPoseKeypointHelper.get_largest_person(keypoints)
        if idx is None:
            return None

        kp_idx = YoloPoseKeypointHelper.yolo_keypoints[keypoint_name]
        x, y = keypoints.xy[idx, kp_idx].tolist()
        conf = keypoints.conf[idx, kp_idx].item()

        if conf == 0:
            return None

        if target_size is not None:
            orig_h, orig_w = keypoints.orig_shape
            scale_x = target_size[1] / orig_w
            scale_y = target_size[0] / orig_h
            x = int(x * scale_x)
            y = int(y * scale_y)

        return (x, y)

    @staticmethod
    def get_multiple_keypoint_coordinates(keypoints, keypoint_names, target_size=None):
        return [YoloPoseKeypointHelper.get_keypoint_coordinate(keypoints, name, target_size)
                for name in keypoint_names if name != "None"]

class DrawingHelper:
    @staticmethod
    def _check_input(tensor):
        if not isinstance(tensor, torch.Tensor):
            raise TypeError("Input must be a PyTorch tensor")
        if tensor.dim() != 4:
            raise ValueError("Input tensor must have 4 dimensions [B,H,W,C]")
        if tensor.shape[3] not in [1, 4]:
            raise ValueError("Last dimension must be 1 (mask) or 4 (image)")
        return tensor.shape[3] == 4

    @staticmethod
    def _check_color(color, is_image):
        if is_image:
            if not isinstance(color, (list, tuple)) or len(color) != 4:
                raise ValueError("Color for image must have 4 channels (RGBA)")
            return [c / 255.0 for c in color]
        else:
            if not isinstance(color, (int, float)):
                raise ValueError("Color for mask must be a single value")
            return float(color)
    @staticmethod
    def _apply_drawing(tensor, draw_func):
        is_image = DrawingHelper._check_input(tensor)
        result = tensor.clone()
        for b in range(tensor.shape[0]):
            slice = result[b].cpu().numpy()
            draw_func(slice)
            result[b] = torch.from_numpy(slice)
        return result

    @classmethod
    def draw_line(cls, tensor, start, end, color, thickness=1):
        color = cls._check_color(color, cls._check_input(tensor))
        def draw(slice):
            cv2.line(slice, start, end, color, thickness)
        return cls._apply_drawing(tensor, draw)

    @classmethod
    def draw_circle(cls, tensor, center, radius, color, thickness=-1):
        color = cls._check_color(color, cls._check_input(tensor))
        def draw(slice):
            cv2.circle(slice, center, radius, color, thickness)
        return cls._apply_drawing(tensor, draw)

    @classmethod
    def draw_rectangle(cls, tensor, start, end, color, thickness=1):
        color = cls._check_color(color, cls._check_input(tensor))
        def draw(slice):
            cv2.rectangle(slice, start, end, color, thickness)
        return cls._apply_drawing(tensor, draw)

    @classmethod
    def draw_rotated_rectangle(cls, tensor, center, size, angle, color, thickness=1):
        color = cls._check_color(color, cls._check_input(tensor))

        def draw(slice):
            # OpenCV의 회전 각도는 반시계 방향이 양수이므로, 부호를 반대로 바꿉니다.
            rect = ((center[0], center[1]), (size[0], size[1]), -angle)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            cv2.drawContours(slice, [box], 0, color, thickness)

        return cls._apply_drawing(tensor, draw)

class ImageProcessingHelper:
    @staticmethod
    def prepare_image(image, mask=None):
        # 입력 이미지를 [B,H,W,4] 형태로 변환
        if image.shape[3] == 3:
            image = torch.cat([image, torch.ones_like(image[:, :, :, :1])], dim=3)

        # 마스크 처리
        if mask is not None:
            if len(mask.shape) == 3:
                mask = mask.unsqueeze(-1)
            image[:, :, :, 3] = mask.squeeze(-1)

        return image

    @staticmethod
    def prepare_mask(mask):
        # 마스크를 [B,H,W,1] 형태로 변환
        if len(mask.shape) == 3:
            return mask.unsqueeze(-1)
        return mask

    @staticmethod
    def finalize_mask(mask):
        # 마스크를 [B,H,W] 형태로 변환하여 반환
        return mask.squeeze(-1)

    @staticmethod
    def finalize_image(image):
        # 이미지를 [B,H,W,4] 형태로 유지
        return image

    @staticmethod
    def smooth_and_dilate_mask(mask, tolerance, iterations):
        smoothed = gaussian_filter(mask, sigma=tolerance)
        threshold = np.max(smoothed) / 2
        binary = np.where(smoothed >= threshold, 1, 0).astype(np.uint8)
        dilated = binary_dilation(binary, iterations=iterations)
        return dilated.astype(np.float32)

    @staticmethod
    def composite_images(original, overlay, mask, overlay_mask, x, y, size):
        start_x, start_y = int(x - size / 2), int(y - size / 2)
        end_x, end_y = start_x + size, start_y + size

        start_x = max(0, start_x)
        start_y = max(0, start_y)
        end_x = min(original.shape[2], end_x)
        end_y = min(original.shape[1], end_y)

        crop_height = end_y - start_y
        crop_width = end_x - start_x

        original_crop = original[:, start_y:end_y, start_x:end_x, :]
        mask_crop = mask[:, start_y:end_y, start_x:end_x, :]

        overlay_resized = torch.nn.functional.interpolate(overlay.permute(0, 3, 1, 2),
                                                          size=(crop_height, crop_width),
                                                          mode='bilinear',
                                                          align_corners=False).permute(0, 2, 3, 1)
        overlay_mask_resized = torch.nn.functional.interpolate(overlay_mask.permute(0, 3, 1, 2),
                                                               size=(crop_height, crop_width),
                                                               mode='nearest').permute(0, 2, 3, 1)

        alpha = mask_crop * overlay_mask_resized
        alpha = alpha.expand(-1, -1, -1, 4)

        composed_crop = original_crop * (1 - alpha) + overlay_resized * alpha

        result = original.clone()
        result[:, start_y:end_y, start_x:end_x, :] = composed_crop

        return result

    @staticmethod
    def prepare_input_mask(input_mask, target_size):
        """
        입력 마스크의 크기를 타겟 크기에 맞게 조정합니다.
        Returns [B, H, W, 1]
        """
        if isinstance(input_mask, torch.Tensor):
            if len(input_mask.shape) == 2:  # [H,W]
                input_mask = input_mask.unsqueeze(0)  # [1,H,W]
            
            if len(input_mask.shape) == 3:  # [B,H,W]
                input_mask = input_mask.unsqueeze(-1)  # [B,H,W,1]
                
            input_size = (input_mask.shape[1], input_mask.shape[2])
        else:
            raise ValueError("입력 마스크는 torch.Tensor 형식이어야 합니다.")
            
        if input_size[0] != target_size[0] or input_size[1] != target_size[1]:
            input_mask_permuted = input_mask.permute(0, 3, 1, 2)
            resized_mask = torch.nn.functional.interpolate(
                input_mask_permuted, 
                size=target_size, 
                mode='nearest'
            )
            return resized_mask.permute(0, 2, 3, 1)
        
        return input_mask

    @staticmethod
    def grow_mask(mask, expand, tapered_corners):
        if expand == 0:
            return mask

        c = 0 if tapered_corners else 1
        kernel = np.array([[c, 1, c],
                           [1, 1, 1],
                           [c, 1, c]])

        out = []
        for m in mask:
            output = m.cpu().numpy()
            for _ in range(abs(expand)):
                if expand < 0:
                    output = scipy.ndimage.grey_erosion(output, footprint=kernel)
                else:
                    output = scipy.ndimage.grey_dilation(output, footprint=kernel)
            output = torch.from_numpy(output).to(mask.device)
            out.append(output)

        return torch.stack(out, dim=0)

class GeometryHelper:
    @staticmethod
    def calculate_middle_point(x1, y1, x2, y2):
        x1, y1, x2, y2 = map(lambda x: torch.tensor(x, dtype=torch.float32), (x1, y1, x2, y2))

        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        length = torch.sqrt(dx.pow(2) + dy.pow(2))

        # 각도를 계산할 때 y축 방향을 고려합니다
        angle = torch.atan2(-dy, dx) * 180 / torch.pi

        return mx.item(), my.item(), angle.item(), length.item()

    @staticmethod
    def apply_offset(mx, my, angle, length, offset):
        mx, my, angle, length, offset = map(lambda x: torch.tensor(x, dtype=torch.float32),
                                            (mx, my, angle, length, offset))
        # 각도를 라디안으로 변환
        angle_rad = angle * torch.pi / 180

        # 오프셋 적용 (y축 방향 고려)
        offset_x = offset * torch.cos(angle_rad) * length
        offset_y = offset * torch.sin(angle_rad) * length

        new_mx = mx + offset_x
        new_my = my - offset_y  # y축 방향을 고려하여 부호를 변경

        return new_mx.item(), new_my.item()

class TensorHelper:
    @staticmethod
    def create_empty_mask(image_size):
        return torch.zeros((1, image_size[0], image_size[1], 1), dtype=torch.float32, device="cpu")

    @staticmethod
    def prepare_overlay(overlay_image, overlay_mask, square_size, angle, offset_x, offset_y):
        B, H, W, C = overlay_image.shape

        overlay_image_np = overlay_image[0].cpu().numpy()
        overlay_mask_np = overlay_mask[0].cpu().numpy().squeeze(-1)

        # ComfyUI 각도를 OpenCV 각도로 변환
        cv2_angle = angle + 90  # 시계 방향으로 90도 덜 회전

        center = (W // 2, H // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, cv2_angle, 1.0)

        # 오프셋 적용 (y 축 방향 반전)
        rotation_matrix[0, 2] += offset_x
        rotation_matrix[1, 2] -= offset_y  # y 축 방향 반전

        # 이미지 회전
        rotated_image = cv2.warpAffine(overlay_image_np, rotation_matrix, (W, H),
                                       flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_CONSTANT,
                                       borderValue=0)

        # 마스크 회전 - 이진 마스크로 처리
        _, binary_mask = cv2.threshold(overlay_mask_np, 0.5, 1, cv2.THRESH_BINARY)
        rotated_mask = cv2.warpAffine(binary_mask, rotation_matrix, (W, H),
                                      flags=cv2.INTER_NEAREST,
                                      borderMode=cv2.BORDER_CONSTANT,
                                      borderValue=0)

        # 크기 조정
        resized_image = cv2.resize(rotated_image, (square_size, square_size), interpolation=cv2.INTER_LINEAR)
        resized_mask = cv2.resize(rotated_mask, (square_size, square_size), interpolation=cv2.INTER_NEAREST)

        # NumPy 배열을 텐서로 변환
        resized_image_tensor = torch.from_numpy(resized_image).float().unsqueeze(0)
        resized_mask_tensor = torch.from_numpy(resized_mask).float().unsqueeze(0).unsqueeze(-1)

        return resized_image_tensor, resized_mask_tensor

class InpaintingUtils:
    @staticmethod
    def get_mask_bbox(mask, threshold=0.01):
        # 마스크 차원 확인 및 처리
        if len(mask.shape) == 3 and mask.shape[0] == 1:
            mask = mask.squeeze(0)  # [H, W] 형태로 변환
        
        # 마스크에서 임계값 이상인 픽셀 찾기
        mask_binary = (mask > threshold).float()
        if not torch.any(mask_binary):
            return None  # 마스크가 비어있음
        
        # 마스크의 바운딩 박스 계산
        nonzero_indices = torch.nonzero(mask_binary)
        if nonzero_indices.shape[0] == 0:
            return None
        
        min_y = torch.min(nonzero_indices[:, 0]).item()
        max_y = torch.max(nonzero_indices[:, 0]).item()
        min_x = torch.min(nonzero_indices[:, 1]).item()
        max_x = torch.max(nonzero_indices[:, 1]).item()
        
        return min_y, min_x, max_y, max_x

    @staticmethod
    def adjust_bbox_to_multiple_of_8(bbox, image_height, image_width):
        min_y, min_x, max_y, max_x = bbox
        
        # 8의 배수로 조정
        min_x = (min_x // 8) * 8
        min_y = (min_y // 8) * 8
        max_x = ((max_x + 7) // 8) * 8
        max_y = ((max_y + 7) // 8) * 8
        
        # 이미지 경계 확인
        min_x = max(0, min_x)
        min_y = max(0, min_y)
        max_x = min(image_width, max_x)
        max_y = min(image_height, max_y)
        
        return min_y, min_x, max_y, max_x

    @staticmethod
    def expand_bbox(bbox, padding_ratio, image_height, image_width, min_padding=8):
        min_y, min_x, max_y, max_x = bbox
        
        height = max_y - min_y
        width = max_x - min_x
        
        pad_y = max(int(height * padding_ratio), min_padding)
        pad_x = max(int(width * padding_ratio), min_padding)
        
        new_min_y = max(0, min_y - pad_y)
        new_min_x = max(0, min_x - pad_x)
        new_max_y = min(image_height, max_y + pad_y)
        new_max_x = min(image_width, max_x + pad_x)
        
        return new_min_y, new_min_x, new_max_y, new_max_x

    @staticmethod
    def create_feather_mask(size, feather):
        h, w = size
        mask = torch.ones((h, w))
        
        if feather <= 0:
            return mask
        
        for i in range(feather):
            mask[i, :] = i / feather
            mask[h - 1 - i, :] = i / feather
            mask[:, i] = i / feather
            mask[:, w - 1 - i] = i / feather
        
        gaussian_blur = T.GaussianBlur(kernel_size=feather*2+1, sigma=feather/3)
        mask = mask.unsqueeze(0).unsqueeze(0)  # [1, 1, h, w]
        mask = gaussian_blur(mask)
        mask = mask.squeeze()  # [h, w]
        
        return mask

    @staticmethod
    def crop_and_resize_images_by_masks(images, masks, padding_ratio, resize_scale, max_size):
        first_image = images[0]
        if first_image.ndim != 4 or first_image.shape[0] != 1:
            raise ValueError(f"Unsupported image shape: {first_image.shape}. Expected [1, H, W, C].")
        image_height, image_width = first_image.shape[1:3]
        device = first_image.device

        all_bboxes = []
        for mask in masks:
            bbox = InpaintingUtils.get_mask_bbox(mask.to(device))
            if bbox:
                all_bboxes.append(bbox)
        if not all_bboxes:
            # warning removed or logged
            combined_bbox = (0, 0, image_height - 1, image_width - 1)
        else:
            min_y = min(b[0] for b in all_bboxes)
            min_x = min(b[1] for b in all_bboxes)
            max_y = max(b[2] for b in all_bboxes)
            max_x = max(b[3] for b in all_bboxes)
            combined_bbox = (min_y, min_x, max_y, max_x)

        expanded_bbox = InpaintingUtils.expand_bbox(combined_bbox, padding_ratio, image_height, image_width)
        adj_min_y, adj_min_x, adj_max_y, adj_max_x = InpaintingUtils.adjust_bbox_to_multiple_of_8(expanded_bbox, image_height, image_width)

        orig_crop_width = adj_max_x - adj_min_x
        orig_crop_height = adj_max_y - adj_min_y
        if orig_crop_width <= 0 or orig_crop_height <= 0:
            raise ValueError(f"Invalid original crop size calculated: W={orig_crop_width}, H={orig_crop_height}.")

        target_scale = resize_scale
        if orig_crop_width * target_scale > max_size or orig_crop_height * target_scale > max_size:
            scale_w = max_size / orig_crop_width
            scale_h = max_size / orig_crop_height
            target_scale = min(scale_w, scale_h)
        
        target_w = int(orig_crop_width * target_scale)
        target_h = int(orig_crop_height * target_scale)
        target_w = max(8, (target_w // 8) * 8)
        target_h = max(8, (target_h // 8) * 8)

        resized_images = []
        resized_masks_for_latent = []
        for img, msk in zip(images, masks):
            cropped_img = img[:, adj_min_y:adj_max_y, adj_min_x:adj_max_x, :]

            resized_img = torch.nn.functional.interpolate(
                cropped_img.permute(0, 3, 1, 2).float(),
                size=(target_h, target_w),
                mode="bilinear",
                align_corners=False
            ).permute(0, 2, 3, 1)
            resized_images.append(resized_img)

            current_msk = msk
            if current_msk.ndim == 2:
                current_msk = current_msk.unsqueeze(0)
            elif current_msk.ndim == 4 and current_msk.shape[0] == 1 and current_msk.shape[1] == 1:
                current_msk = current_msk.squeeze(1)
            elif current_msk.ndim != 3 or current_msk.shape[0] != 1:
                try:
                    slice_msk = current_msk[0]
                    while slice_msk.ndim > 2:
                        slice_msk = slice_msk.squeeze(0)
                    current_msk = slice_msk.unsqueeze(0)
                except Exception as e:
                    current_msk = torch.zeros((1, image_height, image_width), device=device)

            cropped_msk = current_msk[:, adj_min_y:adj_max_y, adj_min_x:adj_max_x]

            target_latent_h = target_h // 8
            target_latent_w = target_w // 8
            resized_msk_latent = torch.nn.functional.interpolate(
                cropped_msk.unsqueeze(1).float(),
                size=(target_latent_h, target_latent_w),
                mode="nearest"
            ).squeeze(1)
            resized_masks_for_latent.append(resized_msk_latent)

        return (resized_images, resized_masks_for_latent,
                adj_min_x, adj_min_y, orig_crop_width, orig_crop_height,
                target_w, target_h)

class PoseMaskHelper:
    @staticmethod
    def process_pose_mask(
        keypoint_helper_cls,
        original_image, 
        POSE_KEYPOINT,
        points_a, points_b, points_c, points_d,
        radius_pixels, smooth_mask, input_mask
    ):
        """
        Common logic for processing pose masks (Shared by DwposeMask and YoloPoseMask)
        points_a, points_b... are lists of keypoint names [start_point, end_point]
        """
        original_image = ImageProcessingHelper.prepare_image(original_image)
        image_size = original_image.shape[1:3]

        coords_a = keypoint_helper_cls.get_multiple_keypoint_coordinates(POSE_KEYPOINT, points_a, image_size)
        coords_b = keypoint_helper_cls.get_multiple_keypoint_coordinates(POSE_KEYPOINT, points_b, image_size)
        coords_c = keypoint_helper_cls.get_multiple_keypoint_coordinates(POSE_KEYPOINT, points_c, image_size)
        coords_d = keypoint_helper_cls.get_multiple_keypoint_coordinates(POSE_KEYPOINT, points_d, image_size)

        mask_line_a = TensorHelper.create_empty_mask(image_size)
        mask_line_b = TensorHelper.create_empty_mask(image_size)
        mask_line_c = TensorHelper.create_empty_mask(image_size)
        mask_line_d = TensorHelper.create_empty_mask(image_size)

        debug_image = original_image.clone()

        def draw_line_and_points(mask, debug_img, coords, color_mask, color_debug):
            if len(coords) == 2:
                mask = DrawingHelper.draw_line(mask, coords[0], coords[1], color_mask, thickness=radius_pixels * 2)
                debug_img = DrawingHelper.draw_line(debug_img, coords[0], coords[1], color_debug, thickness=radius_pixels * 2)
                
                mask = DrawingHelper.draw_circle(mask, coords[0], radius_pixels, color_mask)
                mask = DrawingHelper.draw_circle(mask, coords[1], radius_pixels, color_mask)
                debug_img = DrawingHelper.draw_circle(debug_img, coords[0], radius_pixels, color_debug, thickness=2)
                debug_img = DrawingHelper.draw_circle(debug_img, coords[1], radius_pixels, color_debug, thickness=2)
            elif len(coords) == 1:
                mask = DrawingHelper.draw_circle(mask, coords[0], radius_pixels, color_mask)
                debug_img = DrawingHelper.draw_circle(debug_img, coords[0], radius_pixels, color_debug, thickness=2)
            return mask, debug_img

        mask_line_a, debug_image = draw_line_and_points(mask_line_a, debug_image, coords_a, 1.0, [0, 255, 0, 255])
        mask_line_b, debug_image = draw_line_and_points(mask_line_b, debug_image, coords_b, 1.0, [0, 0, 255, 255])
        mask_line_c, debug_image = draw_line_and_points(mask_line_c, debug_image, coords_c, 1.0, [255, 0, 0, 255])
        mask_line_d, debug_image = draw_line_and_points(mask_line_d, debug_image, coords_d, 1.0, [255, 255, 0, 255])

        mask_combined = torch.max(torch.max(torch.max(mask_line_a, mask_line_b), mask_line_c), mask_line_d)

        if input_mask is not None:
            input_mask_prepared = ImageProcessingHelper.prepare_input_mask(input_mask, image_size)
            mask_with_input = mask_combined * input_mask_prepared
        else:
            mask_with_input = mask_combined.clone()

        def process_mask_smoothing(mask):
            mask_np = mask.squeeze().cpu().numpy()
            if smooth_mask > 0:
                mask_np = gaussian_filter(mask_np, sigma=smooth_mask)
            return torch.from_numpy(mask_np).unsqueeze(0).unsqueeze(-1)

        if smooth_mask > 0:
            mask_line_a = process_mask_smoothing(mask_line_a)
            mask_line_b = process_mask_smoothing(mask_line_b)
            mask_line_c = process_mask_smoothing(mask_line_c)
            mask_line_d = process_mask_smoothing(mask_line_d)
            mask_combined = process_mask_smoothing(mask_combined)
            mask_with_input = process_mask_smoothing(mask_with_input)

        mask_line_a = ImageProcessingHelper.finalize_mask(mask_line_a)
        mask_line_b = ImageProcessingHelper.finalize_mask(mask_line_b)
        mask_line_c = ImageProcessingHelper.finalize_mask(mask_line_c)
        mask_line_d = ImageProcessingHelper.finalize_mask(mask_line_d)
        mask_combined = ImageProcessingHelper.finalize_mask(mask_combined)
        mask_with_input = ImageProcessingHelper.finalize_mask(mask_with_input)
        debug_image = ImageProcessingHelper.finalize_image(debug_image)

        return (mask_line_a, mask_line_b, mask_line_c, mask_line_d, mask_combined, mask_with_input, debug_image)