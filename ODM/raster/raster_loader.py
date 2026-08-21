"""
Raster loading module.

Provides functionality for loading multispectral orthomosaic
TIFF images using rasterio.

Supports:
    - Loading the entire orthomosaic
    - Loading individual bands
    - Loading individual tiles/windows
    - Reading orthomosaic metadata
    - Detecting empty/no-data tiles
    - Preserving NIR and Red Edge bands

The loader does NOT normalize or rescale spectral values.

The raw values stored in the TIFF are preserved so that
vegetation-index calculations receive the original spectral
measurements.
"""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window


class RasterLoader:

    def __init__(self, tif_path):

        self.tif_path = Path(tif_path)

        if not self.tif_path.exists():

            raise FileNotFoundError(
                f"Raster does not exist: {self.tif_path}"
            )

    # ============================================================
    # LOAD ENTIRE IMAGE
    # ============================================================

    def load(self, band_indexes=None):
        """
        Load bands from the entire orthomosaic.

        If band_indexes is None, all bands are loaded.

        Returns:
            numpy.ndarray
            Shape: (bands, height, width)

        Spectral values are preserved exactly as stored
        in the TIFF, except for conversion to float32.
        """

        with rasterio.open(self.tif_path) as src:

            if band_indexes is None:

                band_indexes = list(
                    range(1, src.count + 1)
                )

            bands = src.read(
                indexes=band_indexes
            ).astype(
                np.float32,
                copy=False
            )

            bands = self._apply_nodata_mask(
                bands,
                src,
                band_indexes
            )

        return bands

    # ============================================================
    # LOAD TILE / WINDOW
    # ============================================================

    def load_window(
        self,
        x,
        y=None,
        width=None,
        height=None,
        band_indexes=None
    ):
        """
        Load a tile/window from the orthomosaic.

        Supports either:

            loader.load_window(window)

        or:

            loader.load_window(
                x,
                y,
                width,
                height
            )

        If band_indexes is None, all available bands
        are loaded.

        Returns:
            numpy.ndarray
            Shape: (bands, height, width)
        """

        with rasterio.open(self.tif_path) as src:

            # ----------------------------------------------------
            # RASTERIO WINDOW
            # ----------------------------------------------------

            if isinstance(x, Window):

                window = x

            # ----------------------------------------------------
            # X / Y / WIDTH / HEIGHT
            # ----------------------------------------------------

            else:

                if (
                    y is None
                    or width is None
                    or height is None
                ):

                    raise ValueError(
                        "Tile coordinates require "
                        "x, y, width, and height."
                    )

                window = Window(
                    col_off=x,
                    row_off=y,
                    width=width,
                    height=height
                )

            # ----------------------------------------------------
            # DETERMINE BANDS
            # ----------------------------------------------------

            if band_indexes is None:

                band_indexes = list(
                    range(1, src.count + 1)
                )

            # ----------------------------------------------------
            # LOAD TILE
            # ----------------------------------------------------

            bands = src.read(
                indexes=band_indexes,
                window=window
            ).astype(
                np.float32,
                copy=False
            )

            # ----------------------------------------------------
            # APPLY NODATA
            # ----------------------------------------------------

            bands = self._apply_nodata_mask(
                bands,
                src,
                band_indexes
            )

        return bands

    # ============================================================
    # NODATA HANDLING
    # ============================================================

    @staticmethod
    def _apply_nodata_mask(
        bands,
        src,
        band_indexes
    ):
        """
        Convert explicit raster nodata values to NaN.

        IMPORTANT:

        Zero is NOT automatically treated as nodata.

        This is critical for multispectral imagery because
        zero can be a legitimate stored spectral value.

        Only nodata values explicitly defined by the TIFF
        metadata are masked.
        """

        result = bands.astype(
            np.float32,
            copy=True
        )

        for i, band_index in enumerate(
            band_indexes
        ):

            nodata = src.nodatavals[
                band_index - 1
            ]

            if nodata is None:
                continue

            band = result[i]

            invalid = (
                np.isclose(
                    band,
                    nodata
                )
            )

            band[invalid] = np.nan

            result[i] = band

        return result

    # ============================================================
    # TILE DATA CHECK
    # ============================================================

    @staticmethod
    def tile_has_data(bands):
        """
        Determine whether a tile contains usable data.

        A tile is considered valid if at least one pixel
        contains a finite, non-nodata value.

        IMPORTANT:

        Zero is NOT automatically considered invalid.

        This prevents legitimate zero-valued spectral
        measurements from being discarded.
        """

        if bands is None:
            return False

        if bands.size == 0:
            return False

        return bool(
            np.any(
                np.isfinite(bands)
            )
        )

    # ============================================================
    # VALID PIXEL MASK
    # ============================================================

    @staticmethod
    def valid_pixel_mask(bands):
        """
        Return a 2D mask identifying pixels where at least
        one spectral band contains a finite value.

        Returns:
            bool ndarray
            Shape: (height, width)
        """

        if bands is None:

            raise ValueError(
                "Bands cannot be None."
            )

        if bands.ndim != 3:

            raise ValueError(
                "Expected bands with shape "
                "(bands, height, width)."
            )

        return np.any(
            np.isfinite(bands),
            axis=0
        )

    # ============================================================
    # GET METADATA
    # ============================================================

    def get_metadata(self):
        """
        Return metadata needed by the processing pipeline.
        """

        with rasterio.open(
            self.tif_path
        ) as src:

            return {

                "width": src.width,

                "height": src.height,

                "count": src.count,

                "pixel_width": abs(
                    src.transform.a
                ),

                "pixel_height": abs(
                    src.transform.e
                ),

                "crs": src.crs,

                "transform": src.transform,

                "dtypes": src.dtypes,

                "nodata": src.nodata,

                "nodatavals": src.nodatavals,

                "bounds": src.bounds,

                "scales": src.scales,

                "offsets": src.offsets
            }

    # ============================================================
    # BAND INFORMATION
    # ============================================================

    def get_band_information(self):
        """
        Return information about every band in the TIFF.

        Useful for verifying that the orthomosaic actually
        contains Blue, Green, Red, Red Edge, and NIR.
        """

        with rasterio.open(
            self.tif_path
        ) as src:

            information = []

            for band_number in range(
                1,
                src.count + 1
            ):

                information.append({

                    "band": band_number,

                    "dtype": src.dtypes[
                        band_number - 1
                    ],

                    "nodata": src.nodatavals[
                        band_number - 1
                    ],

                    "scale": src.scales[
                        band_number - 1
                    ],

                    "offset": src.offsets[
                        band_number - 1
                    ],

                    "description": (
                        src.descriptions[
                            band_number - 1
                        ]
                        if src.descriptions
                        else None
                    )
                })

        return information