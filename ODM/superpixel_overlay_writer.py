"""
Handles SuperPixel Overlay onto BOTH orthomosaic images

Works as follows
1. Opens BOTH rasters
   self.ortho = multispectral ; self.rgb_ortho = RGB
2. Checks alignment using dimensions, CRS (coordinate reference system),
   and transform.
3. Creates TWO output files:
   superpixel_labels.tif -> Stores superpixel IDs
   superpixel_overlay.tif -> Stores RGB image with hot-pink boundaries
4. Writes labels, converts invalid labels to 0, and writes the tile's
   labels to the correct raster window.
5. Draws boundaries by comparing neighboring label values and painting
   detected boundaries hot pink (color subject to change).
"""

from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.warp import reproject


class SuperpixelOverlayWriter:
    def __init__(
        self,
        ortho_path,
        output_path,
        rgb_ortho_path,
    ):
        self.ortho_path = Path(ortho_path)
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.rgb_ortho_path = Path(rgb_ortho_path)

        self.labels_path = self.output_path / "superpixel_labels.tif"
        self.overlay_path = self.output_path / "superpixel_overlay.tif"

        aligned_rgb_path = self.rgb_ortho_path.with_name(
            f"{self.rgb_ortho_path.stem}_aligned.tif"
        )

        with rasterio.open(self.ortho_path) as reference:
            target_crs = reference.crs
            target_transform = reference.transform
            target_width = reference.width
            target_height = reference.height

        with rasterio.open(self.rgb_ortho_path) as source:
            if source.count < 3:
                raise ValueError("RGB Orthomosaic should have at least 3 bands.")

            profile = source.profile.copy()
            profile.update(
                driver="GTiff",
                width=target_width,
                height=target_height,
                crs=target_crs,
                transform=target_transform,
                nodata=0,
                count=3,
                dtype="uint8",
            )

            with rasterio.open(aligned_rgb_path, "w", **profile) as destination:
                for band in range(1, 4):
                    reproject(
                        source=rasterio.band(source, band),
                        destination=rasterio.band(destination, band),
                        src_transform=source.transform,
                        src_crs=source.crs,
                        src_nodata=source.nodata,
                        dst_transform=target_transform,
                        dst_crs=target_crs,
                        dst_nodata=0,
                        resampling=Resampling.bilinear,
                    )

        print(f"Aligned RGB orthomosaic created: {aligned_rgb_path}")

        # Use the aligned RGB raster for every downstream overlay operation.
        self.rgb_ortho_path = aligned_rgb_path
        self.ortho = rasterio.open(self.ortho_path)
        self.rgb_ortho = rasterio.open(self.rgb_ortho_path)

        if self.ortho.crs != self.rgb_ortho.crs:
            self.ortho.close()
            self.rgb_ortho.close()
            raise ValueError(
                "Multispectral and aligned RGB rasters must use the same CRS."
            )

        # Check geographic transforms
        if self.ortho.transform != self.rgb_ortho.transform:
            self.ortho.close()
            self.rgb_ortho.close()
            raise ValueError(
                "Multispectral and RGB rasters must have matching transforms."
            )

        if (
            self.ortho.width != self.rgb_ortho.width
            or self.ortho.height != self.rgb_ortho.height
        ):
            self.ortho.close()
            self.rgb_ortho.close()
            raise ValueError(
                "Multispectral and aligned RGB rasters must have matching dimensions."
            )

        # Save the multispectral raster settings for the label output
        self.profile = self.ortho.profile.copy()
        self.profile.update(
            dtype=np.uint32,
            count=1,
            nodata=0,
        )

        # Create the RGB overlay raster profile
        self.overlay_profile = self.rgb_ortho.profile.copy()
        self.overlay_profile.update(
            count=3,
        )

        # Open the overlay file
        self.overlay = rasterio.open(
            self.overlay_path,
            "w",
            **self.overlay_profile,
        )

        # Open the label file
        self.labels = rasterio.open(
            self.labels_path,
            "w",
            **self.profile,
        )

    def write_labels(self, labels, window, id_offset):
        """
        Write the superpixel labels to the output raster.

        Parameters
        ----------
        labels : np.ndarray
            The superpixel labels to write.
        window : rasterio.windows.Window
            The window of the output raster to write to.
        id_offset : int
            The offset to add to the superpixel labels to ensure
            tiles do not reuse the same IDs.
        """
        if labels is None:
            return "No labels to write :("

        labels_to_write = np.where(
            labels >= 0,
            labels + id_offset + 1,  # +1 ensures labels start at 1, not 0
            0,  # 0 is reserved for nodata
        )

        labels_to_write = labels_to_write.astype(np.uint32)

        self.labels.write(
            labels_to_write,
            1,  # First and only output band
            window=window,
        )

    def write_overlay(self, labels, window):
        """Draw superpixel boundaries on the RGB image for this tile."""
        if labels is None:
            return

        # Read RGB pixels for this tile
        rgb = self.rgb_ortho.read(window=window)

        # Detect boundaries between neighboring valid superpixels
        valid = labels >= 0
        boundaries = np.zeros(labels.shape, dtype=bool)

        # Compare each pixel with its left neighbor
        boundaries[:, 1:] |= (
            (labels[:, 1:] != labels[:, :-1]) & valid[:, 1:] & valid[:, :-1]
        )

        # Compare each pixel with the pixel above it
        boundaries[1:, :] |= (
            (labels[1:, :] != labels[:-1, :]) & valid[1:, :] & valid[:-1, :]
        )

        # Copy RGB pixels so we don't modify the source raster
        overlay_pixels = rgb.copy()

        # Paint boundaries hot pink
        overlay_pixels[0, boundaries] = 255  # Red
        overlay_pixels[1, boundaries] = 105  # Green
        overlay_pixels[2, boundaries] = 180  # Blue

        # Write this tile to the output raster
        self.overlay.write(overlay_pixels, window=window)

    @staticmethod
    def save_overlay_jpg(overlay_path, jpg_path):
        """Save an RGB JPEG preview of the completed overlay GeoTIFF."""
        with rasterio.open(overlay_path) as src:
            rgb = src.read([1, 2, 3])
            rgb = np.moveaxis(rgb, 0, -1)

            # JPEG requires 8-bit image data
            if rgb.dtype != np.uint8:
                raise ValueError("JPEG export currently requires an 8-bit RGB overlay.")

        Image.fromarray(rgb).save(jpg_path, quality=95)

    def close(self):
        """Close output and input raster files."""
        self.labels.close()
        self.overlay.close()
        self.ortho.close()
        self.rgb_ortho.close()
