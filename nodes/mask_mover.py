import torch
import numpy as np
from .helper import ImageProcessingHelper

class MaskMover:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required":
            {
                "base_mask": ("MASK",),
                "moving_mask": ("MASK",),
                "dx": ("INT", {"default": 0, "min": -4096, "max": 4096, "step": 1}),
                "dy": ("INT", {"default": 0, "min": -4096, "max": 4096, "step": 1}),
                "operation": (["Add", "Subtract", "Multiply", "Minimum", "Maximum"], {"default": "Add"}),
            },
            "optional": {
                "reference_image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("MASK", "IMAGE")
    RETURN_NAMES = ("result_mask", "debug_image")
    FUNCTION = "move_and_combine_masks"

    def move_and_combine_masks(self, base_mask, moving_mask, dx, dy, operation, reference_image=None):
        # Ensure masks are in the right format
        if len(base_mask.shape) == 3:  # [B,H,W]
            base_mask = base_mask.unsqueeze(-1)  # [B,H,W,1]
        
        if len(moving_mask.shape) == 3:  # [B,H,W]
            moving_mask = moving_mask.unsqueeze(-1)  # [B,H,W,1]
            
        # Get dimensions from base mask
        B, H, W, _ = base_mask.shape
        
        # Create empty result mask with same dimensions as base mask
        result_mask = torch.zeros_like(base_mask)
        
        # Create shifted version of moving mask
        shifted_mask = torch.zeros_like(base_mask)
        
        # Calculate source and target regions for the shift
        if dx >= 0:
            src_start_x, src_end_x = 0, W - dx
            dst_start_x, dst_end_x = dx, W
        else:
            src_start_x, src_end_x = -dx, W
            dst_start_x, dst_end_x = 0, W + dx
            
        if dy >= 0:
            src_start_y, src_end_y = 0, H - dy
            dst_start_y, dst_end_y = dy, H
        else:
            src_start_y, src_end_y = -dy, H
            dst_start_y, dst_end_y = 0, H + dy
            
        # Apply the shift if source and destination regions are valid
        if (src_end_x > src_start_x and src_end_y > src_start_y and 
            dst_end_x > dst_start_x and dst_end_y > dst_start_y):
            
            shifted_mask[:, dst_start_y:dst_end_y, dst_start_x:dst_end_x, :] = \
                moving_mask[:, src_start_y:src_end_y, src_start_x:src_end_x, :]
        
        # Combine masks based on selected operation
        if operation == "Add":
            result_mask = torch.clamp(base_mask + shifted_mask, 0, 1)
        elif operation == "Subtract":
            result_mask = torch.clamp(base_mask - shifted_mask, 0, 1)
        elif operation == "Multiply":
            result_mask = base_mask * shifted_mask
        elif operation == "Minimum":
            result_mask = torch.minimum(base_mask, shifted_mask)
        elif operation == "Maximum":
            result_mask = torch.maximum(base_mask, shifted_mask)
        
        # Create debug image
        debug_image = self.create_debug_image(base_mask, shifted_mask, result_mask, reference_image)
        
        # Return result mask in the expected format [B,H,W]
        return (result_mask.squeeze(-1), debug_image)
    
    def create_debug_image(self, base_mask, shifted_mask, result_mask, reference_image=None):
        # Create a debug visualization
        B, H, W, _ = base_mask.shape
        
        # If reference image is provided, use it as background
        if reference_image is not None:
            # Ensure reference image has the right dimensions
            if reference_image.shape[1:3] != (H, W):
                # Resize reference image to match mask dimensions
                ref_img = torch.nn.functional.interpolate(
                    reference_image.permute(0, 3, 1, 2),
                    size=(H, W),
                    mode='bilinear'
                ).permute(0, 2, 3, 1)
            else:
                ref_img = reference_image.clone()
                
            # Ensure reference image has 4 channels (RGBA)
            if ref_img.shape[3] == 3:
                ref_img = torch.cat([ref_img, torch.ones_like(ref_img[:, :, :, :1])], dim=3)
                
            debug_img = ref_img.clone()
        else:
            # Create a black background with alpha channel
            debug_img = torch.zeros((B, H, W, 4), dtype=torch.float32, device=base_mask.device)
            debug_img[:, :, :, 3] = 1.0  # Set alpha to 1
        
        # Overlay base mask in blue
        blue_mask = torch.zeros((B, H, W, 4), dtype=torch.float32, device=base_mask.device)
        blue_mask[:, :, :, 2] = 0.5  # Blue channel
        blue_mask[:, :, :, 3] = base_mask[:, :, :, 0] * 0.5  # Alpha from mask, semi-transparent
        
        # Overlay shifted mask in red
        red_mask = torch.zeros((B, H, W, 4), dtype=torch.float32, device=base_mask.device)
        red_mask[:, :, :, 0] = 0.5  # Red channel
        red_mask[:, :, :, 3] = shifted_mask[:, :, :, 0] * 0.5  # Alpha from mask, semi-transparent
        
        # Overlay result mask in green
        green_mask = torch.zeros((B, H, W, 4), dtype=torch.float32, device=base_mask.device)
        green_mask[:, :, :, 1] = 1.0  # Green channel
        green_mask[:, :, :, 3] = result_mask[:, :, :, 0] * 0.7  # Alpha from mask, more visible
        
        # Composite all layers
        # First apply blue mask (base)
        alpha_blue = blue_mask[:, :, :, 3:4]
        debug_img = debug_img * (1 - alpha_blue) + blue_mask * alpha_blue
        
        # Then apply red mask (shifted)
        alpha_red = red_mask[:, :, :, 3:4]
        debug_img = debug_img * (1 - alpha_red) + red_mask * alpha_red
        
        # Finally apply green mask (result)
        alpha_green = green_mask[:, :, :, 3:4]
        debug_img = debug_img * (1 - alpha_green) + green_mask * alpha_green
        
        return debug_img 