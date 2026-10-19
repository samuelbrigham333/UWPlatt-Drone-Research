"""Calculate vegetation-index rasters from multispectral tiles.

Tiles use the application band order:
Red, Green, NIR, Red Edge, and optionally Alpha/mask.
"""

import numpy as np


class VegetationIndices:
    def __init__(self, bands):
        if bands is None:
            raise ValueError("Bands cannot be None.")

        bands = np.asarray(bands)
        if bands.ndim != 3:
            raise ValueError("Expected bands with shape (bands, height, width).")
        if bands.shape[0] < 4:
            raise ValueError(
                "Vegetation indices require Red, Green, NIR, and Red Edge bands."
            )

        self.bands = bands

    def ndvi(self):
        red = self.bands[0].astype(np.float32, copy=False)
        nir = self.bands[2].astype(np.float32, copy=False)
        return (nir - red) / (nir + red + 1e-10)

    def gndvi(self):
        green = self.bands[1].astype(np.float32, copy=False)
        nir = self.bands[2].astype(np.float32, copy=False)
        return (nir - green) / (nir + green + 1e-10)

    def ndre(self):
        red_edge = self.bands[3].astype(np.float32, copy=False)
        nir = self.bands[2].astype(np.float32, copy=False)
        return (nir - red_edge) / (nir + red_edge + 1e-10)

    def evenson(self):
        red = self.bands[0].astype(np.float32, copy=False)
        red_edge = self.bands[3].astype(np.float32, copy=False)
        nir = self.bands[2].astype(np.float32, copy=False)
        denominator = nir - red

        result = np.full(nir.shape, np.nan, dtype=np.float32)
        valid = np.isfinite(denominator) & (np.abs(denominator) > 0.2)
        result[valid] = (nir[valid] - red_edge[valid]) / denominator[valid]
        return result

    def ci_red_edge(self):
        red_edge = self.bands[3].astype(np.float32, copy=False)
        nir = self.bands[2].astype(np.float32, copy=False)

        result = np.full(red_edge.shape, np.nan, dtype=np.float32)
        valid = np.isfinite(red_edge) & (red_edge > 0.2) & np.isfinite(nir)
        result[valid] = (nir[valid] - red_edge[valid]) / red_edge[valid]
        return result

    def calculate_all(self):
        """Return all supported indices, in a stable order."""
        return {
            "NDVI": self.ndvi(),
            "GNDVI": self.gndvi(),
            "NDRE": self.ndre(),
            "CI_RedEdge": self.ci_red_edge(),
            "Evenson": self.evenson(),
        }
