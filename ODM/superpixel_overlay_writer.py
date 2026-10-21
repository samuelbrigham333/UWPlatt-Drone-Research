

"""

Generate superpixel labels and RGB/multispectral overlays.



The multispectral orthomosaic is the reference grid.

The RGB orthomosaic is automatically aligned to that grid

using bilinear resampling before overlays are generated.

"""



from pathlib import Path



import numpy as np

import rasterio

from PIL import Image

from rasterio.enums import Resampling

from rasterio.warp import reproject





class SuperpixelOverlayWriter:

    def __init__(self, ortho_path, output_path, rgb_ortho_path):

        # --------------------------------------------------

        # INPUT AND OUTPUT PATHS

        # --------------------------------------------------

        self.ortho_path = Path(ortho_path)

        self.rgb_ortho_path = Path(rgb_ortho_path)

        self.output_path = Path(output_path)



        self.output_path.mkdir(parents=True, exist_ok=True)



        self.labels_path = (

            self.output_path / "superpixel_labels.tif"

        )

        self.overlay_path = (

            self.output_path / "superpixel_overlay.tif"

        )

        self.multispectral_overlay_path = (

            self.output_path / "multispectral_overlay.tif"

        )

        self.aligned_rgb_path = (

            self.output_path / "rgb_orthomosaic_aligned.tif"

        )



        self.ortho = None

        self.rgb_ortho = None

        self.labels = None

        self.overlay = None

        self.multispectral_overlay = None



        try:

            # --------------------------------------------------

            # OPEN MULTISPECTRAL REFERENCE

            # --------------------------------------------------

            self.ortho = rasterio.open(self.ortho_path)



            if self.ortho.count < 3:

                raise ValueError(

                    "Multispectral orthomosaic must contain "

                    "at least three bands."

                )



            # --------------------------------------------------

            # ALIGN RGB TO MULTISPECTRAL GRID

            # --------------------------------------------------

            print(

                "Aligning RGB orthomosaic to "

                "multispectral grid..."

            )



            self.align_rgb_ortho(

                rgb_path=self.rgb_ortho_path,

                reference=self.ortho,

                output_path=self.aligned_rgb_path,

            )



            # Use the aligned RGB, not the original.

            self.rgb_ortho = rasterio.open(

                self.aligned_rgb_path

            )



            # --------------------------------------------------

            # VERIFY ALIGNMENT

            # --------------------------------------------------

            self._validate_alignment()



            print(

                "Aligned RGB dimensions: "

                f"{self.rgb_ortho.width} x "

                f"{self.rgb_ortho.height}"

            )



            # --------------------------------------------------

            # CONFIGURE LABEL OUTPUT

            # --------------------------------------------------

            self.profile = self.ortho.profile.copy()

            self.profile.update(

                driver="GTiff",

                dtype="uint32",

                count=1,

                nodata=0,

            )

            self.profile.pop("photometric", None)



            # --------------------------------------------------

            # CONFIGURE RGB OVERLAY

            # --------------------------------------------------

            self.overlay_profile = (

                self.rgb_ortho.profile.copy()

            )

            self.overlay_profile.update(

                driver="GTiff",

                dtype="uint8",

                count=3,

                nodata=None,

            )

            self.overlay_profile.pop("photometric", None)



            # --------------------------------------------------

            # CONFIGURE MULTISPECTRAL OVERLAY

            # --------------------------------------------------

            self.multispectral_overlay_profile = (

                self.ortho.profile.copy()

            )

            self.multispectral_overlay_profile.update(

                driver="GTiff",

                dtype="uint8",

                count=3,

                nodata=None,

            )

            self.multispectral_overlay_profile.pop(

                "photometric", None

            )



            # --------------------------------------------------

            # CREATE OUTPUT FILES

            # --------------------------------------------------

            self.labels = rasterio.open(

                self.labels_path,

                "w",

                **self.profile,

            )



            self.overlay = rasterio.open(

                self.overlay_path,

                "w",

                **self.overlay_profile,

            )



            self.multispectral_overlay = rasterio.open(

                self.multispectral_overlay_path,

                "w",

                **self.multispectral_overlay_profile,

            )



        except Exception:

            self.close()

            raise



    # ------------------------------------------------------

    # BILINEAR RGB ALIGNMENT

    # ------------------------------------------------------

    @staticmethod

    def align_rgb_ortho(rgb_path, reference, output_path):

        """

        Reproject RGB imagery onto the multispectral grid.



        The output uses the reference raster's:

        - CRS

        - transform

        - width

        - height



        Only the first three RGB bands are written.

        """

        rgb_path = Path(rgb_path)

        output_path = Path(output_path)



        with rasterio.open(rgb_path) as source:

            if source.count < 3:

                raise ValueError(

                    "RGB orthomosaic must contain "

                    "at least three bands."

                )



            if source.crs is None or reference.crs is None:

                raise ValueError(

                    "Both orthomosaics must have a valid CRS."

                )



            if any(

                dtype != "uint8"

                for dtype in source.dtypes[:3]

            ):

                raise ValueError(

                    "RGB alignment currently requires "

                    "8-bit RGB bands."

                )



            # Copy RGB metadata, then replace its grid.

            profile = source.profile.copy()

            profile.update(

                driver="GTiff",

                width=reference.width,

                height=reference.height,

                crs=reference.crs,

                transform=reference.transform,

                count=3,

                dtype="uint8",

                nodata=None,

            )



            # Remove source-specific color settings.

            profile.pop("photometric", None)



            with rasterio.open(

                output_path,

                "w",

                **profile,

            ) as destination:



                # Reproject each RGB channel separately.

                for band in range(1, 4):

                    reproject(

                        source=rasterio.band(source, band),

                        destination=rasterio.band(

                            destination, band

                        ),

                        src_transform=source.transform,

                        src_crs=source.crs,

                        src_nodata=source.nodata,

                        dst_transform=reference.transform,

                        dst_crs=reference.crs,

                        dst_nodata=0,

                        resampling=Resampling.bilinear,

                        init_dest_nodata=True,

                    )



        return output_path



    # ------------------------------------------------------

    # VERIFY RASTER ALIGNMENT

    # ------------------------------------------------------

    def _validate_alignment(self):

        """

        Confirm the aligned RGB raster matches

        the multispectral reference grid.

        """

        if (

            self.ortho.width != self.rgb_ortho.width

            or self.ortho.height != self.rgb_ortho.height

        ):

            raise ValueError(

                "Multispectral and RGB rasters must "

                "have matching dimensions."

            )



        if self.ortho.crs != self.rgb_ortho.crs:

            raise ValueError(

                "Multispectral and RGB rasters must "

                "use the same CRS."

            )



        if self.ortho.transform != self.rgb_ortho.transform:

            raise ValueError(

                "Multispectral and RGB rasters must "

                "have matching transforms."

            )



    # ------------------------------------------------------

    # DETECT SUPERPIXEL BOUNDARIES

    # ------------------------------------------------------

    @staticmethod

    def _detect_boundaries(labels):

        """

        Find locations where neighboring valid

        superpixel IDs differ.

        """

        valid = labels >= 0



        boundaries = np.zeros(

            labels.shape,

            dtype=bool,

        )



        # Compare horizontal neighbors.

        boundaries[:, 1:] |= (

            (labels[:, 1:] != labels[:, :-1])

            & valid[:, 1:]

            & valid[:, :-1]

        )



        # Compare vertical neighbors.

        boundaries[1:, :] |= (

            (labels[1:, :] != labels[:-1, :])

            & valid[1:, :]

            & valid[:-1, :]

        )



        return boundaries



    # ------------------------------------------------------

    # PAINT SUPERPIXEL BOUNDARIES

    # ------------------------------------------------------

    @staticmethod

    def _paint_boundaries(image, boundaries):

        """

        Paint boundaries hot pink: RGB(255, 105, 180).

        """

        image[0, boundaries] = 255

        image[1, boundaries] = 105

        image[2, boundaries] = 180



        return image



    # ------------------------------------------------------

    # NORMALIZE MULTISPECTRAL VISUALIZATION

    # ------------------------------------------------------

    @staticmethod

    def _normalize_multispectral(multispectral):

        """

        Convert three multispectral bands to uint8.



        Each channel is independently scaled to 0-255

        for visualization.

        """

        multispectral = multispectral.astype(np.float32)



        visualization = np.zeros(

            multispectral.shape,

            dtype=np.uint8,

        )



        for band_index in range(3):

            band_data = multispectral[band_index]



            valid = (

                np.isfinite(band_data)

                & (band_data > 0)

            )



            if not np.any(valid):

                continue



            minimum = np.min(band_data[valid])

            maximum = np.max(band_data[valid])



            if maximum <= minimum:

                continue



            normalized = (

                (band_data - minimum)

                / (maximum - minimum)

            ) * 255.0



            normalized = np.clip(

                normalized,

                0,

                255,

            )



            visualization[band_index] = (

                normalized.astype(np.uint8)

            )



        return visualization



    # ------------------------------------------------------

    # WRITE SUPERPIXEL LABELS

    # ------------------------------------------------------

    def write_labels(self, labels, window, id_offset):

        """

        Write unique superpixel IDs to a GeoTIFF.



        Zero is reserved for NoData.

        """

        if labels is None:

            return



        labels_to_write = np.where(

            labels >= 0,

            labels + id_offset + 1,

            0,

        ).astype(np.uint32)



        self.labels.write(

            labels_to_write,

            1,

            window=window,

        )



    # ------------------------------------------------------

    # WRITE RGB OVERLAY

    # ------------------------------------------------------

    def write_overlay(self, labels, window):

        """

        Draw superpixel boundaries on the aligned RGB

        orthomosaic.

        """

        if labels is None:

            return



        rgb = self.rgb_ortho.read(

            indexes=[1, 2, 3],

            window=window,

        )



        boundaries = self._detect_boundaries(labels)



        overlay_pixels = self._paint_boundaries(

            rgb.copy(),

            boundaries,

        )



        self.overlay.write(

            overlay_pixels,

            window=window,

        )



    # ------------------------------------------------------

    # WRITE MULTISPECTRAL OVERLAY

    # ------------------------------------------------------

    def write_multispectral_overlay(self, labels, window):

        """

        Draw the same superpixel boundaries on a

        three-band multispectral visualization.

        """

        if labels is None:

            return



        multispectral = self.ortho.read(

            indexes=[1, 2, 3],

            window=window,

        )



        visualization = self._normalize_multispectral(

            multispectral

        )



        boundaries = self._detect_boundaries(labels)



        visualization = self._paint_boundaries(

            visualization,

            boundaries,

        )



        self.multispectral_overlay.write(

            visualization,

            window=window,

        )



    # ------------------------------------------------------

    # EXPORT JPEG PREVIEW

    # ------------------------------------------------------

    @staticmethod

    def save_overlay_jpg(overlay_path, jpg_path):

        """

        Export a three-band uint8 GeoTIFF as a JPEG.

        """

        with rasterio.open(overlay_path) as src:

            rgb = src.read([1, 2, 3])



            rgb = np.moveaxis(

                rgb,

                0,

                -1,

            )



            if rgb.dtype != np.uint8:

                raise ValueError(

                    "JPEG export requires an 8-bit overlay."

                )



        Image.fromarray(rgb).save(

            jpg_path,

            quality=95,

        )



    # ------------------------------------------------------

    # CLOSE RASTER DATASETS

    # ------------------------------------------------------

    def close(self):

        """

        Close all open input and output raster files.

        """

        for name in (

            "labels",

            "overlay",

            "multispectral_overlay",

            "ortho",

            "rgb_ortho",

        ):

            dataset = getattr(self, name, None)



            if dataset is not None and not dataset.closed:

                dataset.close()
