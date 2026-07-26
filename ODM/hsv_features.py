"""
HSV Feature Extraction

Converts RGB raster bands into HSV feature rasters
"""

import cv2
import numpy as np

class HSVFeatures:
    def __init__(self, bands):

        self.bands = bands

    def calculate(self):
        rgb = self._create_rgb()

        shv = cv2.cvtColor(
            rgb,
            cv2.COLOR_RGB2HSB
        )

        return {
            "Hue": hsv [:, : , 0].astype(np.flaot32),

            "Saturation": hsv[:, : , 1].astype(np.float32),

            "Value": hsv[:, : , 2].astype(np.float32),
        }

    def _create_rgb(self):
        """
        Convert raster bands to RGB image
        :return:
        """

        red = self.bands[0]
        green = self.bands[1]
        blue = self.bands[2]

        rgb = np.dstack((red, green, blue))

        rgb = np.clip(rgb, 0, 255)

        return rgb.astype(np.uint8)
