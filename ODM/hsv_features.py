import cv2
import numpy as np


class HSVFeatures:

    def __init__(self, bands):
        self.bands = bands

    def calculate(self):

        rgb = self._create_rgb()

        hsv = cv2.cvtColor(
            rgb,
            cv2.COLOR_RGB2HSV
        )

        return {
            "Hue": hsv[:, :, 0].astype(np.float32),
            "Saturation": hsv[:, :, 1].astype(np.float32),
            "Value": hsv[:, :, 2].astype(np.float32),
        }

    def _create_rgb(self):

        red = self.bands[0]
        green = self.bands[1]
        blue = self.bands[2]

        height, width = red.shape

        rgb = np.empty((height, width, 3), dtype=np.uint8)

        rgb[:, :, 0] = np.clip(red,   0, 255).astype(np.uint8)
        rgb[:, :, 1] = np.clip(green, 0, 255).astype(np.uint8)
        rgb[:, :, 2] = np.clip(blue,  0, 255).astype(np.uint8)

        return rgb