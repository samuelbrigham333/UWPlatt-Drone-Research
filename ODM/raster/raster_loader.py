import rasterio
import numpy as np

class RasterLoader:

    def __init__(self, tif_path):
        self.tif_path = tif_path

    def load(self):
        with rasterio.open(self.tif_path) as src:

            bands = src.read().astype(np.float32)

        return bands