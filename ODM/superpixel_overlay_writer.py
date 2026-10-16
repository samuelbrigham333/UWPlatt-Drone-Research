from pathlib import Path

import numpy as np
import rasterio


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

        self.ortho = rasterio.open(self.ortho_path)  # opens the multispectral ortho
        self.rgb_ortho = rasterio.open(self.rgb_ortho_path)  # opens the rgb ortho

        if (
            self.ortho.width != self.rgb_ortho.width
            or self.ortho.height != self.rgb_ortho.height
        ):
            raise ValueError(
                "Multispectral and RGB rasters must have matching dimensions."
            )

        if self.ortho.crs != self.rgb_ortho.crs:
            raise ValueError("Multispectral and RGB rasters must use the same CRS.")

        if self.ortho.transform != self.rgb_ortho.transform:
            raise ValueError(
                "Multispectral and RGB rasters must use the same Transform."
            )

        self.profile = self.ortho.profile.copy()  # saves the raster settings

        self.profile.update(
            dtype=np.uint32,  # 32-bit unsigned integer
            count=1,
            nodata=0,
        )

        # create the overlay raster
        self.overlay_profile = self.rgb_ortho.profile.copy()
        self.overlay_profile.update(
            count=3,
        )

        # open the overlay file
        self.overlay = rasterio.open(self.overlay_path, "w", **self.overlay_profile)

        self.labels = rasterio.open(
            self.labels_path,
            "w",
            **self.profile,  # pulls settings from profile that were just saved
            # ** unpacks the dict into keyword args
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
            The offset to add to the superpixel labels.
            Ensures tiles do not reuse the same IDs
        """

        if labels is None:
            return "No labels to write :("

        labels_to_write = np.where(
            labels >= 0,
            labels + id_offset + 1,  # +1 to ensure labels start at 1 and not 0
            0,  # 0 is reserved for nodata
        )

        labels_to_write = labels_to_write.astype(np.uint32)

        self.labels.write(
            labels_to_write,
            1,  # output rasters first and only band
            window=window,
        )

    def write_overlay(self, labels, window):
        rgb = self.rgb_ortho.read(window=window)  # grabs and reads rgb_ortho

        # detects the boundaries between neighboring superpixels
        boundaries = np.zeros(labels.shape, dtype=bool)

        boundaries[:, 1:] |= labels[:, 1:] != labels[:, :-1]
        boundaries[1:, :] |= (
            labels[1:, :] != labels[:-1, :]
        )  # compares each row with the row immediately above it

        valid = labels >= 0 

        boundaries[:, 1:] |= (
            (labels[:, 1:] != labels[:, :-1])
            & valid[:, 1:]  # checks the pixels on the right
            & valid[:, :-1]  # checks the pixels on the left
        )
        boundaries[1:, :] |= (
            (labels[1:, :] != labels[:-1, :]) & valid[1:, :] & valid[:-1, :]
        )

        # copy RGB pixels so we don't modify the source raster
        overlay_pixels = rgb.copy()

        # Paint boundaries "hot pink" (can be changed to be any color)
        # NOTE: red would be 255 at the top, other values 0.
        overlay_pixels[0, boundaries] = 255
        overlay_pixels[1, boundaries] = 105
        overlay_pixels[2, boundaries] = 180

        self.overlay.write(overlay_pixels, window=window)

    def close(self):
        self.labels.close()
        self.overlay.close()
        self.ortho.close()
        self.rgb_ortho.close()
