import numpy as np

class VegetationIndices:
    def __init__(self, bands):
        self.bands = bands

    def ndvi(self):
        red = self.bands