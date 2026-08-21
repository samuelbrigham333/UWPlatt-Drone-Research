"""
Superpixel Overlay Writer

Creates a single full-orthomosaic visualization from
tile-by-tile SLIC segmentation

The original multispectral orthomosaic is NEVER modified

Output:
    - 3-band RGB GeoTIFF
    - JPG Visualization
"""

from pathlib import Path

import cv2
import numpy as np
import rasterio

class SuperpixelOverlayWriter:

    YELLOW = (255, 255, 0)

    def __init__(
            self,
            source_path,
            output_directory,
            yellow_thickness = 1, #can be changed?
            jpeg_quality = 95,
    ):
        self.source_path = Path(source_path)
        self.output_directory = Path (output_directory)

        self.yellow_thickness = yellow_thickness
        self.jpeg_quality = jpeg_quality

        self.output_directory.mkdir(
            parents = True,
            exist_ok= True,
        )

        self.geotiff_path = (
            self.output_directory /
            "odm_orthophoto_superpixels.tif"
        )

        self.jpg_path = (
            self.output_directory / "odm_orthophoto_superpixels.jpg"
        )

        self._source = None
        self._geotiff = None

        self._initialize()

    #INITIALIZE

    def _initialize(self):

        self._source = rasterio.open(
            self.source_path,
            "r"
        )

        if self._source.count < 3:
            self.close()

            raise ValueError(
                "Superpixel visualization requires at least 3 bands for RGB."
            )

    #CREATE 3-band RGB GeoTIFF

        profile = self._source.profile.copy()

        profile.update(
        drive="GTiff",
        count = 3,
        dtype = "uint8",
        compress = "deflate",
        photometric = "RGB"
     )

    #remove multispectral-specific metadata that should not describe the RGB visualization

        profile.pop("nodata", None)

        self._geotiff = rasterio.open(
            self.geotiff_path,
            "w",
            **profile
        )

    #WRITE

    def write_tile(self,
                   tile_bands,
                   labels,
                   window
                   ):

        if tile_bands.ndim != 3:

            raise ValueError(
                "tile_bands must have shape "
                "(bands, height, width)."
                f"Received: {tile_bands.shape}"
            )

        height = tile_bands.shape[1]
        width = tile_bands.shape[2]

        if labels.shape != (height, width):

            raise ValueError(
                "SLIC labels do not match tile dimensions. "
                f"Labels: {labels.shape}, "
                f"Tile: {(height, width)}"
            )

        blue = tile_bands[0]
        green = tile_bands[1]
        red = tile_bands[2]

        rgb_max = max(
            float(np.nanmax(blue)),
            float(np.nanmax(green)),
            float(np.nanmax(red)),

        )

        if not np.isfinite(rgb_max):
            rgb_max = 1.0

        if rgb_max <= 1.0:

            scale = 255.0

        else:

            scale = 255.0 / rgb_max

        blue = np.nan_to_num(
            blue,
            nan = 0.0,
            posinf = 0.0,
            neginf = 0.0,
        )

        green = np.nan_to_num(
            green,
            nan = 0.0,
            posinf = 0.0,
            neginf = 0.0
        )

        red = np.nan_to_num(
            red,
            nan = 0.0,
            posinf = 0.0,
            neginf = 0.0,
        )

        blue = np.clip(
            blue * scale,
            0,
            255
        ).astype(np.uint8)

        green = np.clip(
            green * scale,
            0,
            255
        )

        red = np.clip(
            red * scale,
            0,
            255
        )

        image = cv2.merge(
            [
                blue,
                green,
                red
            ]
        )

        boundaries = self._find_boundaries(
            labels
        )

        if self.yellow_thickness == 1:

            image[boundaries] = (
                0,
                255,
                255
            )

        else:
            boundary_uint8 = (
                boundaries.astype(np.uint8) * 255
            )

            kernel = np.ones(
                (3, 3),
                dtype = np.uint8
            )

            boundary_uint8 = cv2.dilate(
                boundary_uint8,
                kernel,
                iterations=self.yellow_thickness - 1
            )

            image[
                boundary_uint8 > 0
            ] = (
                0,
                255,
                255
            )

    #WRITE TILE TO GEOTIFF

        rgb_image = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB
        )

        self._geotiff.write(
            rgb_image[:, :, 0],
            2,
            window = window
        )

        self._geotiff.write(
            rgb_image[:, :, 2],
            3,
            window = window
        )

        self._store_jpeg_tile(
            image,
            window
        )

    #FIND BOUNDARIES

    @staticmethod
    def _find_boundaries(labels):
        boundaries = np.zeros(
            labels.shape,
            dtype=bool
        )

        boundaries[:, :, 1] |= (
            labels[:, :, -1] !=
            labels [:, 1:]
        )

        boundaries[:-1, :] |= (
            labels[:-1, :] !=
            labels [1:, :]
        )

        return boundaries

    def _store_jpeg_tile(self,
                         image,
                         window
    ):
        if not hasattr(
            self,
            "_jpeg_tiles"
        ):

            self._jpeg_tiles = []
        self._jpeg_tiles.append(
            (
                int(window.col_off),
                int(window.row_off),
                image.copy()
            )
        )

    def _create_jpeg(self):

        if not hasattr(
            self,
            "_jpeg_tiles"
        ):

            return

        if not self._jpeg_tiles:

            return

        width = self._source.width
        height = self._source.height

        full_image = np.zeros(
            (height, width, 3),
            dtype = np.uint8
        )

        for(
            x,
            y,
            tile
        ) in self._jpeg_tiles:

            tile_height = tile.shape[0]
            tile_width = tile.shape[1]

            end_x = min(
                x + tile_width,
                width
            )

            end_y = min(
                y + tile_height,
                height
            )

            actual_width = end_x - x
            actual_height = end_y -y

            if(
                actual_width <= 0 or
                actual_height <= 0
            ):
                continue

            full_image[
            y:end_y,
            x:end_x
            ] = tile[
                :actual_height,
                :actual_width
                ]

        cv2.imwrite(
            str(self.jpg_path),
            full_image,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                self.jpeg_quality
            ]
        )

        #release tiles

        self._jpeg_tiles.clear()

    #CLOSE

    def close(self):
        try:
            if self._geotiff is not None:
                self._geotiff.close()
                self._geotiff = None
            if self._source is not None:
                self._source.close()
                self._source = None
            self._create_jpeg()

        finally:
            self._source = None
            self._geotiff = None

    #CONTEXT MANAGER

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


