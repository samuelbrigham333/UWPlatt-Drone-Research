"""Process an individual multispectral tile.

The vegetation index math remains in VegetationIndices, and the SLIC
implementation remains in SuperpixelSegmenter. This class coordinates them.
"""

from ODM.raster.vegetation_indices import VegetationIndices
from ODM.superpixel_segmenter import SuperpixelSegmenter


class TileProcessor:
    def __init__(self, compactness, sigma):
        self.compactness = compactness
        self.sigma = sigma

    def process(self, tile, target_segments):
        print("\n[1/3] Calculating vegetation indices...")

        vegetation = VegetationIndices(tile)
        index_rasters = vegetation.calculate_all()

        for name in index_rasters:
            print(f"      {name:<12} ✓")

        print("\n[2/3] Generating superpixels from vegetation indices...")

        segmenter = SuperpixelSegmenter(
            num_segments=target_segments,
            compactness=self.compactness,
            sigma=self.sigma,
        )
        labels = segmenter.run(tile, index_rasters=index_rasters)

        return labels, index_rasters
