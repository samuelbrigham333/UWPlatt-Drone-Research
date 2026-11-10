"""
Superpixel segmentation module.

Runs SLIC on vegetation-index rasters calculated from an already-loaded tile.

The source tile is used only to identify valid pixels; the index rasters are
the feature channels passed to SLIC.

Expected tile and index raster shapes:

    tile: (bands, height, width)
    each index raster: (height, width)
"""

import numpy as np
from skimage.segmentation import slic


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

    def run(self, tile, index_rasters):

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
        # VALID PIXEL MASK
        # --------------------------------------------------

        valid_mask = np.any(np.isfinite(tile) & (tile != 0), axis=0)

        if not np.any(valid_mask):
            print("Tile contains no data.")

            return None

        # --------------------------------------------------
        # PREPARE VEGETATION-INDEX IMAGE FOR SLIC
        # --------------------------------------------------

        if not index_rasters:
            raise ValueError("At least one vegetation-index raster is required.")

        index_arrays = []
        for name, raster in index_rasters.items():
            index_array = np.asarray(raster, dtype=np.float32)
            if index_array.shape != (height, width):
                raise ValueError(
                    f"Index '{name}' has shape {index_array.shape}; "
                    f"expected {(height, width)}."
                )
            index_arrays.append(index_array)

        index_image = np.stack(index_arrays, axis=-1)

        # SLIC expects:
        #
        # height × width × channels
        #
        image = index_image.astype(np.float32, copy=False)

        # --------------------------------------------------
        # REMOVE NaN / INF
        # --------------------------------------------------

        image = np.nan_to_num(image, nan=0.0, posinf=0.0, neginf=0.0)

        # --------------------------------------------------
        # NORMALIZE CHANNELS INDEPENDENTLY
        #
        # This is important for multispectral imagery.
        #
        # We do NOT want NIR or Red Edge to dominate SLIC
        # simply because its numerical range differs.
        # --------------------------------------------------

        image = self._normalize_channels(image, valid_mask)

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

            valid_values = values[valid_mask]

            valid_values = valid_values[np.isfinite(valid_values)]

            if valid_values.size == 0:
                continue

            minimum = float(np.min(valid_values))

            maximum = float(np.max(valid_values))

            if maximum <= minimum:
                normalized[:, :, channel] = 0.0

                continue

            normalized[:, :, channel] = (values - minimum) / (maximum - minimum)

        return normalized
