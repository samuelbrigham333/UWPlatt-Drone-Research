import numpy as np

class VegetationIndices:
    def __init__(self, bands):
        self.bands = bands

    def ndvi(self):
        red = self.bands[2]
        nir = self.bands[4]

        return (nir - red) / (nir + red + 1e-10)    #this is the basic format you can follow for all future indices
                                                    #theoretically if you have the formula you can create a case for it
    def ndre(self):

        red_edge = self.bands[3]
        nir = self.bands[4]

        return (nir - red_edge) / (nir + red_edge + 1e-10)

    def calculate_all(self):

        return {
            "NDVI": self.ndvi(),
            "NDRE": self.ndre()
        }


    #BANDS CHEAT SHEET
    #Blue: 0
    #Green: 1
    #Red: 2
    #Red Edge: 3
    #NIR: 4