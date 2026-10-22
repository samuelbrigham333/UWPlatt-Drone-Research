
"""
Calculate vegetation indices from multispectral raster tiles.

Expected band order:
    0 - Red
    1 - Green
    2 - NIR
    3 - Red Edge
    4 - Alpha / mask

Each vegetation index is calculated per pixel.
"""

import numpy as np


class VegetationIndices:
    def __init__(self, bands):
        if bands.ndim != 3:
            raise ValueError(
                "Expected raster shape (bands, height, width)."
            )

        if bands.shape[0] < 5:
            raise ValueError(
                "At least five bands are required."
            )

        self.red = bands[0].astype(np.float32)
        self.green = bands[1].astype(np.float32)
        self.nir = bands[2].astype(np.float32)
        self.red_edge = bands[3].astype(np.float32)
        self.alpha = bands[4]

        self.valid_mask = (
            (self.alpha > 0)
            & np.isfinite(self.red)
            & np.isfinite(self.green)
            & np.isfinite(self.nir)
            & np.isfinite(self.red_edge)
        )

    def _safe_divide(self, numerator, denominator, threshold=0.0):
        result = np.full(
            numerator.shape,
            np.nan,
            dtype=np.float32,
        )

        valid = (
            self.valid_mask
            & np.isfinite(numerator)
            & np.isfinite(denominator)
            & (np.abs(denominator) > threshold)
        )

        np.divide(
            numerator,
            denominator,
            out=result,
            where=valid,
        )

        return result

    def ndvi(self):
        return self._safe_divide(
            self.nir - self.red,
            self.nir + self.red,
        )

    def gndvi(self):
        return self._safe_divide(
            self.nir - self.green,
            self.nir + self.green,
        )

    def ndre(self):
        return self._safe_divide(
            self.nir - self.red_edge,
            self.nir + self.red_edge,
        )

    def evenson(self):
        return self._safe_divide(
            self.nir - self.red_edge,
            self.nir - self.red,
            threshold=0.2,
        )

    def ci_red_edge(self):
        return self._safe_divide(
            self.nir - self.red_edge,
            self.red_edge,
            threshold=0.2,
        )

    def calculate_all(self):
        return {
            "NDVI": self.ndvi(),
            "GNDVI": self.gndvi(),
            "NDRE": self.ndre(),
            "CI_RedEdge": self.ci_red_edge(),
            "Evenson": self.evenson(),
        }
