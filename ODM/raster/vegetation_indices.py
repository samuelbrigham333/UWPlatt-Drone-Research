import numpy as np

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
        nir = self.bands[4]
        red_edge = self.bands[3]
        red = self.bands[2]

        return (nir - red_edge) / (nir - red +1e-10)

    def ci_rededge(self):
        nir = self.bands[4]
        red_edge = self.bands [3]

        return (nir / (red_edge + 1e-10)) -1


    def calculate_all(self):

        return {
            "NDVI": self.ndvi(),
            "GNDVI": self.gndvi(),
            "NDRE": self.ndre(),
            "CI_RedEdge": self.ci_rededge(),
            "EvensonIndices": self.evenson()        #name subject to change


        }


    #BANDS CHEAT SHEET
    #Blue: 0
    #Green: 1
    #Red: 2
    #Red Edge: 3
    #NIR: 4