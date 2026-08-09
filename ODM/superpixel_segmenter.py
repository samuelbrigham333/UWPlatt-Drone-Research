
"""
Superpixel Segmenter

Processes an orthomosaic tile-by-tile using SLIC
to reduce memory usage.
"""

from pathlib import Path

import numpy as np
import rasterio

from skimage.segmentation import slic


class SuperpixelSegmenter:

    def __init__(
        self,
        image_path,
        num_segments=500,
        compactness=10,
        sigma=1,
    ):

        self.image_path = Path(image_path)

        self.num_segments = num_segments
        self.compactness = compactness
        self.sigma = sigma

    # PUBLIC INTERFACE

    def run(self, tile):

        image = self._load_tile(tile)

        labels = self._generate_superpixels(image)

        return labels

    # LOAD TILE

    def _load_tile(self, tile):
        """
        Load only the requested tile from the orthomosaic.
        """

        with rasterio.open(self.image_path) as src:

            window = rasterio.windows.Window(
                col_off=tile["x"],
                row_off=tile["y"],
                width=tile["width"],
                height=tile["height"],
            )

            bands = src.read(
                indexes=[1, 2, 3],
                window=window
            ).astype(np.float32)


        image = np.moveaxis(
            bands,
            0,
            -1
        )

        # NORMALIZE IMAGE

        image -= image.min()

        max_value = image.max()

        if max_value > 0:
            image /= max_value

        return image

    # GENERATE SUPERPIXELS

    def _generate_superpixels(self, image):
        """
        Run SLIC on a single tile.
        """

        return slic(
            image,
            n_segments=self.num_segments,
            compactness=self.compactness,
            sigma=self.sigma,
            start_label=1,
            channel_axis=-1
        )
