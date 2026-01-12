import torch
import numpy as np
from .helper import ImageProcessingHelper

MAX_RESOLUTION = 8192

class MaskSplitAndGrowBase:
    OUTPUT_NODE = False
    CATEGORY = "image/mask"

    def _prepare_mask(self, mask):
        # Ensure 3D mask [B, H, W]
        if mask.dim() == 2:
            mask = mask.unsqueeze(0)
        return mask

    def _get_white_rows(self, mask):
        # Calculate row sums efficiently
        # mask is [B, H, W]
        row_sums = mask.sum(dim=2).sum(dim=0)
        white_rows = torch.nonzero(row_sums).squeeze(-1)
        return white_rows

    def _calculate_split_points(self, height, white_rows, ratios):
        points = []
        if len(white_rows) == 0:
            # Fallback to absolute height
            for r in ratios:
                points.append(int(height * r))
        else:
            # Calculate within white region
            white_min = white_rows[0].item()
            white_max = white_rows[-1].item()
            white_height = white_max - white_min + 1
            for r in ratios:
                points.append(white_min + int(white_height * r))
        return points

    def _grow_masks(self, masks, expand, tapered_corners):
        processed_masks = []
        for m in masks:
             # Use helper for growing mask
            processed_masks.append(ImageProcessingHelper.grow_mask(m, expand, tapered_corners))
        return tuple(processed_masks)

class MaskSplitAndGrow2Ways(MaskSplitAndGrowBase):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "mask": ("MASK",),
                "split_y": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "expand": ("INT", {"default": 0, "min": -MAX_RESOLUTION, "max": MAX_RESOLUTION, "step": 1}),
                "tapered_corners": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("MASK", "MASK")
    FUNCTION = "split_and_grow_mask"

    def split_and_grow_mask(self, mask, split_y, expand, tapered_corners):
        mask = self._prepare_mask(mask)
        batch, height, width = mask.shape
        
        white_rows = self._get_white_rows(mask)
        split_points = self._calculate_split_points(height, white_rows, [split_y])
        split_point = split_points[0]

        upper_mask = mask.clone()
        upper_mask[:, split_point:, :] = 0 

        lower_mask = mask.clone()
        lower_mask[:, :split_point, :] = 0 

        return self._grow_masks([upper_mask, lower_mask], expand, tapered_corners)

class MaskSplitAndGrow3Ways(MaskSplitAndGrowBase):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "mask": ("MASK",),
                "split_y1": ("FLOAT", {"default": 0.33, "min": 0.0, "max": 1.0, "step": 0.01}),
                "split_y2": ("FLOAT", {"default": 0.67, "min": 0.0, "max": 1.0, "step": 0.01}),
                "expand": ("INT", {"default": 0, "min": -MAX_RESOLUTION, "max": MAX_RESOLUTION, "step": 1}),
                "tapered_corners": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("MASK", "MASK", "MASK")
    FUNCTION = "split_and_grow_mask"

    def split_and_grow_mask(self, mask, split_y1, split_y2, expand, tapered_corners):
        mask = self._prepare_mask(mask)
        batch, height, width = mask.shape
        
        white_rows = self._get_white_rows(mask)
        split_points = self._calculate_split_points(height, white_rows, [split_y1, split_y2])
        sp1, sp2 = split_points[0], split_points[1]

        upper_mask = mask.clone()
        upper_mask[:, sp1:, :] = 0 

        middle_mask = mask.clone()
        middle_mask[:, :sp1, :] = 0
        middle_mask[:, sp2:, :] = 0 

        lower_mask = mask.clone()
        lower_mask[:, :sp2, :] = 0 

        return self._grow_masks([upper_mask, middle_mask, lower_mask], expand, tapered_corners)