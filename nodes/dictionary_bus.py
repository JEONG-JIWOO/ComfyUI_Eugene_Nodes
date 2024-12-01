"""
Dictionary Bus Nodes
Utility nodes for managing dictionary and model components as a single bundle
"""

class DictBus:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "dict": ("DICT",),
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
            },
            "optional": {
                "image": ("IMAGE",),
                "latent": ("LATENT",),
                "list": ("LIST",),
            }
        }

    RETURN_TYPES = ("DICT_BUS",)
    FUNCTION = "create_bus"
    CATEGORY = "dictionary/bus"

    def create_bus(self, dict, model, clip, vae, image=None, latent=None, list=None):
        return ([dict, model, clip, vae, image, latent, list],)


class DictBusUnpack:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "dict_bus": ("DICT_BUS",),
            }
        }

    RETURN_TYPES = ("DICT_BUS", "DICT", "MODEL", "CLIP", "VAE", "IMAGE", "LATENT", "LIST")
    RETURN_NAMES = ("bus", "dict", "model", "clip", "vae", "image", "latent", "list")
    FUNCTION = "unpack_bus"
    CATEGORY = "dictionary/bus"

    def unpack_bus(self, dict_bus):
        dict_, model, clip, vae, image, latent, list_ = dict_bus
        return (dict_bus, dict_, model, clip, vae, image, latent, list_)


class DictBusEdit:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "dict_bus": ("DICT_BUS",),
            },
            "optional": {
                "dict": ("DICT",),
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "vae": ("VAE",),
                "image": ("IMAGE",),
                "latent": ("LATENT",),
                "list": ("LIST",),
            }
        }

    RETURN_TYPES = ("DICT_BUS",)
    FUNCTION = "edit_bus"
    CATEGORY = "dictionary/bus"

    def edit_bus(self, dict_bus, dict=None, model=None, clip=None, vae=None, image=None, latent=None, list=None):
        orig_dict, orig_model, orig_clip, orig_vae, orig_image, orig_latent, orig_list = dict_bus

        new_dict = dict if dict is not None else orig_dict
        new_model = model if model is not None else orig_model
        new_clip = clip if clip is not None else orig_clip
        new_vae = vae if vae is not None else orig_vae
        new_image = image if image is not None else orig_image
        new_latent = latent if latent is not None else orig_latent
        new_list = list if list is not None else orig_list

        new_bus = (new_dict, new_model, new_clip, new_vae, new_image, new_latent, new_list)
        return (new_bus,)