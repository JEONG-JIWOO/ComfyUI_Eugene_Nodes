import torch
import torch.nn.functional as F
import torchvision.transforms as T
import numpy as np


class LatentExpander:
    def __init__(self):
        self.gaussian_blur = T.GaussianBlur(kernel_size=15, sigma=(0.1, 10.0))

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "latent": ("LATENT",),
                "image_width": ("INT", {"default": 1024, "min": 64, "max": 8192}),
                "image_height": ("INT", {"default": 1024, "min": 64, "max": 8192}),
                "border_ratio": ("FLOAT", {"default": 0.05, "min": 0.01, "max": 0.2}),
                "blur_sigma": ("FLOAT", {"default": 2.0, "min": 0.1, "max": 10.0}),
                "blend_weight": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0})
            }
        }

    RETURN_TYPES = ("LATENT", "MASK")
    RETURN_NAMES = ("latent", "mask")
    FUNCTION = "expand"
    CATEGORY = "latent/expand"

    def create_base_a(self, samples, new_size):
        return F.interpolate(samples, size=new_size, mode='bilinear', align_corners=False)

    def create_border_mask(self, size, border_ratio):
        h, w = size
        border = int(min(h, w) * border_ratio)
        mask = torch.ones((1, 1, h, w))
        mask[:, :, border:-border, border:-border] = 0
        return mask

    def create_base_b(self, samples, new_size, original_size, border_ratio):
        border_mask = self.create_border_mask(original_size, border_ratio)
        border_latent = samples * border_mask.to(samples.device)
        resized = F.interpolate(border_latent, size=new_size, mode='bilinear', align_corners=False)
        return resized

    def create_blend_mask(self, new_size, original_size, feather=10):
        mask = torch.ones((1, 1, new_size[0], new_size[1]))
        y_start = (new_size[0] - original_size[0]) // 2
        x_start = (new_size[1] - original_size[1]) // 2

        mask[:, :, y_start:y_start + original_size[0],
        x_start:x_start + original_size[1]] = 0

        if feather > 0:
            self.gaussian_blur.sigma = (feather / 3, feather / 3)
            mask = self.gaussian_blur(mask)
        return mask

    def apply_gaussian_blur(self, samples, mask, sigma):
        self.gaussian_blur.sigma = (sigma, sigma)
        blurred = self.gaussian_blur(samples)
        return samples * (1 - mask) + blurred * mask

    def expand(self, latent, image_width, image_height, border_ratio=0.05,
               blur_sigma=2.0, blend_weight=0.5):
        device = latent["samples"].device
        samples = latent["samples"]
        batch_size, channels, orig_height, orig_width = samples.shape

        new_size = (image_height // 8, image_width // 8)
        original_size = (orig_height, orig_width)

        base_a = self.create_base_a(samples, new_size)
        base_b = self.create_base_b(samples, new_size, original_size, border_ratio)
        blended = base_a * (1 - blend_weight) + base_b * blend_weight

        blend_mask = self.create_blend_mask(new_size, original_size).to(device)

        y_start = (new_size[0] - orig_height) // 2
        x_start = (new_size[1] - orig_width) // 2
        blended[:, :, y_start:y_start + orig_height,
        x_start:x_start + orig_width] = samples

        result = self.apply_gaussian_blur(blended, blend_mask, blur_sigma)

        return ({"samples": result}, blend_mask.squeeze())