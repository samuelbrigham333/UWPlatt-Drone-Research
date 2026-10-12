
import numpy as np
import rasterio


class SuperpixelOverlayWriter:
    def __init__(
        self,
        ortho_path,
        output_path,
    ):
        self.ortho_path = ortho_path
        self.output_path = output_path

        self.output_directory.mkdir(parents=True, exist_ok=True)

        self.labels_path = self.output_path / "superpixel_labels.tif"

        self.overlay_path = self.output_path / "superpixel_overlay.tif"

        self.ortho = rasterio.open(self.ortho_path)

        self.profile = self.ortho.profile.copy()  # saves the raster settings

        self.profile.update(
            dtype=np.uint32,  # 32-bit unsigned integer
            count=1,
            nodata=0,
        )

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

    def close(self):
        self.labels.close()
