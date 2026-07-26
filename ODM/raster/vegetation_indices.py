"""
Vegettation index calculation module.

Computes common multispectral vegetation indices from
an orthomosaic loaded by RasterLoader

Each method returns a NumPy array representing a single
vegetation index raster.
"""

import numpy as np

class VegetationIndices:
    def __init__(self, bands):

        self.blue = bands[0].astype(np.float32)
        self.green = bands[1].astype(np.float32)
        self.red = bands[2].astype(np.float32)
        self.red_edge = bands[3].astype(np.float32)
        self.nir = bands[4].astype(np.float32)

#BASIC VEGETATION INDICES

    def ndvi(self):
        return (self.nir - self.red) / (
            self.nir + self.red + 1e-10
        )

    def gndvi(self):
        return (self.nir - self.green) /(
            self.nir + self.green + 1e-10
        )

    def ndre(self):
        return (self.nir - self.red_edge) / (
            self.nir + self.red_edge + 1e-10
        )

#CUSTOM INDICES

    def evenson(self):
        denominator = self.nir - self.red

        result = np.full(
            self.nir.shape,
            np.nan,
            dtype=np.float32
        )

        mask = np.abs(denominator) > 0.2

        result[mask] = (
            self.nir[mask] - self.red_edge[mask]
        ) / denominator[mask]

        return result

    def ci_red_dege(self):

        """
        Chlorophyll index - Red Edge
        """

        result = np.full(
            self.red_edge.shape,
            np.nan,
            dtype = np.float32
        )

        mask = self.red_edge > 0.2

        result[mask] = (
            self.nir[mask] - self.red_edge[mask]
        ) / self.red_edge[mask]

        return result

#Public Interface

    def calculate_all(self):
        """
        Calculate all vegetation index
        """

        return{
            "NDVI": self.ndvi(),
            "GNDVI": self.gndvi(),
            "NDRE": self.ndre(),
            "CI_RedEdge": self.ci_red_dege(),
            "Evenson": self.evenson(),
        }