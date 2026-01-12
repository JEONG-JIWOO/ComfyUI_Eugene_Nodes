import torch
import torch.nn.functional as F
import numpy as np
from .helper import InpaintingUtils, ImageProcessingHelper, MAX_RESOLUTION

def _process_image_inputs(image1, image2, image3, image4, image5):
    images = []
    if image1 is not None: images.append(image1)
    if image2 is not None: images.append(image2)
    if image3 is not None: images.append(image3)
    if image4 is not None: images.append(image4)
    if image5 is not None: images.append(image5)
    return images

def _process_mask_inputs(mask1, mask2, mask3, mask4, mask5):
    masks = []
    if mask1 is not None: masks.append(mask1)
    if mask2 is not None: masks.append(mask2)
    if mask3 is not None: masks.append(mask3)
    if mask4 is not None: masks.append(mask4)
    if mask5 is not None: masks.append(mask5)
    return masks

def _process_latent_inputs(latent1, latent2, latent3, latent4, latent5):
    latents = []
    if latent1 is not None: latents.append(latent1)
    if latent2 is not None: latents.append(latent2)
    if latent3 is not None: latents.append(latent3)
    if latent4 is not None: latents.append(latent4)
    if latent5 is not None: latents.append(latent5)
    return latents

def encode_batch_images(vae, images):
    # Optimized VAE encoding
    pixel_samples = [image for image in images]
    pixel_samples = torch.cat(pixel_samples, dim=0)
    
    # Move to same device and dtype as VAE to avoid overhead if possible
    # VAE usually expects inputs in [-1, 1] range? No, ComfyUI VAE usually takes [0, 1] or manages it.
    # ComfyUI standard VAE encode takes [B, H, W, 3]
    
    pixels = pixel_samples[:,:,:,:3]
    
    # Optimization: Use no_grad and ensure inputs are continuous
    with torch.no_grad():
        # .contiguous() might help memory layout
        pixels = pixels.contiguous()
        latent = vae.encode(pixels)
    
    return latent

class LatentExpander:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "latent": ("LATENT",),
                "expand_pixels": ("INT", {"default": 128, "min": 0, "max": MAX_RESOLUTION, "step": 8}),
                "tapered_corners": ("BOOLEAN", {"default": True}),
                "mask_blur": ("INT", {"default": 8, "min": 0, "max": 64, "step": 1}),
            },
        }

    RETURN_TYPES = ("LATENT", "MASK")
    FUNCTION = "expand_latent"
    CATEGORY = "latent"

    def expand_latent(self, latent, expand_pixels, tapered_corners, mask_blur):
        samples = latent['samples']
        device = samples.device
        b, c, h, w = samples.shape
        
        # Expand pixels in latent space (divide by 8)
        expand_latent_pixels = expand_pixels // 8
        
        # Calculate new size
        new_h = h + expand_latent_pixels * 2
        new_w = w + expand_latent_pixels * 2
        
        # Create new canvas
        new_samples = torch.zeros((b, c, new_h, new_w), dtype=samples.dtype, device=device)
        
        # Place original latent in center
        new_samples[:, :, expand_latent_pixels:expand_latent_pixels+h, expand_latent_pixels:expand_latent_pixels+w] = samples
        
        # Create mask
        # 1.0 for original area, 0.0 for expanded area (or vice versa depending on inpainting needs)
        # Usually for outpainting, we want the expanded area to be masked (1.0) and original area unmasked (0.0)
        # But ComfyUI inpainting mask: 1.0 means "replace this", 0.0 means "keep this".
        # So we want expanded area = 1.0
        
        mask_h = new_h * 8
        mask_w = new_w * 8
        mask = torch.ones((mask_h, mask_w), dtype=torch.float32, device="cpu")
        
        # Original area = 0.0
        orig_y = expand_latent_pixels * 8
        orig_x = expand_latent_pixels * 8
        orig_h_px = h * 8
        orig_w_px = w * 8
        
        mask[orig_y:orig_y+orig_h_px, orig_x:orig_x+orig_w_px] = 0.0
        
        # Apply blur/feathering to the boundary
        if mask_blur > 0:
            # We can use the helper's create_feather_mask logic or just blur
            # Simple gaussian blur on the mask
             mask = mask.unsqueeze(0).unsqueeze(0) # B, C, H, W
             # Use helper if available, or just torchvision
             # Re-implementing simplified blur here as helper.create_feather_mask creates a new mask
             import torchvision.transforms as T
             blur = T.GaussianBlur(kernel_size=mask_blur*2+1, sigma=mask_blur/3)
             mask = blur(mask).squeeze()

        # Output mask should be [B, H, W]?? No, ComfyUI usually expects [H, W] or [1, H, W] for single mask
        # But this node prob returns batch if input is batch? 
        # Latent mask is usually stored in 'noise_mask' of LATENT dict
        
        # The node description implies returning a MASK output separately too
        
        output_latent = {
            "samples": new_samples,
            # 'noise_mask': mask.to(device).unsqueeze(0) # optional?
        }
        
        # Add noise mask to latent
        # Ensure mask matches latent batch size
        mask_tensor = mask.to(device)
        if mask_tensor.dim() == 2:
            mask_tensor = mask_tensor.unsqueeze(0)
            
        # Optimization: Expand mask to batch size
        if b > 1:
            mask_tensor = mask_tensor.repeat(b, 1, 1)
            
        output_latent['noise_mask'] = mask_tensor

        return (output_latent, mask_tensor)


class SetMultipleLatentNoiseMasks:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "latent1": ("LATENT",),
                "mask1": ("MASK",),
            },
            "optional": {
                "latent2": ("LATENT",), "mask2": ("MASK",),
                "latent3": ("LATENT",), "mask3": ("MASK",),
                "latent4": ("LATENT",), "mask4": ("MASK",),
                "latent5": ("LATENT",), "mask5": ("MASK",),
            }
        }

    RETURN_TYPES = ("LATENT",)
    FUNCTION = "set_masks"
    CATEGORY = "latent"

    def set_masks(self, latent1, mask1, latent2=None, mask2=None, latent3=None, mask3=None, 
                  latent4=None, mask4=None, latent5=None, mask5=None):
        latents = _process_latent_inputs(latent1, latent2, latent3, latent4, latent5)
        masks = _process_mask_inputs(mask1, mask2, mask3, mask4, mask5)

        if len(latents) != len(masks):
            # Try to match or broadcast? For now, strict matching or matching up to count
            count = min(len(latents), len(masks))
            latents = latents[:count]
            masks = masks[:count]

        output_samples_list = []
        output_masks_list = []

        for latent, mask in zip(latents, masks):
            samples = latent['samples']
            
            # Prepare mask
            if mask.dim() == 2:
                mask = mask.unsqueeze(0)
            
            # Resize mask to samples shape if needed (latent space)
            # Latent mask (noise_mask) should be [B, 1, H*8, W*8] usually? 
            # Or [B, 1, H, W]?
            # ComfyUI noise_mask is usually [B, 1, H, W] (latent dimensions) OR [B, 1, H*8, W*8] (pixel dimensions)?
            # Checking standard nodes: VAEEncodeForInpaint uses pixel level mask, resizes to latent.
            # Here we assume input mask is pixel level.
            
            # Check mask shape
            b, c, h, w = samples.shape
            
            # We need to resize input mask to latent dimensions [B, 1, H, W]
            mask_resized = F.interpolate(mask.unsqueeze(1), size=(h, w), mode="nearest")
            
            output_samples_list.append(samples)
            output_masks_list.append(mask_resized)

        # Concatenate
        if not output_samples_list:
             return ({"samples": torch.empty(0)},) # Error handling?

        output_samples = torch.cat(output_samples_list, dim=0)
        output_masks = torch.cat(output_masks_list, dim=0)

        output = {
            "samples": output_samples,
            "noise_mask": output_masks
        }
        return (output,)

class SetMultipleImageNoiseMasks:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "vae": ("VAE",),
                "image1": ("IMAGE",),
                "mask1": ("MASK",),
            },
            "optional": {
                "image2": ("IMAGE",), "mask2": ("MASK",),
                "image3": ("IMAGE",), "mask3": ("MASK",),
                "image4": ("IMAGE",), "mask4": ("MASK",),
                "image5": ("IMAGE",), "mask5": ("MASK",),
            }
        }

    RETURN_TYPES = ("LATENT",)
    FUNCTION = "set_masks"
    CATEGORY = "latent"

    def set_masks(self, vae, image1, mask1, image2=None, mask2=None, image3=None, mask3=None,
                  image4=None, mask4=None, image5=None, mask5=None):
        images = _process_image_inputs(image1, image2, image3, image4, image5)
        masks = _process_mask_inputs(mask1, mask2, mask3, mask4, mask5)
        
        count = min(len(images), len(masks))
        images = images[:count]
        masks = masks[:count]

        # Use helper for encoding
        samples = encode_batch_images(vae, images)
        
        # Prepare masks
        # Masks are from images, [B, H_img, W_img]
        # Need to resize to latent dims [B, 1, H_lat, W_lat]
        b, c, h, w = samples.shape
        
        output_masks_list = []
        for i, mask in enumerate(masks):
            # Input mask might correspond to input image batch
            # If image i has B=1, mask i should have B=1
            curr_img_b = images[i].shape[0]
            
            if mask.dim() == 2:
                mask = mask.unsqueeze(0)
            
            if mask.shape[0] != curr_img_b:
                # Broadcasting or error?
                # Assume standard 1-to-1 or mask broadcasting
                if mask.shape[0] == 1:
                    mask = mask.repeat(curr_img_b, 1, 1)
            
            mask_resized = F.interpolate(mask.unsqueeze(1), size=(h, w), mode="nearest") # [B, 1, H, W]
            output_masks_list.append(mask_resized)

        output_masks = torch.cat(output_masks_list, dim=0)
        if output_masks.shape[0] != samples.shape[0]:
            # This can happen if images had different batch sizes logic vs masks
            # For simplicity, we assume they align or we truncate
            pass

        return ({"samples": samples, "noise_mask": output_masks},)


class CropMultipleImagesByMasks:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "vae": ("VAE",),
                "padding_ratio": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01}),
                "resize_scale": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1}),
                "max_size": ("INT", {"default": MAX_RESOLUTION, "min": 64, "max": MAX_RESOLUTION, "step": 64}),
                "image1": ("IMAGE",), "mask1": ("MASK",),
            },
            "optional": {
                "image2": ("IMAGE",), "mask2": ("MASK",),
                "image3": ("IMAGE",), "mask3": ("MASK",),
                "image4": ("IMAGE",), "mask4": ("MASK",),
                "image5": ("IMAGE",), "mask5": ("MASK",),
            }
        }
        
    RETURN_TYPES = ("LATENT", "IMAGE", "MASK", "INT", "INT", "INT", "INT", "INT", "INT")
    RETURN_NAMES = ("latent", "resized_images", "resized_masks", "x", "y", "width", "height", "target_w", "target_h")
    FUNCTION = "process"
    CATEGORY = "latent"

    def process(self, vae, padding_ratio, resize_scale, max_size,
                image1, mask1, image2=None, mask2=None, image3=None,
                mask3=None, image4=None, mask4=None, image5=None, mask5=None):
        
        images = _process_image_inputs(image1, image2, image3, image4, image5)
        masks = _process_mask_inputs(mask1, mask2, mask3, mask4, mask5)
        
        # Ensure count matches
        count = min(len(images), len(masks))
        images = images[:count]
        masks = masks[:count]

        if count == 0:
             raise ValueError("No input images/masks provided")

        # Use helper for core logic
        (resized_images_list, resized_masks_latent_list,
         x, y, width, height, target_w, target_h) = InpaintingUtils.crop_and_resize_images_by_masks(
             images, masks, padding_ratio, resize_scale, max_size
         )
         
        # Encode
        latent = encode_batch_images(vae, resized_images_list)
        
        # Prepare outputs
        if len(resized_images_list) > 1:
            resized_images_out = torch.cat(resized_images_list, dim=0)
        else:
            resized_images_out = resized_images_list[0]
            
        # Combine masks for latent (noise_mask)
        # Helper returned list of [1, H_lat, W_lat] (squeezed channel?)
        # Let's check helper: returns list of [1, H_lat, W_lat] (via squeeze(1)?)
        # Step 44 code: resized_msk_latent is squeezed: .squeeze(1) -> [1, H, W] or [B, H, W]
        
        # We need [B, 1, H, W] for noise_mask
        output_masks_list = []
        for m in resized_masks_latent_list:
            if m.dim() == 2:
                m = m.unsqueeze(0) # [1, H, W]
            output_masks_list.append(m.unsqueeze(1)) # [1, 1, H, W]
            
        output_noise_mask = torch.cat(output_masks_list, dim=0)
        latent['noise_mask'] = output_noise_mask
        
        # MASK output (resized masks combined)
        # Just concat the masks
        if len(resized_masks_latent_list) > 1:
             # These are latent sized masks. Node typically returns pixel sized masks?
             # User expectation: resized_masks usually pixel sized.
             # Helper returns latent sized masks as 2nd return.
             # We might need to resize back or use the cropped_msk from helper (not returned).
             # Efficient way: Interpolate latent mask back to pixel size (x8)
             resized_masks_out = F.interpolate(output_noise_mask, scale_factor=8, mode='nearest').squeeze(1)
        else:
             resized_masks_out = F.interpolate(output_noise_mask, scale_factor=8, mode='nearest').squeeze(1)

        return (latent, resized_images_out, resized_masks_out, x, y, width, height, target_w, target_h)


class MergeInpaintedLatent:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "vae": ("VAE",),
                "original_images": ("IMAGE",),
                "inpainted_latent": ("LATENT",),
                "x": ("INT", {"default": 0}),
                "y": ("INT", {"default": 0}),
                "width": ("INT", {"default": 0}), # Original crop width
                "height": ("INT", {"default": 0}), # Original crop height
                "feather": ("INT", {"default": 8, "min": 0, "max": 64, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "merge"
    CATEGORY = "latent"

    def merge(self, vae, original_images, inpainted_latent, x, y, width, height, feather):
        # Decode inpainted latent
        samples = inpainted_latent['samples']
        inpainted_images = vae.decode(samples) # [B, H, W, 3]
        
        # Resize decoded image back to original crop size (width, height)
        # The latent might have been resized (target_w, target_h)
        # We need to resize it to match the original crop area size
        
        # inpainted_images is [B, target_h, target_w, 3]
        target_h, target_w = inpainted_images.shape[1:3]
        
        # Resize to original crop size
        if target_w != width or target_h != height:
             inpainted_images = inpainted_images.permute(0, 3, 1, 2)
             inpainted_images = F.interpolate(inpainted_images, size=(height, width), mode="bilinear", align_corners=False)
             inpainted_images = inpainted_images.permute(0, 2, 3, 1)
             
        # Now paste back
        merged_images_list = []
        
        # Helper for feathering
        feather_mask = InpaintingUtils.create_feather_mask((height, width), feather)
        feather_mask = feather_mask.to(original_images.device)
        if feather_mask.dim() == 2:
            feather_mask = feather_mask.unsqueeze(0).unsqueeze(-1) # [1, H, W, 1]
        elif feather_mask.dim() == 3:
            feather_mask = feather_mask.unsqueeze(-1)

        for i, orig_img in enumerate(original_images):
            # If inpainted is batch, use i-th, else use 0-th?
            idx = i if i < len(inpainted_images) else 0
            inpaint_img = inpainted_images[idx]
            
            # Composite
            # orig_img is [H_org, W_org, 3]
            # insert inpaint_img at x, y
            
            result = orig_img.clone()
            
            # Ensure crop fits (clamp)
            y_start = max(0, y)
            x_start = max(0, x)
            y_end = min(orig_img.shape[0], y + height)
            x_end = min(orig_img.shape[1], x + width)
            
            # Adjust source crop if clamped
            src_y_start = y_start - y
            src_x_start = x_start - x
            src_y_end = src_y_start + (y_end - y_start)
            src_x_end = src_x_start + (x_end - x_start)
            
            if src_y_end > inpaint_img.shape[0] or src_x_end > inpaint_img.shape[1]:
                # Should not happen if width/height are consistent
                pass

            src_crop = inpaint_img[src_y_start:src_y_end, src_x_start:src_x_end, :]
            dest_crop = result[y_start:y_end, x_start:x_end, :]
            mask_crop = feather_mask[0, src_y_start:src_y_end, src_x_start:src_x_end, :]
            
            # Blending
            composed = dest_crop * (1 - mask_crop) + src_crop * mask_crop
            result[y_start:y_end, x_start:x_end, :] = composed
            
            merged_images_list.append(result)
            
        return (torch.stack(merged_images_list, dim=0),)