"""
Region Feature Extraction

Extracts statistical features from each SLIC superpixel region.

For every region this class calculates:

    - Pixel area
    - Physical area in square meters
    - Mean
    - Standard deviation
    - Minimum
    - Maximum

for every supplied feature raster.

Feature rasters can include:

    - NDVI
    - GNDVI
    - NDRE
    - CI Red Edge
    - Evenson
    - Hue
    - Saturation
    - Value

The class operates entirely on the current tile, which keeps
memory usage low when processing large orthomosaics.
"""

import numpy as np


class RegionFeatureExtractor:

    def __init__(
        self,
        labels,
        pixel_area_m2=0.0025,
        tile_number=None
    ):
        """
        Parameters
        ----------
        labels : numpy.ndarray
            2D SLIC label array with shape:

                (height, width)

        pixel_area_m2 : float
            Physical area represented by one pixel.

            Example:
                0.05 m × 0.05 m = 0.0025 m²

        tile_number : int, optional
            Tile number used to create unique region IDs.
        """

        if labels is None:
            raise ValueError(
                "Labels cannot be None."
            )

        if labels.ndim != 2:
            raise ValueError(
                "Labels must be a 2D array. "
                f"Received shape: {labels.shape}"
            )

        if pixel_area_m2 <= 0:
            raise ValueError(
                "pixel_area_m2 must be greater than zero."
            )

        self.labels = labels
        self.pixel_area_m2 = float(pixel_area_m2)
        self.tile_number = tile_number

        self.features = {}

    # ============================================================
    # ADD FEATURE
    # ============================================================

    def add_feature(
        self,
        name,
        raster
    ):
        """
        Add a feature raster.

        The raster must have the exact same spatial dimensions
        as the label array.
        """

        if raster is None:
            raise ValueError(
                f"Feature '{name}' cannot be None."
            )

        if raster.shape != self.labels.shape:
            raise ValueError(
                f"Feature '{name}' shape "
                f"{raster.shape} does not match "
                f"labels shape {self.labels.shape}."
            )

        self.features[name] = np.asarray(
            raster,
            dtype=np.float32
        )

    # ============================================================
    # ADD MULTIPLE FEATURES
    # ============================================================

    def add_features(
        self,
        features
    ):
        """
        Add multiple feature rasters.

        Parameters
        ----------
        features : dict
            Example:

                {
                    "NDVI": ndvi,
                    "GNDVI": gndvi,
                    "NDRE": ndre,
                    "Hue": hue
                }
        """

        if features is None:
            return

        for name, raster in features.items():

            self.add_feature(
                name,
                raster
            )

    # ============================================================
    # EXTRACT FEATURES
    # ============================================================

    def get_features(self):
        """
        Extract statistics for every superpixel.

        Returns
        -------
        dict
            Dictionary keyed by unique region ID.
        """

        results = {}

        # --------------------------------------------------------
        # FIND REGIONS
        # --------------------------------------------------------

        region_ids = np.unique(
            self.labels
        )

        # --------------------------------------------------------
        # PROCESS EACH REGION
        # --------------------------------------------------------

        for region_id in region_ids:

            # Ignore negative labels.
            #
            # SLIC normally produces labels starting at 0,
            # so label 0 is a legitimate region and MUST NOT
            # automatically be discarded.
            if region_id < 0:
                continue

            mask = (
                self.labels == region_id
            )

            area_pixels = int(
                np.count_nonzero(mask)
            )

            if area_pixels == 0:
                continue

            # ----------------------------------------------------
            # PHYSICAL AREA
            # ----------------------------------------------------

            area_m2 = (
                area_pixels *
                self.pixel_area_m2
            )

            # ----------------------------------------------------
            # UNIQUE REGION ID
            # ----------------------------------------------------

            if self.tile_number is not None:

                unique_id = (
                    f"T{self.tile_number}_R{region_id}"
                )

            else:

                unique_id = (
                    f"R{region_id}"
                )

            # ----------------------------------------------------
            # BASE REGION INFORMATION
            # ----------------------------------------------------

            region = {

                "area_pixels":
                    area_pixels,

                "area_m2":
                    area_m2,

                "region_id":
                    unique_id
            }

            if self.tile_number is not None:

                region["tile"] = (
                    self.tile_number
                )

            # ----------------------------------------------------
            # FEATURE STATISTICS
            # ----------------------------------------------------

            for name, raster in self.features.items():

                values = raster[mask]

                # ------------------------------------------------
                # ONLY USE FINITE VALUES
                # ------------------------------------------------

                valid = np.isfinite(
                    values
                )

                values = values[
                    valid
                ]

                # ------------------------------------------------
                # NO VALID DATA
                # ------------------------------------------------

                if values.size == 0:

                    region[
                        f"{name}_mean"
                    ] = np.nan

                    region[
                        f"{name}_std"
                    ] = np.nan

                    region[
                        f"{name}_min"
                    ] = np.nan

                    region[
                        f"{name}_max"
                    ] = np.nan

                    continue

                # ------------------------------------------------
                # STATISTICS
                # ------------------------------------------------

                region[
                    f"{name}_mean"
                ] = float(
                    np.mean(values)
                )

                region[
                    f"{name}_std"
                ] = float(
                    np.std(values)
                )

                region[
                    f"{name}_min"
                ] = float(
                    np.min(values)
                )

                region[
                    f"{name}_max"
                ] = float(
                    np.max(values)
                )

            # ----------------------------------------------------
            # STORE REGION
            # ----------------------------------------------------

            results[
                unique_id
            ] = region

        return results

    # ============================================================
    # ALIAS
    # ============================================================

    def extract(self):
        """
        Alias for get_features().

        Allows either:

            extractor.get_features()

        or:

            extractor.extract()
        """

        return self.get_features()