"""
Vegetation index calculation module.

Computes common multispectral vegetation indices from
an orthomosaic loaded by RasterLoader

Each method returns a NumPy array representing a single
vegetation index raster.
"""

import numpy as np



class VegetationIndices:
    def __init__(self, bands):
        self.bands = bands


#BASIC VEGETATION INDICES

    def ndvi(self):
        red = self.bands[2].astype(np.float32)
        nir = self.bands[4].astype(np.float32)

        result = (nir - red) / (nir + red + 1e-10)

        del red
        del nir

        return result

    def gndvi(self):
        green = self.bands[1].astype(np.float32)
        nir = self.bands[4].astype(np.float32)

        result = (nir - green) / (
            nir + green + 1e-10
        )

        del green
        del nir

        return result



    def ndre(self):
        red_edge = self.bands[3].astype(np.float32)
        nir = self.bands[4].astype(np.float32)

        result = (nir - red_edge) / (
            nir + red_edge + 1e-10
        )

        del red_edge
        del nir

        return result
#CUSTOM INDICES

    def evenson(self):
        red = self.bands[2].astype(np.float32)
        red_edge = self.bands[3].astype(np.float32)
        nir = self.bands[4].astype(np.float32)

        denominator = nir - red

        result = np.full(
            nir.shape,
            np.nan,
            dtype=np.float32
        )

        mask = np.abs(denominator) > 0.2

        result[mask] = (
                               nir[mask] - red_edge[mask]
                       ) / denominator[mask]

        del red
        del red_edge
        del nir
        del denominator
        del mask

        return result


    def ci_red_edge(self):
       red_edge = self.bands[3].astype(np.float32)
       nir = self.bands[4].astype(np.float32)

       result = np.full(
           red_edge.shape,
           np.nan,
           dtype=np.float32
       )

       mask = red_edge > 0.2

       result[mask] = (
           nir[mask] - red_edge[mask]
       ) / red_edge[mask]

       del red_edge
       del nir

       return result


