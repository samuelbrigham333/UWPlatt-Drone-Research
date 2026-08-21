"""
Superpixel segmentation module.

Runs SLIC on an already-loaded raster tile.

The segmenter does NOT reopen the TIFF. The application
loads each tile once and passes the tile data here.

Expected tile shape:

    (bands, height, width)

For multispectral imagery:

    Band 0 = Blue
    Band 1 = Green
    Band 2 = Red
    Band 3 = Red Edge
    Band 4 = NIR
"""

import numpy as np
from skimage.segmentation import slic


class SuperpixelSegmenter:

    def __init__(
        self,
        num_segments,
        compactness=10.0,
        sigma=1.0
    ):

        if num_segments <= 0:
            raise ValueError(
                "num_segments must be greater than zero."
            )

        if compactness <= 0:
            raise ValueError(
                "compactness must be greater than zero."
            )

        if sigma < 0:
            raise ValueError(
                "sigma cannot be negative."
            )

        self.num_segments = int(
            num_segments
        )

        self.compactness = float(
            compactness
        )

        self.sigma = float(
            sigma
        )

    # ------------------------------------------------------
    # RUN SLIC
    # ------------------------------------------------------

    def run(self, tile):

        if tile is None:
            raise ValueError(
                "Tile cannot be None."
            )

        if tile.ndim != 3:
            raise ValueError(
                "Expected tile with shape "
                "(bands, height, width). "
                f"Received {tile.shape}"
            )

        bands, height, width = tile.shape

        if height == 0 or width == 0:
            return None

        # --------------------------------------------------
        # VALID PIXEL MASK
        # --------------------------------------------------

        valid_mask = np.any(
            np.isfinite(tile)
            & (tile != 0),
            axis=0
        )

        if not np.any(valid_mask):

            print(
                "    Tile contains no data."
            )

            return None

        # --------------------------------------------------
        # PREPARE IMAGE FOR SLIC
        # --------------------------------------------------

        # SLIC expects:
        #
        # height × width × channels
        #
        image = np.moveaxis(
            tile,
            0,
            -1
        ).astype(
            np.float32,
            copy=False
        )

        # --------------------------------------------------
        # REMOVE NaN / INF
        # --------------------------------------------------

        image = np.nan_to_num(
            image,
            nan=0.0,
            posinf=0.0,
            neginf=0.0
        )

        # --------------------------------------------------
        # NORMALIZE CHANNELS INDEPENDENTLY
        #
        # This is important for multispectral imagery.
        #
        # We do NOT want NIR or Red Edge to dominate SLIC
        # simply because its numerical range differs.
        # --------------------------------------------------

        image = self._normalize_channels(
            image,
            valid_mask
        )

        # --------------------------------------------------
        # ACTUAL NUMBER OF SEGMENTS
        # --------------------------------------------------

        pixel_count = (
            height * width
        )

        requested_segments = min(
            self.num_segments,
            pixel_count
        )

        print(
            f"    SLIC segments: "
            f"{requested_segments}"
        )

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
            mask=valid_mask
        )

        # --------------------------------------------------
        # REMOVE INVALID PIXELS
        # --------------------------------------------------

        labels = labels.astype(
            np.int32,
            copy=False
        )

        labels[
            ~valid_mask
        ] = -1

        # --------------------------------------------------
        # REPORT
        # --------------------------------------------------

        valid_labels = labels[
            labels >= 0
        ]

        if valid_labels.size == 0:

            print(
                "    SLIC produced no valid regions."
            )

            return None

        unique_regions = np.unique(
            valid_labels
        )

        print(
            f"Generated "
            f"{len(unique_regions)} "
            f"valid superpixels."
        )

        return labels

    # ------------------------------------------------------
    # NORMALIZE CHANNELS
    # ------------------------------------------------------

    @staticmethod
    def _normalize_channels(
        image,
        valid_mask
    ):

        normalized = np.zeros_like(
            image,
            dtype=np.float32
        )

        channels = image.shape[2]

        for channel in range(channels):

            values = image[
                :, :, channel
            ]

            valid_values = values[
                valid_mask
            ]

            valid_values = valid_values[
                np.isfinite(valid_values)
            ]

            if valid_values.size == 0:
                continue

            minimum = float(
                np.min(valid_values)
            )

            maximum = float(
                np.max(valid_values)
            )

            if maximum <= minimum:

                normalized[
                    :, :, channel
                ] = 0.0

                continue

            normalized[
                :, :, channel
            ] = (
                values - minimum
            ) / (
                maximum - minimum
            )

        return normalized