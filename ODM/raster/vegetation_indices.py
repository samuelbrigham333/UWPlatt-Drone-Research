"""
Vegetation index calculation module

Implements common multipspectral vegetation indices used to assess
vegetation vigor, chlorophyll concentration, and plant health
Each index is computed from the raster bands loaded from
the orthomosaic and returned as a NumPy array for further analysis
"""

import numpy as np
from numpy._core._rational_tests import denominator


class VegetationIndices:
    def __init__(self, bands):
        self.bands = bands

    def ndvi(self):
        red = self.bands[2]
        nir = self.bands[4]

        return (nir - red) / (nir + red + 1e-10)    #this is the basic format you can follow for all future indices
                                                    #theoretically if you have the formula you can create a case for it


    def gndvi(self):
        green = self.bands[2]
        nir = self.bands[4]

        return (nir - green) / (nir + green + 1e-10)




    def ndre(self):

        red_edge = self.bands[3]
        nir = self.bands[4]

        return (nir - red_edge) / (nir + red_edge + 1e-10)


    def evenson(self):
        nir = self.bands[4].astype(float)
        red_edge = self.bands[3].astype(float)
        red = self.bands[2].astype(float)

        denominator = nir - red
        result = np.full(nir.shape, np.nan)

        mask = np.abs(denominator) > 0.2

        result[mask] = (
            (nir[mask] - red_edge[mask]) /
            denominator[mask]
        )

        return result


        #return (nir - red_edge) / (nir - red +1e-10) OG EVENSON EQUATION UNMASKED

    def ci_rededge(self):
        nir = self.bands[4].astype(float)
        red_edge = self.bands[3].astype(float)

        result = np.full(red_edge.shape, np.nan)

        mask = red_edge > 0.2

        result[mask] = (nir[mask] - red_edge[mask]) / red_edge[mask]

        return result

    #filter out anything that is 0 set the min to 0 ndvi > .2
    #greater than 0.2 run it


    def calculate_all(self):

        return {
            "NDVI": self.ndvi(),
            "GNDVI": self.gndvi(),
            "NDRE": self.ndre(),
            "CI_RedEdge": self.ci_rededge(),
            "EvensonIndices": self.evenson()  #name subject to change


        }


    #BANDS CHEAT SHEET
    #Blue: 0
    #Green: 1
    #Red: 2
    #Red Edge: 3
    #NIR: 4

    #past some threshold call the values 0?
    #suggestion from evenson^