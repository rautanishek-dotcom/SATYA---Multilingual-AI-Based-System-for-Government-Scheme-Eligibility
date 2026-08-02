import random

SUPPORTED_AUGMENTATIONS = [
    "rotate",
    "brightness",
    "contrast",
    "gaussian_noise",
    "crop",
    "blur",
    "perspective",
]


def apply_augmentation(image, augmentation_name, strength=0.5):
    if augmentation_name == "rotate":
        return image
    if augmentation_name == "brightness":
        return image
    if augmentation_name == "contrast":
        return image
    if augmentation_name == "gaussian_noise":
        return image
    if augmentation_name == "crop":
        return image
    if augmentation_name == "blur":
        return image
    if augmentation_name == "perspective":
        return image
    return image
