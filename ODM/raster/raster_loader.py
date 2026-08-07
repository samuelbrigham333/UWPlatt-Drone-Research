"""
Raster loading module

Provides functionality for loading multispectral orthomosaic
TIFF images using rasterio. Supports loading either the entire image
or a specified window for tiled processing
"""

import numpy as np
import rasterio

class RasterLoader:
    def __init__(self, tif_path):
        self.tif_path = tif_path

    def load(self, band_indexes=None):
        with rasterio.open(self.tif_path) as src:

            if band_indexes is None:
                band_indexes = list(range(1, src.count + 1))

            bands = src.read(band_indexes).astype(np.float32)

        return bands

    def load_window(self, window, band_indexes=None):
        with rasterio.open(self.tif_path) as src:

            if band_indexes is None:
                band_indexes = list(range(1, src.count + 1))

            bands = src.read(
                band_indexes,
                window = window
            ).astype(np.float32)

        return bands

    def get_metadata(self):

        with rasterio.open(self.tif_path) as src:

            return{
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "crs": src.crs,
                "transform": src.transform
            }

    def get_metadate(self):

        with rasterio.open(self.tif_path) as src:

            return{
                "width": src.width,
                "height": src.height,
                "pixel_width": src.transform.a,
                "pixel_height": abs(src.transform.e),
                "crs": src.crs,
            }