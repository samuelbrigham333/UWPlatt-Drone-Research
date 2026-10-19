"""
Superpixel segmentation module.

Runs SLIC on an already-loaded raster tile.

The segmenter does NOT reopen the TIFF. The application
loads each tile once and passes the tile data here.

Expected tile shape:

    (bands, height, width)

For multispectral imagery:

    Band 0 = Red
    Band 1 = Green
    Band 2 = NIR
    Band 3 = Red Edge
    Band 4 = Alpha / mask (optional index input)
"""

import numpy as np
from skimage.segmentation import slic

from ODM.vegetation_indices import VegetationIndices


class SuperpixelSegmenter:
    def __init__(self, num_segments, compactness=10.0, sigma=1.0):

        if num_segments <= 0:
            raise ValueError("num_segments must be greater than zero.")

        if compactness <= 0:
            raise ValueError("compactness must be greater than zero.")

        if sigma < 0:
            raise ValueError("sigma cannot be negative.")

        self.num_segments = int(num_segments)

        self.compactness = float(compactness)

        self.sigma = float(sigma)

    # ------------------------------------------------------
    # RUN SLIC
    # ------------------------------------------------------

    def run(self, tile, index_rasters=None):

        if tile is None:
            raise ValueError("Tile cannot be None.")

        if tile.ndim != 3:
            raise ValueError(
                "Expected tile with shape "
                "(bands, height, width). "
                f"Received {tile.shape}"
            )

        _bands, height, width = tile.shape

        if height == 0 or width == 0:
            return None

        # --------------------------------------------------
        # PREPARE VEGETATION-INDEX IMAGE FOR SLIC
        # --------------------------------------------------

        if index_rasters is None:
            index_rasters = VegetationIndices(tile).calculate_all()

        if not index_rasters:
            raise ValueError("At least one vegetation-index raster is required.")

        index_names = tuple(index_rasters)
        index_arrays = []
        for name in index_names:
            index_array = np.asarray(index_rasters[name], dtype=np.float32)
            if index_array.shape != (height, width):
                raise ValueError(
                    f"Index '{name}' has shape {index_array.shape}; "
                    f"expected {(height, width)}."
                )
            index_arrays.append(index_array)

        index_image = np.stack(index_arrays, axis=-1)

        # The four reflectance bands are required to calculate the indices.
        valid_mask = np.all(np.isfinite(tile[:4]), axis=0)

        # The fifth band is the orthomosaic alpha/mask band when present.
        if _bands >= 5:
            valid_mask &= np.isfinite(tile[4]) & (tile[4] > 0)

        if not np.any(valid_mask):
            print("    Tile contains no data.")

            return None

        # --------------------------------------------------
        # PREPARE IMAGE FOR SLIC
        # --------------------------------------------------

        image = self._normalize_channels(index_image, valid_mask)

        # --------------------------------------------------
        # ACTUAL NUMBER OF SEGMENTS
        # --------------------------------------------------

        pixel_count = height * width

        requested_segments = min(self.num_segments, pixel_count)

        print(f"    SLIC segments: {requested_segments}")

        # --------------------------------------------------
        # SLIC
        # --------------------------------------------------

        labels = slic(
            image,
            n_segments=requested_segments,
            compactness=self.compactness,
            sigma=self.sigma,
            start_label=0,
            channel_axis=-1,
            mask=valid_mask,
        )

        # --------------------------------------------------
        # REMOVE INVALID PIXELS
        # --------------------------------------------------

        labels = labels.astype(np.int32, copy=False)

        labels[~valid_mask] = -1

        # --------------------------------------------------
        # REPORT
        # --------------------------------------------------

        valid_labels = labels[labels >= 0]

        if valid_labels.size == 0:
            print("    SLIC produced no valid regions.")

            return None

        unique_regions = np.unique(valid_labels)

        print(f"Generated {len(unique_regions)} valid superpixels.")

        return labels

    # ------------------------------------------------------
    # NORMALIZE CHANNELS
    # ------------------------------------------------------

    @staticmethod
    def _normalize_channels(image, valid_mask):

        normalized = np.zeros_like(image, dtype=np.float32)

        channels = image.shape[2]

        for channel in range(channels):
            values = image[:, :, channel]

            finite_mask = valid_mask & np.isfinite(values)
            valid_values = values[finite_mask]

            if valid_values.size == 0:
                continue

            minimum = float(np.min(valid_values))

            maximum = float(np.max(valid_values))

            if maximum <= minimum:
                normalized[:, :, channel] = 0.0

                continue

            normalized_channel = normalized[:, :, channel]
            normalized_channel[finite_mask] = (values[finite_mask] - minimum) / (
                maximum - minimum
            )

        return normalized
