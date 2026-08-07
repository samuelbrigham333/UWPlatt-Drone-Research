"""
Superpixel Segmenter

Uses SLIC to divide an image
into perceptually similar regions called superpixels.
"""

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from ODM.raster.raster_loader import RasterLoader

from skimage.segmentation import slic, mark_boundaries

class SuperpixelSegmenter:

    def __init__(
            self,
            image_path,
            num_segments = 500,
            compactness = 10,
            sigma = 1
                ):

        self.image_path = Path(image_path)

        self.num_segments = num_segments
        self.compactness = compactness
        self.sigma = sigma

        self.image = None
        self.labels = None

    def run(self):
        self._load_image()
        self._generate_superpixels()
        return self.labels

    def _load_image(self):
        loader = RasterLoader(self.image_path)
        bands = loader.load(band_indexes = [1, 2, 3])

        if bands.shape[0] < 3:
            raise ValueError(
                "Orthomosaic must contain at least three bands."
            )

        self.image = np.moveaxis(bands[:3], 0, -1)

        self.image -= self.image.min()

        max_value = self.image.max()
        if max_value > 0:
            self.image /= max_value

    def _generate_superpixels(self):

        self.labels = slic(
            self.image,
            n_segments = self.num_segments,
            compactness = self.compactness,
            sigma = self.sigma,
            start_label = 1
        )

    def get_labels(self):
        return self.labels

    def get_region_ids(self):
        self._require_labels()
        return np.unique(self.labels)

    def get_region_mask(self, region_ids):

        self._require_labels()

        return self.labels == region_ids

    def get_number_of_regions(self):

        self._require_labels()

        return len(self.get_region_ids())

    def visualize(self):

        self._require_labels()

        boundary_image = mark_boundaries(
            self.image,
            self.labels,
        )

        plt.figure(figsize=(10, 10))
        plt.imshow(boundary_image)
        plt.axis('off')
        plt.show()

    def save_visualization(self, output_path):

        self._require_labels()

        boundary_image = mark_boundaries(
            self.image,
            self.labels,
        )

        plt.imsave(output_path, boundary_image)

    def save_labels(self, output_path):
        self._require_labels()

        np.save(output_path, self.labels)

    def _require_labels(self):
        if self.labels is None:
            raise RuntimeError(
                "Run segmenter.run() before accessing results." #this should never occur?
            )